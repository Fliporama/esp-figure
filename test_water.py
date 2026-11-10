"""Sanity check on water: ESP most negative on the O side, most positive on an H, sensible range."""
import tempfile
import numpy as np, pyvista as pv
from esp_figure import calc, render, read_xyz

with tempfile.TemporaryDirectory() as root:
    out = calc("O", "water", root=root)
    sym, xyz = read_xyz(out / "mol.xyz")
    surf = pv.read(out / "surf.vtk")
    V = surf["esp"]
    nearest = np.linalg.norm(surf.points[:, None] - xyz[None], axis=2).argmin(1)   # nearest atom per vertex
    assert sym[nearest[V.argmin()]] == "O", "ESP minimum should be on the oxygen side"
    assert sym[nearest[V.argmax()]] == "H", "ESP maximum should be on a hydrogen"
    assert -0.12 < V.min() < -0.04 and 0.04 < V.max() < 0.12, f"range {V.min():.3f}..{V.max():.3f}"
    render("water", root=root)
    assert all((out / f).exists() for f in ("ball.png", "rainbow_esp.png", "rwb_esp.png", "caption.txt"))
print("ok")
