"""--nci: |sign(lambda2) rho| equals dens.cube point by point (same grid, same density); the linear water dimer has an
attractive (blue) s < 0.5 lobe between H and O; isolated water has none off the atoms; render writes nci.png."""
import tempfile
from pathlib import Path
import numpy as np
from esp_figure import calc, read_cube, read_xyz, render

DIMER = ("6\nwater dimer\nO 0 0 0\nH 0.9572 0 0\nH -0.23965 0.9267 0\nO 2.9072 0 0\nH 3.493 0 0.7572\n"
         "H 3.493 0 -0.7572\n")
with tempfile.TemporaryDirectory() as root:
    for name, text in (("dimer", DIMER), ("water", "3\nwater\nO 0 0 0.1173\nH 0 0.7572 -0.4692\nH 0 -0.7572 -0.4692\n")):
        f = Path(root) / f"{name}.xyz"
        f.write_text(text)
        out = calc(str(f), name, root=root, nci=True)
        assert "\nNCI: " in (out / "method.txt").read_text(encoding="utf-8")
        s, l, rho = (read_cube(out / f"{k}.cube") for k in ("rdg", "sl2rho", "dens"))
        assert np.allclose(s.points, rho.points) and np.allclose(abs(l["rho"]), rho["rho"], rtol=1e-4, atol=1e-12)
        _, xyz = read_xyz(out / "mol.xyz")
        p, s, l = s.points, s["rho"], l["rho"]
        nci = (s < 0.5) & (abs(l) < 0.05) & (np.linalg.norm(p[:, None] - xyz[None], axis=2).min(1) > 1.0)
        if name == "dimer":   # contact region: between H1 and O3, away from both nuclei
            mid = (np.linalg.norm(p - xyz[1], axis=1) > 0.5) & (np.linalg.norm(p - xyz[3], axis=1) > 0.5) & \
                  (abs(p[:, 1]) < 0.4) & (abs(p[:, 2]) < 0.4) & (p[:, 0] > xyz[1, 0]) & (p[:, 0] < xyz[3, 0])
            m = l[(s < 0.5) & (abs(l) < 0.05) & mid].min()
            assert m < -0.015, m
            render(name, style="rwb", root=root)
            cap = (out / "caption.txt").read_text(encoding="utf-8")
            assert (out / "nci.png").exists() and "nci.png:" in cap and "no NCI surface" not in cap, cap
        else:
            assert not nci.any(), nci.sum()
print(f"ok (dimer H...O lobe min sign(lambda2) rho {m:.4f} a.u.)")
