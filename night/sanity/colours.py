"""Element colours: P, Si, Br, I get real colours; H/C/N/O/S/Cl keep theirs; render() uses the table.

Contract: esp_figure.py has a module-level dict COLORS (element symbol -> "#rrggbb") that render() uses
for atoms and bonds; "#ff69b4" (pink) stays the fallback for elements not in it.
Pass if: P, Si, Br, I are in COLORS and not pink; H/C/N/O/S/Cl unchanged; with COLORS patched to pure
green, a rendered P/Si/Br/I molecule shows green and no pink (so render really reads COLORS).
"""
import tempfile
from pathlib import Path
import numpy as np
from _util import Checks, esp_figure, skip

C = getattr(esp_figure, "COLORS", None) or skip("esp_figure.COLORS not defined yet")
ok = Checks()
old = {"H": "#f2f2f2", "C": "#7f7f7f", "N": "#1f3fff", "O": "#ff1f1f", "S": "#e6c619", "Cl": "#1fd01f"}
new = ("P", "Si", "Br", "I")
ok("P/Si/Br/I coloured, not pink", all(C.get(e, "#ff69b4").lower() != "#ff69b4" for e in new), str({e: C.get(e) for e in new}))
ok("H/C/N/O/S/Cl unchanged", all(C.get(e, "").lower() == v for e, v in old.items()), str({e: C.get(e) for e in old}))

import pyvista as pv
from PIL import Image
esp_figure.COLORS = {e: "#00ff00" for e in new}
with tempfile.TemporaryDirectory() as root:
    out = Path(root) / "els"
    out.mkdir()
    (out / "mol.xyz").write_text("4\nels\nP 0 0 0\nSi 2.2 0 0\nBr 0 2.2 0\nI 2.2 2.2 0.5\n")
    s = pv.Sphere(radius=3, center=(1.1, 1.1, 0))
    s.point_data["esp"] = np.zeros(s.n_points)
    s.save(out / "surf.vtk")
    (out / "method.txt").write_text("input: test\n")
    esp_figure.render("els", style="rwb", root=root)
    px = np.asarray(Image.open(out / "ball.png").convert("RGB")).reshape(-1, 3).astype(int)
r, g, b = px.T
green = ((g > 120) & (g > r + 60) & (g > b + 60)).sum()
pink = ((r > 150) & (b > 90) & (g < r - 60) & (g < b)).sum()
ok("render uses COLORS", green > 1000 and pink == 0, f"{green} green px, {pink} pink px")
ok.finish()
