"""NCI (non-covalent interaction) cubes and picture.

Contract: calc(..., nci=True)  (CLI --nci) writes, from the run's total density on the same grid as dens.cube
(GRID points per axis, MARGIN), with analytic AO derivatives (no finite differences on the cube):
  runs/<name>/rdg.cube     reduced density gradient s = |grad rho| / (2 (3 pi^2)^(1/3) rho^(4/3))
  runs/<name>/sl2rho.cube  sign(lambda2) * rho, lambda2 = middle eigenvalue of the Hessian of rho (a.u.)
and a method.txt line starting "NCI:". render(name) also writes nci.png when both cubes exist: the s = 0.5
isosurface where rho < 0.05 a.u., coloured by sign(lambda2) rho on [-0.04, +0.04] (blue = attractive, e.g.
H-bond; green = weak vdW; red = steric).
Pass if:
  - cube values match a direct PySCF evaluation (rho, gradient, Hessian from AO 2nd derivatives) at 300 grid
    points of the water dimer where rho > 1e-4: s within 1 %, sign(lambda2) rho within 1e-3 relative (cube files
    keep ~6 significant digits, and this script's own SCF converges to a slightly different density: the
    reference implementation gave 1.05e-4; a sign error gives 2).
  - water dimer (.xyz, linear O-H...O, H...O 1.95 Å): grid points with s < 0.5 and |sl2rho| < 0.05 exist on the
    H...O contact (within 0.4 Å of the H...O segment, > 0.5 Å from both atoms) with min sl2rho < -0.015.
  - isolated water (.xyz): no grid point with s < 0.5 and |sl2rho| < 0.05 more than 1.0 Å from every nucleus
    (no spurious lobes).
  - PAM3 fold (locked gas baseline night/baseline/pam3_opt.xyz): every intramolecular H-bond
    (esp_figure.hbond_pairs) has such a contact lobe on the attractive side: min sl2rho < -0.01 if H...O < 2.3 Å,
    < -0.005 otherwise (reference: H35...O5 2.14 Å -0.0166; H26...O16 2.50 Å, at the H-bond cutoff, -0.0078).
  - nci.png is rendered for the dimer.
"""
import tempfile
from pathlib import Path
import numpy as np
from _util import ROOT, Checks, esp_figure, need
from pyscf import gto, dft

need("nci")
ok = Checks()
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
    s, l = (esp_figure.read_cube(out / f"{k}.cube") for k in ("rdg", "sl2rho"))
    return s.points, s.point_data["rho"], l.point_data["rho"]


def contact(p, s, l, xyz, i, j):
    """min sl2rho of NCI points (s < 0.5, |sl2rho| < 0.05) on the i...j contact, or None."""
    a, b = xyz[i], xyz[j]
    t = np.clip((p - a) @ (b - a) / ((b - a) @ (b - a)), 0, 1)
    on = (np.linalg.norm(p - (a + t[:, None] * (b - a)), axis=1) < 0.4) & \
         (np.linalg.norm(p - a, axis=1) > 0.5) & (np.linalg.norm(p - b, axis=1) > 0.5) & (s < 0.5) & (abs(l) < 0.05)
    return l[on].min() if on.any() else None


with tempfile.TemporaryDirectory() as root:
    d = Path(root) / "dimer.xyz"
    d.write_text(DIMER)
    out = esp_figure.calc(str(d), "dimer", root=root, nci=True)
    ok("method.txt has an NCI line", any(x.startswith("NCI:") for x in (out / "method.txt").read_text(encoding="utf-8").splitlines()))
    p, s, l = cubes(out)
    sym, xyz = esp_figure.read_xyz(out / "mol.xyz")
    # independent evaluation at 300 grid points with rho > 1e-4
    mol = gto.M(atom=list(zip(sym, map(tuple, xyz))), basis="6-31g*", verbose=0)
    mf = dft.RKS(mol).density_fit()
    mf.xc = "b3lyp"
    mf.kernel()
    dm = mf.make_rdm1()
    rng = np.random.default_rng(0)
    idx = rng.permutation(np.where(abs(l) > 1e-4)[0])[:300]
    ao = mol.eval_gto("GTOval_sph_deriv2", p[idx] / B2A)          # 0, x y z, xx xy xz yy yz zz
    c0 = ao[0] @ dm
    rho = np.einsum("pi,pi->p", c0, ao[0])
    g = 2 * np.einsum("pi,xpi->xp", c0, ao[1:4])
    pairs = {(0, 0): 4, (0, 1): 5, (0, 2): 6, (1, 1): 7, (1, 2): 8, (2, 2): 9}
    H = np.zeros((len(idx), 3, 3))
    for (a, b), k in pairs.items():
        H[:, a, b] = H[:, b, a] = 2 * (np.einsum("pi,pi->p", c0, ao[k]) +
                                       np.einsum("pi,ij,pj->p", ao[1 + a], dm, ao[1 + b]))
    lam2 = np.linalg.eigvalsh(H)[:, 1]
    s_ref = np.linalg.norm(g, axis=0) / (2 * (3 * np.pi ** 2) ** (1 / 3) * rho ** (4 / 3))
    l_ref = np.sign(lam2) * rho
    es, el = np.max(abs(s[idx] / s_ref - 1)), np.max(abs(l[idx] - l_ref) / abs(l_ref))
    ok("rdg.cube matches direct evaluation (1 %)", es <= 0.01, f"max rel. dev. {es:.2e}")
    ok("sl2rho.cube matches direct evaluation (1e-3 relative)", el <= 1e-3, f"max rel. dev. {el:.2e}")
    m = contact(p, s, l, xyz, 1, 3)
    ok("dimer: attractive lobe on H...O (min sl2rho < -0.015)", m is not None and m < -0.015, f"{m}")
    esp_figure.render("dimer", style="rwb", root=root)
    ok("nci.png rendered", (out / "nci.png").exists())

    w = Path(root) / "water.xyz"
    w.write_text(WATER)
    out = esp_figure.calc(str(w), "water", root=root, nci=True)
    p, s, l = cubes(out)
    _, xyz = esp_figure.read_xyz(out / "mol.xyz")
    far = np.linalg.norm(p[:, None] - xyz[None], axis=2).min(1) > 1.0
    n = int(((s < 0.5) & (abs(l) < 0.05) & far).sum())
    ok("isolated water: no off-atom NCI points", n == 0, f"{n} points")

    out = esp_figure.calc(str(ROOT / "night/baseline/pam3_opt.xyz"), "pam3", root=root, nci=True)
    p, s, l = cubes(out)
    sym, xyz = esp_figure.read_xyz(out / "mol.xyz")
    hb = esp_figure.hbond_pairs(esp_figure.mol_from_xyz(sym, xyz), xyz)
    ms = [contact(p, s, l, xyz, h, a) for h, a in hb]
    lim = [-0.01 if np.linalg.norm(xyz[h] - xyz[a]) < 2.3 else -0.005 for h, a in hb]
    ok("PAM3 fold: every H-bond has an attractive lobe (< -0.01 below 2.3 A, else < -0.005)",
       hb and all(m is not None and m < t for m, t in zip(ms, lim)),
       ", ".join(f"H{h + 1}...{sym[a]}{a + 1} {np.linalg.norm(xyz[h] - xyz[a]):.2f} A: {m}" for (h, a), m in zip(hb, ms))
       or "no H-bonds found")
ok.finish()
