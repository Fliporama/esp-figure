# Night report 2026-11-13 (second run)

## 1. Needs you

- **No skipped questions** (STATE "Skipped" is empty). **No package installs** to approve.
- **Look at `nci.png` yourself.** It was built tonight but has not been viewed: the night agent couldn't run the viewer.
  The sanity check only confirms that the PNG file gets written. My recommendation is to render it for the water
  dimer and for gas PAM3 fold in the day session before anyone uses NCI in a figure.
- **Delete `runs/_look_nci.py`.** The night agent left it there (it's git-ignored, so it does no harm).
- **The NCI roadmap tick claims more than was tested.** `IMPROVEMENTS.md` says "own code, checked against Multiwfn". The sanity
  check passes, so the tick is allowed, but the Multiwfn comparison hasn't been run. The line already says "Multiwfn check
  still open". My recommendation: keep the tick and do the Multiwfn check in the next day session.
- **Next night:** def2 + ECP mixed basis is the only week-3 item left (its sanity check `def2` currently skips).

## 2. Verdict

✅ **Merge.** All 4 regression checks pass. Every sanity check passes except `def2`, which skips because it isn't built yet.
The three items built tonight (charges, NCI, Fukui) each pass their locked sanity check.

## 3. Checks

**Regression** (`night/check_result.json`):

| Name | Value | Limit | Result |
|---|---|---|---|
| water_test | True | True | PASS |
| pam3_sp.scf_energy | −782.4865368 Eh | −782.4865368 ± 1e-6 | PASS |
| pam3_sp.esp_min | −0.0663 a.u. | −0.0663 ± 1e-4 | PASS |
| pam3_sp.esp_max | 0.0780 a.u. | 0.078 ± 1e-4 | PASS |

**Sanity** (`night/sanity_result.json`, `any_fail: false`). Items built tonight are listed line by line. Earlier items are listed
per entry, and all their lines pass:

| Entry | Check | Value | Result |
|---|---|---|---|
| **charges** | water_mk: one charge per atom, mol.xyz order | O H H | PASS |
| | water_mk: method.txt names the scheme | | PASS |
| | water_mk: ESP fit RRMS < 0.15 | 0.1180 | PASS |
| | water_mk: Σq = total charge (1e-4) | −1.0e-6 | PASS |
| | water MK: q(O) −0.95..−0.70 | −0.7534 | PASS |
| | water MK: q(H1) = q(H2) ± 0.01 | 0.3767 / 0.3768 | PASS |
| | formamide_mk: order, scheme, RRMS < 0.15, Σq | 0.0669, 5.9e-17 | PASS (4 lines) |
| | formamide MK: surface ESP RMS < 0.8 × Mulliken's | 0.0042 vs 0.0065 a.u. | PASS |
| | formamide MK: q(O) < 0, q(N) < 0, q(C) > 0 | −0.492 / −0.832 / 0.539 | PASS |
| | water_chelpg: order, scheme, RRMS < 0.15, Σq | 0.1114, 0.0 | PASS (4 lines) |
| | water CHelpG: q(H1) = q(H2) ± 0.01 | 0.3747 / 0.3747 | PASS |
| | water CHelpG: q(O) within 0.1 e of MK | −0.7493 vs −0.7534 | PASS |
| **nci** | method.txt has an NCI line | | PASS |
| | rdg.cube vs direct evaluation (1 %) | 5.7e-5 | PASS |
| | sl2rho.cube vs direct evaluation (1e-3) | 1.05e-4 | PASS |
| | water dimer: attractive H···O lobe (< −0.015) | −0.0253 | PASS |
| | nci.png rendered | file exists | PASS |
| | isolated water: no off-atom NCI points | 0 | PASS |
| | PAM3 fold: every H-bond has an attractive lobe | H26···O16 2.50 Å −0.0078; H35···O5 2.14 Å −0.0166 | PASS |
| **fukui** | one row per atom, mol.xyz order | C O H H | PASS |
| | f+ and f− each sum to 1 (±0.02) | 1.00 / 1.00 | PASS |
| | match direct PySCF (0.01) | 0.0000 | PASS |
| | formaldehyde: f+ on C and O above every H | C 0.278, O 0.274, H 0.224 | PASS |
| | formaldehyde: f− largest on O | O 0.434 | PASS |
| | method.txt flags f+ as basis-limited | | PASS |
| | formamide: f− largest on O or N | O 0.290, N 0.259 | PASS |
| | `--fukui` with spin > 0 refused | refused | PASS |
| def2 | esp_figure has no HEAVY_BASIS yet | n/a | SKIP (not built) |
| stereo, guards, d3, solvent, restart, rerank, colours, freq, orbitals, extrema, bonds, uks, optconv | all lines | as on main | PASS |

## 4. Done tonight

- **MK/CHelpG charges** (`bb460e5`): the atomic charges are fitted by least squares, so their Coulomb potential matches the
  DFT ESP at points outside the molecule. A Lagrange constraint makes them sum to the total charge. MK puts the fit points on
  shells at 1.4–2.0 × vdW radius; CHelpG puts them on a cubic grid. The fit code is shared, and only the point selection
  differs. Water q(O) is −0.753 (MK) and −0.749 (CHelpG).
- **RDG/NCI** (`66bffe3`): the reduced density gradient s = |∇ρ|/(2(3π²)^{1/3}ρ^{4/3}) drops towards 0 wherever two atoms
  interact weakly. The sign of the second Hessian eigenvalue λ₂ separates attraction (λ₂ < 0, H-bonds) from steric clash.
  Both ρ and its derivatives come from analytic AO derivatives, on the same grid as the density cube.
- **Fukui** (`2f464ce`): f+ ≈ ρ(N+1) − ρ(N) shows where an electron is added (nucleophilic attack goes there), and
  f− ≈ ρ(N) − ρ(N−1) where one is removed. Both come from vertical UKS doublet single points at the neutral geometry, with
  Mulliken condensation onto atoms. f+ is basis-limited because 6-31G(d) has no diffuse functions.
- Side fixes: `--orbitals` no longer overwrites earlier method.txt lines. `scf()` now chooses UKS or RKS from `mol.spin`, and
  every earlier caller gets the same choice as before.
- STATE + roadmap (`0c4fc32`).

## 5. Figures

None tonight. No jobs were queued, and the new features ran only on small test molecules.

## 6. Candidate references

| Quantity | Value | Suggested tol |
|---|---|---|
| water MK q(O) | −0.7534 | 0.005 |
| water CHelpG q(O) | −0.7493 | 0.005 |
| water MK / CHelpG RRMS | 0.1180 / 0.1114 | 0.005 |
| formamide MK q(O/N/C) | −0.492 / −0.832 / 0.539 | 0.01 |
| water dimer min sign(λ₂)ρ on the H···O lobe | −0.0253 a.u. | 0.002 |
| PAM3 fold (gas, pam3_opt) NCI lobes H35···O5 / H26···O16 | −0.0166 / −0.0078 a.u. | 0.002 |
| formaldehyde f+ C / O, f− O | 0.278 / 0.274 / 0.434 | 0.01 |

## 7. Run info

- Phase 1 (code): 22:00–22:19 (18 min). Sanity: 22:19–22:58 (39 min). Regression: 22:58–23:01. Phase 2 (queue): no jobs,
  so there is no `phase2.log`. Phase 3 (review): from 23:01.
- Nothing was cut short. The night itself skipped two things: the visual check of `nci.png`, and running the new features
  on PAM3 (the CPU is kept free for `pam3s_ext_freq`).
- `git diff --stat main`: `esp_figure.py` +167/−16 (11 files, +426/−128 in total), new `test_charges.py`, `test_nci.py`, `test_fukui.py`,
  `IMPROVEMENTS.md` (3 ticks), `night/STATE.md`, plus logs and result JSONs.
