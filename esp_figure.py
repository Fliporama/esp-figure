#!/usr/bin/env python3
"""ESP figures in two stages: `calc` does the chemistry once, `render` makes PNGs in seconds.

  python esp_figure.py calc "C[C@@H](C(N)=O)C[C@H](C(N)=O)C[C@H](C)C(N)=O" --name pam3 [--charge 0] [--opt] [--d3] [--solvent water] [--rerank 5] [--orbitals] [--force]
  (SMILES must specify all stereo; that one is the syndiotactic PAM trimer, esp_figure.PAM3)
  python esp_figure.py render pam3 [--style rwb|rainbow|both] [--limit 0.06] [--view=x,y,z] [--extrema] [--hbonds]

Results live in runs/<name>/: mol.xyz, dens.cube, surf.vtk (with ESP), method.txt,
and after render: ball.png, <style>_esp.png, caption.txt (+ homo/lumo .cube/.png with --orbitals).
"""
import argparse, re, sys, time
from pathlib import Path
import numpy as np

B2A = 0.529177   # bohr -> Å
ISO = 0.001      # density isovalue for the surface, a.u.
GRID = 100       # density grid points per axis
# ponytail: fixed point count, so spacing grows with molecule size; raise GRID if big molecules look faceted
MARGIN = 6.0     # bohr of empty space around the molecule; less -> holes near the O atoms
LIMITS = {"rainbow": 0.06, "rwb": 0.03}
H2EV = 27.211386 # Hartree -> eV
OPT_CONV = {  # geomeTRIC rules, recorded in method.txt
    "gau": "gau (geomeTRIC default, Gaussian-like: energy 1e-6 Eh, gradient rms/max 3e-4/4.5e-4, displacement rms/max 1.2e-3/1.8e-3, all five)",
    "qchem": "qchem (geomeTRIC qccnv: RMS gradient 3e-4 AND either energy change 1e-6 Eh or RMS displacement 1.2e-3; max criteria not used)",
}
ORB_ISO = 0.02   # orbital isovalue (a.u.) for the HOMO/LUMO pictures, a common GaussView-like choice
ORB_COLORS = ("#2e8b57", "#8e44ad")   # +/- phase: green/purple, so no one reads them as ESP red/blue
ORB_OPACITY = 0.3   # lower than the ESP surface (0.7): lobes in front must not tint the atoms' element colours
CONFS = 50       # conformers tried in the MMFF conformer search (SMILES input only)
HB_CUT = 2.5     # Å; H···N/O closer than this (and >3 bonds apart) counts as an intramolecular H-bond
LEVEL = "B3LYP/6-31G(d)"
SOLVENTS = {"water": 78.3553}   # dielectric constants for --solvent (PySCF/Gaussian value for water)
# H-capped PAM trimer, syndiotactic (adjacent CONH2 alternate sides of the zigzag backbone; checked by night/sanity/stereo.py).
# Free-radical PAM is atactic; syndiotactic is the model choice (user decision 2026-11-11).
PAM3 = "C[C@@H](C(N)=O)C[C@H](C(N)=O)C[C@H](C)C(N)=O"
# Elements with both MMFF94 parameters and a 6-31G(d) basis in PySCF (no I: 6-31G(d) stops before it)
ELEMENTS = {"H", "C", "N", "O", "F", "Si", "P", "S", "Cl", "Br"}
# ponytail: one list for SMILES and .xyz input; .xyz needs no MMFF, widen it when other basis sets arrive
# Jmol-style colours; unknown elements fall back to pink (#ff69b4) so they stand out
COLORS = {"H": "#f2f2f2", "C": "#7f7f7f", "N": "#1f3fff", "O": "#ff1f1f", "S": "#e6c619", "Cl": "#1fd01f",
          "F": "#90e050", "P": "#ff8000", "Si": "#f0c8a0", "Br": "#a62929", "I": "#940094", "B": "#ffb5b5",
          "Li": "#cc80ff", "Na": "#ab5cf2", "K": "#8f40d4", "Mg": "#8aff00", "Ca": "#3dff00", "Al": "#bfa6a6",
          "Fe": "#e06633", "Cu": "#c88033", "Zn": "#7d80b0"}


def read_xyz(path):
    lines = Path(path).read_text().splitlines()
    rows = [l.split() for l in lines[2:2 + int(lines[0])]]
    return [r[0] for r in rows], np.array([r[1:4] for r in rows], float)


def xyz_text(sym, xyz, comment):
    return f"{len(sym)}\n{comment}\n" + "".join(f"{s} {x:.6f} {y:.6f} {z:.6f}\n" for s, (x, y, z) in zip(sym, xyz))


def read_cube(path):
    """Gaussian cube (bohr) -> PyVista grid (Å) with point data 'rho'."""
    import pyvista as pv
    L = Path(path).read_text().split("\n")
    n, *o = L[2].split()
    ax = [L[3 + i].split() for i in range(3)]
    shape = [int(a[0]) for a in ax]
    step = np.array([a[1:4] for a in ax], float)
    data = np.array(" ".join(L[6 + abs(int(n)):]).split(), float).reshape(shape)
    g = pv.ImageData(dimensions=shape, spacing=np.diag(step) * B2A, origin=np.array(o[:3], float) * B2A)
    g.point_data["rho"] = data.ravel(order="F")
    return g


