#!/usr/bin/env python3
"""sam_probe.py -- linear probe on SAM 2.1 encoder patch features (plan.md).
Train on sam_dense/train (302 non-evaluation scenes); predict every 16x16
patch of the 20 evaluation scenes; write sam_labels/<scene>.png (AI4Mars
codes 0 soil, 1 bedrock, 2 sand, 3 big rock; 255 outside valid) and report
patch accuracy against the gold majority on the evaluation scenes.
Probe (fixed): StandardScaler + LogisticRegression(C=1, class_weight=balanced, max_iter=2000).
"""
import csv, json, numpy as np
from pathlib import Path
from PIL import Image
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.metrics import confusion_matrix

H = Path(__file__).resolve().parent
D = H / "data/ai4mars_test/ai4mars-dataset-merged-0.6/msl/ncam"
X, y = [], []
for f in sorted((H / "sam_dense/train").glob("*.npz")):
    z = np.load(f); X.append(z["X"].astype(np.float32)); y.append(z["y"])
X = np.concatenate(X); y = np.concatenate(y)
print("train patches", len(y), "class counts", np.bincount(y, minlength=4).tolist())
clf = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, class_weight="balanced", max_iter=2000))
clf.fit(X, y)
OUT = H / "sam_labels"; OUT.mkdir(exist_ok=True)
ev = [l for l in (H / "eval_scenes.txt").read_text().splitlines() if l and not l.startswith("#")]
yt, yp = [], []
for sc in ev:
    emb = np.load(H / "sam_dense/eval" / f"{sc}.npz")["emb"].astype(np.float32)      # 256x64x64
    pred = clf.predict(emb.reshape(256, -1).T).reshape(64, 64).astype(np.uint8)
    lab = np.kron(pred, np.ones((16, 16), np.uint8))                                 # 1024x1024
    Image.fromarray(lab).save(OUT / f"{sc}.png")
    gold = np.array(Image.open(D / "labels/test/masked-gold-min3-100agree" / f"{sc}_merged.png"))
    g = gold.reshape(64, 16, 64, 16).transpose(0, 2, 1, 3).reshape(64, 64, 256)
    for a in range(64):
        for b in range(64):
            lb = g[a, b][g[a, b] != 255]
            if len(lb) >= 128: yt.append(np.bincount(lb, minlength=4).argmax()); yp.append(pred[a, b])
yt, yp = np.array(yt), np.array(yp)
cm = confusion_matrix(yt, yp, labels=[0, 1, 2, 3])
acc = float((yt == yp).mean())
per = {n: (float(cm[i, i] / cm[i].sum()) if cm[i].sum() else None) for i, n in enumerate(["soil", "bedrock", "sand", "big_rock"])}
res = dict(train_patches=int(len(y)), eval_patches=int(len(yt)), patch_accuracy=acc, recall_per_class=per,
           confusion_rows_gold_cols_pred=cm.tolist(), gold_counts=np.bincount(yt, minlength=4).tolist())
(H / "sam_probe_eval.json").write_text(json.dumps(res, indent=1))
print(json.dumps(res, indent=1))
