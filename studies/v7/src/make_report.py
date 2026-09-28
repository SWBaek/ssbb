"""Fresh V7 technical presentation. Reads V7 results only; no company guide content.
The internal submission edition is assembled separately and is not published.
"""
from pathlib import Path
import json, math
import numpy as np
import pandas as pd
from model import ROOT, SPEC, SQ2
from pptx_builder import build

R=ROOT/'results'; O=ROOT/'report'; S=json.loads((R/'summary.json').read_text())
A=pd.read_csv(R/'baseline.csv'); B=pd.read_csv(R/'improved.csv'); D=pd.read_csv(R/'doe.csv')
C=pd.read_csv(R/'candidates.csv'); E=pd.read_csv(R/'main_effects.csv'); J=pd.read_csv(R/'interactions.csv')
SS=pd.read_csv(R/'factorial_decomposition.csv'); ST=pd.read_csv(R/'current_strata.csv')
SEL=S['selected']; sl=[]
F=lambda x,n=3:f'{float(x):.{n}f}'
RT=lambda n,N:f'{int(n)}/{int(N)} ({100*n/N:.1f}%)'
H=lambda h:{3:'3',5:'3·5',7:'3·5·7'}[int(h)]

def tx(t,x=.55,y=2.2,w=9.7,h=.65,size=13,bold=False,color='ink'):
 return dict(kind='text',text=str(t),x=x,y=y,w=w,h=h,size=size,bold=bold,color=color)
def tb(rows,x=.55,y=2.2,w=9.7,h=3.6,widths=None,size=12,**kw):
 return dict(kind='table',rows=[[str(v) for v in r] for r in rows],x=x,y=y,w=w,h=h,widths=widths or [1]*len(rows[0]),size=size,**kw)
def ch(cat,ser,x=.55,y=2.2,w=6.1,h=3.5,typ='line',**kw):
 return dict(kind='chart',categories=[str(x) for x in cat],series=[dict(name=n,values=[float(v) for v in a],color=c) for n,a,c in ser],x=x,y=y,w=w,h=h,type=typ,**kw)
def bx(t,x,y,w,h,size=13):return dict(kind='box',text=t,x=x,y=y,w=w,h=h,size=size,fill='white',align='center')
def ln(x,y,x2,y2):return dict(kind='line',x=x,y=y,x2=x2,y2=y2,arrow=True,color='ink')
def foot(t):return tx('→ '+t,y=6.36,h=.55,size=12.1,bold=True,color='teal')
def add(sid,title,stage,sub,msg,els,source,notes=''):
 sl.append(dict(sid=sid,title=title,stage=stage,subtitle=sub,message=msg,elements=els,source=source,notes='[목적 및 방법]\n'+sub+'\n[결과 해석]\n'+msg+'\n'+notes+'\n[적용 범위]\n240 Vac · 48 Arms · 11.52 kVA · Peak dq · PWM/제어 62.5 kHz(16 μs). 회로·검출계·LF 전환 및 잠정 판정은 참조모델의 가정이며 실물 검증이 아님.'))

def resultrows(key):
 a=S[key]['initial'];b=S[key]['selected'];n=a['n']
 return [['지표','초기 제어','선정 제어'],['평균 THD [%]',F(a['thd_mean']),F(b['thd_mean'])],['최대 THD [%]',F(a['thd_max']),F(b['thd_max'])],['THD 만족',f"{a['thd_pass_n']}/{n}",f"{b['thd_pass_n']}/{n}"],['종합 만족',f"{a['combined_pass_n']}/{n}",f"{b['combined_pass_n']}/{n}"]]

sl.append(dict(sid='cover',cover=True,title='11.52 kVA 북미 V2G AC단\ndq 전류제어의 THD 개선 검토',subtitle='240 Vac · 48 Arms · Peak dq\nPWM 및 제어 연산 모두 62.5 kHz / 16 μs',author_line='SSBB 수치해석 연구 | V7 기술 공개본',date_line='V7 · 2026.09.28\n240×48=11.52 kVA | 새 수치해석 결과 기반',source='specification.json; results/summary.json',notes='이번 공개본은 기술 사양·수치모델·분석과 검증만 담는다. 실제 제품 회로를 식별한 모델이나 인증된 제어기라는 의미는 아니다. 원시 데이터는 V7 모델에서 전부 새로 생성했다.'))
add('spec','1. Define / 대상 사양','D','확정 사양을 실행 전 검사와 데이터 기록에 연결함','공칭 전압·전류·용량의 산술관계가 일치하며, dq 단위와 두 클록을 별도로 고정함.',[
 tb([['항목','V7 적용값','확인 방법'],['공칭 AC 전압','240 Vrms','기준 조건 및 사양 검사'],['정격 AC 전류 / 용량','48 Arms / 11.52 kVA','240×48=11,520 VA'],['외부 dq 입력','id*, iq*: 피크값 A의 DC 지령','API 및 제어 로그'],['PWM / 제어 주파수','각각 62.5 kHz','실행 횟수 1:1 검사'],['PWM / 제어 주기','각각 16 μs','8 μs 중앙샘플은 별도 가정'],['dq 벡터 한계','√(id*²+iq*²) ≤ 67.882 Apeak','각 축 동시 정격 지령은 거부']],h=3.8,widths=[2.2,4.0,3.5]),foot('실제 파형의 RMS ≤48 A 판정은 기본파 dq 지령 제한과 별도로 수행함.')], 'specification.json; src/model.py assert_spec(); qa/unit_tests.json')
add('revision','1. Define / 변경 범위와 비교 원칙','D','전압 변경과 제어 개선의 효과를 혼합하지 않음','230 V 기준이었던 이전 해석을 240 V로 변경하고, 초기·DOE·개선·검증을 새로 계산함.',[
 tb([['항목','변경 / 유지','이유'],['공칭 전압','230 → 240 Vrms','사용자 사양 정정'],['공칭 용량','11.04 → 11.52 kVA','동일 48 Arms에서 산출'],['전압 변화 검증','216 / 264 Vrms','240 V의 ±10%로 설계한 추가 시험'],['Peak dq / PWM / 제어','정의 및 16 μs 유지','사용자 확인 사양'],['회로·제어 후보·시험 격자','명시한 가정과 후보 범위 유지','전압 이외의 변경을 최소화'],['성능 비교','V7 초기 ↔ V7 선정안','V6→V7 차이를 개선 성과에 합산하지 않음']],h=3.7,widths=[2.3,3.4,4]),foot('이전 결과 CSV·파형·선정값은 V7 계산 입력으로 읽지 않음.')], 'specification.json; qa/frozen_protocol.json; source_lineage.json','수치해석 구현 및 문서 템플릿을 재사용하는 것과 이전 성능 데이터의 재사용은 다르다. 검증된 모델 구현을 사양에 맞춰 수정하고 모든 수치 실행을 새로 수행했다. 전압 ±10%는 연구자가 설정한 시험범위이며 규격 운전범위의 인용이 아니다.')
add('charter','1. Define / Project Y와 기술 목표','D','시험집합과 판정식을 먼저 고정함','동일 운전조건에서 THD 기준 만족률을 높이되, 다른 제약조건 미달을 숨기지 않음.',[
 tb([['항목','정의'],['과제 범위','북미 V2G AC단의 참조 수치모델에서 고조파 전류제어 개선'],['Project Y','240 V 기준 운전조건 47개 중 THD₂–₄₀ ≤5%인 조건의 비율'],['기술 목표','THD 만족률 ≥95% : 47개 중 최소 45개 만족'],['제품 적용 전 확인조건','전류·추종·피크·포화·정상상태 조건 동시 만족'],['대상 밖','실물 제품 인증, 제조 수율, DC-link/CLLC 통합 및 실제 배포'],['목표의 성격','자체 설계 목표. 고객 또는 외부 인증 요구와 구분']],h=3.6,widths=[2.6,7.1]),foot('THD 5%와 만족률 95%는 서로 다른 지표이며 사전에 고정한 설계 기준임.')], 'specification.json; qa/frozen_protocol.json','THD 기준 만족과 모든 보조조건 만족을 분리한다. 어떤 후보도 보조조건을 만족하지 못하면 제약충족 최적안으로 부르지 않는다. 목표값을 맞추기 위한 초기 모델 보정 또는 실패조건 삭제는 수행하지 않았다.')
