"""--igm (IGMH via Multiwfn): water dimer with automatic fragments reproduces the day-session integral and puts the
delta-g_inter maximum on the H...O contact (attractive sign(lambda2) rho); the same fragments given as "1-3;4-6" give the
same run (cached), swapped "4-6;1-3" recomputes to the same integral; the cubes have the claimed grid (0.2 bohr, atoms +
3 bohr); igm.png renders; a single water without fragments and bad fragment strings exit with a message before any
SCF; fragments bonded to each other get a WARNING in method.txt."""
import re, tempfile
from pathlib import Path
import numpy as np
from esp_figure import calc, render, read_cube, read_xyz

DIMER = """6
water dimer, linear O-H...O, H...O 1.95 A
O 0.000000 0.000000 0.000000
H 0.957200 0.000000 0.000000
H -0.239650 0.926700 0.000000
O 2.907200 0.000000 0.000000
H 3.493000 0.000000 0.757200
H 3.493000 0.000000 -0.757200
"""


def integral(out):
    return float(re.search(r"Integral of delta-g_inter: (\S+) a.u.", (out / "method.txt").read_text(encoding="utf-8")).group(1))


def must_exit(*a, **kw):
    try:
        calc(*a, **kw)
    except SystemExit as e:
        assert isinstance(e.code, str), e.code
        return e.code
    raise AssertionError("no exit")


with tempfile.TemporaryDirectory() as root:
    d = Path(root) / "dimer.xyz"
    d.write_text(DIMER)
    out = calc(str(d), "auto", root=root, igm=True)
    I = integral(out)
    assert abs(I / 0.0856 - 1) < 0.02, I
    assert "fragments [[1, 2, 3], [4, 5, 6]] (1-based, mol.xyz order; covalently bonded molecules)" in (out / "method.txt").read_text(encoding="utf-8")
    g, l = read_cube(out / "dg_inter.cube"), read_cube(out / "igm_sl2rho.cube")
    k = int(np.argmax(g["rho"]))
    p = g.points[k]
    assert 0.96 < p[0] < 2.9 and np.hypot(p[1], p[2]) < 0.4 and l["rho"][k] < -0.015, (p, l["rho"][k])   # on H2...O4
    assert not list(out.glob("*.cub"))
    sp = np.array(g.spacing) / 0.529177
    lo, hi = np.array(g.bounds[::2]), np.array(g.bounds[1::2])
    xyz = read_xyz(out / "mol.xyz")[1]
    reach = min((xyz - lo).min(), (hi - xyz).min()) / 0.529177
    assert np.allclose(sp, 0.2, atol=1e-4) and 2.5 <= reach <= 3.0 + 1e-6, (sp, reach)   # IGM line: +3 bohr, Multiwfn rounds
    render("auto", style="rwb", root=root)
    assert (out / "igm.png").exists() and "igm.png: IGMH" in (out / "caption.txt").read_text(encoding="utf-8")

    t = (out / "method.txt").stat().st_mtime
    calc(str(d), "auto", root=root, igm=True, igm_frags="1-3;4-6")   # same fragments: cached, not rewritten
    assert (out / "method.txt").stat().st_mtime == t
    out = calc(str(d), "auto", root=root, igm=True, igm_frags="4-6;1-3")   # other fragments -> recompute, same physics
    assert "fragments [[4, 5, 6], [1, 2, 3]] (1-based, mol.xyz order; given)" in (out / "method.txt").read_text(encoding="utf-8")
    assert abs(integral(out) - I) < 1e-6, (integral(out), I)

    w = Path(root) / "water.xyz"
    w.write_text("3\nwater\nO 0 0 0.117300\nH 0 0.757200 -0.469200\nH 0 -0.757200 -0.469200\n")
    print(must_exit(str(w), "w", root=root, igm=True))
    for bad, msg in (("1-3;3-6", "disjoint"), ("1-3;6-4", "non-empty"), ("1-3;", "cannot read"), ("a-b;4-6", "cannot read"),
                     ("1-3;4-7", "atoms 1..6")):
        assert msg in must_exit(str(d), "bad", root=root, igm=True, igm_frags=bad), bad
    assert "needs --igm" in must_exit(str(d), "bad", root=root, igm_frags="1-3;4-6")
    out = calc(str(d), "bonded", root=root, igm=True, igm_frags="1-2;3-6")   # O1-H3 crosses the fragments
    assert "WARNING: fragments covalently bonded to each other (O1-H3)" in (out / "method.txt").read_text(encoding="utf-8")
    assert not (Path(root) / "w").exists() or not (Path(root) / "w" / "method.txt").exists()
print("ok", I)
