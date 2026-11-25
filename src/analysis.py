"""Quantitative analysis for: False positives in ICS intrusion detection (Li, Shimanaeva).
A1 base-rate analysis, A2 operating-constraint threshold analysis, A3 alarm-logic simulation.
All outputs written to results/ as CSV + JSON summary."""
import json, os
import numpy as np
from scipy import stats, optimize
from numba import njit

os.makedirs("results", exist_ok=True)
out = {}

# ---------------- A1: base-rate (Bayesian detection rate) ----------------
TPR = 0.95
N_DAY = 1e5  # scored events per day (assumption, stated in Methods)
rows = []
for p in [1e-3, 1e-4, 1e-5, 1e-6]:
    for fpr in [1e-2, 1e-3, 1e-4, 1e-5, 1e-6]:
        ppv = TPR * p / (TPR * p + fpr * (1 - p))
        fa_day = N_DAY * (1 - p) * fpr
        rows.append(dict(p=p, fpr=fpr, ppv=ppv, false_alarms_day=fa_day))
out["A1"] = rows
with open("results/a1_base_rate.csv", "w") as f:
    f.write("p,fpr,ppv,false_alarms_per_day\n")
    for r in rows:
        f.write(f"{r['p']:.0e},{r['fpr']:.0e},{r['ppv']:.4f},{r['false_alarms_day']:.2f}\n")

# ---------------- A2: achievable recall under operating constraints ----------------
# benign score ~ N(0,1) (or unit-variance Student t, nu=5); attack ~ N(d,1)
NU = 5
t_scale = np.sqrt((NU - 2) / NU)  # unit-variance t
def thr_for_alpha(alpha, tail="normal"):
    if tail == "normal":
        return stats.norm.isf(alpha)
    return stats.t.isf(alpha, NU) * t_scale

constraints = {
    "passive_alert": 100 / N_DAY,            # <=100 alerts/day reviewed by analysts
    "operator_confirm": 10 / N_DAY,          # <=10 interruptions/day to operators
    "auto_block": 1 / (365 * N_DAY),         # <=1 false trip per year
}
dgrid = np.round(np.arange(1.0, 10.01, 0.25), 2)
a2 = []
for name, alpha in constraints.items():
    for tail in ["normal", "t5"]:
        h = thr_for_alpha(alpha, "normal" if tail == "normal" else "t")
        for d in dgrid:
            a2.append(dict(mode=name, tail=tail, alpha=alpha, threshold=h, d=float(d),
                           recall=float(stats.norm.sf(h - d))))
out["A2_constraints"] = {k: v for k, v in constraints.items()}
with open("results/a2_recall_vs_d.csv", "w") as f:
    f.write("mode,tail,alpha,threshold,d,recall\n")
    for r in a2:
        f.write(f"{r['mode']},{r['tail']},{r['alpha']:.3e},{r['threshold']:.3f},{r['d']},{r['recall']:.4f}\n")

# minimal d' needed for recall >= 0.9 under each constraint
need = {}
for name, alpha in constraints.items():
    for tail in ["normal", "t5"]:
        h = thr_for_alpha(alpha, "normal" if tail == "normal" else "t")
        need[f"{name}|{tail}"] = dict(threshold=float(h), d_for_recall90=float(h + stats.norm.isf(0.9) * -1 * -1) if False else float(h - stats.norm.isf(0.9)))
out["A2_d_needed_recall90"] = need

# cost-optimal (unconstrained) threshold, Bayes rule, p=1e-6, C_FN=1e6 units
P_ATT, C_FN = 1e-6, 1e6
cost_rows = []
for mode, cfp in [("passive_alert", 1.0), ("operator_confirm", 1e2), ("auto_block", 1e4)]:
    for d in [3.0, 4.0, 6.0]:
        t = (np.log((1 - P_ATT) * cfp / (P_ATT * C_FN)) + d * d / 2) / d
        alpha = stats.norm.sf(t); beta = stats.norm.sf(t - d)
        cost_rows.append(dict(mode=mode, c_fp=cfp, d=d, threshold=float(t), fpr=float(alpha),
                              recall=float(beta), false_pos_day=float(N_DAY * (1 - P_ATT) * alpha),
                              false_pos_year=float(365 * N_DAY * (1 - P_ATT) * alpha)))
