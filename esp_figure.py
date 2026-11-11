#!/usr/bin/env python3
"""ESP figures in two stages: `calc` does the chemistry once, `render` makes PNGs in seconds.

  python esp_figure.py calc "C[C@@H](C(N)=O)C[C@H](C(N)=O)C[C@H](C)C(N)=O" --name pam3 [--charge 0] [--opt] [--d3] [--orbitals] [--force]
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
ORB_ISO = 0.02   # orbital isovalue (a.u.) for the HOMO/LUMO pictures, a common GaussView-like choice
ORB_COLORS = ("#2e8b57", "#8e44ad")   # +/- phase: green/purple, so no one reads them as ESP red/blue
ORB_OPACITY = 0.3   # lower than the ESP surface (0.7): lobes in front must not tint the atoms' element colours
CONFS = 50       # conformers tried in the MMFF conformer search (SMILES input only)
HB_CUT = 2.5     # Å; H···N/O closer than this (and >3 bonds apart) counts as an intramolecular H-bond
LEVEL = "B3LYP/6-31G(d)"
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


def geometry(spec, charge, no_hbond=False):
    """SMILES or .xyz -> symbols, coords (Å), charge, description, RDKit mol (None for .xyz)."""
    if spec.endswith(".xyz"):
        if no_hbond:
            sys.exit("--no-hbond needs SMILES input (it picks among conformers)")
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
    return (sym, m.GetConformer(cids[best]).GetPositions(), Chem.GetFormalCharge(m),
            ("syndiotactic H-capped PAM trimer, " if spec == PAM3 else "") + f"{how}, RDKit ETKDG + MMFF94 (draft)", m)


def calc(spec, name, charge=0, opt=False, force=False, no_hbond=False, root="runs", d3=False, orbitals=False):
    out = Path(root) / name
    log = out / "method.txt"
    level = "B3LYP-D3(BJ)/6-31G(d)" if d3 else LEVEL
    if log.exists() and not force:
        text = log.read_text(encoding="utf-8")
        first = text.splitlines()[0]
        if first != f"input: {spec}":
            sys.exit(f"{out} holds a different molecule ({first}). Use another --name, or --force.")
        if f"level of theory: {level}," not in text:
            sys.exit(f"{out} was computed at a different level of theory (not {level}). Use another --name, or --force.")
        if not orbitals or (out / "homo.cube").exists():
            print(f"{out} already computed (use --force to redo)")
            return out
    out.mkdir(parents=True, exist_ok=True)
    import pyscf, rdkit
    from pyscf import gto, dft, df
    from pyscf.tools import cubegen

    t0 = time.time()
    sym, xyz, charge, geo, rdm = geometry(spec, charge, no_hbond)
    mol = gto.M(atom=[(s, tuple(map(float, r))) for s, r in zip(sym, xyz)],
                charge=charge, basis="6-31g*", verbose=0)

    def scf(mol):
        mf = dft.RKS(mol).density_fit()
        mf.xc = "b3lyp"
        if d3:
            mf.disp = "d3bj"   # pip install pyscf-dispersion; post-SCF energy term, density and ESP unchanged
        mf.kernel()
        return mf

    mf = scf(mol)
    if opt:
        from pyscf.geomopt.geometric_solver import optimize   # pip install geometric
        mol = optimize(mf)
        mf = scf(mol)
        geo = f"{level} optimised geometry (geomeTRIC), started from {geo}"
    if not mf.converged:
        print("WARNING: SCF did not converge; results are not trustworthy", file=sys.stderr)
    dm = mf.make_rdm1()
    xyz = mol.atom_coords() * B2A
    (out / "mol.xyz").write_text(f"{len(sym)}\n{name}\n" + "".join(
        f"{s} {x:.6f} {y:.6f} {z:.6f}\n" for s, (x, y, z) in zip(sym, xyz)))

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

    log.write_text(f"""input: {spec}
