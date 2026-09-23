"""Deterministic, reduced AC-stage model. NOT a product or PSIM model.

All plant dynamics are integrated, never synthesized from a desired THD.
Plant is an averaged voltage-source bridge with an assumed dead-time error.
No switched diode/Coss/DCM or low-frequency-leg commutation is represented.
"""
from dataclasses import dataclass, asdict
import math
import numpy as np
from scipy.linalg import expm
from numba import njit

FS = 32000.0
TS = 1.0 / FS
F0 = 50.0
W0 = 2 * math.pi * F0
LF_NOM = 0.0015
RF_NOM = 0.15

@dataclass(frozen=True)
class Case:
    case_id: str
    p: float = 700.0
    q: float = 0.0
    vrms: float = 230.0
    vdc: float = 400.0
    lf: float = LF_NOM
    lg: float = 0.0002
    rf: float = RF_NOM
    rg: float = 0.10
    dead_us: float = 1.0
    zero_a: float = 0.25
    v3: float = 0.0
    v5: float = 0.0
    offset_a: float = 0.0
    adc_step: float = 0.0
    dead_shape: int = 0  # 0=tanh, 1=piecewise-linear assumed alternative

@dataclass(frozen=True)
class Control:
    bw_hz: float = 300.0
    comp_gain: float = 0.0
    comp_width_a: float = 0.30
    estimated_dead_us: float = 1.0


def sogi_zoh(dt=TS):
    a = np.array([[-math.sqrt(2)*W0, -W0], [W0, 0.]])
    b = np.array([math.sqrt(2)*W0, 0.])
    phi = expm(a * dt)
    gamma = np.linalg.solve(a, (phi - np.eye(2)) @ b)
    return phi, gamma

@njit(cache=True)
def grid_v(t, vp, h3, h5):
    return vp*(math.sin(W0*t) + h3*math.sin(3*W0*t) + h5*math.sin(5*W0*t))

@njit(cache=True)
def dead_voltage(i, e, width, shape):
    if shape == 0:
        return e * math.tanh(i / width)
    return e * min(1.0, max(-1.0, i / width))

@njit(cache=True)
def rhs(t, i, u, L, R, vdc, vp, e, width, h3, h5, shape):
    vi = min(vdc, max(-vdc, u - dead_voltage(i, e, width, shape)))
    return (vi - R*i - grid_v(t, vp, h3, h5)) / L

@njit(cache=True)
def rk4_step(t, i, u, dt, L, R, vdc, vp, e, width, h3, h5, shape):
    k1 = rhs(t, i, u, L, R, vdc, vp, e, width, h3, h5, shape)
    k2 = rhs(t+dt/2, i+dt*k1/2, u, L, R, vdc, vp, e, width, h3, h5, shape)
    k3 = rhs(t+dt/2, i+dt*k2/2, u, L, R, vdc, vp, e, width, h3, h5, shape)
    k4 = rhs(t+dt, i+dt*k3, u, L, R, vdc, vp, e, width, h3, h5, shape)
    return i + dt*(k1+2*k2+2*k3+k4)/6

@njit(cache=True)
def _simulate(params, ctrl, phi, gamma, cycles, substeps, transient):
    # Stored channels at t_n, before plant integration to t_(n+1).
    # [t, grid voltage, true current, reference, applied command,
    #  generated command, saturation indicator, PLL phase error, dead-time loss]
    p,q,vrms,vdc,L,R,dead_us,zero,h3,h5,off,quant,shape = params
    bw,alpha,comp_width,estimate = ctrl
    n = int(cycles * FS / F0)
    out = np.zeros((n,9))
    vp = math.sqrt(2)*vrms
    edead = vdc * FS * dead_us * 1e-6
    eest = vdc * FS * estimate * 1e-6
    kp = 2*math.pi*bw*LF_NOM
    ki = 2*math.pi*bw*RF_NOM
    wnpll = 2*math.pi*20.0
    kppll = 2*0.7071067811865476*wnpll
    kipll = wnpll*wnpll
    # PLL initialized synchronized; this study does not evaluate PLL acquisition.
    theta = 0.0
    xp = 0.0; yp = -vp; xj = 0.0; yj = 0.0
    zpll=0.0; zd=0.0; zq=0.0; i=0.0; applied=0.0
    omega = W0
    dt = TS / substeps
    for k in range(n):
        t = k*TS
        vg = grid_v(t, vp, h3, h5)
        ps = p; qs = q
        if transient:
            # Fixed post-freeze step: half commands until t=0.3 s.
            if t < 0.3:
                ps = 0.5*p; qs = 0.5*q
        idref = math.sqrt(2)*ps/vrms
        iqref = -math.sqrt(2)*qs/vrms
        s=math.sin(theta); c=math.cos(theta)
        imeas=i+off
        if quant>0:
            imeas=round(imeas/quant)*quant
        idm=imeas*s-yj*c
        iqm=imeas*c+yj*s
        de=idref-idm; qe=iqref-iqm
        iref=idref*s+iqref*c
        diref=omega*(idref*c-iqref*s)
        raw=vg+RF_NOM*iref+LF_NOM*diref+kp*(iref-imeas)+zd*s+zq*c
        raw += alpha*eest*math.tanh(iref/comp_width)
        limit=0.95*vdc
        cmd=min(limit,max(-limit,raw))
        clipped=1.0 if abs(raw)>limit else 0.0
        # Conditional integration; no uncontrolled integrator growth at saturation.
        if clipped==0.0 or (iref-imeas)*raw<0.0:
            zd += TS*ki*de
            zq += TS*ki*qe
        out[k,0]=t; out[k,1]=vg; out[k,2]=i; out[k,3]=iref
        out[k,4]=applied; out[k,5]=cmd; out[k,6]=clipped
        out[k,7]=math.atan2(math.sin(theta-W0*t),math.cos(theta-W0*t))
        out[k,8]=dead_voltage(i,edead,zero,int(shape))
        # SOGI inputs are held during each control interval.
        xn=phi[0,0]*xj+phi[0,1]*yj+gamma[0]*imeas
        yn=phi[1,0]*xj+phi[1,1]*yj+gamma[1]*imeas
        xj=xn; yj=yn
        eqpll=(xp*c+yp*s)/vp
        zpll += kipll*eqpll*TS
        omega=min(2*math.pi*55,max(2*math.pi*45,W0+kppll*eqpll+zpll))
        theta=(theta+omega*TS) % (2*math.pi)
        xn=phi[0,0]*xp+phi[0,1]*yp+gamma[0]*vg
        yn=phi[1,0]*xp+phi[1,1]*yp+gamma[1]*vg
        xp=xn; yp=yn
        for j in range(substeps):
            i=rk4_step(t+j*dt,i,applied,dt,L,R,vdc,vp,edead,zero,h3,h5,int(shape))
        applied=cmd  # Explicit one-control-period command delay.
    return out


