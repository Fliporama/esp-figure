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

## Skipped (waiting on you)

## Next
- Week 2 remaining: frequency check (`freq` sanity waits for `calc(freq=...)`), open-shell UKS
  (`uks` sanity waits for `calc(spin=...)`). Code + sanity only; no PAM3 frequency jobs until the user
  asks (the ext geometry is not fully converged, so its frequencies need a decision first).

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
