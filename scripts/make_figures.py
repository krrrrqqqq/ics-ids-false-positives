"""Draw Fig. 1 and Fig. 2 of the article from the committed results.

Usage: python scripts/make_figures.py [output_dir]
Writes fig1_recall_vs_separability.png and fig2_alarm_logic.png (300 dpi).
"""
import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "figures"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Liberation Serif", "Nimbus Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "font.size": 10,
    "axes.labelsize": 10,
    "legend.fontsize": 9,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "axes.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
})
CM = 1 / 2.54

# ---------- Fig. 1: recall versus separability ----------
rows = [r for r in csv.DictReader(open(RES / "a2_recall_vs_d.csv")) if r["tail"] == "normal"]
modes = [
    ("passive_alert", "Passive (≤ 100/day)", "-", "#9ecae1"),
    ("operator_confirm", "Operator-confirmed (≤ 10/day)", "--", "#4292c6"),
    ("auto_block", "Automatic (≤ 1/year)", "-", "#08306b"),
]
d90 = {"passive_alert": 4.37, "operator_confirm": 5.00, "auto_block": 6.72}
fig, ax = plt.subplots(figsize=(16 * CM, 8 * CM))
for key, label, ls, col in modes:
    pts = [(float(r["d"]), float(r["recall"])) for r in rows if r["mode"] == key]
    pts.sort()
    ax.plot([p[0] for p in pts], [100 * p[1] for p in pts], ls, color=col, lw=1.6, label=label)
    ax.plot(d90[key], 90, "o", color=col, ms=4.5, zorder=3)
    ax.vlines(d90[key], 0, 90, colors=col, lw=0.7, linestyles=":")
    ax.annotate(f"{d90[key]:.1f}", (d90[key], 2), xytext=(3, 0), textcoords="offset points", fontsize=9)
ax.axhline(90, color="0.5", lw=0.7, ls=(0, (4, 3)))
ax.text(1.05, 91.5, "90% recall", fontsize=9, color="0.3")
ax.set_xlim(1, 10)
ax.set_ylim(0, 102)
ax.set_yticks([0, 25, 50, 75, 90, 100])
ax.set_xlabel("Detector separability $d$′ (distance between benign and attack score means, in SD)")
ax.set_ylabel("Recall (%)")
ax.legend(loc="lower left", frameon=False, ncol=3, bbox_to_anchor=(0, 1.0), handlelength=2.4, columnspacing=1.4)
fig.tight_layout()
fig.savefig(OUT / "fig1_recall_vs_separability.png", dpi=300)
plt.close(fig)

# ---------- Fig. 2: alarm logics at equal false-alarm rate ----------
sim = [r for r in csv.DictReader(open(RES / "r3_simulation_full.csv")) if float(r["rho"]) == 0.8]
logics = [
    ("Static threshold", "#d9d9d9", ""),
    ("Persistence (3 in a row)", "#969696", "///"),
    ("CUSUM", "#08306b", ""),
]
deltas = [0.5, 1.0, 2.0, 4.0]
w = 0.26
fig, ax = plt.subplots(figsize=(16 * CM, 7.5 * CM))
for i, (name, col, hatch) in enumerate(logics):
    xs, ys, lo, hi = [], [], [], []
    for j, dl in enumerate(deltas):
        r = next(r for r in sim if r["logic"] == name and float(r["delta_sd"]) == dl)
        y = 100 * float(r["p300"])
        xs.append(j + (i - 1) * w)
        ys.append(y)
        lo.append(y - 100 * float(r["p300_lo"]))
        hi.append(100 * float(r["p300_hi"]) - y)
    bars = ax.bar(xs, ys, w * 0.95, color=col, hatch=hatch, edgecolor="black", linewidth=0.5, label=name)
    ax.errorbar(xs, ys, yerr=[lo, hi], fmt="none", ecolor="black", elinewidth=0.7, capsize=2)
    for x, y in zip(xs, ys):
        ax.text(x, y + 2.5, f"{y:.0f}", ha="center", va="bottom", fontsize=8)
ax.set_xticks(range(len(deltas)))
ax.set_xticklabels(["0.5σ", "1σ", "2σ", "4σ"])
ax.set_ylim(0, 112)
ax.set_yticks([0, 25, 50, 75, 100])
ax.set_xlabel("Attack magnitude (step bias added to the residual, in standard deviations)")
ax.set_ylabel("Detected within 5 min (%)")
ax.legend(loc="upper left", frameon=False, ncol=3, bbox_to_anchor=(0, 1.08))
fig.tight_layout()
fig.savefig(OUT / "fig2_alarm_logic.png", dpi=300)
plt.close(fig)
print("written to", OUT)
