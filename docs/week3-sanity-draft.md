# Week-3 sanity checks: DRAFT for user approval (2026-11-12)

Not locked, not in `reference.json` yet. Once approved: one script per row in `night/sanity/`, each
docstring the contract, each tested against a throwaway reference implementation and one deliberate
bug (as for weeks 1–2), then listed in `reference.json`.

| Item | Contract (what the night agent builds) | Test system | Pass if | Reference source |
|---|---|---|---|---|
| MK charges | `calc(..., charges="mk")` (CLI `--charges mk`): Merz–Kollman ESP-fitted charges (points on 1.4/1.6/1.8/2.0 × vdW shells, 4–6 pts/Å², total-charge constraint); `charges.txt` + method.txt line naming the scheme | water, formamide | Σq = total charge (1e-6); water q(O) −0.75..−0.95, q(H) = q(H') (1e-4); formamide q(O) < 0, q(N) < 0, q(carbonyl C) > 0; ESP fit RRMS < 0.15; charges reproduce the surface ESP better than Mulliken (RMS) | literature MK for water at B3LYP/6-31G(d) ≈ −0.80/+0.40; fixed numbers from a throwaway reference run on our own code before locking |
| RDG / NCI | `calc(..., nci=True)`: cubes `rdg.cube` (s = \|∇ρ\| / (2(3π²)^⅓ ρ^{4/3})) and `sl2rho.cube` (sign(λ₂)ρ); render draws the s = 0.5 isosurface coloured by sign(λ₂)ρ in [−0.04, +0.04] (blue H-bond, green vdW, red steric) | water dimer (.xyz, linear H-bond), PAM3 fold geometry (locked baseline) | water dimer: an s = 0.5 lobe between H···O with sign(λ₂)ρ < −0.015; PAM3 fold: a blue lobe on the H26···O16 axis, none needed on ext; isolated water: no lobe with \|sign(λ₂)ρ\| > 0.01 off-atom | Multiwfn on a molden export once (day session) for the dimer's lobe min sign(λ₂)ρ, ±20 % |
| Fukui | `calc(..., fukui=True)`: f⁺ = ρ(N+1) − ρ(N), f⁻ = ρ(N) − ρ(N−1) at fixed geometry (UKS for N±1; needs the `uks` item), condensed per atom (Hirshfeld or Mulliken differences) in `fukui.txt` | formaldehyde, formamide | Σ condensed f = 1 (±0.02) for each; formaldehyde: f⁺ largest on C, f⁻ largest on O; formamide: f⁻ largest on O or N (not C) | textbook ordering; numbers from a throwaway reference run |
| def2 + ECP | `.xyz` input with heavy elements (Z > 36) uses def2-SVP + def2 ECP automatically, method.txt says so; MMFF path still refuses them (guard) | HI (.xyz), CH₃I (.xyz) | SCF converges; method.txt names def2-SVP + ECP for I and 6-31G(d) for the rest (or def2-SVP throughout: decide); HI dipole direction H⁺→I⁻; guard: `[I-]` SMILES still refused with a clear message | PySCF direct run on the same geometry, energy within 1e-6 Eh |

## Decisions needed from the user

1. MK only, or also CHelpG (grid-based; same fit code, different point selection)? Proposed: MK only.
2. NCI: own code (≈40 lines, as proposed in IMPROVEMENTS §5) checked against Multiwfn once, or Multiwfn only? Proposed: own code.
3. Fukui depends on UKS (night 3). Proposed: schedule it only after `uks` passes.
4. def2: def2-SVP everywhere for heavy-element inputs, or mixed (6-31G(d) light / def2-SVP + ECP heavy)? Proposed: def2-SVP everywhere for such inputs; mixed bases complicate the caption.
