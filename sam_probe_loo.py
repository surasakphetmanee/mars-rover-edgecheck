#!/usr/bin/env python3
"""sam_probe_loo.py -- D9 Part B: leave-one-out SAM 2 probe for the one real rock scene.
Same recipe as sam_probe.py (StandardScaler + LogisticRegression C=1, balanced, 2000 it),
trained on sam_dense/train minus this scene's npz; the scene is embedded here
(SAM 2.1 Hiera-S encoder, as sam_dense.py eval) and classified per 16x16 patch.
Writes sam_labels_d9/<scene>.png, maps_d9_real_sam2/<scene>.txt, sam_probe_loo.json.
Runs in the sam2 environment (see README)."""
import os, json, subprocess, sys, time
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
import numpy as np, torch
from pathlib import Path
from PIL import Image
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor

H = Path(__file__).resolve().parent
D = H / "data/ai4mars_test/ai4mars-dataset-merged-0.6/msl/ncam"
CKPT = Path(os.environ["SAM2_CKPT"])   # sam2.1_hiera_small.pt
SC = "NLB_556756308EDR_F0651642NCAM00285M1"
X, y, left_out = [], [], 0
for f in sorted((H / "sam_dense/train").glob("*.npz")):
    if f.stem == SC: left_out = len(np.load(f)["y"]); continue
    z = np.load(f); X.append(z["X"].astype(np.float32)); y.append(z["y"])
X = np.concatenate(X); y = np.concatenate(y)
clf = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, class_weight="balanced", max_iter=2000)).fit(X, y)
dev = "mps" if torch.backends.mps.is_available() else "cpu"
pred = SAM2ImagePredictor(build_sam2("configs/sam2.1/sam2.1_hiera_s.yaml", str(CKPT), device=dev))
img = np.array(Image.open(D / "images/edr" / f"{SC}.JPG").convert("RGB"))
t0 = time.perf_counter()
with torch.inference_mode():
    pred.set_image(img); emb = pred._features["image_embed"][0].float().cpu().numpy()
t_enc = time.perf_counter() - t0
p = clf.predict(emb.reshape(256, -1).T).reshape(64, 64).astype(np.uint8)
OUT = H / "sam_labels_d9"; OUT.mkdir(exist_ok=True)
Image.fromarray(np.kron(p, np.ones((16, 16), np.uint8))).save(OUT / f"{SC}.png")
gold = np.array(Image.open(D / "labels/test/masked-gold-min3-100agree" / f"{SC}_merged.png"))
g = gold.reshape(64, 16, 64, 16).transpose(0, 2, 1, 3).reshape(64, 64, 256)
yt, yp = [], []
for a in range(64):
    for b in range(64):
        lb = g[a, b][g[a, b] != 255]
        if len(lb) >= 128: yt.append(np.bincount(lb, minlength=4).argmax()); yp.append(p[a, b])
yt, yp = np.array(yt), np.array(yp)
res = dict(scene=SC, train_patches=int(len(y)), left_out_patches=int(left_out), eval_patches=int(len(yt)),
           patch_accuracy=float((yt == yp).mean()),
           recall_per_class={n: (float((yp[yt == i] == i).mean()) if (yt == i).any() else None) for i, n in enumerate(["soil", "bedrock", "sand", "big_rock"])},
           pred_counts=np.bincount(yp, minlength=4).tolist(), gold_counts=np.bincount(yt, minlength=4).tolist(),
           rock_pred_counts=np.bincount(yp[yt == 3], minlength=4).tolist(), t_enc_s=t_enc, device=dev)
(H / "sam_probe_loo.json").write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))
MD = H / "maps_d9_real_sam2"; MD.mkdir(exist_ok=True)
subprocess.run([sys.executable, str(H / "scene_map.py"), SC, str(OUT / f"{SC}.png"), str(MD / f"{SC}.txt")], check=True)
print((MD / f"{SC}.txt").read_text())