def hbond_pairs(m, xyz):
    """Intramolecular H-bonds as (H index, acceptor index): H on N/O within HB_CUT of an N/O more than
    3 bonds away (i.e. not its own amide O)."""
    from rdkit import Chem
    topo = Chem.GetDistanceMatrix(m)
    don = [a.GetIdx() for a in m.GetAtoms() if a.GetSymbol() == "H" and a.GetNeighbors()[0].GetSymbol() in "NO"]
    acc = [a.GetIdx() for a in m.GetAtoms() if a.GetSymbol() in ("N", "O")]
    return [(h, a) for h in don for a in acc if topo[h, a] > 3 and np.linalg.norm(xyz[h] - xyz[a]) < HB_CUT]


def hbonds(m, xyz):
    return len(hbond_pairs(m, xyz))


def mol_from_xyz(sym, xyz):
    """Bond graph from coordinates (for H-bond topology when only mol.xyz is available)."""
    from rdkit import Chem
    from rdkit.Chem import rdDetermineBonds
    m = Chem.MolFromXYZBlock(f"{len(sym)}\n\n" + "".join(f"{s} {x} {y} {z}\n" for s, (x, y, z) in zip(sym, xyz)))
    rdDetermineBonds.DetermineConnectivity(m)
    return m


def bond_list(sym, xyz, charge=0):
    """Covalent bonds as (i, j, order), order 1/2/3, from coordinates (RDKit DetermineBondOrders).
    If no valid bond-order assignment exists (e.g. a charged run), every bond comes back as single."""
    from rdkit.Chem import rdDetermineBonds
    m = mol_from_xyz(sym, xyz)
    try:
        rdDetermineBonds.DetermineBondOrders(m, charge=charge)
    except ValueError:
        pass
    return [(b.GetBeginAtomIdx(), b.GetEndAtomIdx(), max(1, int(b.GetBondTypeAsDouble()))) for b in m.GetBonds()]


def stick_offsets(xyz, bonds, i, j, order, view):
    """Sideways shifts (Å) of the sticks for one bond: one stick for single, two for double, three for triple.
    Multiple sticks lie in the plane of a neighbouring atom (e.g. the amide plane for C=O),
    or perpendicular to the view direction when there is no usable neighbour."""
    if order == 1:
        return [np.zeros(3)]
    d = (xyz[j] - xyz[i]) / np.linalg.norm(xyz[j] - xyz[i])
    nbr = [(a, b) for a, b, _ in bonds for a, b in ((a, b), (b, a)) if a in (i, j) and b not in (i, j)]
    for a, b in nbr + [(None, None)]:
        v = xyz[b] - xyz[a] if a is not None else np.cross(d, view)
        v = v - (v @ d) * d
        if np.linalg.norm(v) > 0.1:
            break
    else:
        v = np.cross(d, [1.0, 0, 0]) if abs(d[0]) < 0.9 else np.cross(d, [0, 1.0, 0])
    v /= np.linalg.norm(v)
    return [k * 0.11 * v for k in ((-1, 1) if order == 2 else (-1.4, 0, 1.4))]


def esp_extrema(surf, sym, xyz):
    """Most negative and most positive ESP on the surface, with the nearest atom (e.g. 'O12', 1-based)."""
    out = []
    for kind, i in (("min", int(surf["esp"].argmin())), ("max", int(surf["esp"].argmax()))):
        p = surf.points[i]
        k = int(np.linalg.norm(xyz - p, axis=1).argmin())
        out.append({"kind": kind, "value": float(surf["esp"][i]), "point": p, "atom": f"{sym[k]}{k + 1}"})
    return out


def check_input(sym, charge):
    """Refuse what the method can't do, before any compute: unsupported elements, open-shell (radical) molecules."""
    from pyscf.data.elements import charge as Z
    bad = sorted(set(sym) - ELEMENTS)
    if bad:
        sys.exit(f"unsupported element(s) {', '.join(bad)}: MMFF94 + 6-31G(d) cover only {', '.join(sorted(ELEMENTS))}")
    if (sum(Z(s) for s in sym) - charge) % 2:
        sys.exit("odd number of electrons (radical / open-shell): only closed-shell RKS is supported; "
                 "check the charge, or add the missing H")


