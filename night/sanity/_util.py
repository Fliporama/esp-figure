"""Shared helpers for the sanity scripts. Exit codes: 0 pass, 1 fail, 77 = feature not built yet (skip)."""
import inspect, re, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import esp_figure  # noqa: E402

H2KCAL = 627.5095
# Gas-phase, no-D3 baselines on the locked geometries (method.txt of runs/pam3_opt, runs/pam3_ext_opt, 2026-11-11)
BASE = {"fold": {"xyz": ROOT / "night/baseline/pam3_opt.xyz", "e": -782.48653680, "min": -0.0663, "max": 0.0780},
        "ext": {"xyz": ROOT / "night/baseline/pam3_ext_opt.xyz", "e": -782.47776309, "min": -0.0696, "max": 0.0748}}
UNSPEC_PAM3 = "CC(C(N)=O)CC(C(N)=O)CC(C)C(N)=O"


def skip(msg):
    print("SKIP:", msg)
    sys.exit(77)


def need(param):
    """Skip unless esp_figure.calc() has this keyword argument (the agent's feature flag)."""
    if param not in inspect.signature(esp_figure.calc).parameters:
        skip(f"calc() has no '{param}' argument yet")


def calc(spec, name, **kw):
    """Run calc in a temp dir; return (method.txt text, scf energy, esp min, esp max)."""
    with tempfile.TemporaryDirectory() as tmp:
        log = (esp_figure.calc(str(spec), name, root=tmp, **kw) / "method.txt").read_text(encoding="utf-8")
    e = float(re.search(r"SCF energy: (\S+)", log).group(1))
    lo, hi = map(float, re.search(r"ESP range on surface: (\S+) to (\S+)", log).groups())
    return log, e, lo, hi


class Checks:
    """Collect named pass/fail lines; finish() exits 0 only if all passed."""
    def __init__(self):
        self.ok = True

    def __call__(self, name, cond, detail=""):
        self.ok &= bool(cond)
        print(f"{'PASS' if cond else 'FAIL'} {name}: {detail}")

    def finish(self):
        sys.exit(0 if self.ok else 1)
