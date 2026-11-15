# Night state

## Done
- Stereo, guards, full element colour table, D3 `--d3` (day session 2026-11-11; sanity checks pass).
  `esp_figure.PAM3` is the syndiotactic SMILES; unspecified-stereo SMILES are now refused.
- Night 2026-11-12: solvent `--solvent water` (IEF-PCM eps 78.3553, SCF + opt + ESP; `test_solvent.py`),
  restart for `--opt` (`opt_traj.xyz`, resumes from last complete frame; `test_restart.py`),
  DFT re-ranking `--rerank N` (same D3/solvent flags as the run; `test_rerank.py`). All defaults unchanged.
- Day session 2026-11-12 (merged into main, all sanity + regression pass):
  - Double bonds as double sticks (`bond_list`; `bonds` sanity now passes) and HOMO/LUMO
    (`calc --orbitals`; `orbitals` sanity passes).
  - Restart fix: a resumed `--opt` no longer writes the restart point twice.
  - `night.ps1` copies main's `runs/<name>` into the worktree for every queued job, so `--opt` resumes
    across nights. Per-job cap raised from 4 h to 6 h (`-JobTimeoutSec 21600`).
  - Render: back-side ESP extrema listed in a corner note (not labelled through the molecule);
    `--limit rainbow,rwb`; only the surface layer nearest the camera is drawn (fixes dark seams).
  - Re-rank sanity: "distinct energies" threshold 1e-7 -> 1e-4 Eh (user-approved; catches mirror duplicates).
- **Folded vs. extended in water + D3: DONE 2026-11-12. Do not re-queue `pam3s_fold` / `pam3s_ext`.**
  Fold resumed and converged (`runs/pam3s_fold`, E -782.58249894). Ext was stopped at step 58 (energy and
  gradients converged, displacement not) and finished as a single point (`runs/pam3s_ext_sp`,
  E -782.57747593). Folded lower by 3.15 kcal/mol. Figures rendered. Details in CLAUDE.md Status.

- Night 2026-11-13 (code + fast tests; `freq`/`uks` sanity run after this phase):
  - Frequency check `calc --freq` (analytic Hessian, `harmonic_analysis`, imaginary modes as negative numbers;
    `test_freq.py`). Water 1710.7/3720.3/3844.2 cm-1, planar NH3 1 imaginary (-898.6). D3 + PCM analytic Hessian
    matches central finite differences of analytic gradients within 0.1 cm-1 (water). The imaginary count is
    raw (no noise cutoff). PAM3 timing has not been measured.
    Side fixes: a cached run refuses a recompute with different `--opt`/`--no-hbond` (before: `--freq` without
    `--opt` would overwrite an optimised run with a draft single point); `--force` also deletes the old
    method.txt; a finished `--opt` re-used for `--freq`/`--orbitals` is captioned "continued from step N of a
    finished optimisation" (was "restarted ... interrupted").
  - Open-shell UKS `calc --spin N` (`test_uks.py`): CH3 doublet energy = direct UKS, <S^2> 0.7537, ESP
    -0.0155/+0.0194 from the total density; also runs through `--opt --d3 --solvent water` (stays planar,
    <S^2> 0.7537). Level string carries the multiplicity ("UB3LYP/6-31G(d) (doublet)"), so the caption, cache
    and restart tag tell spin states apart. Warning in method.txt if <S^2> is off by > 10 %.
    Refused for now: `--spin` with SMILES (MMFF94 has no radical atom types), with `--orbitals` (HOMO/LUMO
    indexing is RKS-only) and with `--freq` (UKS Hessian untested).
  - No queue jobs: no PAM3 frequencies until you decide (see Next).
  - Phase 3 review failed (network, 02:12); review done in the day session 2026-11-13: regression + all sanity + tests pass, merged.

