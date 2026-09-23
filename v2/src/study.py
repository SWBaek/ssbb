"""Sequential, reproducible numerical BB study. Run: python -m src.study."""
from pathlib import Path
from dataclasses import asdict,replace
from itertools import product
import json,hashlib,datetime,sys,platform
import numpy as np
import pandas as pd
from .model import *
ROOT=Path(__file__).resolve().parents[1]
CFG=json.loads((ROOT/'study_config.json').read_text())
RESULT=ROOT/'results'; DATA=ROOT/'data'; REPORT=ROOT/'report'
for pth in [RESULT,DATA,REPORT]: pth.mkdir(exist_ok=True)
ALL=[]; LOG=[]
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def jwrite(name,x): (RESULT/name).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
def stage(name,detail):
 LOG.append(dict(stage=name,detail=detail,utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
 jwrite('stage_log.json',LOG); print(name,detail,flush=True)
def cases(ss,angles,volts,prefix):
 out=[]
 for k,(s,a,v) in enumerate(product(ss,angles,volts)):
  out.append(Case(f'{prefix}{k:03}',p=s*math.cos(math.radians(a)),q=s*math.sin(math.radians(a)),vrms=v))
 return out

def batch(name,jobs,keep_full=False):
 records=[]; waves=[]; harms=[]; cp=[]; controls=[]
 for k,(case,ctl,opts) in enumerate(jobs):
  opts={**dict(cycles=CFG['cycles'],substeps=CFG['integration_substeps']),**opts}
  w=simulate(case,ctl,**opts); m,h=metrics(w,case,CFG['thd_limit_pct'])
  # Every result has its complete raw measured window, without rescaling.
  v=w if keep_full else w[-6400:]
  waves.append(v); harms.append(h); cp.append(asdict(case)); controls.append(asdict(ctl))
  row=dict(run_id=f'{name}_{k:04}',group=name,**m,**{f'ctl_{a}':b for a,b in asdict(ctl).items()},
           wave_file=f'data/{name}.npz',wave_index=k,solver_substeps=opts['substeps'],solver_cycles=opts['cycles'])
  records.append(row)
 frame=pd.DataFrame(records); frame.to_csv(RESULT/f'{name}.csv',index=False)
 # Single fixed shape per batch, deterministic input and exact float64 waveforms.
 np.savez_compressed(DATA/f'{name}.npz',wave=np.array(waves),harmonics=np.array(harms),
   cases_json=json.dumps(cp),controls_json=json.dumps(controls),run_ids=np.array(frame.run_id.tolist()),
   columns=np.array(['t','vg','i','iref','applied_command','generated_command','saturated','pll_error_rad','commutation_loss_v','harmonic_feedback_v']))
 ALL.extend(records)
 return frame

def summary(df):
 return dict(n=len(df),mean_thd=float(df.thd_pct.mean()),min_thd=float(df.thd_pct.min()),max_thd=float(df.thd_pct.max()),
  thd_pass=int(df.thd_pass.sum()),combined_pass=int(df.combined_pass.sum()),guard_fail=int((~df.guard_pass).sum()),
  thd_pass_pct=float(100*df.thd_pass.mean()),combined_pass_pct=float(100*df.combined_pass.mean()))

def verify():
 checks=[]
 def add(label,passed,value): checks.append(dict(check=label,passed=bool(passed),value=float(value)))
 # Metrics against a constructed analytic unit-test signal, not performance data.
 t=np.arange(25600)/FS; w=np.zeros((len(t),10));w[:,0]=t;w[:,1]=230*math.sqrt(2)*np.sin(W0*t)
 w[:,2]=math.sqrt(2)*(3*np.sin(W0*t)+.09*np.sin(3*W0*t)+.12*np.sin(5*W0*t))+.02
 c=Case('analytic',p=690)
 m,_=metrics(w,c); add('Known 3-4-5 harmonic THD is5%',abs(m['thd_pct']-5)<1e-10,m['thd_pct'])
 add('DC excluded and recovered',abs(m['dc_a']-.02)<1e-12,m['dc_a'])
 c=Case('ideal',p=700,dead_us=0); m,_=metrics(simulate(c),c)
 add('Ideal grid/current case THD<0.05%',m['thd_pct']<.05,m['thd_pct'])
 conv=[]
 for ctl in [Control(),Control(800,5,5)]:
  vals=[]
  for ns in [2,4,8,16]:
   c=Case('convergence',p=525,vrms=253)
   w=simulate(c,ctl,substeps=ns); m,_=metrics(w,c); vals.append(m['thd_pct'])
   conv.append(dict(**asdict(ctl),substeps=ns,thd=m['thd_pct']))
  add(f"RK4 4->16 substeps THD error {ctl.k3}",abs(vals[1]-vals[3])<.01,abs(vals[1]-vals[3]))
 # Independent projection of the same sampled signal checks FFT implementation.
 c=Case('projection',p=700,q=350); w=simulate(c); m,h=metrics(w,c); z=w[-6400:];tt=z[:,0];ii=z[:,2]
 hh=[]
 for k in range(1,41):
  hh.append(math.sqrt(2)*math.hypot(float(np.mean(ii*np.sin(k*W0*tt))),float(np.mean(ii*np.cos(k*W0*tt)))))
 add('FFT vs direct harmonic projection',np.max(np.abs(h-hh))<1e-10,np.max(np.abs(h-hh)))
 pd.DataFrame(conv).to_csv(RESULT/'convergence.csv',index=False)
 jwrite('verification.json',checks)
 if not all(x['passed'] for x in checks): raise AssertionError('Numerical verification failed')
 return checks

def main():
 ALL.clear(); LOG.clear(); (RESULT/'test_report.json').unlink(missing_ok=True)
 stage('D','Freeze research-only boundaries, baseline and test matrices')
 frozen=dict(config=CFG,baseline=asdict(Control(**CFG['baseline'])),nominal_plant=asdict(Case('nominal')),
   source_sha256={p:sha(ROOT/p) for p in ['src/model.py','src/study.py','src/audit.py','study_config.json','docs/00_protocol.md','evidence/public_references.json']})
 jwrite('protocol_freeze.json',frozen)
 stage('M0','Numerical and metric implementation checks')
 checks=verify(); baseline=Control(**CFG['baseline'])
 main_cases=cases(CFG['main_s_va'],CFG['main_angles_deg'],CFG['main_vrms'],'M')
 train=cases(CFG['training_s_va'],CFG['training_angles_deg'],[230.],'T')
 sentinel=cases([1400,2800,5600,7000],[-45,0,45],[207,230,253],'S')
 for name,cc in [('main_cases',main_cases),('training_cases',train),('sentinel_cases',sentinel)]:
  pd.DataFrame([asdict(c) for c in cc]).to_csv(RESULT/f'{name}.csv',index=False)
 stage('M1','Measure frozen baseline, no artificial THD calibration or waveform scaling')
 b=batch('baseline',[(c,baseline,{}) for c in main_cases]); sb=batch('sentinel_baseline',[(c,baseline,{}) for c in sentinel])
 stage('A/I','27x9 full factorial computer experiment; deterministic effect sizes, no fabricated p-values')
 cand=[Control(float(f),float(k3),float(k5)) for f,k3,k5 in product(CFG['doe_design_hz'],CFG['doe_k3_ohm'],CFG['doe_k5_ohm'])]
 jobs=[(c,ctl,{}) for ctl in cand for c in train]
 d=batch('doe',jobs)
 aggregate=d.groupby(['ctl_design_hz','ctl_k3','ctl_k5'],as_index=False).agg(mean_thd=('thd_pct','mean'),max_thd=('thd_pct','max'),guard_pass=('guard_pass','sum'))
 aggregate['guard_fail']=len(train)-aggregate.guard_pass;aggregate['gain_sum']=aggregate.ctl_k3+aggregate.ctl_k5
 aggregate=aggregate.sort_values(['guard_fail','max_thd','mean_thd','gain_sum']).reset_index(drop=True)
 aggregate.to_csv(RESULT/'doe_candidates.csv',index=False)
 win=aggregate.iloc[0]; selected=Control(float(win.ctl_design_hz),float(win.ctl_k3),float(win.ctl_k5))
 jwrite('selected_control.json',dict(control=asdict(selected),selection='training guard failures, worst THD, mean THD, gain sum',candidate_grid_only=True,training_run_ids=d.run_id.tolist()))
 stage('I freeze',str(asdict(selected)))
 a=batch('improved',[(c,selected,{}) for c in main_cases]); sa=batch('sentinel_improved',[(c,selected,{}) for c in sentinel])
 stage('V1','Out-of-range sensitivity and alternate error-shape scenarios; not a production distribution')
 rng=np.random.default_rng(CFG['holdout_seed']); hold=[]
 for k in range(CFG['holdout_n']):
  s=rng.uniform(450,1200); angle=rng.uniform(-80,80);L=rng.uniform(.8,1.2)*LN
  hold.append(Case(f'H{k:03}',p=s*math.cos(math.radians(angle)),q=s*math.sin(math.radians(angle)),vrms=rng.uniform(207,253),vdc=rng.uniform(390,410),lf=L,
    lg=rng.uniform(.05e-3,.8e-3),rf=rng.uniform(.12,.18),rg=rng.uniform(.05,.3),dead_us=rng.uniform(.12,.28),zero_a=rng.uniform(.15,.4),
    v3=rng.uniform(-.01,.01),v5=rng.uniform(-.005,.005),offset_a=rng.uniform(-.02,.02),adc_step=.005,shape=k%2,bus_ripple=rng.uniform(0,.015)))
 pd.DataFrame([asdict(c) for c in hold]).to_csv(RESULT/'holdout_cases.csv',index=False)
 hb=batch('holdout_baseline',[(c,baseline,{}) for c in hold]);ha=batch('holdout_improved',[(c,selected,{}) for c in hold])
 ha[~ha.combined_pass].to_csv(RESULT/'holdout_failures.csv',index=False)
 stage('V2','Control ablations, fixed-S phase, reverse power, transients, refinement')
 acases=cases([525,700,875],[-60,0,60],[230.],'A')
 abctrl=[baseline,Control(selected.design_hz,0,0),Control(500,selected.k3,0),Control(500,0,selected.k5),Control(500,selected.k3,selected.k5),selected]
 ab=batch('ablation',[(c,ctl,{}) for ctl in abctrl for c in acases])
 ph=cases([700,1400],[-90,-60,-30,0,30,60,90],[230.],'P')
 phase=batch('phase',[(c,ctl,{}) for ctl in [baseline,selected] for c in ph])
 rev=[Case('R'+str(k),p=-p,q=0) for k,p in enumerate([525,700,1400,5600])]
 reverse=batch('reverse_power',[(c,ctl,{}) for ctl in [baseline,selected] for c in rev])
 tcase=[Case('X0',p=700),Case('X1',p=700,q=700),Case('X2',p=2800,q=-1400)]
 trans=batch('transient',[(c,ctl,{'step':True}) for ctl in [baseline,selected] for c in tcase],keep_full=True)
 ref=batch('refinement',[(c,selected,{'substeps':16}) for c in [main_cases[2],main_cases[-1],hold[0],hold[-1]]])
 # Longer settling check separated from tuning.
 duration=batch('duration',[(c,selected,{'cycles':80}) for c in [main_cases[2],hold[0]]])
 # One-factor plant sensitivities at a single baseline, not statistical sample variation.
 nominal=Case('N',p=700); sens=[]
 for fac,levels in [('dead_us',[.12,.2,.28]),('lg',[.05e-3,.2e-3,.8e-3]),('zero_a',[.15,.25,.4]),('v3',[-.01,0,.01])]:
  for lev in levels:
   c=replace(nominal,case_id=f'{fac}:{lev}',**{fac:lev});sens.append((c,baseline,{}))
 sensitivity=batch('plant_sensitivity',sens)
 allf=pd.DataFrame(ALL);allf.to_csv(RESULT/'all_runs.csv',index=False)
 # Per-case before/after joins, guard failures not filtered out.
 pair=b.merge(a,on='case_id',suffixes=('_before','_after'));pair['delta_pp']=pair.thd_pct_before-pair.thd_pct_after
 pair.to_csv(RESULT/'paired_main.csv',index=False)
 for label,df in [('baseline',b),('improved',a),('sentinel_baseline',sb),('sentinel_improved',sa)]:
  df.assign(s_round=df.s_va.round()).groupby('s_round').agg(n=('thd_pct','size'),mean_thd=('thd_pct','mean'),min_thd=('thd_pct','min'),max_thd=('thd_pct','max'),passes=('combined_pass','sum')).to_csv(RESULT/f'{label}_by_load.csv')
 env=dict(python=sys.version,platform=platform.platform(),numpy=np.__version__,timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
 jwrite('environment.json',env)
 out=dict(study_id=CFG['study_id'],evidence_level=CFG['evidence_level'],selected=asdict(selected),baseline=summary(b),improved=summary(a),sentinel_baseline=summary(sb),sentinel_improved=summary(sa),holdout_baseline=summary(hb),holdout_improved=summary(ha),
   main_mean_reduction_pp=float(pair.delta_pp.mean()),main_worsened=int((pair.delta_pp< -1e-6).sum()),total_performance_runs=len(ALL),numerical_checks=len(checks),
   target_main_pct=CFG['main_target_pass_pct'],target_met=bool(a.thd_pass.mean()*100>=CFG['main_target_pass_pct']),main_guard_all_pass=bool(a.guard_pass.all()),
   explicit_limitations=['Not calibrated against this product','No switching or LF-leg commutation model','Q-specific actual mechanism not established','Research THD 2:40 threshold, not certification','Ideal DC source excludes full OBC interactions','Synthetic stress distribution is not a defect probability'])
 jwrite('summary.json',out)
 stage('C','Persist code, raw numerical windows, assumptions and limitations')
 from .report import build
 build(ROOT)
 manifest={str(p.relative_to(ROOT)):dict(bytes=p.stat().st_size,sha256=sha(p)) for f in ['data','results','report','docs','evidence','src','tests'] for p in (ROOT/f).rglob('*') if p.is_file() and '__pycache__' not in str(p) and p.name!='manifest.json'}
 jwrite('manifest.json',manifest)
 print(json.dumps(out,ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__': main()
