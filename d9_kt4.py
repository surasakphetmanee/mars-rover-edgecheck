#!/usr/bin/env python3
"""D9 -- KT4 (planner vs checker) over the injected maps and the real rock scene (D9_rock.md).
Writes kt4_d9.csv (one row per map, KT4 columns + n, seed, rock_adjacent_planner) and
d9_summary.csv (H6a, H6b, rescue/stop by n and arm). Planner, checker, K, M, theta as KT4."""
import csv, json, subprocess
from pathlib import Path
from planner import ARCS, read_map, plan, arc_cells
H = Path(__file__).resolve().parent
BIN = H / "checker" / "edgecheck"; PARAMS = H / "terrain_params.csv"; K, M = 8, 3
THS = (0.01, 0.05, 0.10)

def check(mp):
    return json.loads(subprocess.run([str(BIN), "terrain", str(mp), str(PARAMS), str(K), str(M)],
                                     capture_output=True, text=True, check=True).stdout)

def slip_adjacent(a, g, C):
    """planner's nominal arc has a rock as the outward slip neighbour in bands 0..2"""
    for (r, col), s in zip(arc_cells(a, C), a):
        if not (0 <= col < C): return False
        nb = [col - 1, col + 1] if s == "S" else [col + (1 if s == "R" else -1)]
        if any(0 <= x < C and g[r][x] == "r" for x in nb): return True
    return False

rows = []
def one(arm, mp, n, s):
    R, C, g = read_map(mp); j = check(mp); P = j["arcs"]; pa, pcost = plan(R, C, g)
    amin = min(range(len(P)), key=lambda i: (P[i], i))
    row = dict(arm=arm, map=f"{mp.parent.name}/{mp.stem}", n=n, seed=s,
               planner_arc=ARCS[pa] if pa is not None else "", planner_cost=pcost,
               p_planner=P[pa] if pa is not None else "", best_arc=ARCS[amin], p_best=P[amin],
               rerank=(pa is not None and P[pa] - P[amin] > 1e-12),
               p_saved=(P[pa] - P[amin]) if pa is not None else "",
               pmin_closed_loop=j["pmin_k"], pmax_worst=j["pmax_k"],
               n_rock=sum(r.count("r") for r in g),
               rock_adjacent_planner=(pa is not None and slip_adjacent(ARCS[pa], g, C)))
    for th in THS:
        row[f"veto@{th}"] = pa is None or P[pa] > th
        row[f"rescue@{th}"] = pa is not None and P[pa] > th and P[amin] <= th
    rows.append(row)

for arm in ("gold", "sam2"):
    for mp in sorted((H / f"maps_d9_{arm}").glob("*.txt")):
        tag = mp.stem.split("__")[1]; n = int(tag[1:tag.index("_")]); s = int(tag.split("_s")[1])
        one(arm, mp, n, s)
for arm in ("gold", "sam2"):
    for mp in sorted((H / f"maps_d9_real_{arm}").glob("*.txt")) if (H / f"maps_d9_real_{arm}").exists() else []:
        one(f"real_{arm}", mp, "", "")
with open(H / "kt4_d9.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

inj = [r for r in rows if r["n"] != ""]
summ = []
for n in (1, 2, 4, 8):
    for arm in ("gold", "sam2"):
        S = [r for r in inj if r["n"] == n and r["arm"] == arm]
        rr = [r for r in S if r["rerank"]]
        d = dict(n=n, arm=arm, maps=len(S), rerank=len(rr),
                 p_saved_median=sorted(r["p_saved"] for r in rr)[len(rr) // 2] if rr else "",
                 p_saved_max=max((r["p_saved"] for r in rr), default=0.0),
                 rock_adjacent_among_rerank=sum(r["rock_adjacent_planner"] for r in rr))
        for th in THS:
            d[f"veto@{th}"] = sum(r[f"veto@{th}"] for r in S); d[f"rescue@{th}"] = sum(r[f"rescue@{th}"] for r in S)
            d[f"stop@{th}"] = d[f"veto@{th}"] - d[f"rescue@{th}"]
        summ.append(d)
resc05 = sum(r["rescue@0.05"] for r in inj)
h6a = resc05 > 0
h6b = all(max((r["p_saved"] for r in inj if r["n"] == n and r["rerank"]), default=0.0) > 0.0168 for n in (1, 2, 4, 8))
summ.append(dict(n="H6a", arm=f"rescue@0.05={resc05}/{len(inj)}", maps="supported" if h6a else "refuted"))
summ.append(dict(n="H6b", arm="max p_saved > 0.0168 at every n", maps="supported" if h6b else "refuted"))
with open(H / "d9_summary.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(summ[0].keys())); w.writeheader(); w.writerows(summ)
for d in summ: print(d)
for r in rows:
    if r["arm"].startswith("real"): print(r)
