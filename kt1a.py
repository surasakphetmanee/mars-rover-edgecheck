#!/usr/bin/env python3
"""exp1 / KT1a -- edgecheck (front end A) vs PRISM / PRISM-games on M006.

1. export every M006 model with PRISM's own -exportmodel (explicit engine);
2. for each of the 380 ledger rows, run edgecheck on the export
   (reward rows -> 'unsupported', recorded, not hidden);
3. bounded variants F<=k, k in {4,8,16}: PRISM computes them here, the
   checker computes them on the same export.
Writes kt1a_results.csv. Every number comes from a tool run in this script.
"""
import csv, json, re, subprocess, sys, time
from pathlib import Path

H = Path(__file__).resolve().parent
ORA = H / "oracle_m006"
EXP = H / "exports"; EXP.mkdir(exist_ok=True)
BIN = H / "checker" / "edgecheck"
import os
PRISM = Path(os.environ.get("PRISM", "prism"))              # PRISM 4.10.1 on PATH or $PRISM
PG = Path(os.environ.get("PRISM_GAMES", "prism-games"))    # PRISM-games 3.2.4
TOL = 1e-6
KS = (4, 8, 16)

def export(model_id):
    tra = EXP / f"{model_id}.tra"
    if not tra.exists():
        binp = PG if "_smg_" in model_id else PRISM
        r = subprocess.run([str(binp), str(ORA / "models" / f"{model_id}.prism"), "-explicit",
                            "-exportmodel", str(EXP / f"{model_id}.all")], capture_output=True, text=True)
        if r.returncode != 0: raise SystemExit(f"export failed {model_id}: {r.stdout[-500:]}")
    return tra, EXP / f"{model_id}.lab"

def to_spec(prop):
    m = re.fullmatch(r'\s*(<<\w+>>)?(Pmax|Pmin)=\?\s*\[\s*(F|G)\s*(<=\s*(\d+))?\s*(!?)"(\w+)"\s*\]\s*', prop)
    if not m: return None
    co, opt, op, _, k, neg, lab = m.groups()
    return f"{co or ''}{opt} {op}{'<=' + k if k else ''} {neg}{lab}"

def check(tra, lab, spec):
    t = time.perf_counter()
    r = subprocess.run([str(BIN), "explicit", str(tra), str(lab), spec, "--players", "defender,attacker"],
                       capture_output=True, text=True)
    if r.returncode != 0: return None, r.stderr.strip(), None
    kv = dict(x.split("=", 1) for x in r.stdout.split())
    return float(kv["value"]), kv["stop"], float(kv["check_us"])

def prism_bounded(model_id, props):
    binp = PG if "_smg_" in model_id else PRISM
    pf = EXP / f"{model_id}.bounded.props"; pf.write_text("\n".join(props) + "\n")
    r = subprocess.run([str(binp), str(ORA / "models" / f"{model_id}.prism"), str(pf), "-explicit"],
                       capture_output=True, text=True)
    vals = [float(x) for x in re.findall(r"^Result: ([0-9.eE+-]+)", r.stdout, re.M)]
    if len(vals) != len(props): raise SystemExit(f"PRISM bounded failed on {model_id}:\n{r.stdout[-800:]}")
    return vals

rows = []
ledger = json.load(open(ORA / "results.json"))["properties"]
models = sorted({p["model_id"] for p in ledger})
for i, mid in enumerate(models):
    tra, lab = export(mid)
    for p in [q for q in ledger if q["model_id"] == mid]:
        spec = to_spec(p["prism_property"])
        row = dict(row_id=p["property_id"], model_id=mid, property=p["prism_property"], kind="ledger",
                   prism_value=p["value"], checker_value="", abs_diff="", status="", checker_stop="", checker_us="")
        if spec is None:
            row["status"] = "unsupported"
        else:
            v, stop, us = check(tra, lab, spec)
            if v is None: row["status"] = "checker_error:" + stop
            else:
                d = abs(v - p["value"])
                row.update(checker_value=repr(v), abs_diff=f"{d:.3e}", checker_stop=stop, checker_us=us,
                           status="agree" if d <= TOL else "DISAGREE")
        rows.append(row)
    # bounded variants on the same export
    if "_smg_" in mid:
        props = [f'<<defender>>Pmin=? [ F<={k} "unsafe" ]' for k in KS] + [f'<<attacker>>Pmax=? [ F<={k} "unsafe" ]' for k in KS]
    else:
        props = [f'Pmax=? [ F<={k} "unsafe" ]' for k in KS] + [f'Pmin=? [ G<={k} !"unsafe" ]' for k in KS]
    pv = prism_bounded(mid, props)
    for prop, val in zip(props, pv):
        spec = to_spec(prop)
        v, stop, us = check(tra, lab, spec)
        d = abs(v - val)
        rows.append(dict(row_id=f"{mid}/{prop}", model_id=mid, property=prop, kind="bounded",
                         prism_value=val, checker_value=repr(v), abs_diff=f"{d:.3e}", status="agree" if d <= TOL else "DISAGREE",
                         checker_stop=stop, checker_us=us))
    print(f"[{i+1}/{len(models)}] {mid}", file=sys.stderr, flush=True)

with open(H / "kt1a_results.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
from collections import Counter
print(Counter((r["kind"], r["status"]) for r in rows))
worst = max((float(r["abs_diff"]) for r in rows if r["abs_diff"]), default=0)
print("worst |diff| =", worst)
