#!/usr/bin/env python3
"""sam_dense.py -- SAM 2.1 Hiera-S encoder embeddings per 16x16 patch.

  sam_dense.py train|eval  (scene lists from all_test_scenes.txt / eval_scenes.txt)
train: for every non-evaluation scene, patches whose valid pixels are >= 50 %
       gold-labelled, label = majority class, <= 400 per scene (seed 20261030)
       -> sam_dense/train/<scene>.npz (X float16 [n,256], y [n])
eval : full 64x64x256 embedding (float16) per evaluation scene
       -> sam_dense/eval/<scene>.npz
"""
import os, sys, time
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
import numpy as np, torch
from pathlib import Path
from PIL import Image
from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor

H = Path(__file__).resolve().parent
D = H / "data/ai4mars_test/ai4mars-dataset-merged-0.6/msl/ncam"
CKPT = Path(os.environ.get("SAM2_CKPT", H / "checkpoints/sam2.1_hiera_small.pt"))
dev = "mps" if torch.backends.mps.is_available() else "cpu"
pred = SAM2ImagePredictor(build_sam2("configs/sam2.1/sam2.1_hiera_s.yaml", str(CKPT), device=dev))
mode = sys.argv[1]
ev = [l for l in (H / "eval_scenes.txt").read_text().splitlines() if l and not l.startswith("#")]
alls = (H / "all_test_scenes.txt").read_text().split()
scenes = ev if mode == "eval" else [s for s in alls if s not in set(ev)]
OUT = H / "sam_dense" / mode; OUT.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(20261030)

def embed(scene):
    img = np.array(Image.open(D / "images/edr" / f"{scene}.JPG").convert("RGB"))
    with torch.inference_mode():
        pred.set_image(img)
        return pred._features["image_embed"][0].float().cpu().numpy()        # 256x64x64

times = []
for i, sc in enumerate(scenes):
    out = OUT / f"{sc}.npz"
    if out.exists(): continue
    if not (D / "images/edr" / f"{sc}.JPG").exists(): print("missing", sc); continue
    t0 = time.perf_counter(); emb = embed(sc); times.append(time.perf_counter() - t0)
    if mode == "eval":
        np.savez_compressed(out, emb=emb.astype(np.float16), t_enc=times[-1], device=dev)
    else:
        gold = np.array(Image.open(D / "labels/test/masked-gold-min3-100agree" / f"{sc}_merged.png"))
        rngm = np.array(Image.open(D / "images/rng-30m" / f"{sc.replace('EDR','RNG')}.png"))
        mxy = np.array(Image.open(D / "images/mxy" / f"{sc.replace('EDR','MXY')}.png"))
        valid = (rngm == 0) & (mxy == 0)
        g = gold.reshape(64, 16, 64, 16).transpose(0, 2, 1, 3).reshape(64, 64, 256)
        v = valid.reshape(64, 16, 64, 16).transpose(0, 2, 1, 3).reshape(64, 64, 256)
        X, y = [], []
        for a in range(64):
            for b in range(64):
                vv = v[a, b]; gg = g[a, b][vv]
                if vv.sum() == 0: continue
                lab = gg[gg != 255]
                if len(lab) < 0.5 * vv.sum(): continue
                X.append(emb[:, a, b]); y.append(np.bincount(lab, minlength=4).argmax())
        X = np.array(X, dtype=np.float16).reshape(-1, 256); y = np.array(y, dtype=np.int8)
        if len(y) > 400:
            k = rng.choice(len(y), 400, replace=False); X, y = X[k], y[k]
        np.savez_compressed(out, X=X, y=y, t_enc=times[-1])
    if i % 20 == 0: print(f"{mode} {i+1}/{len(scenes)} {sc} enc={times[-1]:.2f}s", flush=True)
print(f"{mode} done: {len(times)} scenes, median encoder {np.median(times):.2f}s on {dev}", flush=True)
