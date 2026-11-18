"""IGM (independent gradient model) via Multiwfn: IGMH, Hirshfeld partition of the molecular density.

Contract: calc(..., igm=True, igm_frags=None)  (CLI --igm, --igm-frags "1-3;4-6"; 1-based atom indices of mol.xyz).
After the SCF it writes runs/<name>/wfn.molden (pyscf.tools.molden.from_scf) and runs Multiwfn noGUI
(/root/multiwfn/*/Multiwfn_noGUI; environment as in docs/multiwfn-nci-check.md) main function 20 -> 11 (IGMH),
grid = all atoms + 3 bohr, spacing 0.2 bohr. Writes:
  runs/<name>/dg_inter.cube      delta-g_inter (a.u.), interfragment only
  runs/<name>/igm_sl2rho.cube    sign(lambda2) rho on the same grid
  method.txt line starting "IGM:" naming "IGMH", the Multiwfn version, the fragments, and Multiwfn's
  "Integral of delta-g_inter" value.
Fragments: igm_frags if given, else the covalently bonded molecules (needs >= 2; a single molecule without
igm_frags exits cleanly with a message, no traceback). Multiwfn missing -> clean exit with the install hint.
render(name) also writes igm.png when both cubes exist: delta-g_inter = 0.005 a.u. isosurface coloured by
sign(lambda2) rho on [-0.04, +0.04], same colour map as nci.png.
Pass if (B3LYP/6-31G(d), gas; reference numbers from a throwaway implementation, 2026-11-15):
  - dimer cubes: spacing <= 0.2 bohr, box reaches >= 2.5 bohr beyond every atom; delta-g_inter >= -1e-6;
  - water dimer (.xyz, auto fragments): delta-g_inter maximum lies on the H...O contact (within 0.4 Å of the
    H...O segment) with sign(lambda2) rho < -0.015 there; behind the donor (x < -1.0 Å) max delta-g_inter < 1e-3;
    grid integral of delta-g_inter within 10 % of REF_DIMER;
  - method.txt IGM line contains "IGMH" and "Integral";
  - single water without igm_frags: clean exit (SystemExit with a message);
  - PAM3 fold (gas baseline tests/data/pam3_opt.xyz), igm_frags = the two amide groups (C, O, N, H on N) of its
    shortest H-bond: delta-g_inter maximum on that H...O contact, sign(lambda2) rho < -0.01 there; integral
    within 10 % of REF_PAM3;
  - igm.png rendered for the dimer.
"""
import tempfile
from pathlib import Path
import numpy as np
from _util import ROOT, Checks, esp_figure, need

need("igm")
REF_DIMER, REF_PAM3 = 0.0856, 0.0757   # grid integrals of delta-g_inter (a.u.), throwaway reference 2026-11-15
B2A = 0.529177
DIMER = """6
water dimer, linear O-H...O, H...O 1.95 A
O 0.000000 0.000000 0.000000
H 0.957200 0.000000 0.000000
H -0.239650 0.926700 0.000000
O 2.907200 0.000000 0.000000
H 3.493000 0.000000 0.757200
H 3.493000 0.000000 -0.757200
"""
WATER = "3\nwater\nO 0 0 0.117300\nH 0 0.757200 -0.469200\nH 0 -0.757200 -0.469200\n"


def cubes(out):
    g, l = (esp_figure.read_cube(out / f"{k}.cube") for k in ("dg_inter", "igm_sl2rho"))
    return g, g.points, g.point_data["rho"], l.point_data["rho"]


def on_segment(p, a, b, tol=0.4):
    t = np.clip((p - a) @ (b - a) / ((b - a) @ (b - a)), 0, 1)
    return np.linalg.norm(p - (a + t * (b - a))) < tol


def integral(grid, dg):
    return dg.sum() * np.prod(grid.spacing) / B2A ** 3   # spacing in Å -> bohr^3