add('logic','1. Define / 업무 목표와 개선 지표','D','큰 목표에서 직접 측정할 수 있는 지표로 범위를 좁힘','제품의 계통연계 품질 확보를 위해 전류 품질을 개선하고, 모델 내 목표 달성 여부를 확인함.',[
 bx('Big Y\nV2G 계통연계 품질',.65,2.4,2.7,1),bx('Little y\nAC 전류 품질',4,2.4,2.6,1),bx('Project Y\nTHD 설계기준 만족률',7.2,2.4,2.7,1),ln(3.4,2.9,3.96,2.9),ln(6.66,2.9,7.15,2.9),
 tb([['이번에 확인','확보되지 않은 근거'],['Peak dq 추종과 저차 고조파 저감','실제 회로·부품·검출계·LF 전환 로직'],['동일조건 초기·개선 대응 비교','HW 파형과의 모델 일치성'],['선정 이후 조건·모델 가정의 변화','고객 규격·제조 분포·전체 안정도']],y=4.05,h=2.05,widths=[1,1]),foot('수치모델의 만족률을 양산 수율 또는 인증 통과율로 환산하지 않음.')], 'specification.json; src/model.py; results/summary.json')
add('dq','1. Define / Peak dq 지령과 전력','D','Theta는 내부 동기각이며 외부 명령이 아님','전류제어기는 피크값 기준 id*와 iq*를 직접 입력받고, 각각의 DC 성분을 추종함.',[
 tx('iα* = id* cosθ − iq* sinθ\nP₁* = V₁ id*/√2,   Q₁* = −V₁ iq*/√2',y=2.18,h=.93,size=18,bold=True),
 tb([['id* / iq* [Apeak]','기본파 RMS [A]','240 V 기본파 전력'],['67.882 / 0','48.000','P₁*=11.52 kW, Q₁*=0'],['0 / +67.882','48.000','P₁*=0, Q₁*=−11.52 kvar'],['48.000 / 0','33.941','48 Arms 운전과 다름'],['67.882 / 67.882','67.882','합성 전류 초과로 입력 거부']],y=3.36,h=2.5,widths=[2.7,2.7,4.3]),tx('+Iq는 진상전류로 정의한 모델 규약임. 실제 통신·SW 부호 규약은 별도 확인 필요.',y=6.31,size=12,color='red')], 'src/model.py validate(), run_core(), measure(); qa/unit_tests.log','양의 d축은 계통 송전 유효전류이다. q축은 이 Park 정의에서 양수일 때 진상이며 Q는 음수다. DC 지령은 피크값으로 정의되므로 RMS 환산은 표시를 위해 한 번만 수행한다. 실제 고객 Q 부호를 확인한 것은 아니다.')
add('tests','1. Define / 시험 구성과 수량','D','조건 수와 해석 실행 수를 구분함','기준조건 47개 안에서 선정용 9개와 미사용 38개를 구분하며, 검증 집합별 분모를 유지함.',[
 tb([['대상','수량·구성','확인 목적'],['기준 운전조건','240 V, 직접 dq 조합 47개','초기·선정안 전체 비교'],['제어 선정용','기준조건 중 9개','27개 후보의 선택'],['선정 미사용','47−9=38개','선정 후 같은 모델의 나머지 조건 확인'],['전압 변화 조건','216 / 264 V × dq 12조합 =24개','같은 전류지령의 전압 민감도'],['회로·검출계 편차','가정 범위의 24개 조건','후속 변동 영향 확인'],['LF 전환 방식 변경','별도 6개 조건','회로 구조 가정의 영향']],h=3.7,widths=[2.3,3.9,3.5]),foot('DOE: 27후보×9조건=243회. 같은 조건의 초기·선정 비교는 2회 실행임.')], 'results/*_conditions.csv; results/candidate_plan.csv; qa/frozen_protocol.json','기준전류 격자는 RMS 환산 설명용 값 d={0,4,8,16,32,48}, q=0 및 ±같은 수준으로 생성하고 합성48 A 이내의 비영 지령만 선택한다. 실제 API는 모두 Peak A이다. 9개 선정용 조건은 d=4,8,16에서 q=−d,0,+d이다. 38개는 47개에 포함된다.')
add('metrics','1. Define / THD 측정과 판정','D','고조파 정의·평가 구간·분모를 고정함','THD₂–₄₀와 정격전류 대비 고조파 비율을 구분하고, 실제 전체 RMS 전류도 별도로 계산함.',[
 tx('THD₂–₄₀ [%] = 100 × √(Σₕ₌₂⁴⁰ Iₕ²) / I₁\nProject Y [%] = THD 기준 만족 조건 수 / 47 × 100',y=2.16,h=1.08,size=17,bold=True),
 tb([['항목','이번 해석의 정의'],['기본파 / 차수','60 Hz 기준 2~40차, 상한 2.4 kHz'],['평가 구간','마지막 계통 15주기; 60 Hz일 때 0.25 s'],['DC / 스위칭 리플','THD₂–₄₀에서 제외, 실제 RMS 전류에는 포함'],['시간 표본','2 μs로 저장한 파형값. 독립 실험 표본 수가 아님'],['미포함 규격 판정','개별 고조파·DC 주입·인증용 왜곡 지표와 동일성 미검증']],y=3.56,h=2.55,widths=[2.2,7.5]),foot('수치 판정용 THD 5%를 북미 계통연계 인증의 합격기준으로 인용하지 않음.')], 'src/model.py harmonics_projection(), measure(); specification.json','고조파 RMS를 기본파 RMS로 정규화하므로 낮은 전류에서 상대왜곡이 커질 수 있다. ih_over_rated_pct는 Iₕ합성을48 A로 나눈 별도 진단지표다. 인증용 지표와의 동등성은 본 해석에서 검증하지 않았다.')
add('guard','1. Define / 보조 조건과 종합 판정','D','THD 개선만으로 제어안을 채택하지 않음','각 조건의 THD·전류 추종·전류 한계·제한 동작·주기적 정상상태를 동시에 판정함.',[
 tb([['항목','판정식 / 한계','근거 구분'],['d축·q축 오차','각각 |e|≤max(0.3, 0.02×|idq*|) Apeak','자체 설계 기준'],['실제 RMS 전류','평가 파형 전체 RMS≤48 A','사용자 정격 반영'],['전류 피크','평가 구간 |i|max≤75 A','가정한 한계'],['전압·보상 제한','전압 제한 시간비≤1%; 공진·적분 제한 미발생','자체 설계 기준'],['주기적 정상상태','연속주기 1~7차 계수변화의 RMS≤max(0.03,0.002 Iref,rms)','자체 수치 판정'],['종합 만족','THD와 위 항목을 모두 만족','논리 AND']],h=3.95,widths=[2.0,5.65,2.05],size=11.5),tx('48 A 이외의 보조 한계는 확인된 제품 요구사항이 아니며 적용 전 합의가 필요함.',y=6.43,size=11.8,color='red')], 'src/model.py measure(); specification.json','주기성 판정은 PWM 리플의 주기별 비동기를 피하기 위해 1~7차 Fourier 계수 변화를 사용한다. 전체 비선형 폐루프 안정성 증명이 아니다. 전류피크75 A도 실제 보호사양이 아니며 RMS 정격에서 자동 도출된 값이 아니다.')
add('model','2. Measure / 측정 시스템 구성','M','회로·제어·검출 경로를 분리함','기본 dq PI와 PLL은 유지하고, 개선 단계에서는 고조파 전류오차 피드백만 추가함.',[
 bx('id* · iq*\nPeak A, DC',.55,2.5,1.6,.86),bx('dq PI\n전향·교차결합 보상',2.6,2.5,2.05,.86),bx('16 μs 연산\n명령 갱신 FIFO',5.13,2.5,1.9,.86),bx('PWM 62.5 kHz\n브리지·RL·계통',7.52,2.5,2.47,.86),ln(2.18,2.93,2.57,2.93),ln(4.68,2.93,5.1,2.93),ln(7.06,2.93,7.49,2.93),
 bx('LPF + ADC\n전류 검출',6.2,4.25,2.05,.83),bx('SOGI 직교축\ndq 변환',2.65,4.25,2.1,.83),ln(8.8,3.39,8.8,4.67),ln(8.76,4.67,8.28,4.67),ln(6.16,4.67,4.78,4.67),ln(3.7,4.21,3.7,3.4),
 bx('SOGI-PLL → θ\n계통전압으로 내부 동기각 생성',.65,5.6,4.35,.65,size=12),bx('준공진 피드백 추가\n기본 dq 명령·회로는 변경하지 않음',5.42,5.6,4.55,.65,size=12)], 'src/model.py; specification.json','SOGI의 가상β축을 이용하는 단상 dq 모델이다. DC-link는 강성 전원이며 외부 전압제어와 CLLC 동역학은 포함하지 않는다. 실제 OBCM 전체 제어도 또는 확인된 양산SW 블록도로 사용하지 않는다.')
