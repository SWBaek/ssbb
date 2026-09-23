"""Independent raw-data audit and post-selection diagnostics (not selection criteria)."""
from pathlib import Path
import json, hashlib
import numpy as np
import pandas as pd
from .model import Case, metrics, FS

def audit(root: Path):
    root=Path(root); r=root/'results'; allf=pd.read_csv(r/'all_runs.csv')
    maximum=0.; max_h=0.; count=0; checks=[]
    for fn,rows in allf.groupby('wave_file'):
        with np.load(root/fn,allow_pickle=False) as z:
            cases=json.loads(str(z['cases_json'])); ids=z['run_ids']; waves=z['wave']; hh=z['harmonics']
            assert len(ids)==len(rows)==len(cases)
            for row in rows.itertuples():
                j=row.wave_index; assert ids[j]==row.run_id
                m,h=metrics(waves[j],Case(**cases[j]))
                maximum=max(maximum,abs(m['thd_pct']-row.thd_pct)); max_h=max(max_h,float(np.max(abs(h-hh[j]))))
                for k in ['thd_pass','guard_pass','combined_pass']: assert m[k]==getattr(row,k)
                count+=1
    checks.append(dict(check='Every performance record has raw data and repeatable THD/guard',passed=count==len(allf) and maximum<1e-10 and max_h<1e-10,n=count,max_thd_error_pp=maximum,max_harmonic_error_a=max_h))
    # Compare new numerical integrations with previously frozen final runs.
    nom=pd.concat([pd.read_csv(r/'improved.csv'),pd.read_csv(r/'holdout_improved.csv')]).set_index('case_id')
    numerical=[]
    for name in ['refinement','duration']:
        for row in pd.read_csv(r/f'{name}.csv').itertuples():
            ref=nom.loc[row.case_id]
            numerical.append(dict(test=name,case_id=row.case_id,thd_reference=ref.thd_pct,thd_test=row.thd_pct,absolute_delta_pp=abs(ref.thd_pct-row.thd_pct)))
    pd.DataFrame(numerical).to_csv(r/'final_numerical_crosschecks.csv',index=False)
    checks.append(dict(check='Final RK4/duration THD crosschecks <0.01pp',passed=bool(max(x['absolute_delta_pp'] for x in numerical)<.01),max_delta_pp=max(x['absolute_delta_pp'] for x in numerical)))
    # Post-selection dynamic diagnostic: a cycle-RMS deviation from final periodic waveform.
    # No product transient acceptance criterion has been supplied.
    trans=[]
    with np.load(root/'data/transient.npz',allow_pickle=False) as z:
        frame=pd.read_csv(r/'transient.csv')
        for row in frame.itertuples():
            w=z['wave'][row.wave_index]; t=w[:,0]; cur=w[:,2]; template=cur[-640:]
            aligned=template[np.arange(len(cur))%640]
            start=int(.3*FS); err=cur-aligned
            moving=np.sqrt(np.convolve(err**2,np.ones(640)/640,'valid'))
            ts=t[639:]; threshold=.02*row.i1_rms_a
            pos=np.flatnonzero(ts>=.3+.02)
            bad=pos[moving[pos]>threshold]
            first=(int(bad[-1])+1) if len(bad) else int(pos[0])
            settling=float((ts[first]-.3)*1000) if first<len(ts) else None
            sl=slice(start,start+int(.1*FS))
            trans.append(dict(run_id=row.run_id,case_id=row.case_id,design_hz=row.ctl_design_hz,k3=row.ctl_k3,k5=row.ctl_k5,
                settling_cycle_metric_ms=settling,criterion_rms_a=threshold,peak_current_first100ms_a=float(abs(cur[sl]).max()),saturation_first100ms=float(w[sl,6].mean()),
                note='Post-selection diagnostic, one-cycle trailing window, 2% final I1; not OEM transient pass/fail'))
    pd.DataFrame(trans).to_csv(r/'transient_diagnostics.csv',index=False)
    # Preserve actual excluded-envelope failures. They are not dropped from any denominator.
    g=pd.read_csv(r/'sentinel_improved.csv'); g[~g.combined_pass].to_csv(r/'sentinel_failures.csv',index=False)
    worst=g.loc[g.thd_pct.idxmax()]
    phase=pd.read_csv(r/'phase.csv'); phase.assign(s=phase.s_va.round()).groupby(['s','ctl_design_hz','ctl_k3','ctl_k5']).agg(min_thd=('thd_pct','min'),max_thd=('thd_pct','max')).reset_index().to_csv(r/'phase_invariance.csv',index=False)
    (r/'raw_audit.json').write_text(json.dumps(checks,indent=2,allow_nan=False))
    if not all(x['passed'] for x in checks): raise AssertionError('Audit failed')
    return checks

if __name__=='__main__':
    print(json.dumps(audit(Path(__file__).resolve().parents[1]),indent=2))
