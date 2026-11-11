"""render --extrema / --hbonds: same H-bond definition as method.txt, extrema on the right atoms (seconds)."""
import tempfile
from pathlib import Path
import pyvista as pv
from esp_figure import calc, render, read_xyz, mol_from_xyz, hbond_pairs, hbonds, esp_extrema

# H-bond lines use the same definition as the count in method.txt (PAM3 pilot: 2 after optimisation)
sym, xyz = read_xyz(Path(__file__).parent / "night/baseline/pam3_opt.xyz")
m = mol_from_xyz(sym, xyz)
pairs = hbond_pairs(m, xyz)
assert len(pairs) == 2 == hbonds(m, xyz), pairs
assert all(sym[h] == "H" and sym[a] in ("N", "O") for h, a in pairs)

with tempfile.TemporaryDirectory() as root:
    out = calc("O", "water", root=root)
    sym, xyz = read_xyz(out / "mol.xyz")
    surf = pv.read(out / "surf.vtk")
    ex = {e["kind"]: e for e in esp_extrema(surf, sym, xyz)}
    assert ex["min"]["atom"].startswith("O") and ex["max"]["atom"].startswith("H"), ex
    assert ex["min"]["value"] == surf["esp"].min() and ex["max"]["value"] == surf["esp"].max()
    render("water", style="rwb", root=root, extrema=True, hbond_lines=True)
    cap = (out / "caption.txt").read_text()
    assert "ESP minimum" in cap and "ESP maximum" in cap and "H-bonds drawn: none" in cap, cap
    assert (out / "rwb_esp.png").exists()
print("ok")