def geometry(spec, charge, no_hbond=False, top=1):
    """SMILES or .xyz -> symbols, coords (Å), charge, description, RDKit mol (None for .xyz).
    top > 1: coords is a list of the `top` lowest distinct MMFF conformers instead (for DFT re-ranking)."""
    if spec.endswith(".xyz"):
        if no_hbond or top > 1:
            sys.exit("--no-hbond and --rerank need SMILES input (they pick among conformers)")
        sym, xyz = read_xyz(spec)
        check_input(sym, charge)
        return sym, xyz, charge, f"geometry read from {Path(spec).name}", None
    from rdkit import Chem
    from rdkit.Chem import AllChem
    m = Chem.MolFromSmiles(spec)
    if m is None:
        sys.exit(f"bad SMILES: {spec}")
    check_input([a.GetSymbol() for a in Chem.AddHs(m).GetAtoms()], Chem.GetFormalCharge(m))
    # Undefined stereo would make each conformer a random stereoisomer, so "lowest energy" compares different molecules.
    loose = [f"{'stereocentre at' if s.type.name.startswith('Atom') else 'double bond'} atom {s.centeredOn}"
             for s in Chem.FindPotentialStereo(m)
             if s.specified != Chem.StereoSpecified.Specified]
    if loose:
        sys.exit(f"unspecified stereo ({', '.join(loose)}): write @/@@ or /\\ into the SMILES, "
                 f"e.g. syndiotactic PAM3 {PAM3}")
    m = Chem.AddHs(m)
    # Conformer search: embed many, keep the lowest MMFF energy, so the figure isn't one random shape.
    cids = list(AllChem.EmbedMultipleConfs(m, numConfs=CONFS, randomSeed=7))
    if not cids:
        sys.exit("RDKit could not embed the molecule")
    energies = np.array([e for _, e in AllChem.MMFFOptimizeMoleculeConfs(m, maxIters=2000)])
    ok = np.ones(len(cids), bool)
    if no_hbond:
        ok = np.array([hbonds(m, m.GetConformer(c).GetPositions()) == 0 for c in cids])
        if not ok.any():
            sys.exit(f"--no-hbond: all {len(cids)} conformers have an intramolecular H-bond (< {HB_CUT} Å)")
    best = int(np.argmin(np.where(ok, energies, np.inf)))
    sym = [a.GetSymbol() for a in m.GetAtoms()]
    how = (f"lowest-energy of {ok.sum()}/{len(cids)} H-bond-free (no H···N/O < {HB_CUT} Å) conformers"
           if no_hbond else f"lowest-energy of {len(cids)} conformers")
    xyz = m.GetConformer(cids[best]).GetPositions()
    if top > 1:   # the `top` lowest *distinct* minima (MMFF lands many embeddings in the same one), lowest first
        heavy = [a.GetIdx() for a in m.GetAtoms() if a.GetAtomicNum() > 1]
        P = [m.GetConformer(c).GetPositions()[heavy] for c in cids]
        P = [p - p.mean(0) for p in P]
        # Best-fit RMSD over rotations AND reflections (no det fix in Kabsch) AND heavy-atom graph automorphisms:
        # mirror-image conformers are the same shape when the molecule is achiral, incl. meso-like syndiotactic PAM3,
        # whose mirror image maps onto itself only after swapping the two chain ends.
        hm = Chem.RemoveHs(m)                  # keeps heavy-atom order, so its indices match P
        perms = [list(p) for p in hm.GetSubstructMatches(hm, uniquify=False, useChirality=False, maxMatches=1000)]
        fit = lambda a, b: np.sqrt(max(0.0, ((a ** 2).sum() + (b ** 2).sum() - 2 * np.linalg.svd(a.T @ b)[1].sum()) / len(a)))
        rmsd = lambda a, b: min(fit(a[p], b) for p in perms)
        picks = []
        for i in np.argsort(np.where(ok, energies, np.inf))[:ok.sum()]:
            if all(abs(energies[i] - energies[j]) > 0.1 or rmsd(P[i], P[j]) > 0.1 for j in picks):
                picks.append(i)
            if len(picks) == top:
                break
        xyz = [m.GetConformer(cids[i]).GetPositions() for i in picks]
        how = (f"of the {len(picks)} lowest distinct MMFF minima (heavy-atom RMSD or energy apart by > 0.1 Å / "
               f"0.1 kcal/mol) among {ok.sum()}/{len(cids)}{' H-bond-free' if no_hbond else ''} conformers")
    return (sym, xyz, Chem.GetFormalCharge(m),
            ("syndiotactic H-capped PAM trimer, " if spec == PAM3 else "") + f"{how}, RDKit ETKDG + MMFF94 (draft)", m)


