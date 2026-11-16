# Night report 2026-11-16

## Needs you

- **No open questions** in STATE "Skipped". No package installs to approve.
- **The UV-Vis roadmap box was ticked by phase 1 without a sanity check.** I unticked it, because review.md only allows
  a tick when the item's sanity entry passes. Recommendation: write `night/sanity/uvvis.py` in a day session (STATE
  Next #1). It should check formaldehyde S1 n→π* as dark near 4.0 eV, one π→π* against a literature TD-B3LYP value
  (ethylene or N-methylacetamide), and that the area under `uvvis.csv` matches the oscillator strengths.
- **The PAM3 UV-Vis spectrum is not usable as a figure** (see Figures). Recommendation: if you want a PAM3 spectrum,
  rerun with ~30 states (when that flag exists) on `runs/pam3s_fold/mol.xyz`, not on the old pilot geometry.
- **Merge will probably conflict in `IMPROVEMENTS.md`.** Main added the "Day session only / `render --pick`" block
  directly below the week-4 lines this branch edits. Keep both sides: three week-4 lines (IGM `[x]`, IR `[x]`,
  UV-Vis `[ ]`) followed by main's new block. `README.md` was changed only on main, so it merges cleanly.
- Delete by hand (night can't delete): `test_zz_probe_igm.py`, `_probe_igm.py`, `_probe_igm.txt`, `/root/igm_probe/`
  in WSL, `runs/formamide_ir`, `runs/formamide_uv`, `runs/water_dimer_igm`.

## Verdict

⚠️ **Look first.** All 4 regression checks and all 19 sanity checks pass, including the new `ir` and `igm` checks,
so the code is mergeable. But UV-Vis is unvalidated, and its first PAM3 result shows a "peak" that the 10-state cutoff
produces, not the chemistry. Also expect the IMPROVEMENTS.md conflict described above.

## Checks

| Check | Value | Limit | Result |
|---|---|---|---|
| **Regression** `water_test` | True | True | PASS |
| `pam3_sp.scf_energy` | −782.4865368 | −782.4865368 ± 1e-6 | PASS |
| `pam3_sp.esp_min` | −0.0663 | −0.0663 ± 1e-4 | PASS |
| `pam3_sp.esp_max` | 0.078 | 0.078 ± 1e-4 | PASS |
| **Sanity** stereo | same molecule; 3/3 centres specified; 50/50 conformers match; sides [1,−1,1] | as stated | PASS (4/4) |
| guards | [CH3], [Pd], unspecified stereo each exit 1 with a clear message | exit 1 + message | PASS (3/3) |
| d3 | E_disp fold −41.64, ext −41.07 kcal/mol; SCF part and ESP unchanged; fold−ext −0.57 | 5–60 kcal/mol, unchanged, < 0 | PASS (7/7) |
| solvent | ΔG_solv water −6.46; ESP grows +17/+20 % (fold), +19/+23 % (ext); fold−ext −5.51 → −2.41 | −3..−12; < 50 %; rises | PASS (4/4) |
| restart | killed after 3; E −169.88541843 vs −169.88541847; 5 vs 7 steps | same E, fewer steps | PASS (3/3) |
| rerank | 5 distinct energies; chosen = lowest −782.4792142 | distinct > 1e-4, min | PASS (2/2) |
| colours | P/Si/Br/I set; H…Cl unchanged; 0 pink px | as stated | PASS (3/3) |
| freq | water [1710.9, 3721.1, 3844.8]; 0 imag; planar NH₃ 1 imag | ±5 cm⁻¹; 0; 1 | PASS (3/3) |
| orbitals | HOMO/LUMO −7.895/1.774 eV = direct; O lone pair 85 % | match; ≥ 70 % | PASS (4/4) |
| extrema | −0.0678/0.0756 = range; min at O, max at N–H | as stated | PASS (4/4) |
| bonds | fold 2 H-bonds, ext 1; 34 bonds, 3 C=O doubles | as stated | PASS (5/5) |
| uks | CH₃ E = direct; ⟨S²⟩ 0.7537; ESP −0.0155..0.0194 | 0.75–0.77; ±0.05 | PASS (5/5) |
| optconv | gau/qchem named; 4 vs 5 steps; ΔE 2e-7 | fewer steps; 1e-6 | PASS (4/4) |
| charges | water MK q(O) −0.7534, RRMS 0.118; formamide RRMS 0.067; CHelpG q(O) −0.7493 | −0.95..−0.70; < 0.15; ±0.1 of MK | PASS (18/18) |
| nci | cubes 5.7e-5 / 1.05e-4 rel.; dimer lobe −0.0253; PAM3 lobes −0.0078 (2.50 Å), −0.0166 | 1 %, 1e-3; < −0.015; < −0.005 / −0.01 | PASS (7/7) |
| fukui | sums 1.00; = direct; formaldehyde f− O 0.434; spin refused | ±0.02; 0.01 | PASS (8/8) |
| def2 | CH₃I E = direct (1e-8); σ-hole +0.0256; min −0.0202 at I | 1e-6; > 0.01; < −0.01 | PASS (8/8) |
| **ir** (new) | water 79.99/1.80/20.38 km/mol; bend peak 1642.0 (0.960 × 1710.9 = 1642.5); FWHM tail 0.106; formamide C=O 1842.2 strongest; CH₄ 3 dark | ±15 % of 79.6/1.8/20.1; as stated | PASS (9/9) |
| **igm** (new) | dimer integral 0.08555, max 0.0455 on H···O (sl2rho −0.0254); reach 2.85 bohr; PAM3 fold integral 0.07575, max on H35···O5 | ±10 % of 0.0856; ≥ 2.5 bohr; ±10 % of 0.0757 | PASS (10/10) |
| uvvis | — | no sanity entry | **unvalidated** |

## Done tonight

- **IR spectrum** (`cda1d4d`): IR intensity is the square of how much the dipole changes along a normal mode. Here the
  code nudges each atom ±0.001 bohr (6N SCFs), takes central differences of the dipole, and projects them onto
  PySCF's normal modes. The spectrum scales frequencies by 0.960 (harmonic B3LYP overestimates them), and each band is
  a Lorentzian with FWHM 10 cm⁻¹. Weak points: `--ir` on an existing `--freq` run recomputes the Hessian, and nothing
  can restart inside the 6N loop.
- **IGM via Multiwfn** (`938ae80`): IGMH compares the density gradient of the fragments added one by one with their
  sum. Where the gradients cancel, the fragments interact; δg_inter maps only that interaction, which makes it cleaner
  than NCI for picking out *which* contact. The code drives Multiwfn noGUI (menu 20 → 11). Untested: `--solvent`
  and `--opt`.
- **UV-Vis (TD-DFT)** (`db4e062`): linear-response TD-B3LYP gives vertical excitation energies and oscillator
  strengths f. The TD step uses 6-31+G(d), because excited states are more diffuse than the ground state. Each band is
  a Gaussian (FWHM 0.3 eV) with height ε ∝ f. **Unvalidated.** The test only shows the code matches direct PySCF; it
  doesn't compare against literature.
- STATE/roadmap commits `2e97ac4`, `a6fb21d`. Review: unticked UV-Vis (see Needs you).
- Queue: `pam3_uvvis` finished, exit 0, 7431 s (2 h 04 min) for 10 states of a 35-atom molecule in 6-31+G(d).

## Figures

The script copies these to `night/figures/pam3_uvvis/` after this phase:
- [rwb_esp.png](night/figures/pam3_uvvis/rwb_esp.png), [rainbow_esp.png](night/figures/pam3_uvvis/rainbow_esp.png),
  [ball.png](night/figures/pam3_uvvis/ball.png). These are the regression geometry (gas, unspecified-stereo pilot),
  identical to `pam3_sp`. The left rim still shows the known jagged stripes.
- [uvvis.png](night/figures/pam3_uvvis/uvvis.png). **Don't use it.** Weaknesses:
  - **All 10 states are nearly dark**: f ≤ 0.014, and S1 at 5.45 eV (228 nm, f 0.0014). That fits amide n→π*
    (~5.5 eV, ~220 nm), so the 225 nm shoulder is plausibly real.
  - **The 195 nm "maximum" is a cutoff artefact.** The plot's strongest band comes from states 8–9 (6.30–6.38 eV,
    f 0.007–0.014), right at the 193 nm edge. The real amide π→π* band (~6.5 eV, ~190 nm, f ~0.2–0.3 per amide)
    lies *above* the 10th state. So the true spectrum peaks inside the grey region and is several times taller.
    ε_max ≈ 2200 L mol⁻¹ cm⁻¹ is far too low for three amides.
  - **Rydberg states**: in gas phase with diffuse functions, some of these 10 states are probably Rydberg states,
    which solvent would push up.
  - **Wrong geometry**: the job used the old pilot geometry, not the syndiotactic `pam3s_fold`.

