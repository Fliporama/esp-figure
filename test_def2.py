"""def2 + ECP mixed basis: CH3I gets def2-SVP + ECP on I and 6-31G(d) elsewhere (energy = direct PySCF), the ESP uses
I's effective nuclear charge (sigma hole + negative belt, not a huge positive ESP); HBr (Z = 35) is unchanged;
SMILES with I and elements without a def2-SVP ECP are refused."""
import re, tempfile
from pathlib import Path
import numpy as np
import pyvista as pv
from pyscf import gto, dft
from esp_figure import calc, read_xyz


def refused(word, *a, **kw):
    try:
        calc(*a, **kw)
    except SystemExit as e:
        assert word in str(e), e
        return
    raise AssertionError(f"not refused: {a} {kw}")


with tempfile.TemporaryDirectory() as root:
    f = Path(root) / "ch3i.xyz"
    f.write_text("5\nmethyl iodide\nC 0 0 0\nI 0 0 2.140\nH 1.028 0 -0.363\nH -0.514 0.890 -0.363\nH -0.514 -0.890 -0.363\n")
    out = calc(str(f), "ch3i", root=root)
    log = (out / "method.txt").read_text(encoding="utf-8")
    e = float(re.search(r"SCF energy: (\S+)", log).group(1))
    lo, hi = map(float, re.search(r"ESP range on surface: (\S+) to (\S+)", log).groups())
    sym, x = read_xyz(Path(root) / "ch3i" / "mol.xyz")
    mf = dft.RKS(gto.M(atom=list(zip(sym, map(tuple, x))), basis={"I": "def2-svp", "default": "6-31g*"},
                       ecp={"I": "def2-svp"}, verbose=0)).density_fit()
    mf.xc = "b3lyp"
    assert abs(e - mf.kernel()) < 1e-6, (e, mf.e_tot)
    assert "B3LYP/6-31G(d) + def2-SVP/ECP (I)" in log and "effective charges (I 25" in log, log
    assert -0.1 < lo < -0.01 and 0.01 < hi < 0.1, (lo, hi)          # full Z = 53 would make it strongly positive
    s = pv.read(out / "surf.vtk")
    V, c, i = s.point_data["esp"], x[sym.index("C")], x[sym.index("I")]
    v = s.points - i
    on_axis = v @ (i - c) / np.linalg.norm(i - c) / np.linalg.norm(v, axis=1) > np.cos(np.radians(15))
    assert V[on_axis].max() > 0.01, V[on_axis].max()                                     # sigma hole beyond I
    assert sym[np.linalg.norm(x - s.points[V.argmin()], axis=1).argmin()] == "I"         # negative belt around I
    refused("not supported yet", str(Path(root) / "ch3i.xyz"), "ch3i_n", root=root, nci=True)

    f = Path(root) / "hbr.xyz"
    f.write_text("2\nhydrogen bromide\nH 0 0 0\nBr 0 0 1.414\n")
    assert "def2" not in (calc(str(f), "hbr", root=root) / "method.txt").read_text(encoding="utf-8")

    refused("need .xyz input", "CI", "x", root=root)
    f = Path(root) / "fr.xyz"   # def2 stops at Rn (Z = 86)
    f.write_text("1\nfrancium\nFr 0 0 0\n")
    refused("unsupported element Fr", str(f), "fr", root=root, spin=1)
print(f"ok (CH3I E {e:.8f}, ESP {lo} to {hi})")