def simulate(case: Case, control: Control, cycles=40, substeps=16, transient=False):
    if cycles < 20 or substeps < 1:
        raise ValueError('At least 20 cycles and one integration substep required')
    if min(case.vrms,case.vdc,case.lf+case.lg,case.rf+case.rg,case.zero_a,control.comp_width_a) <= 0:
        raise ValueError('Nonpositive physical/regularization parameter')
    if case.p==0 and case.q==0:
        raise ValueError('Zero-current point excluded by protocol')
    if abs(case.p+1j*case.q)/case.vrms >= 35.0:
        raise ValueError('Reference point exceeds assumed current envelope')
    params=np.array([case.p,case.q,case.vrms,case.vdc,case.lf+case.lg,case.rf+case.rg,
        case.dead_us,case.zero_a,case.v3,case.v5,case.offset_a,case.adc_step,case.dead_shape],float)
    ctrl=np.array(list(asdict(control).values()),float)
    phi,gamma=sogi_zoh()
    out=_simulate(params,ctrl,phi,gamma,int(cycles),int(substeps),bool(transient))
    if not np.isfinite(out).all():
        raise FloatingPointError('Nonfinite simulation result')
    return out


def harmonic_metrics(wave, p_ref, q_ref, vrms):
    nwin=int(10*FS/F0)
    z=wave[-nwin:]
    i=z[:,2]; t=z[:,0]
    # Coherent 10-cycle rectangular window. FFT harmonic bins are 10*h.
    f=np.fft.rfft(i)/len(i)
    amps=np.sqrt(2)*np.abs(f[np.arange(1,41)*10])
    i1=float(amps[0]); ih=float(np.linalg.norm(amps[1:]))
    if i1<0.01:
        thd=float('inf')
    else:
        thd=100*ih/i1
    ip=2*np.mean(i*np.sin(W0*t))
    iq=2*np.mean(i*np.cos(W0*t))
    p=float(np.mean(i*z[:,1]))
    q=float(-vrms*iq/math.sqrt(2)) # fundamental Q only, defined convention
    sref=math.hypot(p_ref,q_ref)
    tol=max(20.,0.02*sref)
    ncy=int(FS/F0)
    periodic=float(np.sqrt(np.mean((i[-ncy:]-i[-2*ncy:-ncy])**2)))
    # Auxiliary values are diagnostic, NOT IEEE TRD or grid certification.
    dc=float(np.mean(i))
    residual=float(np.sqrt(max(0.,np.mean(i*i)-dc*dc-i1*i1)))
    peak=float(np.max(np.abs(i)))
    sat=float(np.mean(z[:,6]))
    guards=bool(abs(p-p_ref)<=tol and abs(q-q_ref)<=tol and peak<50 and sat<0.001)
    return dict(thd_pct=float(thd),i1_rms_a=i1,harmonic_rms_a=ih,
        i_rms_a=float(np.sqrt(np.mean(i*i))),i_dc_a=dc,p_w=p,q1_var=q,
        p_error_w=p-p_ref,q_error_var=q-q_ref,pq_tolerance=tol,peak_a=peak,
        saturation_fraction=sat,periodicity_rms_a=periodic,
        pll_error_deg=float(np.mean(z[:,7])*180/math.pi),
        residual_to_35a_pct=100*residual/35.,
        thd_pass=bool(thd<=5.0),guardrail_pass=guards,
        combined_pass=bool(thd<=5.0 and guards)), amps
