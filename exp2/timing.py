#!/usr/bin/env python3
"""exp2 / KT2, KT3 (run 2: wall AND thread CPU time; run 1 kept as timing_run1_invalid.csv --
wall-clock under background QoS measured scheduler starvation, not compute, and
other jobs were running) -- latency of the on-board check (build the terrain MDP from
the map + evaluate all 27 arcs), 30 reps per cell, on
  (a) 'pcore'    : the binary as launched (macOS normally schedules it on a P-core)
  (b) 'standin'  : the same binary under `taskpolicy -c background` (background
                   QoS -> efficiency cores, reduced clock; single-threaded).
Maps: synthetic, R = C in {16, 32, 64, 128}, classes drawn with seed 20261030
(b .4, o .3, s .2, r .1); plus the scene-sized grid R=10, C=11. K in {8,16,32,64}, M = 3.
"""
import csv, json, random, subprocess
from pathlib import Path
H = Path(__file__).resolve().parent; E = H.parent
BIN = E / "checker" / "edgecheck"; PARAMS = E / "terrain_params.csv"
MD = H / "maps"; MD.mkdir(exist_ok=True)
def make(R, C):
    rnd = random.Random(20261030 + R * 1000 + C)
    rows = ["".join(rnd.choices("bosr", [.4, .3, .2, .1])[0] for _ in range(C)) for _ in range(R)]
    p = MD / f"synth_{R}x{C}.txt"; p.write_text(f"{R} {C}\n" + "\n".join(rows) + "\n"); return p
cells = [(10, 11)] + [(n, n) for n in (16, 32, 64, 128)]
rows = []
for R, C in cells:
    mp = make(R, C)
    for K in (8, 16, 32, 64):
        for where, pre in (("pcore", []), ("standin", ["taskpolicy", "-c", "background"])):
            j = json.loads(subprocess.run(pre + [str(BIN), "terrain", str(mp), str(PARAMS), str(K), "3", "--reps", "30"],
                                          capture_output=True, text=True, check=True).stdout)
            rows.append(dict(map=mp.stem, R=R, C=C, K=K, where=where, states=j["states"], transitions=j["transitions"],
                             lat_us_median=j["lat_us_median"], lat_us_q1=j["lat_us_q1"], lat_us_q3=j["lat_us_q3"],
                             cpu_us_median=j["cpu_us_median"], cpu_us_q1=j["cpu_us_q1"], cpu_us_q3=j["cpu_us_q3"],
                             build_us_min=j["build_us_min"], reps=j["reps"]))
            print(rows[-1], flush=True)
with open(H / "timing.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
