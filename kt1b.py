#!/usr/bin/env python3
"""exp1 / KT1b -- edgecheck (front end B, builds the MDP from the map itself)
vs PRISM on gen_rover.py's encoding of the same map and parameters.

  kt1b.py MAP [MAP ...]  -> appends rows to kt1b_results.csv
Compared per map, K in {4, 8} (M = 3): Pmin/Pmax F<=K fail, Pmin/Pmax F fail
(closed loop, M = 0 model) and the 27 per-arc values Pmin[F<=K fail | arc].
Run twice: blind counts as fail, and --noblind.
"""
import csv, json, re, subprocess, sys
from pathlib import Path

H = Path(__file__).resolve().parent
BIN = H / "checker" / "edgecheck"; PRISM = Path.home() / "ResearchTools/bin/prism"
PY = sys.executable; PARAMS = H / "terrain_params.csv"; TOL = 1e-6
WORK = H / "kt1b_models"; WORK.mkdir(exist_ok=True)

def prism(model, props, consts=None):
    pf = model.with_suffix(".props"); pf.write_text("\n".join(props) + "\n")
    cmd = [str(PRISM), str(model), str(pf), "-explicit"] + (["-const", consts] if consts else [])
    r = subprocess.run(cmd, capture_output=True, text=True)
    res, cs, cur = [], [], None
    for ln in r.stdout.splitlines():          # pair each Result with the constants line above it
        if ln.startswith("Model constants: "): cur = ln[len("Model constants: "):]
        elif ln.startswith("Result: "): res.append(ln.split()[1]); cs.append(cur)
    if not res: raise SystemExit(f"PRISM failed on {model}:\n{r.stdout[-1500:]}")
    return [float(x) for x in res], cs

rows = []
for mp in map(Path, sys.argv[1:]):
    for noblind in (False, True):
        tag = f"{mp.parent.name}__{mp.stem}" + ("_noblind" if noblind else "")   # folder-namespaced: gold and SAM 2 maps share scene ids
        nb = ["--noblind"] if noblind else []
        m0 = WORK / f"{tag}_M0.prism"; m3 = WORK / f"{tag}_M3.prism"
        subprocess.run([PY, str(H / "gen_rover.py"), str(mp), str(PARAMS), str(m0), "--M=0"] + nb, check=True)
        subprocess.run([PY, str(H / "gen_rover.py"), str(mp), str(PARAMS), str(m3), "--M=3"] + nb, check=True)
        for K in (4, 8):
            out = subprocess.run([str(BIN), "terrain", str(mp), str(PARAMS), str(K), "3"] + nb,
                                 capture_output=True, text=True, check=True).stdout
            j = json.loads(out)
            pv, _ = prism(m0, [f'Pmin=? [ F<={K} "fail" ]', f'Pmax=? [ F<={K} "fail" ]',
                               'Pmin=? [ F "fail" ]', 'Pmax=? [ F "fail" ]'])
            for name, cv, p in zip(("pmin_k", "pmax_k", "pmin_inf", "pmax_inf"),
                                   (j["pmin_k"], j["pmax_k"], j["pmin_inf"], j["pmax_inf"]), pv):
                rows.append(dict(map=f"{mp.parent.name}/{mp.stem}", blind_is_fail=not noblind, K=K, quantity=name, arc="",
                                 prism=p, checker=cv, abs_diff=abs(p - cv)))
            av, cs = prism(m3, [f'Pmin=? [ F<={K} "fail" ]'], "A1=0:2,A2=0:2,A3=0:2")
            for p, c in zip(av, cs):
                a = dict(kv.split("=") for kv in c.split(","))
                idx = int(a["A1"]) * 9 + int(a["A2"]) * 3 + int(a["A3"])
                arc = "".join("LSR"[int(a[f"A{i}"])] for i in (1, 2, 3))
                cv = j["arcs"][idx]
                rows.append(dict(map=f"{mp.parent.name}/{mp.stem}", blind_is_fail=not noblind, K=K, quantity="arc", arc=arc,
                                 prism=p, checker=cv, abs_diff=abs(p - cv)))
        print(f"{mp.stem} done", file=sys.stderr, flush=True)

out = H / "kt1b_results.csv"; new = not out.exists()
with open(out, "a", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    if new: w.writeheader()
    w.writerows(rows)
bad = [r for r in rows if r["abs_diff"] > TOL]
print(f"rows={len(rows)} disagree={len(bad)} worst={max(r['abs_diff'] for r in rows):.3e}")
for r in bad[:10]: print("DISAGREE", r)
