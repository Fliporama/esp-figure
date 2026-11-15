# Week-4 sanity checks

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
