"""V7 switching reference model. External dq currents are PEAK A, never RMS.
One ADC/control event per PWM. Explicit FIFO prevents lost delayed commands.
The model is not PSIM, measured hardware, or a complete OBC firmware emulator.
"""
from dataclasses import dataclass,asdict
import math
from pathlib import Path
import json
import numpy as np
from scipy.linalg import expm
from numba import njit

ROOT=Path(__file__).resolve().parents[1]
SPEC=json.loads((ROOT/'specification.json').read_text())
V_NOM=240.;I_RATED=48.;SQ2=math.sqrt(2);I_PEAK_MAX=I_RATED*SQ2
TP=16e-6;TS=16e-6;FSW=62500.;FCTRL=62500.;F0=60.
LN=.0011;RN=.18
TRACE_COLS=['id_ref_peak_a','iq_ref_peak_a','id_fb_peak_a','iq_fb_peak_a','i_sample_a','command_v','resonator_v','limit_flag','theta_error_deg','pll_hz','resonator_limit_flag','integrator_limit_flag']
PWM_COLS=['applied_v','duty_high','lower_leg','voltage_limit_flag','source_sample_index']

@dataclass(frozen=True)
class Case:
    case_id:str
    id_peak_a:float
    iq_peak_a:float
    vac_v:float=240.
    vdc_v:float=400.
    fgrid_hz:float=60.
    lf_h:float=.001
    lg_h:float=.0001
    rf_ohm:float=.08
    rg_ohm:float=.1
    dead_s:float=200e-9
    sensor_hz:float=10000.
    sensor_offset_a:float=0.
    sensor_gain:float=1.
    adc_bits:int=12
    grid_h3:float=0.
    grid_h5:float=0.
    extra_delay_pwm:int=0
    grid_phase_rad:float=0.
    lf_grid_polarity:bool=False

@dataclass(frozen=True)
class Control:
    bandwidth_design_hz:float=800.
    pll_design_hz:float=15.
    kr_ohm:float=0.
    band_hz:float=8.
    max_harmonic:int=7
    prediction_s:float=16e-6


def assert_spec():
    s=SPEC['user_confirmed'];d=SPEC['derived_not_substituted']
    assert s['nominal_ac_voltage_rms_v']==V_NOM==240.
    assert s['rated_ac_current_rms_a']==I_RATED==48.
    assert s['switching_frequency_hz']==FSW==FCTRL==s['controller_frequency_hz']==62500.
    assert TS==TP==s['controller_period_s']==16e-6
    assert d['controller_evaluations_per_pwm']==1
    assert abs(d['max_dq_command_vector_peak_a']-I_PEAK_MAX)<1e-12
    assert d['rated_apparent_power_va']==240*48==11520
    assert 'peak' in s['dq_command_scaling']


def validate(c):
    for k,v in asdict(c).items():
        if k!='case_id' and not math.isfinite(float(v)):raise ValueError(k)
    if math.hypot(c.id_peak_a,c.iq_peak_a)>I_PEAK_MAX+1e-10:raise ValueError('Peak dq vector exceeds sqrt(2)*48 A')
    if min(c.vac_v,c.vdc_v,c.lf_h,c.sensor_hz)<=0 or c.lg_h<0 or c.rf_ohm+c.rg_ohm<=0:raise ValueError('Invalid physical input')
    if not 0<=c.dead_s<TP*.1 or c.extra_delay_pwm not in (0,1,2):raise ValueError('Invalid timing')
    if not 55<=c.fgrid_hz<=65:raise ValueError('Unsupported grid frequency')


