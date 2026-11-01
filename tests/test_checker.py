#!/usr/bin/env python3
"""make test -- runs without PRISM, Storm, torch or the dataset.

1. Terrain front end: every (map, K, blind) row group of kt1b_results.csv and
   kt1b_d9_results.csv is re-run through checker/edgecheck and compared with the
   stored `checker` column (regression, tolerance 1e-12) and the stored `prism`
   column (oracle, tolerance 1e-6, the pre-registered KT1b tolerance).
2. Explicit front end: tests/explicit_small.{tra,lab}, a 3-state MDP whose values
   are known by hand (Pmax F unsafe = 1/2, Pmin F unsafe = 0, Pmax F<=1 unsafe = 1/2).
"""
import csv, itertools, json, re, subprocess, sys
from pathlib import Path
H = Path(__file__).resolve().parent.parent
BIN = H / "checker" / "edgecheck"; PARAMS = H / "terrain_params.csv"
ARCS = ["".join(a) for a in itertools.product("LSR", repeat=3)]
REG, ORA = 1e-12, 1e-6
fails, n = 0, 0

def run(args):
    return subprocess.run([str(BIN)] + args, capture_output=True, text=True, check=True).stdout

for csvname in ("kt1b_results.csv", "kt1b_d9_results.csv"):
    rows = list(csv.DictReader(open(H / csvname)))
    groups = {}
    for r in rows: groups.setdefault((r["map"], r["K"], r["blind_is_fail"]), []).append(r)
    for (mp, K, blind), rs in sorted(groups.items()):
        args = ["terrain", str(H / f"{mp}.txt"), str(PARAMS), K, "3"] + ([] if blind == "True" else ["--noblind"])
        j = json.loads(run(args))
        for r in rs:
            got = j["arcs"][ARCS.index(r["arc"])] if r["quantity"] == "arc" else j[r["quantity"]]
            n += 1
            if abs(got - float(r["checker"])) > REG or abs(got - float(r["prism"])) > ORA:
                fails += 1; print(f"FAIL {csvname} {mp} K={K} blind={blind} {r['quantity']} {r['arc']}: got {got!r} stored {r['checker']} prism {r['prism']}")
    print(f"{csvname}: {len(groups)} checker runs, {sum(len(v) for v in groups.values())} values compared")

def explicit(spec, expect):
    global n, fails
    out = run(["explicit", str(H / "tests/explicit_small.tra"), str(H / "tests/explicit_small.lab"), spec])
    v = float(re.search(r"value=(\S+)", out).group(1)); n += 1
    if abs(v - expect) > REG: fails += 1; print(f"FAIL explicit {spec}: got {v} expected {expect}")
explicit("Pmax F unsafe", 0.5); explicit("Pmin F unsafe", 0.0); explicit("Pmax F<=1 unsafe", 0.5); explicit("Pmin G !unsafe", 0.5)
print(f"{n} values checked, {fails} failures")
sys.exit(1 if fails else 0)
