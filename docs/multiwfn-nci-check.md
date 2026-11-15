# Multiwfn NCI check (water dimer): PASSED 2026-11-15

Our `calc --nci` (own code) against Multiwfn 2026.11.13 (Linux noGUI, `/root/multiwfn/Multiwfn_2026.11.13_bin_Linux_noGUI/`)
on the same wavefunction (`runs/multiwfn_check/water_dimer.molden`, E −152.82371656) and the same grid
(`runs/water_dimer_nci_fine/rdg.cube`, 131×78×89, 0.1 bohr).

| Quantity | Pass limit | Result |
|---|---|---|
| s (RDG), points with s ≤ 2 and 1e-4 ≤ ρ < 0.0499 (107 718) | within 1 % | max 2.0e-4 relative (mean 5.6e-6); near s = 0.5: 3.2e-5 |
| sign(λ2)ρ, ρ < 0.05 | within 1e-3 a.u. | max 8.5e-5 (near nuclei 2e-4 relative, cube rounding) |
| H-bond lobe min sign(λ2)ρ (s ≤ 0.5) | −0.0263 | −0.02634 both, same 288 points; no sign flips |

Smoke test first: ρ at (0.5, 0.3, 0.2) bohr = 0.8347732921 in both, so Multiwfn reads PySCF's molden (basis
convention included) exactly as PySCF does.

**Gotcha:** Multiwfn sets s = 100 wherever ρ ≥ `RDG_maxrho` (0.05, `settings.ini`), to hide the core regions. Our
code doesn't cap. A naive comparison shows "100 % different" at 59k points; all of them have ρ ≥ 0.05 (2 sit at
exactly 0.05 and fall on different sides by rounding). The cap is cosmetic: it doesn't touch the NCI lobes.

## How to drive Multiwfn non-interactively (for IGM etc.)

```bash
D=/root/multiwfn/Multiwfn_2026.11.13_bin_Linux_noGUI
ulimit -s unlimited; export OMP_STACKSIZE=200M Multiwfnpath=$D      # manual §2.1.2; without them it may crash
cd <empty work dir>                                                  # cubes are written to the cwd (RDG.cub, ...)
printf "5\n13\n8\n<grid.cube>\n2\n0\n5\n15\n8\n<grid.cube>\n2\n0\nq\n" | $D/Multiwfn_noGUI file.molden
```

Menu path: 5 (grid data) → function 13 RDG / 15 sign(λ2)ρ → grid 8 (copy another cube's grid) → 2 (export cube) →
0 (main menu). Every prompt needs its answer on stdin, in order; a missing one ends in `forrtl: severe (59)` (the
exit code is then non-zero, so check the files exist). Point properties (main menu 1) also ask for the unit
(1 = bohr). Comparison script and Multiwfn cubes: `runs/multiwfn_check/` (git-ignored).
