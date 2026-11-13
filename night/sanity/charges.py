"""MK and CHelpG charges: atomic point charges fitted to the ESP.

Contract: calc(..., charges="mk" or "chelpg")  (CLI --charges mk / --charges chelpg) fits one point charge per atom
to the ESP of the run's density (nuclei + electrons, same as the surface ESP) by linear least squares, with the sum
of the charges constrained to the molecular charge (Lagrange multiplier; no restraints, so not RESP).
  mk:     points on 4 shells at 1.4, 1.6, 1.8, 2.0 x the Merz-Singh-Kollman radii (H 1.20, C 1.50, N 1.50, O 1.40,
          F 1.35, P 1.80, S 1.75, Cl 1.70 Å; others: name them in method.txt), 4-6 points per Å², points inside
          any atom's shell of the same scale dropped.
  chelpg: points on a 0.3 Å cubic grid, kept if outside every atom's Breneman radius (H 1.45, C 1.50, N 1.70,
          O 1.70 Å; others 2.0) and within 2.8 Å of at least one atom's radius sphere.
Writes runs/<name>/charges.txt: one line per atom "<i> <element> <q>" (0-based, mol.xyz order, charge in e;
lines starting with "#" are comments) and method.txt lines
  "atomic charges: MK ..." or "atomic charges: CHelpG ..."   (scheme, radii, number of fit points)
  "ESP fit RRMS: <x>"   (sqrt(sum (V_fit - V)^2 / sum V^2) over the fit points)
Pass if (water as an exactly C2v .xyz, formamide from SMILES):
  MK:  sum q = total charge (1e-4: charges.txt is read back, printed values round); water q(O) -0.95..-0.70
       (literature MK at B3LYP/6-31G(d) about -0.80; the day-session reference gave -0.753 on this geometry),
       q(H1) = q(H2) within 0.01 (the shells are not exactly symmetric); formamide q(O) < 0, q(N) < 0,
       carbonyl q(C) > 0; RRMS < 0.15; formamide charges reproduce the surface ESP (surf.vtk, an independent set
       of points) with an RMS below 0.8 x that of Mulliken charges from a direct PySCF run (reference: 0.0042
       vs 0.0065 a.u.; on water the two are nearly equal, so water is not used for this).
  CHelpG (water): sum q = 0 (1e-4), q(H1) = q(H2) within 0.01, RRMS < 0.15, |q(O) CHelpG - q(O) MK| < 0.1.
"""
import re, tempfile
from pathlib import Path
import numpy as np
import pyvista as pv
from _util import Checks, esp_figure, need
from pyscf import gto, dft

need("charges")
ok = Checks()
B2A = 0.529177
WATER = "3\nwater C2v\nO 0 0 0.117300\nH 0 0.757200 -0.469200\nH 0 -0.757200 -0.469200\n"


def run(spec, name, scheme, root):
    out = esp_figure.calc(spec, name, root=root, charges=scheme)
    log = (out / "method.txt").read_text(encoding="utf-8")
    rows = [l.split() for l in (out / "charges.txt").read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("#")]
    sym, xyz = esp_figure.read_xyz(out / "mol.xyz")
    q = np.array([float(r[2]) for r in rows])
    ok(f"{name}: one charge per atom, mol.xyz order", [r[1] for r in rows] == sym and len(q) == len(sym),
       f"{[r[1] for r in rows]} vs {sym}")
    tag = {"mk": "MK", "chelpg": "CHelpG"}[scheme]
    ok(f"{name}: method.txt names the scheme", f"atomic charges: {tag}" in log)
    rr = float(re.search(r"ESP fit RRMS: (\S+)", log).group(1))
    ok(f"{name}: ESP fit RRMS < 0.15", rr < 0.15, f"{rr:.4f}")
    ok(f"{name}: sum q = total charge (1e-4)", abs(q.sum()) <= 1e-4, f"{q.sum():.2e}")
    return out, sym, xyz, q


def surface_rms(out, sym, xyz, q):
    """RMS (a.u.) of the point-charge ESP against the computed ESP on the 0.001 a.u. surface."""
    s = pv.read(out / "surf.vtk")
    d = np.linalg.norm(s.points[:, None] - xyz[None], axis=2) / B2A
    return float(np.sqrt(np.mean(((q / d).sum(1) - s.point_data["esp"]) ** 2)))


with tempfile.TemporaryDirectory() as root:
    w = Path(root) / "water.xyz"
    w.write_text(WATER)
    out, sym, xyz, q = run(str(w), "water_mk", "mk", root)
    ok("water MK: q(O) -0.95..-0.70", -0.95 <= q[0] <= -0.70, f"{q[0]:.4f}")
    ok("water MK: q(H1) = q(H2) within 0.01", abs(q[1] - q[2]) <= 0.01, f"{q[1]:.4f} / {q[2]:.4f}")
    qmk = q[0]

    out, sym, xyz, q = run("NC=O", "formamide_mk", "mk", root)
    mf = dft.RKS(gto.M(atom=list(zip(sym, map(tuple, xyz))), basis="6-31g*", verbose=0)).density_fit()
    mf.xc = "b3lyp"
    mf.kernel()
    a, b = surface_rms(out, sym, xyz, q), surface_rms(out, sym, xyz, mf.mulliken_pop(verbose=0)[1])
    ok("formamide MK: surface ESP RMS < 0.8 x Mulliken's", a < 0.8 * b, f"MK {a:.4f} vs Mulliken {b:.4f} a.u.")
    c = {s: q[[i for i, t in enumerate(sym) if t == s]] for s in ("O", "N", "C")}
    ok("formamide MK: q(O) < 0, q(N) < 0, q(C) > 0", c["O"][0] < 0 and c["N"][0] < 0 and c["C"][0] > 0,
       f"O {c['O'][0]:.3f}, N {c['N'][0]:.3f}, C {c['C'][0]:.3f}")

    _, sym, xyz, q = run(str(w), "water_chelpg", "chelpg", root)
    ok("water CHelpG: q(H1) = q(H2) within 0.01", abs(q[1] - q[2]) <= 0.01, f"{q[1]:.4f} / {q[2]:.4f}")
    ok("water CHelpG: q(O) within 0.1 e of MK", abs(q[0] - qmk) < 0.1, f"{q[0]:.4f} vs MK {qmk:.4f}")
ok.finish()