def coefficients(ctrl):
    w=2*math.pi*F0;k=SQ2;a=np.array([[-k*w,-w],[w,0.]])
    ad=expm(a*TS);bd=np.linalg.solve(a,(ad-np.eye(2)))@np.array([k*w,0.])
    hc=np.zeros((3,4));wc=2*math.pi*ctrl.band_hz
    for j,h in enumerate([3,5,7]):
        wh=h*w;K=wh/math.tan(wh*TS/2);den=K*K+2*wc*K+wh*wh
        hc[j]=[2*ctrl.kr_ohm*wc*K/den,2*(wh*wh-K*K)/den,(K*K-2*wc*K+wh*wh)/den,float(h<=ctrl.max_harmonic)]
    return ad,bd,hc

@njit(cache=True)
def grid(t,vp,w,ph,h3,h5):
    x=w*t+ph
    return vp*(math.cos(x)+h3*math.cos(3*x+.2)+h5*math.cos(5*x-.3))

@njit(cache=True)
def rl_sensor(i,z,u,v,dt,L,R,wf,blank,lower,dc):
    a=R/L;ea=math.exp(-a*dt);ef=math.exp(-wf*dt);eq=(u-v)/R
    inn=eq+(i-eq)*ea
    # Analytic first-order sensor driven by analytic RL current.
    if abs(wf-a)<1e-8:
        zn=eq+(z-eq)*ef+wf*(i-eq)*dt*ef
    else:
        zn=eq+(z-eq)*ef+wf*(i-eq)*(ea-ef)/(wf-a)
    if blank and i*inn<0 and -lower*dc<=v<=(1-lower)*dc:
        tz=-math.log(-eq/(i-eq))/a
        eaz=math.exp(-a*tz);efz=math.exp(-wf*tz)
        zz=eq+(z-eq)*efz+wf*(i-eq)*(eaz-efz)/(wf-a)
        return 0.,zz*math.exp(-wf*(dt-tz))
    return inn,zn

