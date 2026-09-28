"""Fresh V6 finite numerical experiment. All condition plans frozen before results.
The selection function reads only DOE outputs; verification does not retune it.
"""
import os,sys,json,time,hashlib,itertools,platform
from dataclasses import asdict,replace
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import qmc
from model import *

RES=ROOT/'results';WAV=ROOT/'waveforms';QA=ROOT/'qa'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def clean(o):
    if isinstance(o,dict):return {k:clean(v) for k,v in o.items()}
    if isinstance(o,(list,tuple)):return [clean(v) for v in o]
    if isinstance(o,np.generic):return o.item()
    return o

def savejson(p,o):Path(p).write_text(json.dumps(clean(o),ensure_ascii=False,indent=2)+'\n')
def csv(p,x):pd.DataFrame(x).to_csv(p,index=False,float_format='%.12g')


def plans():
    levels=[0,4,8,16,32,48];qs=sorted(set(levels+[-x for x in levels]));main=[]
    train={(4,0),(4,4),(4,-4),(8,0),(8,8),(8,-8),(16,0),(16,16),(16,-16)}
    for d,q in itertools.product(levels,qs):
        if 0<math.hypot(d,q)<=48+1e-10:main.append(Case(f'N{len(main)+1:03d}',d*SQ2,q*SQ2))
    train_ids=[c.case_id for c in main if (round(c.id_peak_a/SQ2),round(c.iq_peak_a/SQ2)) in train]
    pairs=[(4,0),(0,4),(0,-4),(8,8),(8,-8),(16,16),(16,-16),(32,0),(0,32),(48,0),(0,48),(0,-48)]
    volt=[Case(f'V{k+1:03d}',d*SQ2,q*SQ2,vac_v=v) for k,(v,(d,q)) in enumerate(itertools.product([207.,253.],pairs))]
    # Ranges are design assumptions, not identified manufacturing distributions.
    u=qmc.LatinHypercube(d=11,seed=20260928).random(24);var=[]
    for k,x in enumerate(u):
        d,q=pairs[k%len(pairs)]
        var.append(Case(f'R{k+1:03d}',d*SQ2,q*SQ2,vac_v=230.,vdc_v=380+40*x[0],fgrid_hz=59.5+x[1],lf_h=.0009+.0002*x[2],lg_h=.00005+.0002*x[3],rf_ohm=.064+.032*x[4],rg_ohm=.05+.15*x[5],dead_s=(100+200*x[6])*1e-9,sensor_hz=8000+4000*x[7],sensor_offset_a=-.05+.1*x[8],sensor_gain=.995+.01*x[9],grid_h3=.015*x[10],grid_h5=.0075*x[0],extra_delay_pwm=k%2))
    return main,train_ids,volt,var

ALL=[]
def execute(group,c,ctl,tag,**kw):
    rid=f'{group}_{c.case_id}_{tag}';fp=WAV/(rid+'.npz')
    if fp.exists():raise RuntimeError('Existing V6 waveform: use a new clean output tree to rerun')
    w=simulate(c,ctl,**kw);m,h=measure(w,c,kw.get('step',(None,None,None))[1:] if kw.get('step') else None)
    row=dict(run_id=rid,group=group,control_tag=tag,**asdict(c),**asdict(ctl),**m,**{f'h{k+1}_rms_a':float(v) for k,v in enumerate(h)},pwm_count=w['pwm_count'],control_count=w['control_count'],load_count=w['load_count'],lf_transition_count=w['lf_transition_count'])
    metadata=dict(case=asdict(c),control=asdict(ctl),options=kw,metrics=clean(m),spec_sha256=sha(ROOT/'specification.json'),model_sha256=sha(ROOT/'src/model.py'),run_id=rid)
    # Keep full controller timeline only for transient tests. Steady-state raw records
    # contain all uniform current samples in the complete measurement interval.
    n=len(w['control']);nk=len(w['pwm']);start=0 if group=='transient' else n-nk
    np.savez_compressed(fp,current_a=w['current_a'],control=w['control'][start:],control_start_index=start,pwm=w['pwm'],dt_s=w['dt_s'],t0_s=w['t0_s'],end_s=w['end_s'],pwm_count=w['pwm_count'],control_count=w['control_count'],load_count=w['load_count'],lf_transition_count=w['lf_transition_count'],metadata=json.dumps(clean(metadata),ensure_ascii=False))
    row['wave_sha256']=sha(fp);row['wave_bytes']=fp.stat().st_size;ALL.append(row)
    if len(ALL)%25==0:print('runs',len(ALL),rid,flush=True)
    return row