add('timing','2. Measure / PWM·제어 동기','M','매 PWM 주기마다 제어 연산 1회 수행함','16 μs의 제어 주기와 ADC 샘플→PWM 반영 지연을 서로 다른 항목으로 기록함.',[
 tb([['PWM 구간 [μs]','ADC·연산 시각 [μs]','명령 반영 [μs]','명령 유지 구간'],['0~16','8','16','16~32 μs'],['16~32','24','32','32~48 μs'],['32~48','40','48','48~64 μs'],['기준 실행0.75 s','제어46,875회','PWM46,875주기','1:1 검사']],h=2.65,widths=[2.3,2.8,2.3,2.3]),
 tx('확정: PWM=제어=16 μs.\n가정: 중앙 샘플링, 다음 경계 반영(기본 지연 8 μs).\n추가 지연에서는 FIFO의 적용 시각만 늦추며 연산 주기는 바꾸지 않음.',y=5.15,h=1.0,size=13),foot('명령의 순서·출처·반영 주기를 저장 로그로 확인함.')], 'src/model.py run_core(); qa/raw_audit.json; TI ePWM API','TI 문서에서 ADC 이벤트와 PWM shadow load는 구분된 설정이다. 샘플링 및 적용 지연은 실제 MCU 설정을 제공받지 않아 가정했다. 제어 주기가16 μs라는 사실만으로 그 지연값이 확인되었다고 말하지 않는다.')
add('physics','2. Measure / 회로 모델 및 가정','M','스위칭 상태를 계산하되 실제 HW 모델로 과장하지 않음','구간별 브리지 전압으로 RL 전류와 센서 응답을 계산하며, 미제공 회로 정수는 가정값임.',[
 tx('L di/dt = ubridge − vg − Ri\nubridge = (HF pole − LF pole) Vdc',y=2.18,h=.8,size=17,bold=True),
 tb([['항목','기준 가정 / 구현'],['DC-link / Lf / Lg','400 V 강성 전원 / 1.0 mH / 0.1 mH'],['Rf / Rg','0.08 Ω / 0.10 Ω'],['HF 스위칭','중앙정렬 PWM, 200 ns dead-time, 경계 이벤트 분할'],['LF 전환','기준: 전압 명령 부호 / 계통 부호형은 별도 민감도 시험'],['전류 검출','10 kHz 1차 LPF, 12 bit, ±100 A'],['미포함','LF blanking·Coss·열·EMI 필터·DC-link/CLLC 에너지 동역학']],y=3.17,h=3.05,widths=[2.4,7.3],size=11.6)], 'specification.json; src/model.py grid(), rl_sensor(), run_core()','수치 출력 간격은2 μs지만 switching/dead-time 사건의 시각에서 내부 구간을 나누므로200 ns를2 μs로 반올림하지 않는다. 계통전압은 각 구간 중앙값으로 근사하며 대표 시간간격 세분화로 민감도를 확인한다. LF 전환 가정이 제품과 일치하는지는 별도 확인이 필요하다.')
add('verify','2. Measure / 데이터 신뢰성 확인','M','구현 검증·수치 검증·실물 검증을 구분함','결정론적 동일 입력 반복을 Gage R&R 표본으로 만들지 않고, 계산 체계의 재현성을 확인함.',[
 tb([['구분','수행한 검증','결과의 의미'],['구현 검사',f"{S['audit']['unit_tests']['tests_run']}개 단위 검사",'단위·좌표·클록·RL·필터 계산 확인'],['원자료 검사',f"{S['campaign_runs']}개 저장 파형 재계산",'해시·지표·40개 고조파·판정 대조'],['별도 계산법',f"60 Hz {S['fft_check']['runs']}회 FFT 비교",'고조파 계산 경로 교차 확인'],['수치 민감도','2→1→0.5 μs / 0.75→1.5 s','대표조건 시간·기간 민감도'],['재실행','대표4회 전류 배열 대조','동일 환경에서의 결정론적 재현'],['실물 일치성','실제 HW 파형·회로 실측 없음','검증되지 않음']],h=3.7,widths=[2.0,3.5,4.2]),foot('자동검사 통과를 실물 측정시스템 검증 또는 제품 인증으로 대체하지 않음.')], 'qa/unit_tests.json; qa/raw_audit.json; qa/replay.json; results/refinement_comparison.csv','데이터와 코드가 일치한다는 검증과 실제 제품을 재현한다는 검증은 다르다. 실제 측정시스템 평가의 대체 인정 여부도 별도 판단 사항이며 본 보고서가 스스로 승인하지 않는다.')
s0=S['nominal']['initial'];s1=S['nominal']['selected'];lo=A[np.hypot(A.id_peak_a,A.iq_peak_a)/SQ2<=8.0000001];lb=B[B.case_id.isin(lo.case_id)]
add('baseline','2. Measure / 현 수준 파악','M','240 V 기준의 초기 제어를 새로 계산함',f"47개 기준조건의 초기 평균 THD는 {F(s0['thd_mean'])}%, 최대 {F(s0['thd_max'])}%로 확인됨.",[
 ch(A.case_id,[('초기 THD [%]',A.thd_pct,'gray'),('설계 한계5%',np.full(len(A),5.),'red')],w=6.05,discrete=True,cat_skip=6,max=math.ceil(s0['thd_max']+1)),
 tb([['항목','초기 현 수준'],['평균 THD',F(s0['thd_mean'])+'%'],['최대 THD',F(s0['thd_max'])+'%'],['THD 만족',RT(s0['thd_pass_n'],47)],['종합 만족',RT(s0['combined_pass_n'],47)]],x=6.92,y=2.55,w=3.28,h=2.65,widths=[1,1.2],size=11.5),foot('이전 THD에 정격비를 곱하거나 초기 성능을 특정 값에 맞추지 않았음.')], 'results/baseline.csv; qa/frozen_protocol.json','그래프의 가로축은 시간 순서가 아닌 조건 ID다. 출력전류가 넓은 범위로 구성된 유한집합의 평균이지 평균적인 제품/산업 성능 추정값이 아니다. 임의 초기 5~8% 보정은 하지 않았다.')
add('strata0','2. Measure / 전류 수준별 현 수준','M','전류 크기로 층별 분석하여 취약 영역을 구분함','P=0이어도 Q 지령이 있으면 전류가 흐르므로, 저전류 여부는 dq 벡터 크기로 판단함.',[
 tb([['지령 벡터의 RMS 환산 범위','조건 수','초기 평균 THD','초기 최대 THD','THD 만족']]+[[{'low_le_8Arms':'0 초과~8 A','medium_8_to_24Arms':'8 초과~24 A','high_24_to_48Arms':'24 초과~48 A'}[x.stratum],int(x.n),F(x.thd_mean)+'%',F(x.thd_max)+'%',f'{int(x.thd_pass_n)}/{int(x.n)}'] for _,x in ST[ST.control=='initial'].iterrows()],h=2.42,widths=[3.2,1.2,2,2,1.3],size=11.6),
 tx(f'저전류 {len(lo)}개 조건의 평균 THD: {F(lo.thd_pct.mean())}%\n합성 지령의 RMS 환산값 = √(id*²+iq*²)/√2\n층별 평균은 서로 다른 운전조건을 같은 가중으로 비교한 기술통계임.',y=5.05,h=1.05,size=13),foot('낮은 유효전력을 낮은 전류와 동일시하지 않음.')], 'results/current_strata.csv; results/baseline.csv','층별 경계는 사전에 정의한8/24/48 Arms 환산값이며 API는Peak A다. 시험분포를 알고리즘에 유리하게 바꾸거나 저전류 미달을 분모에서 제외하지 않는다.')
