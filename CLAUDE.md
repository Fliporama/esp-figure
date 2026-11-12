# esp-figure — project handoff

Read this first. It carries everything decided in an earlier chat so a new
session (you, or Claude Code in VS Code) doesn't start from zero.

## Goal

Make publication-quality molecule figures like the ones made with
Gaussian + GaussView, using only free tools, as **one repeatable command**:

1. Ball-and-stick structure (glossy spheres, two-tone bonds)
2. Electrostatic potential (ESP) mapped onto the electron-density surface,
   in two colour styles: red-white-blue and rainbow

First target molecule: polyacrylamide (PAM) oligomer.

## Status

- Prototype works (three scripts, see "Prototype" below). Output was checked
  visually and looks close to GaussView quality.
- `esp_figure.py` + `test_water.py` built to the design below (approved
  2026-11-10). Water test passes; `runs/pam3/` has draft (MMFF) figures,
  checked visually. Target molecule: the H-capped PAM trimer. Default figure
  style (1600×1000 PNG); no journal requirements.
- Conformer search added (lowest MMFF of 50). For PAM3 the MMFF winner is
  folded with 1 inter-amide N–H···O H-bond (the earlier "4" counted each
  amide H against its own C=O, ~2.45 Å by geometry; `hbonds()` now excludes
  acceptors ≤3 bonds away).
- Conformer comparison done 2026-11-11 (B3LYP/6-31G(d), gas phase, no D3):
  `runs/pam3_opt` (folded, 2 H-bonds after opt, E −782.486537) vs.
  `runs/pam3_ext_opt` (`--no-hbond` start, 1 H-bond formed during opt,
  E −782.477763): folded lower by 5.5 kcal/mol. ESP −0.066/+0.078 vs.
  −0.070/+0.075 a.u. Both runs used an unspecified-stereo SMILES (see
  IMPROVEMENTS.md §1); treat as a pilot. Open figure issues: jagged
  stripes on parts of the surface in both opt renders; ext needs a `--view`
  (left amide points at the camera).
- Gas-phase syndiotactic control done 2026-11-11 (B3LYP/6-31G(d), no D3, no solvent):
  `runs/pam3s_gas_fold` E -782.485784, 1 H-bond (H26...O16 2.00 A), ESP -0.071/+0.082;
  `runs/pam3s_gas_ext` E -782.475815, 0 H-bonds (stayed open), ESP -0.066/+0.069.
  Folded lower by 6.3 kcal/mol (pilot, unspecified stereo: 5.5).