@njit(cache=True)
def run_core(par,cv,ad,bd,hc,ncycles,nsub,nkeep,step_time,step_d,step_q,oracle):
    id0,iq0,vac,dc,fg,L,R,dead,fc,off,gain,bits,h3,h5,extra,ph,lfgrid=par
    bw,pbw,kr,band,hm,predict=cv
    vp=SQ2*vac;wg=2*math.pi*fg;wf=2*math.pi*fc;dt=TP/nsub
    kp=2*math.pi*bw*LN;ki=2*math.pi*bw*RN
    wn=2*math.pi*pbw;kpp=SQ2*wn;kip=wn*wn
    lsb=200/(2**int(bits)) if bits else 0.
    raw=np.empty(nkeep*nsub,np.float32);tr=np.empty((ncycles,12),np.float32);pw=np.empty((nkeep,5),np.float32)
    i=0.;z=0.;theta=ph;omega=2*math.pi*F0;pll_z=0.
    xv=vp*math.cos(ph);yv=vp*math.sin(ph);xi=0.;yi=0.;pv=vp*math.cos(ph);pi=0.
    zd=0.;zq=0.;e1=0.;e2=0.;y1=np.zeros(3);y2=np.zeros(3)
    # Queue indexed by PWM boundary. Every control result has one independent slot.
    queue=np.zeros(ncycles+5);src=np.full(ncycles+5,-1,np.int64)
    cmd=0.;source=-1;ctrl_count=0;load_count=0;lf_transitions=0;prev_lower=0.
    target=0.;gate=0.;turnon=-1.
    for p in range(ncycles):
        t0=p*TP
        if src[p]>=0:cmd=queue[p];source=src[p];load_count+=1
        # Nominal LF follows voltage command sign. Grid polarity is an explicit alternative.
        if lfgrid>0.5:lower=0. if math.cos(wg*(t0+TP/2)+ph)>=0 else 1.
        else:lower=0. if cmd>=0 else 1.
        if p>0 and lower!=prev_lower:lf_transitions+=1
        prev_lower=lower
        dr=lower+cmd/dc;d=min(1.,max(0.,dr));rail_clip=1. if d!=dr else 0.
        rise=t0+.5*TP*(1-d);fall=t0+.5*TP*(1+d)
        haspulse=d>1e-14 and d<1-1e-14
        didrise=not haspulse;didfall=not haspulse
        initial=1. if d>=1-1e-14 else 0.
        # Gate transition state persists across PWM boundaries, including pending dead-time.
        if initial!=target:
            target=initial;gate=-1. if dead>0 else target;turnon=t0+dead
        if p>=ncycles-nkeep:pw[p-(ncycles-nkeep)]=np.array([cmd,d,lower,rail_clip,float(source)])
        for j in range(nsub):
            left=t0+j*dt;end=t0+(j+1)*dt
            for seg in range(8):
                if not didrise and left>=rise-1e-15:
                    target=1.;gate=-1. if dead>0 else target;turnon=rise+dead;didrise=True
                if not didfall and left>=fall-1e-15:
                    target=0.;gate=-1. if dead>0 else target;turnon=fall+dead;didfall=True
                if gate<0 and left>=turnon-1e-15:gate=target
                right=end
                if not didrise and rise<right-1e-15:right=rise
                if not didfall and fall<right-1e-15:right=fall
                if gate<0 and turnon>left+1e-15 and turnon<right-1e-15:right=turnon
                tm=(left+right)/2;v=grid(tm,vp,wg,ph,h3,h5);blank=gate<0
                if not blank:pole=gate
                elif i>0:pole=0.
                elif i<0:pole=1.
                else:pole=min(1.,max(0.,lower+v/dc))
                i,z=rl_sensor(i,z,(pole-lower)*dc,v,right-left,L,R,wf,blank,lower,dc)
                left=right
                if left>=end-1e-15:break
            if p>=ncycles-nkeep:raw[(p-(ncycles-nkeep))*nsub+j]=i
            # EXACTLY once at the middle of EVERY PWM interval (no p%2 gate).
            if j+1==nsub//2:
                t=t0+TP/2;v=grid(t,vp,wg,ph,h3,h5);im=gain*z+off
                if bits:im=round(im/lsb)*lsb
                if p>0:
                    a=ad[0,0]*xv+ad[0,1]*yv+bd[0]*pv;b=ad[1,0]*xv+ad[1,1]*yv+bd[1]*pv;xv=a;yv=b
                    a=ad[0,0]*xi+ad[0,1]*yi+bd[0]*pi;b=ad[1,0]*xi+ad[1,1]*yi+bd[1]*pi;xi=a;yi=b
                refd=id0;refq=iq0
                if step_time>=0 and t>=step_time:refd=step_d;refq=step_q
                # Smooth energization only; steady DC requests unmodified after 50 ms.
                ramp=min(1.,t/.05);refd*=ramp;refq*=ramp
                if oracle:theta=wg*t+ph;omega=wg
                cs=math.cos(theta);sn=math.sin(theta)
                idm=im*cs+yi*sn;iqm=-im*sn+yi*cs
                ed=refd-idm;eq=refq-iqm;err=refd*cs-refq*sn-im
                uh=0.;hcclip=0.
                for h in range(3):
                    yy=hc[h,0]*(err-e2)-hc[h,1]*y1[h]-hc[h,2]*y2[h];yyc=min(30.,max(-30.,yy))
                    if hc[h,3]>0 and yy!=yyc:hcclip=1.
                    y2[h]=y1[h];y1[h]=yyc;uh+=hc[h,3]*yyc
                e2=e1;e1=err
                vd=v*cs+yv*sn;vq=-v*sn+yv*cs
                ud=vd+RN*idm-omega*LN*iqm+kp*ed+zd
                uq=vq+RN*iqm+omega*LN*idm+kp*eq+zq
                thp=theta+omega*predict;ur=ud*math.cos(thp)-uq*math.sin(thp)+uh
                lim=1. if abs(ur)>dc else rail_clip;u=min(dc,max(-dc,ur))
                # Basic integrator freeze under bridge saturation, logged separately.
                if lim==0.:
                    zd+=ki*TS*ed;zq+=ki*TS*eq
                zclip=1. if abs(zd)>150 or abs(zq)>150 else 0.;zd=min(150.,max(-150.,zd));zq=min(150.,max(-150.,zq))
                due=p+1+int(extra);queue[due]=u;src[due]=p
                if not oracle:
                    pe=(-xv*sn+yv*cs)/max(10.,math.hypot(xv,yv));pll_z+=kip*TS*pe
                    omega=min(2*math.pi*65,max(2*math.pi*55,2*math.pi*F0+kpp*pe+pll_z))
                ae=math.atan2(math.sin(theta-wg*t-ph),math.cos(theta-wg*t-ph))*180/math.pi
                tr[p]=np.array([refd,refq,idm,iqm,im,u,uh,lim,ae,omega/(2*math.pi),hcclip,zclip])
                theta=(theta+omega*TS)%(2*math.pi);pv=v;pi=im;ctrl_count+=1
    return raw,tr,pw,ctrl_count,load_count,lf_transitions


