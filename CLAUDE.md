# esp-figure — project handoff

Read this first. It carries what was decided in earlier sessions so a new session doesn't start from zero.
The dated development log (2026-11-10 to 11-18) is in the git history of this file.

## Goal

Make publication-quality molecule figures like the ones made with
Gaussian + GaussView, using only free tools, as **one repeatable command**:

1. Ball-and-stick structure (glossy spheres, two-tone bonds)
2. Electrostatic potential (ESP) mapped onto the electron-density surface,
   in two colour styles: red-white-blue and rainbow

Target molecule: the H-capped **syndiotactic polyacrylamide trimer** (PAM3),
`C[C@@H](C(N)=O)C[C@H](C(N)=O)C[C@H](C)C(N)=O` (`esp_figure.PAM3`, checked by `tests/sanity/stereo.py`).
Figure style: the default 1600×1000 PNG; no journal requirements.

## Status (2026-11-18)

**Features** (`esp_figure.py calc | render | panel`; README lists every option):
- Input SMILES or `.xyz`. Guards refuse unsupported elements, odd electron counts (unless `--spin`) and
  unspecified stereo before any compute. Supported with SMILES: H C N O F Si P S Cl Br; Z > 36 via `.xyz`
  (def2-SVP + ECP mixed basis).
- Geometry: RDKit 50 conformers / MMFF; `--rerank N` (DFT single points), `--opt` (geomeTRIC, restart from
  `opt_traj.xyz`, `--opt-conv qchem` for floppy chains), `--no-hbond`.
- Level: B3LYP/6-31G(d) default; `--d3`, `--solvent water` (IEF-PCM), `--ref-level` (PBE0-D3(BJ)/6-311+G(d,p),
  SMD with solvent, for surface/ESP/analyses only).
- Analyses: `--freq` (+ `--ir`), `--orbitals`, `--charges mk|chelpg`, `--nci` (own code, `--nci-step`),
  `--igm` (IGMH via Multiwfn, env `MULTIWFN`), `--fukui`, `--spin` (UKS), `--uvvis` (**unvalidated**).
- Render: `--limit rainbow,rwb`, `--view x,y,z|auto`, `--extrema` (global) / `--extrema all` (every local
  extremum, Multiwfn-style; extrema.txt; only expected-sign ones drawn), `--hbonds`; `panel` for side-by-side maps.
  No specular on the ESP surface (a glint read as V ≈ 0). Solvent runs add a caption sentence on the convention
  (solute polarised by the continuum, continuum charges not mapped).

**Validation against a reference Gaussian 16 + Multiwfn calculation** (acrylic acid; raw files local in the
gitignored `ref/esp-20260212/`; `ref/validate_acrylic.{py,txt}`, `tests/test_reflevel.py`, `tests/test_extrema.py`):
- Same level, same geometry: surface ESP MAE 0.03 kcal/mol, extrema within 0.4 %, energy 0.15 kcal/mol, D3 identical.
- Whole pipeline from SMILES (`--opt --rerank 2 --d3 --solvent water --ref-level`, `runs/acrylic_full`): same
  conformer (RMSD 0.006 Å), same 6 maxima + 2 minima within 0.07 Å, all values within 2.6 %.
- Cheaper levels vs the reference (ESP extrema): default gas −22/−19 %, `--d3 --solvent water` −8/−9 %
  (IEF-PCM vs SMD −6/−5 %, basis −2/0 %, B3LYP 0/−3 %). Solvent dominates, not the basis.
- Acrylamide (reference extrema only): at the reference level on our geometry −59.73/+66.59 vs −59.86/+66.28 kcal/mol.

**PAM3 results** (syndiotactic; runs in `runs/`, not in git):
- Water + D3 (B3LYP-D3(BJ)/6-31G(d) + IEF-PCM, optimised in PCM): fold (`pam3s_fold`, 1 H-bond H26···O16 1.95 Å)
  vs ext (`pam3s_ext`, converged at step 59; single point `pam3s_ext_sp`): **dE −3.15 kcal/mol** (gas, no D3: −6.3).
  ESP fold −0.0864/+0.1021, ext −0.0891/+0.1076 a.u. Both 0 imaginary frequencies.
