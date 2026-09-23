"""Numerical verification, distinct from empirical model validation."""
import json
from dataclasses import replace
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp
from .model import *


def run_verification(outdir):
    outdir=Path(outdir); outdir.mkdir(parents=True,exist_ok=True)
    checks=[]; convergence=[]
    def record(name,value,limit,unit='',note=''):
        checks.append(dict(test=name,value=float(value),limit=float(limit),unit=unit,
                           passed=bool(value<=limit),note=note))
    # Independently constructed signal, not a plant result.
    t=np.arange(6400)*TS
    x=np.zeros((6400,9)); x[:,0]=t
    x[:,1]=230*math.sqrt(2)*np.sin(W0*t)
    x[:,2]=math.sqrt(2)*(10*np.sin(W0*t)+.3*np.sin(3*W0*t+.7)+.4*np.cos(5*W0*t-.2))
    m,h=harmonic_metrics(x,2300,0,230)
    record('known_harmonic_THD',abs(m['thd_pct']-5.),1e-10,'percentage point')
    record('known_fundamental_RMS',abs(m['i1_rms_a']-10.),1e-10,'A')
    record('known_active_power',abs(m['p_w']-2300),1e-8,'W')
    x[:,2]=-math.sqrt(2)*5*np.cos(W0*t)
    m,_=harmonic_metrics(x,0,1150,230)
    record('reactive_power_sign',abs(m['q1_var']-1150),1e-8,'var')
    # Exact scalar RL solution, with nonzero initial state and DC forcing.
    y=2.; L=.0017; R=.25; u=13.; dt=TS/2
    for k in range(1280):
        y=rk4_step(k*dt,y,u,dt,L,R,400.,0.,0.,.25,0.,0.,0)
    exact=u/R+(2-u/R)*np.exp(-R*1280*dt/L)
    record('RL_closed_form',abs(y-exact),1e-8,'A')
    # Nonlinear one-period integration checked against independent SciPy solver.
    # One fixed applied command over one control interval in each test.
    rng=np.random.default_rng(9341)
    err=[]
    for _ in range(80):
        ti=rng.uniform(0,.02); yi=rng.uniform(-10,10); ui=rng.uniform(-360,360)
        rr=rng.uniform(.15,.45); ll=rng.uniform(.0013,.0025)
        ee=rng.uniform(4,18); zz=rng.uniform(.15,.45)
        def f(tt,xx):
            vi=np.clip(ui-ee*np.tanh(xx[0]/zz),-400,400)
            return [(vi-rr*xx[0]-230*np.sqrt(2)*np.sin(W0*tt))/ll]
        ref=solve_ivp(f,(ti,ti+TS),[yi],method='DOP853',rtol=2e-12,atol=1e-13).y[0,-1]
        yy=yi
        for j in range(16):
            yy=rk4_step(ti+j*TS/16,yy,ui,TS/16,ll,rr,400.,230*np.sqrt(2),ee,zz,0.,0.,0)
        err.append(abs(yy-ref))
    record('nonlinear_RK4_vs_DOP853',max(err),0.001,'A','80 independently generated one-step cases; 16 substeps (initial 8-substep stress check failed; see development log)')
    probes=[Case('low',p=350,q=0),Case('reactive',p=0,q=700),
            Case('hard',p=350,q=-700,dead_us=1.3,zero_a=.15,vrms=253,lf=.00135)]
    controls=[Control(),Control(900,1.,.3)]
    waves={}
    for c in probes:
        for co in controls:
            results={}
            for sub in [4,8,16]:
                w=simulate(c,co,substeps=sub)
                m,_=harmonic_metrics(w,c.p,c.q,c.vrms)
                results[sub]=m
                convergence.append(dict(case_id=c.case_id,comp_gain=co.comp_gain,bw_hz=co.bw_hz,substeps=sub,**m))
            tag=c.case_id+'_'+str(co.comp_gain)
            record('time_refinement_'+tag,abs(results[8]['thd_pct']-results[16]['thd_pct']),.02,'THD percentage point')
            record('periodic_steady_state_'+tag,results[16]['periodicity_rms_a'],.0001,'A')
            waves[tag]=w[-6400:]
    c=Case('duration',p=350,q=700); co=Control(900,1.,.3)
    wa=simulate(c,co,cycles=40); wb=simulate(c,co,cycles=60)
    ma,_=harmonic_metrics(wa,c.p,c.q,c.vrms); mb,_=harmonic_metrics(wb,c.p,c.q,c.vrms)
    record('settling_40_vs_60_cycles',abs(ma['thd_pct']-mb['thd_pct']),.001,'THD percentage point')
    record('deterministic_repeat',np.max(np.abs(wa-simulate(c,co))),0.,'all channels')
    record('PLL_locked_phase_error',abs(ma['pll_error_deg']),.5,'degree','50 Hz steady state; acquisition NOT tested')
    # Independent harmonic projection vs FFT, including arbitrary window origin.
    zz=wa[-6400:]; yy=zz[:,2]; tt=zz[:,0]
    hdir=[]
    for hh in range(1,41):
        a=2*np.mean(yy*np.sin(hh*W0*tt)); b=2*np.mean(yy*np.cos(hh*W0*tt))
        hdir.append(math.hypot(a,b)/math.sqrt(2))
    _,hfft=harmonic_metrics(wa,c.p,c.q,c.vrms)
    record('FFT_vs_direct_projection',np.max(np.abs(np.array(hdir)-hfft)),1e-10,'A')
    # Power balance for the assumed averaged circuit, quadrature evaluated at samples.
    interval=wa[-6401:]
    y0=interval[:-1,2]; y1=interval[1:,2]; u=interval[:-1,4]
    ee=c.vdc*FS*c.dead_us*1e-6
    vi0=np.clip(u-ee*np.tanh(y0/c.zero_a),-c.vdc,c.vdc)
    vi1=np.clip(u-ee*np.tanh(y1/c.zero_a),-c.vdc,c.vdc)
    input_power=np.mean(((vi0-interval[:-1,1])*y0+(vi1-interval[1:,1])*y1)/2)
    loss=(c.rf+c.rg)*np.mean((y0*y0+y1*y1)/2)
    storage=(c.lf+c.lg)*(y1[-1]**2-y0[0]**2)/(2*6400*TS)
    residual=input_power-loss-storage
    record('mean_power_balance',abs(residual),.5,'W','interval trapezoid; command held separately in each interval; energy storage included')
    (outdir/'verification.json').write_text(json.dumps(dict(checks=checks,all_passed=all(r['passed'] for r in checks)),indent=2),encoding='utf-8')
    import pandas as pd
    pd.DataFrame(convergence).to_csv(outdir/'convergence.csv',index=False,float_format='%.12g')
    np.savez_compressed(outdir/'verification_waveforms.npz',**waves)
    for item in checks:
        print(('PASS ' if item['passed'] else 'FAIL ')+item['test']+': '+str(item['value']),flush=True)
    return checks

if __name__=='__main__':
    import sys
    checks=run_verification(sys.argv[1] if len(sys.argv)>1 else 'results')
    if not all(x['passed'] for x in checks):
        raise SystemExit('Numerical gate FAILED. Do not proceed to performance claims.')
