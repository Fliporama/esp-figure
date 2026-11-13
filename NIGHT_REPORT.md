# Night night/2026-11-13

Phase 3 (review) failed at 02:12 on a network error (`ENOTFOUND`, API unreachable) and the push failed with it.
This report was written in the day session of 2026-11-13, following `night/review.md`.

## Needs you
- **Week 3 (MK, NCI, Fukui, def2): not built.** Four questions in `night/STATE.md` "Skipped"; recommendation: MK only,
  own NCI code, Fukui via internal UKS at fixed geometry, def2-SVP everywhere. Approve `docs/week3-sanity-draft.md` to unblock.
- **PAM3 frequency jobs: none queued.** Recommend: finish the ext optimisation first (`--opt-conv qchem`), else expect
  small spurious imaginary torsion modes. PAM3 Hessian timing is unmeasured; it may not fit the 6 h cap.
- No package installs.

## Verdict
✅ merge: all regression checks, all 13 sanity checks and the four tests pass; code read, no bugs found.

## Checks
| Check | Value | Limit | Result |
|---|---|---|---|
| water_test | pass | pass | ✅ |
| pam3_sp scf_energy | -782.4865368 | -782.4865368 ± 1e-6 | ✅ |
| pam3_sp esp_min / esp_max | -0.0663 / 0.078 | ± 1e-4 | ✅ |
| sanity: stereo, guards, d3, solvent, restart, rerank, colours, orbitals, extrema, bonds, optconv | pass | pass | ✅ |
| sanity freq: water modes | 1710.9 / 3721.1 / 3844.8 | ref 1710.7 / 3720.5 / 3844.3 ± 5 cm-1 | ✅ |
| sanity freq: imaginary (water / planar NH3) | 0 / 1 (-898.6) | 0 / 1 | ✅ |
| sanity uks: CH3 energy vs direct UKS | -39.83752120 | equal | ✅ |
| sanity uks: <S^2> | 0.7537 | 0.75-0.77 | ✅ |
| sanity uks: ESP | -0.0155 .. +0.0194 | min<0<max, within 0.05 | ✅ |
| test_freq / test_uks / test_water / test_restart | exit 0 (653 / 327 / 37 / 347 s) | exit 0 | ✅ |

## Done tonight
- **Frequency check `calc --freq`** (b2808c7): analytic Hessian of the SCF (D3 and PCM terms included, checked against
  finite differences), translations/rotations projected out; 0 imaginary modes = a true minimum. Raw count, no noise
  cutoff. Side fixes: cached runs refuse a recompute with different `--opt`/`--no-hbond`; `--force` deletes old method.txt;
  caption says "continued from step N of a finished optimisation".
- **Open-shell UKS `calc --spin N`** (9b098c6): separate alpha/beta orbitals; surface and ESP use the total density;
  <S^2> written to method.txt with a > 10 % contamination warning. `.xyz` input only (MMFF94 can't build radicals);
  refused with `--orbitals`/`--freq` for now.
- STATE + roadmap (c02e9a0).

## Figures
None: no queued jobs.

## Candidate references
- `freq`: water 1710.7 / 3720.3 / 3844.2 cm-1 (B3LYP/6-31G(d), DF), planar NH3 imaginary -898.6 cm-1.
- `uks`: CH3 doublet E -39.83752120 Eh, <S^2> 0.7537.

## Run info
- Phase 1 code 01:00-01:30 (1794 s), sanity 01:30-02:12, queue empty, phase 3 failed 02:12-02:15 (network).
- Day session: regression 190 s, tests as above.
- Merging removes the night-2 `night/logs/pam3s_*` logs and the old `check_result.json` (kept in git history).
- Changed: `esp_figure.py` (+56/-17), `test_freq.py`, `test_uks.py`, `IMPROVEMENTS.md`, `night/STATE.md`, logs.
