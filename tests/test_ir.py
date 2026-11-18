"""--ir: water intensities (bend, sym, asym) near the day-session reference, scaled Lorentzian spectrum on 400-4000,
ir.png rendered; --ir without --freq refused."""
import re, tempfile
import numpy as np
from _root import ROOT  # noqa: F401  (repo root on sys.path)
from esp_figure import calc, render


def ir(out):
    log = (out / "method.txt").read_text(encoding="utf-8")
    f = [float(x) for x in re.search(r"frequencies \(cm-1\): (.+)", log).group(1).split(",")]
    i = [float(x) for x in re.search(r"IR intensities \(km/mol\): (.+)", log).group(1).split(",")]
    return f, i, log


with tempfile.TemporaryDirectory() as root:
    try:
        calc("O", "x", root=root, ir=True)
        raise AssertionError("--ir without --freq accepted")
    except SystemExit as e:
        assert "--freq" in str(e), e

    out = calc("O", "w", root=root, opt=True, freq=True, ir=True)
    f, i, log = ir(out)
    assert all(abs(a - b) <= max(0.15 * b, 1.0) for a, b in zip(i, [79.6, 1.8, 20.1])), i
    x, y = np.loadtxt(out / "ir_spectrum.csv", delimiter=",", skiprows=1, unpack=True)
    k = np.argmin(abs(x - 0.96 * f[0]))
    assert abs(y[k] - i[0]) < 0.02 * i[0], (y[k], i[0])          # peak height = intensity (bands far apart)
    assert "FWHM 10" in log and "0.960" in log and "harmonic" in log
    render("w", style="rwb", root=root)
    assert (out / "ir.png").exists()
print("ok", f, i)
