"""V6 report authoring from V6 CSV/JSON only. Editable industrial DMAIC layout."""
from pathlib import Path
import json,math
import numpy as np
import pandas as pd
from model import ROOT,SPEC,SQ2,TS,TP
from pptx_builder import build

R=ROOT/'results';S=json.loads((R/'summary.json').read_text())
A=pd.read_csv(R/'baseline.csv');B=pd.read_csv(R/'improved.csv');D=pd.read_csv(R/'doe.csv');C=pd.read_csv(R/'candidates.csv')
E=pd.read_csv(R/'main_effects.csv');J=pd.read_csv(R/'interactions.csv');SS=pd.read_csv(R/'factorial_decomposition.csv');ST=pd.read_csv(R/'current_strata.csv')
SEL=S['selected'];slides=[]
fmt=lambda x,n=3:f'{float(x):.{n}f}'
rate=lambda a,b:f'{a}/{b} ({100*a/b:.1f}%)'

def tx(t,x=.55,y=2.2,w=9.7,h=.65,size=13,bold=False,color='ink'):
 return dict(kind='text',text=str(t),x=x,y=y,w=w,h=h,size=size,bold=bold,color=color)
def tb(rows,x=.55,y=2.2,w=9.7,h=3.65,widths=None,size=12,**kw):
 return dict(kind='table',rows=[[str(c) for c in row] for row in rows],x=x,y=y,w=w,h=h,widths=widths or [1]*len(rows[0]),size=size,**kw)
def bx(t,x,y,w,h,size=13,color='ink'):
 return dict(kind='box',text=t,x=x,y=y,w=w,h=h,size=size,color=color,fill='white',align='center')
def ln(x,y,x2,y2):return dict(kind='line',x=x,y=y,x2=x2,y2=y2,arrow=True,color='ink')
def ch(cats,series,x=.55,y=2.3,w=6.25,h=3.65,typ='line',**kw):
 return dict(kind='chart',categories=[str(x) for x in cats],series=[dict(name=n,values=[float(z) for z in v],color=col) for n,v,col in series],x=x,y=y,w=w,h=h,type=typ,**kw)
def add(title,stage,sub,msg,els,src,notes=''):
 slides.append(dict(title=title,stage=stage,subtitle=sub,message=msg,elements=els,source=src,notes='[적용 목적]\n'+sub+'\n[결과 해석]\n'+msg+'\n'+notes+'\n[판단 범위]\n확정 입력: 230 Vac, 48 Arms, Peak dq, PWM·제어 62.5 kHz / 16 μs. 그 밖의 회로 및 판정 조건은 명시한 모델 가정임. 결과는 해당 수치모델과 유한 조건 집합에 한함.'))
def foot(t,y=6.3):return tx('→ '+t,y=y,h=.55,size=12.3,bold=True,color='teal')

# 01
slides.append(dict(cover=True,title='11.52 kVA급 북미 V2G OBCM\nAC단 dq 전류제어의 THD 개선 검토',subtitle='230 Vac · 48 Arms · Peak dq\nPWM 및 제어 연산 모두 62.5 kHz / 16 μs',author_line='백승우  |  Six Sigma Black Belt 과제',date_line='V6 · 2026.09.28\n230×48=11.04 kVA. 제품급 명칭과 기준점 계산값을 구분함.',source='사용자 최종 사양; specification.json',notes='V5는 최신 사양을 반영하지 못해 폐기 대상으로 구분하였다. V6는 새로운 조건과 모델로 502회 해석을 수행한다. 11.52 kVA는 사용자가 지정한 제품급 명칭이며 230 V와 48 A를 곱한 값으로 오기하지 않는다. 240 V 또는 50.087 A로 임의 변경하지 않았다.'))
# 02
add('1. Define / 최우선 사양 고정','D','V5의 잘못된 사양을 V6 입력에서 차단함','계산 전에 사양 자동검사를 수행하고, 모든 실행에 동일한 사양 해시를 저장함.',[
 tb([['구분','V6 적용값','적용 근거'],['기준 AC 전압','230 Vrms','사용자 확정'],['정격 AC 전류','48 Arms','사용자 확정'],['외부 dq 지령','d축·q축 모두 Peak A의 DC 지령','사용자 확정'],['PWM 주파수 / 주기','62.5 kHz / 16 μs','사용자 확정'],['제어 연산 주파수 / 주기','62.5 kHz / 16 μs','사용자 확정'],['PWM : 제어 실행 횟수','1 : 1','매 PWM 주기 1회 연산']],h=3.65,widths=[2,4,2.5]),foot('정격 32 Arms, 제어 32 μs, RMS dq 입력을 현재 사양으로 사용하지 않음.')], 'specification.json; src/model.py assert_spec(); qa/unit_tests.json','V5와 달리 외부 dq 입력에 √2를 추가로 곱하지 않는다. 입력 검사는 Peak A 기준 67.882 A의 벡터 한계를 사용한다. 32 A는 일부 시험조건으로는 등장할 수 있으나 정격전류가 아니다.')
# 03
add('1. Define / 용량 표기의 정합성','D','제품급 명칭과 기준 운전점의 계산값을 구분함','11.52 kVA급 명칭은 유지하되, 모든 기준 해석에는 230 Vac와 48 Arms를 적용함.',[
 tb([['항목','값','보고서에서의 의미'],['제품급 명칭','11.52 kVA급','사용자가 지정한 명칭'],['기준점 피상전력','230×48 = 11,040 VA','실제 입력으로 산출한 11.04 kVA'],['참고 산술관계','240×48 = 11,520 VA','240 V로 해석했다는 뜻이 아님'],['dq 벡터 최대값','√2×48 = 67.882 Apeak','각 축 개별 한계가 아니라 합성 벡터 한계'],['사양 확인 필요','명판 기준 전압과 용량의 관계','제품급 명칭만으로 계산 입력을 바꾸지 않음']],h=3.5,widths=[2.2,3.2,4.4]),tx('주의: 230 V에서 11.52 kVA를 유지하도록 전류를 50.087 Arms로 높이지 않았음.',y=6.03,size=12.5,color='red')], 'specification.json / derived_not_substituted','단상 정현파 전압 조건에서 전압 실효값×전류 실효값은 피상전력이다. 유효전력은 역률에 따라 달라진다. 11.52 kVA와 230×48의 산술 불일치를 묵시적으로 수정하지 않고 명시한다.')
# 04
add('1. Define / 과제 등록 및 목표','D','Project Y를 수치해석 설계기준 만족률로 정의함','저전류 운전의 THD를 개선하되, 전류 용량과 추종성 등 다른 조건의 미달을 함께 확인함.',[
 tb([['항목','정의'],['과제명','북미 V2G AC단의 dq 전류제어 THD 설계기준 만족률 개선'],['Project Y','기준 230 V 운전조건 47개 중 THD₂–₄₀ ≤ 5%인 조건의 비율'],['목표','THD 만족률 95% 이상 (47개 중 최소 45개)'],['보조 확인','dq 추종 / 실제 RMS≤48 A / 피크·포화 / 정상상태'],['적용 수준','참조 수치모델의 제어 후보 선정 및 한계 확인'],['미확정 사항','지도 MBB·Owner·등록기간, 모델 가정 및 고객 판정 기준']],widths=[2.2,7.2]),foot('THD 5%는 잠정 설계기준이며 북미 인증 적합성을 판정하지 않음.')], 'specification.json; results/summary.json','표지의 완료는 수치 연구의 수행 완료를 뜻한다. 실제 제품 적용·인증·사내 승인이 완료됐다는 의미가 아니다. 목표 만족률과 개별 조건의 THD 한계는 서로 다른 지표이다.')
# 05
add('1. Define / Big Y–Little y 전개','D','실제 업무 목표와 본 과제에서 측정하는 지표를 연결함','하드웨어 실험 대신 수치모델을 사용하므로, 제품 품질 성과와 모델 내 개선 성과를 분리함.',[
 bx('Big Y\nV2G 계통연계 품질 확보',.7,2.4,2.75,1.05),bx('Little y\nAC 전류 품질 개선',4.0,2.4,2.65,1.05),bx('Project Y\nTHD 설계기준 만족률',7.2,2.4,2.8,1.05),ln(3.5,2.93,3.96,2.93),ln(6.7,2.93,7.15,2.93),tb([['이번 과제에서 확인','별도 검증이 필요한 제품 요구'],['Peak dq 전류지령 추종, 저차 고조파 저감','실제 HW·소자·EMI 필터·DC-link 및 CLLC 상호작용'],['고정 조건 전후 비교와 후보 선정','고객 규격, 시험소 인증, 실차 통합'],['모델·파라미터 편차 영향 확인','양산 공차분포와 실제 고장률']],y=4.1,h=1.9,widths=[1,1],size=12),foot('수치모델의 만족률을 양산 수율 또는 고객 인증 통과율로 환산하지 않음.')], '구성 참고: Snubber p.4·10; CLLC p.3; docs/Model_and_Conventions.md')
