"""def2 + ECP for heavy elements, mixed basis.

Contract: esp_figure.HEAVY_BASIS = "def2-SVP". For .xyz input, atoms with Z > 36 (that PySCF's def2-SVP covers) get
def2-SVP plus the def2 ECP; all other atoms keep 6-31G(d) (basis {el: "def2-svp", default "6-31g*"},
ecp {el: "def2-svp"}); the default density fitting is unchanged. The level string, method.txt and caption name
both, e.g. "B3LYP/6-31G(d) + def2-SVP/ECP (I)". Runs without heavy atoms are unchanged (no "def2" anywhere).
The nuclear part of the ESP uses the effective (ECP) nuclear charges. SMILES input with such elements is still
refused before any compute (MMFF path), with a clear message.
Pass if:
  - CH3I (.xyz): SCF energy within 1e-6 Eh of a direct PySCF run with that basis/ECP on the run's mol.xyz;
    method.txt names "def2-SVP", "ECP" and "6-31G(d)"; surface ESP within +-0.1 a.u. (full Z = 53 on iodine
    would give a large positive ESP).
  - CH3I sigma-hole: the most positive surface ESP within 15 deg of the C->I axis beyond I is > +0.01 a.u.
    (reference +0.026), and the surface ESP minimum is nearest I and < -0.01 (negative belt; reference -0.020).
    With the full Z = 53 on iodine both would be strongly positive.
  - HBr (.xyz, Z = 35): no "def2" in method.txt (6-31G(d) unchanged).
  - CH3I renders (rwb_esp.png).
  - SMILES CI is refused (exit, no traceback, message names I).
"""
import re, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
import pyvista as pv
from _util import ROOT, Checks, esp_figure, skip
from pyscf import gto, dft

if not hasattr(esp_figure, "HEAVY_BASIS"):
    skip("esp_figure has no HEAVY_BASIS yet")
ok = Checks()
CH3I = "5\nmethyl iodide\nC 0 0 0\nI 0 0 2.140\nH 1.028 0 -0.363\nH -0.514 0.890 -0.363\nH -0.514 -0.890 -0.363\n"
HBR = "2\nhydrogen bromide\nH 0 0 0\nBr 0 0 1.414\n"


def run(text, name, root):
    f = Path(root) / f"{name}.xyz"
    f.write_text(text)
    out = esp_figure.calc(str(f), name, root=root)
    return out, (out / "method.txt").read_text(encoding="utf-8"), pv.read(out / "surf.vtk")


with tempfile.TemporaryDirectory() as root:
    out, log, surf = run(CH3I, "ch3i", root)
    e = float(re.search(r"SCF energy: (\S+)", log).group(1))
    sym, xyz = esp_figure.read_xyz(out / "mol.xyz")
    mol = gto.M(atom=list(zip(sym, map(tuple, xyz))), basis={"I": "def2-svp", "default": "6-31g*"},
                ecp={"I": "def2-svp"}, verbose=0)
    mf = dft.RKS(mol).density_fit()
    mf.xc = "b3lyp"
    ref = mf.kernel()
    ok("CH3I energy matches direct PySCF (mixed basis + ECP)", abs(e - ref) <= 1e-6, f"{e:.8f} vs {ref:.8f}")
    lvl = re.search(r"level of theory: (.*)", log).group(1)
    ok("method.txt names def2-SVP, ECP and 6-31G(d)", all(k in lvl for k in ("def2-SVP", "ECP", "6-31G(d)")), lvl[:80])
    V = surf.point_data["esp"]
    ok("CH3I surface ESP within +-0.1 a.u. (effective nuclear charge)", abs(V).max() <= 0.1, f"{V.min():.4f} to {V.max():.4f}")
    c, i = xyz[sym.index("C")], xyz[sym.index("I")]
    v = surf.points - i
    cos = v @ (i - c) / np.linalg.norm(i - c) / np.linalg.norm(v, axis=1)
    hole = V[cos > np.cos(np.radians(15))].max()
    at = sym[np.linalg.norm(xyz - surf.points[V.argmin()], axis=1).argmin()]
    ok("CH3I sigma-hole > +0.01 a.u. on the C->I axis", hole > 0.01, f"{hole:+.4f}")
    ok("CH3I ESP minimum nearest I and < -0.01 (negative belt)", at == "I" and V.min() < -0.01, f"{V.min():+.4f} at {at}")
    esp_figure.render("ch3i", style="rwb", root=root)
    ok("CH3I renders", (out / "rwb_esp.png").exists())

    out, log, surf = run(HBR, "hbr", root)
    ok("HBr unchanged (no def2)", "def2" not in log, re.search(r"level of theory: (.*)", log).group(1)[:60])

    r = subprocess.run([sys.executable, "-c", f"from esp_figure import calc; calc('CI', 'x', root={root!r})"],
                       cwd=ROOT, capture_output=True, text=True, timeout=120)
    msg = (r.stdout + r.stderr).strip()
    ok("SMILES CI refused with a clear message", r.returncode != 0 and "Traceback" not in r.stderr and "I" in msg, msg[-150:])
ok.finish()
