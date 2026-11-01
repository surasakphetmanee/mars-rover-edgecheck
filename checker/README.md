# edgecheck — on-device bounded probabilistic model checker

Plain C99, libc only, IEEE double. All memory allocated at load; the checking
loops allocate nothing. One file: `edgecheck.c`.

```bash
cc -std=c99 -O2 -Wall -Wextra -o edgecheck edgecheck.c -lm
```

## Front end A — explicit models (PRISM / PRISM-games export)

```bash
prism model.prism -explicit -exportmodel model.all          # writes model.tra/.lab/...
./edgecheck explicit model.tra model.lab "Pmax F<=20 unsafe"
./edgecheck explicit game.tra game.lab "<<defender>>Pmin F unsafe" --players defender,attacker
```

Spec: `[<<player>>]Pmax|Pmin F|G [<=k] [!]label` (`F label`, `G !label`).
MDPs and turn-based two-player SMGs. Rewards are not supported.

## Front end B — rover terrain map (the on-board path)

```bash
./edgecheck terrain MAP.txt terrain_params.csv K M [--reps N] [--noblind]
```

`MAP.txt`: `R C`, then R rows of C class codes, far row first
(`b` bedrock, `o` soil, `s` sand, `u` unknown, `r` rock). The checker builds
the terrain MDP from the map on every call (no PRISM, no export) and prints
JSON: closed-loop `Pmin/Pmax F<=K fail`, unbounded values, and
`P(F<=K fail | arc)` for all 3^M arcs (first M steering choices fixed,
remaining K−M chosen to minimise failure). Model: `../plan.md` Def. 1′.

## Validation

- KT1a: 300 M006 ledger rows + 480 bounded rows vs PRISM / PRISM-games,
  worst |Δ| 1.11e-16 (`../kt1a_results.csv`).
- KT1b: terrain front end vs PRISM on `../gen_rover.py`'s independent
  encoding of the same map (`../kt1b_results.csv`).
