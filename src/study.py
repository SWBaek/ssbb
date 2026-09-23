"""Execute frozen numerical BB experiments sequentially. Run python -m src.study."""
from pathlib import Path
from dataclasses import asdict, replace
from itertools import product, combinations
import json, hashlib, time, sys, platform
import numpy as np
import pandas as pd
from scipy.stats import qmc
from .model import Case, Control, simulate, harmonic_metrics, FS, TS, F0, W0
from .verify import run_verification
ROOT=Path(__file__).resolve().parents[1]
RESULTS=ROOT/'results'; DATA=ROOT/'data'
CONFIG=json.loads((ROOT/'study_config.json').read_text())

def write_json(path,obj):
    Path(path).write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main_cases():
    out=[]
    for v,p,q in product(CONFIG['main_vrms'],CONFIG['main_p_w'],CONFIG['main_q_var']):
        if p==0 and q==0: continue
        out.append(Case(f'M{len(out)+1:03d}',p=p,q=q,vrms=v))
    assert len(out)==72
    return out

def holdout_cases():
    # Uniform LHS is coverage, NOT a measured manufacturing distribution.
    bounds=np.array([[175,3500],[-1750,1750],[207,253],[380,420],[.00135,.00165],
        [.00005,.00040],[.12,.18],[.05,.20],[.7,1.3],[.15,.45],[0,.01],[0,.005],[-.05,.05],[0,.02]])
    unit=qmc.LatinHypercube(d=14,seed=CONFIG['holdout_seed']).random(64)
    xx=qmc.scale(unit,bounds[:,0],bounds[:,1]); out=[]
    names=['p','q','vrms','vdc','lf','lg','rf','rg','dead_us','zero_a','v3','v5','offset_a','adc_step']
    for k,x in enumerate(xx):
        out.append(Case(f'H{k+1:03d}',**dict(zip(names,map(float,x))),dead_shape=k%2))
    for p,q,v in product([0,175],[-700,700],[207,253]):
        out.append(Case(f'H{len(out)+1:03d}',p=p,q=q,vrms=v,dead_us=1.3,zero_a=.15,
                        lf=.00135,lg=.0004,dead_shape=1))
    assert len(out)==72
    return out

class Archive:
    """Lossless float64 traces. NPZ arrays: channels x samples; max 32 runs/file."""
    def __init__(self,phase): self.phase=phase; self.batch=0; self.buffer={}
    def add(self,key,wave,full=False):
        if len(self.buffer)>=32: self.flush()
        path=f'data/{self.phase}_{self.batch:03d}.npz'
        value=wave if full else wave[-6400:, [2,3,4,5,6,7]]
        self.buffer[key]=np.ascontiguousarray(value.T)
        return path
    def flush(self):
        if self.buffer:
            np.savez_compressed(DATA/f'{self.phase}_{self.batch:03d}.npz',**self.buffer)
            self.buffer={}; self.batch+=1

def run_phase(phase,jobs,all_rows,full=False):
    arc=Archive(phase); rows=[]; start=time.perf_counter()
    for k,(case,ctrl) in enumerate(jobs):
        runid=f'{phase}_{k+1:04d}'
        w=simulate(case,ctrl,cycles=CONFIG['cycles'],substeps=CONFIG['plant_substeps'],transient=full)
        m,h=harmonic_metrics(w,case.p,case.q,case.vrms)
        row=dict(run_id=runid,phase=phase,**asdict(case),**asdict(ctrl),**m)
        row['wave_archive']=arc.add(runid,w,full); row['wave_full']=full
        for hh,amp in enumerate(h,1): row[f'h{hh:02d}_rms_a']=float(amp)
        if full:
            n=640; t=w[n-1:,0]
            p=np.convolve(w[:,1]*w[:,2],np.ones(n)/n,mode='valid')
            q=np.convolve(-np.sqrt(2)*case.vrms*w[:,2]*np.cos(W0*w[:,0]),np.ones(n)/n,mode='valid')
            tol=max(20.,.02*np.hypot(case.p,case.q))
            bad=np.where((t>=.3)&((np.abs(p-case.p)>tol)|(np.abs(q-case.q)>tol)))[0]
            settle=0. if len(bad)==0 else (None if bad[-1]==len(t)-1 else float(t[bad[-1]+1]-.3))
            row['step_settling_s']=settle
            row['step_peak_a']=float(np.max(np.abs(w[w[:,0]>=.3,2])))
        rows.append(row)
        if (k+1)%16==0 or k+1==len(jobs):
            print(f'{phase}: {k+1}/{len(jobs)} in {time.perf_counter()-start:.1f}s',flush=True)
    arc.flush(); frame=pd.DataFrame(rows)
    frame.to_csv(RESULTS/f'{phase}.csv',index=False,float_format='%.12g')
    all_rows.extend(rows); return frame