def amide(i, bonds, sym):
    """The amide group (carbonyl C, O, N, H on N) containing atom i (an N-H hydrogen or a carbonyl O); 0-based."""
    nb = {k: set() for k in range(len(sym))}
    for a, b, _ in bonds:
        nb[a].add(b); nb[b].add(a)
    x = next(iter(nb[i]))                                           # N (for H) or C (for O)
    n, c = (x, next(k for k in nb[x] if sym[k] == "C" and any(sym[o] == "O" for o in nb[k]))) if sym[x] == "N" else \
           (next(k for k in nb[x] if sym[k] == "N"), x)
    o = next(k for k in nb[c] if sym[k] == "O")
    return sorted({c, o, n, *(k for k in nb[n] if sym[k] == "H")})


ok = Checks()
with tempfile.TemporaryDirectory() as root:
    d = Path(root) / "dimer.xyz"
    d.write_text(DIMER)
    out = esp_figure.calc(str(d), "dimer", root=root, igm=True)
    sym, xyz = esp_figure.read_xyz(out / "mol.xyz")
    grid, p, g, l = cubes(out)
    lo, hi = np.array(grid.bounds[::2]), np.array(grid.bounds[1::2])
    sp = max(grid.spacing) / B2A
    reach = min((xyz - lo).min(), (hi - xyz).min()) / B2A
    ok("dimer grid: spacing <= 0.2 bohr, >= 2.5 bohr beyond atoms", sp <= 0.2 + 1e-4 and reach >= 2.5, f"spacing {sp:.3f}, reach {reach:.2f} bohr")
    ok("dimer: delta-g_inter >= -1e-6", g.min() >= -1e-6, f"min {g.min():.2e}")
    k = int(np.argmax(g))
    ok("dimer: max on the H...O contact, sign(l2)rho < -0.015", on_segment(p[k], xyz[1], xyz[3]) and l[k] < -0.015,
       f"max {g[k]:.4f} at {np.round(p[k], 2)} Å, sl2rho {l[k]:.4f}")
    behind = g[p[:, 0] < -1.0].max()
    ok("dimer: behind the donor max delta-g_inter < 1e-3", behind < 1e-3, f"{behind:.2e}")
    I = integral(grid, g)
    ok("dimer: integral within 10 % of reference", REF_DIMER is not None and abs(I / REF_DIMER - 1) <= 0.10, f"{I:.5f} vs {REF_DIMER}")
    line = next((x for x in (out / "method.txt").read_text(encoding="utf-8").splitlines() if x.startswith("IGM:")), "")
    ok("method.txt IGM line", "IGMH" in line and "Integral" in line, line)
    esp_figure.render("dimer", style="rwb", root=root)
    ok("igm.png rendered", (out / "igm.png").exists())

    w = Path(root) / "water.xyz"
    w.write_text(WATER)
    try:
        esp_figure.calc(str(w), "water", root=root, igm=True)
        ok("single water without fragments: clean exit", False, "no exit")
    except SystemExit as e:
        ok("single water without fragments: clean exit", isinstance(e.code, str), f"{e.code}")

    sym, xyz = esp_figure.read_xyz(ROOT / "tests/data/pam3_opt.xyz")
    pairs = esp_figure.hbond_pairs(esp_figure.mol_from_xyz(sym, xyz), xyz)
    h, o = min(pairs, key=lambda q: np.linalg.norm(xyz[q[0]] - xyz[q[1]]))
    bonds = esp_figure.bond_list(sym, xyz)
    frags = [[i + 1 for i in amide(h, bonds, sym)], [i + 1 for i in amide(o, bonds, sym)]]
    out = esp_figure.calc(str(ROOT / "tests/data/pam3_opt.xyz"), "pam3", root=root, igm=True, igm_frags=frags)
    grid, p, g, l = cubes(out)
    k = int(np.argmax(g))
    ok(f"PAM3 fold: max on H{h + 1}...O{o + 1}, sign(l2)rho < -0.01", on_segment(p[k], xyz[h], xyz[o]) and l[k] < -0.01,
       f"frags {frags}; max {g[k]:.4f} at {np.round(p[k], 2)} Å, sl2rho {l[k]:.4f}")
    I = integral(grid, g)
    ok("PAM3 fold: integral within 10 % of reference", REF_PAM3 is not None and abs(I / REF_PAM3 - 1) <= 0.10, f"{I:.5f} vs {REF_PAM3}")
ok.finish()
