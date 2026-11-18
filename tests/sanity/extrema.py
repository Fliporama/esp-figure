"""ESP surface extrema (V_s,min / V_s,max): right values, right atoms, marked on the map.

Interface (built 2026-11-11, d4afae9): esp_extrema(surf, sym, xyz) -> [{"kind": "min"|"max", "value",
"point" (Å), "atom"}], computed at render time from surf.vtk; render(name, extrema=True) marks them and writes
"... (V_s,min, marked): <v> a.u. ..." / "(V_s,max, ...)" lines to caption.txt.
Pass on formamide if: values equal the "ESP range on surface" in method.txt within 1e-4 a.u.; the min
point is nearest the carbonyl O, the max point nearest an H bonded to N (day session: -0.0678 on O, +0.0756
on N-H); render(extrema=True) runs and the caption names both.
"""
import re, tempfile
import numpy as np
import pyvista as pv
from _util import Checks, esp_figure, skip

if not hasattr(esp_figure, "esp_extrema"):
    skip("esp_figure.esp_extrema not defined yet")
ok = Checks()
with tempfile.TemporaryDirectory() as root:
    out = esp_figure.calc("NC=O", "formamide", root=root)
    log = (out / "method.txt").read_text(encoding="utf-8")
    sym, xyz = esp_figure.read_xyz(out / "mol.xyz")
    lo, hi = map(float, re.search(r"ESP range on surface: (\S+) to (\S+)", log).groups())
    ex = {e["kind"]: e for e in esp_figure.esp_extrema(pv.read(out / "surf.vtk"), sym, xyz)}
    near = {k: int(np.linalg.norm(xyz - np.asarray(e["point"]), axis=1).argmin()) for k, e in ex.items()}
    ok("V_s,min / V_s,max equal the ESP range", abs(ex["min"]["value"] - lo) <= 1e-4 and abs(ex["max"]["value"] - hi) <= 1e-4,
       f"{ex['min']['value']:.4f}/{ex['max']['value']:.4f} vs {lo}/{hi}")
    n_h = [i for i, s in enumerate(sym) if s == "H" and
           any(sym[j] == "N" and np.linalg.norm(xyz[i] - xyz[j]) < 1.2 for j in range(len(sym)))]
    ok("min nearest the carbonyl O", sym[near["min"]] == "O", f"atom {near['min']} {sym[near['min']]}")
    ok("max nearest an N-H hydrogen", near["max"] in n_h, f"atom {near['max']}, N-H atoms {n_h}")
    esp_figure.render("formamide", style="rwb", root=root, extrema=True)
    cap = (out / "caption.txt").read_text(encoding="utf-8")
    ok("marked map rendered, caption names V_s,min and V_s,max",
       (out / "rwb_esp.png").exists() and "V_s,min" in cap and "V_s,max" in cap)
ok.finish()