def summarize(frame):
    return dict(n=len(frame),thd_pass=int(frame.thd_pass.sum()),pass_rate_pct=float(100*frame.thd_pass.mean()),
        combined_pass=int(frame.combined_pass.sum()),combined_pass_rate_pct=float(100*frame.combined_pass.mean()),
        mean_thd_pct=float(frame.thd_pct.mean()),median_thd_pct=float(frame.thd_pct.median()),
        worst_thd_pct=float(frame.thd_pct.max()),worst_case=str(frame.loc[frame.thd_pct.idxmax(),'case_id']),
        max_abs_p_error_w=float(frame.p_error_w.abs().max()),max_abs_q_error_var=float(frame.q_error_var.abs().max()),
        peak_a=float(frame.peak_a.max()),guard_failures=int((~frame.guardrail_pass).sum()),
        max_periodicity_rms_a=float(frame.periodicity_rms_a.max()))

def factor_effects(doe):
    factors=['bw_hz','comp_gain','comp_width_a']
    grouped=doe.groupby(factors,sort=True).thd_pct.mean()
    values=grouped.to_numpy().reshape(3,3,3)
    grand=values.mean(); total=float(np.sum((values-grand)**2)); components={}; records=[]
    for order in [1,2,3]:
        for axes in combinations(range(3),order):
            collapsed=tuple(i for i in range(3) if i not in axes)
            term=(values.mean(axis=collapsed,keepdims=True) if collapsed else values.copy())-grand
            for subset,part in components.items():
                if set(subset)<set(axes): term=term-part
            components[axes]=term
            ss=float(np.sum(np.broadcast_to(term,values.shape)**2))
            records.append(dict(term=' x '.join(factors[a] for a in axes),order=order,sum_squares=ss,share_pct=100*ss/total))
    result=pd.DataFrame(records)
    assert abs(result.sum_squares.sum()-total)<1e-8
    result.to_csv(RESULTS/'factor_effects.csv',index=False,float_format='%.12g')
    return result

