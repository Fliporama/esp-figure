"""Regression: default-settings single point (B3LYP/6-31G(d), gas) on the locked PAM3 geometry reproduces the
reference energy and ESP range (2026-11-11). A change here means the default method or surface changed. ~3 min."""
import re, tempfile
from _root import ROOT
from esp_figure import calc

with tempfile.TemporaryDirectory() as root:
    log = (calc(str(ROOT / "tests/data/pam3_opt.xyz"), "pam3", root=root) / "method.txt").read_text(encoding="utf-8")
e = float(re.search(r"SCF energy: (\S+)", log).group(1))
lo, hi = map(float, re.search(r"ESP range on surface: (\S+) to (\S+)", log).groups())
assert abs(e - -782.4865368) < 1e-6, e
assert abs(lo - -0.0663) < 1e-4 and abs(hi - 0.0780) < 1e-4, (lo, hi)
print(f"ok (E {e:.8f} Eh, ESP {lo:.4f} to {hi:.4f} a.u.)")