abl=pd.read_csv(R/'ablation.csv')
add('causes','3. Analyze / 가인자 도출','A','영향 가능성과 변경 가능성으로 후보를 분류함','원인을 이미 확인한 것으로 가정하지 않고, 모델에 구현된 경로와 제어로 변경할 항목을 구분함.',[
 tb([['후보','이번 과제의 취급','이유'],['HF dead-time·검출 지연','원인 가정 / 제거 비교','구현한 비선형·위상 오차의 영향 확인'],['전류 PI·PLL 기본 설정','유지','고조파 보상 개선의 효과 분리'],['L/R·계통·센서 편차','선정 후 검증 인자','실물값 미확인, 강건성 민감도 확인'],['고조파 보상 이득 Kr','DOE 인자 A','보상 강도 변화'],['공진 대역 파라미터 fc','DOE 인자 B','주파수 주변 응답과 동작 변화'],['보상 차수 조합','DOE 인자 C','3 / 3·5 / 3·5·7차의 비교']],h=3.8,widths=[2.7,3.1,3.9]),foot('모델에 넣은 오차항을 제거해 확인한 결과는 실제 제품 원인의 독립 규명이 아님.')], 'src/model.py; results/ablation.csv; results/candidate_plan.csv')
add('ablation','3. Analyze / 가정한 왜곡 경로 검토','A','하나의 가정만 변경한 진단 결과를 비교함','dead-time 제거와 검출계 이상화를 구분하여 초기 모델의 민감도를 확인함.',[
 tb([['조건','기준 THD','dead-time=0','검출계 이상화']]+[[cid]+[F(abl[(abl.case_id==cid)&(abl.control_tag==x)].thd_pct.iloc[0])+'%' for x in ['nominal','no_deadtime','ideal_sensor']] for cid in abl.case_id.unique()],h=2.25,widths=[1.5,2.5,2.7,3.0]),
 tx('검출계 이상화: LPF 200 kHz, 양자화 해제.\n실제 제품의 측정오차를 제거했다는 뜻이 아니라 모델 가정을 바꾼 진단임.\n고조파 보상은 원인 가정의 정확한 역함수를 주입하지 않고 전류오차를 사용함.',y=4.85,h=1.2,size=13),foot('진단에서 얻은 값을 제품의 치명원인 기여율로 해석하지 않음.')], 'results/ablation.csv; src/study.py','이 비교에서 출력이 변했다는 것은 모델이 해당 요소에 민감하다는 증거이다. 단독 경로의 제거가 다른 폐루프 응답도 바꿀 수 있으므로 개선량을 선형적으로 더하거나 원인 기여율로 계산하지 않는다.')
add('algorithm','4. Improve / 개선 제어 구조','I','기본 dq PI에 선택 차수의 준공진 피드백을 추가함','회로와 기본 dq 지령을 유지한 채, 실제 전류오차의 고조파 성분에 보상 전압을 생성함.',[
 tx('eα = id* cosθ − iq* sinθ − iα,meas\nu* = u*dq→α + Σ Gₕ(z) eα\nGₕ(s) = 2Krωc s / (s² + 2ωc s + ωh²)',y=2.18,h=1.35,size=16.5,bold=True),
 tb([['설정','정의'],['대상 차수','h=3 / 3·5 / 3·5·7'],['중심 주파수','60 Hz에서 180 / 300 / 420 Hz'],['제어 시간축','Ts=16 μs로 계수 계산, 사전왜곡 Tustin 이산화'],['보상 제한','각 공진 출력 ±30 V; 제한 발생 여부 별도 판정']],y=3.9,h=2.22,widths=[2.5,7.2]),foot('PLL 동기각은 내부 신호이며 외부 전류 지령 인터페이스는 변경하지 않음.')], 'src/model.py coefficients(), run_core(); Imperix TN110','유한 대역 공진항을 사용한다. 추가 가정에 해당하는 전압 제한과 주파수 고정값을 기록한다. 공진 필터 극점의 안정성은 전체 비선형 폐루프의 안정여유를 보증하지 않는다.')
add('doe','4. Improve / 실험계획과 선정 규칙','I','3인자 3수준의 모든 조합을 계산함','선정용 9개 운전조건에서 27개 제어 후보를 비교하고, 검증 결과를 보기 전에 설정을 고정함.',[
 tb([['인자','수준','분석 목적'],['A: Kr [Ω]','6 / 12 / 18','보상 이득의 영향'],['B: fc [Hz]','4 / 8 / 16','대역 파라미터의 영향'],['C: 차수 조합','3 / 3·5 / 3·5·7','보상 차수 확대의 영향'],['실행 수','27후보 ×9운전조건 =243회','다른 운전조건 9개는 반복시험9회가 아님']],h=2.65,widths=[2.6,3.2,3.9]),
 tx('선정 순서: 종합 만족 수 최대 → 최대 THD 최소 → 평균 THD 최소\n동률이면 Kr·fc·최고 차수가 작은 순으로 선정함.\n사전 저장: 사양·조건 CSV·후보·선정용 ID·선정 규칙의 해시.',y=5.18,h=.98,size=12.8)], 'qa/frozen_protocol.json; results/candidate_plan.csv; src/study.py','완전요인배치는 각 인자를 다른 인자와 균형 있게 비교할 수 있는 설계다. 각 후보의9개 반응은 목적이 다른 운전조건이므로 순수 반복오차를 추정하는 데 사용하지 않는다. 결정론적 해석이므로 실행 순서는고정되며 실험 드리프트를 모사한 무작위 반복을 추가하지 않았다.')
means={f:E[E.factor==f].sort_values('level') for f in ['kr_ohm','band_hz','max_harmonic']}
ymin=max(0,math.floor(E.mean_thd.min()*2)/2-.2);ymax=math.ceil(E.mean_thd.max()*2)/2+.2
add('effects','4. Improve / 주효과 해석','I','수준별 평균 차이로 우선 검토 인자를 판단함','다른 두 인자와 운전조건을 동일 가중 평균한 결과이며, 선택한 범위에서의 영향도임.',[
 ch(['6 Ω','12 Ω','18 Ω'],[('Kr 평균 THD',means['kr_ohm'].mean_thd,'blue')],x=.55,w=3.08,h=2.95,min=ymin,max=ymax,markers=True),ch(['4 Hz','8 Hz','16 Hz'],[('fc 평균 THD',means['band_hz'].mean_thd,'gray')],x=3.8,w=3.08,h=2.95,min=ymin,max=ymax,markers=True),ch(['3','3·5','3·5·7'],[('차수 평균 THD',means['max_harmonic'].mean_thd,'teal')],x=7.05,w=3.08,h=2.95,min=ymin,max=ymax,markers=True),
 tx('수준 평균1개: 다른 두 인자9조합 ×9운전조건 =81개 반응의 평균\n수준 간 최대−최소: '+', '.join(f'{label} {v.mean_thd.max()-v.mean_thd.min():.3f}%p' for label,v in [('Kr',means['kr_ohm']),('fc',means['band_hz']),('차수',means['max_harmonic'])]),y=5.45,h=.72,size=12.5),foot('주효과가 크다는 판단과 통계적 유의성(p-value)을 구분함.')], 'results/main_effects.csv; results/doe.csv','세 그래프는 동일 세로축을 사용한다. 범위 밖 값의 효과 또는 실제 제조 산포에 대한 기여도는 알 수 없다. 다음 페이지에서 Kr와 차수의 조건 의존성을 확인한다.')
