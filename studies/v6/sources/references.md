# V6 근거 및 적용 범위

기준일: 2026-09-28. 외부 문헌은 제어·실험계획 방법의 참고자료이며, 본 OBCM의 실측 성능 또는 인증 근거가 아님.

## 최우선 입력
- 사용자가 최종 확인한 값: 230 Vac, 48 Arms, Peak dq, PWM 62.5 kHz, 제어 연산 62.5 kHz / 16 μs.
- 사용자가 지정한 제품급 명칭: 11.52 kVA급. 230×48=11.04 kVA와 산술적으로 일치하지 않으므로 명칭과 계산값을 분리함. 240 V 또는 50.087 A로 바꾸지 않음.
- 실제 회로 정수, DC-link 제어, Q 부호, ADC/PWM 이벤트 설정은 미제공. specification.json의 추가 모델 가정으로 분리함.

## 외부 방법 참고
1. TI, C2000 F2838x Driverlib ePWM module: https://software-dl.ti.com/C2000/docs/C2000_driverlib_api_guide/f2838x/build/html/modules/epwm.html
   ADC 트리거와 PWM shadow load는 개별 설정임. 제어주기 16 μs가 입력됐다고 지연 8 μs까지 확인된 것은 아님.
2. Imperix, Single-phase PV inverter with Fictive-Axis Emulation: https://imperix.com/doc/example/single-phase-pv-inverter-with-fictive-axis-emulation
   단상 회전좌표계 제어 및 직교축 구성의 방법 참고. V6는 해당 제품을 복제하거나 그 실측 검증을 승계하지 않음.
3. Imperix, SOGI PLL: https://imperix.com/doc/implementation/sogi-pll
   계통 위상 추정 방법 참고. V6의 각도는 PLL 내부 신호이며 외부 전력 지령이 아님.
4. Imperix, Proportional resonant controller: https://imperix.com/doc/implementation/proportional-resonant-controller
   유한 대역폭 준공진기와 디지털 이산화 방법 참고. V6는 180/300/420 Hz를 사용함.
5. NIST/SEMATECH, Three-level full factorial designs §5.3.3.9: https://www.itl.nist.gov/div898/handbook/pri/section3/pri339.htm
   3인자 3수준의 모든 27조합 구성에 사용함. 결정론적 조건을 실물 반복표본으로 해석하지 않음.
6. NIST/SEMATECH, Analysis of paired observations §7.3.1.1: https://www.itl.nist.gov/div898/handbook/prc/section3/prc311.htm
   동일 Case의 전후 차이를 계산하는 대응 구조 참고. 본 수행에서는 t-검정의 모집단 추론을 수행하지 않음.
7. NESCOE, Ancillary Services Primer (2017): https://nescoe.com/resource-center/ancillary-services-primer-sep2017/
   미국의 계통 주파수 60 Hz 배경 참고. V6는 북미용 해석을 위해 60 Hz를 추가 가정했으며 사용자가 확정한 세 전기 사양과 구분함.

## 기존 첨부 슬라이드의 활용
- LDC Snubber: 변경 가능한 인자와 제외 사유, 부작용의 분리(p.10,18~19).
- 22 kW CLLC: 측정/해석 경로, 요인설계 → 영향도 → 선정의 연결(p.5,16~19).
- DC CAP: 목적 성능이 우수해도 다른 요구사항에 미달하면 적용안을 기각(p.14).
- Heatsink 및 Tub Outer: 해석 기반 설계 제안과 실물 검증의 구분.
- GNSS·TIG·HONDA·NFC·HMI·디스플레이: Big Y 전개, 시험조건 정의, 개선안 및 관리기준 표현.
- 기존 11개 보고서의 문장 전개와 흰 배경/회색 제목띠/표/단계 표시를 참고함. 원본 사내 슬라이드·이미지·폰트 파일은 배포하거나 GitHub에 올리지 않음.
- V1~V5의 성능 숫자, 보정계수, 파형, 후보 선정 결과는 V6 데이터 입력으로 사용하지 않음.
