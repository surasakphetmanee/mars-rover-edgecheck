#!/usr/bin/env python3
"""D5 -- planner-continuation value per arc (D5_planner.md) beside the checker's optimistic V_K(a).
Writes d5_policies/<arm>__<scene>.txt (steer per cell), d5_arcs.csv, kt4_d5.csv, d5_summary.csv;
with --prism also d5_prism.csv (PRISM on gen_rover_policy.py DTMC, constants sweep, one call per map)."""
import csv, json, math, os, re, subprocess, sys
from pathlib import Path
from planner import ARCS, COST, STEP, read_map, plan
H = Path(__file__).resolve().parent
BIN = H / "checker" / "edgecheck"; PARAMS = H / "terrain_params.csv"; K, M = 8, 3
PRISM = Path(os.environ.get("PRISM", "prism"))
THS = (0.01, 0.05, 0.10)
params = {r["class"]: (float(r["slip"]), float(r["sink"])) for r in csv.DictReader(open(PARAMS))}
NAME = {"b": "bedrock", "o": "soil", "s": "sand", "u": "unknown"}

def policy_steer(R, C, g, r, c):
    """receding-horizon weighted sum from cell (r,c): first steer of the cheapest 3-cell arc"""
    best, best_a = math.inf, None
    for i, a in enumerate(ARCS):
        cost, col = 0.0, c
        for k, s in enumerate(a):
            col += STEP[s]; rr = r + 1 + k
            if not (0 <= col < C): cost = math.inf; break
            if rr < R: cost += COST[g[rr][col]]
            cost += 0.5 if s != "S" else 0.0
        if cost < best: best, best_a = cost, i
    return ARCS[best_a][0] if best_a is not None else "S"

def land(R, C, g, r, c):
    if r >= R: return "thru"
    if c < 0 or c >= C: return "fail"
    if g[r][c] == "r": return "fail"
    return (r, c)

def step_dist(R, C, g, r, c, d):
    """distribution over outcomes of steering d from (r,c): list of (prob, outcome)"""
    tr, tc = r + 1, c + d; base = land(R, C, g, tr, tc)
    if base in ("thru", "fail"): return [(1.0, base)]
    slip, sink = params[NAME[g[tr][tc]]]; ok = 1.0 - slip - sink; out = []
    if ok > 0: out.append((ok, base))
    if sink > 0: out.append((sink, "fail"))
    if slip > 0:
        if d != 0: out.append((slip, land(R, C, g, tr, tc + d)))
        else: out += [(slip / 2, land(R, C, g, tr, tc - 1)), (slip / 2, land(R, C, g, tr, tc + 1))]
    return out

