# Six Sigma BB | V2G AC-stage THD numerical study

## 현재 수행본: v2

**v1의 평균 THD 18.95%는 실제 OBCM의 초기 성능을 나타내는 근거로 사용하지 않습니다.** 과도한 등가 왜곡 가정과 제품 상관성 부족이 확인되어, 공개 제조사 자료와 부하 조건을 구분하여 v2를 다시 수행합니다. v1 파일은 변경 이력과 비교를 위해 보존합니다.

- [v2 최종 HTML 발표자료](v2/report/index.html)
- [v2 실행 방법과 범위](v2/README.md)
- [공개 레퍼런스 근거](v2/evidence/public_references.json)
- [최종 수치 요약](v2/results/report_summary.md)
- [전체 원시 파형](v2/data/)
- [전체 실행 결과](v2/results/all_runs.csv)
- [논리 검토](v2/docs/02_logic_review.md)
- [기존 11개 BB 보고서와 비교](v2/docs/03_reference_comparison.md)
- [원격 재현 기록](https://github.com/SWBaek/ssbb/actions/workflows/reproduce_v2.yml)

첫 게시에서는 검증된 소스를 복원한 뒤 GitHub Actions가 해석, 원시 파형, 결과표, 보고서와 시험 기록을 생성하여 이 저장소에 커밋합니다. 작업의 완료 여부는 Actions 상태와 실제 결과 파일을 기준으로 확인합니다.

## 주장 범위

본 과제는 generic averaged AC-stage 수치 연구입니다. 실제 OBCM 실측값, PSIM 실행 결과, 고객 규격 적합성, 사내 BB 승인으로 표시하지 않습니다. THD 5%는 연구용 잠정 기준입니다. 공개 reference의 특정 운전점 성능을 '업계 평균'으로 일반화하지 않으며, 사용자가 설명한 5~8%는 실제 측정 로그가 아닌 현수준 참고 정보입니다.

Q를 포함한 운전점에서 저전류 THD 개선은 분석하지만, 실제 totem-pole의 Q 고유 영교차/정류 메커니즘은 이 모델로 입증하지 않습니다. 중·고부하 확인군의 전압 포화 실패도 결과에 유지합니다. 기존 사내 PPTX 원본·이미지는 업로드하지 않았습니다.
