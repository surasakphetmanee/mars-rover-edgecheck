# D5 — planner-continuation values (M6 panel ask, PV). Declared 2026-11-01 before running

The paper's per-arc value V_K(a) fixes the arc's three steers and lets steps 4..K be chosen
to *minimise* failure (optimistic continuation). The panel asked for the number an operator
would log: the same arc followed by the **planner itself** driving steps 4..K.

Policy (fixed here): at every cell (r, c) with r ≥ 3 the weighted-sum planner re-plans with
its own 3-cell horizon from that cell — cost over the next three nominal cells (class costs
bedrock 1, soil 1.5, sand/unknown 4, rock/off-image ∞, cells beyond the far row 0) plus 0.5
per turn, ties → lowest arc index — and takes the first steer of the winning arc; if every arc
is ∞ it steers straight. The planner sees no slip, as in KT4. The result is a DTMC per arc.

Computed by `d5_planner_cont.py` (Python backward induction, K = 8, blind = fail, same
`terrain_params.csv`) for the 27 arcs of the 40 KT4 maps → `d5_arcs.csv` (both values per arc)
and `kt4_d5.csv` (per map: the planner's arc under both values, best arc under both, veto at
θ ∈ {0.01, 0.05, 0.10} under both, re-rank under both). Oracle: PRISM on a DTMC encoding of
the same policy (`gen_rover_policy.py`, constants A1..A3 sweep, one call per map) →
`d5_prism.csv`; |Δ| > 1e-6 → stop.

Descriptive, no hypothesis. Pre-declared summary: median and max of V^plan − V^opt over
all 1,080 arcs; number of maps whose veto at θ = 0.05 changes between the two values;
number of maps whose best arc changes.
