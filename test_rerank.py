"""Re-ranking on ethylene glycol: 3 distinct conformers get DFT single points, the run continues with the lowest,
and a result with another --rerank setting is not reused. Plus (MMFF only): PAM3's 5 picks contain no mirror pairs."""
import re, tempfile
from rdkit import Chem
from rdkit.Chem import AllChem
from rdkit.Geometry import Point3D
from esp_figure import calc, geometry, PAM3

# PAM3 (syndiotactic) is meso-like: a conformer and its mirror image are the same shape after swapping chain ends, and
# have identical MMFF energies. Distinct picks must therefore all differ in MMFF energy.
sym, xyzs, *_ = geometry(PAM3, 0, top=5)
m = Chem.AddHs(Chem.MolFromSmiles(PAM3))
AllChem.EmbedMolecule(m, randomSeed=1)
ff_e = []
for x in xyzs:
    c = m.GetConformer()
    for i, p in enumerate(x):
        c.SetAtomPosition(i, Point3D(*map(float, p)))
    ff_e.append(AllChem.MMFFGetMoleculeForceField(m, AllChem.MMFFGetMoleculeProperties(m)).CalcEnergy())
assert len(ff_e) == 5 and min(abs(a - b) for i, a in enumerate(ff_e) for b in ff_e[i + 1:]) > 1e-3, ff_e

with tempfile.TemporaryDirectory() as root:
    log = (calc("OCCO", "plain", root=root) / "method.txt").read_text(encoding="utf-8")
    e0 = float(re.search(r"SCF energy: (\S+)", log).group(1))
    log = (calc("OCCO", "rr", root=root, rerank=3) / "method.txt").read_text(encoding="utf-8")
    es = [float(x) for x in re.search(r"DFT re-ranking energies: (.+) Eh", log).group(1).split(",")]
    e = float(re.search(r"SCF energy: (\S+)", log).group(1))
    # distinct shapes: mirror-image gauche duplicates differ only by DFT grid noise (~1e-5 Eh), real ones by >0.1 kcal/mol
    assert len(es) == 3 and min(abs(x - y) for i, x in enumerate(es) for y in es[i + 1:]) > 1e-4, es
    assert abs(e - min(es)) < 1e-6, (e, es)                       # continued with the lowest
    assert abs(es[0] - e0) < 1e-6, (es[0], e0)                    # first candidate = the plain run's MMFF pick
    assert "lowest B3LYP/6-31G(d) single-point energy of the 3 lowest distinct MMFF minima" in log, log
    for name, n in (("plain", 3), ("rr", 2), ("rr", 0)):         # any --rerank mismatch must not reuse a result
        try:
            calc("OCCO", name, root=root, rerank=n)
            raise AssertionError(f"reused {name} for --rerank {n}")
        except SystemExit as ex:
            assert "different --rerank setting" in str(ex)
    assert calc("OCCO", "rr", root=root, rerank=3)                # same setting is reused
print(f"ok (DFT energies {es}, picked {es.index(min(es)) + 1}; PAM3 MMFF picks {[round(x, 3) for x in ff_e]})")
