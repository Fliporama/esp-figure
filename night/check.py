"""Regression checks against night/reference.json. Exit 0 if all pass, 1 otherwise.

  python night/check.py [--ref night/reference.json] [--out night/check_result.json]

Entry kinds under "regression":
  {"cmd": "test_water.py"}                       pass = script exits 0
  {"xyz": "<file>", "scf_energy": {...}, ...}    default-settings single point; each of
                                                 scf_energy / esp_min / esp_max = {"value", "tol"}
A null "value" fails (reported with the computed number, so it can be proposed as a reference).
"""
import argparse, json, re, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def single_point(xyz, name):
    from esp_figure import calc
    with tempfile.TemporaryDirectory() as tmp:
        log = (calc(str(xyz), name, root=tmp) / "method.txt").read_text()
    e = float(re.search(r"SCF energy: (\S+)", log).group(1))
    lo, hi = map(float, re.search(r"ESP range on surface: (\S+) to (\S+)", log).groups())
    return {"scf_energy": e, "esp_min": lo, "esp_max": hi}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default=ROOT / "night/reference.json")
    ap.add_argument("--out", default=ROOT / "night/check_result.json")
    a = ap.parse_args()
    checks = []
    for name, entry in json.loads(Path(a.ref).read_text())["regression"].items():
        if "cmd" in entry:
            ok = subprocess.run([sys.executable, entry["cmd"]], cwd=ROOT).returncode == 0
            checks.append({"name": name, "value": ok, "expected": True, "tol": None, "pass": ok})
            continue
        got = single_point(ROOT / entry["xyz"], name)   # absolute xyz paths pass through unchanged
        for key in ("scf_energy", "esp_min", "esp_max"):
            if key in entry:
                exp, tol = entry[key]["value"], entry[key]["tol"]
                checks.append({"name": f"{name}.{key}", "value": got[key], "expected": exp, "tol": tol,
                               "pass": exp is not None and abs(got[key] - exp) <= tol})
    result = {"checks": checks, "all_pass": all(c["pass"] for c in checks)}
    Path(a.out).write_text(json.dumps(result, indent=1))
    for c in checks:
        print(f"{'PASS' if c['pass'] else 'FAIL'} {c['name']}: {c['value']} (expected {c['expected']} ± {c['tol']})")
    sys.exit(0 if result["all_pass"] else 1)


if __name__ == "__main__":
    main()
