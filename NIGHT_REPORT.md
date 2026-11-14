# Night report 2026-11-15

## 1. Needs you

All four Week-4 items were skipped because each one needs a decision from you (details in `night/STATE.md` → Skipped):

1. **Compare against a reference.** Have the Gaussian reference files (.log/.fchk + geometry) been bought, and where should they go?
   *Recommendation:* put them in `ref/`. Then queue `calc ref/<geom>.xyz --name ref_pam3` at the level of theory the reference used. Check the route line in the .log; it is probably B3LYP/6-31G(d).
2. **IGM via Multiwfn.** May a day session install Multiwfn in WSL?
   *Recommendation:* yes. Install it once and use it for both IGM and the NCI cross-check on the water dimer, which is still open.
3. **IR spectrum.** IR intensities need dipole derivatives, and PySCF has no built-in route for DF-RKS + PCM. Which way should I go?
   - (a) Finite-difference dipoles, no install. About 1 day of compute for PAM3.
   - (b) `pyscf-properties`. This needs a pip install, which needs your approval.

   I also need a frequency scale factor and a peak width.
   *Recommendation:* (a), tried on formamide first. Scale factor about 0.96 for B3LYP/6-31G(d); check the exact value in NIST CCCBDB. Lorentzian FWHM 10 cm⁻¹.
4. **UV-Vis (TD-DFT).** How many states, how much broadening, and which basis?
   *Recommendation:* 10 states, Gaussian broadening of 0.3 eV, and 6-31+G(d) for the TD step only (the caption would say so). Without diffuse functions, Rydberg-like states come out too high.

**Package installs to approve:** none requested tonight. Option 3(b) would be one.

## 2. Verdict

✅ **Merge.** The regression is 4/4 and all 17 sanity entries pass, including `def2`, the item built tonight. Defaults are unchanged: runs without heavy atoms build the same calculation as before.

Merge note: since this branch started, main has gained two NCI commits (`8eb5fe3`, `f2484d0`). Because of that, `git diff main` makes it look as if this branch removes `--nci-step` and the nci.png tilt. It doesn't; the night never touched those lines. I compared the hunks by hand and they don't overlap, so the merge should be clean. I couldn't confirm this with `git merge-tree` because it needed approval.

## 3. Checks

Regression (`night/check_result.json`, `all_pass: true`):

| name | value | limit | result |
|---|---|---|---|
| water_test | True | True | PASS |
| pam3_sp.scf_energy | −782.4865368 | −782.4865368 ± 1e-6 | PASS |
| pam3_sp.esp_min | −0.0663 | −0.0663 ± 1e-4 | PASS |
| pam3_sp.esp_max | 0.078 | 0.078 ± 1e-4 | PASS |

Sanity (`night/sanity_result.json`, `any_fail: false`). Each entry's lines, as the locked scripts printed them:

