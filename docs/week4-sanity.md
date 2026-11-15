# Week-4 sanity checks

## IGM: LOCKED 2026-11-15 (day session)

`night/sanity/igm.py` is the contract (docstring wins). Method: **IGMH** (Lu & Chen, JCC 43, 539 (2022): IGM on a
Hirshfeld partition of the real density), run by Multiwfn from a molden export; recommended over the original
promolecular IGM (PCCP 19, 17928 (2017)) because it uses our actual wavefunction. Fragments: covalent molecules by
default, `--igm-frags` for intramolecular contacts (PAM3: the two amide groups of an H-bond).

| Check | Limit | Reference value |
|---|---|---|
| grid | spacing <= 0.2 bohr, >= 2.5 bohr beyond atoms | 0.200, 2.74 |
| dimer delta-g_inter max | on the H...O segment, sign(l2)rho < -0.015 | 0.0455 at 1.67 Å, -0.0254 |
| dimer behind donor | max < 1e-3 | 0 |
| dimer integral | within 10 % | 0.0856 (= Multiwfn's own printout 0.085546) |
| PAM3 fold (gas baseline), shortest H-bond H35...O5 | max on that contact, sign(l2)rho < -0.01 | 0.0294, -0.0161 (NCI check: -0.0166) |
| PAM3 integral | within 10 % | 0.0757 |
| single molecule, no fragments | clean exit | - |

Deliberate bugs, all caught: 0-based fragment indices (5 checks), delta-g instead of delta-g_inter (5), promolecular
IGM instead of IGMH (both integrals, 3.4x too large; location checks pass, so the integrals are what tell the
methods apart), spacing 0.378 bohr (grid check; that run's method.txt still claimed 0.2). Not independent: the
reference itself calls Multiwfn, so this checks plumbing (fragments, grid, files, sign) and chemistry anchors,
not Multiwfn's IGMH. Runtime ~7 min (two SCFs + Multiwfn). Multiwfn ignores an "A" suffix on the spacing prompt.

## IR: LOCKED 2026-11-15 (day session)

`night/sanity/ir.py` is the contract; its docstring wins over this file. Decisions in `night/STATE.md` Answers
(week 4 #3): finite-difference dipole derivatives, scale 0.960 (plotted spectrum only), Lorentzian FWHM 10 cm-1.

| Check | System | Limit | Reference value |
|---|---|---|---|
| intensity order | water | bend > asym > sym | 79.6 / 20.1 / 1.8 km/mol (exp. gas ~54 / 45 / 2: same order) |
| intensity values | water | each within 15 % or 1 km/mol | 79.6, 1.8, 20.1 (bend, sym, asym) |
| strongest band | formamide | raw frequency 1700-1900 cm-1 (C=O) | 1842.2 cm-1, 357 km/mol |
| symmetry zeros | methane | exactly 3 modes < 0.1 km/mol, 6 > 1 | A1 + E 0.00; T2 15.5 (1374), 26.5 (3162) |
| scaled peak | water csv | bend within 2 cm-1 of 0.960 x raw | 1642.0 vs 1642.5 |
| line shape | water csv | value at peak + 15 cm-1 = 0.07-0.13 of peak | 0.106 (Gaussian of same FWHM: 0.003) |
| caption line | method.txt | "harmonic", "0.960", "FWHM 10" | - |

Tested against a throwaway reference implementation (central differences, h = 1e-3 bohr, PySCF `norm_mode`,
974.88 km/mol per (e/sqrt(amu))^2): all pass. Deliberate bugs, each caught by at least one check:

| Bug | Caught by |
|---|---|
| mode vectors without 1/sqrt(m) | water values (124 / 8 / 50) |
| \|dmu/dQ\| instead of \|dmu/dQ\|^2 | water values (280 / 42 / 141) |
| spectrum not scaled | scaled peak (1711 vs 1642.5) |
| Gaussian instead of Lorentzian | line shape (0.003) |

Lesson: the intensity order alone caught none of the two intensity bugs; the absolute reference values are what
make the check bite. Runtime: ~34 min for all three molecules with the CPU shared with a PAM3 job (timeout 3600 s).
Not checked: IR in PCM (the solute dipole from a solvated density is the usual choice; no reference here).
