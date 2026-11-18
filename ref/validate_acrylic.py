"""Gaussian-vs-PySCF validation on acrylic acid from a reference Gaussian 16 + Multiwfn calculation (raw files local in esp-20260212/, not in git).

Reference: Gaussian 16 C.01, PBE0-D3(BJ)/6-311+G(d,p) (5D 7F), SMD water, single point on their
PBE0-D3(BJ)/6-31+G(d,p)/PCM geometry; ESP surface from Multiwfn (rho = 0.001; vtxe.pdb holds 23607 vertices, kcal/mol).

Same geometry (read from their .fchk) for every level, so only method/software differ:
  ref  PBE0-D3(BJ)/6-311+G(d,p)/SMD     their level: the actual validation
  fun  B3LYP-D3(BJ)/6-311+G(d,p)/SMD    only the functional differs from ref
  bas  PBE0-D3(BJ)/6-31G(d)/SMD         only the basis differs from ref
  pcm  PBE0-D3(BJ)/6-311+G(d,p)/IEF-PCM only the solvent model differs from ref (esp_figure's PCM)
  sol  PBE0-D3(BJ)/6-311+G(d,p)/gas     only the solvent differs from ref
  wat  B3LYP-D3(BJ)/6-31G(d)/IEF-PCM    esp_figure --d3 --solvent water
  def  B3LYP/6-31G(d)/gas               esp_figure default
For each: SCF energy, ESP at THEIR surface vertices vs. their ESP, and extremes on OUR own surface
(same pipeline as esp_figure.calc, but no density fitting).
Part 2: acrylamide (reference extrema only, no raw files: -59.86 / +66.28 kcal/mol) at ref and wat
level on our runs/acrylamide_w geometry (s-cis, B3LYP-D3(BJ)/6-31G(d)/PCM). Needs that run.
Usage: python ref/validate_acrylic.py  -> ref/validate_acrylic.txt  (~15 min on 8 cores)
"""
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import esp_figure as ef
from pyscf import gto, dft, __version__ as pyscf_version
from pyscf.tools import cubegen

REF = ROOT / "ref" / "esp-20260212"
KCAL = 627.5095
BOHR = 0.529177210903   # Å
G_E = -266.960376768   # e-sp.log SCF Done (includes D3(BJ) and SMD-CDS)
G_MIN, G_MAX = -43.65, 62.01   # Multiwfn surface extrema, kcal/mol (surfanalysise.pdb)
AM_MIN, AM_MAX = -59.86, 66.28  # reference acrylamide extrema, kcal/mol
LEVELS = {"ref": ("pbe0", "6-311+g(d,p)", "smd", True),
          "fun": ("b3lyp", "6-311+g(d,p)", "smd", True),
          "bas": ("pbe0", "6-31g*", "smd", True),
          "pcm": ("pbe0", "6-311+g(d,p)", "pcm", True),
          "sol": ("pbe0", "6-311+g(d,p)", None, True),
          "wat": ("b3lyp", "6-31g*", "pcm", True),
          "def": ("b3lyp", "6-31g*", None, False)}


def fchk_geometry(path):
    lines = Path(path).read_text().splitlines()
    def block(key):
        i = next(k for k, l in enumerate(lines) if l.startswith(key))
        n, vals = int(lines[i].split()[-1]), []
        for l in lines[i + 1:]:
            vals += l.split()
            if len(vals) >= n:
                return vals[:n]
    Z = [int(v) for v in block("Atomic numbers")]
    R = np.array([float(v) for v in block("Current cartesian coordinates")]).reshape(-1, 3)   # bohr
    return [gto.mole._symbol(z) for z in Z], R


def vertices(path):
    P, V = [], []
    for l in Path(path).read_text().splitlines():
        if l.startswith("HETATM"):
            P.append([float(l[30:38]), float(l[38:46]), float(l[46:54])])
            V.append(float(l[60:66]))
    return np.array(P) / BOHR, np.array(V)


