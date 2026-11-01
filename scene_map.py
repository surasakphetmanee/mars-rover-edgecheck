#!/usr/bin/env python3
"""scene_map.py -- AI4Mars scene -> range-bearing class map (plan.md Def. 1').

  scene_map.py SCENE_ID SOURCE OUT.txt   SOURCE = gold | <path to a label png>

Rules (fixed 2026-10-30, before any checking):
  valid pixel = inside the 30 m range mask, outside the rover mask, and above
  the first image row that is >= 50 % rover (the near field under the arm);
  grid R = 10 range bands x C = 11 bearing sectors over the valid rows
  (band 0 = nearest = image bottom); per cell, over valid pixels:
    no valid pixels or < 50 % labelled          -> 'u' unknown
    big rock >= 25 % of labelled pixels          -> 'r' rock
    otherwise majority of soil / bedrock / sand  -> 'o' / 'b' / 's'
Label values (AI4Mars): 0 soil, 1 bedrock, 2 sand, 3 big rock, 255 null.
"""
import sys
import numpy as np
from pathlib import Path
from PIL import Image

R, C = 10, 11
D = Path(__file__).resolve().parent / "data/ai4mars_test/ai4mars-dataset-merged-0.6/msl/ncam"

def masks(scene):
    """valid pixels, restricted to the rows above the rover body: the grid
    stops at the first image row (from the top) where the rover mask covers
    >= 50 % of the row. Mask-only rule, identical for every arm (pilot
    2026-10-30: the arm/deck occludes the near field and is never labelled)."""
    rng = np.array(Image.open(D / "images/rng-30m" / f"{scene.replace('EDR', 'RNG')}.png"))
    mxy = np.array(Image.open(D / "images/mxy" / f"{scene.replace('EDR', 'MXY')}.png"))
    valid = (rng == 0) & (mxy == 0)
    rover_rows = np.where(mxy.mean(axis=1) >= 0.5)[0]
    if len(rover_rows): valid[rover_rows.min():] = False
    return valid

def grid_edges(valid, width=1024):
    rows = np.where(valid.any(axis=1))[0]
    if len(rows) == 0: return None, None
    y0, y1 = rows.min(), rows.max() + 1
    return np.linspace(y0, y1, R + 1).astype(int), np.linspace(0, width, C + 1).astype(int)

def class_map(label, valid):
    ye, xe = grid_edges(valid, label.shape[1])
    if ye is None: return ["u" * C] * R
    grid = []
    for b in range(R):                                   # b = 0 nearest -> image bottom band
        top, bot = ye[R - 1 - b], ye[R - b]
        row = ""
        for c in range(C):
            v = valid[top:bot, xe[c]:xe[c + 1]]; l = label[top:bot, xe[c]:xe[c + 1]][v]
            nv = int(v.sum()); lab = l[l != 255]
            if nv == 0 or len(lab) < 0.5 * nv: row += "u"; continue
            if (lab == 3).mean() >= 0.25: row += "r"; continue
            cnt = [(lab == k).sum() for k in (0, 1, 2)]
            row += "obs"[int(np.argmax(cnt))]
        grid.append(row)
    return grid

def main():
    scene, src, out = sys.argv[1:4]
    if src == "gold":
        label = np.array(Image.open(D / "labels/test/masked-gold-min3-100agree" / f"{scene}_merged.png"))
    else:
        label = np.array(Image.open(src))
    grid = class_map(label, masks(scene))
    Path(out).write_text(f"{R} {C}\n" + "\n".join(reversed(grid)) + "\n")   # file: far row first

if __name__ == "__main__":
    main()
