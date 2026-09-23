# 00. 과제 범위 및 사전 분석 계획

기준일: 2026-09-23. 상태: numerical-study protocol; 고객/사내 승인 기준 아님.

## 과제와 완료 범위

상위 과제: **OBCM V2G 저부하·무효전력 운전 시 계통 전류 THD 규격 만족률 향상**.
이번 실행 범위는 **일반화된 단상 계통연계 AC단 수치모델에서의 제어 개선 연구**이다. 실제 제품 회로도, 양산 SW, 실측 파형 또는 PSIM 실행 결과는 제공되지 않았다. 따라서 이 연구의 baseline은 실제 OBCM 현수준이 아니다.

수치 실험, 원인 분석, 설계 인자 선정, 개선 확인, 회귀시험 체계, HTML 보고서 및 기존 사례 대비 검토를 수행한다. 하드웨어 검증, PSIM correlation, 제품 인증, 사내 BB 완료 승인은 별도 미완료 항목으로 유지한다. AI가 수치를 임의 작성하거나 합격 결과를 미리 지정하지 않는다.

## 순차 단계

1. Define: 범위/가정/기준/대상 시험점 고정.
2. Measure-V: 모델 방정식, 구현, 시간간격 수렴, THD 계산, 물리 법칙 검증.
3. Measure-B: 동일 조건의 baseline 전체 측정.
4. Analyze: 기전별 ablation 및 결정론적 요인 실험.
5. Improve: 사전 지정 학습 시험점에서 설정 선정 후 동결.
6. Verify: 전체 matrix와 미사용 조건/모델 불확실성에서 개선 전후 비교.
7. Control/Review: 재현 절차, 원시 데이터, 해시, 제한사항, 기존 11개 보고서 대비 논리 검토 및 HTML 산출물.

후속 단계가 실패하면 실패를 보존한다. holdout 결과를 본 뒤 같은 holdout으로 재튜닝하지 않는다.

## 잠정 설계 판정 규칙

- Project Y_sim = 100 × THD 기준 만족 시험점 수 / 고정 대상 시험점 수.
- THD_I: 기본파 RMS로 정규화한 2~40차 정수 고조파 RSS, 정상상태 10개 기본파 주기 사용.
- 잠정 기준: THD_I <= 5.0%. 이 값은 본 참조 연구의 가정이며 고객 규격, IEEE 1547 TRD 기준 또는 확정 제품 요구사항으로 주장하지 않는다.
- 잠정 목표: 주 시험행렬 Y_sim >= 95%. 달성 여부는 실행 결과로 판정한다.
- 별도 guardrails: P/Q 오차 각각 <= max(20 W 또는 var, 지령 피상전력의 2%); 정상상태 peak current < 50 A; 정상상태 modulation saturation 비율 < 0.1%.
- THD 통과율과 guardrail을 모두 포함한 통과율을 별도로 보고한다. 실패 사례를 분모에서 제외하지 않는다.
- P=Q=0인 무전류 지령은 THD 지표가 부적절하여 사전에 제외하며, 가동 실패를 사후 제외하지 않는다.
- THD 5%와 TRD 5%는 동의어가 아니다. IEC/IEEE 측정 규약 전체, interharmonics, DC injection, EMC, ride-through, anti-islanding 등은 이 판정에 포함되지 않는다.

## 모델 경계와 가정

- 참조 모델: 단상 전압원형 AC단 + 직렬 L/R 필터 + 계통, sampled-data dq 전류제어 및 SOGI-PLL, 전압 feedforward, 전압 제한, 계산 지연.
- 명목 조건(제품 사양 아님): 230 Vrms / 50 Hz, 400 V DC bus, 32 kHz control/PWM 기준, L_filter=1.5 mH, R_filter=0.15 ohm, L_grid=0.2 mH, R_grid=0.10 ohm.
- 저차 고조파 원인 후보는 등가 dead-time 전압오차, 계통 고조파, 지연, 전류 검출 오차로 한정한다. 등가 dead-time 모델은 실제 스위치/diode/Coss 및 totem-pole 영교차 전환을 검증한 모델이 아니다.
- DC bus는 외부에서 유지되는 것으로 가정한다. CLLC, DC-link 외부루프, 2ω bus ripple, 열/손실/EMI, 자성체 포화, 실제 게이트 시퀀스, MCU 실행시간은 완료 주장 범위에서 제외한다.
- 실제품 설계값을 제공받은 경우 이 참조모델을 별도 revision으로 갱신하고 전 실험을 다시 수행해야 한다.

## 데이터 및 통계 원칙

같은 결정론적 조건을 반복 실행한 값을 독립 표본으로 세지 않는다. 임의 noise를 추가하여 Gage R&R, p-value 또는 Cpk를 만들지 않는다. 효과크기, 교호작용, 독립 조건에서의 확인과 수치 오차를 중심으로 보고한다. 불확실성 범위는 가정의 탐색 범위이며 제조 산포 분포나 양산 합격확률을 뜻하지 않는다.

코드, 입력, 실행 환경, 원시 파형, 집계 결과, 검증 결과와 파일 해시를 연결한다. 보고서 숫자는 결과 파일에서 생성한다. 원가/공수 절감 실측 근거가 없으므로 재무성과를 만들어내지 않는다.

## 자료 반출 경계

업로드된 기존 사내 PPTX 원본, 이미지, 개인/고객별 물량 및 비용 정보는 이 저장소에 복제하지 않는다. 비교 검토는 익명 사례 ID와 관련 슬라이드 번호, 방법론상 관찰 및 차이점만 남긴다.

## 외부 참고

- NREL/TP-5D00-78751 (2021), Background Information on the Power Quality Requirements in IEEE Std 1547-2018: https://www.osti.gov/biblio/1827312
- TI TIDM-02008: https://www.ti.com/tool/TIDM-02008 (일반적인 양방향 totem-pole 및 영교차 문제의 참고이며 본 모델 검증 자료 아님)
- NASA-STD-7009B: https://standards.nasa.gov/node/263 (verification/validation/credibility 구분 참고; 당사 BB 의무 규정 아님)

외부 문서는 모델 타당성의 참고 자료이지, 본 시뮬레이션이 실제 제품을 재현한다는 실증 근거가 아니다.
