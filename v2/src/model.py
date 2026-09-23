"""V2 reference numerical AC-stage model, NOT PSIM/HW/product validation.

Averaged bidirectional voltage bridge, series L/R, current-dependent effective
commutation voltage error, sampled dq current control and SOGI PLL. Harmonic
feedback is causal; it does not invert or receive the plant's error parameters.
No hard-coded THD, output waveform injection, or post-hoc outcome scaling.
"""
from dataclasses import dataclass, asdict
import math
import numpy as np
from scipy.linalg import expm
from numba import njit
FS=32000.; TS=1/FS; F0=50.; W0=2*math.pi*F0
LN=1.5e-3; RN=.15
@dataclass(frozen=True)
class Case:
    case_id: str
    p: float=700.
    q: float=0.
    vrms: float=230.
    vdc: float=400.
    lf: float=LN
    lg: float=.2e-3
    rf: float=RN
    rg: float=.1
    dead_us: float=.2
    zero_a: float=.25
    v3: float=0.
    v5: float=0.
    offset_a: float=0.
    adc_step: float=0.
    shape: int=0
    bus_ripple: float=0.  # relative 100Hz amplitude; optional sensitivity only
@dataclass(frozen=True)
class Control:
    design_hz: float=500.
    k3: float=0.
    k5: float=0.
    res_width_hz: float=5.

def oscillator(w, damping, dt=TS):
    a=np.array([[-damping,-w],[w,0.]])
    b=np.array([damping,0.]); phi=expm(a*dt)
    return phi, np.linalg.solve(a,(phi-np.eye(2))@b)
@njit(cache=True)
def grid(t,vp,h3,h5):
    return vp*(math.sin(W0*t)+h3*math.sin(3*W0*t)+h5*math.sin(5*W0*t))
@njit(cache=True)
def loss(i,e,zero,shape):
    if shape==0: return e*math.tanh(i/zero)
    return e*min(1.,max(-1.,i/zero))
@njit(cache=True)
def rhs(t,i,u,L,R,vdc,vp,e,z,h3,h5,shape,ripple):
    bus=vdc*(1+ripple*math.sin(2*W0*t))
    vb=min(bus,max(-bus,u-loss(i,e*(bus/vdc),z,shape)))
    return (vb-R*i-grid(t,vp,h3,h5))/L
@njit(cache=True)
def _run(pa,ct,pp,gg,hp,hg,cycles,substeps,step):
    p,q,vr,vd,L,R,dead,z,h3,h5,off,quant,shape,ripple=pa
    design,k3,k5,rwidth=ct
    n=int(cycles*FS/F0); out=np.zeros((n,10)); vp=math.sqrt(2)*vr
    E=vd*FS*dead*1e-6
    kp=2*math.pi*design*LN; ki=2*math.pi*design*RN
    wn=2*math.pi*20; kppll=2/math.sqrt(2)*wn; kipll=wn*wn
    theta=0.; xp=0.; yp=-vp; xj=0.; yj=0.; zd=0.; zq=0.; zi=0.; i=0.; u=0.; omega=W0
    hx=np.zeros((2,2)); gains=np.array([k3,k5]); dt=TS/substeps
    for k in range(n):
        t=k*TS; vg=grid(t,vp,h3,h5)
        fac=.5 if step and t<.3 else 1.
        dr=math.sqrt(2)*p*fac/vr; qr=-math.sqrt(2)*q*fac/vr
        sn=math.sin(theta); cs=math.cos(theta)
        im=i+off
        if quant>0: im=round(im/quant)*quant
        dm=im*sn-yj*cs; qm=im*cs+yj*sn
        ir=dr*sn+qr*cs; err=ir-im
        uh=k3*hx[0,0]+k5*hx[1,0]
        raw=vg+RN*ir+LN*omega*(dr*cs-qr*sn)+kp*err+zd*sn+zq*cs+uh
        limit=.95*vd*(1+ripple*math.sin(2*W0*t))
        cmd=min(limit,max(-limit,raw)); sat=1.0 if abs(raw)>limit else 0.0
        if sat==0 or err*raw<0:
            zd+=TS*ki*(dr-dm); zq+=TS*ki*(qr-qm)
            for j in range(2):
                a=hp[j,0,0]*hx[j,0]+hp[j,0,1]*hx[j,1]+hg[j,0]*err
                b=hp[j,1,0]*hx[j,0]+hp[j,1,1]*hx[j,1]+hg[j,1]*err
                hx[j,0]=a; hx[j,1]=b
        out[k,0]=t; out[k,1]=vg; out[k,2]=i; out[k,3]=ir; out[k,4]=u
        out[k,5]=cmd; out[k,6]=sat; out[k,7]=math.atan2(math.sin(theta-W0*t),math.cos(theta-W0*t))
        out[k,8]=loss(i,E,z,int(shape)); out[k,9]=uh
        a=pp[0,0]*xj+pp[0,1]*yj+gg[0]*im; b=pp[1,0]*xj+pp[1,1]*yj+gg[1]*im
        xj=a; yj=b
        eq=(xp*cs+yp*sn)/vp; zi+=kipll*eq*TS
        omega=min(2*math.pi*55,max(2*math.pi*45,W0+kppll*eq+zi))
        theta=(theta+omega*TS)%(2*math.pi)
        a=pp[0,0]*xp+pp[0,1]*yp+gg[0]*vg; b=pp[1,0]*xp+pp[1,1]*yp+gg[1]*vg
        xp=a; yp=b
        for j in range(substeps):
            tt=t+j*dt
            a=rhs(tt,i,u,L,R,vd,vp,E,z,h3,h5,int(shape),ripple)
            b=rhs(tt+dt/2,i+dt*a/2,u,L,R,vd,vp,E,z,h3,h5,int(shape),ripple)
            c=rhs(tt+dt/2,i+dt*b/2,u,L,R,vd,vp,E,z,h3,h5,int(shape),ripple)
            d=rhs(tt+dt,i+dt*c,u,L,R,vd,vp,E,z,h3,h5,int(shape),ripple)
            i+=dt*(a+2*b+2*c+d)/6
        u=cmd
    return out

