"""Run every test (tests/test_*.py) and sanity check (tests/sanity/*.py), one process each.

  python tests/run_all.py                 # everything: several hours (freq, IR, NCI, IGM run real DFT)
  python tests/run_all.py water extrema   # only scripts whose name contains one of these words
  python tests/run_all.py --timeout 3600

Exit codes of a script: 0 pass, 77 skip (feature not built, or local reference files absent), anything else fail.
Sanity checks print PASS/FAIL lines; those are shown for each script. Exit 0 if nothing failed."""
import argparse, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument("only", nargs="*", help="run only scripts whose file name contains one of these")
ap.add_argument("--timeout", type=int, default=7200, help="seconds per script (default 7200)")
a = ap.parse_args()
scripts = sorted(HERE.glob("test_*.py")) + sorted(p for p in (HERE / "sanity").glob("*.py") if p.name != "_util.py")
scripts = [p for p in scripts if not a.only or any(w in p.name for w in a.only)]
failed = []
for p in scripts:
    t0 = time.time()
    try:
        r = subprocess.run([sys.executable, str(p)], cwd=HERE.parent, capture_output=True, text=True, timeout=a.timeout)
        status, log = {0: "PASS", 77: "SKIP"}.get(r.returncode, "FAIL"), r.stdout + r.stderr
    except subprocess.TimeoutExpired:
        status, log = "FAIL", f"timed out after {a.timeout} s"
    print(f"{status} {p.relative_to(HERE.parent)} ({time.time() - t0:.0f} s)", flush=True)
    lines = [l for l in log.splitlines() if l.startswith(("PASS", "FAIL", "SKIP"))]
    for l in lines if status != "FAIL" else lines or log.splitlines()[-15:]:
        print("   ", l)
    if status == "FAIL":
        failed.append(p.name)
print(f"\n{len(scripts) - len(failed)}/{len(scripts)} passed or skipped" + (f"; failed: {', '.join(failed)}" if failed else ""))
sys.exit(1 if failed else 0)
