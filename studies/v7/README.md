# V7 — 240 Vac / 48 Arms / 11.52 kVA / Peak dq / 16 us

Recomputed numerical reference study of single-phase V2G AC current control. The PWM and controller both operate at62,500 Hz (16us), one controller evaluation per PWM period. External commands `id_peak_a` and `iq_peak_a` are peak-valued DC dq currents. Their vector bound is67.8822509939 Apeak, corresponding to48 Arms fundamental current.

## Scope

All502 numerical execution records were freshly computed at the updated V7 specification. V6 implementation was revised, but no prior performance CSV,waveform or selected settings were loaded as study inputs. Nominal240×48=11,520 VA. Additional216/264 V cases are model sensitivity tests, not certified capability claims;264×48 exceeds the nominalVA.

This public directory contains numerical methods, assumptions, source, result tables and a technical-only report. Internal corporate procedure material and the private submission edition are not included. The original company slides and fonts are not distributed.

## Recompute from a clean directory

Python3.13, dependencies in `requirements.txt`. Create the empty `results`, `waveforms`, `qa`, `report` directories first.

```sh
python -m pip install -r requirements.txt
python src/test_model.py
python src/study.py
python src/analyze.py
python src/audit_v7.py
python src/make_report.py
libreoffice --headless --convert-to pdf --outdir report report/SSBB_V7_Technical_Public.pptx
python src/verify_report.py
```

`study.py` rejects existing waveform output rather than silently mixing versions. To repeat the entire study, use a new output directory containing the source and specification. To regenerate the report from existing V7 results, run only `make_report.py`,export PDF,and `verify_report.py`.

## Data organization

- `specification.json`: confirmed inputs, modeled assumptions, provisional engineering criteria.
- `source_lineage.json`: pinned upstream implementation and exact changes.
- `results/main_conditions.csv`:47 reference conditions;9 used for27-candidate selection and38 evaluated after selection.
- `results/all_runs.csv`:502 execution records, all numerical metrics and raw waveform hashes.
- `results/doe.csv`, `candidates.csv`, `selected_control.json`:243 DOE responses,27 candidate summaries and selected configuration.
- `results/*paired.csv`, `*failures.csv`: before/after comparisons and retained failures.
- `waveforms/*.npz`:502 current,PWM,controller and metadata records, supplied separately as Release archives.
- `qa/`: unit tests, full raw recalculation, Fourier/FFT cross-check, time-step/duration comparison, clock/FIFO and replay audits.
- `report/`:editable technicalPPTX,PDF,frozen deck specification and object verification.
- `docs/`:signal/model conventions,statistical interpretation,glossary.

## Interpretation

THD≤5% and target95% are provisional engineering goals,not externally prescribed certification requirements. Pass in a QA file means record or computation integrity; it does not mean all physical conditions pass. ActualRMS≤48 A includes ripple and is assessed separately from the fundamental dq command bound. Hardware matching,actualLF commutation,energy dynamics and product approval remain unvalidated.
