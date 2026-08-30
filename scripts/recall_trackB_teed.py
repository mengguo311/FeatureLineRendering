"""TRACK B — install + batch-cache a LEARNED 2D edge detector (TEED) over the chair views.

*** METHOD-PATH. Mesh-free. No mesh_oracle import. ***

TEED (github.com/xavysp/TEED, "Tiny and Efficient Model for the Edge Detection
Generalization", ICCVW 2023) ships its BIPED-pretrained weights INSIDE the repo
(checkpoints/BIPED/<epoch>/<epoch>_model.pth, 249 KB — the model is 58K parameters), so no
external weight download is needed.  No DexiNed/PiDiNet fallback was required.

THE REPO'S EXACT CONTRACT (read off dataset.py:401-435, main.py:127-168,
utils/img_processing.py:39-140 — not guessed):
  input   BGR uint8 -> float32, MINUS mean_bgr = [104.007, 116.669, 122.679].  NO /255
          rescale, no ImageNet std.  Layout CHW.
  model   TED().forward(x) -> [out_1, out_2, out_3, block_cat]; the FUSED map the repo
          scores with is the LAST element (img_processing.py:151 `fuse_num = shape[0]-1`).
  output  torch.sigmoid(fused).  The repo then min-max stretches it per image and INVERTS
          it for the saved PNG; we cache the raw sigmoid instead, because a per-image
          contrast stretch is not comparable ACROSS views and the M1a evidence aggregate is
          multi-view.  (`--normalize` reproduces the repo's stretch as an ablation.)

ALPHA.  The chair PNGs are RGBA; they are composited over WHITE before the forward pass —
the same background final_recipe.photo_edge_map composites over, and the background
`out/2dgs_chair` was trained with (cfg_args white_background=True).  Feeding TEED the raw
premultiplied RGB would put a fake black halo on every silhouette.

SCALE.  TEED was trained at ~512 px; the chair renders are 800.  The net is fully
convolutional so 800 runs natively, but its receptive field is then relatively smaller.
Both are cached per view — `native` (800) and `ms` (elementwise max over scales 1.0 and
0.64, each resampled back to 800) — and TRACK C chooses between them ON THE VAL VIEWS,
never on TEST.
"""
import os
import sys
import time
import json
import argparse

import cv2
import numpy as np
import torch

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
TEED_DIR = os.path.expanduser("~/3dgs_line/ext/TEED")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts/explore/syn"))

from src import common
import final_recipe as FR

OUT = os.path.join(TIER1, "out")
MEAN_BGR = np.array([104.007, 116.669, 122.679], np.float32)   # dataset.py dataset_info
DEFAULT_CKPT = os.path.join(TEED_DIR, "checkpoints/BIPED/5/5_model.pth")  # main.py default
SCALES = (1.0, 0.64)                                            # 0.64*800 = 512 = train res


def load_teed(ckpt, device="cuda"):
    if TEED_DIR not in sys.path:
        sys.path.insert(0, TEED_DIR)
    from ted import TED
    model = TED().to(device).eval()
    sd = torch.load(ckpt, map_location=device)
    model.load_state_dict(sd)
    n = sum(p.numel() for p in model.parameters())
    return model, n


def composite_white(rgba_path):
    """RGBA png -> BGR uint8 over a WHITE background (identical to FR.photo_edge_map)."""
    im = cv2.imread(rgba_path, cv2.IMREAD_UNCHANGED)
    if im.ndim == 3 and im.shape[2] == 4:
        a = im[:, :, 3:4].astype(np.float32) / 255.0
        return (im[:, :, :3].astype(np.float32) * a + 255.0 * (1 - a)).astype(np.uint8)
    return im[:, :, :3]


