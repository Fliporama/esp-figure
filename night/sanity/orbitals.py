"""HOMO/LUMO: energies, cube files and pictures.

Contract: calc(..., orbitals=True)  (CLI --orbitals) writes runs/<name>/homo.cube and lumo.cube
(orbital values, pyscf.tools.cubegen.orbital, same grid settings as the density) and method.txt lines
  "HOMO: <e> eV"   "LUMO: <e> eV"
render(name) then also writes homo.png and lumo.png when the cubes exist.
Pass on water if: HOMO < LUMO; both within 0.01 eV of a direct PySCF B3LYP/6-31G(d) (density fitting)
calculation on the run's mol.xyz; >= 70 % of the HOMO's |psi|^2 (cube points) lies nearer O than H
(it is the O lone pair; 85 % in the day-session check); homo.png and lumo.png exist.
"""
import re, tempfile
import numpy as np
from _util import Checks, esp_figure, need
from pyscf import gto, dft

need("orbitals")
ok = Checks()
with tempfile.TemporaryDirectory() as root:
    out = esp_figure.calc("O", "water", root=root, orbitals=True)
    log = (out / "method.txt").read_text(encoding="utf-8")
    homo, lumo = (float(re.search(rf"{k}: (\S+) eV", log).group(1)) for k in ("HOMO", "LUMO"))
    sym, xyz = esp_figure.read_xyz(out / "mol.xyz")
    mf = dft.RKS(gto.M(atom=list(zip(sym, map(tuple, xyz))), basis="6-31g*", verbose=0)).density_fit()
    mf.xc = "b3lyp"
    mf.kernel()
    e = mf.mo_energy * 27.211386
    ref = e[mf.mol.nelectron // 2 - 1], e[mf.mol.nelectron // 2]
    ok("HOMO < LUMO", homo < lumo, f"{homo:.3f} / {lumo:.3f} eV")
    ok("energies match direct PySCF", abs(homo - ref[0]) <= 0.01 and abs(lumo - ref[1]) <= 0.01,
       f"{homo:.3f}/{lumo:.3f} vs {ref[0]:.3f}/{ref[1]:.3f} eV")
    g = esp_figure.read_cube(out / "homo.cube")
    w = g.point_data["rho"] ** 2
    near = np.linalg.norm(g.points[:, None] - xyz[None], axis=2).argmin(1)
    frac = w[np.array(sym)[near] == "O"].sum() / w.sum()
    ok("HOMO is the O lone pair (>= 70 % nearer O)", frac >= 0.7, f"{frac:.0%}")
    esp_figure.render("water", style="rwb", root=root)
    ok("homo.png and lumo.png rendered", (out / "homo.png").exists() and (out / "lumo.png").exists())
ok.finish()