# 06
add('1. Define / dq 전류 지령의 정의','D','외부 입력은 d축·q축의 피크값 DC 전류 지령임','Theta는 SOGI-PLL 내부 동기각으로만 사용하며 외부 전력 명령으로 사용하지 않음.',[
 tx('iα* = id* cosθ − iq* sinθ\nP₁* = V₁·id*/√2,   Q₁* = −V₁·iq*/√2',y=2.15,h=.9,size=18,bold=True),tb([['지령 예시 [Apeak]','기본파 전류 [Arms]','230 V에서의 전력'],['id*=67.882, iq*=0','48.000','P₁*=11.040 kW, Q₁*=0'],['id*=0, iq*=+67.882','48.000','P₁*=0, Q₁*=−11.040 kvar'],['id*=48.000, iq*=0','33.941','48 Arms 운전과 다른 지령임'],['id*=67.882, iq*=67.882','67.882','전류 벡터 초과로 입력 거부']],y=3.25,h=2.45,widths=[3,2.5,4.4]),tx('Q 부호: +Iq는 진상전류로 정의한 모델 규약임. 실제 CAN 부호는 별도 확인 필요.',y=6.2,size=12,color='red')], 'src/model.py validate(), run_core(); qa/unit_tests.log','d축과 q축은 amplitude-preserving Park 변환의 peak 좌표이다. 정상 지령은 DC이며 초기 50 ms 기동 구간에만 공통 ramp를 적용한다. 위상은 변환의 기준이므로 DC 명령을 사용하더라도 필요하다.')
# 07
add('2. Measure / 수치해석 시스템 구성','M','회로·제어·측정 경로를 분리하여 구성함','기본 dq PI와 PLL을 고정하고, 개선 시 준공진 전류 피드백만 추가함.',[
 bx('id* · iq*\n[Peak A, DC]',.55,2.5,1.6,.8),bx('dq PI +\n전향·교차결합 보상',2.65,2.5,2.05,.8),bx('16 μs 제어\nPWM 갱신 FIFO',5.2,2.5,1.8,.8),bx('62.5 kHz PWM\nAC단 RL·계통',7.5,2.5,2.45,.8),ln(2.15,2.9,2.6,2.9),ln(4.7,2.9,5.15,2.9),ln(7.,2.9,7.45,2.9),bx('전류 측정\n아날로그 LPF + ADC',5.75,4.2,2.3,.85),bx('SOGI 직교축\n전류 dq 변환',2.7,4.2,2.25,.85),ln(8.8,3.35,8.8,4.62),ln(8.75,4.62,8.1,4.62),ln(5.7,4.62,5.,4.62),ln(3.85,4.15,3.85,3.35),bx('SOGI-PLL → θ\n계통전압으로 내부 위상 추정',.65,5.55,4.25,.65,size=12),bx('추가 보상: 3·5·7차 준공진 피드백\n기본파 dq 명령은 유지함',5.45,5.55,4.55,.65,size=12)], 'src/model.py; 외부 방법 참고: Imperix SOGI-PLL / PR','단상 직교축은 SOGI로 구성한다. 회로는 이상적 강성 DC 전원과 HF/LF bridge를 포함한다. 실제 OBCM 전체 구성도 또는 양산 SW 구현의 확인 도면은 아니다.')
# 08
add('2. Measure / PWM·제어 시간축 검증','M','매 PWM 16 μs마다 제어 연산 1회 수행함','ADC 중앙 샘플링과 다음 PWM 경계 반영을 가정하여 기본 지연 8 μs를 별도 정의함.',[
 tb([['PWM 구간 [μs]','ADC·제어 시각 [μs]','결과 반영 [μs]','명령 유지'],['0~16','8','16','16~32 μs'],['16~32','24','32','32~48 μs'],['32~48','40','48','48~64 μs'],['기준 실행 0.75 s','제어 46,875회','PWM 46,875주기','1 : 1 확인']],h=2.5,widths=[2.5,2.8,2.5,2.6]),tx('추가 지연 시험에서도 제어 연산은 계속 16 μs마다 수행함.\nFIFO의 적용 시각만 늦추며 미적용 명령을 다음 명령이 덮어쓰지 않도록 검사함.',y=5.08,h=.83,size=13),foot('제어주기 16 μs는 확정값, ADC 위치·샘플→PWM 지연은 모델 가정임.')], 'qa/raw_audit.json; src/model.py run_core(); TI ePWM module','모든 실행에서 PWM 수와 제어 수가 동일한지 검사한다. FIFO source_sample_index 차이는 기본 1, 추가 1주기 지연 시 2이며 주기 자체가 32 μs로 변경된 것이 아니다. 하드웨어 지연이 8 μs라고 확인된 것은 아니다.')
# 09
add('2. Measure / 회로 모델과 수치 적분','M','스위칭 상태와 dead-time을 직접 계산함','평균전압 오차항으로 THD를 맞추지 않고, gate 상태에 따른 전압으로 전류를 적분함.',[
 tx('L·di/dt = ubridge − vg − R·i\nubridge = (HF pole − LF pole)·Vdc',y=2.15,h=.78,size=18,bold=True),tb([['항목','구현 및 한계'],['HF PWM','중앙정렬 PWM, turn-on dead-time, 이벤트 경계별 적분'],['dead-time 상태','PWM 경계를 넘는 대기 이벤트 보존 / 전류 방향에 따른 다이오드 도통'],['LF 레그','기준: 브리지 전압 명령 부호 / 대안: 계통 부호 고정의 별도 검증'],['수치 근사','구간 중앙 계통전압 + 해석적 RL/센서 갱신 / 시간간격 세분화 확인'],['미포함','LF 전환 blanking, Coss·열·EMI 필터·DC-link/CLLC 에너지 동역학']],y=3.13,h=2.75,widths=[2,7.5]),foot('저주파 레그 구현 가정의 민감도를 별도 결과로 제시함.')], 'src/model.py grid(), rl_sensor(), run_core(); docs/Model_and_Conventions.md','HF gate는 0/1/blank 중 하나이며 두 gate의 동시 on 상태는 정의하지 않는다. LF도 실제제품동작이 확정된 것은 아니다. 지령부호형 LF가 실제 firmware에서 구현 가능한지 별도 확인해야 한다.')
# 10
add('2. Measure / 확정값과 추가 가정','M','제공되지 않은 회로 사양을 확정값으로 표현하지 않음','THD 절대값의 신뢰도는 회로·검출·전환 로직에 대한 실제 근거가 확보되어야 높아짐.',[
 tb([['항목','기준 가정값','확인 필요 사항'],['계통 기본파','60 Hz','북미용 해석 가정 / 요구 주파수 범위'],['DC-link','400 V 강성 전원','제어·에너지 교환 동역학 미포함'],['Lf / Lg','1.0 / 0.1 mH','실물 인덕턴스·주파수 의존성'],['Rf / Rg','0.08 / 0.10 Ω','전력 손실·계통 임피던스'],['dead-time','200 ns','실제 PWM gate timing'],['전류 검출','10 kHz LPF, 12 bit / ±100 A','실제 ADC·offset·gain·노이즈'],['기본 제어','전류 설계 800 Hz / PLL 설계 15 Hz','실제 이득 및 안정여유']],h=3.9,widths=[2,3.3,4.2],size=11.6),tx('초기 THD가 기존 결과 또는 5~8% 목표에 맞도록 가정값을 보정하지 않았음.',y=6.42,size=11.8,color='red')], 'specification.json; sources/references.md','계통 60 Hz는 북미 해석 맥락에 따라 추가한 가정이다. 사용자가 확정한 주파수 62.5 kHz는 계통 주파수가 아니라 PWM 및 제어 주파수이다.')
# 11
add('1. Define / 시험 구성과 수량의 의미','D','운전조건·제어 후보·해석 실행 수를 구분함','기준 조건을 먼저 고정한 후, 선정용 조건에서 후보를 비교하고 나머지 조건을 평가함.',[
 tb([['대상','구성','용도'],['기준 운전조건 47개','230 V에서 직접 dq 지령 조합','전체 전후 성능 비교'],['선정용 9개','47개에 포함','제어 후보 27개 비교에만 사용'],['선정 미사용 38개','47−9=38개','선정 이후 확인 / 별도 47개가 아님'],['전압 검증조건 24개','207·253 V × dq 12조합','전압 변화 시 동일 전류 명령 검증'],['편차 검증조건 24개','회로·검출·주파수·지연 변경','가정 범위에서 성능 변화 확인']],h=3.15,widths=[2.5,3.25,4.1]),tx('DOE 실행 = 27후보×9운전조건 = 243회\n동일 운전조건을 초기·선정 제어로 각각 실행하면 조건 1개, 실행 2회임.',y=5.64,h=.85,size=13,bold=True)], 'results/*_conditions.csv; candidate_plan.csv; qa/frozen_protocol.json','전체 캠페인 502회에는 기준/DOE/추가검증/구조진단/수치세분화/과도 등 용도가 다른 실행이 포함된다. 502회를 독립실물표본수로 해석하지 않는다. 47,24,24의 만족률은 분모를 섞어 하나의 신뢰도로 합치지 않는다.')
