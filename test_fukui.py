"""--fukui: formaldehyde f+/f- each sum to 1, match a direct PySCF RKS/UKS Mulliken calculation, and order as the
textbook says (f- largest on O; f+ on C and O above H); --fukui with --spin is refused before any compute."""
import tempfile
from pathlib import Path
import numpy as np
from pyscf import gto, dft
from esp_figure import calc, read_xyz


def chg(sym, xyz, q, s, pcm=False):
    mf = (dft.UKS if s else dft.RKS)(gto.M(atom=list(zip(sym, map(tuple, xyz))), basis="6-31g*", charge=q, spin=s,
                                           verbose=0)).density_fit()
    mf.xc = "b3lyp"
    if pcm:
        mf = mf.PCM()
        mf.with_solvent.method, mf.with_solvent.eps = "IEF-PCM", 78.3553
    mf.kernel()
    return mf.mulliken_pop(verbose=0)[1]


def fukui(out):
    rows = [l.split() for l in (out / "fukui.txt").read_text(encoding="utf-8").splitlines() if not l.startswith("#")]
    return [r[1] for r in rows], np.array([[float(r[2]), float(r[3])] for r in rows])


with tempfile.TemporaryDirectory() as root:
    out = calc("C=O", "ch2o", root=root, fukui=True)
    els, f = fukui(out)
    sym, xyz = read_xyz(out / "mol.xyz")
    assert els == sym and np.allclose(f.sum(0), 1, atol=1e-4), f
    q0, qa, qc = chg(sym, xyz, 0, 0), chg(sym, xyz, -1, 1), chg(sym, xyz, 1, 1)
    assert np.abs(f - np.c_[q0 - qa, qc - q0]).max() < 1e-3, (f, np.c_[q0 - qa, qc - q0])
    o, c, h = sym.index("O"), sym.index("C"), [i for i, s in enumerate(sym) if s == "H"]
    assert f[:, 1].argmax() == o and min(f[o, 0], f[c, 0]) > f[h, 0].max(), f
    assert "basis-limited" in (out / "method.txt").read_text(encoding="utf-8")
    # --solvent applies to the ions too: matches direct PCM runs on the same geometry, and differs from gas phase
    x = Path(root) / "ch2o.xyz"
    x.write_text((out / "mol.xyz").read_text())
    _, fw = fukui(calc(str(x), "ch2o_w", root=root, fukui=True, solvent="water"))
    ref = np.c_[chg(sym, xyz, 0, 0, 1) - chg(sym, xyz, -1, 1, 1), chg(sym, xyz, 1, 1, 1) - chg(sym, xyz, 0, 0, 1)]
    assert np.abs(fw - ref).max() < 1e-3 and np.abs(fw - f).max() > 5e-3, (fw, ref, f)
    x = Path(root) / "ch3.xyz"
    x.write_text("4\nmethyl\nC 0 0 0\nH 1.08 0 0\nH -0.54 0.935 0\nH -0.54 -0.935 0\n")
    try:
        calc(str(x), "r", root=root, spin=1, fukui=True)
        raise AssertionError("--fukui with --spin not refused")
    except SystemExit as e:
        assert "closed-shell" in str(e), e
print(f"ok (CH2O f+ C {f[c, 0]:.3f} O {f[o, 0]:.3f}; f- O {f[o, 1]:.3f})")
