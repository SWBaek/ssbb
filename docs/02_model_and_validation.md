# 02. 모델 및 검증의 정확한 의미

## 회로 모델

계통으로 나가는 전류를 양으로 정의한다. 상태는 선로 전류 i이며, 플랜트는 `L di/dt = vinv - R i - vg`, `L=Lf+Lg`, `R=Rf+Rg`이다. 입력은 전압원형 AC단의 평균 출력이다. 실제 totem-pole 두 leg의 스위칭 상태를 푸는 모델이 아니다.

`vg = sqrt(2) Vrms [sin(wt)+v3 sin(3wt)+v5 sin(5wt)]`, `w=2π·50`. 여기서 Vrms는 **기본파** RMS이고 고조파가 존재할 때 전체 RMS와 다르다.

`vinv = clip(u_delayed - e_dt, -Vdc, Vdc)`.

`e_dt = Vdc·fs·td·tanh(i/I0)`는 본 연구에서 정의한 등가 데드타임 비선형이다. 대체 모델에서는 tanh 대신 `clip(i/I0,-1,1)`을 사용한다. 계수와 완화 폭 I0는 측정으로 식별되지 않았다. dead-time, DCM, Coss, diode 역회복, LF leg 전환을 동일 현상으로 취급하지 않는다. 본 식은 이 중 실제 소자 동작을 재현하지 않는다.

## 제어 모델

32 kHz sampled-data 전류 루프와 20 Hz SOGI-PLL을 사용한다. SOGI는 연속 상태방정식을 행렬 지수로 정확 ZOH 이산화한다. PLL은 50 Hz에서 동기된 초기조건으로 시작한다. PLL 획득/주파수 변동/ROCOF 검증은 아니다.

`id*=sqrt(2)P/Vrms`, `iq*=-sqrt(2)Q/Vrms`, `i*=id* sin(theta)+iq* cos(theta)`. 양의 Q는 계통 기본파 전압에 비해 전류가 지연하는 convention이다. 실제 차량 통신 신호 부호와의 매핑은 하지 않았다.

전류 alpha는 검출값, beta는 SOGI 출력이다. dq PI의 proportional 부분을 역변환하면 `Kp(i*-i_meas)`가 되며 integral 두 축은 별도로 계산한다. `Kp=2π·bw·Lf_nom`, `Ki=2π·bw·Rf_nom`. bw는 **이득 산정을 위한 명목 대역폭 인자**다. 실제 폐루프 교차주파수나 위상여유를 측정한 값은 아니다. 플랜트의 grid L/R와 delay 때문에 지정 bw와 실제 응답이 일치한다고 가정하지 않는다.

전압/전류 지령 feedforward, 한 제어주기 계산 지연, ±0.95 Vdc 전압 제한, 조건부 적분을 포함한다. 보상 전압은 `alpha·Vdc·fs·td_est·tanh(i*/Ic)`이다. true current나 true dead-time를 직접 사용하지 않으며 추정 td_est는 1 us로 고정한다. 하지만 명목 true td와 값이 같으므로 명목 결과는 여전히 이상적으로 잘 맞은 모델 조건이다. 이를 보완하려고 추정값을 고정한 채 holdout의 true td와 모델 형상을 변경한다.

## 수치 구현 검증

플랜트는 4차 Runge–Kutta, 제어주기당 16분할로 적분한다. 8분할에서 독립 DOP853 대비 1 mA 허용오차를 초과한 stress 조건을 보존하고 16분할로 해결했다. 최종 일부 조건은 32분할로 재확인한다.

알려진 고조파 신호, RL 폐형식 해, 독립 DOP853 단일구간 해, FFT와 직접 직교투영, 정상상태 지속시간, 시간 간격 수렴, ZOH 구간별 전력 수지를 검증한다. 이들은 numerical verification이다. 실제 제품 파형·측정값과의 empirical validation은 아니다. 상용 시뮬레이터를 사용해도 이 구분은 사라지지 않는다. 참고: NASA-STD-7009B(2024), https://standards.nasa.gov/standard/nasa/nasa-std-7009 . 이는 비교 관점이지 사내 의무 규격이 아니다.

## 계측 및 데이터 해상도

THD는 32 ksample/s로 기록된 마지막 10개 기본파 주기의 2~40차 정수 고조파를 기본파로 정규화한다. 50 Hz와 32 kHz가 정수비여서 coherent FFT를 사용한다. DC, interharmonics, switching ripple을 포함한 모든 왜곡 지표 또는 IEEE 규격 측정기를 구현한 것이 아니다. zero-current point는 사전 제외한다. guardrail은 기본파 Q와 전체 유효전력 P, peak와 saturation을 따로 본다.

일반 운전점은 마지막 10주기의 모든 제어 샘플을 lossless float64로 저장한다. 시작 과도 구간은 필요 시 입력/코드로 재생성 가능하다. 과도응답 8런은 전체 40주기 파형을 저장한다. 플랜트 substep 중간값 자체는 저장하지 않으며 기록 샘플 기준 THD라고 한정한다.

## 주장 가능한 결론과 경계

- 가능: 지정한 참조 모델과 인자 범위에서 조건부 제어 개선 효과, 잔여 실패 및 상대 성능 변화.
- 미입증: 실제 OBC THD 현수준, Q 운전의 실제 원인, IEEE 1547 적합성, PSIM correlation, 양산 yield, 전체 시스템 안정도 여유, 재무성과.
- 누락 계통: CLLC/DC-link 외부루프/2ω bus ripple, 실제 EMI 필터, LF/HF leg 상태천이, 소자 기생성분, 온도·효율, 보호 및 anti-islanding, MCU의 실제 연산 시간.
- 실제 무효전력 원인 검증을 위해서는 전압·전류 영교차의 상대 위상과 actual gate sequence를 포함한 모델 및 실제 제어 SW/과거 파형이 추가로 필요하다.
