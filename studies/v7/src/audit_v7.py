"""Cross-file V7 audit. Checks evidence integrity, not hardware validity."""
from pathlib import Path
import hashlib,json,math,sys
import numpy as np
import pandas as pd
from model import ROOT,SPEC,assert_spec
from study import sha,savejson

def main():
    assert_spec();r=ROOT/'results';q=ROOT/'qa';f=json.loads((q/'frozen_protocol.json').read_text())
    assert sha(ROOT/'specification.json')==f['spec_sha256']
    assert sha(ROOT/'src/model.py')==f['model_sha256']
    assert sha(ROOT/'src/study.py')==f['study_sha256']
    assert all(sha(r/k)==v for k,v in f['plans'].items())
    assert sha(r/'candidate_plan.csv')==f['candidate_plan_sha256']
    a=pd.read_csv(r/'all_runs.csv');n=pd.read_csv(r/'main_conditions.csv');d=pd.read_csv(r/'candidates.csv');s=json.loads((r/'selected_control.json').read_text())
    assert len(a)==502 and len(set(a.run_id))==502 and len(n)==47
    assert n.vac_v.eq(240).all() and n.selection_used.sum()==9
    nominal_groups=['baseline','doe','improved','variation','structure','ablation','functional','transient','refinement','long_duration']
    assert a[a.group.isin(nominal_groups)].vac_v.eq(240).all()
    assert set(a[a.group=='voltage'].vac_v)=={216.,264.}
    assert a[a.group=='doe'].case_id.nunique()==9 and len(a[a.group=='doe'])==243
    best=d.sort_values(['combined','thd_max','thd_mean','kr_ohm','band_hz','max_harmonic'],ascending=[False,True,True,True,True,True]).iloc[0]
    assert best.candidate==s['candidate']
    assert set(s['selected_from_ids'])==set(n.loc[n.selection_used,'case_id'])
    peak=math.sqrt(2)*48;assert np.max(np.hypot(a.id_peak_a,a.iq_peak_a))<=peak+1e-8
    max_u=0.;hashok=True
    for row in a.itertuples():
        p=ROOT/'waveforms'/(row.run_id+'.npz');assert sha(p)==row.wave_sha256
        z=np.load(p);m=json.loads(str(z['metadata']))
        assert m['spec_sha256']==f['spec_sha256'] and m['model_sha256']==f['model_sha256']
        assert m['case']['vac_v']==row.vac_v and m['run_id']==row.run_id
        assert int(z['pwm_count'])==int(z['control_count'])
        tr=z['control'];pw=z['pwm'];start=int(z['control_start_index'])
        source=pw[:,4].astype(int);valid=(source>=start)&(source<start+len(tr))
        err=np.max(np.abs(pw[valid,0].astype(float)-tr[source[valid]-start,5].astype(float)))
        max_u=max(max_u,float(err));assert err<=1e-6
    b=pd.read_csv(r/'improved.csv');initial=pd.read_csv(r/'baseline.csv')
    raw=json.loads((q/'raw_audit.json').read_text());assert raw['runs']==502 and raw['all_flags_equal']
    goals={'scope':'engineering targets only; no external certification status','thd_limit_pct':5.,'nominal_case_n':47,'required_pass_rate_pct':95.,'minimum_pass_n':45,'actual_thd_pass_n':int(b.thd_pass.sum()),'thd_goal_met':bool(b.thd_pass.sum()>=45),'auxiliary_all_conditions_met':bool(b.combined_pass.all()),'combined_pass_n':int(b.combined_pass.sum()),'combined_fail_ids':b.loc[~b.combined_pass,'case_id'].tolist(),'new_nominal_combined_fail_ids':pd.read_csv(r/'main_paired.csv').query('new_failure')['case_id'].tolist(),'mean_thd_decrease_pp':float(initial.thd_pct.mean()-b.thd_pct.mean())}
    savejson(r/'engineering_goals.json',goals)
    savejson(q/'v7_consistency.json',{'status':'PASS','runs':len(a),'nominal_voltage_v':240.,'nominal_capacity_va':11520.,'peak_command_bound_a':peak,'pwm_and_control_hz':62500.,'all_source_hashes_verified':True,'all_raw_wave_hashes_verified':True,'pwm_applied_vs_source_command_max_difference_v':max_u,'selection_recomputed_from_doe_only':True,'all_condition_sets_preserved':True,'old_performance_data_imported':False,'note':'Pass denotes numerical record integrity, not all engineering constraints or hardware qualification.'})
    print(json.dumps(goals,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
