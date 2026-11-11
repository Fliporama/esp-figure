"""Implicit solvent (PCM) on water and the locked folded/extended PAM3 geometries.

Contract: calc(..., solvent="water")  (CLI --solvent water). "SCF energy" in method.txt is then the total
energy in solvent (PySCF mf.e_tot with PCM, eps 78.3553), and the ESP is computed from the solvated density.
Pass if: water dG_solv = E(water) - E(gas) is -3 to -12 kcal/mol; for both PAM3 geometries |ESP min| and
ESP max grow, each by less than 50 %; E(fold) - E(ext) in water is above the gas value (-5.51 kcal/mol).
(Day-session estimate: water -6.5 kcal/mol.)
"""
from _util import BASE, H2KCAL, Checks, calc, need

need("solvent")
ok = Checks()
e_gas = calc("O", "water_gas")[1]
e_aq = calc("O", "water_aq", solvent="water")[1]
dg = (e_aq - e_gas) * H2KCAL
ok("water dG_solv -3 to -12 kcal/mol", -12 <= dg <= -3, f"{dg:.2f} kcal/mol")
e = {}
for k, b in BASE.items():
    _, e[k], lo, hi = calc(b["xyz"], f"pcm_{k}", solvent="water")
    gmin, gmax = lo / b["min"] - 1, hi / b["max"] - 1
    ok(f"{k}: ESP extremes grow < 50 %", 0 < gmin < 0.5 and 0 < gmax < 0.5,
       f"min {b['min']} -> {lo:.4f} ({gmin:+.0%}), max {b['max']} -> {hi:.4f} ({gmax:+.0%})")
gas = (BASE["fold"]["e"] - BASE["ext"]["e"]) * H2KCAL
aq = (e["fold"] - e["ext"]) * H2KCAL
ok("E(fold) - E(ext) rises in water", aq > gas, f"gas {gas:.2f} -> water {aq:.2f} kcal/mol")
ok.finish()
