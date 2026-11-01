# VERIFY — code-level checks on checker/edgecheck.c (ladder: CBMC, KLEE)

Source under test: `checker/edgecheck.c` sha256 fb103ce555ff9331…; KLEE snapshot
`edgecheck_snapshot.c` sha256 fb103ce555ff9331… (must match; the KLEE container mounts only this folder).

| run | harness | bound | checks | status |
|---|---|---|---|---|
| CBMC large | `cbmc_terrain.c` | map ≤ 3×3, K ≤ 3, M ≤ 2, nondet class per cell, nondet slip/sink with slip+sink ≤ 1 | bounds, pointer, signed overflow, NaN, div-by-zero, unwinding assertions; model fits allocation; every value in [0,1] | **stopped, no result**: still in floating-point SAT after 76 min CPU when the session ended (2026-10-31) |
| CBMC small | `cbmc_terrain_small.c` | map ≤ 2×2, K ≤ 2, M ≤ 1, same nondeterminism | same | **stopped, no result**: still in floating-point SAT after 48 min CPU when the session ended (`cbmc_small.log`) |
| KLEE 4×4 | `klee_terrain.c` | symbolic R, C ≤ 4, symbolic class per cell, concrete assumed params, K=4, M=2 | memory errors; CSR structure; each choice sums to 1 ± 1e-12; destinations in range; arc values in [0,1] | **incomplete**: 25 min time limit, 74 paths explored, 0 completed, **0 errors** (`klee-out-terrain-4x4-timeout/`) |
| KLEE 2×2 symbolic size | `klee_terrain_small.c` | R, C ≤ 2 symbolic, otherwise as above | same | **incomplete**: 40 min limit, 26 paths, 0 completed, **0 errors** (`klee-out-terrain-2x2-symsize-timeout/`) |
| KLEE 2×2 concrete size | `klee_terrain_2x2c.c` | R = C = 2, class per cell symbolic | same | **complete**: 16/16 paths, **0 errors**, 5 s (`klee-out-2x2-concrete/`). Caveat: KLEE concretises floating-point expressions, so the traversable class was fixed per path; the 16 paths are rock / not-rock per cell, not all 5⁴ class assignments |
| exhaustive + sanitizers | `exhaustive.c` | **every** class assignment of every map with R, C ≤ 3 (1,985,305 maps) × (K, M) ∈ {(2,1), (4,2), (8,3)}, assumed params | ASan + UBSan; same structural asserts; values in [0,1]; Pmin ≤ Pmax; every arc ≥ closed-loop Pmin | **pass**: all assertions held, no sanitizer report (`exhaustive.log`) |

Not covered: the explicit front end's file parser (front end A) — its
correctness evidence is KT1a (780/780 rows against PRISM), not symbolic execution.
