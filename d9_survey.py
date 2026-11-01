#!/usr/bin/env python3
"""D9 sampling frame: big-rock content of every gold test label inside the valid region
(scene_map.py rules). cellsXX = cells whose rock share >= XX %; coneXX = those inside the
reachable cone (band b, |col-5| <= b+1, b < 8). Output: d9_survey.csv. Run 2026-11-01 BEFORE D9_rock.md."""
import sys, csv, numpy as np
sys.path.insert(0, ".")
from PIL import Image
from scene_map import D, masks, grid_edges, R, C
scenes = [l.strip() for l in open("all_test_scenes.txt") if l.strip()]
out = []
for sc in scenes:
    try:
        lab = np.array(Image.open(D / "labels/test/masked-gold-min3-100agree" / f"{sc}_merged.png"))
        v = masks(sc)
    except FileNotFoundError:
        continue
    l = lab[v]; labelled = (l != 255)
    frac_lab = labelled.mean() if v.sum() else 0
    rock_px = (l == 3).sum()
    rock_frac = rock_px / max(labelled.sum(), 1)
    # per-cell rock fraction
    ye, xe = grid_edges(v, lab.shape[1])
    cells = {0.25: 0, 0.10: 0, 0.05: 0}; cone = {0.25: 0, 0.10: 0, 0.05: 0}
    if ye is not None:
        for b in range(R):
            top, bot = ye[R-1-b], ye[R-b]
            for c in range(C):
                vv = v[top:bot, xe[c]:xe[c+1]]; ll = lab[top:bot, xe[c]:xe[c+1]][vv]
                nv = int(vv.sum()); lb = ll[ll != 255]
                if nv == 0 or len(lb) < 0.5*nv: continue
                f = (lb == 3).mean()
                for th in cells:
                    if f >= th:
                        cells[th] += 1
                        if b < 8 and abs(c - C//2) <= b+1: cone[th] += 1
    out.append(dict(scene=sc, labelled=round(frac_lab,3), rock_px=int(rock_px), rock_frac=round(rock_frac,4),
                    cells25=cells[0.25], cells10=cells[0.10], cells05=cells[0.05],
                    cone25=cone[0.25], cone10=cone[0.10], cone05=cone[0.05]))
w = csv.DictWriter(sys.stdout, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