| entry | check (limit) | value | result |
|---|---|---|---|
| stereo | same molecule as PAM3 | `C[C@@H](C(N)=O)C[C@H](C(N)=O)C[C@H](C)C(N)=O` | PASS |
| stereo | 3 stereocentres, all specified | 3, all Specified | PASS |
| stereo | all conformers are the input isomer | 50/50 | PASS |
| stereo | syndiotactic (sides alternate) | [1, −1, 1] | PASS |
| guards | [CH3] refused | exit 1, odd electrons → `--spin` hint | PASS |
| guards | [Pd] refused | exit 1, unsupported element (+ .xyz hint for Z > 36) | PASS |
| guards | unspecified-stereo PAM3 refused | exit 1, names 3 centres | PASS |
| d3 | fold: E_disp < 0, 5–60 kcal/mol | −41.64 | PASS |
| d3 | fold: SCF part unchanged | −782.48653680 vs −782.48653680 | PASS |
| d3 | fold: ESP unchanged | −0.0663/0.0780 | PASS |
| d3 | ext: E_disp < 0, 5–60 kcal/mol | −41.07 | PASS |
| d3 | ext: SCF part unchanged | −782.47776308 vs −782.47776309 | PASS |
| d3 | ext: ESP unchanged | −0.0696/0.0748 | PASS |
| d3 | D3 favours folded | −0.57 kcal/mol | PASS |
| solvent | water ΔG_solv −3 to −12 kcal/mol | −6.46 | PASS |
| solvent | fold: ESP extremes grow < 50 % | +17 % / +20 % | PASS |
| solvent | ext: ESP extremes grow < 50 % | +19 % / +23 % | PASS |
| solvent | E(fold) − E(ext) rises in water | −5.51 → −2.41 kcal/mol | PASS |
| restart | killed after 3 steps | 3 frames, killed | PASS |
| restart | same final energy | −169.88541843 vs −169.88541847 | PASS |
| restart | fewer steps when resumed | 5 vs 7 | PASS |
| rerank | 5 distinct DFT energies | −782.4792142 … −782.4733707 | PASS |
| rerank | chosen = lowest | −782.47921420 | PASS |
| colours | P/Si/Br/I coloured, not pink | #ff8000 / #f0c8a0 / #a62929 / #940094 | PASS |
| colours | H/C/N/O/S/Cl unchanged | as before | PASS |
| colours | render uses COLORS | 172191 green px, 0 pink | PASS |
| freq | water: 3 modes within 5 cm⁻¹ | 1710.9 / 3721.1 / 3844.8 | PASS |
| freq | water: 0 imaginary | 0 | PASS |
| freq | planar NH₃: exactly 1 imaginary | 1 (−898.6) | PASS |
| orbitals | HOMO < LUMO | −7.895 / 1.774 eV | PASS |
| orbitals | energies match direct PySCF | identical | PASS |
| orbitals | HOMO = O lone pair (≥ 70 %) | 85 % | PASS |
| orbitals | homo.png / lumo.png rendered | yes | PASS |
| extrema | V_s,min/max = ESP range | −0.0678/0.0756 | PASS |
| extrema | min nearest carbonyl O | atom 2 O | PASS |
| extrema | max nearest an N–H hydrogen | atom 3 | PASS |
| extrema | marked map + caption | yes | PASS |
| bonds | fold: 2 H-bonds | (25,15), (34,4) | PASS |
| bonds | fold: 34 bonds, 3 C=O doubles | yes | PASS |
| bonds | ext: 1 H-bond | (34,9) | PASS |
| bonds | ext: 34 bonds, 3 C=O doubles | yes | PASS |
| bonds | render with H-bond lines | runs | PASS |
| uks | CH₃ energy = direct UKS | −39.83752120 | PASS |
| uks | ⟨S²⟩ 0.75–0.77 | 0.7537 | PASS |
| uks | ESP surface written | 14780 points | PASS |
| uks | ESP from total density, within 0.05 | −0.0155 to 0.0194 | PASS |
| uks | [CH3] without spin refused | yes | PASS |
| optconv | default names its rule (gau) | gau | PASS |
| optconv | qchem names its rule | qchem | PASS |
| optconv | qchem takes no more steps | 7 vs 7 | PASS |
| optconv | same minimum within 1e-5 Eh | −169.88541847 both | PASS |
| charges | water_mk: one charge/atom, order | O H H | PASS |
| charges | water_mk: method.txt names scheme | yes | PASS |
| charges | water_mk: RRMS < 0.15 | 0.1180 | PASS |
| charges | water_mk: Σq = charge (1e-4) | −1.0e-6 | PASS |
| charges | water MK q(O) −0.95..−0.70 | −0.7534 | PASS |
| charges | water MK q(H1) = q(H2) (0.01) | 0.3767 / 0.3768 | PASS |
| charges | formamide_mk: one charge/atom, order | N C O H H H | PASS |
| charges | formamide_mk: method.txt names scheme | yes | PASS |
| charges | formamide_mk: RRMS < 0.15 | 0.0669 | PASS |
| charges | formamide_mk: Σq = charge | 5.9e-17 | PASS |
| charges | formamide MK ESP RMS < 0.8 × Mulliken | 0.0042 vs 0.0065 | PASS |
| charges | formamide MK signs O<0, N<0, C>0 | −0.492 / −0.832 / 0.539 | PASS |
| charges | water_chelpg: one charge/atom, order | O H H | PASS |
| charges | water_chelpg: method.txt names scheme | yes | PASS |
| charges | water_chelpg: RRMS < 0.15 | 0.1114 | PASS |
| charges | water_chelpg: Σq = charge | 0.0 | PASS |
| charges | water CHelpG q(H1) = q(H2) | 0.3747 / 0.3747 | PASS |
| charges | water CHelpG q(O) within 0.1 e of MK | −0.7493 vs −0.7534 | PASS |
| nci | method.txt has an NCI line | yes | PASS |
| nci | rdg.cube = direct evaluation (1 %) | 5.67e-5 | PASS |
| nci | sl2rho.cube = direct (1e-3 rel.) | 1.05e-4 | PASS |
| nci | dimer H···O lobe < −0.015 | −0.0253 | PASS |
| nci | nci.png rendered | yes | PASS |
| nci | isolated water: no off-atom points | 0 | PASS |
| nci | PAM3 fold: every H-bond has a lobe | H26···O16 −0.0078, H35···O5 −0.0166 | PASS |
| fukui | one row per atom, order | C O H H | PASS |
| fukui | f+, f− each sum to 1 (±0.02) | 1.00 / 1.00 | PASS |
| fukui | = direct PySCF (0.01) | 0.0000 | PASS |
| fukui | formaldehyde f+ C, O above every H | 0.278 / 0.274 vs 0.224 | PASS |
| fukui | formaldehyde f− largest on O | 0.434 | PASS |
| fukui | method.txt flags f+ basis-limited | yes | PASS |
| fukui | formamide f− largest on O or N | O 0.290 | PASS |
| fukui | spin > 0 refused | yes | PASS |
| **def2** | CH₃I energy = direct PySCF (mixed + ECP) | −337.70445097 vs −337.70445096 | PASS |
| **def2** | method.txt names def2-SVP, ECP, 6-31G(d) | "B3LYP/6-31G(d) + def2-SVP/ECP (I)" | PASS |
| **def2** | CH₃I ESP within ±0.1 a.u. | −0.0202 to 0.0302 | PASS |
| **def2** | σ-hole > +0.01 on C→I axis | +0.0256 | PASS |
| **def2** | ESP min nearest I, < −0.01 | −0.0202 at I | PASS |
| **def2** | CH₃I renders | yes | PASS |
| **def2** | HBr unchanged (no def2) | plain 6-31G(d) | PASS |
| **def2** | SMILES `CI` refused clearly | yes, with .xyz hint | PASS |