def calc(spec, name, charge=0, opt=False, force=False, no_hbond=False, root="runs", d3=False, solvent=None, rerank=0,
         orbitals=False, opt_conv="gau"):
    out = Path(root) / name
    log = out / "method.txt"
    level = "B3LYP-D3(BJ)/6-31G(d)" if d3 else LEVEL
    rerank = rerank if rerank > 1 else 0       # 0 and 1 both mean: take the lowest-MMFF conformer
    if solvent:
        if solvent not in SOLVENTS:
            sys.exit(f"unknown solvent {solvent}; supported: {', '.join(SOLVENTS)}")
        level += f" + IEF-PCM({solvent}, eps {SOLVENTS[solvent]})"
    if log.exists() and not force:
        text = log.read_text(encoding="utf-8")
        first = text.splitlines()[0]
        if first != f"input: {spec}":
            sys.exit(f"{out} holds a different molecule ({first}). Use another --name, or --force.")
        if f"level of theory: {level}," not in text:
            sys.exit(f"{out} was computed at a different level of theory (not {level}). Use another --name, or --force.")
        if (f"--rerank {rerank})" not in text) if rerank else ("DFT re-ranking energies" in text):
            sys.exit(f"{out} was computed with a different --rerank setting. Use another --name, or --force.")
        if not orbitals or (out / "homo.cube").exists():
            print(f"{out} already computed (use --force to redo)")
            return out
    out.mkdir(parents=True, exist_ok=True)
    import pyscf, rdkit
    from pyscf import gto, dft, df
    from pyscf.tools import cubegen

    t0 = time.time()
    sym, xyz, charge, geo, rdm = geometry(spec, charge, no_hbond, top=rerank)
    # Restart: --opt appends every step to opt_traj.xyz; a rerun after a crash (no method.txt) resumes from the last frame.
    traj, tag, done = out / "opt_traj.xyz", f"{spec} | {level} | charge {charge} | no-hbond {no_hbond} | rerank {rerank}", 0
    if force:
        traj.unlink(missing_ok=True)
    rr = out / "rerank.txt"   # kept on disk so a restarted --opt still reports the re-ranking it started from
    if opt and traj.exists():
        if rerank and not rr.exists():
            sys.exit(f"{traj} exists but {rr.name} is missing. Delete the trajectory, or use --force.")
        L = traj.read_text(encoding="utf-8").splitlines()
        done = len(L) // (len(sym) + 2)                  # complete frames; a frame cut off by a kill is dropped
        last = L[(done - 1) * (len(sym) + 2):done * (len(sym) + 2)]
        if not done or last[0] != str(len(sym)) or not last[1].startswith(tag + " |") or [r.split()[0] for r in last[2:]] != sym:
            sys.exit(f"{traj} is from a different molecule, charge, conformer choice or level of theory. "
                     "Delete it, or use --force.")
        traj.write_text("\n".join(L[:done * (len(sym) + 2)]) + "\n", encoding="utf-8")
        xyz = np.array([r.split()[1:4] for r in last[2:]], float)
        geo = f"{geo}; restarted from step {done} of an interrupted optimisation"
    build = lambda x: gto.M(atom=[(s, tuple(map(float, r))) for s, r in zip(sym, x)], charge=charge, basis="6-31g*", verbose=0)

    def scf(mol):
        mf = dft.RKS(mol).density_fit()
        mf.xc = "b3lyp"
        if d3:
            mf.disp = "d3bj"   # pip install pyscf-dispersion; post-SCF energy term, density and ESP unchanged
        if solvent:            # IEF-PCM: polarises the density, so it changes energy, geometry (with --opt) and ESP
            mf = mf.PCM()
            mf.with_solvent.method = "IEF-PCM"
            mf.with_solvent.eps = SOLVENTS[solvent]
        mf.kernel()
        return mf

    if rerank and not done:
        # DFT re-ranking at the run's own level (D3/solvent included), since MMFF and DFT can order conformers differently.
        es, bad, mf = [], [], None
        for k, x in enumerate(xyz, 1):
            f = scf(build(x))
            es.append(f.e_tot)
            if not f.converged:
                bad.append(f"#{k}")       # never picked
            elif mf is None or f.e_tot < mf.e_tot:
                mf, pick = f, k           # keep only the best SCF (each holds a large density-fitting tensor)
        if mf is None:
            sys.exit("--rerank: no candidate SCF converged")
        rr.write_text(f"DFT re-ranking energies: {', '.join(f'{e:.8f}' for e in es)} Eh (MMFF order; picked #{pick}"
                      f"{'; unconverged, not picked: ' + ' '.join(bad) if bad else ''}; --rerank {rerank})\n", encoding="utf-8")
        mol = mf.mol
    else:
        mol = build(xyz)
        mf = scf(mol)
    if rerank:
        geo = f"lowest {level} single-point energy {geo}"
    if opt:
        from pyscf.geomopt.geometric_solver import optimize   # pip install geometric
        steps = []

        def frame(env):                        # called by geomeTRIC once per step
            if done and not frame.seen:        # a resumed run first re-evaluates the last frame: already in the file
                frame.seen = True
                return
            steps.append(env["energy"])
            with traj.open("a", encoding="utf-8") as f:
                f.write(xyz_text(sym, env["mol"].atom_coords() * B2A, f"{tag} | step {done + len(steps)} E {env['energy']:.10f}"))
        frame.seen = False
        # qchem: GAU gradient criteria AND (energy OR displacement); floppy chains otherwise creep on displacement
        mol = optimize(mf, callback=frame, **({"qccnv": True} if opt_conv == "qchem" else {}))
        mf = scf(mol)
        geo = f"{level} optimised geometry (geomeTRIC), started from {geo}"
    if not mf.converged:
        print("WARNING: SCF did not converge; results are not trustworthy", file=sys.stderr)
    dm = mf.make_rdm1()
    xyz = mol.atom_coords() * B2A
    (out / "mol.xyz").write_text(xyz_text(sym, xyz, name))

    # Surface: isosurface of the density. ESP only at its vertices (full-grid ESP is >10x slower).
    cubegen.density(mol, str(out / "dens.cube"), dm, nx=GRID, ny=GRID, nz=GRID, margin=MARGIN)
    surf = read_cube(out / "dens.cube").contour([ISO], scalars="rho").smooth_taubin(n_iter=30).compute_normals()
    pts = surf.points / B2A
    V = np.zeros(len(pts))
    for i in range(0, len(pts), 1500):   # chunked to limit memory
        p = pts[i:i + 1500]
        V[i:i + 1500] = -np.einsum("ijp,ij->p", df.incore.aux_e2(mol, gto.fakemol_for_charges(p)), dm)  # electrons
    for zc, R in zip(mol.atom_charges(), mol.atom_coords()):
        V += zc / np.linalg.norm(pts - R, axis=1)                                                      # nuclei
    surf.point_data["esp"] = V
    surf.save(out / "surf.vtk")
    orb = ""
    if orbitals:   # closed-shell RKS: HOMO = nelectron//2 - 1; same grid as the density cube
        h = mol.nelectron // 2 - 1
        for k, i in (("homo", h), ("lumo", h + 1)):
            cubegen.orbital(mol, str(out / f"{k}.cube"), mf.mo_coeff[:, i], nx=GRID, ny=GRID, nz=GRID, margin=MARGIN)
        orb = f"HOMO: {mf.mo_energy[h] * H2EV:.4f} eV\nLUMO: {mf.mo_energy[h + 1] * H2EV:.4f} eV\n"
    disp = f" (includes dispersion)\ndispersion energy: {mf.get_dispersion():.8f} Eh (D3(BJ), pyscf-dispersion)" if d3 else ""
    if solvent:
        ws = mf.with_solvent
        disp += (f"\nsolvent: implicit {solvent}, IEF-PCM eps {ws.eps} (PySCF; default vdW radii x {ws.vdw_scale}, "
                 f"Lebedev order {ws.lebedev_order}), in the SCF"
                 f"{' and the optimisation' if opt else ' only (geometry not optimised in solvent)'}; "
                 "SCF energy is the total energy in solvent; mapped ESP is "
                 "nuclei + solvated electron density (PCM surface charges not included)")

    log.write_text(f"""input: {spec}
name: {name}
charge: {charge}
atoms: {len(sym)}
geometry: {geo}{f"{chr(10)}optimisation steps: {len(steps)} (this run; trajectory in opt_traj.xyz)" if opt else ""}{f"{chr(10)}optimisation convergence: {OPT_CONV[opt_conv]}" if opt else ""}
intramolecular H-bonds in final geometry (H···N/O < {HB_CUT} Å): {hbonds(rdm, xyz) if rdm else "n/a"}
level of theory: {level}, density fitting (PySCF default auxiliary basis); ESP integrals exact
SCF energy: {mf.e_tot:.8f} Eh (converged: {mf.converged}){disp}
{rr.read_text(encoding="utf-8") if rerank else ""}surface: electron density isosurface rho = {ISO} a.u. (grid {GRID}^3, margin {MARGIN} bohr), {len(pts)} vertices
ESP range on surface: {V.min():.4f} to {V.max():.4f} a.u.
{orb}software: PySCF {pyscf.__version__}, RDKit {rdkit.__version__}, NumPy {np.__version__}
wall time: {time.time() - t0:.0f} s
caption: Electrostatic potential mapped onto the {ISO} a.u. electron-density isosurface, computed at the {level} level with PySCF {pyscf.__version__} ({geo}).
""")
    print(log.read_text())
    return out