# 12
add('1. Define / 직접 dq 운전조건 선정','D','전류 원 내부의 d·q 조합을 평가함','d축 유효전류와 양·음 q축 무효전류를 직접 조합하고, 전류 벡터 한계를 넘는 조합은 생성하지 않음.',[
 tb([['구분','시험 구성'],['d축 후보 [Apeak]','√2 × {0, 4, 8, 16, 32, 48}'],['q축 후보 [Apeak]','√2 × {0, ±4, ±8, ±16, ±32, ±48}'],['허용 조건','0 < sqrt(id*²+iq*²) ≤ 67.882 Apeak'],['선정용 조건','RMS 환산 표기 (4,0/±4), (8,0/±8), (16,0/±16)'],['실제 입력 파일','id_peak_a, iq_peak_a로 저장 / RMS 값 필드는 외부 입력에 없음'],['경계 포함','id*=67.882, iq*=0 및 id*=0, iq*=±67.882']],widths=[2.3,7.2]),foot('P*=0인 순수 Q 운전도 무전류 또는 저부하 운전으로 취급하지 않음.')], 'results/main_conditions.csv; src/study.py plans()','격자 구성 설명에 쓰는 RMS 환산값과 모델의 Peak 지령을 구분한다. 표시 간소화를 위해 √2×집합으로 적었지만 각 CSV에는 변환된 피크값이 저장되어 있다. 분류 경계의 CSV 반올림 오차는 8자리 반올림으로 제거하며 실제 판정 데이터는 변경하지 않는다.')
# 13
add('1. Define / 측정 지표와 판정 기준','D','THD와 실제 전류 용량을 별도로 판정함','고조파를 줄여도 전류 크기·추종·포화 조건을 만족하지 않으면 종합 만족으로 처리하지 않음.',[
 tb([['항목','잠정 설계 판정','평가 의미'],['THD₂–₄₀','≤ 5%','기본파 대비 2~40차 RMS 합성값'],['dq 추종오차','각 축 ≤ max(0.3 Apeak, 지령크기×2%)','Peak 지령 대비 기본파 Peak 측정값'],['실제 전류 RMS','≤ 48 Arms','스위칭 리플·고조파 포함'],['전류 피크','≤ 75 A (가정)','정상 평가구간의 순간 전류'],['전압·보상 제한','전압 제한 시간비≤1%, 공진·적분 제한 없음','제한의 발생 비율 확인'],['정상성','1~7차 주기간 차이 RMS≤max(0.03 A, Iref,rms×0.2%)','PWM 리플의 위상차와 구분']],h=3.4,widths=[1.9,4.3,3.5],size=11.6),tx('종합 만족 = THD ∧ dq 추종 ∧ 실제 RMS ∧ 피크 ∧ 제한 조건 ∧ 정상성',y=6.08,h=.5,size=13,bold=True)], 'specification.json / criteria; src/model.py measure()','전류 48 Arms는 사용자 정격이며 피크75 A, 오차허용치, THD5%, 포화1% 등은 설계 검토의 추가 가정이다. 고객 표준 규격으로 혼동하지 않는다. IEEE TRD와 제한 대역 THD를 같은 지표로 취급하지 않는다.')
# 14
add('2. Measure / 데이터 취득 신뢰성 검토','M','구현 검사와 실물 모델 검증을 구분함','사양·축 변환·클록·적분·고조파 계산을 검사하고, 실물 일치성은 미검증으로 남김.',[
 tb([['검증 항목','수행 결과','판단 범위'],['사양·수식·입력 검사',f"단위검사 {S['audit']['unit_tests']['tests_run']}개 통과",'잘못된 정격·단위·주기 입력 차단'],['실행 로그 확인','모든 502회에서 PWM:제어=1:1','16 μs 제어를 실제 실행했는지 확인'],['원시 파형 재계산','502회 전 지표와 40차 고조파 대조','보고서 집계와 원자료 정합성'],['FFT 교차계산',f"60 Hz 조건 {S['fft_check']['runs']}회 / 최대차 {S['fft_check']['max_absolute_difference_pp']:.2e}%p",'두 계산 경로의 일관성'],['실행 재현','대표 4개 전류 배열 동일','동일 환경 재현성 / 실물 표본수 아님'],['HW correlation','수행하지 않음','실제 제품과 같은 절대 THD임을 보장하지 않음']],h=3.65,widths=[2.1,4.3,3.4],size=11.4),foot('Gage R&R 수치를 가상으로 만들지 않고 수치 구현 검증 결과를 제시함.')], 'qa/unit_tests.json; raw_audit.json; fft_crosscheck.csv; replay.json')
# 15
s0=S['nominal']['initial'];s1=S['nominal']['selected']
strlabels=['≤8 Arms','8~24 Arms','24~48 Arms'];sa=[ST[(ST.stratum==x)&(ST.control=='initial')].iloc[0] for x in ['low_le_8Arms','medium_8_to_24Arms','high_24_to_48Arms']]
add('2. Measure / 현 수준 파악','M','저전류 조건에서 상대 고조파가 증가함','전체 시험집합 평균과 저전류 집합 평균을 구분하여 현 수준을 확인함.',[
 ch(strlabels,[('초기 평균 THD',[x.thd_mean for x in sa],'gray')],typ='column',w=5.8,max=9,labels=True),tb([['범위','조건 수','평균 THD'],['기준 전체',47,fmt(s0['thd_mean'])+'%'],*[['저전류' if k==0 else strlabels[k],int(x.n),fmt(x.thd_mean)+'%'] for k,x in enumerate(sa)]],x=6.7,y=2.4,w=3.5,h=2.8,widths=[1.1,.8,1.1],size=11.3),foot(f"기준 47개 중 THD 만족 {s0['thd_pass_n']}개. 초기값은 보정 없이 V6 모델에서 계산함.")], 'results/baseline.csv; current_strata.csv','전류 크기 분류는 지령 벡터의 RMS 환산값이다. 전체 평균은 정한 격자 평균이며 업계 평균이 아니다. 저전류가 주요 문제라는 분석과 전체 제품 성능의 수준은 구분한다.')
# 16
low=A[np.round(np.hypot(A.id_peak_a,A.iq_peak_a)/SQ2,8)<=8]
add('2. Measure / 저전류 조건별 현 수준','M','지령과 실제 고조파 크기를 함께 확인함','THD 수치만 보지 않고 d·q 지령과 기본파·고조파 RMS를 연결하여 해석함.',[
 tb([['조건','id* [Apeak]','iq* [Apeak]','I₁ [Arms]','Ih₂–₄₀ [Arms]','THD [%]']]+[[x.case_id,fmt(x.id_peak_a,2),fmt(x.iq_peak_a,2),fmt(x.i1_rms_a),fmt(x.ih_2_40_rms_a),fmt(x.thd_pct)] for _,x in low.iterrows()],h=3.75,widths=[1,1.5,1.5,1.3,1.8,1.3],size=11.3),foot('작은 기본파 전류로 나누는 상대 지표이므로 절대 고조파 값도 함께 관리함.')], 'results/baseline.csv; low-current group ≤8 Arms-equivalent','큰 Q에서 P가 작더라도 합성 전류가 크면 저전류 집합에 들어가지 않는다. 이 표의 모든 입력은 Peak A이다. 모델이 계산한 현 수준이며 실제 제품 측정값이 아니다.')
# 17
AB=pd.read_csv(R/'ablation.csv')
add('3. Analyze / 모델 내 왜곡 경로 확인','A','가정한 회로·검출 항을 제거하여 반응을 비교함','dead-time과 검출계가 THD에 미치는 영향을 수치 진단하되 실제 제품 원인으로 단정하지 않음.',[
 tb([['조건 [RMS 환산 설명]','기준 THD','dead-time=0','고속·무양자화 검출']]+[[lab]+[fmt(AB[(AB.case_id==cid)&(AB.control_tag==tag)].iloc[0].thd_pct)+'%' for tag in ['nominal','no_deadtime','ideal_sensor']] for cid,lab in [('A01','d=4, q=0'),('A02','d=8, q=8'),('A03','d=0, q=48')]],h=2.1,widths=[3,2,2,2.7]),tx('적용 목적: 모델 안에서 어떤 항이 반응을 바꾸는지 확인함.\n해석 한계: 연구자가 구성한 모델의 항 제거는 실제 HW의 독립적인 원인 규명이 아님.\n다음 판단: 기본 회로·PI·PLL을 유지한 상태에서 고조파 피드백 후보를 비교함.',y=4.75,h=1.15,size=13)], 'results/ablation.csv; src/model.py','고속 검출 조건은 sensor_hz=200000, adc_bits=0을 함께 변경했다. 두 효과를 각각 분리해 정량화한 실험은 아니다. 표 제목에도 통합 검출 변경이라고 표현한다.')
