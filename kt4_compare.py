#!/usr/bin/env python3
"""KT4 cross-arm comparison + post-hoc breakdown (labelled post-hoc in results.md).
veto_rescue@th  = planner arc P > th AND the best arc P <= th (the checker re-routes)
veto_stop@th    = planner arc P > th AND no arc P <= th (the checker says stop / re-image)
"""
import csv
from pathlib import Path
H = Path(__file__).resolve().parent
A = {r["scene"]: r for r in csv.DictReader(open(H / "kt4_gold.csv"))}
B = {r["scene"]: r for r in csv.DictReader(open(H / "kt4_sam2.csv"))}
out = []
for th in (0.01, 0.05, 0.10):
    for arm, D in (("gold", A), ("sam2", B)):
        resc = sum(float(r["p_planner"]) > th and float(r["p_best"]) <= th for r in D.values())
        stop = sum(float(r["p_planner"]) > th and float(r["p_best"]) > th for r in D.values())
        out.append(dict(theta=th, arm=arm, veto=resc + stop, veto_rescue=resc, veto_stop=stop))
    dis = sum(A[s][f"veto@{th}"] != B[s][f"veto@{th}"] for s in A)
    out.append(dict(theta=th, arm="gold_vs_sam2_veto_disagree", veto=dis, veto_rescue="", veto_stop=""))
same_plan = sum(A[s]["planner_arc"] == B[s]["planner_arc"] for s in A)
same_best = sum(A[s]["best_arc"] == B[s]["best_arc"] for s in A)
out.append(dict(theta="", arm="planner_arc_same_across_arms", veto=same_plan, veto_rescue="", veto_stop=""))
out.append(dict(theta="", arm="best_arc_same_across_arms", veto=same_best, veto_rescue="", veto_stop=""))
with open(H / "kt4_compare.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
for r in out: print(r)
