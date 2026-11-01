#!/usr/bin/env python3
"""D9 Storm cross-check, parallel (run on a 16-core Linux host, Storm 1.14.0, 16 workers).
Same comparison and columns as storm_check.py: reads kt1b_d9_results.csv beside this file,
models in ./models/ (folder-namespaced stems), writes storm_d9_results.csv + storm_d9_host.txt."""
import csv, itertools, platform, re, subprocess, sys
from fractions import Fraction
from multiprocessing import Pool
from pathlib import Path
H = Path(__file__).resolve().parent; TOL = 1e-6
ARCS = ["".join(a) for a in itertools.product("LSR", repeat=3)]
def storm(key):
    model, prop, consts = key
    cmd = ["storm", "--prism", model, "--prop", prop, "--exact"] + (["--constants", consts] if consts else [])
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    m = re.search(r"Result \(for initial states\): (\S+)", out)
    if not m: raise SystemExit(f"storm failed on {model} {prop} {consts}\n{out[-800:]}")
    return key, m.group(1)
def key_of(r):
    stem = r["map"].replace("/", "__") + ("" if r["blind_is_fail"] == "True" else "_noblind")
    K = int(r["K"]); q = r["quantity"]
    if q == "arc":
        a = ARCS.index(r["arc"]); return (str(H / "models" / f"{stem}_M3.prism"), f'Pmin=? [ F<={K} "fail" ]', f"A1={a//9},A2={a//3%3},A3={a%3}")
    prop = {"pmin_k": f'Pmin=? [ F<={K} "fail" ]', "pmax_k": f'Pmax=? [ F<={K} "fail" ]',
            "pmin_inf": 'Pmin=? [ F "fail" ]', "pmax_inf": 'Pmax=? [ F "fail" ]'}[q]
    return (str(H / "models" / f"{stem}_M0.prism"), prop, None)
if __name__ == "__main__":
    rows = list(csv.DictReader(open(H / "kt1b_d9_results.csv")))
    keys = sorted({key_of(r) for r in rows}, key=str)
    ver = subprocess.run(["storm", "--version"], capture_output=True, text=True).stdout.splitlines()[0]
    (H / "storm_d9_host.txt").write_text(f"{platform.node()} {platform.platform()} {ver} workers={int(sys.argv[1]) if len(sys.argv) > 1 else 16}\n")
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 16) as pool:
        cache = {}
        for i, (k, v) in enumerate(pool.imap_unordered(storm, keys, chunksize=8)):
            cache[k] = Fraction(v)
            if i % 500 == 0: print(f"{i}/{len(keys)}", file=sys.stderr, flush=True)
    out = []
    for r in rows:
        s = cache[key_of(r)]; chk = float(r["checker"]); pr = float(r["prism"])
        out.append(dict(r, storm_exact=str(s), storm_float=float(s), storm_vs_checker=abs(float(s) - chk), storm_vs_prism=abs(float(s) - pr)))
    with open(H / "storm_d9_results.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
    bad = [o for o in out if o["storm_vs_checker"] > TOL or o["storm_vs_prism"] > TOL]
    print(f"rows={len(out)} storm_calls={len(cache)} disagree={len(bad)} worst storm-checker={max(o['storm_vs_checker'] for o in out):.3e} worst storm-prism={max(o['storm_vs_prism'] for o in out):.3e}")
