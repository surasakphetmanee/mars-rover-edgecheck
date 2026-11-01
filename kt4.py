#!/usr/bin/env python3
"""exp3 / KT4 -- does the verified per-arc probability overrule the planner?

  kt4.py ARM MAPDIR   (ARM = gold | sam2 | ...; maps MAPDIR/<scene>.txt)
Planner (plan.md): AutoNav-style weighted sum over the 27 arcs (M = 3):
  cost = sum of class costs of the arc's nominal cells + 0.5 per turn;
  bedrock 1, soil 1.5, sand 4, unknown 4, rock or off-image = infinity;
  ties -> lowest arc index (L < S < R, lexicographic).
Checker: edgecheck terrain MAP terrain_params.csv K=8 M=3 -> P(F<=8 fail | arc).
Pre-registered: theta = 0.05 (also 0.01, 0.10). veto = P(planner arc) > theta;
re-rank = the min-P arc differs from the planner's (P differs by > 1e-12).
"""
import csv, json, math, subprocess, sys
from pathlib import Path

H = Path(__file__).resolve().parent
import os
BIN = H / "checker" / "edgecheck"; PARAMS = Path(os.environ.get("KT4_PARAMS", H / "terrain_params.csv"))
from planner import ARCS, read_map, plan
K, M = 8, 3

arm, mapdir = sys.argv[1], Path(sys.argv[2])
scenes = [l for l in (H / "eval_scenes.txt").read_text().splitlines() if l and not l.startswith("#")]
rows = []
for sc in scenes:
    mp = mapdir / f"{sc}.txt"
    R, C, g = read_map(mp)
    j = json.loads(subprocess.run([str(BIN), "terrain", str(mp), str(PARAMS), str(K), str(M)],
                                  capture_output=True, text=True, check=True).stdout)
    P = j["arcs"]; pa, pcost = plan(R, C, g)
    amin = min(range(len(P)), key=lambda i: (P[i], i))
    row = dict(arm=arm, scene=sc, planner_arc=ARCS[pa] if pa is not None else "", planner_cost=pcost,
               p_planner=P[pa] if pa is not None else "", best_arc=ARCS[amin], p_best=P[amin],
               rerank=(pa is not None and P[pa] - P[amin] > 1e-12),
               p_saved=(P[pa] - P[amin]) if pa is not None else "",
               pmin_closed_loop=j["pmin_k"], pmax_worst=j["pmax_k"],
               n_rock=sum(r.count("r") for r in g), n_sand=sum(r.count("s") for r in g),
               n_unknown=sum(r.count("u") for r in g))
    for th in (0.01, 0.05, 0.10):
        row[f"veto@{th}"] = pa is None or P[pa] > th
    rows.append(row)
out = H / f"kt4_{arm}{os.environ.get('KT4_TAG', '')}.csv"
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
n = len(rows)
print(f"{arm}: scenes={n} rerank={sum(r['rerank'] for r in rows)} "
      + " ".join(f"veto@{t}={sum(r[f'veto@{t}'] for r in rows)}" for t in (0.01, 0.05, 0.10)))
