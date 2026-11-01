#!/usr/bin/env python3
"""exp1 invariants I2-I6 (plan.md) on the class maps in the given directories.
I1 is KT1a/KT1b (checker = PRISM). Writes invariants.csv; exit 1 on any FAIL.
"""
import csv, json, subprocess, sys
from pathlib import Path
H = Path(__file__).resolve().parent; BIN = H / "checker" / "edgecheck"
P = H / "terrain_params.csv"; Z = H / "params_zero.csv"
def run(mp, prm, K, M=3):
    return json.loads(subprocess.run([str(BIN), "terrain", str(mp), str(prm), str(K), str(M)],
                                     capture_output=True, text=True, check=True).stdout)
rows = []
def rec(inv, mp, ok, detail): rows.append(dict(invariant=inv, map=Path(mp).stem, result="PASS" if ok else "FAIL", detail=detail))
maps = [m for d in sys.argv[1:] for m in sorted(Path(d).glob("*.txt"))]
for mp in maps:
    R = int(mp.read_text().split()[0])
    prev = None; ok = True; worst = 0.0
    for K in range(3, 13):
        a = run(mp, P, K)["arcs"]
        if prev:
            d = min(x - y for x, y in zip(a, prev)); worst = min(worst, d); ok &= d >= -1e-15
        prev = a
    rec("I2 monotone in k (k=3..12, 27 arcs)", mp, ok, f"min step {worst:.2e}")
    j = run(mp, P, R + 1)
    d = max(abs(j["pmin_k"] - j["pmin_inf"]), abs(j["pmax_k"] - j["pmax_inf"]))
    rec("I3 bounded(k=R+1) = unbounded", mp, d <= 1e-12, f"max diff {d:.2e}")
    z = run(mp, Z, 8)
    rec("I5 slip=sink=0 -> every arc 0", mp, max(z["arcs"]) == 0.0 and z["pmin_k"] == 0.0, f"max arc {max(z['arcs'])}")
    j8 = run(mp, P, 8)
    nb = json.loads(subprocess.run([str(BIN), "terrain", str(mp), str(P), "8", "3", "--noblind"],
                                   capture_output=True, text=True, check=True).stdout)
    rows.append(dict(invariant="I6 degenerate check (report)", map=mp.stem, result="INFO",
                     detail=f"Pmax_noblind={nb['pmax_k']:.4f} Pmax_blindfail={j8['pmax_k']:.4f} Pmin={j8['pmin_k']:.4f}"))
# I4: uniform bedrock map, zero params: arcs that stay in the image are 0, the straight arc is 0
u = H / "maps" / "uniform_b.txt"; u.write_text("10 11\n" + "\n".join(["b" * 11] * 10) + "\n")
z = run(u, Z, 8)
rec("I4 uniform + zero params -> all arcs 0 (none leave the 11-col image in 3 steps)", u, max(z["arcs"]) == 0.0, f"max arc {max(z['arcs'])}")
e = H / "maps" / "narrow_b.txt"; e.write_text("10 3\n" + "\n".join(["bbb"] * 10) + "\n")
z = run(e, Z, 8); arcs = ["".join(x) for x in __import__("itertools").product("LSR", repeat=3)]
expect = []
for a in arcs:
    c, out = 1, 0
    for s in a:
        c += {"L": -1, "S": 0, "R": 1}[s]
        if not 0 <= c < 3: out = 1; break
    expect.append(float(out))
rec("I4 narrow map: P(arc)=1 iff the arc leaves the image", e, z["arcs"] == expect, f"{sum(expect):.0f} leaving arcs")
deg = [r for r in rows if r["invariant"].startswith("I6")]
pm = [float(r["detail"].split()[0].split("=")[1]) for r in deg]
if pm: rows.append(dict(invariant="I6 summary (restated, PI 2026-10-31: blind excluded)", map="*",
                        result="FAIL" if min(pm) > 0.99 else "PASS",
                        detail=f"Pmax_noblind min {min(pm):.4f} max {max(pm):.4f} over {len(pm)} maps; blind=fail gives 1 by construction (GATE2_I6.md)"))
with open(H / "invariants.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
from collections import Counter
print(Counter((r["invariant"].split()[0], r["result"]) for r in rows))
bad = [r for r in rows if r["result"] == "FAIL"]
for r in bad: print("FAIL", r)
sys.exit(1 if bad else 0)