def auto_view(surf, sym, xyz, n=600):
    """Camera direction that shows V_s,min (weight 2) and V_s,max, C=O double bonds and H-bonds side-on, few overlapping
    heavy atoms, and stays near the chain-flat default (thinnest axis), which the day-session search showed matters:
    without it the top picks looked tangled. Same front/back ray test as render()."""
    c0 = xyz.mean(0)
    ev = np.linalg.svd(xyz - c0)[2]
    ex, bonds = esp_extrema(surf, sym, xyz), bond_list(sym, xyz)
    hb = hbond_pairs(mol_from_xyz(sym, xyz), xyz)
    nrm = surf.compute_normals(point_normals=True, cell_normals=False).point_data["Normals"]
    starts = []
    for x in ex:
        nv = nrm[surf.find_closest_point(x["point"])]
        starts.append(x["point"] + 0.3 * (nv if nv @ (x["point"] - c0) > 0 else -nv))
    dbl = [(i, j) for i, j, o in bonds if o == 2]
    heavy = [k for k, s_ in enumerate(sym) if s_ != "H"]
    k = np.arange(n) + 0.5                     # Fibonacci sphere
    phi, th = np.arccos(1 - 2 * k / n), np.pi * (1 + 5 ** 0.5) * k
    best = (-1e9, ev[2])
    for d in np.c_[np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)]:
        vis = [not len(surf.ray_trace(st, st + 100 * d)[0]) for st in starts]
        co = [(1 - abs((xyz[j] - xyz[i]) @ d) / np.linalg.norm(xyz[j] - xyz[i]))
              * (1 - abs(stick_offsets(xyz, bonds, i, j, 2, d)[1] @ d) / 0.11) for i, j in dbl] or [1.0]
        hbs = [1 - abs((xyz[a] - xyz[h]) @ d) / np.linalg.norm(xyz[a] - xyz[h]) for h, a in hb] or [1.0]
        P = xyz[heavy] - np.outer(xyz[heavy] @ d, d)
        ov = (np.linalg.norm(P[:, None] - P[None], axis=2) < 0.6).sum() - len(heavy)
        score = 2.0 * vis[0] + vis[1] + np.mean(co) + np.mean(hbs) - 0.15 * ov + 1.5 * abs(d @ ev[2])
        best = max(best, (score, d), key=lambda t: t[0])
    return best[1]


def colormap(style):
    """Same convention in every style: red = negative, blue = positive."""
    from matplotlib.colors import LinearSegmentedColormap
    return {"rainbow": LinearSegmentedColormap.from_list("gv", ["#ff0000", "#ffff00", "#00ff00", "#00ffff", "#0000ff"]),
            "rwb": LinearSegmentedColormap.from_list("rwb", ["#e8413a", "#ffffff", "#3a4fe8"])}[style]


