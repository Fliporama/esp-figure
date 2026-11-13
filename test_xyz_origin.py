"""An .xyz single point says where its geometry was optimised: same level (fine), other level (warning: not a
stationary point, imaginary modes may be artefacts), unknown (not optimised here). Imaginary modes are split into
noise (within FREQ_NOISE of zero) and clearly imaginary; the raw count stays (sanity contract)."""
import re, tempfile
from pathlib import Path
import esp_figure as E

with tempfile.TemporaryDirectory() as root:
    opt = E.calc("O", "w_opt", root=root, opt=True)
    xyz = str(opt / "mol.xyz")
    same = (E.calc(xyz, "w_same", root=root, freq=True) / "method.txt").read_text(encoding="utf-8")
    assert "optimised at B3LYP/6-31G(d) in run w_opt" in same, same
    assert "optimised at this level in run w_opt" in same and "WARNING" not in same, same
    other = (E.calc(xyz, "w_d3", root=root, freq=True, d3=True) / "method.txt").read_text(encoding="utf-8")
    assert "WARNING: geometry optimised at B3LYP/6-31G(d) (run w_opt), not at this level" in other, other
    gas = (E.calc(xyz, "w_pcm", root=root, solvent="water") / "method.txt").read_text(encoding="utf-8")
    assert "only (geometry not optimised in solvent)" in gas, gas   # optimised in gas: the old line is right
    nh3 = Path(root) / "nh3.xyz"
    nh3.write_text("4\nplanar NH3\nN 0 0 0\nH 1.01 0 0\nH -0.505 0.875 0\nH -0.505 -0.875 0\n")
    log = (E.calc(str(nh3), "nh3", root=root, freq=True) / "method.txt").read_text(encoding="utf-8")
    assert re.search(r"imaginary frequencies: 1 \(.*0 of them within 50 cm-1 of zero.*1 clearly imaginary", log), log
    assert "geometry not optimised here" in log, log
print("ok")
