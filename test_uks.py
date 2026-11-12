"""--spin: planar CH3 doublet runs as UKS (energy = direct PySCF UKS, <S^2> ~0.75, ESP from the total density);
radicals without --spin and spins that don't fit the electron count are refused before any compute."""
import re, tempfile
from pathlib import Path
import numpy as np
from pyscf import gto, dft
from esp_figure import calc, read_xyz


def refused(word, *a, **kw):
    try:
        calc(*a, **kw)
    except SystemExit as e:
        assert word in str(e), e
        return
    raise AssertionError(f"not refused: {a} {kw}")


with tempfile.TemporaryDirectory() as root:
    xyz = Path(root) / "ch3.xyz"
    xyz.write_text("4\nmethyl\nC 0 0 0\nH 1.08 0 0\nH -0.54 0.935 0\nH -0.54 -0.935 0\n")
    out = calc(str(xyz), "ch3", root=root, spin=1)
    log = (out / "method.txt").read_text(encoding="utf-8")
    e = float(re.search(r"SCF energy: (\S+)", log).group(1))
    s2 = float(re.search(r"<S\^2>: (\S+)", log).group(1))
    lo, hi = map(float, re.search(r"ESP range on surface: (\S+) to (\S+)", log).groups())
    sym, x = read_xyz(out / "mol.xyz")
    mf = dft.UKS(gto.M(atom=list(zip(sym, map(tuple, x))), basis="6-31g*", spin=1, verbose=0)).density_fit()
    mf.xc = "b3lyp"
    assert abs(e - mf.kernel()) < 1e-6, (e, mf.e_tot)
    assert 0.75 <= s2 <= 0.77, s2
    assert -0.05 < lo < 0 < hi < 0.05, (lo, hi)     # alpha-only density would give a strongly positive ESP
    assert "UB3LYP/6-31G(d) (doublet)" in log
    refused("radical", "[CH3]", "a", root=root)
    refused("does not fit", str(xyz), "b", root=root, spin=2)
    refused(">= 0", str(xyz), "b", root=root, spin=-1)
    refused("needs .xyz", "[CH3]", "c", root=root, spin=1)          # MMFF has no radical types
    refused("not supported", str(xyz), "d", root=root, spin=1, freq=True)
    refused("different level", str(xyz), "ch3", root=root, spin=3)  # cached doublet is not a quartet

    # UKS through --opt + D3 + PCM: converges, stays a clean doublet, stays planar, ESP still from the total density
    log = (calc(str(xyz), "ch3p", root=root, spin=1, opt=True, d3=True, solvent="water") / "method.txt").read_text(encoding="utf-8")
    s2p = float(re.search(r"<S\^2>: (\S+)", log).group(1))
    assert "converged: True" in log and 0.75 <= s2p <= 0.77 and "dispersion energy" in log and "IEF-PCM" in log, log
    sym, x = read_xyz(Path(root) / "ch3p" / "mol.xyz")
    assert abs(np.linalg.det(x[1:] - x[0])) < 1e-2, x                 # D3h minimum: all four atoms in one plane
print(f"ok (<S^2> {s2}, ESP {lo} to {hi})")
