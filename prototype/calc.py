import time, numpy as np, pyvista as pv
from rdkit import Chem; from rdkit.Chem import AllChem
from pyscf import gto, dft, df
from pyscf.tools import cubegen
B2A = 0.529177
smi = "CC(C(N)=O)CC(C(N)=O)CC(C)C(N)=O"   # PAM trimer, H-capped
m = Chem.AddHs(Chem.MolFromSmiles(smi)); AllChem.EmbedMolecule(m, randomSeed=7); AllChem.MMFFOptimizeMolecule(m)
atoms = [(a.GetSymbol(), tuple(m.GetConformer().GetAtomPosition(a.GetIdx()))) for a in m.GetAtoms()]
mol = gto.M(atom=atoms, basis="6-31g*", verbose=0)
t = time.time(); mf = dft.RKS(mol).density_fit(); mf.xc = "b3lyp"; mf.kernel(); dm = mf.make_rdm1()
print("SCF", mf.converged, round(time.time()-t))
cube = cubegen.density(mol, "dens.cube", dm, nx=100, ny=100, nz=100, margin=6.0)
# isosurface of rho = 0.001 a.u., then ESP only at its vertices
from render_lib import read_cube
g, Z, xyz = read_cube("dens.cube")
surf = g.contour([0.001], scalars="v").smooth_taubin(n_iter=30).compute_normals()
pts = surf.points / B2A
V = np.zeros(len(pts))
for i in range(0, len(pts), 1500):
    p = pts[i:i+1500]
    V[i:i+1500] = -np.einsum("ijp,ij->p", df.incore.aux_e2(mol, gto.fakemol_for_charges(p)), dm)
for zc, R in zip(mol.atom_charges(), mol.atom_coords()):
    V += zc / np.linalg.norm(pts - R, axis=1)
surf.point_data["v"] = V; surf.save("surf.vtk")
print("ESP range", V.min().round(3), V.max().round(3), "pts", len(pts), round(time.time()-t))