- Free energies (`runs/pam3s_thermo.{py,txt}`, 298 K): **dG −1.29 (RRHO) / −1.62 (quasi-RRHO) kcal/mol**. Within
  the error of one conformer each, soft modes and implicit solvent: call it "comparable", not "folded preferred".
- **`--ref-level` (PBE0-D3(BJ)/6-311+G(d,p) + SMD single points on the PCM geometries, 2026-11-18):**
  `pam3s_fold_ref` (1 h 50 min) vs `pam3s_ext_ref` (1 h 23 min): **dE −0.14 kcal/mol** (D3 −0.52), vs −3.15 at
  B3LYP/PCM. With the B3LYP thermal corrections (+1.86 RRHO / +1.53 qRRHO) dG ≈ +1.7 / +1.4: the sign flips,
  extended slightly lower. Trend gas −6.3 → water+D3 −3.15 → ref −0.14: the folded preference shrinks as the method
  improves (likely 6-31G(d) BSSE over-binding the H-bond, SMD vs PCM, smaller PBE0 D3). Single points, one conformer
  each: say "no measurable preference", and do M1 before any claim. ESP fold −0.0944/+0.1117, ext −0.0980/+0.1212
  a.u. (9–13 % stronger than B3LYP/PCM, same sites): figures comparing both at this level need ≥ `--limit 0.125,0.0625`.
- Figures: `--limit 0.10,0.05`; fold at `--view=0.56,-0.52,-0.64` (`--view auto` picks the same); panels
  `runs/pam3s_panel_{rainbow,rwb}.png`. HOMO/LUMO fold −6.75/+0.53, ext −6.71/+0.61 eV. NCI: H26···O16 lobe
  −0.030 a.u. (`runs/pam3s_fold_nci_fine`, `--view=0.02,0.87,0.50 --hbonds`). Fukui in water: f− top carbonyl
  O4/O9, f+ top C13.
- Don't use `runs/pam3_uvvis`: 10 states cut off the amide π→π* (~190 nm), its "peak" is an artefact.

**Tests** (`tests/`; README has the commands): `tests/test_*.py` per feature, `tests/sanity/*.py` = 19 locked
checks against reference numbers (each docstring is the contract; exit 0 pass / 1 fail / 77 skip), baselines in
`tests/data/`. `python tests/run_all.py [words]` runs all or matching ones. Tests import `tests/_root.py` to find
`esp_figure`. Before committing a change, run the tests that touch it (cap threads with `OMP_NUM_THREADS` if a
long calculation is running).

**Next** (`IMPROVEMENTS.md` has the full open list): render PAM3 fold/ext at `--ref-level`;
small items S5–S10; major M1 (conformer ensembles, needed before any fold/ext claim), M2 (GPU, lab computer;
specs pending: OS, cores, RAM, disk, NVIDIA GPU), M6 (package + Colab notebook). Stearyl acrylate: gas phase only,
hand-built all-trans `.xyz`, too big for `--freq` here; butyl acrylate is the cheap head-group model.

## This machine

Ubuntu 26.04 in WSL, installed with `--no-launch`, so **root only, no Linux
user**. Venv at `/root/esp-venv` (Python 3.14, PySCF 2.15, geometric
included). Run from PowerShell without `bash -c` (SMILES parentheses break
the quoting):

```powershell
wsl -d Ubuntu -u root --cd "/mnt/c/dev/molcule visualizer" -e /root/esp-venv/bin/python esp_figure.py render pam3
```

Multiwfn 2026.11.13 (noGUI) in `/root/multiwfn`; how to script it: `docs/multiwfn-nci-check.md`.
15 GB RAM, 14 cores: one big PySCF job at a time.

## Method (keep these defaults unless the user changes them)

| Step | Choice | Why |
|---|---|---|
| Geometry | RDKit: 50 conformers, keep lowest MMFF energy (draft) | Fast. **Draft only**: final figures need `--opt` |
| Electronic structure | PySCF, B3LYP/6-31G(d), density fitting | Common level of theory in papers; ~2 min for 37 atoms on a laptop-class CPU |
| Surface | Electron density isosurface ρ = 0.001 a.u. | Standard vdW-like surface for ESP maps (as Multiwfn/GaussView) |
| ESP | Computed **only at surface vertices** | See pitfalls |
| Rendering | PyVista offscreen, 1600×1000, SSAA | Close match to GaussView look |

