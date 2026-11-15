"""IR spectrum: harmonic intensities from finite-difference dipole derivatives on top of the --freq modes.

Contract: calc(..., freq=True, ir=True)  (CLI --ir, needs --freq). After the frequencies it computes d(mu)/dx by
central differences of the SCF dipole (same level of theory as the run) and projects it onto the normal modes:
I_i = 974.88 * |d(mu)/dQ_i|^2 km/mol (mu in e*bohr, Q in bohr*sqrt(amu)). It writes to method.txt:
  "IR intensities (km/mol): <I1>, <I2>, ..."   one per vibration, same order as "frequencies (cm-1)" (ascending)
  "IR: harmonic, ...; scale factor 0.960 ...; Lorentzian FWHM 10 cm-1"   one line naming all three
and runs/<name>/ir_spectrum.csv: header line, then "<wavenumber_scaled_cm-1>,<intensity>" rows on a grid of
<= 1 cm-1 spacing covering 400-4000 cm-1; each band is a Lorentzian of FWHM 10 cm-1 centred at 0.960 x the raw
frequency (raw frequencies stay unscaled in method.txt). render draws ir.png from the csv.
Pass if (B3LYP/6-31G(d), gas, --opt --freq --ir; reference numbers from a throwaway implementation, 2026-11-15):
  water: 3 intensities >= 0, order bend > asym stretch > sym stretch, each within 15 % (or 1 km/mol) of REF_WATER;
  formamide: the strongest band has a raw frequency in 1700-1900 cm-1 (C=O stretch);
  methane: of 9 modes exactly 3 below 0.1 km/mol (A1 + E are IR-inactive in Td), the 6 T2 modes above 1 km/mol;
  water ir_spectrum.csv: bend peak within 2 cm-1 of 0.960 x raw bend; intensity at peak + 15 cm-1 (3 half-widths)
  is 0.07-0.13 of the peak (Lorentzian 0.10; a Gaussian of the same FWHM gives 0.002);
  method.txt IR line contains "harmonic", "0.960" and "FWHM 10".
"""
import re, tempfile
import numpy as np
from _util import Checks, need
import esp_figure  # after _util, which puts the repo root on sys.path

need("ir")
REF_WATER = [79.6, 1.8, 20.1]   # bend, sym, asym (km/mol), throwaway reference 2026-11-15 (exp. gas ~54 / 2 / 45)


def run(spec, name):
    with tempfile.TemporaryDirectory() as tmp:
        out = esp_figure.calc(spec, name, root=tmp, opt=True, freq=True, ir=True)
        log = (out / "method.txt").read_text(encoding="utf-8")
        spec_xy = np.loadtxt(out / "ir_spectrum.csv", delimiter=",", skiprows=1)
    f = [float(x) for x in re.search(r"frequencies \(cm-1\): (.+)", log).group(1).split(",")]
    i = [float(x) for x in re.search(r"IR intensities \(km/mol\): (.+)", log).group(1).split(",")]
    return log, f, i, spec_xy


ok = Checks()
log, f, i, xy = run("O", "water")
ok("water: 3 intensities >= 0", len(i) == 3 and min(i) >= 0, f"{i}")
ok("water: bend > asym > sym", len(i) == 3 and i[0] > i[2] > i[1], f"bend {i[0]}, sym {i[1]}, asym {i[2]}")
ok("water: within 15 % of reference", all(abs(a - b) <= max(0.15 * b, 1.0) for a, b in zip(i, REF_WATER)), f"{i} vs {REF_WATER}")
line = next((l for l in log.splitlines() if l.startswith("IR:")), "")
ok("method.txt IR line", all(k in line for k in ("harmonic", "0.960", "FWHM 10")), line)
x, y = xy[:, 0], xy[:, 1]
ok("spectrum grid", x.min() <= 400 and x.max() >= 4000 and np.diff(x).max() <= 1.0 + 1e-9, f"{x.min()}..{x.max()}")
win = (x > 0.96 * f[0] - 100) & (x < 0.96 * f[0] + 100)
peak = x[win][np.argmax(y[win])]
ok("bend peak at 0.960 x raw", abs(peak - 0.96 * f[0]) <= 2, f"peak {peak:.1f}, 0.960 x {f[0]:.1f} = {0.96 * f[0]:.1f}")
tail = np.interp(peak + 15, x, y) / y[win].max()
ok("Lorentzian FWHM 10 (tail at +15 cm-1)", 0.07 <= tail <= 0.13, f"{tail:.3f} of peak")

_, f, i, _ = run("NC=O", "formamide")
top = f[int(np.argmax(i))]
ok("formamide: strongest band is C=O (raw 1700-1900)", 1700 <= top <= 1900, f"strongest at {top:.1f} cm-1; {i}")

_, f, i, _ = run("C", "methane")
ok("methane: 3 inactive (< 0.1), 6 active (> 1)", len(i) == 9 and sum(v < 0.1 for v in i) == 3 and sum(v > 1 for v in i) == 6, f"{i}")
ok.finish()
