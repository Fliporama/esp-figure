# Night report 2026-11-12

## 1. Needs you

- **Both redo jobs timed out, so there is no folded vs. extended result.** Recommendation: queue the same two
  lines again next night. They are in `night/queue.txt`, and the new restart picks them up from `opt_traj.xyz`.
  Put `pam3s_ext` **first**: it has only 5 steps and needs the most time. `pam3s_fold` is nearly converged
  (see Done tonight). The 4 h per-job cap (`-JobTimeoutSec 14400`) is too short for a cold D3+PCM optimisation
  of PAM3. Each step takes about 6.6 min, and the fold run needed more than 31 steps. Consider 6 h, or one
  job per night.
- **Re-rank sanity threshold** (from phase 1): the locked check counts energies as distinct above 1e-7 Eh.
  Mirror duplicates differ by about 1e-5 Eh of grid noise, so it can't catch them. Recommendation: tighten
  it to 1e-4 Eh in `night/sanity/` (locked, so only you can edit it).
- STATE "Skipped" is empty. No package installs to approve.

## 2. Verdict

✅ **merge.** All 4 regression checks pass. The sanity checks for tonight's three features (solvent, restart,
rerank) all pass, and nothing fails. The timed-out jobs are a compute-budget problem, not a code problem:
the restart files they left are valid and get reused.

## 3. Checks

Regression (`night/check.py`, run in this phase):

| Check | Value | Limit | Result |
|---|---|---|---|
| water_test | True | True | PASS |
| pam3_sp.scf_energy | −782.4865368 | −782.4865368 ± 1e-6 | PASS |
| pam3_sp.esp_min | −0.0663 | −0.0663 ± 1e-4 | PASS |
| pam3_sp.esp_max | 0.078 | 0.078 ± 1e-4 | PASS |

Sanity (`night/sanity_result.json`, run before the queue; `any_fail: false`):

| Item | Status | Lines |
|---|---|---|
| stereo | pass | same molecule as PAM3; 3/3 centres specified; 50/50 conformers are the input isomer; amide sides [1,−1,1] (syndiotactic) |
| guards | pass | [CH3] odd electrons → exit 1; [Pd] unsupported → exit 1; unspecified-stereo PAM3 → exit 1 |
| d3 | pass | E_disp fold −41.64, ext −41.07 kcal/mol; SCF part and ESP unchanged; D3 favours folded by 0.57 kcal/mol |
| solvent (tonight) | pass | water ΔG_solv −6.46 kcal/mol (−3..−12); ESP extremes +17/+20 % fold, +19/+23 % ext (< 50 %); fold−ext gas −5.51 → water −2.41 kcal/mol |
| restart (tonight) | pass | killed after 3 steps; same final E (−169.88541843 vs −169.88541847); 6 vs 7 steps when resumed |
| rerank (tonight) | pass | 5 distinct DFT energies; chosen = lowest (−782.4792142) |
| colours | pass | P/Si/Br/I coloured; H/C/N/O/S/Cl unchanged; 0 pink px |
| freq | skip | calc() has no `freq` argument yet |
| orbitals | skip | calc() has no `orbitals` argument yet |
| extrema | pass | V_s,min/max = ESP range (−0.0678/0.0756); min at carbonyl O; max at N–H H; marked map rendered |
| bonds | skip | H-bond half PASS (fold 2, ext 1, render runs); `bond_list` (double sticks) not built |
| uks | skip | calc() has no `spin` argument yet |

## 4. Done tonight

- **Implicit solvent `--solvent water`**, `56b2346`. IEF-PCM models water as a polarisable dielectric
  (ε 78.36) around a cavity. The solute's density polarises it, and the reaction field polarises the density
  back. That is why the ESP extremes grow by about 20 % and the folded shape loses about 3 kcal/mol of its
  advantage: the solvent now stabilises the exposed amides that the intramolecular H-bond used to satisfy.
- **Restart for `--opt`**, `3d85848`. Every geometry step is appended to `opt_traj.xyz`. A rerun with the same
  command (and no `method.txt` yet) resumes from the last complete frame. The optimiser's Hessian is not saved,
  so a resumed run re-learns the curvature. It saves the steps already taken, not more.
- **DFT re-ranking `--rerank N`**, `3d0e829`. MMFF orders conformers by a force field that gets H-bond and
  dispersion energies wrong. B3LYP single points (with the same D3/solvent flags) on the N lowest *distinct*
  conformers pick a better starting geometry. "Distinct" allows for mirror images and the two identical ends
  of syndiotactic PAM3.
- **Redo jobs `pam3s_fold` / `pam3s_ext` (queue)**: both **killed, unfinished**. No `method.txt`, no figures.
  - `pam3s_fold`: re-ranking finished (D3 + water, Eh): −782.57531 (#1, picked), −782.57329, −782.57267,
    −782.56664, −782.57068. Relative to #1 that is +1.3, +1.7, +5.4 and +2.9 kcal/mol, so the MMFF favourite is
    again the DFT lowest. The optimisation ran 31 steps (02:42–06:06), E −782.57531 → −782.58250, before the
    4 h cap at 06:09. At step 31 both gradient criteria are met (rms 9.5e-5, max 3.7e-4). ΔE (1.9e-6 vs 1e-6)
    and the displacements (3.7e-3/9.3e-3 vs 1.2e-3/1.8e-3) are not. The surface is flat: the lowest Hessian
    eigenvalue is about 1.5e-3, typical for a floppy chain sliding along torsions. Expect another 5–20 steps.
  - `pam3s_ext`: started 06:09 and ran only 5 steps (−782.57043 → −782.57441, max gradient still 4.4e-3) before
    the total queue cap (stop − 1 h) at about 07:00.
  - Don't compare these two energies. The ext run is far from a minimum, so any fold−ext difference now is
    meaningless.

## 5. Figures

None: no queued job finished, so there was nothing to render, and `night/figures/` will be empty.
The rendered figures from earlier runs are unchanged (`runs/pam3s_gas_fold`, `runs/pam3s_gas_ext`).

## 6. Candidate references

- `rerank` with `--d3 --solvent water` on PAM3: the picked conformer is MMFF #1, single point −782.57530620 Eh
  (`runs/pam3s_fold/rerank.txt`). Use it only if conformer generation is seeded (the sanity's gas-phase value
  −782.4792142 suggests it is). Otherwise, wait for the converged run.
- Nothing from the optimisations yet: both are unconverged.

## 7. Run info

| Phase | Time (from `night/logs/` file times) |
|---|---|
| 1 code | 00:19 – 01:32 |
| 2a sanity | 01:32 – 02:09 (all entries reported, not cut short) |
| 2b `pam3s_fold` | 02:09 – 06:09, timeout exit 124 (4 h job cap); rerank 02:09–02:42, opt 02:42–06:06 (31 steps) |
| 2b `pam3s_ext` | 06:09 – ~07:00, timeout exit 124 (queue cap stop − 1 h); 5 steps |
| 3 review | 07:00 – |

Cut short: both queue jobs. Their `opt_traj.xyz` are kept in `runs/` for the restart.

`git diff --stat main` (before this report):

```
 IMPROVEMENTS.md |   6 +--
 esp_figure.py   | 122 ++++++++++++++++++++++++++++++++++++++++++++++++--------
 night/STATE.md  |  20 +++++++++-
 test_rerank.py  |  40 +++++++++++++++++++
 test_restart.py |  37 +++++++++++++++++
 test_solvent.py |  30 ++++++++++++++
 6 files changed, 234 insertions(+), 21 deletions(-)
```