# 18
add('3. Analyze / 가인자 선정 및 제외 사유','A','현재 사양을 바꾸지 않는 제어 인자를 선정함','정격·dq 스케일·PWM/제어 주기를 고정하고, 보상 인자 범위 내에서 후보를 비교함.',[
 tb([['인자','변경 여부','선정·제외 사유'],['정격전류 / 지령 단위 / 주파수','고정','사용자 확정 사양이므로 최적화 변수로 사용하지 않음'],['Lf/Rf, sensor, dead-time','기준 고정','실제 확인값 미제공. 편차 영향은 선정 후 별도 검증'],['기본 dq PI / PLL','고정','개선 효과의 출처를 추가 피드백으로 한정'],['공진 이득 Kr','선정','특정 고조파 전류오차에 대한 피드백 크기'],['대역 파라미터 fc','선정','중심 주파수 주변의 제어 범위'],['보상 차수 조합','선정','3차 / 3·5차 / 3·5·7차를 비교']],h=3.65,widths=[2.5,1.7,5.5]),foot('모델의 실제성 개선과 제어기 성능 최적화를 같은 단계에서 섞지 않음.')], 'results/candidate_plan.csv; 구성 참고: Snubber p.10, CLLC p.10')
# 19
add('4. Improve / DOE 계획','I','3인자·3수준의 모든 27개 조합을 비교함','동일한 선정용 9개 운전조건에 모든 후보를 적용하여 243개 반응값을 취득함.',[
 tb([['인자','수준 1','수준 2','수준 3','단위'],['A: 공진 이득 Kr',6,12,18,'Ω'],['B: 대역 파라미터 fc',4,8,16,'Hz'],['C: 보상 차수','3','3·5','3·5·7','조합']],h=1.9,widths=[3,1.5,1.5,1.5,1.2]),tx('완전요인배치: 3³=27후보\n후보당 9개 반응은 서로 다른 운전조건이며 반복오차 추정용 9회가 아님.\n반응: THD 평균·최대값과 모든 보조 조건의 동시 만족 수',y=4.53,h=1.05,size=13),foot('선정규칙과 검증조건을 사전에 저장한 후 계산함.')], 'candidate_plan.csv; qa/frozen_protocol.json; NIST §5.3.3.9','순수 결정론 모델에서 같은 조건 반복을 독립표본처럼 늘리지 않는다. 후보 선정에는 230 V의 9개 조건만 사용한다. 추가 전압·편차·구조 검증 결과는 선정 이후 계산하며 재튜닝에 쓰지 않는다.')
# 20
means={f:E[E.factor==f].sort_values('level') for f in ['kr_ohm','band_hz','max_harmonic']}
add('4. Improve / 주효과 분석','I','인자별 수준 평균으로 영향 크기를 비교함','다른 인자와 9개 운전조건을 동일 가중으로 평균하여 수준별 반응 차이를 산출함.',[
 ch(['6 Ω','12 Ω','18 Ω'],[('Kr별 평균 THD',means['kr_ohm'].mean_thd,'blue')],x=.55,w=3.05,h=2.85,markers=True,min=1.5,max=3),ch(['4 Hz','8 Hz','16 Hz'],[('fc별 평균 THD',means['band_hz'].mean_thd,'gray')],x=3.78,w=3.05,h=2.85,markers=True,min=1.5,max=3),ch(['3','3·5','3·5·7'],[('차수별 평균 THD',means['max_harmonic'].mean_thd,'teal')],x=7.01,w=3.05,h=2.85,markers=True,min=1.5,max=3),tx('수준 평균 1개 = 다른 두 인자 9조합 × 운전조건 9개 = 81개 반응의 평균\n수준간 최대−최소: '+', '.join(f"{k} {v.mean_thd.max()-v.mean_thd.min():.3f}%p" for k,v in [('Kr',means['kr_ohm']),('fc',means['band_hz']),('차수',means['max_harmonic'])]),y=5.4,h=.8,size=12.5),foot('차수 조합과 Kr의 영향을 우선 검토하되, 교호작용과 제약조건을 함께 확인함.',y=6.32)], 'results/main_effects.csv; results/doe.csv','주효과는 이 설계 격자에서의 기술통계다. 그림에는 p-value 또는 유의성 임계선을 추가하지 않았다. 세 그래프는 같은 y축 범위를 사용하여 작은 fc 차이를 과장하지 않는다.')
# 21
ic=[]
for hh in [3,5,7]:ic.append((str(hh)+'차까지',J[J.max_harmonic==hh].sort_values('kr_ohm').thd_pct,['gray','blue','teal'][[3,5,7].index(hh)]))
add('4. Improve / 교호작용 분석','I','한 인자의 효과가 다른 인자 수준에 따라 달라지는지 확인함','Kr 변경 효과를 각 보상 차수에서 비교하여 단순한 인자별 선택을 보완함.',[
 ch([6,12,18],ic,w=5.9,h=3.3,markers=True,min=1,max=3.5),tb([['차수 조합','Kr 6→18 Ω의 THD 감소']]+[[{3:'3',5:'3·5',7:'3·5·7'}[hh],fmt(float(J[(J.max_harmonic==hh)&(J.kr_ohm==6)].thd_pct.iloc[0]-J[(J.max_harmonic==hh)&(J.kr_ohm==18)].thd_pct.iloc[0]))+'%p'] for hh in [3,5,7]],x=6.75,y=2.45,w=3.45,h=2.4,widths=[1,1.7],size=11.5),tx('두 인자의 효과가 달라지는지 확인하는 분석임. 선의 교차 유무만으로 판단하지 않음.',x=6.78,y=5.12,w=3.4,h=.9,size=12),foot('최종 선정은 조합별 실제 반응값과 종합 만족 수로 결정함.')], 'results/interactions.csv; results/candidates.csv','교호작용도는 나머지 인자와 운전조건을 평균한 반응이다. 회로의 실제 물리상호작용을 유일하게 식별했다는 뜻은 아니다.')
# 22
rank=C.sort_values(['combined','thd_max','thd_mean','kr_ohm','band_hz','max_harmonic'],ascending=[False,True,True,True,True,True]).head(5)
add('4. Improve / 제어 조건 선정','I','선정용 조건의 종합 만족 수를 최우선으로 비교함',f"{SEL['candidate']}를 검토 범위 내 우선안으로 선정함. 전역 최적값 또는 제품 적용 승인값은 아님.",[
 tb([['후보','Kr [Ω]','fc [Hz]','차수','종합 만족','최대 THD']]+[[x.candidate,int(x.kr_ohm),int(x.band_hz),{3:'3',5:'3·5',7:'3·5·7'}[int(x.max_harmonic)],f'{int(x.combined)}/9',fmt(x.thd_max)+'%'] for _,x in rank.iterrows()],h=2.8,widths=[1,1,1,1.8,1.6,1.6],highlight_rows=[1]),tx(f"선정: Kr={SEL['kr_ohm']:.0f} Ω, fc={SEL['band_hz']:.0f} Hz, 3·5·7차 (180/300/420 Hz)\n순서: 종합 만족 수 → 최대 THD → 평균 THD → 작은 이득·대역·차수",y=5.34,h=.9,size=13,bold=True),foot('범위 끝의 선정값이므로 더 넓은 범위의 최적성을 주장하지 않음.')], 'results/candidates.csv; selected_control.json','선정에 사용한 값은 새 V6 DOE에서 나온 값이다. 기존 V5 후보 또는 V4의 이득24 Ω 등을 가져오지 않았다. 선정 이후 검증 결과로 이 후보를 바꾸지 않는다.')
# 23
add('4. Improve / 기준조건 개선 효과','I','동일한 47개 운전조건에서 초기·선정안을 대응 비교함',f"평균 THD {s0['thd_mean']:.3f}% → {s1['thd_mean']:.3f}%. THD 만족률과 종합 만족률을 구분하여 확인함.",[
 ch(A.case_id,[('초기',A.thd_pct,'gray'),('선정안',B.thd_pct,'teal')],w=6.15,h=3.5,discrete=True,cat_skip=6,max=9),tb([['지표','초기','선정안'],['평균 THD',fmt(s0['thd_mean'])+'%',fmt(s1['thd_mean'])+'%'],['최대 THD',fmt(s0['thd_max'])+'%',fmt(s1['thd_max'])+'%'],['THD 만족',f"{s0['thd_pass_n']}/47",f"{s1['thd_pass_n']}/47"],['종합 만족',f"{s0['combined_pass_n']}/47",f"{s1['combined_pass_n']}/47"]],x=6.95,y=2.38,w=3.23,h=3.0,widths=[1.3,1,1],size=11.2),foot('47개 중 2개의 실제 RMS 미달은 THD 개선 후에도 남아 있음.')], 'results/baseline.csv; improved.csv; main_paired.csv','x축은 시간이나 생산순서가 아니라 Case ID이다. 선으로 이어 시계열처럼 표현하지 않았다. 같은 ID의 전후 차이를 계산했으며 표본모집단에 대한 t-검정은 수행하지 않았다.')
