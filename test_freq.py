"""--freq: optimised water is a minimum (3 real modes near the day-session values); planar NH3 is a saddle (1 imaginary);
asking for --freq on a finished run without frequencies recomputes instead of returning the old method.txt;
with D3 + PCM the analytic frequencies match a finite-difference Hessian (so both terms are in it)."""
import re, tempfile
from pathlib import Path
import numpy as np
from pyscf import gto, dft
from pyscf.hessian import thermo
from esp_figure import SOLVENTS, calc, read_xyz


def freqs(out):
    log = (out / "method.txt").read_text(encoding="utf-8")
    f = [float(x) for x in re.search(r"frequencies \(cm-1\): (.+)", log).group(1).split(",")]
    return f, int(re.search(r"imaginary frequencies: (\d+)", log).group(1))


with tempfile.TemporaryDirectory() as root:
    calc("O", "w", root=root, opt=True)
    out = calc("O", "w", root=root, opt=True, freq=True)            # cached run without freq -> recompute
    f, n = freqs(out)
    assert "of a finished optimisation" in (out / "method.txt").read_text(encoding="utf-8")   # not "interrupted"
    assert n == 0 and len(f) == 3, (f, n)
    assert all(abs(a - b) <= 5 for a, b in zip(f, [1710.7, 3720.5, 3844.3])), f
    try:                                   # cached --opt run asked for --freq without --opt: refuse, don't overwrite
        calc("O", "w", root=root, freq=True)
        raise AssertionError("recomputed an --opt run as a single point")
    except SystemExit as e:
        assert "different --opt" in str(e), e

    # D3 + PCM: the analytic Hessian must contain the dispersion and solvent terms -> compare with central differences
    # of analytic gradients (same mf settings as esp_figure.calc) at the optimised geometry.
    out = calc("O", "wp", root=root, opt=True, freq=True, d3=True, solvent="water")
    f, n = freqs(out)
    sym, x = read_xyz(out / "mol.xyz")
    mol = gto.M(atom=list(zip(sym, map(tuple, x))), basis="6-31g*", verbose=0)
    def grad(c):
        mf = dft.RKS(mol.set_geom_(c, unit="Bohr", inplace=False)).density_fit()
        mf.xc, mf.disp = "b3lyp", "d3bj"
        mf = mf.PCM()
        mf.with_solvent.method, mf.with_solvent.eps = "IEF-PCM", SOLVENTS["water"]
        mf.conv_tol = 1e-11
        mf.kernel()
        return mf.nuc_grad_method().kernel()
    c0, h, H = mol.atom_coords(), 1e-3, np.zeros((len(sym), len(sym), 3, 3))
    for a in range(len(sym)):
        for k in range(3):
            d = np.zeros_like(c0)
            d[a, k] = h
            H[a, :, k, :] = (grad(c0 + d) - grad(c0 - d)) / (2 * h)
    fd = np.sort(thermo.harmonic_analysis(mol, (H + H.transpose(1, 0, 3, 2)) / 2, imaginary_freq=False)["freq_wavenumber"])
    assert n == 0 and np.abs(np.array(f) - fd).max() < 5, (f, fd)
    print("D3+PCM analytic vs finite-difference:", f, fd.round(1))

    xyz = Path(root) / "nh3.xyz"
    xyz.write_text("4\nplanar NH3\nN 0 0 0\nH 1.0 0 0\nH -0.5 0.866 0\nH -0.5 -0.866 0\n")
    f, n = freqs(calc(str(xyz), "nh3", root=root, freq=True))
    assert n == 1 and f[0] < 0 < f[1] and len(f) == 6, (f, n)
    assert "geometry not optimised here" in (Path(root) / "nh3" / "method.txt").read_text(encoding="utf-8")
print("ok")