- Night 2026-11-13 (second run; code + fast tests; `charges`/`nci`/`fukui` sanity run after this phase):
  - MK/CHelpG charges `calc --charges mk|chelpg` (`test_charges.py`): one constrained least-squares fit
    (`fit_points`, `fit_charges`), ESP at the fit points from the same `esp_at()` as the surface (refactored out,
    default output unchanged). Water MK q(O) -0.753 (= day reference), CHelpG -0.749; RRMS 0.118 / 0.111.
    MK radius for elements without a table value (Si, Br) is 2.0 Å, *assumed* and named in method.txt.
    Side fix: `--orbitals` overwrote earlier method.txt lines (`orb =` -> `orb +=`).
  - RDG/NCI `calc --nci` (`test_nci.py`): `rdg.cube` + `sl2rho.cube` on the dens.cube grid from analytic AO 2nd
    derivatives; `render` draws `nci.png` (s = 0.5, rho < 0.05, sign(lambda2) rho on +/-0.04, blue = attractive;
    caption says these colours are not ESP). Water dimer H...O lobe min -0.0253 a.u.; isolated water: none.
    **nci.png has not been looked at** (viewing it needed a command outside the night allowlist; delete the leftover
    `runs/_look_nci.py`). Grid spacing is GRID-limited (0.15-0.19 bohr for water; coarser for PAM3, NCIPLOT uses ~0.1),
    stated in method.txt. Multiwfn comparison still a day-session job.
  - Fukui `calc --fukui` (`test_fukui.py`): vertical UKS doublets N+-1 at the final geometry, same D3/PCM, Mulliken
    condensation, `fukui.txt`. Formaldehyde f+ C 0.278 / O 0.274, f- O 0.434 (= reference); PCM path checked against
    direct PySCF PCM runs. Unconverged ion SCF exits (nothing cached); <S^2> > 10 % off is flagged. Refused with --spin.
    `scf()` now picks UKS/RKS from `mol.spin` (same choice as before for every caller; `test_uks.py` passes).
  - No queue jobs: STATE asked to keep the queue free of PAM3 jobs tonight (ext freq outside the queue).
  - Phase 3 review: regression 4/4 pass; sanity `charges`, `nci`, `fukui` pass (all earlier entries pass, `def2` skips).
    Roadmap ticks for the three stand. `nci.png` still unviewed; Multiwfn check still open.

- Night 2026-11-15 (code + fast tests; `def2` sanity runs after this phase, I could not run it here: needs approval):
  - def2 + ECP mixed basis (`test_def2.py`): `.xyz` atoms with Z > 36 get def2-SVP + def2 ECP, all others 6-31G(d)
    (`HEAVY_BASIS`, `heavy_atoms()`); runs without heavy atoms build the same Mole as before (basis "6-31g*", no ECP).
    CH3I: E -337.70445097 = direct PySCF, ESP -0.0202/+0.0302, sigma hole on the C->I axis, minimum at I (belt);
    method.txt names the effective nuclear charge (I 25). HBr unchanged. SMILES `CI` refused (hint: use .xyz);
    elements without a def2-SVP ECP (Fr) refused.
    Refused with ECP atoms (review): `--nci` (ECP removes the core density, so RDG would show fake lobes near the heavy
    atom; NCIPLOT adds a core density back) and `--freq` (ECP Hessian untested). `--opt`, `--d3`, `--solvent`,
    `--charges` (I radius 2.0 Å assumed, named), `--fukui`, `--spin` run with the mixed basis but are **untested**.
  - No queue jobs (no PAM3 relevance).
  - Phase 3 review: regression 4/4 pass; sanity 17/17 pass incl. `def2`, so the roadmap tick stands. Branch is 2 commits
    behind main (`8eb5fe3`, `f2484d0`, NCI render / `--nci-step`); hunks don't overlap by inspection.

