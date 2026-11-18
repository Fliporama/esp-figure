"""Restart: a killed --opt resumes from its last step and reaches the same minimum.

Contract: during calc(..., opt=True), each optimisation step appends its geometry as one frame to
runs/<name>/opt_traj.xyz (multi-frame xyz, written as it goes). Re-running the same calc after a crash
(no method.txt yet) starts the optimisation from the last frame. method.txt gets "optimisation steps: <N>"
(steps taken by this run).
Pass if formamide killed after 3 steps and resumed gives the uninterrupted final energy within 1e-6 Eh,
in fewer steps. (Day-session check with geomeTRIC defaults: 7 steps full, 6 resumed, dE 4e-8 Eh.)
"""
import re, subprocess, sys, tempfile, time
from pathlib import Path
from _util import ROOT, Checks, esp_figure, skip

if "opt_traj.xyz" not in Path(esp_figure.__file__).read_text(encoding="utf-8"):
    skip("esp_figure.py does not write opt_traj.xyz yet")
SMI = "NC=O"


def result(out):
    log = (out / "method.txt").read_text(encoding="utf-8")
    return float(re.search(r"SCF energy: (\S+)", log).group(1)), int(re.search(r"optimisation steps: (\d+)", log).group(1))


ok = Checks()
with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
    e_full, n_full = result(esp_figure.calc(SMI, "f", opt=True, root=a))
    traj = Path(b) / "f" / "opt_traj.xyz"
    p = subprocess.Popen([sys.executable, "-c", f"from esp_figure import calc; calc({SMI!r}, 'f', opt=True, root={b!r})"],
                         cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    frames, t0 = 0, time.time()
    while p.poll() is None and frames < 3 and time.time() - t0 < 900:
        time.sleep(0.2)
        frames = traj.read_text().split("\n").count("6") if traj.exists() else 0
    killed = p.poll() is None
    p.kill(); p.wait()
    ok("killed mid-optimisation after 3 steps", killed and frames >= 3, f"{frames} frames, killed={killed}")
    if killed:
        e_res, n_res = result(esp_figure.calc(SMI, "f", opt=True, root=b))
        ok("same final energy", abs(e_res - e_full) <= 1e-6, f"{e_res:.8f} vs {e_full:.8f}")
        ok("fewer steps when resumed", n_res < n_full, f"{n_res} vs {n_full}")
ok.finish()
