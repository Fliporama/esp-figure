"""Optimisation convergence choice for floppy molecules.

Contract: calc(..., opt=True, opt_conv="qchem")  (CLI --opt-conv qchem) passes qccnv=True to geomeTRIC:
converged when the RMS gradient (3e-4) holds AND either the energy change (1e-6 Eh) or the RMS displacement
(1.2e-3) holds; max criteria are not used (geomeTRIC optimize.py). Default opt_conv="gau" is unchanged. method.txt gets one line starting
  "optimisation convergence: "
naming the rule (default runs say "gau"). Reason: PAM3 ext (2026-11-12) met energy + gradients by ~step 46
but crept on to step 58+ on the displacement criterion alone (floppy torsions).
Pass on n-butane if: both runs converge; the qchem run takes strictly fewer steps than the default; final
energies agree within 1e-6 Eh; each method.txt names its rule.
Why butane, not formamide: rigid formamide stops at step 7 under both rules (dE 0), so a qchem flag that never
reaches geomeTRIC would still pass. Butane's soft C-C torsion separates them (2026-11-12, geomeTRIC with
RDKit seed 7: gau 5 steps, qchem 4, dE 2.1e-7 Eh, ~2.5 min per run). If a geomeTRIC upgrade closes the
one-step gap this fails loudly; pick another soft molecule then, don't loosen to <=.
"""
import re, tempfile
from _util import Checks, esp_figure, need

need("opt_conv")
ok = Checks()


def run(root, **kw):
    log = (esp_figure.calc("CCCC", "b", opt=True, root=root, **kw) / "method.txt").read_text(encoding="utf-8")
    e = float(re.search(r"SCF energy: (\S+)", log).group(1))
    n = int(re.search(r"optimisation steps: (\d+)", log).group(1))
    rule = re.search(r"optimisation convergence: (.+)", log)
    return e, n, rule.group(1) if rule else ""


with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
    e0, n0, r0 = run(a)
    e1, n1, r1 = run(b, opt_conv="qchem")
ok("default run names its rule (gau)", "gau" in r0.lower(), r0)
ok("qchem run names its rule", "qchem" in r1.lower(), r1)
ok("qchem stops earlier on a soft torsion", n1 < n0, f"{n1} vs {n0}")
ok("same minimum within 1e-6 Eh", abs(e1 - e0) <= 1e-6, f"{e1:.8f} vs {e0:.8f}")
ok.finish()