def simulate(case,control,duration_s=.75,dt_s=2e-6,step=None,oracle=False):
    assert_spec();validate(case)
    ns=int(round(TP/dt_s))
    if ns%2 or abs(ns*dt_s-TP)>1e-12:raise ValueError('Even subdivision of 16 us required')
    n=int(math.ceil(duration_s/TP));nk=int(math.ceil(15/case.fgrid_hz/TP))+3
    if n<=nk+100:raise ValueError('Duration too short')
    st,sd,sq=(-1.,0.,0.) if step is None else step
    if step is not None and math.hypot(sd,sq)>I_PEAK_MAX+1e-10:raise ValueError('Step exceeds peak dq vector bound')
    par=np.array([case.id_peak_a,case.iq_peak_a,case.vac_v,case.vdc_v,case.fgrid_hz,case.lf_h+case.lg_h,case.rf_ohm+case.rg_ohm,case.dead_s,case.sensor_hz,case.sensor_offset_a,case.sensor_gain,case.adc_bits,case.grid_h3,case.grid_h5,case.extra_delay_pwm,case.grid_phase_rad,float(case.lf_grid_polarity)])
    ad,bd,hc=coefficients(control);cv=np.array(list(asdict(control).values()),float)
    raw,tr,pw,nc,nl,nf=run_core(par,cv,ad,bd,hc,n,ns,nk,st,sd,sq,bool(oracle))
    if not np.isfinite(raw).all() or not np.isfinite(tr).all():raise FloatingPointError('Nonfinite')
    assert nc==n and nl==n-1-case.extra_delay_pwm
    valid=pw[:,4]>=0;indices=np.arange(n-nk,n)[valid]
    assert np.all(indices-pw[valid,4]==1+case.extra_delay_pwm),'Latency FIFO mismatch'
    return {'current_a':raw,'control':tr,'pwm':pw,'dt_s':float(TP/ns),'t0_s':(n-nk)*TP+TP/ns,'end_s':n*TP,'pwm_count':n,'control_count':nc,'load_count':nl,'lf_transition_count':nf}


def harmonics_projection(t,i,f,ph,nh=40):
    dur=t[-1]-t[0];ang=2*np.pi*f*t+ph
    coeff=np.empty((nh,2))
    for h in range(1,nh+1):
        coeff[h-1]=[2*np.trapezoid(i*np.cos(h*ang),t)/dur,2*np.trapezoid(i*np.sin(h*ang),t)/dur]
    return np.hypot(coeff[:,0],coeff[:,1])/SQ2,coeff


