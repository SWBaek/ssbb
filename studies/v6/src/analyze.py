"""Finite-design statistics and independent recalculation from V6 saved records."""
from model import *
from study import clean,savejson,csv,sha
from dataclasses import replace
import pandas as pd
import itertools,time
R=ROOT/'results';Q=ROOT/'qa'

def paired(a,b):
    key='case_id';cols=['case_id','thd_pct','current_rms_a','combined_pass','thd_pass','tracking_pass','rms_pass','peak_pass','saturation_pass','steady_pass']
    x=a[cols].merge(b[cols],on=key,suffixes=('_initial','_selected'),validate='one_to_one')
    x['thd_decrease_pp']=x.thd_pct_initial-x.thd_pct_selected
    x['new_failure']=x.combined_pass_initial & ~x.combined_pass_selected
    return x

def summary(a):
    return {'n':len(a),'thd_mean':float(a.thd_pct.mean()),'thd_max':float(a.thd_pct.max()),'thd_min':float(a.thd_pct.min()),'thd_pass_n':int(a.thd_pass.sum()),'combined_pass_n':int(a.combined_pass.sum()),'rms_pass_n':int(a.rms_pass.sum()),'tracking_pass_n':int(a.tracking_pass.sum()),'saturation_pass_n':int(a.saturation_pass.sum()),'steady_pass_n':int(a.steady_pass.sum())}