# 24
lowb=B[B.case_id.isin(low.case_id)]
add('4. Improve / 저전류 영역 확인','I','규격 마진이 부족했던 조건의 개선 폭을 확인함','전체 평균에 묻히지 않도록 합성 전류 지령 8 Arms 이하인 조건을 별도로 표시함.',[
 ch(low.case_id,[('초기 THD',low.thd_pct,'gray'),('선정 THD',lowb.thd_pct,'teal')],w=6.15,typ='column',max=9,labels=True),tb([['지표','초기','선정안'],['대상 조건',len(low),len(lowb)],['평균 THD',fmt(low.thd_pct.mean())+'%',fmt(lowb.thd_pct.mean())+'%'],['THD 만족',f'{int(low.thd_pass.sum())}/{len(low)}',f'{int(lowb.thd_pass.sum())}/{len(lowb)}']],x=6.95,y=2.5,w=3.23,h=2.35,size=11.4),tx('초기값을 목표 수치에 맞춘 결과가 아님. 이 모델에서 낮은 전류 대비 고조파의 상대 비중이 큰 조건임.',x=6.97,y=5.12,w=3.2,h=1.0,size=12),foot('이 집합을 전체 제품의 평균 성능 또는 산업 평균으로 표현하지 않음.')], 'results/current_strata.csv; baseline.csv; improved.csv','층별 구분은 사전 전류 경계≤8,8~24,24~48 Arms 환산값을 사용한다. 표시/CSV 반올림 때문에 정확히8 A인 조건이 이웃 구간으로 넘어가지 않도록 분류만8자리 반올림한다.')
# 25
u=S['selection_unused']
add('4. Improve / 선정 미사용 조건 검증','I','선정에 사용하지 않은 38개 조건을 분리하여 확인함','선정용 9개에서만 좋은 결과가 나온 것은 아닌지 동일 모델의 나머지 운전조건으로 확인함.',[
 tb([['평가 집합','조건 수','초기 THD 만족','선정 THD 만족','선정 종합 만족'],['제어 선정용',9, f"{int(A[A.case_id.isin(SEL['selected_from_ids'])].thd_pass.sum())}/9",'9/9','9/9'],['선정 미사용',38,f"{u['initial']['thd_pass_n']}/38",f"{u['selected']['thd_pass_n']}/38",f"{u['selected']['combined_pass_n']}/38"],['기준 전체',47,'42/47','47/47','45/47']],h=2.1,widths=[2.5,1,2,2,2]),tx('47 = 9 + 38\n38개는 47개에 포함되므로 별도 실험집합처럼 다시 합산하지 않음.\n같은 기본 수치모델의 검증이며 독립된 하드웨어 모델 검증은 아님.',y=4.8,h=1.1,size=13),foot('선정용 조건 ID와 해시를 사전 저장하여 검증 후 재튜닝을 차단함.')], 'qa/frozen_protocol.json; selected_control.json; main_conditions.csv','별도 검증이라는 말의 강도를 조절했다. 미사용 운전점은 설계변수 일반화의 제한된 확인이며 실물일치성이나 독립적인 검증모델을 뜻하지 않는다.')
# 26
v=S['voltage']
add('4. Improve / 전압 변화 검증','I','207 V·253 V에서도 동일 dq 전류 명령을 적용함','전류 명령을 고정했으므로 전압 변화에 따라 P₁·Q₁ 전력도 달라짐. 일정 전력 시험과 구분함.',[
 tb([['항목','초기','선정안'],['대상 조건 수',24,24],['평균 THD',fmt(v['initial']['thd_mean'])+'%',fmt(v['selected']['thd_mean'])+'%'],['THD 만족','18/24','24/24'],['종합 만족','14/24','20/24'],['잔여 미달','실제 RMS 전류 한계','4개 조건']],h=3.1,widths=[3,3,3]),tx('207×48=9.936 kVA / 253×48=12.144 kVA.\n전압 추가조건은 전류 한계의 수치 민감도 시험이며, 해당 용량의 제품 운전 승인을 뜻하지 않음.',y=5.65,h=.8,size=12.3)], 'results/voltage_conditions.csv; voltage.csv; voltage_paired.csv','명판 용량과 전압별 전류 허용범위가 확정되지 않아 추가 전압조건을 제품 정격 영역이라고 부르지 않는다. 11.52 kVA 명칭을 근거로 전류를 숨겨 제한하지 않는다.')
# 27
v=S['variation']
add('4. Improve / 회로·검출 편차 검증','I','선정 설정을 고정한 채 24개의 가정 변경 조건을 평가함','라틴 초방격으로 범위를 분산 배치했으며 제조 공차의 확률분포로 해석하지 않음.',[
 tb([['변경 항목','검증 범위'],['DC-link / 계통 주파수','380~420 V / 59.5~60.5 Hz'],['Lf / Lg','0.9~1.1 mH / 0.05~0.25 mH'],['dead-time / 검출 LPF','100~300 ns / 8~12 kHz'],['검출 offset / gain','±0.05 A / 0.995~1.005'],['지연','기본8 μs 또는24 μs / 제어 연산은16 μs 유지'],['계통 고조파','3차0~1.5%, 5차0~0.75%']],x=.55,y=2.2,w=5.7,h=3.5,widths=[2.2,3.5],size=11.8),tb([['지표','초기','선정안'],['평균 THD',fmt(v['initial']['thd_mean'])+'%',fmt(v['selected']['thd_mean'])+'%'],['THD 만족','20/24','24/24'],['종합 만족','17/24','21/24']],x=6.57,y=2.55,w=3.65,h=2.55,widths=[1.4,1,1],size=11.4),foot('R010·R012·R023의 실제 RMS 미달 3건을 보존함.')], 'results/variation_conditions.csv; variation.csv; variation_paired.csv','동일 seed와 조건 파일을 저장한다. 공진 계수는60 Hz용 선정값으로 유지하며 주파수마다 모델 지식을 이용해 재튜닝하지 않는다. 추가 지연은 연산 주기와 구분한다.')
# 28
ls=pd.read_csv(R/'structure.csv');ll=ls[ls.control_tag=='selected']
add('4. Improve / LF 전환 가정의 영향','I','실제 제품 적용성에 민감한 구조 가정을 별도로 평가함','LF 레그를 계통전압 부호로 고정하면, THD가 낮아져도 변조 제한이 발생할 수 있음.',[
 tb([['조건','id* [Apeak]','iq* [Apeak]','선정 THD','제한 시간비','종합 만족']]+[[x.case_id,fmt(x.id_peak_a,2),fmt(x.iq_peak_a,2),fmt(x.thd_pct)+'%',f'{100*x.saturation_fraction:.2f}%', '만족' if x.combined_pass else '미달'] for _,x in ll.iterrows()],h=3.4,widths=[1,1.6,1.6,1.5,1.8,1.4],size=11.5),tx('기준 모델과의 차이: 기준 LF는 브리지 전압 명령 부호를 따름.\n실제 LF 전환 로직이 확인되기 전에는 기준 모델의 Q 운전 성능을 제품 성능으로 확정하지 않음.',y=5.83,h=.84,size=12.7,color='red')], 'results/structure.csv; src/model.py lf_grid_polarity','이 페이지가 주요 모델 리스크이다. 명령부호형LF가 실제제어설계의허용사항인지 불명확하므로 이모델에서의THD개선만으로 실제Q문제해결을 주장할수없다. 구조조건6개의만족률을47조건만족률과합산하지않는다.')
# 29
f=B[~B.combined_pass]
rv=pd.read_csv(R/'variation.csv');vf=rv[(rv.control_tag=='selected')&(~rv.combined_pass)]
add('4. Improve / 잔여 미달과 전류 한계','I','기본파 지령 한계와 실제 RMS 한계를 구분함','Peak dq 벡터를 67.882 A로 제한해도 고조파·리플·검출오차 때문에 실제 RMS가 48 A를 넘을 수 있음.',[
 tb([['조건','주요 상태','선정 실제 RMS','48 A 대비 초과','처리']]+[[x.case_id,'정격 순수 Q' if x.case_id.startswith('N') else '회로·검출 편차',fmt(x.current_rms_a,6)+' A',fmt(1000*(x.current_rms_a-48),3)+' mA','미달 보존'] for _,x in pd.concat([f,vf]).iterrows()],h=3.25,widths=[1,2.2,2.4,2.1,1.7],size=11.6),tx('수 mA의 기준모델 경계 초과는 수치 해상도·계측 허용차를 함께 확인해야 함.\n편차조건의 큰 초과와 같은 위험 수준으로 단정하지 않으며, 지령 여유 또는 실제 RMS 제한 설계가 필요함.',y=5.77,h=.85,size=12.4),foot('판정 기준을 완화하거나 미달조건을 제외하여 100% 종합 만족으로 만들지 않음.',y=6.49)], 'results/main_failures.csv; variation.csv; refinement_comparison.csv','보고된 경계 초과는 모델의 엄격한≤48 A 판정이다. 하드웨어오차 허용치를 모르므로 실제제품의불합격이라고확정하지않는다. 지령전류를자동낮추는개선로직은이번DOE에포함하지않았다.')
