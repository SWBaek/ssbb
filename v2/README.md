# SSBB v2 | 저부하 AC단 THD 개선 수치 연구

**v1은 제품 초기 성능의 근거로 사용하지 않습니다. 현재 수행본은v2입니다.**
본 저장물은 공개 제조사 레퍼런스로 THD 수준을 검토한 수치 연구이며, 실제 OBCM/PSIM 실행/제품 검증이나 사내BB승인을 뜻하지 않습니다.

최종발표: `report/index.html` (독립 실행 HTML, 방향키/전체보기/인쇄).
실행원시값: `data/*.npz`. 수치요약·시험조건·선정기록: `results/`.
근거: `evidence/public_references.json`, 최종 논리 검토: `docs/02_logic_review.md`.
기존11개 보고서 비교: `docs/03_reference_comparison.md`.

## 재실행
Python3.13에서 이 폴더를 작업경로로 사용합니다.
```sh
python -m pip install -r requirements.txt
python -m src.study
python -m src.checks
```
663개의 성능해석을 실행하고, 전 측정구간의 원시파형에서 결과를 재계산합니다. 결정론적 실행이므로 독립 실물표본663개라는 뜻이 아닙니다.

## 범위
주시험은S525/700/875VA, 위상-60/-30/0/30/60도, Vac207/230/253V의45점입니다. 튜닝9점은주45점과다릅니다. 별도stress72점과중고부하36점을 분리해보관합니다.
THD_2:40의5%는 연구용 잠정한계입니다. data를임의로scale하거나개선후합격수를사전에정하지않습니다. 후보내최선값이전체영역최적점은아닙니다.

수치모델은 generic averaged voltage-bridge+seriesL/R이며 실제totem-pole commutation과DC-link/CLLC/EMIfilter는 포함하지 않습니다. 저부하THD개선은보여주지만Q고유왜곡의원인입증은아닙니다. 중고부하S035의전압포화문제는개선전후모두남습니다.

## 추적
- `docs/00_protocol.md`: 가정,탐색이력,분모,판정,선정규칙
- `results/protocol_freeze.json`: 주요입력·소스해시
- `results/selected_control.json`: 튜닝군에근거한최종제어값
- `results/all_runs.csv`: 전체결과와원시파형위치
- `results/manifest.json`: 파일별크기/SHA-256
- `results/raw_audit.json`, `results/test_report.json`: 실제검사결과

기존 사내PPTX원문이나이미지는포함하지않습니다. 본출력은AI보조연구이므로기술책임자의검토가필요합니다.
