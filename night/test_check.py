"""check.py must pass on a matching reference and fail on a wrong or missing value (water, seconds)."""
import json, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(ref, out):
    return subprocess.run([sys.executable, str(HERE / "check.py"), "--ref", str(ref), "--out", str(out)],
                          cwd=HERE.parent, capture_output=True, text=True).returncode


with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    (d / "water.xyz").write_text("3\nwater\nO 0 0 0.1173\nH 0 0.7572 -0.4692\nH 0 -0.7572 -0.4692\n")
    ref, out = d / "ref.json", d / "out.json"

    def write(e):
        ref.write_text(json.dumps({"regression": {"water_sp": {"xyz": str(d / "water.xyz"),
                                   "scf_energy": {"value": e, "tol": 1e-6}}}, "sanity": {}}))

    write(None)                                   # missing value -> fail, but the value is reported
    assert run(ref, out) == 1
    c = json.loads(out.read_text())["checks"][0]
    assert c["expected"] is None and c["pass"] is False and c["value"] < -76
    e = c["value"]

    write(e)                                      # matching -> pass
    assert run(ref, out) == 0, out.read_text()
    assert json.loads(out.read_text())["all_pass"] is True

    write(e + 1e-3)                               # off by 1 mEh -> fail
    assert run(ref, out) == 1
    assert json.loads(out.read_text())["checks"][0]["pass"] is False
print("ok")
