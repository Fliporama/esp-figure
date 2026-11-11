"""D3(BJ) dispersion on the locked folded and extended PAM3 geometries.

Contract: calc(..., d3=True)  (CLI --d3). method.txt then has
  "SCF energy: <E> Eh"                 E includes the dispersion correction (PySCF mf.e_tot with mf.disp = "d3bj")
  "dispersion energy: <E_disp> Eh"     the D3(BJ) term alone
D3 is a post-SCF energy term, so the density and the ESP must not change.
Pass if, for both geometries: E_disp < 0 and 5-60 kcal/mol in size; E - E_disp equals the no-D3 baseline
within 1e-6 Eh; ESP min/max equal the baseline within 1e-4 a.u. And E_disp(folded) < E_disp(extended).
(Day-session check with pyscf-dispersion 1.7.0: -41.6 and -41.1 kcal/mol.)
"""
import re
from _util import BASE, H2KCAL, Checks, calc, need

need("d3")
ok = Checks()
disp = {}
for k, b in BASE.items():
    log, e, lo, hi = calc(b["xyz"], f"d3_{k}", d3=True)
    m = re.search(r"dispersion energy: (\S+) Eh", log)
    if not m:
        ok(f"{k}: 'dispersion energy: ... Eh' in method.txt", False)
        continue
    d = disp[k] = float(m.group(1))
    ok(f"{k}: E_disp < 0, 5-60 kcal/mol", d < 0 and 5 <= -d * H2KCAL <= 60, f"{d * H2KCAL:.2f} kcal/mol")
    ok(f"{k}: SCF part unchanged", abs(e - d - b["e"]) <= 1e-6, f"E - E_disp = {e - d:.8f}, baseline {b['e']:.8f}")
    ok(f"{k}: ESP unchanged", abs(lo - b["min"]) <= 1e-4 and abs(hi - b["max"]) <= 1e-4,
       f"{lo:.4f}/{hi:.4f}, baseline {b['min']}/{b['max']}")
if len(disp) == 2:
    ok("D3 favours folded", disp["fold"] < disp["ext"], f"fold - ext = {(disp['fold'] - disp['ext']) * H2KCAL:.2f} kcal/mol")
ok.finish()