## Candidate references

- `pam3_uvvis` (baseline geometry, `--uvvis`): S1 5.4477 eV, f 0.0014; S9 6.3785 eV, f 0.0136; ground state
  B3LYP/6-31+G(d) E −782.52522382 Eh (±1e-6). These are only regression anchors, not validation, and a rerun costs 2 h.
- Formaldehyde S1 4.005 eV, f 0.0000 (from `test_uvvis.py`): a cheap anchor for a future `uvvis` sanity entry.

## Run info

| Phase | Time | Notes |
|---|---|---|
| 1 code | 00:33 – 01:34 | 3 items built; one sanity run started by hand and stopped after 3 entries (avoid a clash) |
| sanity | 01:34 – 02:29 | 19/19 pass |
| regression | 02:29 – 02:32 | 4/4 pass |
| 2 queue | 02:32 – 04:36 | `pam3_uvvis` 2 h 04 min, exit 0, empty stderr |
| 3 review | 04:36 – | this report |

Nothing was cut short. The branch is 2 commits behind main (`a0b24ab` roadmap `--pick`, `31e20f7` README).

Changed on this branch (`git diff --stat main...HEAD`, plus this phase): `esp_figure.py` (237 lines changed: IR, IGM, UV-Vis),
`test_ir.py`, `test_igm.py`, `test_uvvis.py` (new), `IMPROVEMENTS.md`, `night/STATE.md`, `night/queue.txt`,
`NIGHT_REPORT.md`, `night/*_result.json`, `night/logs/*`. Plain `git diff --stat main` also lists `README.md` (−88) and
the main-only roadmap lines. Those are main's commits missing here, not night edits.


## Uncommitted changes left in the worktree (note added by night.ps1)

A Claude phase stopped without committing these (cut off mid-edit?). They are NOT on the branch; inspect them in the worktree before merging.

```
?? _probe_igm.py
?? _probe_igm.txt
?? test_zz_probe_igm.py
```
