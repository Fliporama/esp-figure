"""D3 on water: dispersion < 0, energy shifts by exactly that amount, ESP unchanged (D3 is post-SCF)."""
import re, tempfile
from esp_figure import calc


def run(root, name, **kw):
    log = (calc("O", name, root=root, **kw) / "method.txt").read_text(encoding="utf-8")
    num = lambda pat: [float(x) for x in re.search(pat, log).groups()]
    return log, num(r"SCF energy: (\S+)")[0], num(r"ESP range on surface: (\S+) to (\S+)")


with tempfile.TemporaryDirectory() as root:
    _, e0, esp0 = run(root, "plain")
    log, e1, esp1 = run(root, "d3", d3=True)
    d = float(re.search(r"dispersion energy: (\S+) Eh", log).group(1))
    assert "B3LYP-D3(BJ)/6-31G(d)" in log
    assert -1e-3 < d < 0, d
    assert abs(e1 - e0 - d) < 1e-7, (e1, e0, d)
    assert esp0 == esp1, (esp0, esp1)
    try:                                   # same name, different level must not reuse the old result
        calc("O", "plain", root=root, d3=True)
        raise AssertionError("reused a non-D3 run for a D3 request")
    except SystemExit as e:
        assert "different level of theory" in str(e)
print("ok")
