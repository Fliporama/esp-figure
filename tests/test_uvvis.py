"""--uvvis (unvalidated: no locked sanity check yet). Formaldehyde, B3LYP/6-31+G(d) TD-DFT at the 6-31G(d) geometry:
S1 is the n->pi* state near 4 eV and dark by symmetry (f < 1e-3); the energies match a direct PySCF TDDFT in
6-31+G(d) (so the basis switch really happens); the spectrum peak height of an isolated band is
1.3062974e8 * f / sigma (sigma = 1/e half-width in cm-1, from FWHM 0.3 eV); uvvis.png renders; --uvvis with
--solvent / --spin is refused."""
import re, tempfile
from pathlib import Path
import numpy as np
from pyscf import gto, dft
from _root import ROOT  # noqa: F401  (repo root on sys.path)
from esp_figure import calc, render, read_xyz

with tempfile.TemporaryDirectory() as root:
    out = calc("C=O", "f", root=root, opt=True, uvvis=True)
    log = (out / "method.txt").read_text(encoding="utf-8")
    E = [float(x) for x in re.search(r"excitation energies \(eV\): (.+)", log).group(1).split(",")]
    f = [float(x) for x in re.search(r"oscillator strengths: (.+)", log).group(1).split(",")]
    assert len(E) == len(f) == 10 and 3.6 < E[0] < 4.3 and f[0] < 1e-3, (E, f)
    assert "6-31+G(d)" in log and "FWHM 0.3 eV" in log and "unvalidated" in log

    sym, xyz = read_xyz(out / "mol.xyz")
    mf = dft.RKS(gto.M(atom=list(zip(sym, map(tuple, xyz))), basis="6-31+g*", verbose=0)).density_fit()
    mf.xc = "b3lyp"
    mf.kernel()
    td = mf.TDDFT()
    td.nstates = 10
    td.kernel()
    assert np.allclose(td.e * 27.211386, E, atol=2e-3), (td.e * 27.211386, E)

    e, nm, eps = np.loadtxt(out / "uvvis.csv", delimiter=",", skiprows=1, unpack=True)
    k = int(np.argmax(f))
    sigma = 0.3 / (2 * np.sqrt(np.log(2))) * 8065.544        # cm-1
    peak = np.interp(E[k], e, eps)
    others = sum(1.3062974e8 * b / sigma * np.exp(-((a - E[k]) * 8065.544 / sigma) ** 2) for a, b in zip(E, f) if a != E[k])
    assert abs(peak - 1.3062974e8 * f[k] / sigma - others) < 0.01 * peak, (peak, f[k])
    assert np.allclose(nm, 1239.84193 / e, rtol=0, atol=0.01)   # csv rounds nm to 0.01
    # independent of the 1.3062974e8 constant: f = 4.32e-9 * integral of epsilon over wavenumber (all bands inside the grid)
    area = np.trapezoid(eps, e * 8065.544)
    assert abs(4.319e-9 * area / sum(f) - 1) < 0.01, (4.319e-9 * area, sum(f))
    render("f", style="rwb", root=root)
    assert (out / "uvvis.png").exists()

    ch3i = Path(root) / "ch3i.xyz"
    ch3i.write_text("5\nCH3I\nC 0 0 0\nI 0 0 2.14\nH 1.03 0 -0.36\nH -0.51 0.89 -0.36\nH -0.51 -0.89 -0.36\n")
    for spec, kw in (("C=O", {"solvent": "water"}), (str(ch3i), {"spin": 1}), (str(ch3i), {})):
        try:
            calc(spec, "bad", root=root, uvvis=True, **kw)
            raise AssertionError(f"accepted {kw}")
        except SystemExit as ex:
            assert "--uvvis" in str(ex), ex
print("ok", E, f)
