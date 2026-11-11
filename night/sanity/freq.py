"""Frequency check: harmonic frequencies prove an optimised geometry is a minimum (no imaginary modes).

Contract: calc(..., freq=True)  (CLI --freq). After the SCF (and --opt, if given) it computes the Hessian
and writes to method.txt:
  "frequencies (cm-1): <f1>, <f2>, ..."   vibrations only (3N-6, translations/rotations removed),
                                          ascending, imaginary modes as negative numbers
  "imaginary frequencies: <N>"
Pass if: water --opt --freq gives 3 modes, each within 5 cm-1 of 1710.7 / 3720.5 / 3844.3 (B3LYP/6-31G(d),
PySCF 2.15, day session 2026-11-11), 0 imaginary; planar NH3 (.xyz, no opt, a saddle point) gives exactly 1.
"""
import re, tempfile
from pathlib import Path
from _util import Checks, calc, need

need("freq")
REF = [1710.7, 3720.5, 3844.3]


def parse(log):
    f = [float(x) for x in re.search(r"frequencies \(cm-1\): (.+)", log).group(1).split(",")]
    return f, int(re.search(r"imaginary frequencies: (\d+)", log).group(1))


ok = Checks()
f, n = parse(calc("O", "water", opt=True, freq=True)[0])
ok("water: 3 modes within 5 cm-1", len(f) == 3 and all(abs(a - b) <= 5 for a, b in zip(sorted(f), REF)), f"{f} vs {REF}")
ok("water: 0 imaginary", n == 0 and min(f) > 0, f"{n}")
with tempfile.TemporaryDirectory() as d:
    xyz = Path(d) / "nh3_planar.xyz"
    xyz.write_text("4\nplanar NH3\nN 0 0 0\nH 1.0 0 0\nH -0.5 0.866 0\nH -0.5 -0.866 0\n")
    f, n = parse(calc(xyz, "nh3", freq=True)[0])
ok("planar NH3: exactly 1 imaginary", n == 1 and sum(x < 0 for x in f) == 1, f"{n}; {f}")
ok.finish()