- **Folded vs. extended in water done 2026-11-12** (B3LYP-D3(BJ)/6-31G(d) + IEF-PCM water,
  geometry optimised in PCM; syndiotactic PAM3):
  `runs/pam3s_fold` (`--rerank 5`; DFT confirmed the MMFF #1 pick, next +1.3 kcal/mol)
  E −782.58249894, 1 H-bond (H26···O16 1.95 Å), ESP −0.0864/+0.1021;
  `runs/pam3s_ext_sp` E −782.57747593, 0 H-bonds, ESP −0.0891/+0.1076.
  **Folded lower by 3.15 kcal/mol** (D3 −1.06, SCF+solvation −2.09) vs. 6.3 in gas without
  D3: solvent roughly halves the folded preference, but folded stays lower. Energies, not
  free energies (no entropy, implicit solvent can't H-bond the amides): one conformer each,
  not "PAM3 folds in water".
  Ext optimisation was **stopped at step 58** (`--no-hbond` start, 6 h): energy (<1e-6 Eh/step)
  and gradients (rms 3.7e-5) converged, displacement criterion not met (floppy torsions creep).
  `pam3s_ext_sp` is a single point on that last frame (`runs/pam3s_ext/last_frame.xyz`);
  its method.txt said "geometry not optimised in solvent", wrong for this geometry: corrected
  by hand 2026-11-12 (originals kept in brackets). `pam3s_{fold,ext}_orb` still carry the
  wrong line (same `.xyz` single-point issue, backlog). Figures rendered at ±0.10 rainbow / ±0.05 rwb
  (`--limit 0.10,0.05`). Ext default view is usable; fold is rendered at
  `--view=0.56,-0.52,-0.64` (both extrema, H-bond and one C=O double visible; `--view auto` picks the
  same); dark seams fixed. Comparison panels: `runs/pam3s_panel_{rainbow,rwb}.png` (+ .txt caption).
  HOMO/LUMO (single points with `--orbitals`, `runs/pam3s_{fold,ext}_orb`): fold −6.75/+0.53 eV,
  ext −6.71/+0.61 eV; positive LUMOs in 6-31G(d) are diffuse and say little.
- Night runner (autonomous overnight work) designed and planned:
  `docs/superpowers/specs/2026-11-11-night-runner-design.md`,
  `docs/superpowers/plans/2026-11-11-night-runner.md`; merged into main
  2026-11-11 (dry runs + permission probes passed). Before the first real
  night: sanity entries for week-1 items in `night/reference.json`.
- **Week-1 sanity checks built 2026-11-11** (table approved as is;
  `pyscf-dispersion` 1.7.0 installed). One script per row in `night/sanity/`
  (locked, listed under `sanity` in `night/reference.json`); each docstring is
  the interface contract the night agent must implement (`PAM3`, `COLORS`,
  `calc(d3=, solvent=, rerank=)`, `opt_traj.xyz`, method.txt lines). Exit 0
  pass / 1 fail / 77 not built. `night/check.py --sanity` runs them;
  `night.ps1` runs it after phase 1, before the queue → `night/sanity_result.json`.
  Limits checked against real numbers: D3 −41.6/−41.1 kcal/mol (folded
  favoured by 0.6), water ΔG_solv −6.5 kcal/mol, formamide restart dE 4e-8 Eh
  in 6 vs 7 steps; PAM3 PCM ESP extremes +15–20 %, fold−ext −5.5 → −2.4
  kcal/mol. Syndiotactic PAM3 (verified by `stereo.py`):
  `C[C@@H](C(N)=O)C[C@H](C(N)=O)C[C@H](C)C(N)=O`.
- Built in the day session 2026-11-11 (sanity checks pass, regression unchanged):
  stereo (`esp_figure.PAM3`; caption says syndiotactic), guards (unsupported
  element / odd electrons / unspecified stereo → clean exit before any
  compute; supported = MMFF94 ∩ 6-31G(d): H C N O F Si P S Cl Br), `COLORS`
  table, D3 (`--d3`, off by default; method.txt adds "dispersion energy"). **Unspecified-stereo SMILES (e.g. the old PAM3 one in examples
  below) are now refused.** Decisions for D3/solvent/re-ranking/redo jobs
  are in `night/STATE.md` Answers.
- **Week-2 sanity checks built 2026-11-11** (table approved as is): `freq`,
  `orbitals`, `extrema`, `bonds`, `uks` in `night/sanity/`. Each was tested
  against a throwaway reference implementation (all pass) and against one
  deliberate bug each (all caught). References: water freqs 1710.7/3720.5/
  3844.3 cm⁻¹ (±5), planar NH₃ 1 imaginary; water HOMO = O lone pair
  (85 %); CH₃ UKS ⟨S²⟩ 0.754, ESP −0.016..+0.019. `extrema`/`bonds` follow
  the interface built in d4afae9 (`esp_extrema`, `hbond_pairs`); extrema
  passes, bonds skips (77) until `bond_list` (double sticks) exists. A PAM3
  frequency run (~1 h) is a queue job, not a sanity check.
- **Night 2 + day session 2026-11-12** (merged, all sanity/regression pass): night built
  `--solvent water`, restart (`opt_traj.xyz`), `--rerank N`; helpers built double sticks
  (`bond_list`; `bonds` now passes) and `--orbitals` (HOMO/LUMO cubes, energies, homo/lumo.png,
  lobes at opacity 0.3 so atom colours stay readable). Day fixes: restart no longer writes the
  restart point twice; `night.ps1` copies `runs/<name>` of queued jobs into the worktree so
  `--opt` resumes across nights; back-side ESP extrema are listed in a corner note (not
  labelled through the molecule) with a `--view` hint; `--limit rainbow,rwb`; caption keeps
  the other style's line. Open for the user: 4 h per-job cap (`-JobTimeoutSec 14400`) too
  short for cold D3+PCM PAM3 opts; re-rank sanity "distinct" threshold 1e-7 Eh → 1e-4.
## This machine

Ubuntu 26.04 in WSL, installed with `--no-launch`, so **root only, no Linux
user**. Venv at `/root/esp-venv` (Python 3.14, PySCF 2.15, geometric
included). Run from PowerShell without `bash -c` (SMILES parentheses break
the quoting):

```powershell
wsl -d Ubuntu -u root --cd "/mnt/c/dev/molcule visualizer" -e /root/esp-venv/bin/python esp_figure.py render pam3
```

## Method (keep these defaults unless the user changes them)

| Step | Choice | Why |
|---|---|---|
| Geometry | RDKit: 50 conformers, keep lowest MMFF energy (draft) | Fast. **Draft only** — final figures need DFT optimisation (see TODO) |
| Electronic structure | PySCF, B3LYP/6-31G(d), density fitting | Common level of theory in papers; ~2 min for 37 atoms on a laptop-class CPU |
| Surface | Electron density isosurface ρ = 0.001 a.u. | Standard vdW-like surface for ESP maps |
| ESP | Computed **only at surface vertices** | See pitfalls |
| Rendering | PyVista offscreen, 1600×1000, SSAA | Close match to GaussView look |

Observed ESP range for the PAM trimer: −0.065 to +0.071 a.u. in the gas phase →
colour limits ±0.06 (rainbow) and ±0.03 (red-white-blue) are sensible. In PCM water the
extremes grow ~20–25 % (−0.089 to +0.108): use ±0.10 / ±0.05 (`--limit 0.10,0.05`).

## Rules for figures

- **Red = negative ESP, blue = positive, in every style.** The reference
  figure we copied mixed conventions between panels; never do that.
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
   ids rendered as flat colours, no anti-aliasing, 2× size; a one-ring
   neighbour grow made jagged overlaps, so none). Mesh, winding and normals
   were checked and are fine (2026-11-12). Opacity 0.7 keeps the colours as
   strong as the old two-layer 0.55.
4. **Camera angle**: look along the molecule's thinnest principal axis, with
   the long axis horizontal (SVD of centred coordinates), so the chain lies flat.
5. Cube files are in **bohr**; PyVista scene is in Å. Convert with 0.529177.

## Model improvements

Backlog of science improvements (tacticity, solvent, D3, DFT re-ranking, …)
lives in `IMPROVEMENTS.md`. Read it before changing the method.

## Night runner (autonomous overnight work)

Before bed, from PowerShell in the repo (the default execution policy blocks
scripts, hence `-ExecutionPolicy Bypass`):

```powershell
powershell -ExecutionPolicy Bypass -File night\night.ps1            # stops everything by 08:00
powershell -ExecutionPolicy Bypass -File night\night.ps1 -StopBy 04:00
```

- Works in a separate worktree `C:\dev\esp-night` on branch `night/<date>`,
  pushes only that branch. Read `NIGHT_REPORT.md` on it in the morning.
- Merge: `powershell -ExecutionPolicy Bypass -File night\merge.ps1 <date>`.
  Reject: `git worktree remove --force C:\dev\esp-night; git branch -D night/<date>`.
- Answer the agent's questions under "Answers" in `night/STATE.md` on main.
- Fixed checks live in `night/reference.json` (agent can't edit). Add sanity
  entries for a roadmap item before the night that builds it.
- Laptop: plugged in, lid open or lid-close = do nothing.
- Spec/plan: `docs/superpowers/specs/2026-11-11-night-runner-design.md`,
  `docs/superpowers/plans/2026-11-11-night-runner.md`.

## Open questions for the user

- Exact structure for the final figures (end groups, ester end, crosslinker)?
- Do figures need to match a journal or report style (size, font, DPI)?

## Working preferences

- Explain reasoning so the user learns the method, not just the result.
- Be blunt about weaknesses in the science or the figures.
- Keep code minimal: standard library and the packages above first.
