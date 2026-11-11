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

    # --sanity: exit 0 pass, 77 skip, other or timeout fail
    def sanity(codes):
        ent = {}
        for i, c in enumerate(codes):
            (d / f"s{i}.py").write_text(f"import sys, time; print('PASS x' if {c} == 0 else 'FAIL x'); "
                                        f"time.sleep(5 if {c} == 9 else 0); sys.exit({c})")
            ent[f"s{i}"] = {"script": str(d / f"s{i}.py"), "item": "t", "timeout": 2}
        ref.write_text(json.dumps({"regression": {}, "sanity": ent}))
        rc = subprocess.run([sys.executable, str(HERE / "check.py"), "--sanity", "--ref", str(ref), "--out", str(out)],
                            cwd=HERE.parent, capture_output=True, text=True).returncode
        return rc, [s["status"] for s in json.loads(out.read_text())["sanity"]]

    assert sanity([0, 77]) == (0, ["pass", "skip"])
    assert sanity([0, 1, 9]) == (1, ["pass", "fail", "fail"])
print("ok")
