# Week-3 sanity checks: LOCKED 2026-11-13 (draft 2026-11-12, approved with amendments 2026-11-13)

The scripts in `night/sanity/{charges,nci,fukui,def2}.py` are the contract; their docstrings win over this table.
Each was tested against a throwaway reference implementation (all pass) and one deliberate bug (all caught):
MK distances in Å instead of bohr; sign(lambda1) instead of sign(lambda2); f+ and f- swapped; full Z instead of the
ECP effective charge in the nuclear ESP.

## Limits changed from the table below, measured on the reference implementation

| Check | Table | Locked | Why |
|---|---|---|---|
| sum q | 1e-6 | 1e-4 | charges.txt holds 6 decimals; formamide read back at -1.0e-6 |
| water MK q(O) | -0.95..-0.75 | -0.95..-0.70 | reference gave -0.753: too close to the edge for a correct but different point set |
| MK beats Mulliken | water | formamide, RMS < 0.8 x Mulliken | water: 0.0065 vs 0.0066 a.u. (no margin); formamide 0.0042 vs 0.0065 |
| formaldehyde f+ | largest on C | C and O each above every H | C 0.278 vs O 0.274: Mulliken cannot call it |
| NCI cube vs direct | 1e-6 a.u. | 1e-3 relative | cube files keep ~6 significant digits, and the script's own SCF differs slightly (reference 1.05e-4 relative; a sign error gives 2) |
| PAM3 H-bond lobe | < -0.01 | < -0.01 below 2.3 Å, else < -0.005 | baseline H26...O16 is 2.50 Å (at the cutoff), correctly -0.0078 |
| HI polarity | ESP max at H | dropped: CH3I sigma-hole (> +0.01 on the C-I axis) and belt (min at I, < -0.01) | iodine's sigma-hole makes the HI maximum sit on I (+0.040); my test was wrong chemistry |
| Multiwfn comparison | +-20 % | day session after the build (download approved) | needs our NCI code to exist first |

Runtimes on the reference (CPU shared with a PAM3 frequency run): charges 2 min, def2 2 min, fukui 4 min,
nci 42 min (PAM3 cube dominates). Timeouts in reference.json: 900 / 900 / 1200 / 3600 s.

## Original draft table (2026-11-12)

Not locked, not in `reference.json` yet. Once approved: one script per row in `night/sanity/`, each
docstring the contract, each tested against a throwaway reference implementation and one deliberate
bug (as for weeks 1–2), then listed in `reference.json`.

| Item | Contract (what the night agent builds) | Test system | Pass if | Reference source |
|---|---|---|---|---|
| MK + CHelpG charges | `calc(..., charges="mk" or "chelpg")` (CLI `--charges mk` or `--charges chelpg`). MK: Merz–Kollman ESP-fitted charges (points on 1.4/1.6/1.8/2.0 × vdW shells, 4–6 pts/Å², total-charge constraint). CHelpG: same fit, points on a 0.3 Å cubic grid from the vdW surface out to 2.8 Å beyond it. `charges.txt` + method.txt line naming the scheme | water, formamide | Σq = total charge (1e-6); water q(O) −0.75..−0.95, q(H) = q(H') (1e-4); formamide q(O) < 0, q(N) < 0, q(carbonyl C) > 0; ESP fit RRMS < 0.15; charges reproduce the surface ESP better than Mulliken (RMS); CHelpG: same Σq, symmetry and sign checks, and water q(O) within 0.1 e of MK | literature MK for water at B3LYP/6-31G(d) ≈ −0.80/+0.40; fixed numbers from a throwaway reference run on our own code before locking |
| RDG / NCI | `calc(..., nci=True)`: cubes `rdg.cube` (s = \|∇ρ\| / (2(3π²)^⅓ ρ^{4/3})) and `sl2rho.cube` (sign(λ₂)ρ); render draws the s = 0.5 isosurface coloured by sign(λ₂)ρ in [−0.04, +0.04] (blue H-bond, green vdW, red steric) | water dimer (.xyz, linear H-bond), PAM3 fold geometry (locked baseline) | water dimer: an s = 0.5 lobe between H···O with sign(λ₂)ρ < −0.015; PAM3 fold: a blue lobe on the H26···O16 axis, none needed on ext; isolated water: no lobe with \|sign(λ₂)ρ\| > 0.01 off-atom | Multiwfn on a molden export once (day session) for the dimer's lobe min sign(λ₂)ρ, ±20 % |
| Fukui | `calc(..., fukui=True)`: f⁺ = ρ(N+1) − ρ(N), f⁻ = ρ(N) − ρ(N−1) at fixed geometry (UKS for N±1; needs the `uks` item), condensed per atom (Hirshfeld or Mulliken differences) in `fukui.txt` | formaldehyde, formamide | Σ condensed f = 1 (±0.02) for each; formaldehyde: f⁺ largest on C, f⁻ largest on O; formamide: f⁻ largest on O or N (not C) | textbook ordering; numbers from a throwaway reference run |
| def2 + ECP (mixed basis) | `.xyz` input with heavy elements (Z > 36): def2-SVP + def2 ECP on those atoms only, 6-31G(d) on the rest; method.txt and caption name both; MMFF path still refuses them (guard) | HI (.xyz), CH₃I (.xyz) | SCF converges; method.txt names def2-SVP + ECP for I and 6-31G(d) for the rest; HI dipole direction H⁺→I⁻; guard: `[I-]` SMILES still refused with a clear message | PySCF direct run on the same geometry with basis {I: def2-svp, default 6-31g*}, ecp {I: def2-svp}: energy within 1e-6 Eh |

## Decisions (answered 2026-11-13; see night/STATE.md Answers)

MK + CHelpG; own NCI code + one Multiwfn check; Fukui via internal UKS; def2 mixed basis.

### Original questions

1. MK only, or also CHelpG (grid-based; same fit code, different point selection)? Proposed: MK only.
2. NCI: own code (≈40 lines, as proposed in IMPROVEMENTS §5) checked against Multiwfn once, or Multiwfn only? Proposed: own code.
3. Fukui depends on UKS (night 3). Proposed: schedule it only after `uks` passes.
4. def2: def2-SVP everywhere for heavy-element inputs, or mixed (6-31G(d) light / def2-SVP + ECP heavy)? Proposed: def2-SVP everywhere for such inputs; mixed bases complicate the caption.
