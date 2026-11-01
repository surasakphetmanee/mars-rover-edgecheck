#!/usr/bin/env python3
"""sam_features.py -- SAM 2.1 masks + per-mask encoder features (perception arm).

Needs torch + Meta's sam2 package (see README).
  sam_features.py SCENE [SCENE ...]   -> sam_out/<scene>.npz
Per scene: SAM2AutomaticMaskGenerator (Hiera-S, points_per_side=16, defaults
otherwise; fixed 2026-10-30) on the Navcam EDR frame; the image encoder's
embedding (256 x 64 x 64) averaged over each mask (mask resized to 64 x 64).
Stores masks (bool, 1024 x 1024, packed), features, areas, predicted IoU,
and wall times for the generator and the encoder.
"""
import os, sys, time
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
import numpy as np, torch
from pathlib import Path
from PIL import Image
from sam2.build_sam import build_sam2
from sam2.automatic_mask_generator import SAM2AutomaticMaskGenerator
from sam2.sam2_image_predictor import SAM2ImagePredictor

H = Path(__file__).resolve().parent
D = H / "data/ai4mars_test/ai4mars-dataset-merged-0.6/msl/ncam/images/edr"
OUT = H / "sam_out"; OUT.mkdir(exist_ok=True)
CKPT = Path(os.environ.get("SAM2_CKPT", H / "checkpoints/sam2.1_hiera_small.pt"))
dev = "mps" if torch.backends.mps.is_available() else "cpu"
model = build_sam2("configs/sam2.1/sam2.1_hiera_s.yaml", str(CKPT), device=dev)
amg = SAM2AutomaticMaskGenerator(model, points_per_side=16)
pred = SAM2ImagePredictor(model)

for scene in sys.argv[1:]:
    out = OUT / f"{scene}.npz"
    if out.exists(): continue
    img = np.array(Image.open(D / f"{scene}.JPG").convert("RGB"))
    t0 = time.perf_counter()
    with torch.inference_mode():
        masks = amg.generate(img)
    t1 = time.perf_counter()
    with torch.inference_mode():
        pred.set_image(img)
        emb = pred._features["image_embed"][0].float().cpu().numpy()      # 256 x 64 x 64
    t2 = time.perf_counter()
    segs = np.stack([m["segmentation"] for m in masks]) if masks else np.zeros((0,) + img.shape[:2], bool)
    feats = []
    for s in segs:
        small = np.array(Image.fromarray(s.astype(np.uint8) * 255).resize((64, 64), Image.BILINEAR)) / 255.0
        w = small.sum()
        feats.append((emb * small).reshape(256, -1).sum(1) / w if w > 0 else np.zeros(256))
    np.savez_compressed(out, masks=np.packbits(segs, axis=-1), shape=np.array(segs.shape),
                        feats=np.array(feats, dtype=np.float32),
                        area=np.array([m["area"] for m in masks]), iou=np.array([m["predicted_iou"] for m in masks]),
                        t_amg=t1 - t0, t_enc=t2 - t1, device=dev)
    print(f"{scene}: {len(masks)} masks amg={t1-t0:.1f}s enc={t2-t1:.1f}s on {dev}", flush=True)