def execute():
    RESULTS.mkdir(exist_ok=True); DATA.mkdir(exist_ok=True); events=[]
    def event(stage,detail):
        events.append(dict(sequence=len(events)+1,stage=stage,detail=detail));write_json(RESULTS/'stage_log.json',events)
    event('Define','Frozen protocol, explicit assumed thresholds and generic model boundary.')
    checks=run_verification(RESULTS)
    if not all(x['passed'] for x in checks): raise RuntimeError('Numerical gate failed. Study stopped.')
    event('Measure-V',f'{len(checks)} numerical checks passed; empirical validation not performed.')
    mc=main_cases();train=[x for x in mc if x.vrms==230 and x.p in [350,700,1400] and x.q in [-700,0,700]]
    assert len(train)==9
    pd.DataFrame([asdict(x) for x in mc]).to_csv(RESULTS/'main_cases.csv',index=False,float_format='%.15g')
    pd.DataFrame([asdict(x) for x in train]).to_csv(RESULTS/'training_cases.csv',index=False,float_format='%.15g')
    all_rows=[];baseline=run_phase('baseline',[(c,Control()) for c in mc],all_rows)
    event('Measure-B','72 reference-model baseline cases computed; not a measured product baseline.')
    candidates=[Control(b,a,z) for b,a,z in product(CONFIG['doe_bw_hz'],CONFIG['doe_comp_gain'],CONFIG['doe_comp_width_a'])]
    doe=run_phase('doe',[(c,co) for co in candidates for c in train],all_rows)
    ag=doe.groupby(['bw_hz','comp_gain','comp_width_a'],as_index=False).agg(
        combined_pass=('combined_pass','sum'),worst_thd_pct=('thd_pct','max'),mean_thd_pct=('thd_pct','mean'))
    ag=ag.sort_values(['combined_pass','worst_thd_pct','mean_thd_pct','bw_hz'],ascending=[False,True,True,True],kind='stable')
    ag.to_csv(RESULTS/'doe_candidates.csv',index=False,float_format='%.12g')
    best=ag.iloc[0]; selected=Control(float(best.bw_hz),float(best.comp_gain),float(best.comp_width_a))
    selection=dict(control=asdict(selected),training_case_ids=[x.case_id for x in train],
        selection_rule='max combined pass, min worst THD, min mean THD, min BW',selected_from=27,
        selected_control_frozen_before_holdout=True,model_sha256=sha(ROOT/'src/model.py'),config_sha256=sha(ROOT/'study_config.json'))
    write_json(RESULTS/'selected_control.json',selection);selected_sha=sha(RESULTS/'selected_control.json')
    factor_effects(doe)
    event('Analyze/Freeze',f'27x9 DOE done. Control frozen: {asdict(selected)}. Hash {selected_sha}')
    improved=run_phase('improved',[(c,selected) for c in mc],all_rows)
    event('Improve','Identical 72-point matrix evaluated using frozen control.')
    hc=holdout_cases()
    pd.DataFrame([asdict(x) for x in hc]).to_csv(RESULTS/'holdout_cases.csv',index=False,float_format='%.15g')
    hb=run_phase('holdout_baseline',[(c,Control()) for c in hc],all_rows)
    hi=run_phase('holdout_improved',[(c,selected) for c in hc],all_rows)
    assert sha(RESULTS/'selected_control.json')==selected_sha,'Control changed after holdout!'
    event('Verify-Holdout','64 coverage scenarios + 8 corners without retuning; both assumed plant shapes retained.')
    aj=[]
    for c in [Case('A_low',p=350,q=0),Case('A_Q',p=350,q=700)]:
        aj.extend([(replace(c,case_id=c.case_id+'_no_dead',dead_us=0),Control()),
            (replace(c,case_id=c.case_id+'_base'),Control()),
            (replace(c,case_id=c.case_id+'_bw_only'),replace(selected,comp_gain=0)),
            (replace(c,case_id=c.case_id+'_comp_only'),replace(selected,bw_hz=300)),
            (replace(c,case_id=c.case_id+'_combined'),selected)])
    run_phase('ablation',aj,all_rows)
    pj=[]
    for s,angle in product([350,700,1400],[-90,-75,-45,0,45,75,90]):
        a=np.deg2rad(angle);c=Case(f'S{s}_angle{angle}',p=float(s*np.cos(a)),q=float(s*np.sin(a)))
        pj.extend([(c,Control()),(c,selected)])
    run_phase('constant_S_phase',pj,all_rows)
    tj=[]
    for k,(p,q) in enumerate([(350,0),(700,700),(1400,-1400),(0,1400)]):
        c=Case(f'T{k+1}',p=p,q=q);tj.extend([(c,Control()),(c,selected)])
    run_phase('transient',tj,all_rows,full=True)
    refine=[];refarc=Archive('final_refinement')
    for name,fr in [('baseline',baseline),('improved',improved),('holdout',hi)]:
        ids={fr.thd_pct.idxmax(),(fr.thd_pct-5).abs().idxmin()}
        for idx in sorted(ids):
            r=fr.loc[idx]
            c=Case(**{k:r[k] for k in Case.__dataclass_fields__})
            co=Control(**{k:r[k] for k in Control.__dataclass_fields__})
            w=simulate(c,co,substeps=32);m,_=harmonic_metrics(w,c.p,c.q,c.vrms)
            rid='refine_'+str(len(refine)+1);path=refarc.add(rid,w)
            refine.append(dict(run_id=rid,source_run_id=r.run_id,source_phase=name,case_id=c.case_id,
                thd_16=r.thd_pct,thd_32=m['thd_pct'],difference_pp=abs(r.thd_pct-m['thd_pct']),
                same_thd_decision=bool(r.thd_pass==m['thd_pass']),wave_archive=path))
    refarc.flush();pd.DataFrame(refine).to_csv(RESULTS/'final_refinement.csv',index=False,float_format='%.12g')
    event('Verify-Final','Ablation, constant-S phase sweep, command steps, 32-substep spot checks done.')
    frame=pd.DataFrame(all_rows);frame.to_csv(RESULTS/'all_runs.csv',index=False,float_format='%.15g')
    trainids={x.case_id for x in train}
    summary=dict(study_id=CONFIG['study_id'],evidence_level=CONFIG['evidence_level'],
        baseline=summarize(baseline),improved=summarize(improved),
        unseen_main_baseline=summarize(baseline[~baseline.case_id.isin(trainids)]),
        unseen_main_improved=summarize(improved[~improved.case_id.isin(trainids)]),
        holdout_baseline=summarize(hb),holdout_improved=summarize(hi),control=asdict(selected),
        numerical_tests=len(checks),all_numerical_tests_passed=True,total_performance_runs=len(frame),target_main_pct=95.,
        nominal_target_met=bool(100*improved.thd_pass.mean()>=95.),
        holdout_worse_case_count=int((hi.thd_pct.to_numpy()>hb.thd_pct.to_numpy()).sum()),
        holdout_borderline_count=int((np.abs(hi.thd_pct-5)<=.02).sum()),
        final_refinement_max_difference_pp=max(r['difference_pp'] for r in refine),
        final_refinement_decisions_unchanged=all(r['same_thd_decision'] for r in refine),
        financial_benefit_status='not quantified: no real cost/labor evidence',
        empirical_validation_status='not performed',BB_acceptance_status='not confirmed')
    write_json(RESULTS/'summary.json',summary)
    hi[~hi.combined_pass].to_csv(RESULTS/'holdout_failures.csv',index=False,float_format='%.12g')
    import scipy,numba,matplotlib
    write_json(RESULTS/'environment.json',dict(python=sys.version,platform=platform.platform(),numpy=np.__version__,
        scipy=scipy.__version__,numba=numba.__version__,pandas=pd.__version__,matplotlib=matplotlib.__version__,
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'src').glob('*.py'))}))
    write_json(DATA/'schema.json',dict(format='NPZ lossless float64; channels x samples',
        steady_channels=['current_a','reference_a','applied_command_v','generated_command_v','saturation','pll_phase_error_rad'],
        full_channels=['time_s','grid_v','current_a','reference_a','applied_command_v','generated_command_v','saturation','pll_phase_error_rad','dead_voltage_v'],
        sample_rate_hz=FS,steady_start_s=(CONFIG['cycles']-10)/F0,steady_samples=6400,
        metadata='results/all_runs.csv maps run_id to archive and every plant/control input',
        reconstructed_grid='sqrt(2)*vrms*(sin(2*pi*50*t)+v3*sin(3*2*pi*50*t)+v5*sin(5*2*pi*50*t))',
        numeric_origin='Direct RK4 plant integration with sampled-data control; not fabricated responses.'))
    event('Control/Review','Complete within numerical scope; product validation and BB approval still open.')
    from .report import build_report
    build_report(ROOT)
    paths=sorted([p for folder in ['results','data','report'] for p in (ROOT/folder).rglob('*') if p.is_file() and p.name!='manifest.json'])
    write_json(RESULTS/'manifest.json',dict(algorithm='SHA-256',files=[dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p)) for p in paths]))
    print(json.dumps(summary,indent=2,ensure_ascii=False),flush=True)
if __name__=='__main__': execute()
