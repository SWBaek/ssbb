"""Build a self-contained Korean slide report from executed numerical evidence."""
from pathlib import Path
import json, io, html, hashlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def build_report(root):
    root=Path(root); out=root/'report'; out.mkdir(exist_ok=True)
    R=root/'results'
    S=json.loads((R/'summary.json').read_text())
    load=lambda name: pd.read_csv(R/(name+'.csv'))
    B=load('baseline'); I=load('improved'); HB=load('holdout_baseline'); H=load('holdout_improved')
    D=load('doe_candidates'); F=load('factor_effects'); A=load('ablation')
    C=load('constant_S_phase'); T=load('transient'); RE=load('final_refinement')
    refs=json.loads((root/'docs/reference_cases.json').read_text())
    verification=json.loads((R/'verification.json').read_text())
    b=S['baseline']; z=S['improved']; h=S['holdout_improved']; control=S['control']
    nf=int((~H.thd_pass).sum()); ng=int((~H.combined_pass).sum())
    t1base=T[(T.case_id=='T1')&(T.comp_gain==0)].iloc[0]
    t1new=T[(T.case_id=='T1')&(T.comp_gain==1)].iloc[0]
    sel=json.loads((R/'selected_control.json').read_text())
    trainids=sel['training_case_ids']; trainb=B[B.case_id.isin(trainids)]; traini=I[I.case_id.isin(trainids)]
    def n(v,d=2): return f'{float(v):,.{d}f}'
    def esc(v): return html.escape(str(v))
    def table(head,rows,small=False):
        return '<table'+(' class="small"' if small else '')+'><thead><tr>'+''.join('<th>'+esc(x)+'</th>' for x in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table>'
    def box(title,body,kind=''):
        return f'<div class="box {kind}"><h3>{title}</h3>{body}</div>'
    def cols(a,b): return '<div class="cols"><div>'+a+'</div><div>'+b+'</div></div>'
    def p(s): return '<p>'+s+'</p>'
    def note(s): return '<div class="note">'+s+'</div>'
    def figure(name,draw):
        fig,ax=plt.subplots(figsize=(8.2,4.6),layout='constrained')
        draw(ax)
        ax.tick_params(labelsize=10)
        buff=io.StringIO(); fig.savefig(buff,format='svg',metadata={'Date':None}); plt.close(fig)
        svg=buff.getvalue(); svg=svg[svg.index('<svg'):]
        (out/(name+'.svg')).write_text(svg,encoding='utf-8')
        return '<div class="figure" role="img" aria-label="'+esc(name)+'">'+svg+'</div>'
    def wave(row):
        with np.load(root/row.wave_archive,allow_pickle=False) as a: return a[row.run_id].copy()
    def plot_main(ax):
        ax.plot(np.arange(1,73),B.thd_pct,label='Baseline',marker='.',linewidth=1)
        ax.plot(np.arange(1,73),I.thd_pct,label='Selected',marker='.',linewidth=1)
        ax.axhline(5,linestyle='--',label='Assumed 5% limit')
        ax.set(xlabel='Fixed main-matrix case index',ylabel='THD (2–40) [%]',ylim=(0,42)); ax.legend()
    gmain=figure('main_comparison',plot_main)
    def plot_current(ax):
        for fr,label in [(B,'Baseline'),(I,'Selected')]:
            row=fr.loc[fr.case_id=='M055'].iloc[0]; a=wave(row)
            ax.plot(np.arange(640)/32,a[0,-640:],label=label)
        ax.plot(np.arange(640)/32,a[1,-640:],linestyle='--',label='Reference')
        ax.set(xlabel='One steady-state cycle [ms]',ylabel='Current [A]');ax.legend()
    gwave=figure('worst_nominal_waveform',plot_current)
    def plot_base(ax):
        ax.scatter(B.i1_rms_a,B.thd_pct,label='72 operating points')
        ax.axhline(5,linestyle='--',label='Assumed 5% limit')
        ax.set(xlabel='Fundamental current RMS [A]',ylabel='Baseline THD [%]');ax.legend()
    gbase=figure('baseline_vs_current',plot_base)
    def plot_ablation(ax):
        a=A[A.case_id.str.startswith('A_low')]
        ax.bar(['No dead-time','Baseline','BW only','Comp. only','Combined'],a.thd_pct)
        ax.set(ylabel='THD [%]',title='P=350 W, Q=0 var, V=230 V'); ax.tick_params(axis='x',labelsize=9)
        for j,v in enumerate(a.thd_pct):ax.text(j,v+.5,f'{v:.3f}',ha='center',fontsize=10)
    gab=figure('ablation',plot_ablation)
    def plot_phase(ax):
        for apparent in [350,700,1400]:
            fr=C[(C.comp_gain==0)&C.case_id.str.startswith(f'S{apparent}_')].copy()
            fr['angle']=fr.case_id.str.split('angle').str[-1].astype(int);fr=fr.sort_values('angle')
            ax.plot(fr.angle,fr.thd_pct,marker='o',label=f'S={apparent} VA')
        ax.set(xlabel='Current phase / commanded P-Q angle [deg]',ylabel='Baseline THD [%]');ax.legend()
    gphase=figure('constant_S_phase',plot_phase)
    def plot_effects(ax):
        ax.barh(F.term.str.replace('comp_width_a','Ic').str.replace('comp_gain','alpha').str.replace('bw_hz','bw'),F.share_pct)
        ax.set(xlabel='Share of finite-grid sum of squares [%]');ax.invert_yaxis()
    geffects=figure('factor_effects',plot_effects)
    def plot_holdout(ax):
        ax.plot(np.arange(1,73),H.thd_pct,'o',label='Selected / unseen scenarios')
        ax.axhline(5,linestyle='--',label='Assumed 5% limit');ax.axvline(64.5,linestyle=':',label='LHS | corner scenarios')
        ax.set(xlabel='Holdout case index',ylabel='THD [%]',ylim=(0,7));ax.legend(fontsize=9)
    gh=figure('holdout',plot_holdout)
    fail=H[~H.combined_pass]
    h37=H[H.case_id=='H037'].iloc[0]
    def plot_headroom(ax):
        a=wave(h37); tt=np.arange(640)/32;cmd=a[3,-640:];ref=(.95*h37.vdc)
        ax.plot(tt,cmd,label='Clipped generated command')
        ax.axhline(ref,linestyle='--',label='+/-0.95 Vdc limit');ax.axhline(-ref,linestyle='--')
        ax.set(xlabel='One steady-state cycle [ms]',ylabel='Command [V]');ax.legend(fontsize=9)
    ghead=figure('H037_voltage_headroom',plot_headroom)
    def plot_step(ax):
        for gain,label in [(0,'Baseline'),(1,'Selected')]:
            row=T[(T.case_id=='T1')&(T.comp_gain==gain)].iloc[0];a=wave(row)
            t=a[0]; nn=640
            pw=np.convolve(a[1]*a[2],np.ones(nn)/nn,'valid');tt=t[nn-1:]
            mask=(tt>=.28)&(tt<=.36); ax.plot(tt[mask]*1000,pw[mask],label=label)
        ax.axhline(350,linestyle='--',label='Final P reference');ax.axhline(330,linestyle=':');ax.axhline(370,linestyle=':')
        ax.set(xlabel='Time [ms]',ylabel='One-cycle mean active power [W]');ax.legend(fontsize=9)
    gstep=figure('T1_transient_tradeoff',plot_step)
    slides=[]
    def slide(stage,title,body,source='Own numerical study; see results/manifest.json',tag=''):
        slides.append(dict(stage=stage,title=title,body=body,source=source,tag=tag))
    slide('SIX SIGMA BB · NUMERICAL STUDY', 'V2G 저부하·무효전력 운전<br>전류 THD 개선 연구',
        '<div class="subtitle">일반화된 AC단 수치모델 · 제어 설계안 도출 · 검증 한계 공개</div>'+p('상위 과제: OBCM V2G 저부하·무효전력 운전 시 계통 전류 THD 규격 만족률 향상')+
        '<div class="hero">수치 연구는 실행 완료.<br><span>실제 제품 및 사내 BB 완료는 미입증.</span></div>'+note('2026-09-23 · SSBB-NUM-20260923-v1 · 실제 적분 결과 / PSIM·HW 데이터 아님'),
        'Protocol: docs/00_scope_and_protocol.md · docs/01_experiment_plan.md', 'REFERENCE MODEL')
    slide('결론', '명목 조건은 달성, 불확실성 조건은 미달이 남는다',
        '<div class="metrics">'+box('주 행렬 THD',f'<strong>{z["thd_pass"]}/{z["n"]}</strong><p>baseline {b["thd_pass"]}/{b["n"]} → {n(z["pass_rate_pct"],0)}%</p>')+
        box('미사용 조건 THD',f'<strong>{h["thd_pass"]}/{h["n"]}</strong><p>{n(h["pass_rate_pct"])}% · {nf}점 미달</p>')+
        box('미사용 조건 종합',f'<strong>{h["combined_pass"]}/{h["n"]}</strong><p>{n(h["combined_pass_rate_pct"])}% · {ng}점 미달</p>')+'</div>'+
        p('최대 THD: 주 행렬 <b>'+n(b['worst_thd_pct'])+' → '+n(z['worst_thd_pct'])+'%</b>, 미사용 조건 <b>'+n(h['worst_thd_pct'])+'%</b>. 수치는 모두 가정한 참조모델 결과다.')+
        note('H037은 THD 통과라도 포화 기준 위반. T1 정착시간은 증가. 실제 Q 운전 영교차 메커니즘은 아직 모델에 없다.'), 'results/summary.json · holdout_failures.csv · transient.csv')
    slide('DEFINE', '목표와 완료 범위를 먼저 구분한다',
        table(['항목','정의'],[
        ['Big Y / Little y','제품 전류 품질 확보 / V2G 운전영역의 왜곡 저감'],
        ['이번 Project Y','고정 시험점에서 THD ≤ 5%인 비율. 5%는 잠정 설계 가정.'],
        ['명목 목표','주 행렬 만족률 ≥ 95%. 실행 전 지정했으며 결과를 보고 변경하지 않음.'],
        ['baseline','300 Hz 명목 PI 이득 인자, 보상 없음인 일반화 모델. 실제 제품 현수준 아님.'],
        ['완료 산출물','모델·코드·591개 성능 실행·파형·비교·검토·재현 가능한 보고서'],
        ['미완료 업무','제품 모델 대응, 고객 CTQ 확정, 실물 검증, 제품 SW 반영, MBB 승인']]),
        'docs/00_scope_and_protocol.md · study_config.json')
    slide('DEFINE', 'THD와 종합 판정을 혼합하지 않는다',
        '<div class="equation">THD<sub>I</sub> = 100 × √(Σ<sub>h=2…40</sub> I<sub>h,rms</sub>²) / I<sub>1,rms</sub></div>'+
        cols(box('THD 판정',p('50 Hz 정상상태 마지막 10주기.<br>32 ksample/s, 6,400점 coherent FFT.<br>2~40차 정수 고조파 / 기본파 RMS.')+p('<b>Y<sub>sim</sub> = 100 × 통과 시험점 / 전체 대상 시험점</b>')),
        box('별도 guardrail',p('P/Q 오차 각각 ≤ max(20 W 또는 var, 0.02·S*)<br>정상상태 peak current &lt; 50 A<br>전압 지령 포화 비율 &lt; 0.1%')+p('종합 통과 = THD 통과 AND 모든 guardrail 통과.')))+
        note('IEEE 1547 TRD/정격전류 정규화·interharmonics 등을 검증한 시험이 아니다. 무전류 P=Q=0은 사전에 제외한다.'),
        'src/model.py: harmonic_metrics · E01 (power-quality scope reference)')
    slide('DEFINE', '72점 전체를 독립 검증이라고 부르지 않는다',
        table(['집합','시험 조건','역할'],[
        ['주 행렬 72점','P={0,350,700,1400,2800} W<br>Q={−1400,−700,0,700,1400} var<br>V={207,230,253} Vrms; 무전류 3점 제외','기준/개선 전후 비교'],
        ['학습 9점','P={350,700,1400}, Q={−700,0,700}, V=230','27개 제어 후보 선정'],
        ['주 행렬 중 미사용 63점','72점에서 학습 9점 제외','명목 모델의 미사용 운전점 확인'],
        ['추가 조건 72점','LHS 64점 + 경계 8점; seed=20260923','공차·계통·센서·모델 함수 변경']])+note('추가 72점은 가정 범위의 coverage다. 실제 부품 산포 분포나 양산 합격확률이 아니다.'),
        'results/main_cases.csv · training_cases.csv · holdout_cases.csv')
    slide('MEASURE · MODEL', '계산되는 것은 전류의 미분방정식이다',
        '<div class="equation">(L<sub>f</sub>+L<sub>g</sub>) di/dt = v<sub>inv</sub> − (R<sub>f</sub>+R<sub>g</sub>)i − v<sub>g</sub></div>'+
        '<div class="equation">v<sub>inv</sub> = clip(u<sub>k−1</sub> − e<sub>dt</sub>(i), ±V<sub>dc</sub>)</div>'+
        cols(table(['명목 가정','값'],[['DC bus / grid','400 V / 230 Vrms, 50 Hz'],['Lf / Rf','1.5 mH / 0.15 Ω'],['Lg / Rg','0.2 mH / 0.10 Ω'],['true dead-time / I0','1 μs / 0.25 A']]),
        box('등가 비선형',p('e<sub>dt</sub> = V<sub>dc</sub> f<sub>s</sub> t<sub>d</sub> tanh(i/I<sub>0</sub>)')+p('명목 전압오차 계수 12.8 V.<br>실측 식별값이 아니라 명시한 모델 가정.')+p('플랜트 상태를 RK4로 직접 적분한다. 원하는 THD에 맞춰 파형을 합성하지 않는다.'))),
        'src/model.py: rhs, rk4_step · docs/02_model_and_validation.md')
    slide('MEASURE · CONTROL', 'dq PI·PLL·지연·전압 제한을 이산 시간으로 실행한다',
        '<div class="flow">P*, Q* → i* 생성 → dq PI + feedforward + 보상 → 전압 제한 → 1주기 지연 → 플랜트</div>'+
        table(['구성','구현'],[['주기','제어 31.25 μs; 플랜트 16분할, 1.953125 μs'],['좌표계','id*=√2 P*/V, iq*=−√2 Q*/V; Q>0은 전류 지연'],['PI 이득','Kp=2π·bw·Lf,nom, Ki=2π·bw·Rf,nom'],['동기화','20 Hz SOGI-PLL, 동기된 50 Hz 초기조건'],['비이상','검출 offset/양자화, command 지연, ±0.95 Vdc, 조건부 적분']])+
        note('bw는 이득 산정용 명목 인자다. 실제 교차주파수·위상여유 측정값이 아니다. 실제 차량 CAN 부호와의 매핑도 수행하지 않았다.'),
        'src/model.py: _simulate · docs/02_model_and_validation.md')
    slide('MEASURE · MODEL BOUNDARY', '실제 totem-pole의 축약 모델이라는 점이 가장 큰 한계다',
        cols(box('포함',p('평균 전압원 AC단, L/R 필터, sampled-data 전류제어, PLL, 포화, 지연, 가정한 dead-time 전압오차.')+p('계통 3·5차 고조파, 부품값/센서 가정 변화.')),
        box('포함하지 않음',p('LF leg 전환·전압/전류 영교차 상태천이, 실제 PWM 스위칭, DCM/Coss/역회복, EMI 필터, 자성체 포화.')+p('CLLC, DC-link 외부루프/2ω ripple, 열·효율, 보호, MCU 연산시간.')))+
        note('이 모델에서의 “Q 운전 개선”을 실제 OBCM의 무효전력 운전 문제 해결과 동일하게 해석할 수 없다. 외부 TI 참조설계는 모델 동등성 검증 자료가 아니다.'),
        'docs/02_model_and_validation.md · E02 (TI reference context, not calibration)')
    vmap={x['test']:x for x in verification['checks']}
    slide('MEASURE · VERIFICATION', f'수치 검증 {len(verification["checks"])}개 통과, 실물 검증은 별개다',
        table(['검증','실제 오차','허용 오차'],[
        ['알려진 신호 THD',f'{vmap["known_harmonic_THD"]["value"]:.2e} %p','1e−10 %p'],
        ['RL 폐형식 해',f'{vmap["RL_closed_form"]["value"]:.2e} A','1e−8 A'],
        ['RK4 vs DOP853 (80개 단일구간)',f'{1e3*vmap["nonlinear_RK4_vs_DOP853"]["value"]:.4f} mA','1 mA'],
        ['FFT vs 직접 직교투영',f'{vmap["FFT_vs_direct_projection"]["value"]:.2e} A','1e−10 A'],
        ['구간별 평균 전력수지',f'{vmap["mean_power_balance"]["value"]:.5f} W','0.5 W']])+
        p('별도로 시간 간격 수렴, 정상상태 주기성, 40/60주기 일치, 결정론적 재실행, 잠금 상태 PLL 위상을 확인했다.')+
        note('계산의 내부 일관성을 확인한 결과다. 실제 회로가 이 모델과 같다는 empirical validation은 수행하지 않았다.'),
        'results/verification.json · convergence.csv · E03 NASA / E04 SciPy')
    slide('MEASURE · CORRECTIONS', '초기 검증 실패도 이력에서 제거하지 않았다',
        table(['발견','조치','검증 후'],[
        ['8분할 RK4의 독립 해 대비 오차 약 2.824 mA','허용 1 mA를 유지하고 production을 16분할로 변경','약 0.3852 mA'],
        ['전력수지 좌측 합산 잔차 약 3.48 W','ZOH command 구간별 적분과 인덕터 에너지 변화 반영','약 0.0090 W']])+
        box('통계적 반복과 수치 반복의 구분',p('같은 입력을 다시 실행해 같은 값이 나온다고 현실의 측정시스템 Gage R&R을 통과한 것은 아니다.')+p('p-value를 얻으려고 임의 잡음을 더하지 않았다. 수치 정밀도를 높이려고 모델 응답을 목표값에 맞추지도 않았다.')),
        'docs/05_development_log.md · results/verification.json')
    slide('MEASURE · BASELINE', '가정한 baseline에서는 72점 모두 잠정 THD 기준을 초과한다',
        cols(gbase,box('수치 현수준',p(f'평균 THD <b>{n(b["mean_thd_pct"])}%</b><br>최대 THD <b>{n(b["worst_thd_pct"])}%</b><br>THD 통과 <b>{b["thd_pass"]}/{b["n"]}</b>')+
        p('작은 기본파 전류에서 왜곡 비율이 커지는 패턴이 나타난다. 실제 제품 데이터로 확인한 현상은 아니다.')+p('M072는 baseline에서도 전압 지령 포화 guardrail을 위반한다.'))),
        'results/baseline.csv · nominal assumptions in docs/00_scope_and_protocol.md')
    slide('ANALYZE · CAUSAL CHECK', '모델 안에서는 등가 dead-time 오차가 주요 원인이다',
        cols(gab,box('개별 대책과 조합',p('dead-time 항 제거 → THD 약 0.<br>이득 증가만으로는 미달이 남는다.<br>보상 단독도 개선하며, 조합이 더 낮다.')+
        p('이 검토는 가정한 모델의 원인 분해다. 실제 제품의 치명인자를 실험적으로 동정한 결과가 아니다.')))+note('이득 인자·보상 계수·보상 폭은 실행 전에 정했다. 후속 ablation을 먼저 수행하여 인자를 선정한 것처럼 시간 순서를 바꾸지 않는다.'),
        'results/ablation.csv · docs/01_experiment_plan.md')
    slide('ANALYZE · Q-SPECIFICITY', '동일 S에서 위상만 바꾸면 THD 차이는 작다',
        cols(gphase,box('상위 과제에 남는 공백',p('동일 피상전력의 위상 변화보다 전류 크기에 따른 차이가 훨씬 크다.')+
        p('이 평균모델에는 실제 totem-pole LF leg 영교차 전환 로직이 없다. 따라서 <b>Q 고유의 왜곡 메커니즘을 재현했다고 주장하지 않는다.</b>')))+note('이 결과를 보고 과제명을 조용히 바꾸거나 실제 Q 문제를 해결했다고 확대하지 않았다. 제품 대응 모델의 추가 검증이 필요하다.'),
        'results/constant_S_phase.csv · model boundary: docs/02_model_and_validation.md')
    slide('ANALYZE · EXPERIMENT DESIGN', '27개 제어 조합 × 9개 학습 조건을 전수 계산했다',
        table(['인자','수준','의미'],[['bw','300 / 600 / 900 Hz','PI 이득 산정 인자'],['α','0 / 0.5 / 1.0','보상 전압 배율'],['Ic','0.1 / 0.3 / 0.6 A','지령 전류 기반 tanh 보상 폭']])+
        '<div class="equation">u<sub>comp</sub> = α V<sub>dc</sub> f<sub>s</sub> t<sub>d,est</sub> tanh(i*/I<sub>c</sub>)</div>'+
        p('학습 9점의 종합 통과 수 최대 → 최대 THD 최소 → 평균 THD 최소 → 낮은 bw 우선으로 선정했다.')+
        note('t_d,est=1 μs는 고정. true 전류나 holdout의 true dead-time를 보상기에 주지 않는다. α=0이면 Ic는 효과가 없으며 동일 결과를 독립 반복으로 세지 않는다.'),
        'results/doe.csv · doe_candidates.csv · selected_control.json')
    slide('ANALYZE · FACTOR EFFECTS', '효과크기는 계산하되, 가짜 유의확률은 붙이지 않는다',
        cols(geffects,box('해석의 범위',p('9개 학습 조건 평균 THD에 대해 3×3×3 유한 격자의 제곱합을 분해했다.')+
        p('주효과와 교호작용을 설명하는 기술통계다. 실제 제품의 확률적 인과 기여율이나 ANOVA p-value가 아니다.')+
        p('전체 평균에서 작은 Ic 효과도 특정 저전류점에서는 중요할 수 있다.'))),
        'results/factor_effects.csv · src/study.py: factor_effects')
    slide('IMPROVE · SELECTION', '이산 후보 내 최선값을 동결한 뒤 다른 조건에 적용했다',
        table(['bw [Hz]','α','Ic [A]','학습 종합 통과','최대 THD [%]'],[[n(r.bw_hz,0),n(r.comp_gain,1),n(r.comp_width_a,1),f'{int(r.combined_pass)}/9',n(r.worst_thd_pct,4)] for r in D.head(5).itertuples()])+
        p(f'선정: <b>bw={n(control["bw_hz"],0)} Hz, α={n(control["comp_gain"],1)}, Ic={n(control["comp_width_a"],1)} A</b>. 명목 td 추정값은 1 μs 유지.')+
        note('이득 인자가 탐색 상한에서 선정되었다. 전역 최적점, 실제 폐루프 대역폭, 위상여유 또는 MCU 적용성을 확보한 것으로 표현하지 않는다.'),
        'results/doe_candidates.csv · selected_control.json (freeze before holdout)')
    slide('IMPROVE · MAIN RESULTS', '동일한 72개 조건에서 평균 THD가 크게 낮아졌다',
        cols(gmain,box('전후 비교',p(f'평균 <b>{n(b["mean_thd_pct"])} → {n(z["mean_thd_pct"])}%</b><br>최대 <b>{n(b["worst_thd_pct"])} → {n(z["worst_thd_pct"])}%</b><br>만족률 <b>{n(b["pass_rate_pct"],0)} → {n(z["pass_rate_pct"],0)}%</b>')+
        p('잠정 목표 95%를 주 행렬에서 만족했다. 시험점·플랜트·지표는 동일하고 제어 설정만 바꾸었다.'))),
        'results/baseline.csv · improved.csv · summary.json')
    row55=B[B.case_id=='M055'].iloc[0]
    slide('IMPROVE · WAVEFORM EVIDENCE', '최악 명목점의 전류 파형을 함께 확인한다',
        cols(gwave,box('M055',p(f'P={n(row55.p,0)} W, Q={n(row55.q,0)} var<br>V={n(row55.vrms,0)} Vrms')+
        p(f'THD <b>{n(b["worst_thd_pct"])} → {n(z["worst_thd_pct"])}%</b>')+p('표의 수치와 이 그림은 동일 저장 파형에서 나온다. PNG 그림만 남기지 않고 float64 원시 데이터를 보존한다.'))),
        'results/all_runs.csv: baseline_0055 / improved_0055 · mapped data/*.npz')
    slide('VERIFY · PARTITIONS', '학습과 미사용 조건의 성적을 분리해서 보고한다',
        table(['집합','baseline THD','개선 THD','개선 종합 판정'],[
        ['학습 9점',f'{int(trainb.thd_pass.sum())}/9',f'{int(traini.thd_pass.sum())}/9',f'{int(traini.combined_pass.sum())}/9'],['주 행렬 중 미사용 63점','0/63','63/63','63/63'],
        ['추가 미사용 72점','0/72',f'{h["thd_pass"]}/72',f'{h["combined_pass"]}/72']])+
        p('추가 조건에서는 true dead-time·L/R·Vdc·계통 고조파·센서가 달라진다. 64점 중 절반은 비선형 함수도 바꾼다.')+
        note('학습 데이터 누수는 피했지만 모든 시험은 여전히 동일한 축약 모델 계열이다. “실물 독립 검증”이라고 부를 수 없다.'),
        'results/training_cases.csv · holdout_cases.csv · summary.json')
    slide('VERIFY · ROBUSTNESS', '가정이 달라지면 명목 100%는 유지되지 않는다',
        cols(gh,box('추가 72점',p(f'평균 THD <b>{n(h["mean_thd_pct"])}%</b><br>최대 <b>{n(h["worst_thd_pct"])}%</b><br>THD 통과 <b>{h["thd_pass"]}/72</b>')+
        p('추정 dead-time는 고정한 채 true td를 0.7~1.3 μs로 변경했다. 마지막 8점은 미리 지정한 경계 조건이다.')+
        p('모든 미달과 악화 여부를 저장한다. 이 결과를 보고 재튜닝하지 않았다.'))),
        'results/holdout_improved.csv · holdout_cases.csv · selected_control.json')
    slide('VERIFY · FAILURES', f'종합 미달 {ng}점을 제거하지 않고 남겼다',
        table(['Case','P / Q [W / var]','V [Vrms]','THD [%]','미달 사유'],[
        [r.case_id,f'{n(r.p,1)} / {n(r.q,1)}',n(r.vrms,1),n(r.thd_pct,3),('포화 '+n(100*r.saturation_fraction,3)+'%' if not r.guardrail_pass else 'THD > 5%')] for r in fail.itertuples()])+
        note('5% 근처를 반올림하여 합격 처리하지 않았다. 최종 16→32분할 재검토에서도 관련 THD 판정은 바뀌지 않았다.'),
        'results/holdout_failures.csv · final_refinement.csv')
    slide('VERIFY · SIDE EFFECT', f'THD {h37.thd_pct:.2f}%라도 포화 조건을 위반하면 실패다',
        cols(ghead,box('H037',p(f'Vgrid={n(h37.vrms,2)} Vrms<br>Vdc={n(h37.vdc,2)} V<br>P={n(h37.p,1)} W / Q={n(h37.q,1)} var')+
        p(f'THD <b>{n(h37.thd_pct,3)}%</b><br>포화 비율 <b>{n(100*h37.saturation_fraction,3)}%</b><br>기준: <b>0.1% 미만</b>')+
        p('낮은 THD와 충분한 전압 지령 여유는 같은 목표가 아니다.'))),
        'results/holdout_improved.csv: H037 · comparison principle: A08 p14')
    tt=[]
    for cid in ['T1','T2','T3','T4']:
        aa=T[(T.case_id==cid)&(T.comp_gain==0)].iloc[0];bb=T[(T.case_id==cid)&(T.comp_gain==1)].iloc[0]
        tt.append([cid,f'{n(aa.p,0)} / {n(aa.q,0)}',n(1000*aa.step_settling_s,3),n(1000*bb.step_settling_s,3)])
    slide('VERIFY · TRANSIENT', '정상상태 THD 개선이 모든 응답의 개선을 뜻하지 않는다',
        cols(gstep,table(['Case','P / Q','기존 [ms]','개선 [ms]'],tt,True))+
        note(f'T1은 {1000*t1base.step_settling_s:.3f} → {1000*t1new.step_settling_s:.3f} ms로 느려진다. 0.3 s에서 절반→전 지령, 1주기 이동평균 P/Q의 지정 오차 내 정착을 측정했다. 제품 응답시간 합격 기준은 아직 없으므로 성능 저하로 명시한다.'),
        'results/transient.csv · data/transient_000.npz')
    slide('VERIFY · NUMERICAL MARGIN', '최종 일부 조건의 적분 정밀도를 다시 높여 확인했다',
        table(['대상','THD 16분할 [%]','THD 32분할 [%]','차이 [%p]'],[[r.source_phase+' / '+r.case_id,n(r.thd_16,6),n(r.thd_32,6),f'{r.difference_pp:.3e}'] for r in RE.itertuples()])+
        p('기준/개선의 최악점과 기준에 가장 가까운 점을 재검토했다. 최대 차이는 <b>'+f'{S["final_refinement_max_difference_pp"]:.3e}'+' %p</b>이며 THD 판정은 동일하다.')+
        note('수치 오차가 작다는 결론과 모델 오차가 작다는 결론은 별개다. 모든 holdout 플랜트의 실제 신뢰도를 정량화한 것은 아니다.'),
        'results/final_refinement.csv · data/final_refinement_000.npz')
    slide('CONTROL · REPRODUCIBILITY', '보고서보다 원시 데이터와 재실행 경로를 남긴다',
        table(['산출물','역할'],[['src/model.py / study.py','회로·제어·시험 순서·고정 조건'],['results/all_runs.csv','591개 성능 실행의 모든 입력, THD, 1~40차 RMS, 판정, 파형 경로'],['data/*.npz','일반 실험: 마지막 10주기 전체 제어 샘플; 과도 8런: 40주기 전체'],['selected_control / stage_log','설정 동결 hash, 실제 실행 순서'],['verification / manifest','수치 검증 결과와 최종 파일 SHA-256']])+
        '<pre>python -m src.study\npython -m unittest discover -s tests -v</pre>'+note('소스·기준이 바뀌면 새 revision으로 전체 재계산한다. 현재 holdout을 다시 튜닝에 쓰면 새로운 검증셋이 필요하다.'),
        'README.md · data/schema.json · results/manifest.json')
    slide('CONTROL · APPLICATION GATE', '실제 적용 전에 닫아야 할 조건을 명시한다',
        table(['열린 항목','필요 근거'],[['실제 현수준/CTQ','제품별 THD/TRD 정의, 운전영역, 한계값, 과거 측정 파형'],['모델 대응','실제 소자·필터·PWM/영교차·sampling 구조 및 제품 SW'],['실물 검증','PSIM 교차 확인과 별도의 HW correlation / 검증'],['부작용','DC-link·CLLC, 보호, 열·효율, 전체 루프 안정성, MCU timing'],['관리/성과','정식 calibration·회귀시험 기준·문서 반영, 실측 공수/비용'],['BB 승인','MBB가 인정하는 simulation-only 범위와 완료 조건']])+
        note('이 조건들을 “예정”이라고 기록하는 것은 완료로 간주하는 것과 다르다. 재무 효과는 실측 근거가 없어 미산정이다.'),
        'docs/04_logic_review.md · no empirical / financial evidence supplied')
    for section,items in [('1 / 2',refs[:6]),('2 / 2',refs[6:])]:
        slide('기존 보고서 비교 · '+section, '같은 증거 연결 방식을 채택하되, 없는 근거는 보태지 않는다',
            table(['사례 / 분량','원문에서 확인한 방식','본 연구 적용 / 잔여 차이'],[[r['id']+' '+r['topic']+f'<br>{r["method"]} · {r["slides"]}장',r['observed']+'<br><small>관련 p'+r['pages']+'</small>',r['apply']+'<br><small>'+r['gap']+'</small>'] for r in items],True),
            'User-provided 11 reports, 230 slides · docs/reference_cases.json · anonymized comparison only')
    slide('논리 검토', '해소한 오류와 남아 있는 한계를 분리한다',
        cols(box('처리한 위험',p('임의 결과 생성, 학습/검증 혼용, holdout 재튜닝, 가짜 통계 반복, THD만으로 채택, 제품 인증·원가 절감 과장.')+p('코드·원시 데이터·조건·표·그림·판정을 연결했다. 실패 7점과 과도응답 악화를 공개한다.')),
        box('미해결 경계',p('실제 Q 영교차 원인과 모델의 대응, 실측 없는 파라미터, 고객 CTQ, 제품 전체계 검증, 사내 승인.')+p('동일 작성 에이전트가 수행한 검토이며 독립 MBB 심사로 표현하지 않는다.')))+
        note('가장 중요한 결론: 이 자료는 재현 가능한 참조 수치 연구다. 실제 OBCM BB 과제 전체의 완료를 입증하는 보고서는 아직 아니다.'),
        'docs/04_logic_review.md · report/reference_comparison.md')
    slide('최종 결론', '조건부 제어 개선안과 재현 가능한 검증 기반을 확보했다',
        '<div class="hero compact">명목 성능 개선은 확인했다.<br><span>실물 적용성과 잔여 실패는 열어 둔다.</span></div>'+
        p(f'주 행렬 THD <b>{b["thd_pass"]}/{b["n"]} → {z["thd_pass"]}/{z["n"]}</b>. 추가 조건 THD <b>{h["thd_pass"]}/72</b>, 종합 <b>{h["combined_pass"]}/72</b>.')+
        p('산출물: 수치모델 소스, 고정 시험계획, 원시 파형, 591개 성능 실행, 23개 수치 검증, 단계 기록, 기존 11개 사례 비교와 논리 검토.')+
        note('제품과의 대응이 입증되기 전에는 이득/보상 값을 실제 OBCM에 그대로 적용하지 않는다. 최종 설정은 참조모델 내의 설계 후보이며 실제 제품 릴리스 승인값이 아니다.'),
        'results/summary.json · docs/04_logic_review.md')
    external=[
        ('E01','NREL/TP-5D00-78751 (2021), power quality requirements','https://www.nlr.gov/grid/ieee-standard-1547/background-information-on-power-quality-requirements','THD만으로 전체 계통연계 적합성을 주장하지 않는 배경. 본 threshold의 출처 아님.'),
        ('E02','TI TIDM-02008, bidirectional totem-pole reference','https://www.ti.com/tool/TIDM-02008','실제 양방향 토폴로지/저왜곡 설계의 참고. 본 모델 파라미터·동등성의 근거 아님.'),
        ('E03','NASA-STD-7009B (2024), Models and Simulations','https://standards.nasa.gov/standard/nasa/nasa-std-7009','모델 신뢰도·검증 범위의 구분. 당사 BB 규정으로 적용하지 않음.'),
        ('E04','SciPy solve_ivp documentation','https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html','독립 DOP853 계산의 도구 설명. 실행 버전은 environment.json 참조.')]
    slide('출처 및 추적', '참조자료는 적용 근거와 검증 증거를 구분하여 사용했다',
        table(['ID','공식 자료','이번 연구에서의 역할'],[[a,f'<a href="{url}" target="_blank" rel="noopener">{esc(title)}</a>',role] for a,title,url,role in external],True)+
        p('내부 사례 A01~A11은 사용자 제공 자료의 방법론·구성 비교다. 원본 PPTX·이미지·고객별 물량/비용은 저장소에 복제하지 않았다.')+
        note('보고서 숫자는 results/*.csv 및 summary.json에서 생성한다. 파일별 hash와 코드 hash는 manifest.json과 environment.json에 있다. 외부 자료 확인 기준일: 2026-09-23.'),
        'docs/reference_cases.json · results/environment.json · results/manifest.json')
    css='''
    :root{--ink:#172338;--muted:#526277;--line:#d8e1ea;--paper:#fff;--accent:#135970;--pale:#edf5f8}
    *{box-sizing:border-box}body{margin:0;background:#e8edf2;color:var(--ink);font-family:Arial,"Noto Sans CJK KR","Malgun Gothic",sans-serif;word-break:keep-all;overflow-wrap:anywhere}
    nav{height:52px;display:flex;align-items:center;gap:10px;padding:8px 20px;background:var(--ink);color:white;position:sticky;top:0;z-index:10}
    button,select{font:inherit;font-size:14px;padding:7px 12px;border-radius:5px;border:1px solid #b8c6d2;background:white;color:var(--ink)}select{max-width:600px;flex:1}button{cursor:pointer}nav span{font-size:14px;white-space:nowrap}
    .slide{display:none;width:1280px;height:720px;margin:18px auto;background:var(--paper);padding:38px 48px 48px;position:relative;overflow:hidden;box-shadow:0 6px 24px #17233812}
    .slide.active{display:block}.stage{font-size:13px;font-weight:700;letter-spacing:1.1px;color:var(--accent);text-transform:uppercase;margin-bottom:11px}
    h1{font-size:32px;line-height:1.3;margin:0 0 22px;letter-spacing:-.7px;max-width:1150px}h3{font-size:20px;margin:0 0 13px;color:var(--accent)}
    p{font-size:20px;line-height:1.55;margin:12px 0}.cols{display:grid;grid-template-columns:1.18fr 1fr;gap:26px;align-items:start}
    .box{padding:22px 24px;background:var(--pale);border-top:3px solid var(--accent);border-radius:2px}.box p{font-size:19px}.metrics{display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px;margin:25px 0}.metrics strong{font-size:52px;letter-spacing:-2px}
    .note{font-size:17px;line-height:1.5;background:#f4f6f9;border-left:4px solid var(--accent);padding:12px 17px;margin-top:18px}
    .hero{font-size:42px;line-height:1.45;font-weight:700;letter-spacing:-1.2px;margin:37px 0}.hero span{color:var(--accent)}.hero.compact{font-size:36px;margin:20px 0 25px}
    .subtitle{font-size:22px;color:var(--muted);margin-top:24px}.equation{font:22px/1.65 Georgia,"Noto Sans CJK KR",serif;padding:13px 18px;background:#f4f6f9;margin:10px 0 16px}
    .flow{background:var(--pale);padding:20px;font-size:20px;text-align:center;margin-bottom:18px}
    table{width:100%;border-collapse:collapse;table-layout:auto;font-size:18px;line-height:1.45}th{text-align:left;background:var(--pale);padding:11px 12px;border-bottom:2px solid var(--accent)}td{padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top}table.small{font-size:15px;line-height:1.42}table.small td,table.small th{padding:9px 10px}td:first-child{font-weight:600}small{font-size:.91em;color:var(--muted)}
    .figure{width:100%;margin:0}.figure svg{width:100%;height:auto;max-height:375px;display:block}pre{font-size:19px;line-height:1.5;background:#f4f6f9;padding:16px}a{color:var(--accent);text-decoration:underline}
    footer{position:absolute;bottom:17px;left:48px;right:48px;border-top:1px solid var(--line);padding-top:9px;font-size:11px;color:var(--muted);display:flex;gap:12px;justify-content:space-between}footer .src{max-width:1035px}body.all .slide{display:block}
    @media(max-width:1310px){.slide{width:calc(100% - 24px);height:auto;min-height:690px;padding:30px 34px 58px}footer{left:34px;right:34px}h1{font-size:29px}.hero{font-size:37px}}
    @media(max-width:760px){nav{gap:5px;padding:8px;height:auto;flex-wrap:wrap}nav span{display:none}select{max-width:100%;min-width:160px}.slide{padding:25px 22px 62px;min-height:0;margin:12px auto;overflow:visible}.cols,.metrics{grid-template-columns:1fr}h1{font-size:26px}p,.box p{font-size:17px}.hero{font-size:30px}.hero.compact{font-size:28px}.equation{font-size:17px}table{font-size:14px}table.small{font-size:12px}th,td{padding:7px 6px}.note{font-size:15px}footer{position:static;margin-top:24px;font-size:10px;display:block}.figure svg{max-height:none}.metrics strong{font-size:38px}}
    @media print{@page{size:338.67mm 190.5mm;margin:0}body{background:white}nav{display:none}.slide,.slide.active{display:block;width:1280px;height:720px;min-height:0;margin:0;box-shadow:none;break-after:page;page-break-after:always;print-color-adjust:exact}footer{position:absolute}.slide:last-child{break-after:auto}}
    '''
    js='''const slides=[...document.querySelectorAll('.slide')], select=document.querySelector('select');let current=0;
    function go(n){current=Math.max(0,Math.min(slides.length-1,n));slides.forEach((s,j)=>s.classList.toggle('active',j===current));select.value=current;document.querySelector('#count').textContent=(current+1)+' / '+slides.length;history.replaceState(null,'','#'+(current+1));if(document.body.classList.contains('all'))slides[current].scrollIntoView({behavior:'smooth'});}
    select.addEventListener('change',e=>go(+e.target.value));document.querySelector('#prev').onclick=()=>go(current-1);document.querySelector('#next').onclick=()=>go(current+1);document.querySelector('#all').onclick=()=>{document.body.classList.toggle('all');document.querySelector('#all').textContent=document.body.classList.contains('all')?'슬라이드 보기':'전체 보기'};document.querySelector('#print').onclick=()=>window.print();
    document.addEventListener('keydown',e=>{if(['SELECT','INPUT','TEXTAREA'].includes(e.target.tagName))return;if(['ArrowRight','PageDown',' '].includes(e.key)){e.preventDefault();go(current+1)}if(['ArrowLeft','PageUp'].includes(e.key)){e.preventDefault();go(current-1)}if(e.key==='Home')go(0);if(e.key==='End')go(slides.length-1)});go((parseInt(location.hash.slice(1))||1)-1);'''
    options=''.join(f'<option value="{j}">{j+1:02d} · {esc(s["title"].replace("<br>"," "))}</option>' for j,s in enumerate(slides))
    sections=''.join(f'<section class="slide" id="s{j+1}" aria-label="슬라이드 {j+1}"><div class="stage">{esc(s["stage"])}</div><h1>{s["title"]}</h1><div class="content">{s["body"]}</div><footer><span class="src">{esc(s["source"])}</span><span>{j+1:02d} / {len(slides):02d} · NUMERICAL ONLY</span></footer></section>' for j,s in enumerate(slides))
    text='<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SSBB · V2G THD 참조 수치 연구</title><style>'+css+'</style></head><body><nav><button id="prev" aria-label="이전 슬라이드">←</button><select aria-label="슬라이드 목차">'+options+'</select><button id="next" aria-label="다음 슬라이드">→</button><span id="count"></span><button id="all">전체 보기</button><button id="print">인쇄</button></nav>'+sections+'<script>'+js+'</script></body></html>'
    (out/'index.html').write_text(text,encoding='utf-8')
    # Text evidence companions are generated from the same numerical results.
    comparison='# 기존 11개 BB 보고서 대비 비교\n\n원문은 사용자 제공 프로젝트 자료다. 아래는 익명화한 방법론 관찰이며 원문 자료나 승인 기록을 재배포하지 않는다. 합격 여부는 사용자 설명을 전제로 하고, 공식 심사평가표는 제공되지 않았다.\n\n'
    for r in refs:
        comparison+=f'## {r["id"]} {r["topic"]} ({r["method"]}, {r["slides"]}장)\n\n근거 장: {r["pages"]}.\n\n원문 관찰: {r["observed"]}\n\n이번 적용: {r["apply"]}\n\n차이/미해결: {r["gap"]}\n\n'
    comparison+='## 종합 판단\n\nMeasure→Analyze→Improve의 증거 연결과 부작용·관리 기준을 채택했다. 본 연구는 가정 입력만 사용하므로, 실제 파라미터를 계측한 A05 및 시험값으로 해석을 보정한 A06보다 경험적 근거가 약하다. A07 같은 CAE 설계 사례가 있어도 본 과제의 사내 승인 요건을 자동으로 충족하지 않는다. 원시 데이터·코드·동결 검증의 재현성은 확보하되 실물 적용성과 MBB 승인은 열린 상태다.\n'
    (out/'reference_comparison.md').write_text(comparison,encoding='utf-8')
    lines=['# V2G THD 참조 수치모델 연구 결과','', '**실제 제품·PSIM·HW 검증이 아닌 numerical study.**', '',
        '| 집합 | baseline THD 통과 | 개선 THD 통과 | 개선 종합 통과 | 개선 평균/최대 THD |','|---|---:|---:|---:|---:|']
    for label,k0,k1 in [('주 행렬','baseline','improved'),('주 행렬 중 미사용','unseen_main_baseline','unseen_main_improved'),('추가 조건','holdout_baseline','holdout_improved')]:
        x=S[k0];y=S[k1];lines.append(f'| {label} | {x["thd_pass"]}/{x["n"]} | {y["thd_pass"]}/{y["n"]} | {y["combined_pass"]}/{y["n"]} | {y["mean_thd_pct"]:.4f}% / {y["worst_thd_pct"]:.4f}% |')
    lines+=['',f'선정 설정: {control}. 고정 학습 9점의 27개 이산 후보 중 선정했다.','',
        f'성능 실행 {S["total_performance_runs"]}회, numerical verification {S["numerical_tests"]}개 통과. 주 행렬 목표 {S["target_main_pct"]}%는 달성했다. 추가 조건은 별도 coverage 시험이며 양산 통과확률이 아니다.',
        '', '## 미달 및 부작용', '',f'H037: THD {h37.thd_pct:.6f}%지만 포화 {100*h37.saturation_fraction:.6f}%로 0.1% 미만 guardrail 위반.',
        '', f'THD 실패 {nf}점: '+', '.join(H.loc[~H.thd_pass,'case_id'])+'. 모두 유지했으며 holdout 후 재튜닝하지 않았다.', '',
        f'T1: 정착시간 {1000*t1base.step_settling_s:.3f} → {1000*t1new.step_settling_s:.3f} ms. 정상상태 THD 개선이 모든 과도 성능의 개선을 뜻하지 않는다.', '',
        '## 주장 범위', '', '실제 Q 운전의 LF leg 영교차 메커니즘, 제품 파라미터/제어 SW 대응, 고객 CTQ, 실물 검증, 재무성과, 사내 BB 승인은 미입증/미확인이다. 이 데이터로 실제 제품 규격 만족을 주장하지 않는다.',
        '', '근거: results/summary.json, all_runs.csv, holdout_failures.csv, transient.csv 및 원시 파형. 상세 논리 검토: docs/04_logic_review.md.']
    (out/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (out/'slides.json').write_text(json.dumps([dict(number=j+1,stage=s['stage'],title=s['title'].replace('<br>',' '),source=s['source']) for j,s in enumerate(slides)],ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return len(slides)

if __name__=='__main__':
    build_report(Path(__file__).resolve().parents[1])
