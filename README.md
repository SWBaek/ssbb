# SSBB: V2G THD 참조 수치모델 연구

**직접 계산한 numerical simulation 자료다. 실제 OBCM / PSIM / 하드웨어 시험 결과나 규격 인증 자료가 아니다.**

상위 주제: OBCM V2G 저부하·무효전력 운전 시 계통 전류 THD 규격 만족률 향상.
이번 산출물의 정확한 범위: 일반화된 sampled-data AC단 모델에서 등가 dead-time 보상과 전류제어 이득의 조건부 개선 연구.

## 먼저 볼 자료

- [`report/index.html`](report/index.html): 외부 CDN 없는 독립 실행형 한국어 슬라이드. 파일을 내려받아 브라우저에서 연다. 방향키/PgUp/PgDn, 목차 선택, 전체 보기, 인쇄 지원.
- [`report/summary.md`](report/summary.md): 실행 결과 요약.
- [`docs/04_logic_review.md`](docs/04_logic_review.md): 해소한 논리 오류와 미해결 경계.
- [`report/reference_comparison.md`](report/reference_comparison.md): 기존 11개 BB 자료와 비교.
- [`results/summary.json`](results/summary.json), [`results/all_runs.csv`](results/all_runs.csv): 591개 성능 실행 결과.
- [`results/holdout_failures.csv`](results/holdout_failures.csv): 미사용 조건 검증의 모든 combined 실패.
- [`data/schema.json`](data/schema.json): lossless NPZ 파형과 채널 정의.

## 결과를 읽는 기준

THD <= 5%는 이 참조 연구의 **잠정 설계 기준**이며 고객 규격이나 IEEE 1547 TRD 기준으로 해석하지 않는다. 주 행렬 72점은 학습 9점을 포함하므로 독립 검증 결과와 구분한다. 추가 72 stress 조건은 가정 범위의 coverage이며 제조 yield가 아니다. 실패 결과와 과도응답 악화가 포함되어 있다.

시뮬레이션에서 제어 성능이 개선되어도 실제 totem-pole Q 운전 문제를 해결했다는 결론은 아직 낼 수 없다. 원본 HW/제어 SW/실측 데이터가 없어 참조 파라미터와 baseline을 사용했다. 제품 검증·BB 승인·재무성과는 미완료/미확인으로 표시한다.

## 로컬 재현

Python 3.13 환경에서 실행한다. OS별 세부 부동소수점 차이는 발생할 수 있다.

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m src.study
python -m unittest discover -s tests -v
```

`python -m src.study`는 Define → 수치 검증 → baseline → DOE/설정 동결 → 주 행렬 비교 → 미사용 조건 → 기전/위상/과도 검토 → 보고서/해시 순으로 실행한다. 수치 검증 gate 실패 시 성능 분석으로 넘어가지 않는다. 기존 결과가 있으므로 다른 revision 실행 전 별도 브랜치/사본을 사용한다.

GitHub Actions의 **Reproduce numerical BB study**도 같은 명령으로 재실행하여 `data/`, `results/`, `report/`를 동일 비공개 저장소에 기록한다. 외부 공개 사이트에는 게시하지 않는다.

## 추적성

`docs/00_scope_and_protocol.md`와 `docs/01_experiment_plan.md`는 성능 실험 전에 고정한 계획이다. `results/stage_log.json`은 순서, `selected_control.json`은 동결 설정 및 모델/설정 hash, `environment.json`은 버전/소스 hash, `manifest.json`은 최종 데이터/보고서 SHA-256을 기록한다. 동일 결정론적 입력의 반복을 별도 독립 표본으로 간주하지 않는다.

기존 사내 발표자료는 이 저장소에 복제하지 않았다. 비교에는 익명 ID, 주제 유형, 슬라이드 번호와 제한된 방법론 관찰만 포함한다. 원본은 사용자 제공 프로젝트 소스에서 확인해야 한다.

AI 작성/계산 보조: GPT-6 Astra Pro. 작성 에이전트의 논리 검토는 독립 MBB 심사를 대신하지 않는다.
