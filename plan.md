# EXP1 PLAN — mars-rover-edge-checker (M4, hackathon window, 2026-10-30)

Scope (PI 2026-10-30): KT1 oracle agreement, KT2 latency on a throttled
single core, KT4 veto study on ≥ 20 AI4Mars scenes + demo. CBMC/KLEE kept.
Dafny lemma and H5 sensitivity are stretch. Segmenter: SAM 2 open weights
first (SAM 3.1 via Meta Model API when the key arrives; provenance per scene).

## S1 — oracle regeneration — DONE

`oracle_m006/` is a copy of `missions/M006-EDGECHECKER/{gen_edge.py,run.sh,
collect.py,props}` run from a clean shell: 80 models byte-identical to the
mission's, 380/380 properties `ok`, 0 value cells differ, gates (MDP duality,
SMG determinacy) worst residual 0. Split: 300 reachability/safety properties
(P1, P2, P4 mdp; P1, P2, P3, P5 smg) and 80 reward properties (P3 mdp, P4 smg).

## The checker (`checker/edgecheck.c`) — two front ends, one engine

**Engine.** Backward induction over an explicit model held in CSR arrays:
`x_0 = 1_target`; `x_{j+1}(s) = 1_target(s) ? 1 : opt_{c ∈ choices(s)} Σ_t P(s,c,t)·x_j(t)`,
`opt` = max or min per state (MDP: one optimiser; SMG: by the state's player
and the coalition in the property). Bounded `F≤k`: exactly k sweeps.
Unbounded `F`: sweep until `max|x_{j+1} − x_j| = 0` (exact on acyclic
models) or `< 1e-12` with a cap of 10^6 sweeps; the stopping reason is
printed with the value. `G` is the dual: `Pmin[G ¬φ] = 1 − Pmax[F φ]`,
`<<C>>Pmax[G ¬φ] = 1 − <<C>>Pmin[F φ]`. Plain C99, IEEE double, no
allocation after load, no library beyond libc.

**Front end A — explicit files (oracle family, KT1a).** Reads PRISM's
`-exportmodel` output (`.tra`, `.lab`; SMG rows `src:player choice dst p act`).
The model is therefore *PRISM's own state space*; KT1a tests the engine, not
a translation. Rewards are not supported: the 80 reward rows are reported
`unsupported` (stated in the seed; not hidden).

**Front end B — terrain map (rover family, KT1b/KT2/KT4).** Reads a class
map (rows × cols of class codes) and a per-class parameter CSV and builds the
terrain MDP itself, on the device, every call. This is the on-board path:
no PRISM, no export. Oracle: `gen_rover.py` writes the PRISM model of the
*same* map and parameters; KT1b compares the two. A disagreement is a
translation or engine bug, never a modelling difference.

## The terrain model (Def. 1′, revised from the seed — deviations declared)

AI4Mars labels live in **image space** (Navcam perspective); the dataset ships
no per-pixel 3-D coordinates (MXY = rover-body mask, RNG = >30 m mask). An
inverse-perspective ground grid would need camera pose per image, which we do
not have. **Decision:** an image-space range–bearing grid, the abstraction
AutoNav's arc evaluation also lives in:
- crop to pixels inside the 30 m range mask and outside the rover mask;
  split into `R` horizontal bands (rows; bottom = nearest) × `C` vertical
  sectors (cols); a cell's class = majority of its labelled pixels; cells
  with < 50 % labelled pixels are `unknown`.
- state = (row, col) plus absorbing `collided`, `stuck`, `through` (reached
  the far row: left the checked area safely).
- actions = steer ∈ {L, S, R}: target = (row+1, col−1 | col | col+1).
- outcome for target class t: w.p. `sink_t` → `stuck`; w.p. `slip_t` →
  lateral slip, the rover lands in the target row one column further
  *outward* (both outward neighbours equally when steering straight);
  otherwise the target. Landing on `rock` → `collided`. Leaving the image
  sideways → `collided` (blind: no terrain information; conservative).
- **Dropped from the seed:** tip-over and slope (no geometry in AI4Mars).
  Tiers are collision ≻ stuck. Recorded as a seed deviation; slope returns
  only with a DEM source.

**Command and horizon (Def. 2′, revised).** A command is an arc: m = 3
steering choices. The checker evaluates `P(F≤k fail)` with the first m
actions fixed and the remaining k − m actions chosen to **minimise** failure
(the controller re-plans), k = 8. The seed's worst-case continuation is
dropped: it charges the command for an adversarial driver that does not
exist. Fail = `collided ∨ stuck`; tier values reported separately.

## Parameters (`terrain_params.csv`, D8 provenance column)

| class | slip | sink | provenance |
|---|---|---|---|
| bedrock | 0.02 | 0.000 | assumed |
| soil | 0.05 | 0.002 | assumed |
| sand | 0.15 | 0.020 | assumed; ordering from Curiosity ops thresholds (sandy slopes limited to 12.5° vs bedrock 25°) and megaripple slip up to 77 % |
| unknown | 0.15 | 0.020 | assumed = sand (worst traversable) |
| rock | — | — | entering = collision |

