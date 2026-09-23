# 수치모델과 적용 범위

## 구현식
기본 plant: (Lf+Lg) di/dt = v_bridge - v_grid - (Rf+Rg)i.
평균 bridge command에는 제어 1 sample 지연과 가정한 commutation error가 포함된다.
E=Vdc*fs*t_eff, e_c(i)=E*tanh(i/I0). 별도 검증 절반에는 tanh 대신 선형 포화 함수를 사용한다.
Nominal E=400*32000*200e-9=2.56 V. 이는 총 등가 오차 정의이며 실제 totem-pole의 게이트별 dead time과 일대일 대응시킨 식이 아니다.

제어는 SOGI quadrature 신호를 사용한 dq 기본파 적분과 실전류 오차 비례 제어, grid/feed-forward, 명시한 limiter로 구성한다. SOGI-PLL 20 Hz 설계상수 사용. 스위칭은 직접 계산하지 않고 PWM 평균 전압으로 대체한다. 전류제어 Kp=2*pi*f_design*L_nom, Ki=2*pi*f_design*R_nom. f_design을 실측 폐루프 bandwidth라고 부르지 않는다.

추가하는 3/5차 전류오차 feedback:
C_h(s)=K_h*2*wc*s / (s^2+2*wc*s+(h*w0)^2), wc=2*pi*5 rad/s.
각 resonator는 실제 current error만 입력받는다. 모델의 dead time, I0, error shape를 알고 정확히 역보상하는 함수가 아니다. 토폴로지를 바꾸거나 왜곡을 직접 빼서 파형을 생성하지 않는다.

## 수치 처리
32 kSa/s discrete controller, 50 Hz grid, RK4 plant integration 4 substeps/sample, SOGI/공진 state exact ZOH discretization. 기본 40주기 중 마지막 10주기 저장·분석. refinement는16substeps, duration은80주기. 2~40차 성분만 사용하며 fundamental I1 분모, DC 제외. 모든 성능실험의 측정 구간 6400x10 float64 원시값과 시험입력·제어입력이 저장된다. 과도시험은25600x10 전체파형이다.

## 무엇을 검증했는가
알려진 고조파 신호에서 THD 계산, DC 제외, 이상적 한계조건, integration convergence, FFT/direct projection 비교, 최종 조건에서 시간간격/정착시간 증가 효과를 확인한다. src.audit가 663개 성능파형 전체에서 숫자 및 합부를 재계산한다.

## 무엇을 검증하지 않았는가
위 검증은 구현 및 수치오차 검증이다. 실제 HW의 물리적 검증이 아니다. LCL/EMI필터, 토템폴 LF-leg polarity-dependent commutation, DCM, Coss/diode recovery, 스위칭 리플, 동적 DC-link/CLLC, 실제 ADC/PWM bit-level 구현, 보호/anti-islanding, thermal/EMC/인증 적합성, 실제 MCU 계산시간은 제외한다.
전류 위상 변화 자체는 모델에 있으나, 실제 Q 운전이 왜곡을 추가로 일으키는 토폴로지 고유 메커니즘이 없다. 따라서 Q-containing test matrix의 결과와 Q-specific 원인 입증을 구분한다.
