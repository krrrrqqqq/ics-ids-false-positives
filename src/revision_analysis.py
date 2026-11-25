"""Revision analyses (reviewer items 2 and 3).
R1: sensitivity of required separability d'90 to FP budget, event volume N and benign-tail heaviness.
R2: cost-optimal operating points for d' = 4 and 6, and sensitivity to C_FN.
R3: full alarm-logic simulation table (logic x rho x delta) with 95% CIs.
Thresholds for R3 are taken from the calibration in analysis.py (results/summary.json)."""
import json, math
import numpy as np
from scipy import stats
from numba import njit

S = json.load(open("results/summary.json"))
out = {}

# ---------- R1: sensitivity of d'90 ----------
def thr(alpha, tail):
    if tail == "gauss":
        return stats.norm.isf(alpha)
    nu = tail
    return stats.t.isf(alpha, nu) * math.sqrt((nu - 2) / nu)

z90 = stats.norm.isf(0.9)  # = -1.2816
modes = {
    "Passive alerting": ("per day", [30, 100, 300], 1.0),
    "Operator-confirmed": ("per day", [3, 10, 30], 1.0),
    "Automatic response": ("per year", [0.1, 1, 10], 1 / 365),
}
r1 = []
for mode, (unit, budgets, per_day) in modes.items():
    for b in budgets:
        row = dict(mode=mode, budget=b, unit=unit)
        for N in [1e4, 1e5, 1e6]:
            a = b * per_day / N
            row[f"gauss_N{int(N)}"] = thr(a, "gauss") - z90
        a = b * per_day / 1e5
        for nu in [30, 10, 5, 3]:
            row[f"t{nu}_N100000"] = thr(a, nu) - z90
        r1.append(row)
out["R1"] = r1

# ---------- R2: cost-optimal operating points ----------
P, N = 1e-6, 1e5
r2 = []
for CFN in [1e5, 1e6, 1e7]:
    for mode, cfp in [("Passive alerting", 1.0), ("Operator-confirmed", 1e2), ("Automatic response", 1e4)]:
        for d in [4.0, 6.0]:
            t = (math.log((1 - P) * cfp / (P * CFN)) + d * d / 2) / d
            a, b = stats.norm.sf(t), stats.norm.sf(t - d)
            r2.append(dict(C_FN=CFN, mode=mode, C_FP=cfp, d=d, recall=b,
                           fp_day=N * (1 - P) * a, fp_year=365 * N * (1 - P) * a))
out["R2"] = r2

# ---------- R3: simulation with CIs ----------
@njit(cache=True)
def ar1(n, rho, seed):
    np.random.seed(seed)
    x = np.empty(n); s = np.sqrt(1 - rho * rho); v = np.random.randn()
    for i in range(n):
        v = rho * v + s * np.random.randn(); x[i] = v
    return x

@njit(cache=True)
def count_alarms(x, method, h, k, kappa):
    n_al = 0; run = 0; S_ = 0.0; prev = False
    for i in range(x.shape[0]):
        if method == 0:
            a = x[i] > h
            if a and not prev: n_al += 1
            prev = a
        elif method == 1:
            run = run + 1 if x[i] > h else 0
            if run >= k:
                n_al += 1; run = 0
        else:
            S_ = max(0.0, S_ + x[i] - kappa)
            if S_ > h:
                n_al += 1; S_ = 0.0
    return n_al

@njit(cache=True)
def delays(rho, delta, method, h, k, kappa, trials, warm, horizon, seed):
    np.random.seed(seed)
    s = np.sqrt(1 - rho * rho); out = np.full(trials, -1.0)
    for tr in range(trials):
        v = np.random.randn(); run = 0; S_ = 0.0
        for i in range(warm):
            v = rho * v + s * np.random.randn()
            if method == 1:
                run = run + 1 if v > h else 0
                if run >= k: run = 0
            elif method == 2:
                S_ = max(0.0, S_ + v - kappa)
                if S_ > h: S_ = 0.0
        for j in range(horizon):
            v = rho * v + s * np.random.randn(); x = v + delta
            if method == 0:
                if x > h: out[tr] = j + 1; break
            elif method == 1:
                run = run + 1 if x > h else 0
                if run >= k: out[tr] = j + 1; break
            else:
                S_ = max(0.0, S_ + x - kappa)
                if S_ > h: out[tr] = j + 1; break
    return out

