"""Stereo: the PAM3 SMILES must be syndiotactic with all 3 stereocentres specified.

Contract for the night agent: esp_figure.py defines a module constant PAM3 = "<syndiotactic PAM3 SMILES>",
the same molecule as "CC(C(N)=O)CC(C(N)=O)CC(C)C(N)=O" with @/@@ added.
  python night/sanity/stereo.py [SMILES]   # optional SMILES overrides PAM3 (to test this check itself)

Pass if: 3 stereocentres, all specified; all 50 conformers from geometry() have that same isomer;
with the backbone set all-trans (zigzag), adjacent C(=O)NH2 groups lie on opposite sides of its plane.
"""
import sys
import numpy as np
from _util import Checks, esp_figure, skip, UNSPEC_PAM3
from rdkit import Chem
from rdkit.Chem import rdMolTransforms as T

smi = sys.argv[1] if len(sys.argv) > 1 else getattr(esp_figure, "PAM3", None) or skip("esp_figure.PAM3 not defined yet")
ok = Checks()
m0 = Chem.MolFromSmiles(smi)
ok("same molecule as PAM3", Chem.MolToSmiles(m0, isomericSmiles=False) ==
   Chem.MolToSmiles(Chem.MolFromSmiles(UNSPEC_PAM3), isomericSmiles=False), smi)
st = [s for s in Chem.FindPotentialStereo(m0) if s.type == Chem.StereoType.Atom_Tetrahedral]
ok("3 stereocentres, all specified", len(st) == 3 and all(s.specified == Chem.StereoSpecified.Specified for s in st),
   f"{len(st)} centres, specified: {[str(s.specified) for s in st]}")

sym, xyz, charge, how, m = esp_figure.geometry(smi, 0)
want = Chem.MolToSmiles(m0)
got = []
for c in m.GetConformers():
    mc = Chem.Mol(m, confId=c.GetId())
    Chem.AssignStereochemistryFrom3D(mc)
    got.append(Chem.MolToSmiles(Chem.RemoveHs(mc)))
ok("all conformers are the input isomer", len(got) == 50 and all(g == want for g in got),
   f"{sum(g == want for g in got)}/{len(got)} match")

# Tacticity: zigzag the sp3 carbon backbone, then ask which side of its plane each amide carbon sits.
bb = {a.GetIdx() for a in m.GetAtoms() if a.GetSymbol() == "C" and a.GetHybridization() == Chem.HybridizationType.SP3}
nb = {i: [n.GetIdx() for n in m.GetAtomWithIdx(i).GetNeighbors() if n.GetIdx() in bb] for i in bb}
ends = [i for i in bb if len(nb[i]) == 1]
chain = [ends[0]]
while len(chain) < len(bb):
    chain.append(next(n for n in nb[chain[-1]] if n not in chain))
conf = m.GetConformer(m.GetConformers()[0].GetId())
for a, b, c, d in zip(chain, chain[1:], chain[2:], chain[3:]):
    T.SetDihedralDeg(conf, a, b, c, d, 180.0)
P = conf.GetPositions()
normal = np.linalg.svd(P[chain] - P[chain].mean(0))[2][2]
centres = [s.centeredOn for s in st]
side = []
for i in sorted(centres, key=chain.index):
    co = next(n.GetIdx() for n in m.GetAtomWithIdx(i).GetNeighbors() if n.GetSymbol() == "C" and n.GetIdx() not in bb)   # amide C
    side.append(int(np.sign(normal @ (P[co] - P[i]))))
ok("syndiotactic (amide sides alternate along the zigzag)", len(side) == 3 and side[0] == -side[1] == side[2] != 0,
   f"sides {side}")
ok.finish()
