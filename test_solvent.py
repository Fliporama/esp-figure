"""PCM water on water: solvation lowers the energy by a few kcal/mol and polarises the density (ESP extremes grow)."""
import re, tempfile
from esp_figure import calc


def run(root, name, **kw):
    log = (calc("O", name, root=root, **kw) / "method.txt").read_text(encoding="utf-8")
    num = lambda pat: [float(x) for x in re.search(pat, log).groups()]
    return log, num(r"SCF energy: (\S+)")[0], num(r"ESP range on surface: (\S+) to (\S+)")


with tempfile.TemporaryDirectory() as root:
    _, e0, (lo0, hi0) = run(root, "gas")
    log, e1, (lo1, hi1) = run(root, "aq", solvent="water")
    dg = (e1 - e0) * 627.5095
    assert "IEF-PCM(water, eps 78.3553)" in log and "solvent: implicit water" in log, log
    assert -12 < dg < -3, f"dG_solv {dg:.2f} kcal/mol"
    assert 0 < lo1 / lo0 - 1 < 0.5 and 0 < hi1 / hi0 - 1 < 0.5, (lo0, hi0, lo1, hi1)   # grow, but < 50 %
    log, e3, esp3 = run(root, "aq_d3", solvent="water", d3=True)   # queued jobs combine both: D3 must survive .PCM()
    d = float(re.search(r"dispersion energy: (\S+) Eh", log).group(1))
    assert -1e-3 < d < 0 and abs(e3 - e1 - d) < 1e-7, ("D3 lost or doubled under PCM", e3, e1, d)
    assert esp3 == [lo1, hi1], ("D3 changed the PCM density", esp3)
    log, e2, _ = run(root, "aq_opt", solvent="water", opt=True)   # PCM gradients work (queued jobs use --opt)
    assert "in the SCF and the optimisation" in log and "converged: True" in log and e2 < e1, (e2, e1)
    try:                                   # same name, different model must not reuse the gas result
        calc("O", "gas", root=root, solvent="water")
        raise AssertionError("reused a gas-phase run for a solvent request")
    except SystemExit as e:
        assert "different level of theory" in str(e)
print(f"ok (dG_solv {dg:.2f} kcal/mol, ESP {lo0:.4f}/{hi0:.4f} -> {lo1:.4f}/{hi1:.4f})")