def simulate(case,control=Control(),cycles=40,substeps=4,step=False):
    if cycles<20 or substeps<1 or min(case.vrms,case.vdc,case.lf,case.lg,case.rf,case.rg,case.zero_a)<=0:
        raise ValueError('Invalid solver or physical parameters')
    if math.hypot(case.p,case.q)==0: raise ValueError('THD undefined at zero reference current')
    if math.hypot(case.p,case.q)/case.vrms>35: raise ValueError('Outside reference 35 Arms envelope')
    if min(control.k3,control.k5,case.dead_us)<0 or control.design_hz<=0 or control.res_width_hz<=0:
        raise ValueError('Invalid gain or dead time')
    pa=np.array([case.p,case.q,case.vrms,case.vdc,case.lf+case.lg,case.rf+case.rg,case.dead_us,case.zero_a,case.v3,case.v5,case.offset_a,case.adc_step,case.shape,case.bus_ripple])
    pp,gg=oscillator(W0,math.sqrt(2)*W0)
    hh=[oscillator(h*W0,2*2*math.pi*control.res_width_hz) for h in [3,5]]
    out=_run(pa,np.array(list(asdict(control).values())),pp,gg,np.array([x[0] for x in hh]),np.array([x[1] for x in hh]),int(cycles),int(substeps),bool(step))
    if not np.isfinite(out).all(): raise FloatingPointError('Non-finite simulation')
    return out

def metrics(wave,case,limit=5.,window_cycles=10):
    z=wave[-int(window_cycles*FS/F0):]; i=z[:,2]; t=z[:,0]
    coeff=np.fft.rfft(i)/len(i)
    harm=np.sqrt(2)*np.abs(coeff[np.arange(1,41)*window_cycles])
    if harm[0]<.01: raise ValueError('Fundamental too small')
    thd=100*float(np.linalg.norm(harm[1:])/harm[0])
    p=float(np.mean(i*z[:,1])); q=-case.vrms*math.sqrt(2)*float(np.mean(i*np.cos(W0*t)))
    ip=math.sqrt(2)*float(np.mean(i*np.sin(W0*t)))
    sref=math.hypot(case.p,case.q); tol=max(10.,.02*sref)
    sat=float(np.mean(z[:,6])); pk=float(np.max(np.abs(i))); dc=float(np.mean(i))
    periodic=float(np.sqrt(np.mean((i[-640:]-i[-1280:-640])**2)))
    err=max(abs(p-case.p),abs(q-case.q)); irms=float(np.sqrt(np.mean(i*i)))
    guard=err<=tol and pk<50 and sat<.001 and periodic<max(.002,.001*harm[0]) and abs(dc)<.05
    m=dict(case_id=case.case_id,p_ref=case.p,q_ref=case.q,s_va=sref,angle_deg=math.degrees(math.atan2(case.q,case.p)),vrms=case.vrms,
      thd_pct=thd,i1_rms_a=float(harm[0]),ih_rms_a=float(np.linalg.norm(harm[1:])),irms_a=irms,dc_a=dc,peak_a=pk,
      p_w=p,q1_var=q,p_error_w=p-case.p,q_error_var=q-case.q,pq_tolerance=tol,saturation_fraction=sat,periodicity_rms_a=periodic,
      pll_error_deg=float(np.mean(z[:,7]))*180/math.pi,thd_pass=thd<=limit,guard_pass=bool(guard),combined_pass=bool(thd<=limit and guard))
    return m,harm
