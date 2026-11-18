"""Fukui functions, condensed to atoms.

Contract: calc(..., fukui=True)  (CLI --fukui) runs, at the run's final geometry (no re-optimisation), UKS for the
N+1 and N-1 electron systems (doublets; same functional, basis, density fitting, --d3/--solvent as the run;
called internally, so SMILES input works). Refused with spin > 0. Condensed with Mulliken populations p:
  f+ = p(N+1) - p(N)   (where an added electron goes: nucleophilic attack)
  f- = p(N) - p(N-1)   (where an electron leaves: electrophilic attack)
Writes runs/<name>/fukui.txt: one line per atom "<i> <element> <f+> <f->" (0-based, mol.xyz order; "#" lines are
comments) and a method.txt line starting "Fukui:" that names Mulliken condensation and says f+ is
"basis-limited" (6-31G(d) has no diffuse functions; the anion's extra electron is squeezed).
Pass if:
  - formaldehyde (SMILES C=O): f+ and f- each sum to 1 (+-0.02); every value within 0.01 of a direct PySCF
    calculation (RKS N, UKS N+-1, Mulliken) on the run's mol.xyz; f+ on C and on O each above every H
    (the C=O pi*; C vs O is too close to call with Mulliken: 0.278 vs 0.274 in the reference); f- largest on O.
  - formamide (SMILES NC=O): f- largest on O or N, not C.
  - method.txt says "basis-limited".
  - fukui=True with spin=1 is refused (exit, no traceback).
"""
import subprocess, sys, tempfile
import numpy as np
from _util import ROOT, Checks, esp_figure, need
from pyscf import gto, dft

need("fukui")
ok = Checks()


def read(out):
    rows = [l.split() for l in (out / "fukui.txt").read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("#")]
    return [r[1] for r in rows], np.array([[float(r[2]), float(r[3])] for r in rows])


def pop(sym, xyz, charge, spin):
    mol = gto.M(atom=list(zip(sym, map(tuple, xyz))), basis="6-31g*", charge=charge, spin=spin, verbose=0)
    mf = (dft.UKS if spin else dft.RKS)(mol).density_fit()
    mf.xc = "b3lyp"
    mf.kernel()
    return mol.atom_charges() - mf.mulliken_pop(verbose=0)[1]   # electrons per atom


with tempfile.TemporaryDirectory() as root:
    out = esp_figure.calc("C=O", "ch2o", root=root, fukui=True)
    log = (out / "method.txt").read_text(encoding="utf-8")
    sym, f = read(out)
    s2, xyz = esp_figure.read_xyz(out / "mol.xyz")
    ok("one row per atom, mol.xyz order", sym == s2, f"{sym} vs {s2}")
    ok("f+ and f- each sum to 1 (+-0.02)", np.all(abs(f.sum(0) - 1) <= 0.02), f"{f.sum(0)}")
    p0, pp, pm = pop(s2, xyz, 0, 0), pop(s2, xyz, -1, 1), pop(s2, xyz, 1, 1)
    ref = np.c_[pp - p0, p0 - pm]
    dev = np.max(abs(f - ref))
    ok("values match direct PySCF (0.01)", dev <= 0.01, f"max dev. {dev:.4f}")
    co = min(f[sym.index("C"), 0], f[sym.index("O"), 0])
    ok("formaldehyde: f+ on C and O each above every H", co > max(f[i, 0] for i, x in enumerate(sym) if x == "H"),
       f"f+ {list(zip(sym, f[:, 0].round(3)))}")
    ok("formaldehyde: f- largest on O", sym[f[:, 1].argmax()] == "O", f"f- {dict(zip(sym, f[:, 1].round(3)))}")
    ok("method.txt flags f+ as basis-limited", any(l.startswith("Fukui:") and "basis-limited" in l for l in log.splitlines()))

    out = esp_figure.calc("NC=O", "formamide", root=root, fukui=True)
    sym, f = read(out)
    ok("formamide: f- largest on O or N", sym[f[:, 1].argmax()] in ("O", "N"), f"f- {list(zip(sym, f[:, 1].round(3)))}")

    xyz_file = out.parent / "ch3.xyz"
    xyz_file.write_text("4\nmethyl\nC 0 0 0\nH 1.08 0 0\nH -0.54 0.935 0\nH -0.54 -0.935 0\n")
    r = subprocess.run([sys.executable, "-c", f"from esp_figure import calc; calc({str(xyz_file)!r}, 'r', root={root!r}, spin=1, fukui=True)"],
                       cwd=ROOT, capture_output=True, text=True, timeout=300)
    ok("fukui with spin > 0 refused", r.returncode != 0 and "Traceback" not in r.stderr, (r.stdout + r.stderr).strip()[-150:])
ok.finish()