def wilson(k, n, z=1.959964):
    p = k / n; den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den; hw = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return p, max(0.0, c - hw), min(1.0, c + hw)

def median_ci(d, n_total):
    # distribution-free CI for the median of all trials (undetected = +inf), via binomial order statistics
    arr = np.sort(np.where(d > 0, d, np.inf))
    n = n_total
    lo_i = int(stats.binom.ppf(0.025, n, 0.5)); hi_i = int(stats.binom.isf(0.025, n, 0.5))
    med = np.median(arr) if np.isfinite(np.median(arr)) else math.inf
    return med, arr[max(lo_i - 1, 0)], arr[min(hi_i, n - 1)]

def poisson_ci(k, z=0.05):
    lo = 0.0 if k == 0 else stats.chi2.ppf(z / 2, 2 * k) / 2
    hi = stats.chi2.ppf(1 - z / 2, 2 * k + 2) / 2
    return lo, hi

K, KAPPA, L, TRIALS = 3, 0.5, 30_000_000, 4000
names = {0: "Static threshold", 1: "Persistence (3 in a row)", 2: "CUSUM"}
keys = {0: "static", 1: "persist_3", 2: "cusum"}
r3, far = [], []
for rho in [0.0, 0.8]:
    xv = ar1(L, rho, 101 if rho == 0 else 111)  # same validation stream as analysis.py
    for m in [0, 1, 2]:
        h = S["A3"][f"rho{rho}|{keys[m]}"]["threshold"]
        n_al = count_alarms(xv, m, h, K, KAPPA)
        days = L / 86400
        lo, hi = poisson_ci(n_al)
        far.append(dict(rho=rho, logic=names[m], threshold=h, alarms=n_al, days=days,
                        rate=n_al / days, lo=lo / days, hi=hi / days))
        if m == 1:
            hn = S["A3"][f"rho{rho}|persist_3"]["naive_threshold"]
            nn = count_alarms(xv, 1, hn, K, KAPPA); lo2, hi2 = poisson_ci(nn)
            far.append(dict(rho=rho, logic="Persistence, naive calibration", threshold=hn, alarms=nn,
                            days=days, rate=nn / days, lo=lo2 / days, hi=hi2 / days))
        for delta in [0.5, 1.0, 2.0, 4.0]:
            d = delays(rho, delta, m, h, K, KAPPA, TRIALS, 300, 3600, 999)
            row = dict(rho=rho, logic=names[m], delta=delta, n=TRIALS)
            for lab, lim in [("60s", 60), ("300s", 300), ("1h", 3600)]:
                k = int(np.sum((d > 0) & (d <= lim)))
                row[lab] = wilson(k, TRIALS)
            row["median"] = median_ci(d, TRIALS)
            r3.append(row)
out["R3"] = r3; out["FAR"] = far
json.dump(out, open("results/revision.json", "w"), indent=1, default=lambda o: float(o))

# CSV exports for supplementary material
with open("results/r1_sensitivity_dprime90.csv", "w") as f:
    cols = [c for c in r1[0] if c not in ("mode", "budget", "unit")]
    f.write("mode,budget,unit," + ",".join(cols) + "\n")
    for r in r1:
        f.write(f"{r['mode']},{r['budget']},{r['unit']}," + ",".join(f"{r[c]:.2f}" for c in cols) + "\n")
with open("results/r3_simulation_full.csv", "w") as f:
    f.write("rho,logic,delta_sd,n,p60,p60_lo,p60_hi,p300,p300_lo,p300_hi,p1h,p1h_lo,p1h_hi,median_s,median_lo,median_hi\n")
    for r in r3:
        vals = [r["60s"], r["300s"], r["1h"]]
        f.write(f"{r['rho']},{r['logic']},{r['delta']},{r['n']}," +
                ",".join(f"{a:.4f},{b:.4f},{c:.4f}" for a, b, c in vals) +
                ",{:.0f},{:.0f},{:.0f}\n".format(*[x if math.isfinite(x) else -1 for x in r["median"]]))
print("R1"); [print(r) for r in r1]
print("R2"); [print(r) for r in r2]
print("FAR"); [print(r) for r in far]
print("R3"); [print(r["rho"], r["logic"], r["delta"], [tuple(round(v, 3) for v in r[x]) for x in ("60s", "300s", "1h")], r["median"]) for r in r3]
