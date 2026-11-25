# False positives in ICS intrusion detection: Self-DoS and threshold tuning

[![Reproducibility check](https://github.com/krrrrqqqq/ics-ids-false-positives/actions/workflows/reproduce.yml/badge.svg)](https://github.com/krrrrqqqq/ics-ids-false-positives/actions/workflows/reproduce.yml)

Code, generated data and the literature screening log for:

> D. Li, K. Shimanayeva. *False Positives in Intrusion Detection for Critical Infrastructure: Balancing Missed Attacks Against Self-Inflicted Denial of Service.* International Information Technology University (IITU), Almaty, Kazakhstan, 2026.

The paper asks how sensitive an intrusion detection system (IDS) for an industrial control system may be when its alarms trigger different responses: an analyst alert, an operator decision, or an automatic block or trip. Everything here is synthetic and fully reproducible; no plant data is used.

## What is in this repository

| Path | Contents | Paper section |
| --- | --- | --- |
| `src/analysis.py` | Base-rate model, operating-constraint model, calibration of the alarm-logic simulation | 2.2–2.4; Tables 3–4, Fig. 1 |
| `src/revision_analysis.py` | Sensitivity analysis (budget, event volume, tail heaviness), cost-optimal operating points, full simulation with 95% intervals | 2.3–2.4; Tables 5–7, Fig. 2 |
| `src/cost_ratio_analysis.py` | Sensitivity of the cost-optimal threshold to the false-positive cost: break-even ratio C_FN/C_FP per mode and separability, and a sweep of C_FP (0.1×, 1×, 10×) × C_FN | 2.3; Table 6 |
| `results/` | All generated outputs used in the tables and figures | 3 |
| `data/screening_log.csv` | Title/abstract and full-assessment decisions for the 81 OpenAlex records that passed the keyword filter | 2.1 |
| `data/included_studies.csv` | Extraction table for the 22 included studies: family, evaluation data, false-positive units, and where the full text used for checking was found | 2.1; Table 2 |
| `scripts/check_reproducibility.py` | Re-runs both scripts in a scratch folder and compares every output with `results/` | — |
| `scripts/make_figures.py` | Draws Fig. 1 and Fig. 2 from `results/` into `figures/` (requires matplotlib) | Figs. 1–2 |

### Outputs and where they appear

| File | Used in |
| --- | --- |
| `results/a1_base_rate.csv` | Table 3 (positive predictive value by base rate and FPR) |
| `results/a2_recall_vs_d.csv` | Fig. 1, Table 4 |
| `results/r1_sensitivity_dprime90.csv` | Table 5 |
| `results/revision.json` → `R2` | Table 6 (cost-optimal operating points) |
| `results/r3_simulation_full.csv` | Table 7, Fig. 2 |
| `results/r4_cost_breakeven.csv` | Table 6, last column (break-even C_FN/C_FP) |
| `results/r4_cost_sweep.csv` | Section 3.3, sweep of C_FP and C_FN |
| `results/revision.json` → `FAR` | Validation false-alarm rates (Section 3.4) |

## Reproduce

Python 3.10 or newer.

```bash
pip install -r requirements.txt
python src/analysis.py            # about 40 s; writes results/summary.json, a1, a2
python src/revision_analysis.py   # about 10 s; needs results/summary.json
python src/cost_ratio_analysis.py  # under 1 s
python scripts/check_reproducibility.py   # optional: verifies the committed results
```

Random seeds are fixed, so the outputs are identical on the pinned library versions. The same check runs on every push through GitHub Actions.

## Literature search

OpenAlex, run on 26 November 2026, works published 2000–2025, matched in title, abstract or keywords:

```
("intrusion detection" OR "anomaly detection") AND ("industrial control system" OR SCADA OR "cyber-physical")
AND ("false positive" OR "false alarm")
```

617 records. A keyword filter (`threshold`, `CUSUM`, `alarm/alert management`, `fatigue`, `correlation`, `flood`, `reduction`, `triage`, `operating point`) left 81, which were screened by title and abstract; 17 were assessed on their full abstracts and metadata, and 14 were included. Backward snowballing added 8 studies. Every decision and its reason is in `data/screening_log.csv`. The extracted entries were then checked against the full text of every included study; `data/included_studies.csv` records where each text was found.

## Citation

See `CITATION.cff`, or use the "Cite this repository" button on GitHub.

## Licence

Code: MIT (`LICENSE`). Generated data and the screening log: CC BY 4.0 (`LICENSE-DATA`).
