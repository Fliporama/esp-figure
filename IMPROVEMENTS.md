# Model improvements — backlog

Ideas for making the PAM ESP model more faithful. Not all are needed; pick by
what the paper claims. Add new items as they come up; mark done with a date.

## 1. Fix first

### Tacticity is undefined in the SMILES (found 2026-11-10)
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

| Change | Why | Cost |
|---|---|---|
| Implicit water: `mf.PCM()` or `mf.ddCOSMO()` (PySCF), during opt and ESP | PAM is used in water. Gas phase over-favours intramolecular N–H···O H-bonds (why the conformer search folds). Solvent polarisation also slightly enlarges ESP extremes | ~1.5–2× time |
| Dispersion: B3LYP-D3(BJ) (`pip install simple-dftd3` or `dftd3`) | Plain B3LYP lacks dispersion → folded vs. extended energies are biased (compact shapes under-bound). Without it, energy differences are qualitative only | ~free |
| Re-rank conformers with DFT, not MMFF | MMFF over-weights intramolecular H-bonds. Take top 5–10 MMFF conformers, B3LYP(-D3) single point each (~2 min), optimise the best | +10–20 min |

Proposed CLI: `calc ... --solvent water` and D3 on by default (record both in
method.txt).

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

**Matter for an ESP paper**
- Frequency check (Gaussian `opt freq`): proves the optimised geometry is a
  minimum (no imaginary modes). Reviewers expect it. PySCF: `mf.Hessian()` +
  `pyscf.hessian.thermo`; ~1 h for PAM3.
- Restart / checkpoint (`.chk`): a crashed 1 h opt is lost now. Save the
  geomeTRIC trajectory or last geometry and allow restart from it.
- ESP-fitted charges (MK, CHelpG) and Mulliken: Mulliken is built in;
  MK/CHelpG need ~30 lines (fit to ESP on shells) or an extension. NBO is not
  free (Gaussian bundles NBO 3); IAO/IBO charges in PySCF are a free alternative.
- HOMO/LUMO isosurfaces: often shown next to ESP maps. PySCF `cubegen.orbital`
  + the same render path.
- H-bonds drawn as dashed lines; double bonds drawn as double sticks.

**Nice to have**
- Interactive view to pick the camera, then print the `--view` vector.
- Surface style options: opacity, solid vs. mesh.
- Atom labels / numbering.
- Open-shell molecules (spin multiplicity, UKS): only closed-shell RKS now.
- Spectra (IR/Raman, UV-Vis via TD-DFT): PySCF can; out of scope for ESP figures.

**Beyond GaussView (Multiwfn territory)**
- ESP surface extrema (V_s,min / V_s,max) marked on the map, plus quantitative
  surface statistics. Cheap here, since ESP is already at every vertex.

## 5. Extra analyses (added 2026-11-11, seen on commercial QC service listings)

- **Weak-interaction plots (RDG / NCI, IGM)**: isosurfaces that show where
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
- **Fukui functions** (f⁺, f⁻, f⁰): predict sites for nucleophilic or
  electrophilic attack, from densities of the N, N+1 and N−1 electron systems
  at the same geometry: f⁺ = ρ(N+1) − ρ(N), f⁻ = ρ(N) − ρ(N−1).
  - Two extra SCFs (charge −1 and +1; open-shell, so needs UKS, see section 4).
    ~2× the single-point cost.
  - Show as an isosurface, or map onto the density surface like the ESP
    (same render path). Condensed per-atom values from Hirshfeld or Mulliken
    charge differences.
  - Relevant if the paper discusses reactivity (e.g. crosslinking or
    hydrolysis sites on the amide). Otherwise skip.

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
- [ ] Redo the folded vs. extended comparison with all of the above

**Week 2: credibility + presentation**
- [ ] Frequency check, confirm minimum (§4); 1–3 h per molecule, run overnight
- [ ] HOMO/LUMO surfaces (§4)
- [x] ESP min/max markers on the map (§4): `render --extrema` (2026-11-11)
- [x] H-bonds as dashed lines (`render --hbonds`, 2026-11-11), double bonds as double sticks (`bond_list`, 2026-11-12) (§4)
- [ ] Open-shell UKS (§4)

**Week 3: analyses**
- [ ] MK/CHelpG charges (§4)
- [ ] RDG/NCI plots, own code, checked against Multiwfn (§5)
- [ ] Fukui functions (§5, needs UKS)
- [ ] Basic def2 + ECP support for heavy elements (`.xyz` input; MMFF has no metals)

**Week 4: validation + buffer**
- [ ] Compare against a reference (see below), add tests, update docs
- [ ] IGM via Multiwfn export (§5), if time
- [ ] IR spectrum from the frequency calc, if time
- [ ] UV-Vis (TD-DFT): stretch

**Validation reference:** buy one PAM3 ESP figure from a commercial service
(~500 yuan) *with raw files* (Gaussian `.log`/`.fchk` + geometry). Run our tool
on their geometry and compare energy, ESP range and figure. That gives a
citable Gaussian-vs-PySCF check.

**Out of scope for this month:** transition states and mechanisms; NMR, CD,
optical rotation, phosphorescence; fast results for 150+ atom systems (limited
by laptop compute); expert method choice for unusual chemistry (guards can
refuse a case, but they can't pick the right method).

Expected outcome: ~70–80% of the list working and validated; weeks 1–2 alone
give better-documented PAM figures than the paid service.

## Notes / lessons

- "Intramolecular H-bond" must exclude an amide H's own C=O: syn H–N–C=O
  puts that H ~2.45 Å from its O by geometry alone. `hbonds()` requires the
  acceptor to be >3 bonds away. (An earlier count of "4 H-bonds" for the
  MMFF PAM3 conformer was 1 real + 3 of these.)