def panel(names, labels=None, style="rainbow", out="runs/panel.png", root="runs"):
    """Rendered ESP maps side by side with one shared colour bar, plus a caption file (<out>.txt).
    Refuses maps rendered with different colour limits; gives energy differences only at one level of theory."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import Normalize
    runs = []
    for n in names:
        d = Path(root) / n
        cap, log = ((d / f).read_text(encoding="utf-8") for f in ("caption.txt", "method.txt"))
        m = re.search(rf"^{style}_esp\.png: colour scale -(\S+) to", cap, re.M)
        if not m:
            sys.exit(f"panel: {d} has no {style}_esp.png in caption.txt; render it first")
        sym, xyz = read_xyz(d / "mol.xyz")
        img = plt.imread(d / f"{style}_esp.png")[..., :3]
        img = img[:, : int(img.shape[1] * 0.86)]           # drop the render's own colour bar (title starts at x ~ 0.866)
        ink = img.min(axis=2) < 0.97                         # crop the white margins
        r, c = np.flatnonzero(ink.any(1)), np.flatnonzero(ink.any(0))
        img = img[max(r[0] - 15, 0): r[-1] + 15, max(c[0] - 15, 0): c[-1] + 15]
        runs.append(dict(label=n, lim=float(m.group(1)), img=img, cap=re.search(r"^caption: (.+)", log, re.M).group(1),
                         e=float(re.search(r"SCF energy: (\S+)", log).group(1)),
                         level=re.search(r"level of theory: (.+)", log).group(1), atoms=sym,
                         esp=re.search(r"ESP range on surface: (\S+) to (\S+)", log).groups(),
                         hb=len(hbond_pairs(mol_from_xyz(sym, xyz), xyz))))
    for k, lab in enumerate(labels or []):
        runs[k]["label"] = lab
    if len({x["lim"] for x in runs}) > 1:
        sys.exit("panel: colour limits differ (" + ", ".join(f"{x['label']} {x['lim']}" for x in runs) +
                 "); maps meant to be compared must share them: re-render with the same --limit")
    same = len({x["level"] for x in runs}) == 1 and len({tuple(sorted(x["atoms"])) for x in runs}) == 1
    e0, lim = min(x["e"] for x in runs), runs[0]["lim"]
    asp = max(x["img"].shape[0] / x["img"].shape[1] for x in runs)    # pad to one shape so titles line up
    for x in runs:
        h, w = x["img"].shape[:2]
        H, W = max(h, int(round(w * asp))), max(w, int(round(h / asp)))
        pad = np.ones((H, W, 3))
        pad[(H - h) // 2:(H - h) // 2 + h, (W - w) // 2:(W - w) // 2 + w] = x["img"]
        x["img"] = pad
    fig, axs = plt.subplots(1, len(runs), figsize=(5.2 * len(runs) + 1.0, 5.2 * asp + 1.1), dpi=200, squeeze=False)
    fig.subplots_adjust(left=0.01, right=0.9, top=0.84, bottom=0.02, wspace=0.04)
    for k, (ax, x) in enumerate(zip(axs[0], runs)):
        x["de"] = f"ΔE = {(x['e'] - e0) * 627.5095:+.2f} kcal/mol" if same else "ΔE n/a (different molecule or level)"
        ax.imshow(x["img"])
        ax.axis("off")
        ax.set_title(f"({chr(97 + k)}) {x['label']}", loc="left", fontsize=13, pad=30)
        ax.text(0, 1.01, f"{x['de']}  ·  {x['hb']} H-bond{'s' if x['hb'] != 1 else ''}\n"
                f"ESP {float(x['esp'][0]):+.3f} to {float(x['esp'][1]):+.3f} a.u.", transform=ax.transAxes,
                ha="left", va="bottom", fontsize=10, color="#333333")
    cb = fig.colorbar(ScalarMappable(Normalize(-lim, lim), colormap(style)), cax=fig.add_axes([0.92, 0.12, 0.015, 0.62]))
    cb.set_label("ESP (a.u.)")
    out = Path(out)
    fig.savefig(out, bbox_inches="tight", pad_inches=0.15, facecolor="white")
    plt.close(fig)
    txt = [f"{out.name}: ESP maps, {style} colour scale -{lim} to +{lim} a.u. (red = negative, blue = positive), "
           f"same limits in every panel; ΔE relative to the lowest-energy panel" + ("" if same else " (not given: runs differ)")]
    txt += [f"({chr(97 + k)}) {x['label']} [{n}]: {x['de']}; {x['hb']} H-bond(s); {x['cap']}" for k, (x, n) in enumerate(zip(runs, names))]
    out.with_suffix(".txt").write_text("\n".join(txt) + "\n", encoding="utf-8")
    print(f"wrote {out} and {out.with_suffix('.txt')}")


def render(name, style="both", limit=None, view=None, root="runs", extrema=False, hbond_lines=False):
    import pyvista as pv
    out = Path(root) / name
    sym, xyz = read_xyz(out / "mol.xyz")
    surf = pv.read(out / "surf.vtk")

    col = COLORS
    bonds = bond_list(sym, xyz)
    ev = np.linalg.svd(xyz - xyz.mean(0))[2]   # principal axes: long, middle, thin

    def molecule(p):
        for s, r in zip(sym, xyz):
            p.add_mesh(pv.Sphere(radius=0.17 if s == "H" else 0.30, center=r,theta_resolution=40, phi_resolution=40),
                       color=col.get(s, "#ff69b4"), smooth_shading=True, specular=0.8, specular_power=40)
        for i, j, order in bonds:
            off = stick_offsets(xyz, bonds, i, j, order, ev[2])
            mid = (xyz[i] + xyz[j]) / 2   # two-tone bond, like GaussView
            for o in off:
                for a, b, s in ((xyz[i], mid, sym[i]), (mid, xyz[j], sym[j])):
                    p.add_mesh(pv.Cylinder(center=(a + b) / 2 + o, direction=b - a, radius=0.08 if order == 1 else 0.05,
                                           height=np.linalg.norm(b - a), resolution=30),
                               color=col.get(s, "#ff69b4"), smooth_shading=True, specular=0.6)
        for h, a in hb:                       # dashed H-bond: 0.12 Å dashes with 0.08 Å gaps
            d = xyz[a] - xyz[h]
            n = int(np.linalg.norm(d) / 0.2)
            for t in range(n):
                c = xyz[h] + d * (t + 0.3) / n
                p.add_mesh(pv.Cylinder(center=c, direction=d, radius=0.035, height=0.12, resolution=16), color="#555555")

    hb = hbond_pairs(mol_from_xyz(sym, xyz), xyz) if hbond_lines else []
    auto = isinstance(view, str) and view == "auto"
    if auto:
        view = auto_view(surf, sym, xyz)
        print("--view auto picked --view=" + ",".join(f"{c:.2f}" for c in view))
    ex = esp_extrema(surf, sym, xyz) if extrema else []
    cam = np.asarray(view, float) if view is not None else ev[2]   # camera direction of the ESP pictures (tilt 0)
    cam = cam / np.linalg.norm(cam)
    nrm = surf.compute_normals(point_normals=True, cell_normals=False).point_data["Normals"] if ex else None
    for e in ex:   # on the back if the surface lies between the point and the camera
        n = nrm[surf.find_closest_point(e["point"])]
        n = n if n @ (e["point"] - xyz.mean(0)) > 0 else -n   # outward
        start = e["point"] + 0.3 * n          # off the surface first: a ray from a rim point would graze it
        e["front"] = not len(surf.ray_trace(start, start + 100 * cam)[0])
        e["view"] = ",".join(f"{c:.2f}" for c in (e["point"] - xyz.mean(0)) / np.linalg.norm(e["point"] - xyz.mean(0)))

    def markers(p):   # a label drawn over the molecule for a back-side point would sit on the wrong atoms
        front = [e for e in ex if e["front"]]
        for e in front:
            p.add_mesh(pv.Sphere(radius=0.15, center=e["point"]), color="#222222")
        if front:
            p.add_point_labels(np.array([e["point"] for e in front]), [f"{e['value']:+.3f}" for e in front], font_size=22,
                               point_size=1, shape_opacity=0.7, always_visible=True, show_points=False)
        back = [f"V_s,{e['kind']} {e['value']:+.3f} a.u. at {e['atom']}: back side, not visible" for e in ex if not e["front"]]
        if back:
            p.add_text("\n".join(back), position=(30, 25), font_size=14, color="black")   # pixels: keep off the edge

    def aim(p, tilt=0.0):
        if view is None:                      # look down the thinnest axis, long axis horizontal
            p.view_vector(ev[2] + tilt * ev[1], viewup=ev[1])
        else:
            v = np.asarray(view, float)
            p.view_vector(v, viewup=ev[1] if abs(v @ ev[1]) < 0.9 * np.linalg.norm(v) else ev[0])
        p.camera.zoom(1.5)

    def front_layer(mesh):
        """Only the triangles nearest the camera. Through a 70 % surface, a lobe hidden behind another shows its
        edge-on rim as dark ribbons (worst on folded shapes, off-axis views). Visible triangles are found by
        drawing triangle ids as flat colours, without anti-aliasing, at twice the picture size."""
        ids = np.arange(mesh.n_cells)
        m = mesh.copy()
        m.cell_data["id"] = np.c_[ids & 255, ids >> 8 & 255, ids >> 16 & 255].astype(np.uint8)
        p = pv.Plotter(off_screen=True, window_size=(3200, 2000))
        p.disable_anti_aliasing()
        p.set_background("white")             # 0xffffff is never a triangle id
        p.add_mesh(m, scalars="id", rgb=True, lighting=False, preference="cell")
        aim(p)
        img = p.screenshot(return_img=True).astype(np.int64)
        p.close()
        code = img[..., 0] + (img[..., 1] << 8) + (img[..., 2] << 16)
        return mesh.extract_cells(np.unique(code[code < mesh.n_cells])).extract_surface(algorithm="dataset_surface")

    def shoot(path, add_surface=None, tilt=0.0):
        p = pv.Plotter(off_screen=True, window_size=(1600, 1000))
        p.set_background("white")
        p.enable_depth_peeling(20)            # without it the transparent surface bands
        p.enable_anti_aliasing("ssaa")
        molecule(p)
        if add_surface:
            add_surface(p)
        aim(p, tilt)
        p.screenshot(path)
        p.close()

    cmaps = {st: colormap(st) for st in ("rainbow", "rwb")}
    shoot(out / "ball.png")
    styles = ["rainbow", "rwb"] if style == "both" else [style]
    lims = dict(LIMITS)
    if limit is not None:                     # one value for both styles, or [rainbow, rwb]
        lv = list(limit) if isinstance(limit, (list, tuple)) else [limit]
        lims.update(rainbow=lv[0], rwb=lv[-1])
    cap = out / "caption.txt"                 # keep the line of a style rendered earlier and not redone now
    notes = [l for l in (cap.read_text(encoding="utf-8").splitlines() if cap.exists() else [])
             if re.match(r"(rainbow|rwb)_esp\.png:", l) and l.split("_")[0] not in styles and (out / l.split(":")[0]).exists()]
    front = front_layer(surf)                 # same camera for every ESP style
    if auto:
        notes.append("view: --view auto picked --view=" + ",".join(f"{c:.2f}" for c in view))
    for st in styles:
        lim = lims[st]
        shoot(out / f"{st}_esp.png", lambda p: markers(p) or p.add_mesh(
            front, scalars="esp", cmap=cmaps[st], clim=(-lim, lim), opacity=0.7, smooth_shading=True, specular=0.3,
            scalar_bar_args=dict(title="ESP (a.u.)\n", fmt="%.3f", n_labels=5, color="black", vertical=True,
                                 position_x=0.88, position_y=0.2, width=0.05, height=0.6,
                                 title_font_size=28, label_font_size=24)))
        notes.append(f"{st}_esp.png: colour scale -{lim} to +{lim} a.u. ({st}; red = negative, blue = positive; "
                     f"values beyond the limits are shown at the end colours; only the surface layer facing the "
                     f"viewer is drawn)")
    for k in ("homo", "lumo"):
        if not (out / f"{k}.cube").exists():
            continue
        g = read_cube(out / f"{k}.cube")
        e = float(re.search(rf"{k.upper()}: (\S+) eV", (out / "method.txt").read_text(encoding="utf-8")).group(1))

        def lobes(p, g=g, label=f"{k.upper()} ({e:.2f} eV)".replace("-", "\u2212")):
            for v, c in zip((ORB_ISO, -ORB_ISO), ORB_COLORS):
                lobe = g.contour([v], scalars="rho")
                if lobe.n_points:
                    p.add_mesh(lobe.smooth_taubin(n_iter=30).compute_normals(), color=c, opacity=ORB_OPACITY,
                               smooth_shading=True, specular=0.3, culling="back")
            p.add_text(label, position="upper_left", font_size=20, color="black")
        shoot(out / f"{k}.png", lobes, tilt=0.6)   # ~30 deg tilt: pi lobes above/below a planar molecule both show
        notes.append(f"{k}.png: {k.upper()} isosurfaces at +/-{ORB_ISO} a.u. (orbital value); colours show the phase "
                     f"(green +, purple -), not ESP sign; "
                     f"default view tilted ~30 deg from the ESP view")
    for e in ex:
        notes.append(f"ESP {'minimum' if e['kind'] == 'min' else 'maximum'} on the surface (V_s,{e['kind']}): "
                     f"{e['value']:+.4f} a.u., nearest atom {e['atom']}; "
                     + ("marked on the map" if e["front"] else f"on the back side, listed in the corner (--view={e['view']} faces it)"))
        if not e["front"]:
            print(f"V_s,{e['kind']} is on the back side; --view={e['view']} faces it")
    if hbond_lines:
        notes.append("H-bonds drawn: " + (", ".join(f"{sym[h]}{h + 1}···{sym[a]}{a + 1} {np.linalg.norm(xyz[h] - xyz[a]):.2f} Å"
                                                for h, a in hb) or "none") + f" (H on N/O, acceptor > 3 bonds away, < {HB_CUT} Å)")
    cap.write_text((out / "method.txt").read_text(encoding="utf-8") + "\n".join(notes) +
                   f"\nrendering: PyVista {pv.__version__}, VTK {'.'.join(map(str, pv.vtk_version_info))}\n", encoding="utf-8")
    print(f"wrote PNGs to {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("calc", help="geometry + DFT + ESP surface (minutes)")
    c.add_argument("input", help="SMILES string or .xyz file")
    c.add_argument("--name", required=True, help="run name; results go to runs/<name>/")
    c.add_argument("--charge", type=int, default=0, help="total charge (.xyz input only; SMILES carries its own)")
    c.add_argument("--opt", action="store_true", help="DFT geometry optimisation first (pip install geometric; 30-60 min)")
    c.add_argument("--force", action="store_true", help="recompute even if results exist")
    c.add_argument("--no-hbond", action="store_true", help="take the lowest-MMFF conformer with no intramolecular H-bond")
    c.add_argument("--d3", action="store_true", help="add D3(BJ) dispersion (pip install pyscf-dispersion); changes energies, not the ESP")
    c.add_argument("--solvent", choices=sorted(SOLVENTS), help="implicit solvent (IEF-PCM) for SCF, --opt and ESP (slower)")
    c.add_argument("--rerank", type=int, default=0, metavar="N",
                   help="DFT single points on the N lowest distinct MMFF conformers, continue with the lowest (PAM3: ~2 min each in gas phase)")
    c.add_argument("--orbitals", action="store_true", help="also write HOMO/LUMO cubes + energies; render then draws homo/lumo.png")
    c.add_argument("--opt-conv", choices=sorted(OPT_CONV), default="gau",
                   help="--opt convergence: gau (geomeTRIC default) or qchem (gradient AND energy-or-displacement; for floppy chains)")
    r = sub.add_parser("render", help="PNGs from an existing run (seconds)")
    r.add_argument("name")
    r.add_argument("--style", choices=["rwb", "rainbow", "both"], default="both")
    r.add_argument("--limit", type=lambda s: [float(x) for x in s.split(",")],
                   help="colour limit in a.u.: one value for both styles, or rainbow,rwb e.g. 0.10,0.05 (default 0.06,0.03)")
    r.add_argument("--view", type=lambda s: s if s == "auto" else [float(x) for x in s.split(",")],
                   help="camera direction, e.g. --view=0,0,1, or auto (scores 600 directions: extrema, C=O, H-bonds, chain flat); "
                        "default: along the thinnest molecular axis")
    r.add_argument("--extrema", action="store_true", help="mark the most negative/positive ESP point (V_s,min/max) with values")
    r.add_argument("--hbonds", action="store_true", help="draw intramolecular H-bonds as dashed lines")
    q = sub.add_parser("panel", help="rendered ESP maps side by side, one colour bar (seconds)")
    q.add_argument("names", nargs="+", help="run names, already rendered with the same --limit")
    q.add_argument("--labels", type=lambda s: s.split(","), help="panel titles, comma-separated, e.g. folded,extended")
    q.add_argument("--style", choices=["rwb", "rainbow"], default="rainbow")
    q.add_argument("--out", default="runs/panel.png")
    a = ap.parse_args()
    if a.cmd == "calc":
        calc(a.input, a.name, a.charge, a.opt, a.force, a.no_hbond, d3=a.d3, solvent=a.solvent, rerank=a.rerank,
             orbitals=a.orbitals, opt_conv=a.opt_conv)
    elif a.cmd == "panel":
        panel(a.names, a.labels, a.style, a.out)
    else:
        render(a.name, a.style, a.limit, a.view, extrema=a.extrema, hbond_lines=a.hbonds)