# 30
tr=pd.read_csv(R/'transient_envelope.csv')
add('4. Improve / d·q축 과도응답 검토','I','축별 명령 변화와 q축 반전의 응답을 확인함','정상상태 THD 개선과 과도응답 개선을 동일하게 취급하지 않음.',[
 tb([['시험','명령 변화 [RMS 환산 설명]','초기 관측 정착','선정 관측 정착']]+[[cid,lab,fmt(tr[(tr.case_id==cid)&(tr.control=='initial')].estimated_settling_ms.iloc[0],2)+' ms',fmt(tr[(tr.case_id==cid)&(tr.control=='selected')].estimated_settling_ms.iloc[0],2)+' ms'] for cid,lab in [('T01','d:8→16, q:0 고정'),('T02','d:16 고정, q:0→16'),('T03','d:16 고정, q:+16→−16'),('T04','d:40→48, q:0 고정')]],h=2.4,widths=[1,4.2,2,2],size=11.7),tx('관측 정의: 저장한 dq 피드백을 중심 정렬 1주기 이동평균한 뒤 허용오차에 진입하여 유지되는 시각임.\nT03에서는 선정안의 관측 정착이 늦어짐. T04의 8.34 ms는 1/2주기 관측 하한임.',y=5.1,h=1.03,size=12.5),foot('변경하지 않은 축의 일시적 편차도 결과표에 함께 저장함.')], 'results/transient.csv; transient_envelope.csv; raw transient control logs','표에서 RMS환산을사용한것은해석용이다.모든step입력은Peak A로저장된다. 1주기필터는후처리이며 제어에들어가지않는다. 지표에 필터지연과평균화영향이 있으므로일반적인2%정착시간과직접비교하지않는다.')
# 31
ref=S['numerical_refinement'];dur=S['duration']
add('4. Improve / 수치 결과의 민감도 확인','I','시간간격과 계산기간을 변경하여 결과의 일관성을 확인함','대표조건에서만 수행한 수치 검증이며, 모든 회로 가정의 정확도를 입증한 것은 아님.',[
 tb([['검증','계산 변경','최대 THD 차이','최대 RMS 차이'],['시간간격 세분화','2 → 1 → 0.5 μs',fmt(ref['max_abs_thd_pp'],6)+'%p',fmt(1000*ref['max_abs_rms_a'],4)+' mA'],['계산기간 연장','0.75 → 1.5 s',fmt(dur['max_abs_thd_pp'],6)+'%p',fmt(1000*dur['max_abs_rms_a'],4)+' mA'],['고조파 교차계산','직접 투영 vs coherent FFT',f"{S['fft_check']['max_absolute_difference_pp']:.2e}%p",'THD 계산 비교'],['동일조건 재실행','대표 4회','전류 배열 동일','독립표본 추가 아님']],h=2.45,widths=[2.2,2.8,2.5,2.3],size=11.5),tx('대표 세분화·기간 연장 검토에서 종합 판정 변화 없음.\n조건에 따른 수치 민감도가 존재하므로 미검증 조건의 미세한 차이까지 유의하다고 주장하지 않음.',y=5.23,h=.9,size=12.7),foot('검증된 코드 재현성과 검증되지 않은 실제 HW 일치성을 분리함.')], 'qa/raw_audit.json; fft_crosscheck.csv; replay.json; results/refinement_comparison.csv; duration_comparison.csv','전류ADC양자화와스위칭사건으로세분화반응이엄밀한단조수렴은아닐수있다. 최대차는정해진대표조건의관측값이지전영역오차상한이아니다.')
# 32
add('5. Control / 성과 확인 및 최종 판단','C','THD 성과와 잔여 적용 리스크를 함께 정리함','기준조건의 THD 목표는 달성했으나, 모든 전류·구조조건을 만족한 제품 적용안으로 확정하지 않음.',[
 tb([['대상','THD 만족: 초기→선정','종합 만족: 초기→선정','최종 해석'],['기준 230 V 47조건','42/47 → 47/47','40/47 → 45/47','THD 목표 달성 / 실제 RMS 2조건 미달'],['전압 추가 24조건','18/24 → 24/24','14/24 → 20/24','실제 RMS 4조건 미달'],['편차 24조건','20/24 → 24/24','17/24 → 21/24','실제 RMS 3조건 미달'],['LF 구조 변경 6조건','5/6 → 6/6','1/6 → 2/6','LF 전환 가정 민감 / 제품 확인 필요']],h=2.8,widths=[2.3,2.4,2.5,3.3],size=11.4),tx('수치모델 내 제어 후보 선정 완료\n≠ 실제 OBCM의 THD 규격 만족 입증\n≠ 북미 계통연계 인증 또는 사내 BB 승인 완료',y=5.25,h=1.0,size=14,bold=True,color='red')], 'results/summary.json; paired comparison files','48 Arms와LF전환가정의잔여문제를주요결론으로둔다. 기준조건47개중THD47개만족을종합100%또는실물100%로요약하지않는다. 11.52 kVA급명칭과11.04기준점계산값은끝까지구분한다.')
# 33
add('5. Control / 표준화 및 후속 검증','C','사양·조건·코드·원자료를 연결하여 관리함','다음 변경은 보고서 숫자 수정이 아니라 사양 변경 → 모델 변경 → 동일시험 재계산의 순서로 수행함.',[
 tb([['관리 항목','관리 방법','재검증 조건'],['최우선 사양','specification.json + 실행 전 assertion','전압·전류·Peak/RMS·클록 변경'],['시험조건','사전 고정 CSV·seed·선정조건 ID','조건 추가 또는 판정 기준 변경'],['제어 설정','selected_control.json와 선정규칙','PI/PLL/공진기·delay 변경'],['원시 데이터','실행 ID·SHA-256·명령/파형 로그','코드/가정과 해시 불일치'],['실물 후속검증','LF 동작·검출·회로값·RMS 제한 확인','확보한 HW로 모델 correlation'],['문서 개정','V6 별도 보존 / V5 성과 근거 배제','사내 MBB 검토 및 요구사항 확정']],h=3.6,widths=[2,4,3.7],size=11.8),foot('코드·데이터 검증에 합격해도 실제 제어 SW 적용은 별도 승인해야 함.')], 'qa/frozen_protocol.json; docs/Model_and_Conventions.md; delivery manifests')
# 34
add('5. Control / 정량·정성 성과의 범위','C','근거가 없는 재무 성과를 산정하지 않음','실측 시험공수·재시험 비용·양산 물동 정보가 없어 비용 절감액은 계산하지 않았음.',[
 tb([['구분','확보한 결과','주장하지 않는 내용'],['정량 성과','동일 조건 THD 감소·설계기준 만족 수','양산 불량률·고객 인증 합격률'],['개발 산출물','Peak dq·1:1 클록 수치모델, 후보 선정','실제 양산 코드와 완전 동등'],['재현성','원시 파형·조건·코드·해시·검증 기록','실측 근거 없이 모델 정확도 확정'],['잔여 리스크','RMS 경계, LF 전환, 미제공 회로·규격','미달조건을 제외한 전영역 만족'],['다음 의사결정','명판 전압·LF 로직·계측사양 우선 확인','V5 수치를 재활용하거나 정격비로 환산']],h=3.45,widths=[1.7,4.2,3.8]),foot('V6는 최신 사양을 반영한 새로운 참조 수치연구로 관리함.')], 'results/summary.json; docs/V6_Review.md','기존사례처럼성과와관리산출물로종결하되 없는재무근거를추정하지않는다. 본문은34쪽까지이며 이후는용어·계산근거·상세표이다.')
