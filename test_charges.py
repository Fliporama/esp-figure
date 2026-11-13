"""--charges mk|chelpg: the fit recovers known point charges exactly; water MK/CHelpG charges are sensible,
symmetric and sum to zero; a cached run recomputes when a different scheme is asked for."""
import re, tempfile
from pathlib import Path
import numpy as np
from esp_figure import calc, fit_charges, fit_points

# Fit alone: ESP of three point charges, sampled on MK points, must give those charges back (sum constrained to 0).
sym, xyz = ["O", "H", "H"], np.array([[0, 0, 0.1173], [0, 0.7572, -0.4692], [0, -0.7572, -0.4692]])
q0 = np.array([-0.8, 0.4, 0.4])
for scheme in ("mk", "chelpg"):
    p, _ = fit_points(scheme, sym, xyz)
    V = (q0 * 0.529177 / np.linalg.norm(p[:, None] - xyz[None], axis=2)).sum(1)
    q, rr = fit_charges(p, V, xyz, 0)
    assert np.allclose(q, q0, atol=1e-8) and rr < 1e-8, (scheme, q, rr)

with tempfile.TemporaryDirectory() as root:
    w = Path(root) / "water.xyz"
    w.write_text("3\nwater\nO 0 0 0.117300\nH 0 0.757200 -0.469200\nH 0 -0.757200 -0.469200\n")
    got = {}
    for scheme, tag in (("mk", "MK"), ("chelpg", "CHelpG")):
        out = calc(str(w), "w", root=root, charges=scheme)    # second pass: cached run, other scheme -> recompute
        log = (out / "method.txt").read_text(encoding="utf-8")
        assert f"atomic charges: {tag} " in log, log
        rr = float(re.search(r"ESP fit RRMS: (\S+)", log).group(1))
        q = np.array([float(l.split()[2]) for l in (out / "charges.txt").read_text(encoding="utf-8").splitlines()
                      if not l.startswith("#")])
        assert abs(q.sum()) < 1e-5 and abs(q[1] - q[2]) < 0.01 and -0.95 < q[0] < -0.70 and rr < 0.15, (scheme, q, rr)
        got[scheme] = q
    assert abs(got["mk"][0] - got["chelpg"][0]) < 0.1, got
    log = (calc(str(w), "wo", root=root, charges="mk", orbitals=True) / "method.txt").read_text(encoding="utf-8")
    assert "atomic charges: MK " in log and "HOMO:" in log, log          # orbitals must not drop the charges lines
print(f"ok (water q(O): MK {got['mk'][0]:.3f}, CHelpG {got['chelpg'][0]:.3f})")
