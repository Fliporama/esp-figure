"""DFT re-ranking of the lowest MMFF conformers.

Contract: calc(<SMILES>, ..., rerank=5)  (CLI --rerank 5) takes the 5 lowest-MMFF *distinct* conformers
(MMFF often lands several embeddings in the same minimum; drop duplicates first), runs a
B3LYP single point on each, and continues with the lowest. method.txt gets one line
  "DFT re-ranking energies: <E1>, <E2>, <E3>, <E4>, <E5> Eh"
Pass on syndiotactic PAM3 (esp_figure.PAM3) if: 5 distinct energies are listed, and the final SCF energy
(no --opt) equals the lowest of them within 1e-6 Eh, i.e. the lowest really was the one used.
"""
import re
from _util import Checks, calc, esp_figure, need, skip

need("rerank")
smi = getattr(esp_figure, "PAM3", None) or skip("esp_figure.PAM3 not defined yet (stereo item)")
ok = Checks()
log, e, *_ = calc(smi, "rerank", rerank=5)
m = re.search(r"DFT re-ranking energies: (.+) Eh", log)
es = [float(x) for x in m.group(1).split(",")] if m else []
ok("5 distinct DFT energies in method.txt", len(es) == 5 and min(abs(x - y) for i, x in enumerate(es) for y in es[i + 1:]) > 1e-7,
   f"{es}")
ok("chosen = lowest", bool(es) and abs(e - min(es)) <= 1e-6, f"final {e:.8f}, lowest {min(es) if es else None}")
ok.finish()