MAIN=len(slides)
# 35-40 glossary
G=[
('사양·단위',[('제품급 명칭','11.52 kVA급','사용자가 지정한 명칭. 230×48의 계산값이 아님.'),('기준점 용량','230 V×48 A=11.04 kVA','해석에 사용한 입력의 피상전력.'),('Peak dq','피크값 보존 d·q 좌표','DC 값이라는 사실과 RMS 크기 정의는 별개.'),('전류 벡터 한계','sqrt(id²+iq²)≤67.882 Apeak','각 축에 각각67.882를동시지령할수없음.'),('RMS 전류','파형 제곱 평균의 제곱근','스위칭 리플·고조파를 포함한 실제파형 판정.'),('제어주기','16 μs','PWM주기16 μs와같음.62.5 kHz로1:1 연산.')]),
('신호·전력',[('id* / iq*','외부 DC 전류 지령 [Apeak]','d축 유효성분, q축 무효성분.'),('Theta','SOGI-PLL 내부 계통 동기각','외부 유·무효전력 명령이 아님.'),('P₁ / Q₁','기본파 유효·무효전력','모델의 +Iq는진상, Q₁=−V₁ Iq/√2.'),('Ptotal','실제 v(t)i(t)의 구간 평균','고조파가있으면P₁과다를수있음.'),('I₁ / Iₕ','기본파 / h차 고조파 RMS','THD분모와절대고조파를구분.'),('THD₂–₄₀','100×sqrt(Σ₂⁴⁰Ih²)/I₁','DC·40차초과·스위칭리플 제외. 인증TRD와다름.')]),
('모델·시간축',[('HF / LF','고주파 / 저주파 bridge 레그','LF의실제전환로직은미확인.'),('dead-time','양쪽 스위치 turn-on의 공백','V6기준200 ns는가정값.'),('ADC 중앙 샘플','PWM시작후8 μs의전류취득','사용자가확정한항목이아닌모델가정.'),('FIFO','지연된 명령을 순서대로 적용하는 저장구조','이전미적용명령을덮어쓰지않음.'),('샘플→적용 지연','기본8 μs / 추가지연민감도 별도','지연이늘어도제어주기는16 μs.'),('수치 시간간격','출력2 μs / 비교1·0.5 μs','제어주기와다른적분·파형저장간격.')]),
('제어·판정',[('SOGI','직교 성분을 생성하는 필터','가상β축을구성.실제두번째AC전류가아님.'),('dq PI','축별 전류오차의 비례·적분 제어','800 Hz는설계파라미터.측정대역폭이아님.'),('준공진 피드백','특정 고조파 부근의 오차제어','3·5·7차는60 Hz에서180·300·420 Hz.'),('Kr / fc','공진 이득 [Ω] / 대역 파라미터 [Hz]','fc는PWM주파수나계통기본파가아님.'),('포화 시간비','전압 제한이 발생한 평가 비율','미세전압오차또는THD자체가아님.'),('종합 만족','THD와모든보조조건을동시만족','THD만족수와종합만족수를구분.')]),
('시험·데이터',[('운전조건','Id/Iq·전압·회로가정의조합1개','실물시료1대라는뜻이아님.'),('해석 실행','조건1개에제어설정1개를적용','초기·선정비교는같은조건의2회실행.'),('선정용 / 미사용','47개 중9개 / 나머지38개','9+38=47.38을별도로합산하지않음.'),('전압 / 편차 검증','각24개의별도목적조건','서로다른분모의만족률을혼합하지않음.'),('시간 표본','파형저장시각마다의전류값','15계통주기의125000표본은반복시험수가아님.'),('회귀시험','변경 후 같은 기능·성능 시험을 재실행','회귀분석(regression analysis)과다름.')]),
('통계·신뢰성',[('DOE','인자·수준 조합을 계획한 실험','3인자×3수준=27후보,반응243개.'),('주효과','다른조건을평균한수준별반응차이','선정한범위내기술통계, p-value아님.'),('교호작용','한인자효과가다른인자수준에의존','그래프선교차만으로판정하지않음.'),('제곱합 기여도','총 반응변동의 요인별 분해 비중','실제제품원인기여율·불량원인비율아님.'),('모델 보정 / 검증','입력맞춤 / 별도근거와대조','V6는기존THD값으로보정하지않음.'),('%p / %','비율의차이 / 상대비율','2.44%−1.00%=1.44%p,상대감소율과다름.')])]
for gi,(title,items) in enumerate(G,1):
 add(f'용어집 {gi:02d} / {title}','C','보고서에서 사용하는 의미와 해석 한계를 명확히 함','일반 용어의 뜻뿐 아니라 이번 과제에서 사용한 범위까지 함께 설명함.',[
  tb([['용어','이번 과제의 정의','주의사항']]+items,h=4.12,widths=[1.85,3.8,4.05],size=11.2)],'docs/Model_and_Conventions.md; src/model.py; specification.json','용어에붙은수치는V6사양과코드에해당한다. 과거버전의정격·단위·주기를이어받지않는다.')
# 41
add('부록 A01 / 제어·전력 계산식','C','피크 dq와 전력의 환산관계를 고정함','정격48 Arms에대한피크변환은한번만수행하며,API에다시√2를곱하지않음.',[
 tx('id = iα cosθ + iβ sinθ\niq = −iα sinθ + iβ cosθ\niα = id cosθ − iq sinθ',y=2.18,h=1.4,size=18,bold=True),tx('P₁ = V₁ id/√2,   Q₁ = −V₁ iq/√2\nI₁,rms = sqrt(id²+iq²)/√2\nS₁ = V₁ I₁,rms',y=3.86,h=1.28,size=18,bold=True),tx('실제 고조파·DC·스위칭 리플이 있으면 Vrms×Irms와 S₁은 다를 수 있음.\n전압의 고조파가 있는 경우 전체 유효전력은 mean(v·i)로 별도 계산함.',y=5.65,h=.9,size=12.8)], 'src/model.py measure(); qa/unit_tests.log','좌표계는alpha cos기준이며beta는sin위상이다. 초기및선정안모두동일부호를유지한다. 검증테스트는축변환왕복·P/Q부호·정격전류를각각확인한다.')
# 42
add('부록 A02 / 준공진기 디지털 구현','C','모든 계수를16 μs 제어시간축으로 다시 산출함','V4/V5의 계수나50 Hz 중심주파수를 재사용하지 않음.',[
 tx('Gₕ(s) = 2Krωc·s / (s² + 2ωc·s + ωh²)\nωh = 2π·60·h,  h∈{3,5,7};   ωc = 2πfc\nK = ωh / tan(ωhTs/2),   Ts = 16 μs',y=2.18,h=1.25,size=16.8,bold=True),tx('D = K² + 2ωcK + ωh²\nb₀ = 2KrωcK/D,  a₁ = 2(ωh²−K²)/D,  a₂ = (K²−2ωcK+ωh²)/D\ny[n] = b₀(e[n]−e[n−2]) − a₁y[n−1] − a₂y[n−2]',y=3.84,h=1.25,size=14),tx('각공진출력±30 V, 적분상태±150 V의가정제한을적용하고발생여부저장.\n주파수민감도시험에서도60 Hz용공진계수를고정함.',y=5.65,h=.8,size=12.7)], 'src/model.py coefficients(), run_core(); Imperix PR controller','공진기의각극점이단위원내인지검사한다. 이것은공진필터단독의안정성을확인할뿐전체비선형폐루프의안정증명은아니다.')
# 43
add('부록 A03 / 제곱합 분해와 미적용 검정','C','27개 후보 평균의 변동을 요인별로 분해함','오차자유도를 확보하지 못한 분해이므로 F검정·p-value를 계산하지 않음.',[
 tb([['항','자유도','제곱합','기여도 [%]']]+[[x.term.replace('kr_ohm','A').replace('band_hz','B').replace('max_harmonic','C'),int(x.df),fmt(x.SS,6),fmt(x.share_percent)] for _,x in SS.iterrows()]+[['합계',26,fmt(SS.SS.sum(),6),'100.000']],h=3.58,widths=[3,1.4,2.5,2.6],size=11.1),tx('A=Kr, B=fc, C=차수조합. 자유도2+2+2+4+4+4+8=26.\nC의기여도가크다는것은해당격자의반응변동설명이며실제고장원인의비율이아님.',y=6.04,h=.63,size=11.8)], 'results/factorial_decomposition.csv; src/analyze.py; NIST §5.3.3.9','모든교호항을포함한포화모형에는잔차자유도가없다. 교호항을0으로간주하여강제로오차항을만들지않았다. 실물표본또는정당한확률모형없이다른모집단의신뢰구간을붙이지않는다.')
# 44
add('부록 A04 / 대응 비교와 만족률 해석','C','같은 Case끼리 비교하여 변화량을 계산함','개선효과의집계대상과분모를명시하고,추론통계와유한조건비교를구분함.',[
 tx('ΔTHDᵢ = THD초기,ᵢ − THD선정,ᵢ\n평균 감소량 = ΣΔTHDᵢ / N\nTHD 만족률 = 만족 조건 수 / 대상 조건 수 × 100',y=2.2,h=1.3,size=17,bold=True),tb([['질문','이번에 적용한 방법','적용하지 않은 주장'],['같은조건에서개선됐는가?','동일Case의전후차이','제조모집단에대한t검정'],['어느범위에미달이남는가?','전류크기·집합별층별표','모든조건의가중치를임의변경'],['새부작용이생겼는가?','항목별판정전이','종합만족률만보고부작용없음'],['신뢰구간은?','확률모형미정으로산출하지않음','조건수만으로제품신뢰도환산']],y=3.78,h=2.55,widths=[2.7,3.3,3.8],size=11.5)], 'results/*_paired.csv; NIST §7.3.1.1','기준47개는전체47개설계조건을모두계산했으므로그유한집합만족률자체의표본오차는논점이아니다. 다른조건또는실물제품에대한불확도는모델오차·범위선정문제이며샘플수만늘려해결되지않는다.')
# 45,46 candidates
for st,en in [(0,14),(14,27)]:
 part=C.iloc[st:en]
 add(f'부록 A05 / DOE 전체 후보 {st+1}~{en}','C','최종 선정 외의 후보도 모두 보존함','결과가좋은후보만제시하지않고모든27조합의최대·평균THD와종합만족수를기록함.',[
 tb([['후보','Kr','fc','차수','종합 만족','최대 THD','평균 THD']]+[[x.candidate,int(x.kr_ohm),int(x.band_hz),{3:'3',5:'3·5',7:'3·5·7'}[int(x.max_harmonic)],f'{int(x.combined)}/9',fmt(x.thd_max),fmt(x.thd_mean)] for _,x in part.iterrows()],h=4.37,widths=[1.2,1,1,1.8,1.5,1.6,1.6],size=10.6)], 'results/candidates.csv; results/doe.csv','Kr단위Ω, fc단위Hz, THD단위%. 이표의각반응은9개다른운전조건을요약한것이며9회반복표본의평균과표준오차가아니다.')
