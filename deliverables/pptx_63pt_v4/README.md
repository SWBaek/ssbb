# SSBB V4 제출용 자료

- 문서: **V4** / 수치 데이터: **V2(63개 기준조건·60개 변동조건) 유지**.
- 본문35장, 용어집7장 및상세부록16장, 총58장.
- PPTX는 편집 가능한 텍스트·표·차트·도형이다. PDF는 열람용이다.
- 실제 제품 검증 및사내BB승인과구분된 수치설계연구이다.

## 파일

`SSBB_V4_Submission_BaekSeungwoo.pptx` / `.pdf`

`SSBB_V4_Glossary_and_Reading_Guide.md`: 용어56항목,읽는순서,통계해석,데이터사전.

`SSBB_V4_Review_and_Changes.md`: V3의48장재평가와V4변경근거.

`deck_v4.json` / `build_pptx_v4.py`: PPTX재생성용본문·디자인원본.

`source_data/`: 변경하지않은기존결과표·설정·계산정의. 전체원시파형은기존V2연구패키지에보존되어있다.

`analysis/` / `qa/`: 파생기술통계, 원자료정합검사, 리뷰기록.

## 재생성

```bash
python -m pip install python-pptx numpy pandas
python build_pptx_v4.py --spec deck_v4.json --out SSBB_V4_Submission_BaekSeungwoo.pptx
python analyze_existing_data.py --study source_data --out analysis
python validate_v4.py --root .
libreoffice --headless --convert-to pdf --outdir . SSBB_V4_Submission_BaekSeungwoo.pptx
```

Windows PowerPoint 열람용 글꼴은맑은고딕으로지정했다. 변환환경의글꼴에따라줄바꿈이달라질수있어PDF도함께제공한다. 글꼴파일이나기존사내PPT원본·이미지는패키지에포함하지않는다.

V3에서V4를다시편집하려면 `make_v4.py --v3 <V3 delivery폴더> --out <새폴더>`를사용할수있다. 최종파일의재생성에는해당V3폴더가필요하지않으며 `deck_v4.json`만사용한다.