def measure(w,c,final_refs=None):
    raw=np.asarray(w['current_a'],float);dt=float(w['dt_s']);t=float(w['t0_s'])+np.arange(len(raw))*dt
    end=t[-1];start=end-15/c.fgrid_hz;k=np.searchsorted(t,start,side='right')
    tt=np.r_[start,t[k:]];ii=np.r_[np.interp(start,t,raw),raw[k:]];dur=end-start
    hs,co=harmonics_projection(tt,ii,c.fgrid_hz,c.grid_phase_rad);i1=hs[0];ih=np.linalg.norm(hs[1:])
    thd=100*ih/i1 if i1>.05 else None
    irms=float(np.sqrt(np.trapezoid(ii*ii,tt)/dur));id1=co[0,0];iq1=-co[0,1]
    rd,rq=(c.id_peak_a,c.iq_peak_a) if final_refs is None else final_refs
    tol=max(.3,.02*math.hypot(rd,rq));ts=(np.arange(len(w['control']))+int(w.get('control_start_index',0))+.5)*TP;tr=w['control'][ts>=start]
    ptime=float(w['end_s'])-len(w['pwm'])*TP+np.arange(len(w['pwm']))*TP;pw=w['pwm']
    weight=np.maximum(0.,np.minimum(ptime+TP,end)-np.maximum(ptime,start))
    clip=max(float(np.mean(tr[:,7])),float(np.dot(weight,pw[:,3])/dur))
    hclip=float(np.mean(tr[:,10]));zclip=float(np.mean(tr[:,11]));peak=float(np.max(abs(ii)))
    # Compare low-order harmonic envelopes, not asynchronous PWM ripple across grid cycles.
    cy=[]
    for j in [1,2]:
        a=end-j/c.fgrid_hz;b=a+1/c.fgrid_hz;sel=(tt>a)&(tt<b)
        tx=np.r_[a,tt[sel],b];iy=np.r_[np.interp(a,tt,ii),ii[sel],np.interp(b,tt,ii)]
        _,cx=harmonics_projection(tx,iy,c.fgrid_hz,c.grid_phase_rad,7);cy.append(cx)
    per=float(np.linalg.norm(cy[0]-cy[1])/SQ2);ref_rms=math.hypot(rd,rq)/SQ2
    ang=2*np.pi*c.fgrid_hz*tt+c.grid_phase_rad;vv=SQ2*c.vac_v*(np.cos(ang)+c.grid_h3*np.cos(3*ang+.2)+c.grid_h5*np.cos(5*ang-.3))
    p=float(np.trapezoid(vv*ii,tt)/dur)
    flags={'thd_pass':thd is not None and thd<=5.,'tracking_pass':abs(id1-rd)<=tol and abs(iq1-rq)<=tol,'rms_pass':irms<=48.,'peak_pass':peak<=75.,'saturation_pass':clip<=.01 and hclip==0 and zclip==0,'steady_pass':per<=max(.03,.002*ref_rms)}
    return dict(thd_pct=thd,i1_rms_a=float(i1),ih_2_40_rms_a=float(ih),ih_over_rated_pct=100*float(ih)/48.,current_rms_a=irms,peak_a=peak,dc_a=float(np.trapezoid(ii,tt)/dur),id_peak_measured_a=float(id1),iq_peak_measured_a=float(iq1),id_error_peak_a=float(id1-rd),iq_error_peak_a=float(iq1-rq),dq_tolerance_peak_a=tol,p_w=p,p1_w=c.vac_v*id1/SQ2,q1_var=-c.vac_v*iq1/SQ2,p1_target_w=c.vac_v*rd/SQ2,q1_target_var=-c.vac_v*rq/SQ2,saturation_fraction=clip,resonator_limit_fraction=hclip,integrator_limit_fraction=zclip,periodic_rms_a=per,pll_error_deg=float(np.mean(tr[:,8])),pll_hz=float(np.mean(tr[:,9])),measurement_start_s=start,measurement_end_s=end,**{k:bool(v) for k,v in flags.items()},combined_pass=bool(all(flags.values()))),hs
