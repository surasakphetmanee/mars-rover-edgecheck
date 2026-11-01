#!/usr/bin/env python3
"""D8 (M6 panel) -- Storm 1.14.0 as a second reference engine on every terrain model
already compared in KT1b. Storm runs with --exact (rational arithmetic); the
rational is compared with the checker's double and with PRISM's stored value at the
pre-registered tolerance 1e-6. Reads kt1b_results.csv and kt1b_models/ (folder-namespaced stems; the first run
read gold stems that the SAM 2 run had overwritten, see storm_check.log.run1); writes
storm_results.csv. Nothing is typed by hand."""
import csv, re, subprocess, sys
from fractions import Fraction
from pathlib import Path
H = Path(__file__).resolve().parent; TOL = 1e-6
rows = list(csv.DictReader(open(H / "kt1b_results.csv")))
ARCS = ["".join(a) for a in __import__("itertools").product("LSR", repeat=3)]
def storm(model, prop, consts=None):
    cmd = ["storm", "--prism", str(model), "--prop", prop, "--exact"] + (["--constants", consts] if consts else [])
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    m = re.search(r"Result \(for initial states\): (\S+)", out)
    if not m: raise SystemExit(f"storm failed on {model} {prop} {consts}\n{out[-800:]}")
    return Fraction(m.group(1))
out, cache = [], {}
for i, r in enumerate(rows):
    stem = r["map"].replace("/", "__") + ("" if r["blind_is_fail"] == "True" else "_noblind")   # matches kt1b.py namespacing
    K = int(r["K"]); q = r["quantity"]
    if q == "arc":
        model = H / "kt1b_models" / f"{stem}_M3.prism"; a = ARCS.index(r["arc"])
        consts = f"A1={a//9},A2={a//3%3},A3={a%3}"; prop = f'Pmin=? [ F<={K} "fail" ]'
    else:
        model = H / "kt1b_models" / f"{stem}_M0.prism"; consts = None
        prop = {"pmin_k": f'Pmin=? [ F<={K} "fail" ]', "pmax_k": f'Pmax=? [ F<={K} "fail" ]',
                "pmin_inf": 'Pmin=? [ F "fail" ]', "pmax_inf": 'Pmax=? [ F "fail" ]'}[q]
    key = (str(model), prop, consts)
    if key not in cache: cache[key] = storm(model, prop, consts)
    s = cache[key]; chk = float(r["checker"]); pr = float(r["prism"])
    out.append(dict(r, storm_exact=str(s), storm_float=float(s), storm_vs_checker=abs(float(s) - chk),
                    storm_vs_prism=abs(float(s) - pr)))
    if i % 500 == 0: print(f"{i}/{len(rows)}", file=sys.stderr, flush=True)
with open(H / "storm_results.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
bad = [o for o in out if o["storm_vs_checker"] > TOL or o["storm_vs_prism"] > TOL]
print(f"rows={len(out)} storm_calls={len(cache)} disagree={len(bad)} "
      f"worst storm-checker={max(o['storm_vs_checker'] for o in out):.3e} worst storm-prism={max(o['storm_vs_prism'] for o in out):.3e}")