No published per-class probability exists (novelty.md). Every results table
that uses these prints `assumed`.

## The planner being checked

AutoNav-style weighted-sum cost over the 27 arcs: cost = Σ over the arc's
cells of class cost (bedrock 1, soil 1.5, sand 4, unknown 4, rock ∞) +
0.5 per non-straight step. Top-ranked arc = the planner's command. Same
family as the weighted-sum A* of verified-legged-nav.

## Experiments

- **exp1 / KT1a** checker vs PRISM on the 300 reachability rows of M006
  (+ bounded variants `F≤{4,8,16}` on the 20 MDP models via PRISM). Report
  |Δ| per row; tolerance 1e-6.
- **exp1 / KT1b** checker (front end B) vs PRISM (gen_rover.py) on every
  test scene: `Pmin[F≤k fail]` and the 27 per-command values for k ∈ {4, 8},
  plus unbounded `Pmin/Pmax[F fail]`.
- **exp2 / KT2, KT3** latency of one command check and of all 27, 30 reps,
  median/IQR, on (a) the Mac P-core and (b) the stand-in: the same binary
  under `taskpolicy -c background` (macOS schedules background QoS threads on
  the efficiency cores at reduced clock; single-threaded). Scale sweep on
  synthetic maps R = C ∈ {16, 32, 64, 128}, k ∈ {8, 16, 32, 64} for H3.
- **exp3 / KT4** on ≥ 20 scenes: planner's top arc vs checker's verdict at
  threshold θ = 0.05 (pre-registered); veto = planner's arc has P > θ;
  re-rank = the arc with minimal P differs from the planner's; P saved =
  P(planner arc) − P(best arc). Done twice: **(i) AI4Mars gold labels** as
  the class map (perception-free baseline) and **(ii) SAM-derived class map**
  (SAM 2 masks + class assignment), so the segmenter's effect on the verdict
  is a measured difference, not an assumption.

## Perception arm (after plan review R2)

20 evaluation scenes drawn with seed 20261030 from the 322 gold test images
(`eval_scenes.txt`, written before any segmentation). Class map (ii) =
SAM 2.1 Hiera-S automatic masks → per-mask mean of SAM 2 encoder features →
logistic-regression probe trained on gold labels of the 302 non-evaluation
test images → majority class per grid cell. Probe accuracy on the 20 scenes
is reported. Muse Spark zero-shot labelling is added when the API key exists.

**Pilot change (2026-10-30, one image, before any checking).** SAM 2's
automatic mask generator (points_per_side = 16) returned 10 masks covering
0.6 % of the valid area on the first evaluation frame (gold labels cover
87 %): it segments *objects* (rocks), not terrain *stuff*. The perception arm
is therefore a **dense linear probe on the SAM 2.1 image encoder**: each
16 × 16-pixel patch (the encoder's 64 × 64 grid) gets its 256-d embedding;
probe = standardise + multinomial logistic regression (C = 1,
class_weight = balanced, max_iter = 2000), trained on patches of the 302
non-evaluation scenes whose valid pixels are ≥ 50 % gold-labelled (majority
class; ≤ 400 patches per scene, seed 20261030). The paper calls this "SAM 2
encoder features + linear probe", not "SAM segmentation". SAM 3.1 (concept
prompts "sand", "bedrock", "rock" via the Meta Model API) is the zero-shot
arm when the key arrives; it is the model that can segment *stuff* by name.

**Pilot change 2 (2026-10-30, gold class maps viewed, before any checking).**
The rover's arm and deck occlude the near field in many Navcam frames and the
gold labels never cover it, so the nearest bands came out `unknown` across
the board. The grid now stops at the first image row that is ≥ 50 % rover
mask. The rule reads only the rover mask, so it is identical for the gold
and the SAM arms.

## Invariants (GATE-2)

- I1 checker = PRISM within 1e-6 on every row where both return a value.
- I2 `P(F≤k fail)` non-decreasing in k (every scene, every command).
- I3 at k ≥ R (longest path), bounded = unbounded.
- I4 one class everywhere, no slip, no sink → P(fail) = P(leaving sideways
  under the fixed arc) and = 0 for the straight arc from a centre column.
- I5 slip = sink = 0 and no rocks → every command's P(fail) = 0 except arcs
  that leave the image; checker vetoes nothing else.
- I6 degenerate check: report `Pmax[F fail]` (worst driver); if ≈ 1 on every
  scene the map is broken.
- I7 M006 gates re-checked on the checker's side: MDP duality P1 + P2 = 1,
  SMG determinacy P1 = P2, P1 + P3 = 1.

## What runs where

All on the Mac. PRISM 4.10.1 / PRISM-games 3.2.4.
SAM 2 in the project venv (CPU/MPS). No Anthropic API, no Meta API until
the key arrives.
