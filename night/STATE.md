# Night state

## Done
- Stereo, guards, full element colour table (day session 2026-11-11; sanity checks pass).
  `esp_figure.PAM3` is the syndiotactic SMILES; unspecified-stereo SMILES are now refused.
- Dry run 2026-11-11: asked for "Full element colour table" only. It was already checked in the
  roadmap and listed here, so nothing was built, tested, reviewed or queued. The colour sanity
  script was not re-run (the WSL command needed approval in this session).
- Dry run review 2026-11-11: regression 4/4 pass; sanity stereo/guards/colours pass, d3/solvent/
  restart/rerank skip (not built). Queue job `dry_water` ran and rendered. settings.json warns
  `Write(./**)` is ineffective (use `Edit(./**)`); flagged in NIGHT_REPORT.md.

## Skipped (waiting on you)

## Next
- Week 1 items of the roadmap in `IMPROVEMENTS.md`: D3, solvent, restart, re-ranking, then the redo.

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
