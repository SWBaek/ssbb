# SSBB V6: Peak dq / 230 Vac·48 Arms / 62.5 kHz 1:1

이 폴더는 V5의 사양 오류를 배제하고 전면 재계산한 V6 참조 수치연구다. 보고서는 `report/SSBB_V6_Submission_BaekSeungwoo.pptx` 및 PDF이다.

**고정 사양:** 230 Vrms, 48 Arms, Peak dq의 DC 명령, PWM 및 제어 연산 각각 62,500 Hz·16 μs. θ는 PLL 내부 위상이다.

**산술 불일치:** 제품급 명칭은 요청대로 11.52 kVA급이다. 실제 입력의 곱은 230×48=11.04 kVA이다. 240 V로 바꾸거나 50.087 Arms로 높이지 않았다. 명판 기준은 별도 확인이 필요하다.

## 실행 순서
Python 3.13, `requirements.txt`의 패키지를 사용한다. PowerPoint 생성은 python-pptx, PDF 변환은 LibreOffice Impress 및 한국어 표시 가능한 폰트가 필요하다. 폰트 파일은 배포하지 않는다.

```bash
python -m pip install -r requirements.txt
python src/test_model.py
python src/study.py
python src/analyze.py
python src/make_report.py
libreoffice --headless --convert-to pdf --outdir report report/SSBB_V6_Submission_BaekSeungwoo.pptx
python src/verify_report.py
python src/package_delivery.py
```

**재계산은 빈 출력 폴더를 가진 새 복사본에서 실행한다.** `study.py`는 기존 파형을 덮어쓰지 않는다. 원본 결과를 보존한 채 새 복사본의 `results`, `waveforms`, `qa`, `report`를 비운 후 실행한다. 보고서만 재생성할 때는 기존 V6 데이터에서 `make_report.py`와 문서 검증만 실행한다.

## 결과의 성격
- 기본 230 V의 47개 운전조건 = 후보 선정용 9개 + 선정 미사용 38개.
- 27후보×9조건=DOE 243회. 전체 캠페인 502회. 재현 감사의 별도 4회는 성능 데이터에 다시 더하지 않는다.
- 전압 추가 24개, 회로·검출 편차 24개, LF 구조 변경 6개는 다른 평가 집합이다.
- THD 5%는 잠정 설계기준이다. 전류 RMS와 다른 제약을 함께 본 종합 만족과 구분한다.
- 실물, PSIM, 실제 양산 SW 및 인증 검증 결과가 아니다. V5 성능값 재사용 및 이전 THD 값에 맞춘 보정은 없다.

현재 주요 결과와 실패 조건은 `report/V6_Summary.md`, `results/summary.json`, `docs/V6_Review.md`에 있다. 모든 입력·가정·한계는 `specification.json` 및 `docs/Model_and_Conventions.md`에 구분했다.

## 원시 파형
`SSBB_V6_RawWaveforms_*.zip`을 코드 패키지와 같은 위치에 풀면 `ssbb_v6/waveforms`에 합쳐진다. NPZ는 수치 배열과 JSON 메타데이터만 포함하며 pickle을 사용하지 않는다. 모든 결과 행의 `run_id`가 같은 이름의 파형을 가리킨다. 코드·사양·실행 조건, PWM/제어 수, 적용 명령 출처를 기록했다. `qa/raw_audit.json`은 저장 파형의 전 지표 재계산 결과다.

## 배포와 버전 관리
기존 V1~V5를 덮어쓰지 않는다. GitHub에는 V6 소스·CSV·보고서·검증기록을 새 경로로 저장하고, 대용량 원시 파형은 같은 비공개 저장소의 V6 Release 자산으로 제공한다. 로컬 제작물과 원격 재계산물은 환경 정보를 각각 기록하며, 원격 확인 전에는 재현 완료로 표현하지 않는다.