# 47,48 nominal condition IDs compact
main=pd.read_csv(R/'main_conditions.csv')
for st,en in [(0,24),(24,47)]:
 rows=[]
 for k in range(st,en,2):
  cells=[]
  for j in [k,k+1]:
   if j<en:
    x=main.iloc[j];cells += [x.case_id,fmt(x.id_peak_a,2),fmt(x.iq_peak_a,2),'선정' if x.selection_used else '미사용']
   else:cells += ['','','','']
  rows.append(cells)
 add(f'부록 A06 / 기준 운전조건 ID {st+1}~{en}','C','모든 입력은 Peak A이며230 Vac에서동일하게적용함','선정용9조건의ID를표시하여검증대상과선정대상의관계를확인할수있도록함.',[
 tb([['ID','id*','iq*','역할','ID','id*','iq*','역할']]+rows,h=4.1,widths=[1.1,1.1,1.1,1.1,1.1,1.1,1.1,1.1],size=10.5),tx('단위 Apeak / 동일 d·q조합을 초기·선정 제어로 각각 계산함.',y=6.55,size=11.2)], 'results/main_conditions.csv; qa/frozen_protocol.json')
# 49
refs=[['사례','반영한 구성','V6에서 구분한 점'],['LDC Snubber','변경가능인자·효율등부작용','설계지표와다른제약을동시확인'],['OBC CLLC','해석경로·DOE·선정근거','실측파라미터없음을명시'],['DC CAP','최저온도안의부작용기각','THD만족과전류미달구분'],['Heatsink / Tub Outer','CAE설계제안·후속실물검증','모델보정·실물검증을승계하지않음'],['GNSS / TIG / HONDA','현수준·조건·적용계획','실험조건과측정단위일관성'],['NFC / HMI / 디스플레이','요구전개·SW변경·관리기준','미실행통계검정수치복제금지']]
add('부록 A07 / 기존 11개 보고서와 비교','C','문장·구성과 증거 연결을 참고하되 데이터의 성격은 구분함','기존합격사례의통계출력형식을그대로복제하지않고V6자료구조에맞춰설명함.',[tb(refs,h=3.8,widths=[2.5,3.4,3.8],size=11.4)], '첨부된 기존 11개 PPTX; docs/V6_Review.md','원본슬라이드이미지나회사로고·서명을복사하지않는다. V6는흰배경·회색제목띠·표·DMAIC표시·결과해석박스의공통구성요소만반영한다. 합격사례의승인상태를V6에승계하지않는다.')
# 50
add('부록 A08 / 근거 문서와 재현 방법','C','모델·판정·결과·검토 기록을 함께 제공함','모든핵심수치는V6원시파형또는최초사용자사양으로추적가능하도록파일명을연결함.',[
 tb([['파일 / 자료','확인할 내용'],['specification.json','사용자 확정값 / 계산값 / 추가가정 / 잠정판정'],['src/model.py · study.py','Peakdq입력·1:1클록·스위칭·후보선정경로'],['results/*.csv · selected_control.json','전조건반응값·미달조건·고조파·최종설정'],['waveforms/*.npz','전류원시파형·제어로그·PWM명령출처·metadata'],['qa/*.json · *.csv','사양해시·단위검사·원자료재계산·FFT·재현'],['sources/references.md','TI ePWM, Imperix dq/SOGI/PR, NIST 실험계획'],['docs/*.md','모델규약·통계해설·용어집·V6검토기록']],h=3.85,widths=[3.8,5.9],size=11.6),tx('재실행: 새폴더에서 src/test_model.py → src/study.py → src/analyze.py → src/make_report.py',y=6.48,size=10.9)], 'README.md; sources/references.md; delivery manifests','study.py는원시파형경로가이미있으면덮어쓰지않고중단한다. 원본결과폴더를보존한채새복사본에서waveforms/results를비워재실행한다. 보고서만다시만드는경우make_report.py만실행하며시뮬레이션을반복하지않는다.')

# Direct waveform and harmonic evidence; no smoothing is used for metric computation.
za=np.load(ROOT/'waveforms/baseline_N015_initial.npz');zb=np.load(ROOT/'waveforms/improved_N015_selected.npz')
tt=np.linspace(.7,.7+1/60,301)
def displaywave(z):
 return np.interp(tt,float(z['t0_s'])+np.arange(len(z['current_a']))*float(z['dt_s']),z['current_a']).tolist()
ha=A[A.case_id=='N015'].iloc[0];hb=B[B.case_id=='N015'].iloc[0]
add('부록 A09 / 대표 전류 파형과 차수별 변화','C','저전류 조건 N015의 파형과 고조파를 함께 확인함','id*=5.656854 Apeak, iq*=0, 230 V / THD 7.810% → 3.167%.',[
 ch([f'{1000*(t-tt[0]):.2f}' for t in tt],[('초기',displaywave(za),'gray'),('선정안',displaywave(zb),'teal')],x=.55,y=2.2,w=5.7,h=3.4,min=-7,max=7,cat_skip=60,legend=True),
 tb([['차수','초기 [Arms]','선정 [Arms]']]+[[h,fmt(ha[f'h{h}_rms_a'],4),fmt(hb[f'h{h}_rms_a'],4)] for h in [3,5,7,9,11]],x=6.5,y=2.35,w=3.7,h=2.75,widths=[1,1.5,1.5],size=11.3),
 tx('가로축: 시간 [ms] / 세로축: 전류 [A]\n표시는 301개로 줄였으나 지표는 원시 전체 파형에서 계산함.',y=5.72,h=.65,size=11.8),
 tx('3·5·7차는 감소했으나 9·11차는 증가함. THD 감소가 모든 차수의 개선을 뜻하지 않음.',y=6.4,size=11.4,color='red')],
 'waveforms/baseline_N015_initial.npz; improved_N015_selected.npz; results/baseline.csv; improved.csv',
 '파형 표시만 시간 간격을 줄였다. THD·RMS·피크 계산은 저장한 원시 파형을 사용한다. DC 성분도 별도로 기록하며 이 표의 THD 계산에서는 제외한다. 개별 고조파 제한과 DC 주입의 실제 규격 검증은 이번 연구의 합부 판정에 포함하지 않았다.')
# Keep DMAIC order: finish test definition before starting measurement/model sections.
slides=slides[:6]+slides[10:13]+slides[6:10]+slides[13:]
from wording import polish
slides=polish(slides);G=polish(G)

spec=dict(title='11.52 kVA급 북미 V2G / 230 Vac 48 Arms / V6',author='Baek Seungwoo',font='Malgun Gothic',width=10.833333,main_count=MAIN,dataset=f"SSBB-V6-20260928 / {S['campaign_runs']} new switching runs / Peak dq / 16 us",test_map_page=7,glossary_page=MAIN+1,results_page=23,stage_pages={'D':2,'M':10,'A':17,'I':19,'C':32},slides=slides)
(ROOT/'report/deck_v6.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n')
build(spec,ROOT/'report/SSBB_V6_Submission_BaekSeungwoo.pptx')
(ROOT/'report/slide_text.md').write_text('\n\n'.join(f"## {i+1}. {s['title']}\n\n{s.get('subtitle','')}\n\n{s.get('message','')}\n\n"+'\n'.join(e.get('text','') if e['kind']!='table' else '\n'.join(' | '.join(map(str,row)) for row in e['rows']) for e in s.get('elements',[]))+f"\n\n근거: {s.get('source','')}\n\n{s.get('notes','')}" for i,s in enumerate(slides)),encoding='utf-8')
# Glossary and summary are generated from the same report source.
(ROOT/'docs/Glossary.md').write_text('# V6 용어집\n\n'+'\n\n'.join('## '+heading+'\n\n'+'\n\n'.join('**'+term+'**: '+definition+' '+caution for term,definition,caution in items) for heading,items in G)+'\n',encoding='utf-8')
summary=f"""# V6 결과 요약

확정 입력: 230 Vac, 48 Arms, Peak dq, PWM·제어 모두62.5 kHz / 16 μs.
제품급 명칭11.52 kVA와 기준점230×48=11.04 kVA의 불일치는 보존·명시. 240 V로 바꾸지 않음.

| 평가 집합 | 초기 평균 THD | 선정 평균 THD | 초기 THD 만족 | 선정 THD 만족 | 선정 종합 만족 |
|---|---:|---:|---:|---:|---:|
"""
for label,key in [('기준230 V','nominal'),('선정미사용(기준에포함)','selection_unused'),('전압추가','voltage'),('회로·검출편차','variation'),('LF구조변경','structure')]:
 x=S[key];u=x['initial'];v=x['selected'];n=u['n'];summary+=f"| {label} {n}조건 | {u['thd_mean']:.4f}% | {v['thd_mean']:.4f}% | {u['thd_pass_n']}/{n} | {v['thd_pass_n']}/{n} | {v['combined_pass_n']}/{n} |\n"
summary+=f"\n선정: Kr={SEL['kr_ohm']:g} Ω, fc={SEL['band_hz']:g} Hz, 3·5·7차. 모든수치는새V6데이터로계산. 총{S['campaign_runs']}회 + 대표4회재실행. 단위검사28개, 원자료재계산502회, coherent FFT452회.\n\n모든제품요구사항의충족을입증한것은아님. 기준정격순수Q의실제RMS초과2조건, 편차RMS초과3조건, LF전환가정민감성을추가검토해야함. 실제HW및인증검증미실시.\n"
(ROOT/'report/V6_Summary.md').write_text(summary,encoding='utf-8')
print('SLIDE COUNT',len(slides),'MAIN',MAIN)
