# Related work: other free ESP-map tools

Survey done 2026-11-18. Method: web search plus GitHub's repository search with generic terms ("electrostatic
potential pyscf", "ESP isosurface", "molecular electrostatic potential", "gaussview", ...). The five closest
repositories were cloned and their code and docs read; the rest were judged from their READMEs. Nothing was run.
Not searched: GitLab, institutional code, papers without code. Star counts are 0–6 for almost everything: these are
personal research tools, not established packages. Re-run the search before claiming anything about novelty.

## Summary

No other project combines what esp-figure does: GaussView-style figures (transparent surface over ball-and-stick)
from one command, checked against a real Gaussian 16 + Multiwfn job, with local extrema validated against Multiwfn.
One project, **espmap**, shares the core pipeline but aims at measurement rather than figures.

The vertex-only ESP evaluation is **not new**: Bulat et al., *J. Mol. Model.* 2010, and Lu & Chen, *J. Mol. Graph.
Model.* 2012 (Multiwfn) evaluate properties directly on a polygonal surface. Don't claim it as an invention.

## espmap — the close twin

<https://github.com/Azuromalachite/espmap> (MIT; ~5,700-line `esp_map.py`, 464 tests, six adversarial reviews in
`docs/`, measured error budget in `bench/`; also built with Claude Code on a WSL laptop.)

Same pipeline: PySCF DFT → density on a grid → marching cubes → ESP only at the surface vertices (~100× cheaper than
a full grid, no interpolation error).

| | espmap | esp-figure |
|---|---|---|
| Goal | measurement: numbers, uncertainty, per-site statistics | GaussView-style publication figures |
| Surface | ρ = 0.002 a.u. (Bader) | ρ = 0.001 a.u. (Multiwfn, GaussView, the Gaussian reference) |
| Picture | opaque surface only, own matplotlib z-buffer renderer, no ball-and-stick | 70 % transparent surface over ball-and-stick (PyVista) |
| Default level | B3LYP/def2-TZVP, gas | B3LYP/6-31G(d); `--ref-level` PBE0-D3(BJ)/6-311+G(d,p)/SMD |
| Gaussian / Multiwfn check | none | ESP extrema within 0.4 %, local extrema 6 + 2 within 0.2 Å |
| Local extrema | no (σ-hole, per-atom sites) | yes (`render --extrema all`) |
| Its extras | conformer ensembles, record comparison with uncertainty, `--gpu`, Colab notebook, interactive HTML, JSON record with provenance keys, structure gate | freq/IR, NCI, IGM, Fukui, charges, orbitals, D3, 20 locked sanity checks |

Its measured findings that bear on this project:

1. **No specular highlight**: a white glint at a camera-dependent spot reads as an extremum. Shading is kept to a
   0.62–1.0 span. esp-figure uses `specular=0.3` on the surface: worth testing without it.
2. **Solvent convention**: like esp-figure (and Gaussian/Multiwfn), the default maps the solute *polarised by* the
   continuum, without the continuum's own surface charges. Adding them almost cancels the shift on chlorobenzene's
   σ-hole: gas → PCM water −3.60 kcal/mol without, +0.05 with. So "water strengthens the extrema ~20 %" holds
   under this convention only; say so in captions and papers.
3. **Conformers**: folded conformers of a C18 acetate moved V_min by up to 5.2 kcal/mol, more than the basis set.
   Agrees with the PAM3 fold/ext result being "comparable", not "folded preferred".
4. **Basis-set error is molecule-specific** (def2-SVP → def2-TZVP moved V_max +1.5 to +2.8 kcal/mol on four
   molecules, −0.76 on bromobenzene): one molecule's check licenses nothing about another.
5. **Colour maps**: rainbow and 3-stop red-green-blue are most saturated at V = 0, pulling the eye to the least
   meaningful value. Ions (field never changes sign) get a sequential scale instead of a diverging one.
6. **GPU**: GPU4PySCF on a Colab L4 matched the CPU to < 0.001 kcal/mol, 4.3–9.6× faster than a 16-thread laptop
   (closed-shell, gas, density-fitted only). Relevant to the lab-computer decision.
7. `docs/prior-art.md` there is a good, verified reference list (Politzer, Bader, Bulat, Lu & Chen, Murray GIPF).
   It notes that Lu & Chen 2012 discuss **artificial extrema from uneven discretisation**: the tiny PAM3 extrema
   (e.g. a maximum of −0.001 a.u.) may be that.

## Other projects

| Project | What it is | Relation to esp-figure |
|---|---|---|
| [xyzrender](https://github.com/aligfellow/xyzrender) | Polished SVG/PNG/GIF molecule renderer (Goodfellow & Nguyen, *JCTC* 2026) | ESP is a 2D approximation: voxels near the isosurface projected to a heatmap, clipped by density contour rings; needs density + ESP cubes on one grid; range defaults to the 5–95th percentile. Not usable for exact extrema; strong for vector graphics |
| [OrbVista](https://github.com/ts-quantum/orbvista) | Desktop GUI (PySide6 + PyVista + PySCF) for orbitals, ESP, spin density from molden/fchk/cube | Same vertex-ESP idea but no SCF of its own; `int1e_grids` on all vertices at once (points × nao² array, tens of GB at PAM3 size); POV-Ray and Blender export |
| [Sigma-Hole-Analysis](https://github.com/nvonwolff/Sigma-Hole-Analysis) | Local ESP extrema and σ-holes from ORCA density + ESP cubes, PQR output for VMD | Same extremum rule as `esp_local_extrema` (beat all neighbours within a radius); ESP interpolated from cubes rather than exact at vertices |
| [VHoleMapper](https://github.com/lgfachini/VHoleMapper-VHM) | σ/π-hole detection with local frames, MLS derivative check, sector validation | Reads Multiwfn's `vtx.txt`; analysis only |
| [EPM-Studio](https://github.com/Sowden94/EPM-Studio) | Browser teaching tool (draw, map, export 4K/GIF) | Live maps are Gasteiger point charges on a vdW envelope, not QM; six bundled PySCF RHF/6-31G* examples; red negative, green zero, blue positive |
| [VisMap](https://github.com/aaan1s/VisMap) | Mayavi viewer for Multiwfn ESP on several isosurfaces with critical points | 2023, Windows, needs Multiwfn cubes |
| [gaussian-dsh-plugin](https://github.com/yangdw2024/gaussian-dsh-plugin) | AI-agent toolkit (MCP server): SMILES → Gaussian 16 → formchk → Multiwfn → VMD | Automates the commercial workflow; still needs Gaussian 16 |
| [scientific-figure-skills](https://github.com/Nth-5620/scientific-figure-skills) | Agent skills for Blender Cycles figures (ball-and-stick, isosurfaces, ESP) | A route to VMD/ray-traced polish if ever wanted |
| [pyEPMap](https://github.com/anchieta-oliveira/pyEPMap) | GPU force-field ESP maps of proteins | Different field |
| [mmml ESP docs](https://mmml.readthedocs.io/en/latest/esp_cube_generation.html) | GPU PySCF → ESP cube | Compute/export step only |

## Ideas to consider (not built)

- Test the surface without specular shading (espmap finding 1).
- One caption sentence on the solvent convention (finding 2).
- Look at espmap's Colab notebook before building one here.
- A minimum |V| or prominence threshold for `--extrema all`, against discretisation artefacts (finding 7).