@torch.no_grad()
def teed_edge(model, bgr, scales=SCALES, device="cuda"):
    """-> dict(native=[H,W] float32 in (0,1), ms=[H,W] float32) : sigmoid of the fused map."""
    H, W = bgr.shape[:2]
    outs = {}
    for s in scales:
        if s == 1.0:
            img = bgr
        else:
            h8 = int(round(H * s / 8)) * 8
            w8 = int(round(W * s / 8)) * 8
            img = cv2.resize(bgr, (w8, h8), interpolation=cv2.INTER_AREA)
        x = img.astype(np.float32) - MEAN_BGR
        x = torch.from_numpy(x.transpose(2, 0, 1))[None].to(device)
        p = torch.sigmoid(model(x)[-1])[0, 0].float().cpu().numpy()
        if p.shape != (H, W):
            p = cv2.resize(p, (W, H), interpolation=cv2.INTER_LINEAR)
        outs[s] = p
    ms = np.maximum.reduce([outs[s] for s in scales])
    return {"native": outs[1.0].astype(np.float32), "ms": ms.astype(np.float32)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="chair")
    ap.add_argument("--ckpt", default=DEFAULT_CKPT)
    ap.add_argument("--cache", default=os.path.join(OUT, "teed_edges_chair"))
    ap.add_argument("--sample_views", type=int, nargs="*", default=[0, 25, 50])
    args = ap.parse_args()

    os.makedirs(args.cache, exist_ok=True)
    cams, rgb_paths = common.load_cameras(args.scene)
    print(f"[trackB] {len(cams)} views, ckpt={args.ckpt}", flush=True)

    model, nparam = load_teed(args.ckpt)
    print(f"[trackB] TEED loaded: {nparam} parameters "
          f"({nparam/1000:.1f}K) on {torch.cuda.get_device_name(0)}", flush=True)

    # ---- smoke test on one view before committing to the batch
    bgr0 = composite_white(rgb_paths[0])
    e0 = teed_edge(model, bgr0)
    for k, v in e0.items():
        print(f"[trackB] smoke {k}: shape={v.shape} dtype={v.dtype} "
              f"min={v.min():.4f} max={v.max():.4f} mean={v.mean():.4f} "
              f"frac>0.5={float((v > 0.5).mean()):.4f}", flush=True)
    assert e0["native"].shape == bgr0.shape[:2], "TEED output shape != input"
    assert 0.0 <= e0["native"].min() and e0["native"].max() <= 1.0, "not a probability"
    assert e0["native"].max() > 0.5, "TEED produced no confident edge — check preprocessing"

    # ---- batch
    t0 = time.time()
    stats = []
    for i, p in enumerate(rgb_paths):
        bgr = composite_white(p)
        e = teed_edge(model, bgr)
        np.savez_compressed(os.path.join(args.cache, f"v{i:03d}.npz"),
                            native=e["native"].astype(np.float16),
                            ms=e["ms"].astype(np.float16))
        stats.append({"view": i, "name": os.path.basename(p),
                      "frac_gt_0.5_native": float((e["native"] > 0.5).mean()),
                      "frac_gt_0.5_ms": float((e["ms"] > 0.5).mean())})
        if i % 20 == 0:
            print(f"  [{i:3d}/{len(rgb_paths)}] {os.path.basename(p)} "
                  f"frac>0.5 native={stats[-1]['frac_gt_0.5_native']:.4f} "
                  f"ms={stats[-1]['frac_gt_0.5_ms']:.4f}", flush=True)
    dt = time.time() - t0
    print(f"[trackB] cached {len(rgb_paths)} views in {dt:.1f}s "
          f"({dt/len(rgb_paths)*1000:.1f} ms/view, 2 scales each)", flush=True)

    # ---- side-by-side TEED vs Canny visuals
    viz = []
    for v in args.sample_views:
        bgr = composite_white(rgb_paths[v])
        e = teed_edge(model, bgr)
        canny = FR.photo_edge_map(rgb_paths[v])
        cv_img = np.dstack([255 - canny] * 3)
        tn = (255 * (1.0 - e["native"])).astype(np.uint8)
        tm = (255 * (1.0 - e["ms"])).astype(np.uint8)
        panel = np.concatenate([bgr, cv_img,
                                np.dstack([tn] * 3), np.dstack([tm] * 3)], 1)
        cv2.putText(panel, "RGB | CANNY(M1a) | TEED native | TEED ms",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
        pth = os.path.join(OUT, f"teed_sample_{args.scene}_v{v}.png")
        cv2.imwrite(pth, panel)
        viz.append(pth)
        print(f"[trackB] viz -> {pth}", flush=True)

    meta = {"scene": args.scene, "ckpt": args.ckpt, "detector": "TEED (xavysp/TEED)",
            "n_params": int(nparam), "scales": list(SCALES), "cache": args.cache,
            "n_views": len(rgb_paths), "runtime_s": dt,
            "ms_per_view": dt / len(rgb_paths) * 1000, "viz": viz,
            "mean_bgr": MEAN_BGR.tolist(), "background": "white composite",
            "per_view": stats}
    jp = os.path.join(OUT, f"teed_cache_{args.scene}.json")
    json.dump(meta, open(jp, "w"), indent=2)
    print(f"[trackB] wrote {jp}", flush=True)
    print(f"[trackB] DONE. cache size: "
          f"{sum(os.path.getsize(os.path.join(args.cache,f)) for f in os.listdir(args.cache))/1e6:.1f} MB",
          flush=True)


if __name__ == "__main__":
    main()
