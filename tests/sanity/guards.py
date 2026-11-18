"""Guards: refuse input the method can't handle, fast and with a clear message (before any DFT).

Contract: `esp_figure.py calc <SMILES> --name x` exits non-zero within 60 s, and its output (stdout+stderr)
contains the keyword, case-insensitive, and no Python traceback (a clean message, e.g. sys.exit(...)):
  [CH3]                            -> "radical"   (open-shell; only closed-shell RKS is supported)
  [Pd]                             -> "Pd"        (element MMFF94 / 6-31G(d) can't do)
  CC(C(N)=O)CC(C(N)=O)CC(C)C(N)=O  -> "stereo"    (unspecified stereocentres)
Water still running is covered by the regression check (test_water.py).
"""
import subprocess, sys, tempfile
from _util import Checks, ROOT, UNSPEC_PAM3

ok = Checks()
for smi, word in (("[CH3]", "radical"), ("[Pd]", "Pd"), (UNSPEC_PAM3, "stereo")):
    with tempfile.TemporaryDirectory() as tmp:
        code = f"from esp_figure import calc; calc({smi!r}, 'guard', root={tmp!r})"
        try:
            r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=60)
            out, rc = (r.stdout + r.stderr), r.returncode
        except subprocess.TimeoutExpired:
            out, rc = "(still running after 60 s: no guard, it went on to compute)", None
    ok(f"guard {smi}", rc not in (0, None) and word.lower() in out.lower() and "Traceback" not in out, f"exit {rc}; {out.strip()[-200:]!r}")
ok.finish()
