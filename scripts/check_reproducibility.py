"""Re-run both analysis scripts in a scratch folder and compare every output with the committed results/.

Usage (from the repository root):  python scripts/check_reproducibility.py
Exit code 0 = all outputs reproduced within tolerance; 1 = a difference was found.
"""
import csv
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RTOL, ATOL = 1e-6, 1e-9
FILES = ["a1_base_rate.csv", "a2_recall_vs_d.csv", "r1_sensitivity_dprime90.csv",
         "r3_simulation_full.csv", "summary.json", "revision.json"]


def close(a, b):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if math.isinf(a) or math.isinf(b) or math.isnan(a) or math.isnan(b):
            return str(a) == str(b)
        return math.isclose(a, b, rel_tol=RTOL, abs_tol=ATOL)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(close(a[k], b[k]) for k in a)
    return a == b


def num(x):
    try:
        return float(x)
    except ValueError:
        return x


def compare_csv(p, q):
    ra = list(csv.reader(open(p)))
    rb = list(csv.reader(open(q)))
    return len(ra) == len(rb) and all(close([num(x) for x in a], [num(x) for x in b]) for a, b in zip(ra, rb))


def main():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        shutil.copytree(ROOT / "src", tmp / "src")
        (tmp / "results").mkdir()
        for script in ["analysis.py", "revision_analysis.py"]:
            print(f"running {script} ...", flush=True)
            subprocess.run([sys.executable, str(tmp / "src" / script)], cwd=tmp, check=True,
                           stdout=subprocess.DEVNULL)
        ok = True
        for name in FILES:
            new, old = tmp / "results" / name, ROOT / "results" / name
            if name.endswith(".json"):
                same = close(json.loads(new.read_text()), json.loads(old.read_text()))
            else:
                same = compare_csv(new, old)
            print(f"{'OK  ' if same else 'DIFF'} {name}")
            ok &= same
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
