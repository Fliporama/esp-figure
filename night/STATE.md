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

## Skipped (waiting on you)
- Week 3 (MK charges, RDG/NCI, Fukui, def2+ECP): not built. `docs/week3-sanity-draft.md` is still an unapproved
  draft with no `sanity` entries in `reference.json`, and its four decisions are unanswered. Questions and my
  recommendation (same as the draft's proposals):
  1. MK only, or MK + CHelpG? Recommend MK only (CHelpG later = same fit, other points).
  2. NCI: own code checked once against Multiwfn, or Multiwfn only? Recommend own code.
  3. Fukui: UKS now exists (`--spin`, .xyz only). But N±1 runs from a SMILES geometry need the spin from
     `.xyz` or an internal call; is calling UKS internally at the fixed geometry OK? Recommend yes.
  4. def2: def2-SVP everywhere for heavy-element inputs, or mixed? Recommend def2-SVP everywhere.
  Approve the draft (and lock the sanity scripts) to unblock.

## Next
- Decide on PAM3 frequency jobs. Suggested lines once you agree (6 h cap; timing untested, may not fit):
  `calc runs/pam3s_fold/mol.xyz --name pam3s_fold_freq --d3 --solvent water --freq` (an `.xyz` single point:
  the caption will say "geometry not optimised here", which is the known `.xyz` caption issue in
  IMPROVEMENTS.md). The ext geometry stopped at step 58 (displacement not converged): expect small imaginary
  torsion modes; decide whether to finish its optimisation first (`--opt-conv qchem`).
- Answer the week-3 questions above.

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