inter=[(H(h)+'차',J[J.max_harmonic==h].sort_values('kr_ohm').thd_pct,c) for h,c in zip([3,5,7],['gray','blue','teal'])]
add('interaction','4. Improve / 교호작용 해석','I','Kr의 효과가 차수 조합에 따라 달라지는지 확인함','다른 fc 수준과 운전조건을 평균하여, 이득 변경의 효과를 차수별로 비교함.',[
 ch([6,12,18],inter,w=5.95,markers=True,min=max(0,ymin-.4),max=ymax+.3),
 tb([['차수 조합','Kr 6→18 Ω의 THD 감소']]+[[H(h),F(J[(J.kr_ohm==6)&(J.max_harmonic==h)].thd_pct.iloc[0]-J[(J.kr_ohm==18)&(J.max_harmonic==h)].thd_pct.iloc[0])+'%p'] for h in [3,5,7]],x=6.76,y=2.6,w=3.45,h=2.32,widths=[1,1.9],size=11.5),tx('선이 교차하는지만 보지 않고 수준별 효과의 차이를 확인함.',x=6.78,y=5.18,w=3.4,h=.9,size=12.5),foot('인자별로 가장 좋은 수준을 따로 고르지 않고, 실제 조합별 결과로 선정함.')], 'results/interactions.csv; results/candidates.csv','교호작용은 한 인자 변화의 효과가 다른 인자에 의존하는 현상이다. 이 설계에서는 차수 조합별 Kr 효과를 비교한다. 그 자체가 특정 제품의 물리적 원인을 독립적으로 규명한다는 의미는 아니다.')
rank=C.sort_values(['combined','thd_max','thd_mean','kr_ohm','band_hz','max_harmonic'],ascending=[False,True,True,True,True,True]).head(5)
add('selection','4. Improve / 제어조건 선정','I','사전에 정한 순서로 후보를 선택하고 설정을 고정함',f"{SEL['candidate']}: Kr={SEL['kr_ohm']:g} Ω, fc={SEL['band_hz']:g} Hz, {H(SEL['max_harmonic'])}차를 검토 범위 내 선정안으로 결정함.",[
 tb([['후보','Kr [Ω]','fc [Hz]','차수','종합 만족','최대 THD [%]']]+[[x.candidate,int(x.kr_ohm),int(x.band_hz),H(x.max_harmonic),f'{int(x.combined)}/9',F(x.thd_max)] for _,x in rank.iterrows()],h=2.98,widths=[1.2,1.3,1.2,1.9,1.7,2.4],highlight_rows=[1],size=11.6),
 tx(f"선정용 종합 만족: {SEL['combined']}/9\n범위 끝의 이득·대역이 선정되면, 범위 밖 최적성은 추가 확인 대상임.\n선정 미사용·전압·편차 검증 결과로 설정을 다시 바꾸지 않음.",y=5.43,h=.88,size=12.5),foot('선정안은 전역 최적값 또는 실제 제품 적용 승인값이 아님.')], 'results/selected_control.json; results/candidates.csv; qa/execution.json','종합 만족을 우선하므로 THD만 최저인 후보가 반드시 선정되는 것은 아니다. 표의 다른 후보도 모두 보존하며 부록에27개 결과 전체를 제시한다.')
paired=pd.read_csv(R/'main_paired.csv')
add('results','4. Improve / 기준조건 개선 효과','I','동일한 47개 조건을 초기·선정 제어로 대응 비교함',f"평균 THD {F(s0['thd_mean'])}% → {F(s1['thd_mean'])}%; THD 만족 {s0['thd_pass_n']}/47 → {s1['thd_pass_n']}/47.",[
 ch(A.case_id,[('초기 THD',A.thd_pct,'gray'),('선정 THD',B.thd_pct,'teal')],w=6.07,discrete=True,cat_skip=6,max=math.ceil(max(A.thd_pct.max(),B.thd_pct.max())+1)),tb(resultrows('nominal'),x=6.91,y=2.48,w=3.3,h=2.94,widths=[1.4,1,1],size=11.3),foot(f"종합 만족 {s1['combined_pass_n']}/47: THD만 만족한 조건과 모든 항목을 만족한 조건을 분리함.")], 'results/baseline.csv; results/improved.csv; results/main_paired.csv',f"동일Case별 초기−선정 THD의 평균은 {paired.thd_decrease_pp.mean():.9g}%p다. 미사용 조건은 기준집합 안에 포함된다. 다른 버전의 초기값을 사용하여 개선량을 계산하지 않는다.")
add('lowresults','4. Improve / 저전류 영역 개선','I','전체 평균에 가려지는 취약 영역을 별도로 확인함',f"합성 지령의 RMS 환산값이 8 A 이하인 {len(lo)}개 조건: 평균 THD {F(lo.thd_pct.mean())}% → {F(lb.thd_pct.mean())}%.",[
 ch(lo.case_id,[('초기 THD',lo.thd_pct,'gray'),('선정 THD',lb.thd_pct,'teal')],w=6.14,typ='column',max=math.ceil(max(lo.thd_pct.max(),lb.thd_pct.max())+1),labels=True),
 tb([['지표','초기','선정'],['대상 조건',len(lo),len(lb)],['평균 THD',F(lo.thd_pct.mean())+'%',F(lb.thd_pct.mean())+'%'],['THD 만족',f'{int(lo.thd_pass.sum())}/{len(lo)}',f'{int(lb.thd_pass.sum())}/{len(lb)}']],x=6.96,y=2.61,w=3.24,h=2.41,size=11.4),foot('8개 저전류 조건은 기준 47개에 포함되며 별도로 합산하지 않음.')], 'results/current_strata.csv; results/baseline.csv; results/improved.csv','전류 수준별 분포가 다르므로 전체 평균과 저전류 평균을 동시에 보여준다. 초기5~8%의 숫자를 요구조건처럼 만들어 맞춘 것은 아니며 계산된 결과만 제시한다.')
us=S['selection_unused']; trids=SEL['selected_from_ids']
add('unseen','4. Improve / 선정 미사용 조건','I','선정에 사용하지 않은 38개 운전조건을 분리함','같은 수치모델에서 조건 선정에 사용하지 않은 영역도 개선되는지 확인함.',[
 tb([['집합','조건 수','초기 THD 만족','선정 THD 만족','선정 종합 만족'],['선정용',9,f'{int(A[A.case_id.isin(trids)].thd_pass.sum())}/9',f'{int(B[B.case_id.isin(trids)].thd_pass.sum())}/9',f'{int(B[B.case_id.isin(trids)].combined_pass.sum())}/9'],['선정 미사용',38,f"{us['initial']['thd_pass_n']}/38",f"{us['selected']['thd_pass_n']}/38",f"{us['selected']['combined_pass_n']}/38"],['기준 전체',47,f"{s0['thd_pass_n']}/47",f"{s1['thd_pass_n']}/47",f"{s1['combined_pass_n']}/47"]],h=2.43,widths=[2.1,1.1,2.2,2.2,2.1],size=11.2),
 tx('47=9+38. 동일 모델의 미사용 조건 검증은 실물 검증과 다름.\n모델 계열·부품 가정이 공통이므로 모델 오류에 대해서는 독립적이지 않음.',y=5.17,h=.97,size=13),foot('선정 이후 확인한 결과를 다시 선정 데이터에 섞지 않음.')], 'results/main_conditions.csv; qa/frozen_protocol.json; results/summary.json')
add('voltage','4. Improve / 전압 변화 확인','I','216 V·264 V에서 같은 Peak dq 전류를 지령함','전압 변화에 따라 전력도 달라지는 시험이며, 일정전력 제어 시험으로 해석하지 않음.',[
 tb(resultrows('voltage'),h=2.97,widths=[3.2,3.2,3.3]),tx('추가 범위는 240 V의 ±10%로 설정한 수치 민감도 시험임.\n216×48=10.368 kVA / 264×48=12.672 kVA.\n264 V·48 A는 공칭11.52 kVA를 초과하므로 해당 연속운전 허용을 입증한 결과가 아님.',y=5.4,h=1.04,size=12.3,color='red')], 'results/voltage_conditions.csv; results/voltage.csv; results/voltage_paired.csv','사양의공칭용량과전체전압범위의전류/전력capability는별개이다. 전압시험은고정전류지령모델의스트레스확인이다. 요구사항미확인상태에서해당조건을공식정격영역으로승인하지않는다.')