def value_plan(R, C, g, pol, arc):
    """P(fail within K steps) with the arc's 3 steers then the policy; forward distribution over cells"""
    dist = {(-1, C // 2): 1.0}; pfail = 0.0
    for t in range(K):
        nxt = {}
        for (r, c), p in dist.items():
            d = STEP[arc[t]] if t < M else STEP[pol[r][c]]
            for q, o in step_dist(R, C, g, r, c, d):
                if o == "fail": pfail += p * q
                elif o == "thru": pass
                else: nxt[o] = nxt.get(o, 0.0) + p * q
        dist = nxt
    return pfail

arcs_rows, map_rows, prism_rows = [], [], []
PD = H / "d5_policies"; PD.mkdir(exist_ok=True); WD = H / "kt1b_models"
for arm in ("gold", "sam2"):
    for mp in sorted((H / f"maps_{arm}").glob("*.txt")):
        R, C, g = read_map(mp)
        pol = ["".join(policy_steer(R, C, g, r, c) if g[r][c] != "r" else "S" for c in range(C)) for r in range(R)]
        pf = PD / f"{arm}__{mp.stem}.txt"; pf.write_text("\n".join(pol[R - 1 - r] for r in range(R)) + "\n")
        j = json.loads(subprocess.run([str(BIN), "terrain", str(mp), str(PARAMS), str(K), str(M)], capture_output=True, text=True, check=True).stdout)
        vopt = j["arcs"]; vplan = [value_plan(R, C, g, pol, a) for a in ARCS]
        for a, o, p in zip(ARCS, vopt, vplan):
            arcs_rows.append(dict(arm=arm, scene=mp.stem, arc=a, v_opt=o, v_plan=p, gap=p - o))
        pa, pcost = plan(R, C, g)
        bo = min(range(27), key=lambda i: (vopt[i], i)); bp = min(range(27), key=lambda i: (vplan[i], i))
        row = dict(arm=arm, scene=mp.stem, planner_arc=ARCS[pa], v_opt_planner=vopt[pa], v_plan_planner=vplan[pa],
                   best_opt=ARCS[bo], v_opt_best=vopt[bo], best_plan=ARCS[bp], v_plan_best=vplan[bp],
                   rerank_opt=vopt[pa] - vopt[bo] > 1e-12, rerank_plan=vplan[pa] - vplan[bp] > 1e-12,
                   gap_max=max(p - o for o, p in zip(vopt, vplan)))
        for th in THS: row[f"veto_opt@{th}"] = vopt[pa] > th; row[f"veto_plan@{th}"] = vplan[pa] > th
        map_rows.append(row)
        if "--prism" in sys.argv:
            model = WD / f"d5_{arm}__{mp.stem}.prism"
            subprocess.run([sys.executable, str(H / "gen_rover_policy.py"), str(mp), str(PARAMS), str(pf), str(model)], check=True)
            props = model.with_suffix(".props"); props.write_text(f'P=? [ F<={K} "fail" ]\n')
            r = subprocess.run([str(PRISM), str(model), str(props), "-explicit", "-const", "A1=0:2,A2=0:2,A3=0:2"], capture_output=True, text=True)
            cur, got = None, {}
            for ln in r.stdout.splitlines():
                if ln.startswith("Model constants: "): cur = ln[len("Model constants: "):]
                elif ln.startswith("Result: "): got[cur] = float(ln.split()[1])
            if len(got) != 27: raise SystemExit(f"PRISM failed on {model}\n{r.stdout[-1500:]}")
            for cs, v in got.items():
                a = dict(kv.split("=") for kv in cs.split(",")); arc = "".join("LSR"[int(a[f"A{i}"])] for i in (1, 2, 3))
                prism_rows.append(dict(arm=arm, scene=mp.stem, arc=arc, prism=v, python=vplan[ARCS.index(arc)], abs_diff=abs(v - vplan[ARCS.index(arc)])))
            print(mp.stem, "prism ok", file=sys.stderr, flush=True)

def dump(name, rows):
    with open(H / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
dump("d5_arcs.csv", arcs_rows); dump("kt4_d5.csv", map_rows)
if prism_rows: dump("d5_prism.csv", prism_rows)
gaps = sorted(r["gap"] for r in arcs_rows)
summ = [dict(quantity="arcs", value=len(arcs_rows)), dict(quantity="gap_median", value=gaps[len(gaps) // 2]), dict(quantity="gap_max", value=gaps[-1]),
        dict(quantity="gap_min", value=gaps[0]),
        dict(quantity="maps_best_arc_changes", value=sum(r["best_opt"] != r["best_plan"] for r in map_rows)),
        dict(quantity="maps_rerank_opt", value=sum(r["rerank_opt"] for r in map_rows)), dict(quantity="maps_rerank_plan", value=sum(r["rerank_plan"] for r in map_rows))]
for th in THS:
    summ += [dict(quantity=f"veto_opt@{th}", value=sum(r[f"veto_opt@{th}"] for r in map_rows)),
             dict(quantity=f"veto_plan@{th}", value=sum(r[f"veto_plan@{th}"] for r in map_rows)),
             dict(quantity=f"veto_changes@{th}", value=sum(r[f"veto_opt@{th}"] != r[f"veto_plan@{th}"] for r in map_rows))]
if prism_rows:
    summ += [dict(quantity="prism_rows", value=len(prism_rows)), dict(quantity="prism_bad", value=sum(r["abs_diff"] > 1e-6 for r in prism_rows)),
             dict(quantity="prism_worst", value=max(r["abs_diff"] for r in prism_rows))]
dump("d5_summary.csv", summ)
for s in summ: print(s)
