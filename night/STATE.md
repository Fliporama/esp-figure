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

## Skipped (waiting on you)
- (none)

## Next
- **Week 3:** charges, NCI, Fukui built (see Done; taken in roadmap order as night/code.md says, so NCI before
  def2). Left: def2 + ECP mixed basis (`night/sanity/def2.py`). Day session: look at a dimer/PAM3 `nci.png`, Multiwfn
  check of the dimer lobe. PAM3 validation runs once the CPU is free, e.g.
  `calc runs/pam3s_fold/mol.xyz --name pam3s_fold_q --d3 --solvent water --charges mk --fukui` and a gas `--nci` run.
- PAM3 frequencies (day session 2026-11-13, running/done outside the queue): `pam3s_fold_freq`
  (.xyz single point of the fold geometry), then the ext optimisation finished from step 58 with
  `--opt-conv qchem`. PySCF scratch moved to /var/tmp (`/root/.pyscf_conf.py`): /tmp is a 7.7 GB tmpfs and the
  first fold run died there. Do not queue these again.
  Results: fold freq 0 imaginary (lowest 33.2 cm-1; 5.5 h, 9.9 GB RAM). Ext opt converged at step 59
  (`--opt-conv qchem`), E -782.57747616, 0 H-bonds, ESP -0.0890/+0.1076: fold lower by 3.15 kcal/mol (unchanged).
  `pam3s_ext_freq` (.xyz of `runs/pam3s_ext`) starts by itself after tonight's night run has pushed
  (`runs/logs/ext_freq_after_night.sh`, outside the queue). **Do not queue it**, and keep the queue free of
  long PAM3 jobs tonight: the day needs the CPU and RAM for it.

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
