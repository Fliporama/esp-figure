# Night state

## Done
- Stereo, guards, full element colour table, D3 `--d3` (day session 2026-11-11; sanity checks pass).
  `esp_figure.PAM3` is the syndiotactic SMILES; unspecified-stereo SMILES are now refused.
- Night 2026-11-12: solvent `--solvent water` (IEF-PCM eps 78.3553, SCF + opt + ESP; `test_solvent.py`),
  restart for `--opt` (`opt_traj.xyz`, resumes from last complete frame; `test_restart.py`),
  DFT re-ranking `--rerank N` (same D3/solvent flags as the run; `test_rerank.py`). All defaults unchanged.
  Full `check.py --sanity` run once: d3, solvent, restart, rerank all PASS (solvent: water dG_solv -6.46
  kcal/mol; PAM3 ESP extremes +17..23 %; fold-ext gas -5.51 -> water -2.41 kcal/mol. rerank on PAM3 gas:
  MMFF #1 was also the DFT lowest, others +1.8..+5.1 kcal/mol). So the redo jobs pam3s_fold / pam3s_ext
  are queued exactly as in Answers.
- Notes for the day session:
  - Mapped ESP with `--solvent` = nuclei + solvated density; PCM surface charges are NOT added (standard,
    stated in method.txt).
  - Re-ranking dedupe merges mirror-image conformers (RMSD allows reflection + heavy-atom automorphisms):
    syndiotactic PAM3 is meso-like (identical ends), so a conformer and its mirror are the same shape.
    The locked rerank sanity (energies distinct > 1e-7 Eh) can't catch mirror duplicates (~1e-5 Eh DFT
    grid noise); `test_rerank.py` checks the PAM3 picks differ in MMFF energy. Consider tightening the
    sanity to > 1e-4 Eh.
  - Restart resumes geomeTRIC cold (no Hessian carried over), so it saves roughly the steps already done, not more.

## Skipped (waiting on you)

## Next
- Morning: review the queued `runs/pam3s_fold` / `runs/pam3s_ext` (D3 + water + rerank) against the gas
  controls `pam3s_gas_fold` / `pam3s_gas_ext`; render with `--view` as needed; then tick "Redo" in IMPROVEMENTS.md.
- Week 2: frequency check (`freq` sanity waits), HOMO/LUMO (`orbitals`), double sticks (`bond_list`), UKS (`spin`).

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