## 4. Done tonight

- **def2 + ECP mixed basis** (`2aa0182`). 6-31G(d) stops at krypton. For atoms heavier than that (Z > 36, in `.xyz` input) the code now uses def2-SVP plus its effective core potential (ECP): a pseudopotential that replaces the core electrons, so iodine's nucleus counts as charge 25 instead of 53 in the ESP. All other atoms keep 6-31G(d), so the light-atom part stays comparable with earlier runs.
- **STATE + roadmap** (`5770a9b`). The four Week-4 items are logged as skipped with questions; no queue jobs.

Weak points:
- **Tested with heavy atoms:** only single points. `--opt`, `--d3`, `--solvent`, `--charges`, `--fukui` and `--spin` all run with the mixed basis, but nothing has tested them.
- **Refused with heavy atoms:**
  - `--nci`: the ECP removes the core density, so RDG would show fake lobes near the heavy atom.
  - `--freq`: the ECP Hessian is untested.
- **The only test geometry is a hand-built CH₃I** (C–I 2.140 Å, not optimised). The σ-hole and belt checks are qualitative. Nothing compares the numbers with literature or Gaussian values for CH₃I.
- **Charges on iodine:** for `--charges` the iodine radius of 2.0 Å is assumed, not taken from a table (method.txt says so).
- **Phase 1 was short:** 7 minutes (02:49–02:56) for the code, the test and the review subagent. The sanity checks back it up, but it is a thin night.

## 5. Figures

None. No queue jobs ran (`night/queue.txt` is empty), so there are no new runs to render.

## 6. Candidate references

These would add a regression for the heavy-atom path; at the moment only the sanity script guards it. Proposed entry: CH₃I single point from the `test_def2.py` geometry, default flags:
- `ch3i_sp.scf_energy` −337.70445097 Eh (± 1e-6)
- `ch3i_sp.esp_min` −0.0202 a.u. (± 1e-4)
- `ch3i_sp.esp_max` +0.0302 a.u. (± 1e-4)

## 7. Run info

| phase | start → end (from log/file times) | notes |
|---|---|---|
| 1 code | 02:49 → 02:56 | 1 item (def2); Week 4 skipped |
| sanity | 02:56 → 03:58 | 17/17 pass |
| 2 queue | — | empty queue, no `phase2.log` |
| regression | 03:58 → 04:01 | 4/4 pass |
| 3 review | 04:01 → | this report |

Nothing was cut short.

Changed files vs. the branch point `2feb1e5`. `git diff --stat main` also shows main's two newer NCI commits as reversed, and the deleted old report:

```
 IMPROVEMENTS.md |  3 ++-
 esp_figure.py   | 42 +++++++++++++++++++++++++++++++++++-------
 night/STATE.md  | 31 +++++++++++++++++++++++++++----
 test_def2.py    | 51 +++++++++++++++++++++++++++++++++++++++++++++++++++
 4 files changed, 115 insertions(+), 12 deletions(-)
```