def run(sym, R, key):
    """SCF at LEVELS[key] on geometry R (bohr); returns mol, energy, density matrix, ESP on our own surface (kcal/mol)."""
    xc, basis, solv, d3 = LEVELS[key]
    mol = gto.M(atom=list(zip(sym, R)), unit="Bohr", basis=basis, cart=False, verbose=0)
    mf = dft.RKS(mol); mf.xc = xc; mf.grids.atom_grid = (99, 590); mf.conv_tol = 1e-10
    if solv == "smd":
        mf = mf.SMD(); mf.with_solvent.solvent = "water"
    elif solv == "pcm":   # as esp_figure.calc
        mf = mf.PCM(); mf.with_solvent.method = "IEF-PCM"; mf.with_solvent.eps = ef.SOLVENTS["water"]
    if d3:
        mf.disp = "d3bj"
    e = mf.kernel()
    assert mf.converged, key
    dm = mf.make_rdm1()
    cube = Path(__file__).with_name(f"dens_{key}.cube")
    cubegen.density(mol, str(cube), dm, nx=ef.GRID, ny=ef.GRID, nz=ef.GRID, margin=ef.MARGIN)
    surf = ef.read_cube(cube).contour([ef.ISO], scalars="rho").smooth_taubin(n_iter=30)
    cube.unlink()
    return mol, e, dm, ef.esp_at(mol, dm, np.asarray(surf.points) / BOHR) * KCAL


def name(key):
    xc, basis, solv, d3 = LEVELS[key]
    return f"{xc.upper()}{'-D3(BJ)' if d3 else ''}/{basis}/{ {'smd': 'SMD', 'pcm': 'IEF-PCM', None: 'gas'}[solv]}"


def own(Vs, rmin, rmax):
    return (f"{Vs.min():7.2f} ({Vs.min() / KCAL:+.4f}, {Vs.min() / rmin - 1:+5.0%}) "
            f"{Vs.max():7.2f} ({Vs.max() / KCAL:+.4f}, {Vs.max() / rmax - 1:+5.0%})")


sym, R = fchk_geometry(REF / "e-sp.fchk")
pts, Vref = vertices(REF / "vtxe.pdb")
txt = [f"Gaussian-vs-PySCF validation, acrylic acid (reference Gaussian 16 + Multiwfn calculation). PySCF {pyscf_version}.",
       f"Geometry from e-sp.fchk; reference: G16 C.01 PBE0-D3(BJ)/6-311+G(d,p) 5D SMD water, E = {G_E:.9f} Eh,",
       f"Multiwfn surface rho = 0.001 a.u., {len(pts)} vertices, ESP {Vref.min():.2f} .. {Vref.max():.2f} kcal/mol "
       f"(surface extrema {G_MIN} / {G_MAX}). Grid (99,590), no density fitting, spherical d.",
       "",
       "dE: PySCF - Gaussian (only meaningful for ref). ESP columns: at THEIR vertices, kcal/mol. Own surface: our",
       "rho = 0.001 isosurface (esp_figure pipeline), min/max kcal/mol (a.u., change vs. the reference surface extrema).", "",
       f"{'lvl':4} {'method':36} {'E / Eh':>15} {'dE kcal':>8} {'MAE':>5} {'max|d|':>6} {'rho@theirs':>15}  "
       f"{'own min':>24} {'own max':>24}"]
for key in LEVELS:
    mol, e, dm, Vs = run(sym, R, key)
    d = ef.esp_at(mol, dm, pts) * KCAL - Vref
    rho = dft.numint.eval_rho(mol, dft.numint.eval_ao(mol, pts), dm)
    txt.append(f"{key:4} {name(key):36} {e:15.9f} {(e - G_E) * KCAL:8.3f} {np.abs(d).mean():5.2f} {np.abs(d).max():6.2f} "
               f"{rho.min():.5f}-{rho.max():.5f}  {own(Vs, G_MIN, G_MAX)}")
    print(txt[-1], flush=True)

sym, xyz = ef.read_xyz(ROOT / "runs" / "acrylamide_w" / "mol.xyz")
txt += ["", "Acrylamide (reference geometry unknown, reference extrema only: "
        f"{AM_MIN} / {AM_MAX} kcal/mol), our runs/acrylamide_w s-cis geometry:"]
for key in ("ref", "wat"):
    Vs = run(sym, np.asarray(xyz) / BOHR, key)[3]
    txt.append(f"{key:4} {name(key):36} {own(Vs, AM_MIN, AM_MAX)}")
    print(txt[-1], flush=True)
Path(__file__).with_suffix(".txt").write_text("\n".join(txt) + "\n", encoding="utf-8")
