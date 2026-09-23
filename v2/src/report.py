"""Build a self-contained HTML slide report from stored results only."""
from pathlib import Path
import io,json,html
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def table(headers,rows):
    return '<table><thead><tr>'+''.join(f'<th>{html.escape(str(x))}</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join(f'<td>{x}</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table>'
def para(text):return '<p>'+text+'</p>'
def box(text,kind='note'):return f'<div class="{kind}">{text}</div>'
def split(a,b):return f'<div class="columns"><div>{a}</div><div>{b}</div></div>'
def f(x,n=2): return f'{x:.{n}f}'
def build(root):
    root=Path(root); r=root/'results'; output=root/'report';output.mkdir(exist_ok=True)
    def load(n):return pd.read_csv(r/f'{n}.csv')
    s=json.loads((r/'summary.json').read_text());cfg=json.loads((root/'study_config.json').read_text())
    refs=json.loads((root/'evidence/public_references.json').read_text());comp=json.loads((root/'docs/reference_cases.json').read_text())
    from .audit import audit
    audit(root)
    figs={}
    def fig(name,draw):
        ff,ax=plt.subplots(figsize=(8.2,4.2));draw(ax);ff.tight_layout()
        buf=io.StringIO();ff.savefig(buf,format='svg');plt.close(ff)
        val=buf.getvalue();val=val[val.index('<svg'):]
        (output/(name+'.svg')).write_text(val)
        figs[name]=f'<div class="plot">{val}</div>'
    b=load('baseline');a=load('improved');bb=load('baseline_by_load');aa=load('improved_by_load')
    def loadplot(ax):
        for df,label in [(bb,'Baseline'),(aa,'Selected control')]:
            ax.errorbar(df.s_round,df.mean_thd,yerr=[df.mean_thd-df.min_thd,df.max_thd-df.mean_thd],marker='o',capsize=5,label=label)
        ax.axhline(5,linestyle='--',label='Research limit 5%');ax.set(xlabel='Apparent power S (VA)',ylabel='THD 2:40 (%)',ylim=(0,9));ax.legend()
    fig('01_low_load',loadplot)
    rb=load('sentinel_baseline_by_load');ra=load('sentinel_improved_by_load')
    def sentplot(ax):
        for d,l in [(rb,'Baseline'),(ra,'Selected')]:ax.plot(d.s_round,d.mean_thd,'o-',label=l)
        ax.set(xlabel='S (VA)',ylabel='Mean THD (%)');ax.legend()
    fig('02_sentinel',sentplot)
    j=int(b.thd_pct.idxmax()); cid=b.iloc[j].case_id
    with np.load(root/'data/baseline.npz') as z:wb=z['wave'][j];hb=z['harmonics'][j]
    with np.load(root/'data/improved.npz') as z:wa=z['wave'][j];ha=z['harmonics'][j]
    def waveplot(ax):
        n=1280;tm=(wb[-n:,0]-wb[-n,0])*1000
        ax.plot(tm,wb[-n:,3],linestyle=':',label='Reference');ax.plot(tm,wb[-n:,2],label='Baseline');ax.plot(tm,wa[-n:,2],label='Selected')
        ax.set(xlabel='Time (ms)',ylabel='Grid current (A)',title=f'Primary case {cid}: same plant and reference');ax.legend()
    fig('03_waveform',waveplot)
    def harmonicplot(ax):
        hs=np.array([3,5,7,9,11,13]);ix=np.arange(len(hs))
        ax.bar(ix-.18,100*hb[hs-1]/hb[0],.36,label='Baseline');ax.bar(ix+.18,100*ha[hs-1]/ha[0],.36,label='Selected')
        ax.set_xticks(ix,hs);ax.set(xlabel='Harmonic order',ylabel='Harmonic / I1 (%)');ax.legend()
    fig('04_harmonics',harmonicplot)
    d=load('doe_candidates')
    def doeplot(ax):
        for hz,g in d.groupby('ctl_design_hz'):
            g=g.sort_values(['ctl_k3','ctl_k5']);ax.plot(np.arange(len(g)),g.max_thd,'o-',label=f'f_design={hz:g}Hz')
        ax.set_xticks(range(9),['0/0','0/2','0/5','2/0','2/2','2/5','5/0','5/2','5/5']);ax.set(xlabel='K3 / K5 (ohm)',ylabel='Worst training THD (%)');ax.legend()
    fig('05_doe',doeplot)
    ab=load('ablation').groupby(['ctl_design_hz','ctl_k3','ctl_k5']).thd_pct.mean().reset_index()
    def abplot(ax):
        ax.barh(np.arange(len(ab)),ab.thd_pct);ax.set_yticks(range(len(ab)),[f'{row.ctl_design_hz:g} Hz | {row.ctl_k3:g}/{row.ctl_k5:g} ohm' for row in ab.itertuples()]);ax.set(xlabel='Mean THD (%)',ylabel='f_design | K3/K5')
    fig('06_ablation',abplot)
    hbefore=load('holdout_baseline');hafter=load('holdout_improved')
    def holdplot(ax):
        ax.scatter(hbefore.thd_pct,hafter.thd_pct,s=24);ax.plot([0,10],[0,10],linestyle=':',label='Equal THD');ax.axhline(5,linestyle='--');ax.axvline(5,linestyle='--');ax.set(xlim=(0,10),ylim=(0,10),xlabel='Baseline THD (%)',ylabel='Selected THD (%)');ax.legend()
    fig('07_stress',holdplot)
    ph=load('phase');pv=ph[(ph.s_va.round()==700)]
    def phaseplot(ax):
        for k,g in pv.groupby('ctl_design_hz'):
            g=g.sort_values('angle_deg');ax.plot(g.angle_deg,g.thd_pct,'o-',label=f'{k:g} Hz')
        ax.set(xlabel='Current lag angle at fixed S=700VA (degree)',ylabel='THD (%)');ax.legend()
    fig('08_phase',phaseplot)
    sf=load('sentinel_failures');ss=load('sentinel_improved')
    if len(sf):
        row=sf.iloc[0]
        with np.load(root/'data/sentinel_improved.npz') as z:w=z['wave'][int(row.wave_index)]
        def saturationplot(ax):
            z=w[-1280:];tt=(z[:,0]-z[0,0])*1000;ax.plot(tt,z[:,5],label='Limited voltage command');ax.plot(tt,z[:,1],label='Grid voltage');ax.axhline(380,linestyle='--');ax.axhline(-380,linestyle='--');ax.set(xlabel='Time (ms)',ylabel='Voltage (V)',title=f'{row.case_id}: command saturates despite low THD');ax.legend()
        fig('09_saturation',saturationplot)
    td=load('transient_diagnostics')
    def transplot(ax):
        for hz,g in td.groupby('design_hz'):ax.plot(g.case_id,g.settling_cycle_metric_ms,'o-',label=f'{hz:g} Hz')
        ax.set(ylabel='Cycle-RMS diagnostic settling (ms)',xlabel='Step scenario');ax.legend()
    fig('10_transient',transplot)
    ps=load('plant_sensitivity');ps=ps[ps.case_id.str.startswith('dead_us')].copy();ps['dt']=ps.case_id.str.split(':').str[1].astype(float)*1000
    fig('11_sensitivity',lambda ax:(ax.plot(ps.dt,ps.thd_pct,'o-'),ax.set(xlabel='Assumed effective commutation time (ns)',ylabel='Baseline THD at S=700VA (%)')))
    slides=[]
    def slide(stage,title,body,source='',claim=''):
        slides.append(dict(stage=stage,title=title,body=body,source=source,claim=claim))
    bp=s['baseline'];ap=s['improved'];hp=s['holdout_improved'];sp=s['sentinel_improved']
    slide('SUMMARY','저부하 THD 개선 | 재수행 v2',
        '<div class="hero">'+f'{bp["mean_thd"]:.2f}% <span>→</span> {ap["mean_thd"]:.2f}%'+'</div>'+para('공개 레퍼런스로 초기 수치의 규모를 점검하고, 제어 모델·현수준·DOE·별도 검증을 다시 수행했다.')+
        table(['주 시험군','개선 전','개선 후'],[['평균 THD',f(bp['mean_thd'])+'%',f(ap['mean_thd'])+'%'],['최대 THD',f(bp['max_thd'])+'%',f(ap['max_thd'])+'%'],['종합 통과 / 45점','10 / 45','45 / 45']])+box('이는 7 kVA급 참조 AC단의 <b>저부하 45개 수치 시험점</b> 결과다. 실제 제품 실측·PSIM 결과·업계 평균·BB 승인 결과가 아니다.','warn'), 'results/summary.json; 2026-09-23')
    slide('D · RESTART','v1의 숫자를 줄인 것이 아니라 모델을 바꿨다',split(
        para('<b>v1 문제</b><br>실제 제품에 대응되지 않은 1 μs 등가 오차와 초기 제어를 사용했다. plant 오차와 역보상 함수가 거의 일치하여 개선 효과가 과대해석될 여지가 컸다.')+para('v1 평균 18.950% → 0.449%는 제품 baseline/성과 근거에서 제외한다. 과거 실행 기록은 삭제하지 않는다.'),
        para('<b>v2 수정</b><br>200 ns 규모의 등가 commutation 가정, 500 Hz 설계상수의 기본 제어, 낮은 S에 한정한 주 시험군, 오차 피드백 기반 3·5차 보상으로 재구성했다.')+box('목표 THD를 파형에 직접 주입하거나 결과에 보정계수를 곱하지 않았다.')),
        'docs/00_protocol.md; evidence/preliminary_*.json','높은 THD 자체가 항상 고장이라는 앞선 단정도 철회한다. 극저부하 공개 사례에는 약18%도 존재한다[R2].')
    slide('D · EVIDENCE','“평균적인 THD” 하나로 제품군을 대표할 수 없다',
        table(['공식 근거','운전·측정 조건','확인한 THD'],[
         ['R1 TI 7.4 kW OBC','240 Vac → 350 Vdc, 냉각수20℃; 전체 충전 시스템','1.5 kW 초과에서 &lt;5%'],
         ['R3 TI 1 kW PFC','230 Vac, PFC단; DC 출력 234.54 W / 992.43 W','4.76% / 1.38%'],
         ['R2 TI 3.3 kW PFC','230 V/50 Hz, 부하별 그래프','저부하에서 상승, 극저부하 약18%'],
         ['R4 ST 3.6 kW PFC','230 V/50 Hz, full load','minimum 3.5%; 별도 설명은10%부하5%max']])+box('제조사·토폴로지·부하율·방향이 다른 값을 합쳐 “업계 평균5~8%”라고 하지 않는다. 위 근거는 대부분 AC→DC 측정이며 V2G Q 운전 검증이 아니다.','warn'),
        'R1 p81 Fig5-48; R2 p76 Fig3-80; R3 p53 Table3-5; R4 official solution page')
    slide('D · SCOPE','선정한 초기 수준: 저부하 취약영역 약5~8%',split(
        table(['영역','모델 baseline 결과'],[['525 VA (7.5%)',f(bb.iloc[0].mean_thd)+'% 평균'],['700 VA (10%)',f(bb.iloc[1].mean_thd)+'% 평균'],['875 VA (12.5%)',f(bb.iloc[2].mean_thd)+'% 평균'],['1.4~7 kVA 확인군','평균 '+f(s['sentinel_baseline']['mean_thd'])+'%']]),
        para('사용자 제공 “약5~8%”는 참고 현수준 정보다. 운전점별 원시 데이터가 없어 실측 calibration에 사용했다고 주장하지 않는다.')+para('공개 자료는 저부하/중고부하 수준과 경향을 점검하는 근거로 사용했다. 45점의 초기 평균은 <b>'+f(bp['mean_thd'])+'%</b>이며 결과를 이 값에 맞춰 후처리하지 않았다.')+box('이 선택은 비교 가능한 참조 연구 범위 설정이지 해당 OBCM 파라미터 식별 완료가 아니다.')),
        'results/baseline_by_load.csv; evidence/public_references.json')
    slide('D · PROJECT Y','Project Y와 판정의 분모를 고정했다',
        '<div class="equation">Y = 100 × N(THD≤5%) / 45</div>'+para('별도 채택 조건으로 Guard를 평가하고 종합 통과율도 분리해 보고한다. 평균·최대 THD와 harmonic RMS 전류를 함께 보존한다. 주 시험군에서는 THD-only와 종합 통과 결과가 같았다.')+
        table(['항목','고정한 정의'],[['THD','기본파 RMS I1 대비 2~40차 RMS 제곱합의 제곱근'],['측정 창','50 Hz 정수10주기; 32 kSa/s; DC 제외'],['주 연구 목표','45점 THD 통과율 ≥95%; Guard는 모두 통과'],['한계','스위칭리플·인증 측정대역 전체가 아닌 line-harmonic 지표']])+box('THD≤5%는 연구용 잠정 기준이다. 실제 고객/표준 판정값으로 확인된 것이 아니다.','warn'), 'study_config.json; src/model.py::metrics')
    slide('D · TEST MATRIX','P가 아니라 S와 위상을 분리했다',
        '<div class="equation">P = S cosφ &nbsp;&nbsp; Q = S sinφ &nbsp;&nbsp; I1 ≈ S / Vrms</div>'+table(['시험군','조건','개수'],[
         ['튜닝','S 600/800/1000 VA; φ−45/0/+45°; 230 V','9점'],
         ['주 평가','S 525/700/875 VA; φ−60/−30/0/+30/+60°;207/230/253 V','45점'],
         ['중고부하 확인','S 1.4/2.8/5.6/7 kVA; φ−45/0/+45°;207/230/253 V','36점'],
         ['별도 스트레스','S450~1200 VA;φ±80°; 부품·전원·오차형상 변화','72점']])+box('Q가 크면 P가 작아도 전류는 작지 않을 수 있다. 튜닝9점과 주평가45점은 겹치지 않으며, 시험군별 분모를 합치지 않는다.'),
        'results/*_cases.csv; docs/00_protocol.md')
    slide('M · MODEL','전력단과 제어기를 실제로 시간 적분했다',split(
        '<div class="equation">LΣ di/dt = vbridge − vg − RΣ i</div>'+para('32 kHz 이산 dq 전류 제어 + SOGI-PLL → 1 sample command 지연 → 평균 voltage bridge → series L/R → grid current.')+para('Nominal: Lf=1.5 mH, Lg=0.2 mH, Rf=0.15 Ω, Rg=0.10 Ω, DC400 V, AC230 V/50 Hz.'),
        '<div class="equation">ec(i) = E tanh(i/I0)<br>E = Vdc fs teff = 2.56 V</div>'+para('teff=200 ns, I0=0.25 A는 명시적 가정이다. 특정 GaN 레퍼런스의20~200 ns 설정[R2 p63]은 규모 참고일 뿐 해당 제품값이 아니다.')+box('Generic averaged AC단이다. 실제 LF-leg commutation, DCM, Coss, DC-link/CLLC/EMI필터는 제외했다.','warn')),
        'src/model.py; docs/01_model.md')
    slide('M · VERIFICATION','Gage R&R 대신 구현과 수치오차를 확인했다',
        table(['검사','확인하는 것'],[['알려진3/5차 신호 → THD5%','측정 연산의 정확성'],['DC offset 분리','DC를THD고조파로 잘못 합산하지 않음'],['이상 오차0 조건','기본 제어 및 feed-forward 일관성'],['RK4 substeps 2/4/8/16','적분시간간격 수렴'],['FFT vs 직접 삼각함수 투영','독립 방식으로 harmonic 계산 교차검증'],['40주기 vs80주기','측정 시점 정착성 확인']])+box('동일 입력의 동일 결과를 독립 표본으로 세거나, 임의 noise로 p-value·Cpk·Gage R&R을 만들지 않았다. 수치 검증은 물리적 모델 검증을 대신하지 않는다.'),
        'results/verification.json; convergence.csv; final_numerical_crosschecks.csv')
    slide('M · BASELINE','초기 문제는 정상 변환 중 저부하 전류 왜곡이다',split(figs['01_low_load'],
        table(['범위','초기 THD'],[['전체45점 평균',f(bp['mean_thd'])+'%'],['최소 / 최대',f(bp['min_thd'])+' / '+f(bp['max_thd'])+'%'],['THD-only 통과','10 / 45'],['Guard 위반','0 / 45']])+para('동일한 plant에서 전류가 작을수록 등가 비선형 전압오차의 영향이 커지는 수치 결과다. 그래프의 오차막대는 시험조건의 min/max이며 통계 신뢰구간이 아니다.')),
        'results/baseline.csv; baseline_by_load.csv')
    slide('A · CAUSAL HYPOTHESES','plant 가정과 변경할 제어 인자를 구분했다',split(
        table(['구분','취급'],[['Lf/Lg/R·등가전압오차','원인 가정과 민감도 점검, 개선 전후 고정'],['S·Q·Vac','외부 시험조건, 합격을 위해 이동하지 않음'],['기본 전류제어 이득','개선 가능한 변수 f_design'],['3/5차 피드백 이득','개선 가능한 변수 K3/K5'],['DC-link/CLLC','미모델링, 개선된 것으로 주장하지 않음']]),
        figs['11_sensitivity']), 'results/plant_sensitivity.csv; src/model.py',
        '민감도 분석은 가정한 오차가 모델 안에서 영향을 준다는 근거다. 실제 제품의 치명 원인이 동일하다는 증명은 아니다.')
    slide('I · CONTROL','정확한 역보상 대신 전류오차 피드백을 사용했다',
        '<div class="equation">C<sub>h</sub>(s) = K<sub>h</sub> · 2ω<sub>c</sub>s / [s² + 2ω<sub>c</sub>s + (hω₀)²]<br>h ∈ {3,5}, &nbsp; ω<sub>c</sub> = 2π·5 rad/s</div>'+split(
        para('기본 전류제어의 f_design과 3/5차 resonator gain을 조합한다. 입력은 측정 전류와 reference의 오차이며 plant의 dead time·I0·shape를 제어기에 전달하지 않는다.')+para('Limiter와 conditional integration을 적용하고, 실제 전압 포화는 결과의 Guard에 별도로 반영한다.'),
        table(['후보 인자','수준'],[['f_design','500 / 650 / 800 Hz'],['K3','0 / 2 / 5 Ω'],['K5','0 / 2 / 5 Ω'],['실험 규모','27조합 × 9튜닝점 =243회']])),'src/model.py::Control, oscillator, _run')
    slide('A/I · DOE','후보선정은 튜닝군의 성능만 사용했다',split(figs['05_doe'],
        para('<b>선정 순서</b><br>Guard 실패 수 → 최대THD → 평균THD → 이득합.')+
        table(['선정값','결과'],[['f_design','800 Hz'],['K3 / K5','5 / 5 Ω'],['resonator width','5 Hz']])+box('세 인자가 탐색 범위 상단에 있다. 검토한 이산 후보 중 최선이며 전역 최적점이나 실제 폐루프 대역폭800 Hz를 증명한 것이 아니다.','warn')),
        'results/doe_candidates.csv; selected_control.json')
    slide('A/I · ABLATION','제어 이득 변경과 고조파 피드백 효과를 분리했다',split(figs['06_ablation'],
        para('Nominal 9개 진단점에서 500 Hz 기본안, 이득만 증가한 안, 3차만/5차만/둘 다 추가한 안, 최종 조합을 비교했다.')+para('이득 증가만으로도 개선되는 조건이 있다. 따라서 고조파 피드백만이 유일한 해결책이라고 결론 내리지 않는다.')+box('3/5차 피드백은 추가 여유 확보에 기여했다. gain-only와의 비용·CPU·실측 안정도 비교는 제품 설계 단계에서 별도 판단해야 한다.')),
        'results/ablation.csv; 6개 설정×9개 조건=54회')
    slide('I · WAVEFORMS','개선 전후 파형은 같은 조건에서 직접 계산했다',figs['03_waveform']+box('출력 current waveform을 rescale하거나 정현파를 합성해 개선 데이터로 사용하지 않았다. 같은 reference·plant에서 제어만 변경했다.'),
        f'data/baseline.npz & improved.npz; primary {cid}')
    slide('I · HARMONICS','왜곡 감소가 어느 차수에서 일어났는지 확인했다',split(figs['04_harmonics'],
        para('3/5차 피드백을 사용했다고 3/5차 외 성분이 사라지지는 않는다. 비선형 plant 및 제어 이득 변경에 의해 고차 성분도 달라질 수 있다.')+para('THD는2~40차 전체로 계산하며, 일부 보기 좋은 차수만 골라 합격 여부를 판단하지 않는다.')+box('모든 run에 I1~I40과 원시 파형을 함께 저장했다.')),
        f'data/*npz::harmonics; {cid}')
    slide('V · MAIN RESULT','주45점: 평균5.96% → 2.80%',
        table(['S / 기준정격비','시험수','평균 THD 전 → 후','최대 THD 전 → 후','종합 통과 전 → 후'],[
          [f'{int(x.s_round)} VA / {x.s_round/70:g}%',15,f'{x.mean_thd:.3f}% → {y.mean_thd:.3f}%',f'{x.max_thd:.3f}% → {y.max_thd:.3f}%',f'{int(x.passes)}/15 → {int(y.passes)}/15'] for x,y in zip(bb.itertuples(),aa.itertuples())])+
        '<div class="stats"><div><b>3.161%p</b><span>평균THD 감소</span></div><div><b>22.22 →100%</b><span>주 시험 종합 통과율</span></div><div><b>0 /45</b><span>개선 후 Guard 실패</span></div></div>'+box('5%를 간신히 통과시키도록 목표값을 정한 결과가 아니다. 최초 고정 45점 전체의 계산 결과이며 튜닝 9점은 포함되지 않았다.'),
        'results/paired_main.csv; summary.json')
    slide('V · STRESS PLAN','독립 시험조건에서 모델 오차까지 바꿨다',
        table(['변수','사전에 정한 스트레스 범위'],[['부하·위상','450~1200 VA, −80~+80°'],['전원','207~253 Vac,390~410 Vdc,DC100Hz ripple0~1.5%'],['소자·계통','Lf±20%,Lg0.05~0.8 mH,각저항변화'],['commutation','120~280 ns,전류전환폭0.15~0.40 A'],['계측·입력왜곡','offset±20mA,step5mA,V3±1%,V5±0.5%'],['모델 형상','tanh/선형포화 절반씩, seed2026092302']])+box('72점은 정해진 가정으로 생성한 stress set이다. 실제 공차 확률분포, 양산 표본, 제품 불량률의 추정이 아니다.','warn'),
        'results/holdout_cases.csv; docs/00_protocol.md')
    slide('V · STRESS RESULT','별도72점: 최대THD4.47%, 종합72/72 통과',split(figs['07_stress'],
        table(['항목','전 → 후'],[['평균 THD',f(s['holdout_baseline']['mean_thd'])+' → '+f(hp['mean_thd'])+'%'],['최대 THD',f(s['holdout_baseline']['max_thd'])+' → '+f(hp['max_thd'])+'%'],['THD 통과','42/72 →72/72'],['종합 통과','42/72 →72/72']])+para('선정한 제어값을 변경하지 않고 검증했다. 모두 통과했다고 실패를 인위적으로 추가하지 않았다.')+box('동일 계열 평균모델의 범위 검증이다. 다른 시뮬레이터나 HW를 사용한 독립 물리 검증은 아니다.')),
        'results/holdout_baseline.csv; holdout_improved.csv')
    slide('V · HIGHER LOAD','중고부하는 별도 확인, 주성과 분모와 분리',split(figs['02_sentinel'],
        table(['결과 /36점','전 → 후'],[['평균 THD',f(s['sentinel_baseline']['mean_thd'])+' → '+f(sp['mean_thd'])+'%'],['THD 통과','36/36 →36/36'],['종합 통과','35/36 →35/36']])+box('<b>S035는 전후 모두 전압 포화 실패.</b><br>THD 통과만으로 전체 운전영역 적합을 선언하지 않는다.','warn')),
        'results/sentinel_baseline.csv; sentinel_improved.csv')
    slide('V · FAILURE','남은 실패: 7 kVA·253 Vac·+45°의 전압 여유',split(figs.get('09_saturation',''),
        para('S035: P=Q≈4.950 kW/kvar, DC400 V. 정상상태 command 포화비율≈9.06%로 잠정 Guard0.1% 미만을 위반한다.')+para('THD는 개선 전≈0.889%, 후≈0.625%이지만 종합 실패다. 이 조건은 최초36점 분모에서 제거하지 않았다.')+box('동일 조건의 실패가 개선 전에도 있으므로 개선 로직이 새로 만든 문제라고 보지는 않는다. 그렇다고 최종 설정이 전체7kVA영역에 적합한 것도 아니다.','warn')),
        'results/sentinel_failures.csv; data/sentinel_*.npz')
    slide('V · Q LIMITATION','실제 Q 운전의 고유 원인은 아직 증명하지 못했다',split(figs['08_phase'],
        para('S=700 VA를 고정하고 φ=−90~+90°를 바꿀 때 baseline THD 변화폭은 약0.0024%p로 매우 작다.')+para('이 모델의 주 왜곡은 저전류와 commutation 가정에 좌우된다. 실제 totem-pole의 전압·전류 영교차 불일치와LF-leg제어 메커니즘은 포함하지 않았다.')+box('따라서 이번 성과는 <b>Q를 포함한 수치 시험군에서 저부하 전류 THD 개선</b>이다. “실제 무효전력 고유 문제 해결”이라는 결론은 내리지 않는다.','warn')),
        'results/phase.csv; phase_invariance.csv; docs/02_logic_review.md')
    slide('V · TRANSIENT','과도응답은 별도 진단값으로 남겼다',split(figs['10_transient'],
        para('t=0.3s에서 전류 reference를50%→100%로 변경했다. 최종 주기파형 대비1주기RMS 편차가 I1의2% 안에 계속 머무르는 시간을 계산했다.')+
        table(['조건','전 → 후 [ms]'],[[x.case_id,f'{x.settling_cycle_metric_ms:.2f} → {y.settling_cycle_metric_ms:.2f}'] for x,y in zip(td.iloc[:3].itertuples(),td.iloc[3:].itertuples())])+box('이는 선정 후 정의한 진단 지표다. OEM response-time 시험이나 전체 보호/안정도 합격 판정으로 사용하지 않는다.')),
        'results/transient_diagnostics.csv; data/transient.npz')
    raw=json.loads((r/'raw_audit.json').read_text());vr=json.loads((r/'verification.json').read_text())
    test=json.loads((r/'test_report.json').read_text()) if (r/'test_report.json').exists() else {'tests_run':0,'passed':False}
    slide('V · AUDIT','663개 계산을 원시 파형에서 다시 확인했다',
        table(['검증','실제 결과'],[['성능 run 수',s['total_performance_runs']],['원시측정구간 →THD 재계산',f"{raw[0]['n']}개 /최대차 {raw[0]['max_thd_error_pp']:.3g}%p"],['최종 시간간격·duration 검증',f"최대THD차 {raw[1]['max_delta_pp']:.6f}%p"],['해석 구현 기본검사',f'{len(vr)}개 통과'],['자동 test suite',f"{test['tests_run']}개 / {'PASS' if test['passed'] else 'checks 실행 전'}"]])+box('해시와 재계산 검사는 원자료-보고서 연결을 검증한다. 실제 물리 정확도를 보장하는 인증 표시는 아니다.'),
        'results/raw_audit.json; test_report.json; manifest.json')
    for start,end in [(0,6),(6,11)]:
        slide('REVIEW · PRECEDENTS',f'기존 BB 보고서 비교 {start+1}~{end} /11',
            table(['사례 /페이지','원자료에서 참고한 점','v2 적용 또는 남은 한계'],[[f"{c['topic']}<br><small>{c['slides']}장; p{c['pages']}</small>",c['observed'],c['apply']+'<br><small>'+c['gap']+'</small>'] for c in comp[start:end]]),
            'docs/03_reference_comparison.md; reference_cases.json; 기존 전체230장',
            '선례가 있다는 것과 본 과제가 사내 심사에서 승인된다는 것은 다르다. 생산형 MSA를 수치모델에 억지로 복사하지 않았다.')
    slide('REVIEW · EVIDENCE GAP','논리적으로 닫힌 부분과 열린 부분을 구분했다',
        table(['닫힌 비교','아직 없는 근거'],[['고정한 45점에서 동일 plant의 제어 전후 비교','이 plant가 사용자 제품을 대표한다는 실측 검증'],['튜닝점과 평가점을 분리한 이산 후보 선정','연속 영역 전역 최적성·안정 여유·MCU 실시간 검증'],['가정한 72 stress 조건 통과','실제 분포의 수율/불량 확률'],['THD·P/Q·포화·전류·수렴검사','효율·열·EMI·보호·DC-link/CLLC상호작용'],['11사례와 구성·증거 수준 비교','사내 MBB 승인·재무성과']])+box('보고서에서 제약을 밝힌다고 물리 검증 공백이 사라지지는 않는다. 현재 채택 대상은 수치 설계 후보와 시험자산이며 제품 성능 보증이 아니다.','warn'),
        'docs/02_logic_review.md')
    slide('C · CONTROL','결과보다 재실행 가능한 시험자산을 관리한다',split(
        table(['산출물','위치'],[['실행 모델·study','src/'],['조건·해시·선정기록','results/'],['663개 원시측정구간','data/*.npz'],['근거·탐색이력','evidence/'],['가정·기술한계·11사례비교','docs/'],['수치 검증·재계산','tests/; src/checks.py']]),
        '<pre>python -m pip install -r requirements.txt\npython -m src.study\npython -m src.checks</pre>'+para('해석값은 실측값과 분리하고, 모델 수정 시 전체 행렬을 다시 실행한다. 실제 SW나 회로값 입수 후 제품 대응성을 검증하는 단계를 추가한다.')+box('v1은 이력으로 보존하되 현재 제품 baseline의 근거로 쓰지 않는다.')),
        'README.md; requirements.txt; results/manifest.json')
    slide('CONCLUSION','현실적인 초기 규모에서 개선 후보를 확보했다',
        '<div class="hero small">5.96% → 2.80%<br><em>45점의 참조 수치 연구</em></div>'+para('저부하 7.5~12.5% S 영역의 초기 THD를 4.39~7.80%로 확인하고, 이산 후보 비교를 통해 평균 3.16%p 낮췄다. 별도 72점도 모두 통과했다.')+
        box('남은 기술 판단: S035의 전압 여유 문제, 실제 제품에 대한 calibration/validation, Q 고유 왜곡 메커니즘. 이 세 가지를 해결한 것처럼 표현하지 않는다.','warn')+
        para('<b>권고:</b> v2를 수치 연구와 발표 구조의 기준으로 사용하고, 제품 최종 완료보고서에는 실제 사양과 물리 검증 근거를 추가한다.'),
        'results/summary.json; docs/02_logic_review.md')
    slide('APPENDIX · SOURCES','공식 자료와 출처의 적용 범위',
        ''.join(f'<p class="reference"><b>{x["id"]} {html.escape(x["manufacturer"])} · {html.escape(x["design"])}</b><br><a href="{html.escape(x["url"])}">{html.escape(x.get("document",x["url"]))}</a> · {html.escape(str(x.get("location","official solution/tool page")))}<br><small>{html.escape(x["evidence"])}</small></p>' for x in refs),
        '확인일2026-09-23; PDF의 표/그래프는 원문페이지 렌더링으로 확인; 원자료 이미지·PDF는 재배포하지 않음')
    css='''*{box-sizing:border-box}body{margin:0;background:#e8edf1;color:#152637;font-family:system-ui,-apple-system,"Malgun Gothic","Noto Sans CJK KR",sans-serif;line-height:1.55}nav{position:fixed;top:0;width:100%;height:52px;background:#102d40;color:white;z-index:8;display:flex;align-items:center;gap:12px;padding:0 20px;font-size:14px}button,select{font:inherit;border:1px solid #8098a5;border-radius:5px;padding:5px 10px;background:white;color:#173b50;cursor:pointer}select{max-width:440px}#page{margin-left:auto}.slide{display:none;max-width:1280px;min-height:710px;margin:72px auto 28px;background:white;border-top:7px solid #197684;padding:34px 48px 20px;box-shadow:0 10px 32px #102d4015}.slide.active{display:flex;flex-direction:column}.stage{letter-spacing:.12em;font-size:12px;color:#197684;font-weight:800}h1{font-size:31px;line-height:1.28;letter-spacing:-.03em;margin:10px 0 25px}p{margin:10px 0 16px;font-size:18px}.content{flex:1}table{border-collapse:collapse;width:100%;font-size:16px;margin:10px 0 20px}th{background:#eef5f6;text-align:left;color:#155966;padding:12px;border-bottom:2px solid #2b6d7b}td{padding:11px 12px;border-bottom:1px solid #d9e3e8;vertical-align:top}small{font-size:13px;color:#496371}.columns{display:grid;grid-template-columns:1.13fr 1fr;gap:30px;align-items:start}.note,.warn{padding:14px 18px;border-left:4px solid #2d8c94;background:#f0f7f8;font-size:16px;margin:15px 0}.warn{border-left-color:#c58331;background:#fff7e9}.plot svg{width:100%;height:auto;max-height:400px}.hero{font-size:70px;font-weight:750;letter-spacing:-.05em;margin:15px 0;color:#17546b}.hero span{color:#5d808d}.hero.small{font-size:54px}.hero em{font-size:24px;font-style:normal;color:#496371}.equation{background:#f3f6f8;text-align:center;padding:20px;font-family:Georgia,serif;font-size:25px;margin:10px 0 25px}.stats{display:flex;justify-content:space-between;gap:22px;padding:16px 0}.stats b{display:block;font-size:30px;color:#176278}.stats span{font-size:15px}.foot{border-top:1px solid #dbe4e9;padding-top:10px;margin-top:24px;font-size:11px;color:#607886;display:flex;justify-content:space-between;gap:18px}.claim{font-size:15px;color:#7b4e21;padding-top:4px}pre{background:#eef3f6;padding:18px;border-radius:6px;white-space:pre-wrap;font-size:14px}.reference{font-size:14px;margin-bottom:12px}a{color:#176f91}.all .slide{display:flex;flex-direction:column}.all nav{position:sticky}.all .slide{margin-top:28px}@media(max-width:900px){.slide{margin:64px 10px 15px;padding:22px;min-height:0}.columns{grid-template-columns:1fr;gap:15px}h1{font-size:25px}.hero{font-size:48px}p{font-size:16px}table{font-size:14px}td,th{padding:7px}select{max-width:35vw}nav{padding:0 8px;gap:5px}nav .brand{display:none}.stats{flex-wrap:wrap}}@media print{body{background:white}nav{display:none!important}.slide{display:flex;flex-direction:column;margin:0;border:0;box-shadow:none;min-height:0;page-break-after:always;break-after:page;padding:10mm;max-width:none}h1{font-size:25px}p{font-size:15px}table{font-size:13px}.foot{font-size:9px}.plot svg{max-height:350px}.columns{grid-template-columns:1.1fr 1fr}.hero{font-size:55px}@page{size:A4 landscape;margin:8mm}}'''
    opts=''.join(f'<option value="{i}">{i+1:02} · {html.escape(x["title"])}</option>' for i,x in enumerate(slides))
    content=''.join(f'<section class="slide {"active" if i==0 else ""}" id="s{i+1}"><div class="stage">{x["stage"]}</div><h1>{x["title"]}</h1><div class="content">{x["body"]}</div>'+ (f'<div class="claim">{x["claim"]}</div>' if x['claim'] else '')+f'<footer class="foot"><span>{html.escape(x["source"])}</span><span>SSBB · NUMERICAL v2 · {i+1:02}/{len(slides)}</span></footer></section>' for i,x in enumerate(slides))
    js='''let current=0;const sl=[...document.querySelectorAll('.slide')],sel=document.querySelector('select');function show(k){current=Math.max(0,Math.min(sl.length-1,k));sl.forEach((s,i)=>s.classList.toggle('active',i===current));sel.value=current;document.getElementById('page').textContent=`${current+1} / ${sl.length}`;history.replaceState(null,'','#s'+(current+1));window.scrollTo(0,0)}document.getElementById('prev').onclick=()=>show(current-1);document.getElementById('next').onclick=()=>show(current+1);sel.onchange=()=>show(+sel.value);document.getElementById('all').onclick=()=>document.body.classList.toggle('all');document.addEventListener('keydown',e=>{if(e.target.tagName==='SELECT')return;if(e.key==='ArrowRight'||e.key==='PageDown'){e.preventDefault();show(current+1)}if(e.key==='ArrowLeft'||e.key==='PageUp'){e.preventDefault();show(current-1)}});show((parseInt(location.hash.replace('#s',''))||1)-1);'''
    out='<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SSBB v2 · 저부하 THD 개선 수치 연구</title><style>'+css+'</style></head><body><nav><strong class="brand">SSBB · v2</strong><button id="prev">이전</button><select aria-label="슬라이드 선택">'+opts+'</select><button id="next">다음</button><button id="all">전체보기</button><button onclick="print()">인쇄</button><span id="page"></span></nav>'+content+'<script>'+js+'</script></body></html>'
    (output/'index.html').write_text(out,encoding='utf-8')
    (r/'report_index.json').write_text(json.dumps([dict(number=i+1,title=x['title'],source=x['source']) for i,x in enumerate(slides)],ensure_ascii=False,indent=2))
    (r/'report_summary.md').write_text(f'''# v2 결과 요약\n\n참조 수치 모델, 제품/PSIM/사내BB승인 결과 아님.\n\n주45점: baseline THD 평균 {bp['mean_thd']:.6f}%, 최대{bp['max_thd']:.6f}%,10/45통과.\n개선후 평균{ap['mean_thd']:.6f}%, 최대{ap['max_thd']:.6f}%,45/45통과.\n별도72점: 개선후평균{hp['mean_thd']:.6f}%,최대{hp['max_thd']:.6f}%,72/72통과.\n중고부하36점: THD36/36통과,종합35/36통과. S035전압포화는전후모두남음.\nQ고유메커니즘과제품물리검증은미완료.\n총{s['total_performance_runs']}회성능실행,원시파형전체재계산.\n최종보고서{len(slides)}슬라이드.\n''',encoding='utf-8')
if __name__=='__main__': build(Path(__file__).resolve().parents[1])