out["A2_cost_optimal"] = cost_rows

# ---------------- A3: alarm logic simulation ----------------
@njit(cache=True)
def ar1(n, rho, seed):
    np.random.seed(seed)
    x = np.empty(n); s = np.sqrt(1 - rho * rho); v = np.random.randn()
    for i in range(n):
        v = rho * v + s * np.random.randn(); x[i] = v
    return x

@njit(cache=True)
def count_alarms(x, method, h, k, kappa):
    # returns number of alarm onsets; detector resets after each alarm
    n_al = 0; run = 0; S = 0.0; prev = False
    for i in range(x.shape[0]):
        a = False
        if method == 0:
            a = x[i] > h
            if a and not prev: n_al += 1
            prev = a
        elif method == 1:
            if x[i] > h: run += 1
            else: run = 0
            if run >= k:
                n_al += 1; run = 0
        else:
            S = max(0.0, S + x[i] - kappa)
            if S > h:
                n_al += 1; S = 0.0
    return n_al

@njit(cache=True)
def delays(rho, delta, method, h, k, kappa, trials, warm, horizon, seed):
    np.random.seed(seed)
    s = np.sqrt(1 - rho * rho); out = np.full(trials, -1.0)
    for tr in range(trials):
        v = np.random.randn(); run = 0; S = 0.0
        for i in range(warm):  # benign warm-up, state carried over, alarms reset state
            v = rho * v + s * np.random.randn()
            if method == 1:
                run = run + 1 if v > h else 0
                if run >= k: run = 0
            elif method == 2:
                S = max(0.0, S + v - kappa)
                if S > h: S = 0.0
        for j in range(horizon):
            v = rho * v + s * np.random.randn(); x = v + delta
            if method == 0:
                if x > h: out[tr] = j + 1; break
            elif method == 1:
                run = run + 1 if x > h else 0
                if run >= k: out[tr] = j + 1; break
            else:
                S = max(0.0, S + x - kappa)
                if S > h: out[tr] = j + 1; break
    return out

TARGET = 1 / 86400.0   # one false alarm per day at 1 Hz
L = 30_000_000         # ~347 days of benign samples per calibration
K, KAPPA = 3, 0.5
names = {0: "static", 1: "persist_3", 2: "cusum"}
a3 = {}
for rho in [0.0, 0.8]:
    x = ar1(L, rho, 7 if rho == 0 else 11)
    xv = ar1(L, rho, 101 if rho == 0 else 111)  # independent validation stream
    for m in [0, 1, 2]:
        lo, hi = (0.0, 8.0) if m != 2 else (0.5, 80.0)
        f = lambda h: count_alarms(x, m, h, K, KAPPA) / L - TARGET
        h = optimize.brentq(f, lo, hi, xtol=1e-3) if f(lo) > 0 and f(hi) < 0 else float("nan")
        far_val = count_alarms(xv, m, h, K, KAPPA) / L
        rec = dict(threshold=h, far_per_day_validation=far_val * 86400)
        # naive k-of-k calibration that assumes independent samples: alpha_sample = target^(1/k)
        if m == 1:
            h_naive = stats.norm.isf(TARGET ** (1 / K))
            rec["naive_threshold"] = float(h_naive)
            rec["naive_far_per_day"] = count_alarms(xv, 1, h_naive, K, KAPPA) / L * 86400
        for delta in [0.5, 1.0, 2.0, 4.0]:
            d = delays(rho, delta, m, h, K, KAPPA, 4000, 300, 3600, 999)
            det = d[d > 0]
            rec[f"delta{delta}"] = dict(p_detect_1h=float(len(det) / len(d)),
                                        p_detect_60s=float(np.mean((d > 0) & (d <= 60))),
                                        p_detect_300s=float(np.mean((d > 0) & (d <= 300))),
                                        median_delay_s=float(np.median(det)) if len(det) else None,
                                        p90_delay_s=float(np.percentile(det, 90)) if len(det) else None)
        a3[f"rho{rho}|{names[m]}"] = rec
        print(rho, names[m], json.dumps(rec))
out["A3"] = a3
with open("results/summary.json", "w") as fh:
    json.dump(out, fh, indent=1, default=float)
print(json.dumps(out["A2_d_needed_recall90"], indent=1))
for r in cost_rows: print(r)
