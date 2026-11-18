"""render --extrema all: every local ESP minimum/maximum on the surface (esp_local_extrema), like Multiwfn.
1. Synthetic: a sphere with V = x^2 - y^2 has exactly 2 maxima (+-x) and 2 minima (+-y); render writes extrema.txt,
   marks the back-side ones as not visible and adds a caption line. No QM, seconds.
2. If the Gaussian reference files are present (ref/esp-20260212/, not in git): acrylic acid on the vendor geometry at
   --ref-level --solvent water gives Multiwfn's 6 maxima and 2 minima (surfanalysise.pdb), each within 0.25 A and
   0.5 kcal/mol. ~5 min."""
import shutil, sys, tempfile
from pathlib import Path
import numpy as np
import pyvista as pv
from esp_figure import calc, esp_local_extrema, read_xyz, render

REF = Path(__file__).parent / "ref" / "esp-20260212"

with tempfile.TemporaryDirectory() as root:
    out = Path(root) / "sph"
    out.mkdir()
    (out / "mol.xyz").write_text("3\nwater\nO 0.000 0.000 0.117\nH 0.000 0.757 -0.469\nH 0.000 -0.757 -0.469\n")
    (out / "method.txt").write_text("synthetic\n")
    s = pv.Sphere(radius=2.0, theta_resolution=120, phi_resolution=120)
    p = s.points / 2.0
    s["esp"] = 0.05 * (p[:, 0] ** 2 - p[:, 1] ** 2)
    s.save(out / "surf.vtk")
    sym, xyz = read_xyz(out / "mol.xyz")
    ex = esp_local_extrema(s, sym, xyz)
    kinds = [e["kind"] for e in ex]
    assert kinds == ["min", "min", "max", "max"], kinds
    for e in ex:
        axis = 1 if e["kind"] == "min" else 0
        assert abs(abs(e["point"][axis]) - 2.0) < 0.05, e
    render("sph", style="rwb", root=root, view=[0, 0, 1], extrema="all")   # looking down z: all 4 on the rim, visible
    rows = [l.split() for l in (out / "extrema.txt").read_text(encoding="utf-8").splitlines() if not l.startswith("#")]
    assert len(rows) == 4 and all(r[-2] == r[-1] == "yes" for r in rows), rows      # columns: ... front drawn
    render("sph", style="rwb", root=root, view=[1, 0, 0], extrema="all")   # looking down x: the -x maximum is behind
    rows = [l.split() for l in (out / "extrema.txt").read_text(encoding="utf-8").splitlines() if not l.startswith("#")]
    assert [r[-2] for r in rows].count("no") == 1 and [r[-1] for r in rows].count("no") == 1, rows
    assert "local ESP extrema: 2 minima" in (out / "caption.txt").read_text(encoding="utf-8")
    s["esp"] = 0.05 * (p[:, 0] ** 2 - p[:, 1] ** 2) + 0.06                   # all positive: minima of unexpected sign
    s.save(out / "surf.vtk")
    render("sph", style="rwb", root=root, view=[0, 0, 1], extrema="all")
    rows = [l.split() for l in (out / "extrema.txt").read_text(encoding="utf-8").splitlines() if not l.startswith("#")]
    assert len(rows) == 4 and [(r[0], r[-2], r[-1]) for r in rows] == [("min", "yes", "no")] * 2 + [("max", "yes", "yes")] * 2, rows
    assert "2 of unexpected sign" in (out / "caption.txt").read_text(encoding="utf-8")
    print("synthetic sphere: 2 min + 2 max, back side detected, positive minima listed but not drawn")

    if not (REF / "surfanalysise.pdb").exists():
        print("reference files absent: Multiwfn comparison skipped")
        print("test_extrema OK")
        sys.exit(0)
    L = (REF / "e-sp.fchk").read_text().splitlines()
    i = next(k for k, l in enumerate(L) if l.startswith("Atomic numbers"))
    Z = " ".join(L[i + 1:i + 3]).split()[:9]
    j = next(k for k, l in enumerate(L) if l.startswith("Current cartesian coordinates"))
    R = np.array(" ".join(L[j + 1:j + 7]).split()[:27], float).reshape(9, 3) * 0.529177210903
    el = {"1": "H", "6": "C", "8": "O"}
    g = Path(root) / "acrylic.xyz"
    g.write_text("9\nvendor geometry\n" + "".join(f"{el[z]} {x:.8f} {y:.8f} {zz:.8f}\n" for z, (x, y, zz) in zip(Z, R)))
    a = calc(str(g), "acrylic", root=root, solvent="water", ref_level=True)
    sym, xyz = read_xyz(a / "mol.xyz")
    ex = esp_local_extrema(pv.read(a / "surf.vtk"), sym, xyz)
    ref = [(np.array(l[30:54].split(), float), float(l[60:66])) for l in (REF / "surfanalysise.pdb").read_text().splitlines()
           if l.startswith("HETATM")]
    assert len(ex) == len(ref) == 8 and sum(e["kind"] == "min" for e in ex) == 2, [(e["kind"], e["value"]) for e in ex]
    for pt, v in ref:   # Multiwfn's extrema, each matched by ours (one-to-one: 8 found, each nearest within 0.25 A)
        e = min(ex, key=lambda e: np.linalg.norm(e["point"] - pt))
        d, dv = np.linalg.norm(e["point"] - pt), e["value"] * 627.5095 - v
        assert d < 0.25 and abs(dv) < 0.5, (pt, v, e, d, dv)
        print(f"Multiwfn {v:+7.2f} kcal/mol: ours {e['value'] * 627.5095:+7.2f}, {d:.2f} A away")
print("test_extrema OK")
