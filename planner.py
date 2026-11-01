"""AutoNav-style weighted-sum arc planner (plan.md) -- the thing the checker checks.
cost = sum of class costs of the arc's nominal cells + 0.5 per turn;
bedrock 1, soil 1.5, sand 4, unknown 4, rock or off-image = infinity;
ties -> lowest arc index (lexicographic L < S < R)."""
import itertools, math
from pathlib import Path
COST = {"b": 1.0, "o": 1.5, "s": 4.0, "u": 4.0, "r": math.inf}
ARCS = ["".join(a) for a in itertools.product("LSR", repeat=3)]
STEP = {"L": -1, "S": 0, "R": 1}

def read_map(p):
    t = Path(p).read_text().split(); R, C = int(t[0]), int(t[1])
    rows = t[2:2 + R]; return R, C, [rows[R - 1 - r] for r in range(R)]   # g[r], r=0 nearest

def arc_cells(a, C):
    col, out = C // 2, []
    for r, s in enumerate(a):
        col += STEP[s]; out.append((r, col))
    return out

def plan(R, C, g):
    best, best_a = math.inf, None
    for i, a in enumerate(ARCS):
        cost = 0.0
        for (r, col), s in zip(arc_cells(a, C), a):
            if not (0 <= col < C): cost = math.inf; break
            cost += COST[g[r][col]] + (0.5 if s != "S" else 0.0)
        if cost < best: best, best_a = cost, i
    return best_a, best
