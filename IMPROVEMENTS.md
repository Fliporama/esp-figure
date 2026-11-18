# Model improvements — backlog

Ideas for making the PAM ESP model more faithful. Not all are needed; pick by
what the paper claims. Add new items as they come up; mark done with a date.

## 1. Fix first

### Tacticity is undefined in the SMILES (found 2026-11-10) — **FIXED 2026-11-11**
Syndiotactic SMILES in `esp_figure.PAM3`; unspecified-stereo SMILES are refused (Roadmap week 1).

The PAM3 SMILES `CC(C(N)=O)CC(C(N)=O)CC(C)C(N)=O` has no `@`/`@@`, so RDKit
gives each embedded conformer a random configuration at each stereocentre.
Of the 50 conformers: 4 different stereoisomers (16 / 13 / 13 / 8).
"Lowest MMFF energy" therefore compares different molecules, not just
different shapes.

- Fix: write the stereo into the SMILES (isotactic or syndiotactic), state it
  in the caption. Free-radical PAM is atactic; a regular tacticity is the usual
  model choice.
- Note: the first `pam3_opt` / `pam3_ext_opt` comparison ran without this, so
  treat it as a pilot. Both picks share the end-centre configuration; the
  middle (pseudo-asymmetric) centre was not resolved by RDKit.
- Cost: none.

## 2. Worth doing for the paper

All three **done** (see Roadmap week 1; folded vs. extended redone with them 2026-11-12, folded lower by 3.15 kcal/mol).

| Change | Why | Cost |
|---|---|---|
| **DONE 2026-11-12** (`--solvent water`, IEF-PCM). Implicit water: `mf.PCM()` or `mf.ddCOSMO()` (PySCF), during opt and ESP | PAM is used in water. Gas phase over-favours intramolecular N–H···O H-bonds (why the conformer search folds). Solvent polarisation also slightly enlarges ESP extremes | ~1.5–2× time |
| **DONE 2026-11-11** (`--d3`, off by default). Dispersion: B3LYP-D3(BJ) (`pip install simple-dftd3` or `dftd3`) | Plain B3LYP lacks dispersion → folded vs. extended energies are biased (compact shapes under-bound). Without it, energy differences are qualitative only | ~free |
| **DONE 2026-11-12** (`--rerank N`). Re-rank conformers with DFT, not MMFF | MMFF over-weights intramolecular H-bonds. Take top 5–10 MMFF conformers, B3LYP(-D3) single point each (~2 min), optimise the best | +10–20 min |

Proposed CLI: `calc ... --solvent water` and D3 on by default (record both in
method.txt). Built as `--solvent water` and `--d3`; D3 stays off by default (user, 2026-11-11, see STATE Answers).

## 3. Optional / diminishing returns

- **Basis set**: 6-31G(d) is fine for ESP maps. 6-31+G(d,p) sharpens the
  negative regions near O; only needed if quoting ESP minima/maxima as numbers
  or a referee asks.
- **Longer oligomer (5-mer)**: trimer is dominated by its end units; the middle
  unit of a pentamer is closer to the polymer. Cost ~N³ → several hours with
  `--opt`.
- **Ensemble vs. single conformer**: a polymer has no single shape. Fine for a
  figure if the caption states how the conformer was chosen.

## 4. Gaps vs. Gaussian + GaussView (added 2026-11-11)

Most of these are already in PySCF or PyVista and just need wiring into `esp_figure.py`.
Status (2026-11-15): every item marked **DONE** is built and ticked in the Roadmap below; the rest are open.

**Matter for an ESP paper**
- **DONE 2026-11-13** (`--freq`; PAM3 fold and ext 0 imaginary). Frequency check (Gaussian `opt freq`): proves the optimised geometry is a
  minimum (no imaginary modes). Reviewers expect it. PySCF: `mf.Hessian()` +
  `pyscf.hessian.thermo`; ~1 h for PAM3.
- **DONE 2026-11-12** (`opt_traj.xyz`). Restart / checkpoint (`.chk`): a crashed 1 h opt was lost. Save the
  geomeTRIC trajectory or last geometry and allow restart from it.
- **DONE 2026-11-13** (`--charges mk|chelpg`). ESP-fitted charges (MK, CHelpG) and Mulliken: Mulliken is built in;
  MK/CHelpG need ~30 lines (fit to ESP on shells) or an extension. NBO is not
  free (Gaussian bundles NBO 3); IAO/IBO charges in PySCF are a free alternative.