- Night 2026-11-16 (code + fast tests; `ir`/`igm` sanity run after this phase; all defaults unchanged, test_water passes):
  - IR `calc --freq --ir` (`test_ir.py`): dipole derivatives by central differences (1e-3 bohr, 6N SCFs at the run's level),
    projected on PySCF's `norm_mode`, 974.88 km/mol per e^2/amu. Water 79.99/1.80/20.38 km/mol (ref 79.6/1.8/20.1), formamide
    C=O 1842.2 cm-1 strongest (366 km/mol). `ir_spectrum.csv` 400-4000 cm-1 (scaled 0.960, Lorentzian FWHM 10, peak height =
    km/mol); bands below 400 cm-1 named in method.txt (formamide NH2 wag 64 cm-1, 265 km/mol). `ir.png` checked by eye.
    With --solvent: runs, flagged "not comparable to gas phase, untested". `--ir` on an existing --freq run recomputes the
    Hessian too (no reuse); PAM3 IR stays a day-session job (Answers week 4 #3), not queued.
  - IGM `calc --igm [--igm-frags "1-3;4-6"]` (`test_igm.py`): Multiwfn noGUI 20 -> 11 (IGMH), grid atoms + 3 bohr (Multiwfn
    rounds: dimer reach 2.85 bohr) at 0.2 bohr. Water dimer integral 0.085547 (ref 0.0856), max on H...O, sl2rho < -0.015;
    fragments auto = covalent molecules, swapped fragments give the same integral; bonded fragments get a WARNING.
    Refused with --spin (UKS molden untested) and ECP atoms. Untested: --solvent, --opt. `igm.png` (water dimer) checked by eye:
    blue-centred H-bond disc. PAM3 IGM not queued: it needs runs/pam3s_fold/mol.xyz, which the queue doesn't copy.
  - UV-Vis `calc --uvvis` (`test_uvvis.py`), **unvalidated: needs a sanity check**: full TD-DFT, 10 singlets, ground state
    redone in 6-31+G(d), Gaussian FWHM 0.3 eV, epsilon by Gaussian's formula. Formaldehyde S1 4.005 eV (n->pi*, f 0.0000);
    energies = direct PySCF; f = 4.32e-9 * integral of epsilon holds. Refused with --solvent, --spin, ECP atoms. uvvis.png
    greys out wavelengths beyond the highest state and says "unvalidated". If the 6-31+G(d) SCF fails, the main results stay.
  - Queue: `pam3_uvvis` (gas baseline geometry): PAM3 timing and first look at the spectrum.
  - Untracked leftovers to delete by hand (night can't delete): `test_zz_probe_igm.py`, `_probe_igm.py`, `_probe_igm.txt` (Multiwfn prompt
    probe), `/root/igm_probe/` in WSL. Throwaway runs in runs/: `formamide_ir`, `formamide_uv`, `water_dimer_igm`.

## Skipped (waiting on you)
- (none; the four week-4 questions are answered under Answers, 2026-11-15)

## Next
- **Week 4 built (2026-11-16 night)**: IR, IGM, UV-Vis. Open for a day session:
  1. A UV-Vis sanity check (suggestion: formaldehyde S1 n->pi* dark near 4 eV; a pi->pi* reference, e.g. ethylene or
     benzene vs. a literature TD-B3LYP value; peak-height and integral checks of uvvis.csv).
  2. PAM3 IGM in water: `calc runs/pam3s_fold/mol.xyz --name pam3s_fold_igm --d3 --solvent water --igm --igm-frags <amide
     groups of H26...O16>` (outside the queue; --igm with PCM untested), render with the NCI view `--view=0.02,0.87,0.50`.
  3. PAM3 IR (Answers: ~1 day, day session): 222 extra SCFs on top of the Hessian; no restart inside the IR loop.
  4. Reference comparison still waits for `ref/` files.
- **Multiwfn NCI check PASSED (day, 2026-11-15)**: `/root/multiwfn` exists, so IGM (week 4 #2) is unblocked; how to drive
  Multiwfn non-interactively: `docs/multiwfn-nci-check.md`. IR sanity check locked (`night/sanity/ir.py`).
- **Week 3: done** (charges, NCI, Fukui, def2). Day session: decide whether to test `--opt` with ECP atoms (e.g. CH3I C-I distance vs. ~2.14 Å).
- **Week 4 (day, 2026-11-15): IR and IGM have locked sanity checks** (`night/sanity/{ir,igm}.py`, `docs/week4-sanity.md`):
  build IR first, then IGM (IGMH via Multiwfn, menu path in the igm.py docstring and `docs/multiwfn-nci-check.md`).
  UV-Vis: no sanity check yet; build only after IR and IGM pass, marked "unvalidated". Reference comparison: `ref/` empty, skip.
- **Fukui on PAM3 in water: FIXED by day 2026-11-15, do not touch.** The N-1 UKS SCF had not converged and the run exited
  without method.txt. Now: N+-1 start from the neutral density, then level shift 0.3, then second-order SCF
  (`fukui_scf`); if all fail, method.txt says "Fukui: not computed" and the main results are kept. test_fukui, sanity
  fukui, test_water pass. The PAM3 rerun `pam3s_fold_q` was started by day outside the queue (log
  `runs/logs/pam3s_fold_q2.log`); do NOT queue it (the queue copies only runs/<name>, not the input run folder).
  **DONE 2026-11-15 20:05** (40 min): both N+-1 converged from the neutral density (no fallback), <S^2> 0.753/0.755;
  E and ESP identical to pam3s_fold; f- top: carbonyl O4 0.155, O9 0.151 (O15, H-bond acceptor, 0.074); f+ top: C13 0.137.
- PAM3 frequencies: **DONE, do not queue again.** `pam3s_fold_freq` 0 imaginary (lowest 33.2 cm-1; 5.5 h, 9.9 GB);
  ext opt converged at step 59 (`--opt-conv qchem`, E -782.57747616, fold lower by 3.15 kcal/mol, unchanged);
  `pam3s_ext_freq` 0 imaginary (3.6 h, 2026-11-14). Both conformers are minima. The CPU is free again: the
  "no long PAM3 jobs" note of 2026-11-13 no longer applies.

## Answers
<!-- Write your decisions here, one line each, e.g. "Stereo: syndiotactic". -->
- Stereo: syndiotactic (user, 2026-11-11). The PAM3 SMILES gets explicit alternating
  stereocentres; the caption states "syndiotactic trimer".
- D3 (user, 2026-11-11): behind `--d3`, default OFF. IMPROVEMENTS.md says "D3 on by default", but
  that changes the regression numbers; switching the default is a later day-session decision with
  new reference values. Not a reason to skip the item.
- Solvent (user, 2026-11-11): `--solvent water` applies to the geometry optimisation (`--opt`) AND
  the SCF/ESP. IEF-PCM, eps 78.3553 (PySCF `mf.PCM()`). Gas optimisation + solvated ESP mixes models.
- Re-ranking (user, 2026-11-11): the DFT single points use the same flags as the run
  (`--d3` and/or `--solvent` apply to the re-ranking too). The chosen conformer then goes to `--opt`
  if given.
- Redo of folded vs. extended (user, 2026-11-11): queue only when D3, solvent, restart and
  re-ranking all pass their sanity checks. Then queue exactly these two jobs:
  `calc C[C@@H](C(N)=O)C[C@H](C(N)=O)C[C@H](C)C(N)=O --name pam3s_fold --opt --d3 --solvent water --rerank 5`
  `calc C[C@@H](C(N)=O)C[C@H](C(N)=O)C[C@H](C)C(N)=O --name pam3s_ext --opt --d3 --solvent water --no-hbond`
  (Each ~1.5-3 h. The ext start keeps its `--no-hbond` pick without re-ranking, since re-ranking
  would likely pick a folded shape again.)
- Redo status (user, 2026-11-12): DONE in the day session (see Done). The two lines above are history:
  never queue `pam3s_fold` or `pam3s_ext` again unless a new Answer says so.
- Week 3 (user, 2026-11-13):
  1. Charges: MK + CHelpG (`--charges mk|chelpg`), same fit code, different point selection.
  2. NCI: own code; checked once against Multiwfn on the water dimer in a day session (Multiwfn download approved).
  3. Fukui: OK to call UKS internally for N+1 / N-1 at the fixed neutral geometry, also from SMILES input.
     Mulliken-difference condensation; method.txt flags f+ as basis-limited (6-31G(d), no diffuse functions).
  4. def2: build it, MIXED basis: 6-31G(d) on H-Kr, def2-SVP + def2 ECP only on Z > 36; caption names both.
- Week 4 (user, 2026-11-15, taking the night's recommendations):
  1. Reference comparison: the Gaussian files go in `ref/` (.log/.fchk + geometry). Not bought yet: until `ref/`
     holds them, skip this item WITHOUT a question. When they are there: queue `calc ref/<geom>.xyz --name ref_pam3`
     at the reference's level (read the .log route line); mind 5d (PySCF) vs 6d (Gaussian default) for 6-31G(d).
  2. Multiwfn: approved, installed by a day session at `/root/multiwfn` (manual download, site has a CAPTCHA).
     IGM only after the NCI water-dimer check against Multiwfn has passed. Until `/root/multiwfn` exists, skip
     IGM without a question.
  3. IR: finite-difference dipole derivatives, no install; build and validate on formamide first (water too).
     Scale factor 0.960 (NIST CCCBDB, B3LYP/6-31G*), applied to the plotted spectrum only, raw frequencies kept
     in method.txt; Lorentzian FWHM 10 cm-1. Caption names scale factor, FWHM and "harmonic". A PAM3 IR run
     (~1 day) is NOT a queue job: list it under Next for a day session.
  4. UV-Vis: TD-DFT, 10 states, Gaussian broadening 0.3 eV (FWHM). The TD step uses 6-31+G(d) (ground state redone
     in that basis), the caption says so; the ESP/geometry basis is unchanged. Build only after IR.
  Week 4 has no locked sanity checks yet: build and mark "unvalidated: needs a sanity check" as code.md says.
