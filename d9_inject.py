#!/usr/bin/env python3
"""D9 Part C -- inject rock cells into the 20 evaluation maps (D9_rock.md, pre-registered).
For n in {1,2,4,8}, seed s in 0..4: replace n non-rock cells drawn uniformly without
replacement from the reachable cone (band b in 0..7, |col-5| <= b+1) by 'r'.
RNG = random.Random(sha256("D9|scene|arm|n|s")). Writes maps_d9_<arm>/<scene>__n{n}_s{s}.txt
and maps_d9_real_gold/<rock scene>.txt (Part B gold arm)."""
import hashlib, random, subprocess, sys
from pathlib import Path
from planner import read_map
H = Path(__file__).resolve().parent
scenes = [l for l in (H / "eval_scenes.txt").read_text().splitlines() if l and not l.startswith("#")]
ROCK = "NLB_556756308EDR_F0651642NCAM00285M1"

def write_map(path, R, C, g):     # g[r] r=0 nearest; file far row first
    path.write_text(f"{R} {C}\n" + "\n".join(g[R - 1 - r] for r in range(R)) + "\n")

count = 0
for arm in ("gold", "sam2"):
    out = H / f"maps_d9_{arm}"; out.mkdir(exist_ok=True)
    for sc in scenes:
        R, C, g = read_map(H / f"maps_{arm}" / f"{sc}.txt")
        cand = [(b, c) for b in range(8) for c in range(C) if abs(c - C // 2) <= b + 1 and g[b][c] != "r"]
        for n in (1, 2, 4, 8):
            for s in range(5):
                rng = random.Random(int(hashlib.sha256(f"D9|{sc}|{arm}|{n}|{s}".encode()).hexdigest(), 16))
                cells = rng.sample(cand, n)
                h = [list(r) for r in g]
                for b, c in cells: h[b][c] = "r"
                write_map(out / f"{sc}__n{n}_s{s}.txt", R, C, ["".join(r) for r in h]); count += 1
print("injected maps:", count)
rd = H / "maps_d9_real_gold"; rd.mkdir(exist_ok=True)
subprocess.run([sys.executable, str(H / "scene_map.py"), ROCK, "gold", str(rd / f"{ROCK}.txt")], check=True)
print("real rock scene map:", rd / f"{ROCK}.txt")
