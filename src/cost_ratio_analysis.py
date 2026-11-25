"""Sensitivity of the cost-optimal (Bayes) threshold to the cost of a false positive.

The Bayes threshold h* = [ln((1 - p) C_FP / (p C_FN)) + d'^2 / 2] / d' depends on the two costs only through
their ratio R = C_FN / C_FP. This script therefore
  (a) computes, for each response mode and separability d', the break-even ratio R*: the largest C_FN / C_FP for
      which the cost-optimal threshold still meets the mode's false-positive budget; and
  (b) sweeps C_FP over 0.1x, 1x and 10x the value used in the paper for each mode, crossed with C_FN = 1e5, 1e6, 1e7.
Writes results/r4_cost_breakeven.csv and results/r4_cost_sweep.csv. Deterministic; no random numbers.
"""
import csv
import math
from pathlib import Path

from scipy import stats

OUT = Path("results")
OUT.mkdir(exist_ok=True)
P, N = 1e-6, 1e5
MODES = [  # name, budget (false positives per day), C_FP used in the paper
    ("Passive alerting", 100.0, 1.0),
    ("Operator-confirmed", 10.0, 1e2),
    ("Automatic response", 1.0 / 365, 1e4),
]


def bayes_threshold(d, ratio):
    return (math.log((1 - P) / (P * ratio)) + d * d / 2) / d


rows = []
for name, budget_day, cfp in MODES:
    alpha = budget_day / (N * (1 - P))
    h_b = stats.norm.isf(alpha)
    for d in [3.0, 4.0, 5.0, 6.0, 7.0]:
        r_star = (1 - P) / P * math.exp(-(d * h_b - d * d / 2))
        rows.append(dict(mode=name, budget_per_day=f"{budget_day:.6g}", alpha=f"{alpha:.6e}",
                         budget_threshold=f"{h_b:.6f}", d=d, breakeven_ratio=f"{r_star:.6e}",
                         breakeven_C_FN_at_paper_C_FP=f"{r_star * cfp:.6e}"))
with open(OUT / "r4_cost_breakeven.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)

sweep = []
for name, budget_day, cfp0 in MODES:
    for mult in [0.1, 1.0, 10.0]:
        cfp = cfp0 * mult
        for cfn in [1e5, 1e6, 1e7]:
            for d in [4.0, 6.0]:
                h = bayes_threshold(d, cfn / cfp)
                a, b = stats.norm.sf(h), stats.norm.sf(h - d)
                fp_day = N * (1 - P) * a
                sweep.append(dict(mode=name, C_FP=f"{cfp:g}", C_FN=f"{cfn:g}", ratio=f"{cfn / cfp:g}", d=d,
                                  threshold=f"{h:.6f}", recall=f"{b:.6f}", fp_per_day=f"{fp_day:.6e}",
                                  fp_per_year=f"{365 * fp_day:.6e}",
                                  within_budget=int(fp_day <= budget_day * (1 + 1e-9))))
with open(OUT / "r4_cost_sweep.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=sweep[0].keys())
    w.writeheader()
    w.writerows(sweep)

for r in rows:
    print(r["mode"], r["d"], r["breakeven_ratio"], r["breakeven_C_FN_at_paper_C_FP"])
ok = {}
for s in sweep:
    k = (s["mode"], s["d"])
    ok.setdefault(k, [0, 0])
    ok[k][0] += s["within_budget"]
    ok[k][1] += 1
print({k: f"{v[0]}/{v[1]}" for k, v in ok.items()})