- **DONE 2026-11-12** (`--orbitals`). HOMO/LUMO isosurfaces: often shown next to ESP maps. PySCF `cubegen.orbital`
  + the same render path.
- **DONE 2026-11-12** (`render --hbonds`, `bond_list`). H-bonds drawn as dashed lines; double bonds drawn as double sticks.

**Nice to have**
- Interactive view to pick the camera, then print the `--view` vector. **On the Roadmap 2026-11-16** (day session only, `render --pick`).
- Surface style options: opacity, solid vs. mesh.
- Atom labels / numbering.
- **DONE 2026-11-13** (`--spin N`, .xyz input). Open-shell molecules (spin multiplicity, UKS): was closed-shell RKS only.
- Spectra (IR/Raman, UV-Vis via TD-DFT): PySCF can. IR and UV-Vis are now on the Roadmap (week 4; IR sanity check locked 2026-11-15).

**Beyond GaussView (Multiwfn territory)**
- **Markers DONE 2026-11-11** (`render --extrema`); **all local extrema DONE 2026-11-18** (`render --extrema all`,
  `extrema.txt`; acrylic acid = Multiwfn's 6 max + 2 min); surface statistics still open (§7). ESP surface extrema (V_s,min / V_s,max) marked on the map, plus quantitative
  surface statistics. Cheap here, since ESP is already at every vertex.

## 5. Extra analyses (added 2026-11-11, seen on commercial QC service listings)

- **NCI DONE 2026-11-13** (own code, checked against Multiwfn 2026-11-15); **IGM open** (sanity check locked
  2026-11-15). **Weak-interaction plots (RDG / NCI, IGM)**: isosurfaces that show where
  H-bonds (blue), van der Waals contacts (green) and steric clashes (red) sit.
  Directly useful for the folded vs. extended PAM3 comparison, since they make
  the N–H···O H-bonds visible.
  - RDG: s = |∇ρ| / (2(3π²)^(1/3) ρ^(4/3)), coloured by sign(λ₂)ρ. Needs ρ,
    ∇ρ and the Hessian of ρ on a grid. PySCF `dft.numint.eval_rho(..., xctype="MGGA")`
    gives ρ and ∇ρ; λ₂ needs the second derivatives (`deriv=2` AO values).
  - IGM: compares the actual density gradient with a non-interacting sum of
    atomic densities. Easier to read for intramolecular contacts. Usually done
    with Multiwfn (free) from a `.molden`/`.fchk` file. PySCF writes molden
    via `pyscf.tools.molden`.
  - Cheapest route: export molden → Multiwfn → cube → render the isosurface
    with our PyVista code. Writing RDG ourselves is ~40 lines if we'd rather
    avoid the external tool.
- **DONE 2026-11-13** (`--fukui`; PAM3 in water run 2026-11-15). **Fukui functions** (f⁺, f⁻, f⁰): predict sites for nucleophilic or
  electrophilic attack, from densities of the N, N+1 and N−1 electron systems
  at the same geometry: f⁺ = ρ(N+1) − ρ(N), f⁻ = ρ(N) − ρ(N−1).
  - Two extra SCFs (charge −1 and +1; open-shell, so needs UKS, see section 4).
    ~2× the single-point cost.
  - Show as an isosurface, or map onto the density surface like the ESP
    (same render path). Condensed per-atom values from Hirshfeld or Mulliken
    charge differences.
  - Relevant if the paper discusses reactivity (e.g. crosslinking or
    hydrolysis sites on the amide). Otherwise skip.

## 6. Small improvements (added 2026-11-18, from the related-work survey)

Ideas taken from other free ESP tools (`docs/related-work.md`). Each is under a day, testable on water,
acrylic acid or PAM3. Rough order of value.

| # | Change | Source | Why | Cost |
|---|---|---|---|---|
| S1 | No specular highlight on the ESP surface (keep it on the atoms) | espmap | A white glint at a camera-dependent spot reads as an ESP extremum. Now `specular=0.3`. Render both, judge by eye | < 1 h |
| S2 | Caption line on the solvent convention: "ESP of the solute polarised by the continuum; continuum surface charges not included (as Gaussian/Multiwfn)" | espmap | espmap measured that adding the surface charges almost cancels the solvent shift (−3.60 → +0.05 kcal/mol). Our "water strengthens extrema ~20 %" holds under this convention only | < 1 h |
| S3 | Filter trivial local extrema: minimum prominence over the surrounding ring, and drop wrong-sign ones (a "max" at −0.001 a.u.) | VHoleMapper (sector-average validation); Lu & Chen 2012 on artificial extrema from uneven meshes | PAM3 `--extrema all` shows 16, several meaningless. Acrylic acid must still give 6 + 2 (`test_extrema.py`) | 1–2 h |
| S4 | Test that colour maps are not inverted: most negative V maps to the red end in both styles | espmap (3 of its maps shipped inverted) | "Red = negative" is enforced only by eye now | < 1 h |
| S5 | Surface integrity in `calc`: warn if the isosurface touches the box (clipped; pitfall 2) and report the electrons enclosed by it | espmap (a clipped surface changed a value by 26 % silently) | Today only caught by looking | 1–2 h |
| S6 | Grid-spacing convergence, once: PAM3 at 100³ vs a finer grid, extrema difference recorded in the README | espmap error budget | Gives the extrema a stated grid uncertainty. A run, not a feature | overnight run |
| S7 | `results.json` next to `method.txt`: extrema, energies, level, limits, software versions, `git describe --dirty` | espmap record | Fold vs ext or laptop vs lab computer by script instead of copying numbers; the commit says which code made a figure | 2–3 h |
| S8 | `render --html`: interactive 3D view (rotate, hover V), same colours and limits | espmap (plotly), EPM-Studio | Pick views, share with people without Python. PyVista exports HTML, no new dependency | 2–3 h |
| S9 | Rotation GIF/MP4 (`render --movie`) | EPM-Studio, xyzrender | Talks and slides | 2 h |
| S10 | Warn for gas-phase anions with HOMO > 0 (electron unbound, map follows the basis) | espmap | Cheap guard for future charged molecules | < 1 h |

## 7. Major improvements (added 2026-11-18)

Bigger pieces, days each. They change what the tool can claim, not just how figures look. Do one at a time,
each with its own design and sanity check first.

- **M1. Conformer ensembles.** `calc --ensemble K`: K conformers (spread across shapes, folded and extended
  labelled), each a normal run, then statistics per ESP site and on fold − ext energies, optionally Boltzmann
  weighted by the free energies we already compute. Why: espmap measured conformers moving V_min by up to
  5.2 kcal/mol, more than the basis set; our fold vs ext gap (~1.5 kcal/mol in G) is one conformer each. Needed
  before any published fold/ext claim. Source: espmap `--ensemble`. Cost: days + overnight compute; lab computer.
- **M2. GPU backend.** `--gpu` via gpu4pyscf for SCF, ESP and gradients. espmap: 4–10× on a Colab L4, agreeing
  to < 0.001 kcal/mol (closed shell, gas, density fitted only). Why: bigger molecules (PAM4/5, stearyl acrylate)
  and ensembles become practical. Needs the lab computer's NVIDIA GPU; validate PCM/SMD and D3 on GPU ourselves.
- **M3. Quantitative surface analysis** (Multiwfn's surface statistics, open in §4): positive/negative areas,
  area-weighted mean, σ²₊, σ²₋, σ²_tot, ν (GIPF), and per-atom or per-group surface regions with their own
  V_min/V_max/mean. Why: turns pictures into numbers you can tabulate (e.g. amide O vs N–H sites, fold vs ext).
  Check against Multiwfn's output on acrylic acid (`ref/`). Source: espmap `area_stats`/`gipf_stats`/sites,
  Multiwfn. Cost: 1–2 days.
- **M4. Records and comparison.** Build on S7: `esp_figure.py compare A B` that refuses runs at different levels,
  surfaces or limits and reports site differences with an uncertainty (conformer + grid from M1/S6). Source:
  espmap `analysis_key`/`render_key` and `compare`. Cost: 1–2 days after S7 and M3.
- **M5. Measured error budget for PAM3**, kept as data plus a test that recomputes the numbers: basis
  (6-31G(d) → 6-311+G(d,p)), solvent model (PCM/SMD/gas), functional, grid, geometry level, conformer. The
  Gaussian validation already has acrylic acid rows. Why: every number in a caption gets an error bar; the test
  stops the README drifting from the data. Source: espmap `bench/` + `test_claims.py`. Cost: overnight runs + 1 day.
- **M6. Installable package and notebook.** `pip install esp-figure` with an `esp-figure` command, tests in
  `tests/`, and one Colab notebook (SMILES in, figures and caption out). Why: users outside this machine,
  part of the planned public release. Copy the structure of espmap's Colab notebook. Cost: 1–2 days.
- **M7. Input from drawing files** (`.mol`, `.sdf`, ChemDraw `.cdxml`) with a check for 2D drawings (discard the
  coordinates, generate a conformer, say so) and a stereo check like the SMILES guard. Source: espmap structure
  gate. Cost: 1–2 days.
- **M8. Solvent reaction-field option**: `--include-reaction-field` maps the solute + continuum-charge
  potential as well, so both conventions (S2) can be shown. Source: espmap. Cost: ~1 day; check against espmap's
  chlorobenzene numbers.
- **M9 (optional). Ray-traced output** via Blender or POV-Ray export (OrbVista, scientific-figure-skills) to
  match VMD-level polish. Heavy dependency and manual steps; only for covers or posters.

Not worth taking (reasons in `docs/related-work.md`): xyzrender's 2D-projected ESP (less exact), espmap's
perceptual colour maps as defaults (we match GaussView; an option at most), AI-agent/MCP wrappers.

## Roadmap: one month, ~1 session/day (planned 2026-11-11)

The bottleneck is compute and validation, not code: most items are 10–80
lines on top of PySCF. Rhythm: write code and test on water/formamide in the
session, queue PAM3 validation runs overnight, review them at the start of the
next session.

**Week 1: PAM figures paper-ready**
- [x] Stereo: require or set tacticity in SMILES (§1) (2026-11-11, day session)
- [x] Guards with clear errors: radicals, unsupported elements, undefined stereo (2026-11-11, day session)
- [x] D3(BJ) dispersion (§2) (2026-11-11, day session; `--d3`, off by default)
- [x] Implicit solvent `--solvent water` (§2) (2026-11-12, night; IEF-PCM)
- [x] Restart / checkpoint for `--opt` (§4) (2026-11-12, night; `opt_traj.xyz`)
- [x] DFT re-ranking of top MMFF conformers (§2) (2026-11-12, night; `--rerank N`)
- [x] Full element colour table (2026-11-11, day session)
- [x] Redo the folded vs. extended comparison with all of the above (2026-11-12: folded lower by
  3.15 kcal/mol in water + D3, vs. 6.3 in gas; ext opt stopped at step 58, see CLAUDE.md)

**Week 2: credibility + presentation**
- [x] Frequency check, confirm minimum (§4): `calc --freq` (2026-11-13, night). PAM3 in water + D3: fold and ext
  both 0 imaginary (`pam3s_{fold,ext}_freq`, 5.5 h / 3.6 h, ~10 GB RAM; 2026-11-13/14)
  Free energies from them (2026-11-15): dG fold − ext −1.29 (RRHO) / −1.62 (quasi-RRHO) kcal/mol vs. dE −3.15
- [x] HOMO/LUMO surfaces (§4): `calc --orbitals`, render writes homo.png/lumo.png (2026-11-12)
- [x] ESP min/max markers on the map (§4): `render --extrema` (2026-11-11)
- [x] H-bonds as dashed lines (`render --hbonds`, 2026-11-11), double bonds as double sticks (`bond_list`, 2026-11-12) (§4)
- [x] Open-shell UKS (§4): `calc --spin N`, .xyz input only (2026-11-13, night)

**Week 3: analyses**
- [x] MK/CHelpG charges (§4): `calc --charges mk|chelpg` (2026-11-13, night)
- [x] RDG/NCI plots, own code (§5): `calc --nci`, render `nci.png` (2026-11-13, night). Pictures checked by eye and
  fixed 2026-11-15; `--nci-step 0.1` for figures. Multiwfn check **passed** 2026-11-15 (water dimer: s within 2e-4 rel., sl2rho within 8.5e-5, lobe −0.02634 both; `docs/multiwfn-nci-check.md`)
- [x] Fukui functions (§5, needs UKS): `calc --fukui`, Mulliken-condensed (2026-11-13, night)
- [x] Basic def2 + ECP support for heavy elements (`.xyz` input; MMFF has no metals) (2026-11-15, night; mixed basis,
  Z > 36 only; `--nci`/`--freq` refused with ECP atoms)

**Week 4: validation + buffer**
- [x] Compare against a reference (see below), add tests, update docs (2026-11-16, day: vendor acrylic acid +
  acrylamide, `ref/validate_acrylic.{py,txt}`; a script, not a locked sanity check; no PAM3 Gaussian files)
- [x] IGM via Multiwfn export (§5), if time: `calc --igm [--igm-frags]` (2026-11-16, night; IGMH, render igm.png)
- [x] IR spectrum from the frequency calc, if time: `calc --freq --ir` (2026-11-16, night; render ir.png)
- [ ] UV-Vis (TD-DFT): stretch: `calc --uvvis` built (2026-11-16, night; **unvalidated**, no sanity check, so unticked; gas, closed shell)

**Day session only (night agent: skip without a question, see STATE Answers)**
- [ ] Interactive view picker (§4, added 2026-11-16): `render NAME --pick` opens a live PyVista window (WSLg) with the
  same surface, colours, limits and lighting as the PNG; rotate with the mouse, a key prints the `--view` vector to
  paste into `render`. Needs a check by eye (window opens under WSL; printed view reproduces the same picture), which
  a night can't do. Default `render` stays offscreen.

**Validation reference:** ~~buy one PAM3 ESP figure~~ DONE 2026-11-16 with the vendor job already owned
(`ESP-20260212`, Feb 2026; molecules acrylamide, PAM4 Me-capped, ethylene glycol, PEG4, acrylic acid; raw
Gaussian files only for acrylic acid, copied to `ref/esp-20260212/`). Their level: PBE0-D3(BJ)/6-31+G(d,p)/PCM opt
freq, then PBE0-D3(BJ)/6-311+G(d,p)/SMD water single point, Multiwfn surface (rho 0.001). `ref/validate_acrylic.py`:
- At their level on their geometry, PySCF reproduces Gaussian+Multiwfn: ESP at their 23607 vertices MAE 0.03,
  max 0.12 kcal/mol; extrema −43.77/+61.77 vs −43.65/+62.01; energy 0.15 kcal/mol lower (D3 identical, SMD-CDS
  0.003 kcal/mol apart, rest = SMD cavity/grid discretisation). Acrylamide (their geometry unknown) on our s-cis
  `acrylamide_w` geometry: −59.73/+66.59 vs their −59.86/+66.28 kcal/mol.
- Error of our levels vs theirs (ESP extrema, same geometry): functional B3LYP 0/−3 %, basis 6-31G(d) −2/0 %
  (local map up to 3.4 kcal/mol), IEF-PCM instead of SMD −6/−5 %, gas instead of SMD −22/−17 %.
  `--d3 --solvent water` −8/−9 % (acrylamide −10/−11 %); default gas −22/−19 %. Solvent dominates; basis is minor here.
- Their report has an error: the VMD red-white-blue panels use red = positive, the GaussView panels red = negative.

**Out of scope for this month:** transition states and mechanisms; NMR, CD,
optical rotation, phosphorescence; fast results for 150+ atom systems (limited
by laptop compute); expert method choice for unusual chemistry (guards can
refuse a case, but they can't pick the right method).

Expected outcome: ~70–80% of the list working and validated; weeks 1–2 alone
give better-documented PAM figures than the paid service.

## Found 2026-11-12 (not scheduled yet)

- ~~Loose convergence for floppy chains~~ done 2026-11-12: `--opt-conv qchem` (geomeTRIC `qccnv`:
  RMS gradient AND (energy OR RMS displacement); GAU_LOOSE rejected, its gradients are ~6x looser).
  Sanity `optconv` uses n-butane (gau 5 / qchem 4 steps); formamide was too stiff (7/7) and passed
  even with `qccnv` disconnected.
- ~~Dark seams on folded surfaces~~ fixed 2026-11-12: render draws only the surface layer nearest
  the camera (CLAUDE.md pitfall 3). ~~A faint fringe remains where one lobe's edge overlaps another~~ fixed
  2026-11-18 (4e2f46a): mesh split 16-fold and closed before picking visible triangles; ~1 px outline left.
- ~~method.txt for an `.xyz` single point~~ done 2026-11-13: a `runs/<x>/mol.xyz` input of a finished `--opt`
  run is recognised (`xyz_origin`); the caption names run and level, and `--freq` warns when that level differs
  (not a stationary point). Imaginary modes within `FREQ_NOISE` (50 cm-1) of zero are reported as likely noise.
  Runs made before this (`pam3s_{fold,ext}_orb`, `pam3s_fold_freq`) keep the old line.
- ~~View choice~~ done 2026-11-12: `render --view auto` (600 directions; extrema visible, C=O and
  H-bonds side-on, few overlaps, plus a pull towards the chain-flat default). Picks the hand-chosen
  fold view; ext's pick is fine but no better than its default.
- Comparison figure done 2026-11-12: `esp_figure.py panel A B --labels ...` (shared colour bar, refuses
  different limits, ΔE only at one level of theory, writes <out>.txt).

## Found 2026-11-15

- ~~Ext optimisation unconverged~~ done 2026-11-13: resumed from step 58 with `--opt-conv qchem`, converged at
  step 59 (E −782.57747616, 0.0001 kcal/mol below the step-58 single point): fold lower by 3.15 kcal/mol stands.
- ~~NCI picture flaws~~ fixed 2026-11-15 (8eb5fe3), found by looking at it, which no check did:
  colour bar title clipped and bar over the molecule; H-bond disc seen edge-on (default view now tilted ~35°
  about the middle axis, long axis kept horizontal); a spurious lobe at the box corner where rho ~ 0
  (s = |grad rho|/rho^(4/3) is noise there) that also wrecked the camera framing (now rho < 1e-4 dropped).
  Lesson: a sanity check "PNG exists" doesn't check a picture; look at every new picture type once.
- ~~NCI grid coarse~~ done 2026-11-15 (f2484d0): `--nci-step BOHR` gives NCI its own grid (atoms' box + 3 bohr).
  PAM3 at 0.1 bohr: 237x149x157, 28 min; H-bond lobe −0.0299 vs −0.0295 a.u. on the density grid, same lobes,
  smooth instead of blocky. Default `--nci` still uses the density grid (locked sanity contract).
- No automatic NCI view: PAM3 needed a hand-picked `--view` (H-bond lobe hidden behind a vdW lobe in the
  ESP view). `--view auto` scores ESP features, not NCI lobes.
- From the Gaussian validation (2026-11-16): `--solvent water` (IEF-PCM) gives ESP extrema 5–6 % weaker than SMD,
  and our full water setup 8–11 % weaker than the vendor's PBE0-D3/6-311+G(d,p)/SMD. Options: an SMD choice
  (`mf.SMD()` exists in PySCF 2.15, used in `ref/validate_acrylic.py`) and/or a bigger basis for the ESP single
  point only. Not decided; would change the locked water numbers (PAM3 limits ±0.10/±0.05).
  **DONE 2026-11-16** as an option, not a new default: `calc --ref-level` (PBE0-D3(BJ)/6-311+G(d,p) + SMD single
  point for surface/ESP/analyses; 64b1ba6). Whole pipeline from SMILES matches the Gaussian acrylic acid
  extrema within 2.6 % (2026-11-18). `--solvent water` alone stays IEF-PCM, so the locked numbers are unchanged.
- Basis convention: PySCF 6-31G(d) uses 5 spherical d; Gaussian's default is 6 Cartesian d. Matters for the
  week-4 comparison against Gaussian files (energies differ by ~mEh); use `cart=True` or Gaussian `5D` there.

## Notes / lessons

- A resumed `--opt` first re-evaluates the last frame; don't write it again (fixed 585b6f2).
- ESP extrema on the far side of the surface must not get an always-visible label: it lands
  over the wrong atoms. Test visibility with a ray from just off the surface (a ray from the
  surface itself grazes it at the rim and mislabels visible points as hidden).

- "Intramolecular H-bond" must exclude an amide H's own C=O: syn H–N–C=O
  puts that H ~2.45 Å from its O by geometry alone. `hbonds()` requires the
  acceptor to be >3 bonds away. (An earlier count of "4 H-bonds" for the
  MMFF PAM3 conformer was 1 real + 3 of these.)
