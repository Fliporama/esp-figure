"""--ref-level: one PBE0-D3(BJ)/6-311+G(d,p) (+SMD) single point for surface, ESP and analyses.
1. Water: --opt --freq with and without --ref-level give the same frequencies (freq stays at the geometry level), a
   different ESP, and method.txt names both levels; a cached run with the other setting is refused; Fukui + SMD converge.
2. Refused before any SCF: --spin, and Br (no 6-311+G(d,p) in PySCF).
3. If the Gaussian reference files are present (ref/esp-20260212/, not in git): acrylic acid on their geometry with
   --solvent water reproduces their Multiwfn ESP extrema within 1 % and their SMD energy within 0.5 kcal/mol."""
import re, sys, tempfile
from pathlib import Path
import numpy as np
from esp_figure import calc

WATER = "3\nwater\nO 0.000 0.000 0.117\nH 0.000 0.757 -0.469\nH 0.000 -0.757 -0.469\n"
REF = Path(__file__).parent / "ref" / "esp-20260212"


def field(out, key):
    return re.search(rf"^{key}: (.*)$", (out / "method.txt").read_text(encoding="utf-8"), re.M).group(1)


def must_exit(*a, **kw):
    try:
        calc(*a, **kw)
    except SystemExit as e:
        assert isinstance(e.code, str), e.code
        return e.code
    raise AssertionError("no exit")


with tempfile.TemporaryDirectory() as root:
    w = Path(root) / "w.xyz"
    w.write_text(WATER)
    a = calc(str(w), "base", root=root, opt=True, freq=True)
    b = calc(str(w), "ref", root=root, opt=True, freq=True, ref_level=True, solvent="water", fukui=True)
    fa, fb = (np.array(field(o, r"frequencies \(cm-1\)").split(", "), float) for o in (a, b))
    c = calc(str(w), "pcm", root=root, opt=True, freq=True, solvent="water")
    fc = np.array(field(c, r"frequencies \(cm-1\)").split(", "), float)
    assert np.allclose(fb, fc, atol=0.5), (fb, fc)          # same geometry level (B3LYP + PCM), with or without --ref-level
    assert not np.allclose(fa, fc, atol=0.5)                 # and PCM really changes them, so the check can fail
    assert field(b, "analysis level").startswith("PBE0-D3(BJ)/6-311+G(d,p) + SMD(water)"), field(b, "analysis level")
    assert "PBE0-D3(BJ)/6-311+G(d,p) + SMD(water) level" in field(b, "caption")
    assert field(b, "ESP range on surface") != field(c, "ESP range on surface")
    assert "N+1" in (b / "method.txt").read_text(encoding="utf-8") and (b / "fukui.txt").exists()
    assert "different --ref-level" in must_exit(str(w), "pcm", root=root, opt=True, solvent="water", ref_level=True)
    assert "--spin" in must_exit(str(w), "s", root=root, spin=2, ref_level=True)
    br = Path(root) / "hbr.xyz"
    br.write_text("2\nHBr\nH 0 0 0\nBr 0 0 1.41\n")
    assert "Br" in must_exit(str(br), "br", root=root, ref_level=True)

    if not (REF / "e-sp.fchk").exists():
        print("reference files absent: Gaussian comparison skipped")
        print("test_reflevel OK")
        sys.exit(0)
    L = (REF / "e-sp.fchk").read_text().splitlines()
    i = next(k for k, l in enumerate(L) if l.startswith("Atomic numbers"))
    Z = " ".join(L[i + 1:i + 3]).split()[:9]
    j = next(k for k, l in enumerate(L) if l.startswith("Current cartesian coordinates"))
    R = np.array(" ".join(L[j + 1:j + 7]).split()[:27], float).reshape(9, 3) * 0.529177210903
    el = {"1": "H", "6": "C", "8": "O"}
    g = Path(root) / "acrylic.xyz"
    g.write_text("9\nvendor geometry\n" + "".join(f"{el[z]} {x:.8f} {y:.8f} {zz:.8f}\n" for z, (x, y, zz) in zip(Z, R)))
    out = calc(str(g), "acrylic", root=root, solvent="water", ref_level=True)
    vmin, vmax = (float(v) * 627.5095 for v in field(out, "ESP range on surface").replace(" a.u.", "").split(" to "))
    ext = [float(l[60:66]) for l in (REF / "surfanalysise.pdb").read_text().splitlines() if l.startswith("HETATM")]
    assert abs(vmin / min(ext) - 1) < 0.01 and abs(vmax / max(ext) - 1) < 0.01, (vmin, vmax, min(ext), max(ext))
    eg = float(re.findall(r"SCF Done:\s+E\(\S+\)\s+=\s+(\S+)", (REF / "e-sp.log").read_text())[-1])
    e = float(field(out, "SCF energy").split()[0])
    assert abs(e - eg) * 627.5095 < 0.5, (e, eg)
    print(f"Gaussian: ESP {vmin:.2f}/{vmax:.2f} vs {min(ext)}/{max(ext)} kcal/mol, dE {(e - eg) * 627.5095:+.3f} kcal/mol")
print("test_reflevel OK")
