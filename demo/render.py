#!/usr/bin/env python3
"""demo/render.py -- one Navcam frame -> class grid -> the 27 arcs coloured by
their verified P(F<=8 fail | arc), planner's arc vs the checker's best arc.

  render.py SCENE ARM   (ARM = gold | sam2) -> demo/<ARM>/<SCENE>.png
Every number drawn comes from `edgecheck terrain` run inside this script.
"""
import json, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, ListedColormap
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import scene_map as sm
from planner import ARCS, read_map, plan, arc_cells
import plotstyle as ps

E = Path(__file__).resolve().parents[1]
scene, arm = sys.argv[1], sys.argv[2]
mp = E / f"maps_{arm}" / f"{scene}.txt"
j = json.loads(subprocess.run([str(E / "checker/edgecheck"), "terrain", str(mp), str(E / "terrain_params.csv"), "8", "3"],
                              capture_output=True, text=True, check=True).stdout)
P = j["arcs"]; R, C, g = read_map(mp); pa, _ = plan(R, C, g)
amin = min(range(27), key=lambda i: (P[i], i))
img = np.array(Image.open(sm.D / "images/edr" / f"{scene}.JPG").convert("L"))
ye, xe = sm.grid_edges(sm.masks(scene))
fig, ax = plt.subplots(figsize=(7.2, 7.2))
ax.imshow(img, cmap="gray", vmin=0, vmax=255)
CLS = {"b": ps.OKABE_ITO["sky"], "o": ps.OKABE_ITO["orange"], "s": ps.OKABE_ITO["yellow"], "r": ps.OKABE_ITO["vermillion"], "u": "#7F7F7F"}
for r in range(R):
    top, bot = ye[R - 1 - r], ye[R - r]
    for c in range(C):
        ax.add_patch(plt.Rectangle((xe[c], top), xe[c + 1] - xe[c], bot - top, fc=CLS[g[r][c]], ec="white", lw=0.3, alpha=0.28))
def centre(r, c): return ((xe[c] + xe[c + 1]) / 2, (ye[R - 1 - r] + ye[R - r]) / 2)
x0, y0 = (xe[C // 2] + xe[C // 2 + 1]) / 2, ye[R] + 20
norm = Normalize(vmin=0, vmax=max(0.05, max(P))); cmap = ps.SEQ
for i, a in sorted(enumerate(ARCS), key=lambda t: -P[t[0]]):
    pts = [(x0, y0)] + [centre(r, c) for r, c in arc_cells(a, C) if 0 <= c < C]
    xs, ys = zip(*pts); ax.plot(xs, ys, color=cmap(norm(P[i])), lw=1.6, alpha=0.9)
for i, col, ls, lab in ((pa, ps.ROLE["baseline"], "--", f"planner arc {ARCS[pa]}: P={P[pa]:.4f}"),
                        (amin, ps.ROLE["ours"], "-", f"checker best {ARCS[amin]}: P={P[amin]:.4f}")):
    pts = [(x0, y0)] + [centre(r, c) for r, c in arc_cells(ARCS[i], C)]
    xs, ys = zip(*pts); ax.plot(xs, ys, color=col, lw=3.2, ls=ls, label=lab)
sm_ = plt.cm.ScalarMappable(norm=norm, cmap=cmap); cb = fig.colorbar(sm_, ax=ax, fraction=0.035, pad=0.01)
cb.set_label("verified P(F≤8 fail | arc)  [terrain params: assumed]")
ax.set_axis_off(); ax.legend(loc="upper left", fontsize=8, framealpha=0.85)
ax.text(0.01, 0.01, f"{scene}  map={arm}  27 arcs checked in {j['lat_us_median']:.0f} µs (Mac P-core)\n"
        f"classes: b=sky o=orange s=yellow u=grey r=vermillion", transform=ax.transAxes, fontsize=7, color="white",
        va="bottom", bbox=dict(fc="black", alpha=0.6, lw=0))
out = E / "demo" / arm; out.mkdir(parents=True, exist_ok=True)
fig.savefig(out / f"{scene}.png", dpi=130, bbox_inches="tight"); print(out / f"{scene}.png")