def main():
    assert_spec();main,train_ids,volt,var=plans()
    for name,xx in [('main',main),('voltage',volt),('variation',var)]:
        for c in xx:validate(c)
        csv(RES/f'{name}_conditions.csv',[dict(**asdict(c),selection_used=c.case_id in train_ids) for c in xx])
    assert len(main)==47 and len(train_ids)==9 and len(volt)==len(var)==24
    candidates=[Control(kr_ohm=g,band_hz=b,max_harmonic=h) for g,b,h in itertools.product([6.,12.,18.],[4.,8.,16.],[3,5,7])]
    csv(RES/'candidate_plan.csv',[dict(candidate=f'C{k+1:02d}',**asdict(c)) for k,c in enumerate(candidates)])
    frozen={'spec_sha256':sha(ROOT/'specification.json'),'model_sha256':sha(ROOT/'src/model.py'),'study_sha256':sha(__file__),'plans':{p.name:sha(p) for p in RES.glob('*conditions.csv')},'candidate_plan_sha256':sha(RES/'candidate_plan.csv'),'selection_ids':train_ids,'selection_rule':'lexicographic: maximum combined_pass count, minimum max THD, minimum mean THD, minimum Kr, band, harmonic_max','previous_results_loaded':False}
    savejson(QA/'frozen_protocol.json',frozen)
    baseline=[execute('baseline',c,Control(),'initial') for c in main];csv(RES/'baseline.csv',baseline)
    train=[c for c in main if c.case_id in train_ids];doe=[];cand=[]
    for k,ct in enumerate(candidates):
        cid=f'C{k+1:02d}';rows=[execute('doe',c,ct,cid) for c in train];doe+=rows
        cand.append(dict(candidate=cid,**asdict(ct),n=len(rows),combined=sum(r['combined_pass'] for r in rows),thd_pass=sum(r['thd_pass'] for r in rows),thd_max=max(r['thd_pct'] for r in rows),thd_mean=float(np.mean([r['thd_pct'] for r in rows]))))
    csv(RES/'doe.csv',doe);csv(RES/'candidates.csv',cand)
    ranked=sorted(cand,key=lambda x:(-x['combined'],x['thd_max'],x['thd_mean'],x['kr_ohm'],x['band_hz'],x['max_harmonic']))
    best=ranked[0];selected=Control(**{k:best[k] for k in asdict(Control())});savejson(RES/'selected_control.json',dict(**best,control=asdict(selected),scope='best evaluated candidate, not a global optimum',selected_from_ids=train_ids))
    selection_sha=sha(RES/'selected_control.json');print('SELECTED',best,flush=True)
    imp=[execute('improved',c,selected,'selected') for c in main];csv(RES/'improved.csv',imp)
    for name,cases in [('voltage',volt),('variation',var)]:
        rows=[]
        for c in cases:
            rows+=[execute(name,c,Control(),'initial'),execute(name,c,selected,'selected')]
        csv(RES/(name+'.csv'),rows)
    # Structural challenge: explicitly change LF commutation assumption, never pool as nominal.
    structural=[]
    for d,q in [(4,0),(8,8),(8,-8),(0,32),(32,0),(0,-48)]:
        c=Case(f'L{len(structural)//2+1:02d}',d*SQ2,q*SQ2,lf_grid_polarity=True)
        structural += [execute('structure',c,Control(),'initial'),execute('structure',c,selected,'selected')]
    csv(RES/'structure.csv',structural)
    # Mechanism check, not proof of actual product root cause.
    abl=[]
    for d,q in [(4,0),(8,8),(0,48)]:
        cc=Case(f'A{len(abl)//3+1:02d}',d*SQ2,q*SQ2)
        for label,c in [('nominal',cc),('no_deadtime',replace(cc,dead_s=0)),('ideal_sensor',replace(cc,sensor_hz=200000.,adc_bits=0))]:abl.append(execute('ablation',c,Control(),label))
    csv(RES/'ablation.csv',abl)
    # Grid frequency and FIFO validation; sampling interval stays 16 us.
    fun=[]
    for k,(d,q,f,delay) in enumerate([(48,0,60,0),(0,48,60,0),(0,-48,60,0),(-16,0,60,0),(8,8,59,0),(8,-8,61,0),(8,0,60,1),(8,0,60,2)]):
        cc=Case(f'F{k+1:02d}',d*SQ2,q*SQ2,fgrid_hz=f,extra_delay_pwm=delay)
        fun.append(execute('functional',cc,selected,'selected'))
    csv(RES/'functional.csv',fun)
    # d-only, q-only, reversal and approach to full-current boundary.
    trans=[]
    for k,(d,q,dd,qq) in enumerate([(8,0,16,0),(16,0,16,16),(16,16,16,-16),(40,0,48,0)]):
        cc=Case(f'T{k+1:02d}',d*SQ2,q*SQ2)
        for label,ct in [('initial',Control()),('selected',selected)]:trans.append(execute('transient',cc,ct,label,step=(.4,dd*SQ2,qq*SQ2)))
    csv(RES/'transient.csv',trans)
    ref=[];long=[]
    for k,(d,q) in enumerate([(4,0),(8,8),(0,48),(48,0)]):
        cc=Case(f'Q{k+1:02d}',d*SQ2,q*SQ2)
        for label,ct in [('initial',Control()),('selected',selected)]:
            for dt in [2e-6,1e-6,.5e-6]:ref.append(execute('refinement',cc,ct,label+f'_{dt:.1e}',dt_s=dt))
            long.append(execute('long_duration',cc,ct,label,duration_s=1.5))
    csv(RES/'refinement.csv',ref);csv(RES/'long_duration.csv',long)
    assert sha(RES/'selected_control.json')==selection_sha
    csv(RES/'all_runs.csv',ALL);savejson(QA/'execution.json',{'runs':len(ALL),'pwm_control_equal_every_run':all(x['pwm_count']==x['control_count'] for x in ALL),'selection_unchanged':True,'spec_unchanged':sha(ROOT/'specification.json')==frozen['spec_sha256'],'plans_unchanged':all(sha(RES/k)==v for k,v in frozen['plans'].items()),'python':sys.version,'platform':platform.platform(),'run_time_finish_utc':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()})
    print('FINISHED',len(ALL),flush=True)

if __name__=='__main__':main()
