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
- Night runner (autonomous overnight work) designed and planned:
  `docs/superpowers/specs/2026-11-11-night-runner-design.md`,
  `docs/superpowers/plans/2026-11-11-night-runner.md`; merged into main
  2026-11-11 (dry runs + permission probes passed). Before the first real
  night: sanity entries for week-1 items in `night/reference.json`.

## This machine

Ubuntu 26.04 in WSL, installed with `--no-launch`, so **root only, no Linux
user**. Venv at `/root/esp-venv` (Python 3.14, PySCF 2.15, geometric
included). Run from PowerShell without `bash -c` (SMILES parentheses break
the quoting):

```powershell
wsl -d Ubuntu -u root --cd "/mnt/c/dev/molcule visualizer" -e /root/esp-venv/bin/python esp_figure.py render pam3
```

## Setup

PySCF does **not** run natively on Windows. On Windows:

1. PowerShell (admin): `wsl --install` → reboot → set up Ubuntu user.
2. VS Code: install the **WSL** extension, then "WSL: Connect to WSL" and open
   the repo folder from inside WSL (`code .` from the Ubuntu terminal works).
3. In the WSL terminal:

```bash
sudo apt update && sudo apt install -y python3-venv python3-pip libgl1 libxrender1
python3 -m venv .venv && source .venv/bin/activate
pip install --prefer-binary pyscf rdkit pyvista vtk matplotlib pillow
```

Offscreen rendering works without a display (a harmless
`bad X server connection` warning may print).

## Method (keep these defaults unless the user changes them)

| Step | Choice | Why |
|---|---|---|
| Geometry | RDKit: 50 conformers, keep lowest MMFF energy (draft) | Fast. **Draft only** — final figures need DFT optimisation (see TODO) |
| Electronic structure | PySCF, B3LYP/6-31G(d), density fitting | Common level of theory in papers; ~2 min for 37 atoms on a laptop-class CPU |
| Surface | Electron density isosurface ρ = 0.001 a.u. | Standard vdW-like surface for ESP maps |
| ESP | Computed **only at surface vertices** | See pitfalls |
| Rendering | PyVista offscreen, 1600×1000, SSAA | Close match to GaussView look |

Observed ESP range for the PAM trimer: −0.065 to +0.071 a.u. → colour limits
±0.06 (rainbow) and ±0.03 (red-white-blue) are sensible.

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
   its ~25k vertices (~1 min). Snippet below.
2. **Grid box too tight → holes in the surface** near carbonyl oxygens.
   Use `cubegen.density(..., margin=6.0)` (bohr) or more; default is too small.
3. **Transparent surface shows dark banding** unless depth peeling is on:
   `plotter.enable_depth_peeling(20)`.
4. **Camera angle**: look along the molecule's thinnest principal axis, with
   the long axis horizontal (SVD of centred coordinates), so the chain lies flat.
5. Cube files are in **bohr**; PyVista scene is in Å. Convert with 0.529177.

Core ESP-on-surface snippet (works):

```python
from pyscf import gto, df
pts = surf.points / 0.529177            # Å -> bohr
V = np.zeros(len(pts))
for i in range(0, len(pts), 1500):      # chunk to limit memory
    p = pts[i:i+1500]
    V[i:i+1500] = -np.einsum("ijp,ij->p",
        df.incore.aux_e2(mol, gto.fakemol_for_charges(p)), dm)   # electrons
for z, R in zip(mol.atom_charges(), mol.atom_coords()):
    V += z / np.linalg.norm(pts - R, axis=1)                     # nuclei
```

## Prototype files

Copy these into `prototype/` (they were sent as chat attachments):

- `calc.py` — SMILES → MMFF geometry → B3LYP SCF → density cube → isosurface
  → ESP at vertices → `surf.vtk`
- `render_lib.py` — `read_cube()` helper
- `render.py` — ball-and-stick + two ESP styles → PNGs

Known prototype limits: molecule is hard-coded, no colour bar, no method log,
SCF is rerun every time, H-capped trimer instead of the reference figure's
exact end groups.

## Proposed design for `esp_figure.py` (confirm with user before building)

One command, two stages, so appearance tweaks don't redo the chemistry:

```bash
python esp_figure.py calc   "CC(C(N)=O)CC(C(N)=O)CC(C)C(N)=O" --name pam3 [--charge 0] [--opt]
python esp_figure.py render pam3 [--style rwb|rainbow|both] [--limit 0.06] [--view x,y,z]
```

- `calc` saves to `runs/<name>/`: `mol.xyz`, `surf.vtk` (with ESP), `method.txt`.
  Skips work if results already exist (unless `--force`).
- `--opt` runs a DFT geometry optimisation (PySCF + geomeTRIC) before the ESP.
  Off by default for drafts; on for final figures. Can take 30–60 min.
- `render` reads `runs/<name>/` only; takes seconds. Adds a labelled colour bar.
- Input can be a SMILES string or an `.xyz` file.
- One file is fine; split only if it grows past what is easy to read.

Test: `test_water.py` — water molecule, check ESP is negative near O and
positive near the H atoms, and the range is roughly ±0.05–0.1 a.u.

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

- Laptop OS (Windows → WSL needed)?
- Exact structure for the final figures (end groups, ester end, crosslinker)?
- Do figures need to match a journal or report style (size, font, DPI)?

## Working preferences

- Explain reasoning so the user learns the method, not just the result.
- Be blunt about weaknesses in the science or the figures.
- Keep code minimal: standard library and the packages above first.