name: {name}
charge: {charge}
atoms: {len(sym)}
geometry: {geo}
intramolecular H-bonds in final geometry (H···N/O < {HB_CUT} Å): {hbonds(rdm, xyz) if rdm else "n/a"}
level of theory: {level}, density fitting (PySCF default auxiliary basis); ESP integrals exact
SCF energy: {mf.e_tot:.8f} Eh (converged: {mf.converged}){disp}
surface: electron density isosurface rho = {ISO} a.u. (grid {GRID}^3, margin {MARGIN} bohr), {len(pts)} vertices
ESP range on surface: {V.min():.4f} to {V.max():.4f} a.u.
{orb}software: PySCF {pyscf.__version__}, RDKit {rdkit.__version__}, NumPy {np.__version__}
wall time: {time.time() - t0:.0f} s
caption: Electrostatic potential mapped onto the {ISO} a.u. electron-density isosurface, computed at the {level} level with PySCF {pyscf.__version__} ({geo}).
""")
    print(log.read_text())
    return out


def render(name, style="both", limit=None, view=None, root="runs", extrema=False, hbond_lines=False):
    import pyvista as pv
    from matplotlib.colors import LinearSegmentedColormap
    from rdkit import Chem
    out = Path(root) / name
    sym, xyz = read_xyz(out / "mol.xyz")
    surf = pv.read(out / "surf.vtk")

    col = COLORS
    rcov = [Chem.GetPeriodicTable().GetRcovalent(s) for s in sym]

    def molecule(p):
        for s, r in zip(sym, xyz):
            p.add_mesh(pv.Sphere(radius=0.17 if s == "H" else 0.30, center=r,theta_resolution=40, phi_resolution=40),
                       color=col.get(s, "#ff69b4"), smooth_shading=True, specular=0.8, specular_power=40)
        for i in range(len(sym)):
            for j in range(i + 1, len(sym)):
                if np.linalg.norm(xyz[i] - xyz[j]) < 1.25 * (rcov[i] + rcov[j]):
                    mid = (xyz[i] + xyz[j]) / 2   # two-tone bond, like GaussView
                    for a, b, s in ((xyz[i], mid, sym[i]), (mid, xyz[j], sym[j])):
                        p.add_mesh(pv.Cylinder(center=(a + b) / 2, direction=b - a, radius=0.08,
                                               height=np.linalg.norm(b - a), resolution=30),
                                   color=col.get(s, "#ff69b4"), smooth_shading=True, specular=0.6)
        for h, a in hb:                       # dashed H-bond: 0.12 Å dashes with 0.08 Å gaps
            d = xyz[a] - xyz[h]
            n = int(np.linalg.norm(d) / 0.2)
            for t in range(n):
                c = xyz[h] + d * (t + 0.3) / n
                p.add_mesh(pv.Cylinder(center=c, direction=d, radius=0.035, height=0.12, resolution=16), color="#555555")

    hb = hbond_pairs(mol_from_xyz(sym, xyz), xyz) if hbond_lines else []
    ex = esp_extrema(surf, sym, xyz) if extrema else []

    def markers(p):
        for e in ex:
            p.add_mesh(pv.Sphere(radius=0.15, center=e["point"]), color="#222222")
        if ex:
            p.add_point_labels(np.array([e["point"] for e in ex]), [f"{e['value']:+.3f}" for e in ex], font_size=22,
                               point_size=1, shape_opacity=0.7, always_visible=True, show_points=False)

    ev = np.linalg.svd(xyz - xyz.mean(0))[2]   # principal axes: long, middle, thin

    def shoot(path, add_surface=None, tilt=0.0):
        p = pv.Plotter(off_screen=True, window_size=(1600, 1000))
        p.set_background("white")
        p.enable_depth_peeling(20)            # without it the transparent surface bands
        p.enable_anti_aliasing("ssaa")
        molecule(p)
        if add_surface:
            add_surface(p)
        if view is None:                      # look down the thinnest axis, long axis horizontal
            p.view_vector(ev[2] + tilt * ev[1], viewup=ev[1])
        else:
            v = np.asarray(view, float)
            p.view_vector(v, viewup=ev[1] if abs(v @ ev[1]) < 0.9 * np.linalg.norm(v) else ev[0])
        p.camera.zoom(1.5)
        p.screenshot(path)
        p.close()

    cmaps = {  # same convention in every style: red = negative, blue = positive
        "rainbow": LinearSegmentedColormap.from_list("gv", ["#ff0000", "#ffff00", "#00ff00", "#00ffff", "#0000ff"]),
        "rwb": LinearSegmentedColormap.from_list("rwb", ["#e8413a", "#ffffff", "#3a4fe8"]),
    }
    shoot(out / "ball.png")
    notes = []
    for st in (["rainbow", "rwb"] if style == "both" else [style]):
        lim = limit if limit is not None else LIMITS[st]
        shoot(out / f"{st}_esp.png", lambda p: markers(p) or p.add_mesh(
            surf, scalars="esp", cmap=cmaps[st], clim=(-lim, lim), opacity=0.7, smooth_shading=True, specular=0.3,
            culling="back",   # hide the far side: seen through the near side at grazing angles it shows as jagged stripes
            scalar_bar_args=dict(title="ESP (a.u.)\n", fmt="%.3f", n_labels=5, color="black", vertical=True,
                                 position_x=0.88, position_y=0.2, width=0.05, height=0.6,
                                 title_font_size=28, label_font_size=24)))
        notes.append(f"{st}_esp.png: colour scale -{lim} to +{lim} a.u. ({st}; red = negative, blue = positive; "
                     f"values beyond the limits are shown at the end colours)")
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
        notes.append(f"ESP {'minimum' if e['kind'] == 'min' else 'maximum'} on the surface (V_s,{e['kind']}, marked): "
                     f"{e['value']:+.4f} a.u., nearest atom {e['atom']}")
    if hbond_lines:
        notes.append("H-bonds drawn: " + (", ".join(f"{sym[h]}{h + 1}···{sym[a]}{a + 1} {np.linalg.norm(xyz[h] - xyz[a]):.2f} Å"
                                                for h, a in hb) or "none") + f" (H on N/O, acceptor > 3 bonds away, < {HB_CUT} Å)")
    (out / "caption.txt").write_text((out / "method.txt").read_text() + "\n".join(notes) +
                                     f"\nrendering: PyVista {pv.__version__}, VTK {'.'.join(map(str, pv.vtk_version_info))}\n")
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
    c.add_argument("--orbitals", action="store_true", help="also write HOMO/LUMO cubes + energies; render then draws homo/lumo.png")
    r = sub.add_parser("render", help="PNGs from an existing run (seconds)")
    r.add_argument("name")
    r.add_argument("--style", choices=["rwb", "rainbow", "both"], default="both")
    r.add_argument("--limit", type=float, help="colour limit in a.u. (default 0.06 rainbow, 0.03 rwb)")
    r.add_argument("--view", type=lambda s: [float(x) for x in s.split(",")],
                   help="camera direction, e.g. --view=0,0,1 (default: along the thinnest molecular axis)")
    r.add_argument("--extrema", action="store_true", help="mark the most negative/positive ESP point (V_s,min/max) with values")
    r.add_argument("--hbonds", action="store_true", help="draw intramolecular H-bonds as dashed lines")
    a = ap.parse_args()
    if a.cmd == "calc":
        calc(a.input, a.name, a.charge, a.opt, a.force, a.no_hbond, d3=a.d3, orbitals=a.orbitals)
    else:
        render(a.name, a.style, a.limit, a.view, extrema=a.extrema, hbond_lines=a.hbonds)
