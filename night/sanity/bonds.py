"""H-bonds as dashed lines (built 2026-11-11, d4afae9) and double bonds as double sticks (not built yet).

Interface:
  hbond_pairs(mol_from_xyz(sym, xyz), xyz) -> [(h, acceptor)]   exists; render(name, hbond_lines=True) dashes them
  bond_list(sym, xyz) -> [(i, j, order)]                        TO BUILD: covalent bonds with order 1/2/3
                                                                (e.g. RDKit rdDetermineBonds.DetermineBonds);
                                                                render() draws order-2 bonds as two sticks
Pass on the locked PAM3 geometries if: H-bonds folded 2, extended 1 (as in their method.txt); 34 bonds,
exactly 3 of order 2, all C=O; render(hbond_lines=True) runs.
The item counts as done only when all of this passes. Until bond_list exists: exit 77 (not built) if the
H-bond half passes, exit 1 if it fails, so an unbuilt half never reads as a failure.
"""
import tempfile
from pathlib import Path
import numpy as np
from _util import BASE, Checks, esp_figure, skip

if not hasattr(esp_figure, "hbond_pairs") and not hasattr(esp_figure, "bond_list"):
    skip("neither hbond_pairs nor bond_list defined yet")
ok = Checks()
for k, want_hb in (("fold", 2), ("ext", 1)):
    sym, xyz = esp_figure.read_xyz(BASE[k]["xyz"])
    hb = esp_figure.hbond_pairs(esp_figure.mol_from_xyz(sym, xyz), xyz)
    ok(f"{k}: {want_hb} H-bonds", len(hb) == want_hb and all(sym[h] == "H" and sym[a] in ("N", "O") for h, a in hb), f"{hb}")
    if not hasattr(esp_figure, "bond_list"):
        continue
    bl = esp_figure.bond_list(sym, xyz)
    dbl = [(i, j) for i, j, o in bl if o == 2]
    ok(f"{k}: 34 bonds, 3 C=O doubles", len(bl) == 34 and len(dbl) == 3 and all({sym[i], sym[j]} == {"C", "O"} for i, j in dbl),
       f"{len(bl)} bonds, doubles {[(sym[i], sym[j]) for i, j in dbl]}")
with tempfile.TemporaryDirectory() as root:
    out = Path(root) / "fold"
    out.mkdir()
    sym, xyz = esp_figure.read_xyz(BASE["fold"]["xyz"])
    (out / "mol.xyz").write_text(BASE["fold"]["xyz"].read_text())
    import pyvista as pv
    s = pv.Sphere(radius=8, center=xyz.mean(0))
    s.point_data["esp"] = np.zeros(s.n_points)
    s.save(out / "surf.vtk")
    (out / "method.txt").write_text("input: test\n")
    esp_figure.render("fold", style="rwb", root=root, hbond_lines=True)
    ok("render with H-bond lines runs", (out / "ball.png").exists())
if not hasattr(esp_figure, "bond_list") and ok.ok:
    skip("H-bond half passes; bond_list (double sticks) not built yet")
ok.finish()