add('variation','4. Improve / 회로·검출계 편차','I','선정한 설정을 고정하고 24개 가정 변경 조건을 확인함','범위별 배치(LHS)를 사용했으며 제조공차 분포나 제품 신뢰도 표본으로 취급하지 않음.',[
 tb([['변경항목','설정한 범위'],['Vdc / 주파수','380~420 V / 59.5~60.5 Hz'],['Lf / Lg','0.9~1.1 mH / 0.05~0.25 mH'],['dead-time / LPF','100~300 ns / 8~12 kHz'],['offset / gain','±0.05 A / 0.995~1.005'],['추가 지연 / 계통 고조파','0 또는16 μs / 3차0~1.5%, 5차0~0.75%']],x=.55,w=5.78,h=3.4,widths=[2.1,3.6],size=11.5),tb(resultrows('variation'),x=6.69,y=2.47,w=3.51,h=2.94,widths=[1.45,1,1],size=11.1),foot('실행조건과 seed를 보존하고, 미달은 원인별로 별도 기록함.')], 'results/variation_conditions.csv; results/variation.csv; results/variation_paired.csv','LHS는분포구간을고르게배치하는설계도구다. 이번실제제조분포는없으므로24개조건의비율에제품불량확률의의미를부여하지않는다. 공진주파수는60Hz기준으로고정되어주파수변동을계수재튜닝으로제거하지않는다.')
ls=pd.read_csv(R/'structure.csv');l1=ls[ls.control_tag=='selected']
add('lf','4. Improve / LF 전환 가정 검증','I','저주파 레그의 전환 규칙을 바꾸어 모델 의존성을 확인함','기준은 브리지 전압 명령 부호형이며, 아래는 계통전압 부호형으로 변경한 별도 결과임.',[
 tb([['조건','id* [Apeak]','iq* [Apeak]','선정 THD [%]','전압 제한비','종합 판정']]+[[x.case_id,F(x.id_peak_a,2),F(x.iq_peak_a,2),F(x.thd_pct),F(100*x.saturation_fraction,2)+'%','만족' if x.combined_pass else '미달'] for _,x in l1.iterrows()],h=3.25,widths=[1,1.6,1.6,1.9,1.8,1.7],size=11.25),
 tx('실제 LF 동작이 확인되기 전에는, 기준 모델의 무효전력 성능을 제품 성능으로 확정할 수 없음.\n6개 구조 변경 조건을 기준47개 또는 편차24개의 성과 분모에 넣지 않음.',y=5.85,h=.82,size=12.4,color='red')], 'results/structure.csv; src/model.py lf_grid_polarity','실물 totem-pole의영교차·LF blanking·실제스위칭상태에따라성능과포화가달라질수있다. 본질적인모델불확도로기록하며THD가낮다는이유로이검증을생략하지않는다.')
fail=B[~B.combined_pass].copy(); vf=pd.read_csv(R/'variation.csv');vf=vf[(vf.control_tag=='selected')&(~vf.combined_pass)]
failall=pd.concat([fail.assign(dataset='기준'),vf.assign(dataset='편차')])
frows=[['조건 / 집합','RMS [A]','48 A 대비 [mA]','미달 항목']]
for _,x in failall.iterrows():
 flag=[lab for col,lab in [('rms_pass','RMS'),('tracking_pass','추종'),('saturation_pass','제한'),('peak_pass','피크'),('steady_pass','주기성'),('thd_pass','THD')] if not x[col]]
 frows.append([x.case_id+' / '+x.dataset,F(x.current_rms_a,6),F((x.current_rms_a-48)*1000,3),'·'.join(flag)])
add('failures','4. Improve / 잔여 미달과 부작용','I','실패조건을 보존하고 판정 항목별로 구분함',f"기준조건 {len(fail)}개, 회로·검출 편차조건 {len(vf)}개의 종합 미달을 별도 추적함.",[
 tb(frows,h=min(3.9,.45*len(frows)+.2),widths=[2.6,2.6,2.3,2.2],size=11.7),tx('수 mA 수준의 경계 초과는 수치 오차와 계측 허용차를 함께 검토해야 함.\n편차조건의 큰 초과와 동일 위험도로 단정하지 않으며, 48 A 기준을 임의 완화하지 않음.',y=6.04,h=.8,size=12.15)], 'results/main_failures.csv; results/variation.csv; results/refinement_comparison.csv','기본파 지령을48Arms로맞춰도리플·고조파·검출오차로전체RMS가한계를넘을수있다. 지령여유나전체RMS제한제어는별도개선대안이며이번DOE에포함하지않았다. 미달을삭제하여성공률을높이지않는다.')
tr=pd.read_csv(R/'transient_envelope.csv');trrows=[['시험','축별 Peak 지령 변경 [Apeak]','초기 정착 [ms]','선정 정착 [ms]']]
for cid,lab in [('T01','d:11.314→22.627, q:0'),('T02','d:22.627, q:0→22.627'),('T03','d:22.627, q:+22.627→−22.627'),('T04','d:56.569→67.882, q:0')]:
 trrows.append([cid,lab]+[F(tr[(tr.case_id==cid)&(tr.control==tag)].estimated_settling_ms.iloc[0],3) for tag in ['initial','selected']])
add('transient','4. Improve / d·q축 과도응답','I','정상상태 THD와 과도응답의 성과를 구분함','d축 단독 변화, q축 단독 변화, q축 반전 및 정격 접근을 각각 확인함.',[
 tb(trrows,h=2.76,widths=[1,4.7,2,2],size=11.1),tx('관측 정의: dq 피드백의 중심정렬 1계통주기 이동평균이 허용오차에 들어와 유지되는 시각.\n최소 관측 지연은 약8.33 ms이며, 표의 정착시간은 실제 제어 대역폭이나 일반적 2%정착시간이 아님.\n변경하지 않은 축의 일시 편차도 결과 CSV에 보존함.',y=5.36,h=1.06,size=12.15)], 'results/transient_envelope.csv; results/transient.csv; src/analyze.py','필터는오프라인후처리이며실제제어피드백에추가하지않는다. 축간과도변화는THD지표만으로평가할수없다. 과도피크는정상상태raw평가구간과동일하지않으므로이보고서가전시간구간의순간피크보호를검증했다고표현하지않는다.')
ref=S['numerical_refinement'];du=S['duration']
add('convergence','4. Improve / 수치 민감도 확인','I','시간간격·계산기간·고조파 계산법을 교차 확인함','대표조건의 관측 민감도를 기록하며, 이를 모든 운전조건의 오차 상한으로 확대하지 않음.',[
 tb([['검증','비교','최대 THD 차이','최대 RMS 차이'],['시간간격','2→1→0.5 μs',F(ref['max_abs_thd_pp'],6)+'%p',F(1000*ref['max_abs_rms_a'],4)+' mA'],['기간 연장','0.75→1.5 s',F(du['max_abs_thd_pp'],6)+'%p',F(1000*du['max_abs_rms_a'],4)+' mA'],['계산법 비교','직접 투영 / FFT',f"{S['fft_check']['max_absolute_difference_pp']:.2e}%p",'THD 비교'],['대표4회 재실행','동일조건 전류 배열','완전 일치','동일 환경']],h=2.8,widths=[2,2.5,2.6,2.6],size=11.6),tx(f"세분화 판정 일치: {ref['all_verdicts_equal']} / 기간 연장 판정 일치: {du['all_verdicts_equal']}\n동일값 반복은 재현성 검사이며, 통계적 표본 수가 증가한 것이 아님.",y=5.53,h=.76,size=12.6),foot('계산의 재현성과 실물 모델의 타당성은 별개임.')], 'results/refinement_comparison.csv; results/duration_comparison.csv; qa/fft_crosscheck.csv; qa/replay.json')
add('control','5. Control / 표준화와 재검증','C','사양·조건·선정값·원자료·보고서를 함께 관리함','사양 변경 시 문서 숫자만 수정하지 않고, 같은 검증 절차로 다시 계산함.',[
 tb([['관리 대상','산출물 / 규칙','재검증 조건'],['확정 사양·가정','specification.json + 입력 검사','정격·dq단위·클록·회로 변경'],['조건·판정','CSV·seed·사전 프로토콜','조건집합 또는 한계값 변경'],['선정 제어','selected_control.json + 선정 규칙','기본 PI·PLL·보상·지연 변경'],['원시 데이터','실행ID·파형·metadata·SHA-256','조건·코드·사양 해시 불일치'],['적용 전 확인','실물 회로·검출·LF·RMS 제한 확인','새 HW 근거 또는 미달 해소'],['버전 관리','V7 별도 저장; 이전판 보존','과거 성과를 새 결과에 혼합하지 않음']],h=3.78,widths=[2.1,4.0,3.6],size=11.55),foot('본 산출물은 설계 검토용이며 실제 SW의 적용·승인은 별도 절차임.')], 'qa/frozen_protocol.json; results/selected_control.json; docs/Model_and_Conventions.md')
