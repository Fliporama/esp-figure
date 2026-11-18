# Improvements: open items

What is still open, by size. Finished work and the dated development log are in the git history
(this file before 2026-11-18). Related tools these ideas come from: `docs/related-work.md`.

## Known gaps

- **UV-Vis is unvalidated.** `calc --uvvis` runs (gas, closed shell) but has no sanity check. Needs one against
  literature or reference TD-DFT values (e.g. formaldehyde n→π*, ethylene π→π*) before use. For PAM3 the amide
  π→π* (~190 nm) needs ~30 states; 10 states cut the spectrum off and produce a false peak.
- **Interactive view picker** (`render NAME --pick`): a live PyVista window with the same surface, colours and
  lighting as the PNG; a key prints the `--view` vector to paste into `render`. Needs a check by eye that the
  printed view reproduces the picture.
- **No automatic view for NCI pictures**: `--view auto` scores ESP features, not NCI lobes (PAM3 needed a
  hand-picked view).
- IR and IGM in solvent are untested. Raman is not implemented.
- Smaller presentation options: surface opacity / solid vs. mesh, atom labels and numbering.
- Optional science: a pentamer (the middle unit is closer to the polymer than a trimer's), 6-31+G(d,p) or
  `--ref-level` for quoted numbers.

## Small improvements (under a day each)

| # | Change | Source | Why | Cost |
|---|---|---|---|---|
| S5 | Surface integrity in `calc`: warn if the isosurface touches the box (clipped) and report the electrons enclosed by it | espmap (a clipped surface changed a value by 26 % silently) | Today only caught by looking | 1–2 h |
| S6 | Grid-spacing convergence, once: PAM3 at 100³ vs a finer grid, extrema difference recorded in the README | espmap error budget | Gives the extrema a stated grid uncertainty. A run, not a feature | overnight run |
| S7 | `results.json` next to `method.txt`: extrema, energies, level, limits, software versions, `git describe --dirty` | espmap record | Compare runs by script instead of copying numbers; the commit says which code made a figure | 2–3 h |
| S8 | `render --html`: interactive 3D view (rotate, hover V), same colours and limits | espmap (plotly), EPM-Studio | Pick views, share with people without Python. PyVista exports HTML, no new dependency | 2–3 h |
| S9 | Rotation GIF/MP4 (`render --movie`) | EPM-Studio, xyzrender | Talks and slides | 2 h |
| S10 | Warn for gas-phase anions with HOMO > 0 (electron unbound, map follows the basis) | espmap | Cheap guard for charged molecules | < 1 h |

## Major improvements (days each)

They change what the tool can claim, not just how figures look. One at a time, each with its own design and
sanity check first.

- **M1. Conformer ensembles.** `calc --ensemble K`: K conformers (spread across shapes, folded and extended
  labelled), each a normal run, then statistics per ESP site and on fold − ext energies, optionally Boltzmann
  weighted by the free energies already computed. Why: conformers can move V_min by several kcal/mol, more than
  the basis set (espmap: up to 5.2); the PAM3 fold vs ext gap (~1.5 kcal/mol in G) is one conformer each. Needed
  before any published fold/ext claim. Cost: days + long compute.
- **M2. GPU backend.** `--gpu` via gpu4pyscf for SCF, ESP and gradients (espmap: 4–10× on a Colab L4, agreeing to
  < 0.001 kcal/mol; closed shell, gas, density fitted only). Bigger molecules and ensembles become practical.
  Validate PCM/SMD and D3 on GPU ourselves.
- **M3. Quantitative surface analysis** (Multiwfn-style): positive/negative areas, area-weighted mean, σ²₊, σ²₋,
  σ²_tot, ν (GIPF), and per-atom or per-group surface regions with their own V_min/V_max/mean. Turns pictures
  into numbers you can tabulate (e.g. amide O vs N–H sites, fold vs ext). Check against Multiwfn on acrylic acid.
  Cost: 1–2 days.
- **M4. Records and comparison.** Building on S7: `esp_figure.py compare A B` that refuses runs at different
  levels, surfaces or limits and reports site differences with an uncertainty (conformer + grid from M1/S6).
  Cost: 1–2 days after S7 and M3.
- **M5. Measured error budget for PAM3**, kept as data plus a test that recomputes the numbers: basis
  (6-31G(d) → 6-311+G(d,p)), solvent model (PCM/SMD/gas), functional, grid, geometry level, conformer. Every
  number in a caption gets an error bar; the test keeps the README in line with the data. Cost: long runs + 1 day.
- **M6. Installable package and notebook.** `pip install esp-figure` with an `esp-figure` command, and one Colab
  notebook (SMILES in, figures and caption out), for users without this setup. Cost: 1–2 days.
- **M7. Input from drawing files** (`.mol`, `.sdf`, ChemDraw `.cdxml`) with a check for 2D drawings (discard the
  coordinates, generate a conformer, say so) and a stereo check like the SMILES guard. Cost: 1–2 days.
- **M8. Solvent reaction-field option**: `--include-reaction-field` also maps the potential of the continuum's
  surface charges, so both solvent conventions can be shown (espmap: they nearly cancel the solvent shift of the
  extrema). Cost: ~1 day.
- **M9 (optional). Ray-traced output** via Blender or POV-Ray export (OrbVista, scientific-figure-skills) for
  VMD-level polish. Heavy dependency and manual steps; only for covers or posters.

Not worth taking (reasons in `docs/related-work.md`): xyzrender's 2D-projected ESP (less exact), perceptual
colour maps as defaults (the goal is the GaussView look; an option at most), AI-agent/MCP wrappers.

## Publication ideas (not scheduled)

- **Validation report**: what the tool does; the Gaussian 16 + Multiwfn comparison (acrylic acid: extrema
  within 0.4 % on the reference geometry, 1–3 % starting from SMILES, 6 + 2 local extrema within 0.07 Å;
  acrylamide within 0.5 %); the error of each cheaper level (gas −22 %, PCM −8 %); known limits.
- **Software paper** (JOSS or J. Cheminformatics), after M6, M5 and UV-Vis validated or removed. Statement of
  need from `docs/related-work.md`: a free, validated, one-command GaussView/Multiwfn replacement for
  publication ESP figures. Vertex-only ESP is not new (Bulat et al. 2010, Lu & Chen 2012), so argue usefulness and
  validation, not novelty.
- **PAM science paper** with the tool in the methods. Needs M1 first: fold vs ext is "comparable within error"
  with one conformer each.
- Any publication needs a one-sentence statement on AI-assisted coding (commits carry `Co-Authored-By: Claude`).
