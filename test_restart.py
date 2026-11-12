"""Restart on formamide: a run that finds 3 frames of opt_traj.xyz (as after a crash) resumes from the last one,
reaches the same minimum in fewer steps, and refuses a trajectory from another level of theory."""
import re, shutil, tempfile
from pathlib import Path
import numpy as np
from esp_figure import calc


def result(out):
    log = (out / "method.txt").read_text(encoding="utf-8")
    return float(re.search(r"SCF energy: (\S+)", log).group(1)), int(re.search(r"optimisation steps: (\d+)", log).group(1)), log


with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
    e_full, n_full, _ = result(calc("NC=O", "f", opt=True, root=a))
    lines = (Path(a) / "f" / "opt_traj.xyz").read_text(encoding="utf-8").splitlines()
    assert len(lines) == n_full * 8, (len(lines), n_full)          # one 6-atom frame per step
    (Path(b) / "f").mkdir()
    # 3 frames + the start of a 4th, as if killed mid-write: the partial frame must be dropped
    (Path(b) / "f" / "opt_traj.xyz").write_text("\n".join(lines[:3 * 8 + 3]) + "\n", encoding="utf-8")
    shutil.copy(Path(b) / "f" / "opt_traj.xyz", Path(b) / "keep.xyz")
    e_res, n_res, log = result(calc("NC=O", "f", opt=True, root=b))
    assert abs(e_res - e_full) < 1e-6 and n_res < n_full, (e_res, e_full, n_res, n_full)
    assert "restarted from step 3" in log, log
    resumed = (Path(b) / "f" / "opt_traj.xyz").read_text(encoding="utf-8").splitlines()
    assert len(resumed) == (3 + n_res) * 8, (len(resumed), n_res)   # restart point not written again
    xyz = lambda rows: np.array([r.split()[1:4] for r in rows], float)
    d = np.abs(xyz(resumed[3 * 8 + 2:4 * 8]) - xyz(resumed[2 * 8 + 2:3 * 8])).max()
    assert d > 1e-5, f"frame 4 repeats frame 3 (max diff {d} Å)"     # first new frame is a real step
    assert "| step 4 E" in resumed[3 * 8 + 1], resumed[3 * 8 + 1]     # numbering continues
    (Path(b) / "g").mkdir()                                          # same frames, but a D3 request: must refuse
    shutil.copy(Path(b) / "keep.xyz", Path(b) / "g" / "opt_traj.xyz")
    try:
        calc("NC=O", "g", opt=True, root=b, d3=True)
        raise AssertionError("resumed from a trajectory at another level of theory")
    except SystemExit as e:
        assert "different molecule" in str(e)
print(f"ok ({n_full} steps full, {n_res} resumed, dE {e_res - e_full:.1e} Eh)")
