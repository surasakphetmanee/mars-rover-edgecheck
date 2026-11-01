# D9 — rock-containing scenes (M6 panel ask, Miller). Pre-registration, 2026-11-01

Question: does arc choice ever matter when collisions are possible? KT4 found 0 rock
cells in 40 maps, so every veto was a *stop*, and the paper's finding "the scene, not
the arc, decides" is conditional on that sample.

## Part A — sampling frame (measured first, `d9_survey.py` → `d9_survey.csv`)

Big-rock content of all 322 gold test labels (masked-gold-min3-100agree) inside the
valid region of Def. 1′ (30 m mask, rover mask, rows above the rover body):

| quantity | scenes |
|---|---|
| any big-rock pixel | 5 / 322 |
| ≥ 1 rock cell at the Def. 1′ threshold (25 %) | 2 |
| ≥ 1 rock cell at 10 % | 2 |
| ≥ 1 rock cell at 5 % | 2 |
| ≥ 1 rock cell inside the reachable cone (25 %) | 1 (`NLB_556756308…`, 9 cone cells) |

The two options the panel offered are therefore (i) a 20-scene rock sample: **impossible**
from this sampling frame; (ii) a lower rock threshold: **empty** — 5 % selects the same two
scenes as 25 %. The absence of rock cells in KT4 is a property of the AI4Mars gold test
set at the three-annotator / 100 %-agreement consensus level (big rock is the rarest class
and small rocks are not labelled), not of our threshold. This is reported as a result.

## Part B — the one real rock scene (descriptive, n = 1)

`NLB_556756308EDR_F0651642NCAM00285M1`: rock cells in bands 4–5 across columns 0–5.
Same drive (F0651642) as evaluation scene `NLB_556756244…`; it is in the probe's
*training* split (400 patches, 50 of them big rock).
- gold arm: `scene_map.py … gold` → `maps_d9_real_gold/`; KT4 row; KT1b (PRISM) oracle.
- SAM 2 arm: a **leave-one-out probe** (same recipe, this scene's 400 training patches
  removed; `sam_probe_loo.py`) → `maps_d9_real_sam2/`; KT4 row; KT1b oracle. It still
  shares the drive with other training scenes, like 19 of 20 evaluation scenes.
No hypothesis; reported as a case.

## Part C — injected rock on the evaluation maps (pre-registered)

Base maps: the 20 evaluation scenes × {gold, SAM 2} = 40 maps (unchanged files).
Injection (`d9_inject.py`): for n ∈ {1, 2, 4, 8} and seed s ∈ {0,…,4}, replace n cells by
`r`, drawn uniformly without replacement from the candidates = non-rock cells (b, c) with
band b ∈ 0..7 and |c − 5| ≤ b + 1 (the cells an arc can reach by band b). RNG =
`random.Random(sha256("D9|scene|arm|n|s"))`. 800 maps → `maps_d9_gold/`, `maps_d9_sam2/`,
stems `<scene>__n{n}_s{s}`. Scenes, planner, checker (K = 8, M = 3), parameters
(`terrain_params.csv`) and θ ∈ {0.01, 0.05, 0.10} exactly as KT4.

Hypotheses (decided before any injected map was checked):
- **H6a** — at θ = 0.05 the *rescue* fraction (planner arc > θ and some arc ≤ θ) over the
  800 injected maps is strictly positive. (KT4: 0 of 19 vetoes at θ = 0.05 were rescues.)
- **H6b** — for every n, the maximum P saved by re-ranking exceeds the KT4 sink-only
  maximum 0.0168.
Pre-declared descriptive breakdown (no test): rescue / stop by n and arm; among re-ranked
maps, the share in which the planner's nominal arc has a rock cell as the outward slip
neighbour in bands 0–2 (the mechanism the weighted-sum cost cannot see).

Oracle: KT1b (PRISM, `-explicit`) on n = 4, s = 0, all 20 scenes × both arms = 40 maps →
`kt1b_d9_results.csv` (K ∈ {4, 8}, blind and --noblind, 4 + 27 values each). Storm --exact
on the same models if time permits (not a gate). Any |Δ| > 1e-6 → GATE-2 stop.

Scope statement for the paper: Part C is a synthetic perturbation of real maps; it tests
the model, not Mars.