Observed ESP range for the PAM trimer: −0.065 to +0.071 a.u. in the gas phase →
colour limits ±0.06 (rainbow) and ±0.03 (red-white-blue) are sensible. In PCM water the
extremes grow ~20–25 % (−0.089 to +0.108): use ±0.10 / ±0.05 (`--limit 0.10,0.05`).

## Rules for figures

- **Red = negative ESP, blue = positive, in every style.** Never mix conventions between panels
  (`tests/test_colormaps.py` checks rendered pixels).
- Always draw a colour bar labelled in **a.u.** (lowercase), with limits shown.
- Use the same colour limits for any molecules meant to be compared.
- Every run writes the method (level of theory, isovalue, limits, software
  versions) to a text file so it can go straight into a figure caption.

## Pitfalls already hit (don't repeat)

1. **Full-grid ESP is too slow.** `pyscf.tools.cubegen.mep` on an 80³ grid ran
   >10 min. Instead: compute density cube → extract isosurface → ESP only at
   its ~25k vertices (~1 min), as `calc()` in `esp_figure.py` does.
2. **Grid box too tight → holes in the surface** near carbonyl oxygens.
   Use `cubegen.density(..., margin=6.0)` (bohr) or more; default is too small.
3. **Transparent surface shows dark banding** unless depth peeling is on:
   `plotter.enable_depth_peeling(20)`. Back-face culling is not enough on
   compact (folded) shapes: a lobe hidden behind another also faces the camera,
   and its edge-on rim shows through as dark ribbons, worst at off-axis views.
   `render()` draws only the layer nearest the camera (`front_layer`: triangle
   ids rendered as flat colours, no anti-aliasing, 2× size). Visibility is per
   triangle, so a far triangle with one visible pixel pokes out under a near
   lobe's outline as two stacked layers: dark sawtooth seams one triangle wide
   (fixed 2026-11-18): the mesh is split 16-fold first (seams ~1 px), then
   closed (grow one ring, shrink back) to fill pinholes from tiny edge-on
   triangles. A plain grow without the shrink leaves a 3–5 px dark fringe. Mesh, winding and normals
   were checked and are fine (2026-11-12). Opacity 0.7 keeps the colours as
   strong as the old two-layer 0.55.
4. **Camera angle**: look along the molecule's thinnest principal axis, with
   the long axis horizontal (SVD of centred coordinates), so the chain lies flat.
5. Cube files are in **bohr**; PyVista scene is in Å. Convert with 0.529177.
6. **`/tmp` in this WSL is a 7.7 GB tmpfs (RAM).** PySCF's analytic Hessian (`--freq`) for PAM3 writes
   > 9 GB of scratch there and died with "No space left on device" (2026-11-13). Fixed in code: `calc()`
   puts PySCF scratch in `~/.cache/esp-scratch` unless `PYSCF_TMPDIR` is set (6794f8a). Direct PySCF calls
   outside `calc()` (e.g. the sanity scripts' reference runs) still use the global setting:
   `/root/.pyscf_conf.py` sets `TMPDIR = '/var/tmp'` on this machine (not in the repo).
7. **"Intramolecular H-bond" must exclude an amide H's own C=O**: syn H–N–C=O puts that H ~2.45 Å from its O by
   geometry alone; `hbonds()` requires the acceptor > 3 bonds away.
8. **Local ESP extrema: prominence doesn't separate meaningful from trivial ones.** PAM3's carbonyl O minima stand
   out by only 1.2–1.8 kcal/mol, like the trivial ones; the sign does (minimum V > 0, maximum V < 0 = not drawn).
9. **Planar molecules**: coordinates like `-9e-06` written in scientific notation break RDKit's XYZ reader;
   `mol_from_xyz` writes fixed-point.

## Open work

Open improvements, by size, and publication ideas: `IMPROVEMENTS.md`. Read it before changing the method.
Related free tools and what was taken from them: `docs/related-work.md`.

## Working preferences

- Explain reasoning so the user learns the method, not just the result.
- Be blunt about weaknesses in the science or the figures.
- Keep code minimal: standard library and the packages above first.