add('benefits','5. Control / 성과와 적용 범위','C','수치 성과와 실제 제품 성과를 구분함','동일조건 THD 개선은 확인했으나, 실물 신뢰성·제조 수율·비용 절감액으로 확대하지 않음.',[
 tb([['구분','확보한 산출물','남은 확인'],['정량 성과','240 V 동일조건 THD 및 기준 만족 수','고객 규격과 판정지표의 동일성'],['제어 설계','고조파 후보·선정 규칙·부작용 기록','실제 SW 구현·CPU시간·전체 안정도'],['수치 검증','단위·원자료·시간축·재실행 검사','실물 파형과의 일치성'],['재무 성과','계산하지 않음','공수·단가·물동·적용률 등의 실증'],['후속 검증','실제 회로·검출계·LF 전환·RMS 한계','제품에 적용 가능한 최종 설계 여부']],h=3.55,widths=[1.9,3.9,3.9]),foot('근거가 없는 비용절감·양산 불량감소 또는 승인 상태를 만들지 않음.')], 'results/summary.json; specification.json','비용절감액은시험장비가없어서발생하지않은금액을임의추정한것이아니다. 실제과제에서승인된성과산정방식과기초자료가주어지면별도로계산할수있으나이번결론에는없다.')
add('conclusion','5. Control / 최종 기술 판단','C','목표 달성과 미달 항목을 함께 결론에 반영함',f"240 V 기준 THD 목표: {'달성' if s1['thd_pass_n']>=45 else '미달'} ({s1['thd_pass_n']}/47). 종합 판정과 모델 한계는 별도 관리함.",[
 tb([['평가 집합','THD 만족: 초기→선정','종합 만족: 초기→선정']]+[[lab,f"{S[k]['initial']['thd_pass_n']}/{S[k]['initial']['n']} → {S[k]['selected']['thd_pass_n']}/{S[k]['selected']['n']}",f"{S[k]['initial']['combined_pass_n']}/{S[k]['initial']['n']} → {S[k]['selected']['combined_pass_n']}/{S[k]['selected']['n']}"] for lab,k in [('기준240 V','nominal'),('전압 변화','voltage'),('회로·검출 편차','variation'),('LF 전환 변경','structure')]],h=2.65,widths=[2.8,3.45,3.45]),
 tx('모델 내 THD 개선 확인 ≠ 모든 제약을 만족하는 실제 제품 설계 확보\n실물 회로·전류 검출·LF 전환과의 일치성 및 고객 요구조건을 우선 확인해야 함.',y=5.49,h=.88,size=13,bold=True,color='red')], 'results/summary.json; results/*_paired.csv','목표는기준47개에대한THD만족률95%다. 인증상태와제품승인에는다른근거가필요하다. 해석데이터생성과검토완료를과제최종승인또는양산적용완료로표현하지않는다.')
MAIN=len(sl)
# Glossary: definitions and limitations are independent of any corporate process.
G=[('사양·신호',[
 ('11.52 kVA','240 Vrms×48 Arms의 공칭 피상전력','역률1일 때 유효전력11.52 kW와 대응'),('Peak dq','피크값을 보존하는 DC d·q 지령','RMS값과 √2 차이를 구분'),('id* / iq*','유효 / 무효 전류 지령 [Apeak]','q의 양의 방향은 모델부호 규약'),('θPLL','계통전압에 동기된 내부 각도','전류 위상 명령이 아님'),('P₁ / Q₁','기본파 유효 / 무효전력','이번 모델: P₁=V₁id/√2, Q₁=−V₁iq/√2'),('Iref,rms','√(id*²+iq*²)/√2','설명용 환산값. 실제 전체 RMS와 다름')]),
 ('측정·판정',[
 ('THD₂–₄₀','2~40차 RMS 합성을 기본파 RMS로 나눈 %','DC·40차 초과·스위칭 리플 제외'),('전체 RMS 전류','저장 파형의 제곱평균 제곱근','고조파·스위칭 리플 포함'),('보조 조건','추종·RMS·피크·제한·주기성 판정','48 A 외 한계는 자체 가정'),('종합 만족','THD와 모든 보조조건 동시 만족','THD 만족률과 구분'),('포화 시간비','전압명령이 제한된 평가 비율','추가 보상·적분 제한도 따로 확인'),('주기성 오차','연속주기1~7차 계수 차이의 RMS','전체 폐루프 안정도 증명이 아님')]),
 ('모델·시간축',[
 ('HF / LF 레그','고주파 / 저주파 브리지 스위치부','실제 LF 전환 로직 미확인'),('dead-time','상보 스위치의 turn-on 공백','기준200 ns는 모델 가정'),('제어 주기','16 μs; PWM과1:1 연산','샘플→적용 지연과 다름'),('샘플→적용 지연','기준8 μs, 추가1·2 PWM 지연 검증','ADC·shadow 설정은 실제 확인 필요'),('FIFO','지연된 명령을 순서대로 반영','명령출처와 적용값을 기록'),('수치 시간간격','기본2 μs, 대표1·0.5 μs 비교','제어주기를 변경하지 않음')]),
 ('제어·통계',[
 ('Kr / fc','공진 이득[Ω] / 대역 파라미터[Hz]','전체 전류제어 대역폭이 아님'),('DOE','인자·수준의 모든27조합 비교','27후보×9조건=243실행'),('주효과','다른 인자와 조건을 평균한 수준별 차이','이번에는 기술통계; p-value 아님'),('교호작용','인자 효과가 다른 인자 수준에 의존','그래프선 교차만으로 판단하지 않음'),('제곱합 기여도','후보 평균 반응변동의 요인별 분해','실물 고장원인 비율이 아님'),('대응 비교','같은 조건의 초기−선정 차이','집합 밖 제품 모집단 추론과 구분')]),
 ('시험·증거',[
 ('운전조건','id/iq·전압·회로가정의 조합1개','실물 시료1대를 의미하지 않음'),('해석 실행','조건1개와 제어설정1개의 계산','같은 조건의 전후 비교는2회'),('선정용 / 미사용','47개 중9개 / 나머지38개','38개를 다시 더하지 않음'),('시간 표본','파형 저장 시각의 전류값 하나','반복실험 또는 제품 표본 수 아님'),('모델 보정 / 검증','파라미터 맞춤 / 별도 근거와 대조','V7은 THD값 맞춤 보정을 안 함'),('재현성 / 실물 타당성','동일계산 반복 / 실제 제품 대응','자동검사 통과와 실물 검증은 다름')])]
for i,(name,items) in enumerate(G,1):
 add('glossary' if i==1 else f'g{i}',f'용어집 {i:02d} / {name}','C','용어의 정의와 이번 과제의 적용 범위를 함께 설명함','숫자·단위·평가 집합이 혼동되지 않도록 본문과 같은 정의를 사용함.',[tb([['용어','정의','주의사항']]+items,h=4.18,widths=[2.0,4.1,3.6],size=11.3)],'docs/Glossary.md; src/model.py; specification.json')
add('ss','부록 / 제곱합 분해','C','27개 후보 평균의 반응 변동을 분해함','3인자3수준의 모든 교호항을 포함하면 오차 자유도가 남지 않으므로 F·p를 계산하지 않음.',[
 tb([['항','자유도','제곱합','기여도 [%]']]+[[x.term.replace('kr_ohm','A').replace('band_hz','B').replace('max_harmonic','C'),int(x.df),F(x.SS,6),F(x.share_percent,3)] for _,x in SS.iterrows()]+[['합계',26,F(SS.SS.sum(),6),'100.000']],h=3.78,widths=[2.5,1.5,2.8,2.9],size=11.3),tx('A=Kr, B=fc, C=보상 차수. 이 비율은 선택한 설계격자의 변동이며 실제 제품 원인 비율이 아님.',y=6.28,size=12)], 'results/factorial_decomposition.csv; NIST §5.3.3.9','자유도 합은2+2+2+4+4+4+8=26이다. 각반응은9개운전조건의동일가중평균이다. 독립반복오차가없으며고차교호항을0으로가정하는별도정당화도하지않았으므로F통계량이나p-value를추가하지않는다. 실제모집단과오차구조가정의된다면다른추론설계를검토할수있다.')