def main():
    allr=pd.read_csv(R/'all_runs.csv');a=pd.read_csv(R/'baseline.csv');b=pd.read_csv(R/'improved.csv');doe=pd.read_csv(R/'doe.csv');cs=pd.read_csv(R/'candidates.csv')
    selected=json.loads((R/'selected_control.json').read_text());train=selected['selected_from_ids']
    sums={'specification':SPEC,'selected':selected,'campaign_runs':len(allr),'nominal':{'initial':summary(a),'selected':summary(b)}}
    pairs=paired(a,b);pairs.to_csv(R/'main_paired.csv',index=False)
    sums['selection_unused']={'initial':summary(a[~a.case_id.isin(train)]),'selected':summary(b[~b.case_id.isin(train)])}
    for name in ['voltage','variation','structure']:
        x=pd.read_csv(R/(name+'.csv'));u=x[x.control_tag=='initial'];v=x[x.control_tag=='selected'];pp=paired(u,v);pp.to_csv(R/(name+'_paired.csv'),index=False)
        sums[name]={'initial':summary(u),'selected':summary(v),'new_failure_ids':pp.loc[pp.new_failure,'case_id'].tolist()}
    sums['nominal']['new_failure_ids']=pairs.loc[pairs.new_failure,'case_id'].tolist()
    fail=b[~b.combined_pass].copy();fail.to_csv(R/'main_failures.csv',index=False)
    # Equivalent RMS values used only for grouping; input schema remains peak.
    for x in [a,b]:
        x['reference_rms_a']=np.round(np.hypot(x.id_peak_a,x.iq_peak_a)/SQ2,8)
        x['stratum']=pd.cut(x.reference_rms_a,[0,8,24,48.0000001],labels=['low_le_8Arms','medium_8_to_24Arms','high_24_to_48Arms'])
    strata=[]
    for name in a.stratum.cat.categories:
        for tag,x in [('initial',a),('selected',b)]:strata.append({'stratum':name,'control':tag,**summary(x[x.stratum==name])})
    csv(R/'current_strata.csv',strata);sums['strata']=strata
    effects=[]
    for f in ['kr_ohm','band_hz','max_harmonic']:
        g=doe.groupby(f).thd_pct.agg(['mean','min','max','count'])
        for lev,rr in g.iterrows():effects.append({'factor':f,'level':lev,'mean_thd':rr['mean'],'n_responses':int(rr['count'])})
    csv(R/'main_effects.csv',effects)
    inter=doe.groupby(['kr_ohm','max_harmonic']).thd_pct.mean().reset_index();inter.to_csv(R/'interactions.csv',index=False)
    # Orthogonal ANOVA decomposition of 27 deterministic candidate means. No error df / p-value.
    cols=['kr_ohm','band_hz','max_harmonic'];arr=cs.sort_values(cols).thd_mean.to_numpy().reshape(3,3,3);grand=arr.mean();effects_arr={};terms=[]
    for n in range(1,4):
        for sub in itertools.combinations(range(3),n):
            axes=tuple(k for k in range(3) if k not in sub);m=arr.mean(axis=axes,keepdims=True) if axes else arr.copy();v=m-grand
            for ss,z in effects_arr.items():
                if set(ss).issubset(sub):v=v-z
            effects_arr[sub]=v;ssval=float(np.sum(v*v)*(3**(3-n)));terms.append({'term':'*'.join(cols[k] for k in sub),'df':2**n,'SS':ssval})
    total=float(np.sum((arr-grand)**2));assert abs(sum(x['SS'] for x in terms)-total)<1e-10
    for x in terms:x['share_percent']=100*x['SS']/total
    csv(R/'factorial_decomposition.csv',terms);sums['factorial_ss_total']=total
    # Refinement compares both low harmonics and total RMS current, including pass flips.
    rr=pd.read_csv(R/'refinement.csv');re=[]
    for cid,g in rr.groupby('case_id'):
        for tag in ['initial','selected']:
            x=g[g.control_tag.str.startswith(tag)].copy();x['dt']=x.control_tag.str.split('_').str[-1].astype(float);x=x.sort_values('dt');fine=x.iloc[0]
            for _,row in x.iterrows():re.append({'case_id':cid,'control':tag,'dt_s':row['dt'],'thd_pct':row.thd_pct,'rms_a':row.current_rms_a,'delta_thd_pp':row.thd_pct-fine.thd_pct,'delta_rms_a':row.current_rms_a-fine.current_rms_a,'combined_pass':row.combined_pass,'same_verdict_as_finest':row.combined_pass==fine.combined_pass})
    csv(R/'refinement_comparison.csv',re);sums['numerical_refinement']={'max_abs_thd_pp':max(abs(x['delta_thd_pp']) for x in re),'max_abs_rms_a':max(abs(x['delta_rms_a']) for x in re),'all_verdicts_equal':all(x['same_verdict_as_finest'] for x in re)}
    lo=pd.read_csv(R/'long_duration.csv');lcmp=[]
    for _,x in lo.iterrows():
        orig=rr[(rr.case_id==x.case_id)&(rr.control_tag==x.control_tag+'_2.0e-06')].iloc[0]
        lcmp.append({'case_id':x.case_id,'control':x.control_tag,'thd_delta_pp':x.thd_pct-orig.thd_pct,'rms_delta_a':x.current_rms_a-orig.current_rms_a,'same_verdict':bool(x.combined_pass==orig.combined_pass)})
    csv(R/'duration_comparison.csv',lcmp);sums['duration']={'max_abs_thd_pp':max(abs(x['thd_delta_pp']) for x in lcmp),'max_abs_rms_a':max(abs(x['rms_delta_a']) for x in lcmp),'all_verdicts_equal':all(x['same_verdict'] for x in lcmp)}
    # Independent end-window coherent FFT (60 Hz, 0.25 seconds) on uniform current samples.
    fft=[]
    for _,x in allr[allr.fgrid_hz==60.].iterrows():
        z=np.load(ROOT/'waveforms'/(x.run_id+'.npz'));dt=float(z['dt_s']);n=int(round(.25/dt));raw=z['current_a'][-n:].astype(float)
        freq=np.fft.rfft(raw)/n;amps=SQ2*np.abs(freq[15*np.arange(1,41)]);th=100*np.linalg.norm(amps[1:])/amps[0]
        fft.append({'run_id':x.run_id,'fft_thd_pct':th,'projection_thd_pct':x.thd_pct,'absolute_difference_pp':abs(th-x.thd_pct)})
    csv(Q/'fft_crosscheck.csv',fft);sums['fft_check']={'runs':len(fft),'max_absolute_difference_pp':max(x['absolute_difference_pp'] for x in fft)}
    # Raw data audit: recompute every stored metric and all 40 harmonic magnitudes.
    maxdiff=0.;maxharm=0.;passmatch=True;traceok=True
    for k,x in allr.iterrows():
        fp=ROOT/'waveforms'/(x.run_id+'.npz');assert sha(fp)==x.wave_sha256
        zz=np.load(fp);meta=json.loads(str(zz['metadata']));c=Case(**meta['case']);w={key:zz[key] for key in zz.files if key!='metadata'}
        step=meta['options'].get('step');m,h=measure(w,c,step[1:] if step else None)
        for key,val in m.items():
            if isinstance(val,bool):passmatch=passmatch and val==bool(x[key])
            elif val is not None:maxdiff=max(maxdiff,abs(float(val)-float(x[key])))
        maxharm=max(maxharm,max(abs(h[j]-x[f'h{j+1}_rms_a']) for j in range(40)))
        n=int(w['pwm_count']);assert int(w['control_count'])==n
        assert int(w['load_count'])==n-1-c.extra_delay_pwm
        valid=w['pwm'][:,4]>=0;ix=np.arange(n-len(w['pwm']),n)[valid];traceok=traceok and bool(np.all(ix-w['pwm'][valid,4]==1+c.extra_delay_pwm))
        # Verify actual external log is Peak A, not a mislabeled RMS number.
        tr=w['control'];refs=(c.id_peak_a,c.iq_peak_a) if not step else step[1:]
        assert np.allclose(tr[-100:,0],refs[0],atol=1e-5,rtol=0) and np.allclose(tr[-100:,1],refs[1],atol=1e-5,rtol=0)
        if k%100==0:print('audited',k,flush=True)
    assert passmatch and traceok and maxharm<1e-8 and maxdiff<1e-5
    savejson(Q/'raw_audit.json',{'runs':len(allr),'all_wave_hashes_verified':True,'metric_max_csv_roundtrip_difference':maxdiff,'harmonic_max_difference_a':maxharm,'all_flags_equal':passmatch,'all_clock_ratios_one':True,'all_fifo_offsets_verified':traceok,'peak_command_log_verified':True})
    # Exact repeated execution check of representative cases; not independent samples.
    replay=[]
    for runid in [allr.iloc[0].run_id,allr[allr.group=='improved'].iloc[20].run_id,allr[allr.group=='variation'].iloc[1].run_id,allr[allr.group=='functional'].iloc[-1].run_id]:
        z=np.load(ROOT/'waveforms'/(runid+'.npz'));meta=json.loads(str(z['metadata']));w=simulate(Case(**meta['case']),Control(**meta['control']),**meta['options']);eq=bool(np.array_equal(w['current_a'],z['current_a']));replay.append({'run_id':runid,'current_array_exact_equal':eq});assert eq
    savejson(Q/'replay.json',replay)
    # Transient envelope: use offline, one-cycle linear-phase moving average of logged dq.
    # This is a declared observation definition, not closed-loop bandwidth measurement.
    transient=[]
    for _,x in allr[allr.group=='transient'].iterrows():
        z=np.load(ROOT/'waveforms'/(x.run_id+'.npz'));meta=json.loads(str(z['metadata']));tr=z['control'];tt=(np.arange(len(tr))+.5)*TS;step=meta['options']['step'];c=Case(**meta['case']);n=int(round(1/c.fgrid_hz/TS));ker=np.ones(n)/n
        ed=np.convolve(tr[:,2],ker,'valid');eq=np.convolve(tr[:,3],ker,'valid');tc=tt[n//2:n//2+len(ed)]
        rd,rq=step[1:];tol=max(.3,.02*math.hypot(rd,rq));after=tc>=step[0]+.5/c.fgrid_hz;good=(abs(ed-rd)<=tol)&(abs(eq-rq)<=tol)&after
        bad=np.where((~good)&after)[0];first=(bad[-1]+1) if len(bad) else np.searchsorted(tc,step[0]+.5/c.fgrid_hz)
        settle=float(tc[first]-step[0]) if first<len(tc) and np.all(good[first:]) else None
        orth=eq if c.iq_peak_a==rq else ed if c.id_peak_a==rd else None
        dev=float(np.max(abs(orth[after]-(rq if c.iq_peak_a==rq else rd)))) if orth is not None else None
        transient.append({'case_id':c.case_id,'control':x.control_tag,'estimated_settling_ms':None if settle is None else 1000*settle,'unchanged_axis_peak_deviation_a':dev,'measurement':'centered one-cycle average of dq feedback; finite horizon'})
    csv(R/'transient_envelope.csv',transient);sums['transients']=transient
    sums['audit']={'unit_tests':json.loads((Q/'unit_tests.json').read_text()),'raw':json.loads((Q/'raw_audit.json').read_text()),'replays':replay}
    savejson(R/'summary.json',sums);print(json.dumps(clean(sums),ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__':main()
