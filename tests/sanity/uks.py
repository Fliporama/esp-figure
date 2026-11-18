"""Open-shell UKS: radicals run when the spin is given, and are still refused when it isn't.

Contract: calc(..., spin=n)  (CLI --spin n; n = N_alpha - N_beta, PySCF convention) uses UKS when n > 0,
with the same functional/basis/density fitting; the ESP uses the total (alpha + beta) density. method.txt
gets "<S^2>: <value>" (mf.spin_square()). spin=0 stays RKS and unchanged.
Pass if: planar CH3 (.xyz, spin=1) runs; SCF energy within 1e-6 Eh of a direct PySCF UKS on the run's
mol.xyz; <S^2> 0.75-0.77 (day session: 0.754); surf.vtk has ESP from the total density
(min < 0 < max, both within 0.05 a.u.); [CH3] without spin is still refused
with "radical" (guard intact).
"""
import re, subprocess, sys, tempfile
from pathlib import Path
import pyvista as pv
from _util import ROOT, Checks, esp_figure, need
from pyscf import gto, dft

need("spin")
ok = Checks()
with tempfile.TemporaryDirectory() as root:
    xyz = Path(root) / "ch3.xyz"
    xyz.write_text("4\nmethyl\nC 0 0 0\nH 1.08 0 0\nH -0.54 0.935 0\nH -0.54 -0.935 0\n")
    out = esp_figure.calc(str(xyz), "ch3", root=root, spin=1)
    log = (out / "method.txt").read_text(encoding="utf-8")
    e = float(re.search(r"SCF energy: (\S+)", log).group(1))
    s2 = float(re.search(r"<S\^2>: (\S+)", log).group(1))
    sym, x = esp_figure.read_xyz(out / "mol.xyz")
    mf = dft.UKS(gto.M(atom=list(zip(sym, map(tuple, x))), basis="6-31g*", spin=1, verbose=0)).density_fit()
    mf.xc = "b3lyp"
    ref = mf.kernel()
    ok("CH3 energy matches direct UKS", abs(e - ref) <= 1e-6, f"{e:.8f} vs {ref:.8f}")
    ok("<S^2> 0.75-0.77", 0.75 <= s2 <= 0.77, f"{s2}")
    surf = pv.read(out / "surf.vtk")
    ok("ESP surface written", "esp" in surf.point_data and surf.n_points > 1000, f"{surf.n_points} points")
    V = surf.point_data["esp"]   # total density: -0.0155..+0.0194 (day session); alpha-only would be strongly positive
    ok("ESP from the total density (min < 0 < max, both within 0.05 a.u.)", -0.05 < V.min() < 0 < V.max() < 0.05,
       f"{V.min():.4f} to {V.max():.4f}")
r = subprocess.run([sys.executable, "-c", f"from esp_figure import calc; calc('[CH3]', 'g', root={root!r})"],
                   cwd=ROOT, capture_output=True, text=True, timeout=120)
ok("[CH3] without spin still refused", r.returncode != 0 and "radical" in (r.stdout + r.stderr).lower()
   and "Traceback" not in r.stderr, (r.stdout + r.stderr).strip()[-150:])
ok.finish()