add('formulas','부록 / 제어식과 해석식','C','디지털 구현에 사용한 부호·시간축을 정리함','기본파60 Hz와 Ts=16 μs를 구분하고, 피크값 dq의 변환 및 보상 계수를 명시함.',[
 tx('id = iα cosθ + iβ sinθ;  iq = −iα sinθ + iβ cosθ\niα = id cosθ − iq sinθ\nP₁ = V₁id/√2;  Q₁ = −V₁iq/√2',y=2.19,h=1.32,size=16,bold=True),
 tx('ωh=2π·60·h, ωc=2πfc, K=ωh/tan(ωhTs/2)\nD=K²+2ωcK+ωh²\nb₀=2KrωcK/D, a₁=2(ωh²−K²)/D, a₂=(K²−2ωcK+ωh²)/D\ny[n]=b₀(e[n]−e[n−2])−a₁y[n−1]−a₂y[n−2]',y=3.93,h=1.48,size=13.8),tx('±30 V 공진 출력 제한, ±150 V 적분상태 제한은 모델 가정이며 발생 여부를 별도 기록함.',y=6.16,h=.6,size=12)], 'src/model.py coefficients(), run_core(); Imperix TN110')
for st,en in [(0,14),(14,27)]:
 add(f'cand{st}','부록 / DOE 전체 후보 '+f'{st+1}~{en}','C','선정 외 후보를 포함한 모든 반응값을 보존함','Kr[Ω], fc[Hz], THD[%]. 후보1개는 서로 다른9개 운전조건을 요약한 결과임.',[
 tb([['후보','Kr','fc','차수','종합 만족','최대 THD','평균 THD']]+[[x.candidate,int(x.kr_ohm),int(x.band_hz),H(x.max_harmonic),f'{int(x.combined)}/9',F(x.thd_max),F(x.thd_mean)] for _,x in C.iloc[st:en].iterrows()],h=4.39,widths=[1.1,.9,.9,1.7,1.65,1.73,1.72],size=10.6)],'results/candidates.csv; results/doe.csv')
N=pd.read_csv(R/'main_conditions.csv')
for st,en in [(0,24),(24,47)]:
 rows=[['ID','id*','iq*','용도','ID','id*','iq*','용도']]
 for k in range(st,en,2):
  row=[]
  for j in [k,k+1]:
   if j<en:
    x=N.iloc[j];row.extend([x.case_id,F(x.id_peak_a,2),F(x.iq_peak_a,2),'선정용' if x.selection_used else '미사용'])
   else:row+=['','','','']
  rows.append(row)
 add(f'ids{st}',f'부록 / 기준 운전조건 ID {st+1}~{en}','C','240 V의 모든 dq 입력을 Peak A로 표시함','9개 선정용과38개 미사용 조건을 구분함. 반올림 전 입력값은 CSV에 보존함.',[tb(rows,h=4.23,widths=[1.1,1.15,1.15,1.3]*2,size=10.45)],'results/main_conditions.csv; qa/frozen_protocol.json')
za=np.load(ROOT/'waveforms/baseline_N015_initial.npz');zb=np.load(ROOT/'waveforms/improved_N015_selected.npz')
tt=np.linspace(.7,.7+1/60,301)
def draw(z):return np.interp(tt,float(z['t0_s'])+np.arange(len(z['current_a']))*float(z['dt_s']),z['current_a'])
ha=A[A.case_id=='N015'].iloc[0];hb=B[B.case_id=='N015'].iloc[0]
inc=[str(h) for h in [3,5,7,9,11] if hb[f'h{h}_rms_a']>ha[f'h{h}_rms_a']]
add('wave','부록 / 대표 파형과 차수별 변화','C','표시 파형과 계산에 사용한 원시 데이터를 구분함',f"N015: id*=5.657 Apeak, iq*=0, 240 V / THD {F(ha.thd_pct)}% → {F(hb.thd_pct)}%.",[
 ch([F(1000*(t-tt[0]),2) for t in tt],[('초기',draw(za),'gray'),('선정',draw(zb),'teal')],w=5.74,min=-7,max=7,cat_skip=60,h=3.35),
 tb([['차수','초기 [Arms]','선정 [Arms]']]+[[h,F(ha[f'h{h}_rms_a'],4),F(hb[f'h{h}_rms_a'],4)] for h in [3,5,7,9,11]],x=6.57,y=2.47,w=3.63,h=2.76,widths=[1,1.6,1.6],size=11.2),
 tx('가로축: 시간[ms] / 세로축: 전류[A]. 표시만301개로 줄이고 지표는 전체 원자료로 계산함.',y=5.93,size=11.7),tx(('증가한 차수: '+', '.join(inc)+'차. ' if inc else '')+'THD 감소가 모든 차수의 개선을 뜻하지는 않음.',y=6.43,size=11.7,color='red')], 'waveforms/*N015*.npz; results/baseline.csv; results/improved.csv')
add('reproduce','부록 / 데이터 추적 및 재현','C','사양과 실행 결과의 연결을 파일 단위로 유지함','공개본은 수치모델·코드·데이터·방법 근거로 구성하며 사내 절차자료를 포함하지 않음.',[
 tb([['파일','확인 내용'],['specification.json / source_lineage.json','확정 사양·가정·잠정 기준 / 이전 구현과 변경 관계'],['src/model.py / study.py','Peak dq·1:1 클록·스위칭 계산·후보 선정'],['results/*.csv / selected_control.json','모든 반응·미달·선정 결과'],['waveforms/*.npz','전류·제어·PWM 로그·metadata·해시'],['qa/*.json / *.csv','사양·원자료 재계산·FFT·시간축·재현 검증'],['sources/references.md','TI ePWM, Imperix 공진제어, NIST 실험계획']],h=3.57,widths=[3.8,5.9]),tx('새 출력폴더에서 test_model.py → study.py → analyze.py → audit_v7.py → make_report.py',y=6.28,size=11.4)], 'README.md; sources/references.md; qa/frozen_protocol.json','기존파형이있으면study.py는덮어쓰지않고중단한다. 보고서만재생성할경우make_report.py를사용한다. 공개한파일목록과해시를기록하며이전데이터가성과입력에들어오지않았는지검사한다.')

def finalize(slides,main_count,author='SSBB numerical study',outname='SSBB_V7_Technical_Public'):
 pages={s['sid']:i+1 for i,s in enumerate(slides)}
 ds=dict(title='11.52 kVA 북미 V2G / 240 Vac 48 Arms / V7',author=author,font='Malgun Gothic',width=10.833333,main_count=main_count,dataset=f"SSBB-V7-20260928 / {S['campaign_runs']} freshly computed runs / Peak dq / 16 us",test_map_page=pages['tests'],glossary_page=pages['glossary'],results_page=pages['results'],stage_pages={p:next(i+1 for i,s in enumerate(slides) if s.get('stage')==p) for p in 'DMAIC'},slides=slides)
 O.mkdir(exist_ok=True);(O/(outname+'.json')).write_text(json.dumps(ds,ensure_ascii=False,indent=2)+'\n')
 build(ds,O/(outname+'.pptx'))
 (O/(outname+'_text.md')).write_text('\n\n'.join(f"## {i+1}. {s['title']}\n\n{s.get('subtitle','')}\n\n{s.get('message','')}\n\n"+'\n'.join(e.get('text','') if e['kind']!='table' else '\n'.join(' | '.join(row) for row in e['rows']) for e in s.get('elements',[]))+f"\n\n근거: {s.get('source','')}\n\n{s.get('notes','')}" for i,s in enumerate(slides)))
 return ds

if __name__=='__main__':
 ds=finalize(sl,MAIN)
 (ROOT/'docs/Glossary.md').write_text('# V7 기술 용어집\n\n'+'\n\n'.join('## '+head+'\n\n'+'\n\n'.join('**'+term+'**: '+df+' / '+note for term,df,note in its) for head,its in G))
 print('PUBLIC',len(sl),'MAIN',MAIN)
