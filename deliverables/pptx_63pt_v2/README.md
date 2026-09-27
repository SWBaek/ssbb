# Six Sigma BB 제출용 PPTX · 63점 V2 수행본

**수치연구 결과를 발표 가능한 편집형 PowerPoint로 구성한 자료입니다.**
실제 제품 검증, 고객 규격 인증 또는 사내 BB 승인을 의미하지 않습니다.

- 최종 파일: `SSBB_V2_Submission_BaekSeungwoo.pptx`
- 열람용: `SSBB_V2_Submission_BaekSeungwoo.pdf`
- 구성: 본문 28장 + 부록 10장, 편집형 차트 13개 / 표 27개 / 발표자 노트 38장
- 기준: 마지막 대화 첨부 `SSBB_V2_THD_full_package.zip`의 `studies/v2` (주63점 / 별도60점)
- 연구 ID: `SSBB-NUM-20260923-v2`
- 연구일 2026-09-23 / 발표자료 작성일 2026-09-27

## 중요한 버전 구분

저장소 기존 `/v2/`의 45점/72점 수행본과 이 폴더의 63점/60점 수행본은 **서로 다른 데이터**입니다.
기존 자료를 덮어쓰거나 혼합하지 않았습니다. 본 자료의 수치는 `deck.json`에 동결되어 있으며,
각 슬라이드의 원자료 파일 경로와 한계는 하단 및 발표자 노트에 기록했습니다.
모든 차트는 표시 반올림/파형 표시 간격 축소 외에 원래 수치 결과를 변경하지 않았습니다.
전체 원시파형은 마지막 대화 첨부 ZIP에 있습니다. 선택 원자료 해시는 `source_manifest.json`에 있습니다.

## 재생성

```sh
python -m pip install python-pptx==1.0.2
python build_pptx.py --spec deck.json --out SSBB_V2_Submission_BaekSeungwoo.pptx
python validate_pptx.py --pptx SSBB_V2_Submission_BaekSeungwoo.pptx --spec deck.json --out presentation_qa.json
```

`source_bundle.json.xz`는 원본 UTF-8 소스를 압축한 전송용 스냅샷이며 공개 가능한 평문 소스도 함께 저장합니다.
PPTX는 Malgun Gothic을 지정합니다. 폰트 파일은 포함하지 않습니다.
시뮬레이션을 다시 수행하거나 기준·데이터를 재튜닝하지 않는 문서 빌드입니다.

## 검토 범위

기존 BB 보고서 11개(230장)의 등록서, Y-y 전개, 측정, 인자 선정, 개선 검증, Control 패턴을 참고했습니다.
원문 PPTX나 사내 이미지/재무정보는 포함하지 않았습니다.
V2의 원시 파형 재계산 24개 검사를 다시 통과했습니다 (`v2_reaudit.log`).
PowerPoint 수치·차트·표·노트·슬라이드 경계를 별도 확인하며, 38장 모두 렌더링 화면을 검토했습니다.
별도 검증 실패 9건, 신규 포화 실패 2건, 단일 기준점 보정 한계와 제품·주파수 검증 미완료를 보존합니다.

## 제출 전 확인

지도 MBB·Owner, 공식 등록기간, 수치연구 완료보고의 인정 범위, 고객 판정 지표/기준을 확정해야 합니다.
이 항목을 가상의 승인·실측·금액으로 채우지 않았습니다.

AI 보조 제작: GPT-6 Astra Pro. 기술책임자의 최종 검토가 필요합니다.
