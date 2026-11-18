"""Red = negative, blue = positive in every style (CLAUDE.md rule), checked on rendered pixels, not only on the
colour map: a synthetic surface at V = -limit everywhere must come out red, at +limit blue. Catches an inverted
colour map and an inverted colour range (clim). No QM, seconds."""
import tempfile
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pyvista as pv
from esp_figure import colormap, render, LIMITS

for st in ("rainbow", "rwb"):   # the maps themselves
    lo, hi = colormap(st)(0.0), colormap(st)(1.0)
    assert lo[0] > 0.8 and lo[2] < 0.3 and hi[2] > 0.8 and hi[0] < 0.3, (st, lo, hi)

with tempfile.TemporaryDirectory() as root:
    out = Path(root) / "flat"
    out.mkdir()
    (out / "mol.xyz").write_text("3\nwater\nO 0.000 0.000 0.117\nH 0.000 0.757 -0.469\nH 0.000 -0.757 -0.469\n")
    (out / "method.txt").write_text("synthetic\n")
    for sign in (-1, 1):
        s = pv.Sphere(radius=2.0, theta_resolution=60, phi_resolution=60)
        for st in ("rainbow", "rwb"):
            s["esp"] = np.full(s.n_points, sign * LIMITS[st])
            s.save(out / "surf.vtk")
            render("flat", style=st, root=root)
            img = plt.imread(out / f"{st}_esp.png")[:, :1350, :3]   # RGB 0..1, left of the colour bar
            px = img[img.min(axis=2) < 0.95]                         # pixels that are not white background
            r, b = px[:, 0].mean(), px[:, 2].mean()
            want = "red" if sign < 0 else "blue"
            assert (r - b > 0.2) if sign < 0 else (b - r > 0.2), (st, sign, r, b)
            print(f"{st}: V = {sign * LIMITS[st]:+.2f} renders {want} (R {r:.2f}, B {b:.2f})")
print("test_colormaps OK")
