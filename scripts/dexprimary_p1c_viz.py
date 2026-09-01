"""Phase 1c viz — candidates coloured by predicted crease-prob vs GT label, one TEST view."""
import os
import sys
import json
import argparse

import cv2
import numpy as np
import torch
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
OUT = os.path.join(TIER1, "out")

from src import common, render, visibility

def composite_white(path):
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if im.ndim == 3 and im.shape[2] == 4:
        a = im[:, :, 3:4].astype(np.float32) / 255.0
        im = (im[:, :, :3].astype(np.float32) * a + 255.0 * (1 - a)).astype(np.uint8)
    return im[:, :, ::-1]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="chair")
    ap.add_argument("--view", type=int, default=15)
    ap.add_argument("--score", default=None, help="score key in the npz; default = best probe")
    args = ap.parse_args()
    scene = args.scene

    z = np.load(os.path.join(OUT, f"dexp1c_scores_{scene}.npz"))
    res = json.load(open(os.path.join(OUT, f"dexprimary_p1c_{scene}.json")))
    P, y = z["P"], z["y"]
    if args.score is None:
        cand = [k for k in z.files if k.endswith("_probe") or "probe" in k]
        best, key = -1, None
        for name, d in res.get("probes", {}).items():
            a = d.get("refsplit", {}).get("eval_auc", 0) or 0
            nk = name.replace(":", "_").replace("(", "_").replace(")", "") + "_probe" \
                 if not name.startswith("FAM") else None
            if a > best:
                best, key = a, name
        # map probe name -> npz key
        m = {"FAM-A": "FAM-A_probe", "FAM-B": "FAM-B_probe",
             "FAM-C(dino)": "FAM-C_probe", "A+B+C": "A+B+C_probe"}
        key = m.get(key, "FAM-C_probe")
    else:
        key, best = args.score, float("nan")
    s = z[key]
    print(f"[viz] score = {key} (eval AUC {best:.4f})")

    cams, rgb_paths = common.load_cameras(scene)
    g = common.load_gaussians(scene)
    kg = render.defloat_mask(g["mu"], g["opacity"])
    v = args.view
    gb = render.render_gbuffer(g, kg, cams[v])
    vis, uv, _ = visibility.visible_mask(P, cams[v], gb["depth"])
    del gb; torch.cuda.empty_cache()
    lab = (y >= 0) & vis & np.isfinite(s)
    rgb = composite_white(rgb_paths[v])
    thr = np.nanmedian(s[y >= 0][(y[y >= 0] == 1)]) * 0.0 + \
          np.nanpercentile(s[lab], 100 * (1 - (y[lab] == 1).mean()))  # rate-matched thr

    fig, axs = plt.subplots(1, 3, figsize=(16.5, 5.8))
    for ax in axs:
        ax.set_xlim(0, 800); ax.set_ylim(800, 0); ax.set_xticks([]); ax.set_yticks([])
    axs[0].imshow(rgb, alpha=0.35)
    m1 = lab & (y == 0); m2 = lab & (y == 1)
    axs[0].scatter(uv[m1, 0], uv[m1, 1], s=0.15, c="red", linewidths=0, alpha=0.55)
    axs[0].scatter(uv[m2, 0], uv[m2, 1], s=0.15, c="#00b000", linewidths=0, alpha=0.8)
    axs[0].set_title(f"{scene} TEST v{v} — GT label\nCREASE (green) vs TEXTURE (red)")
    axs[1].imshow(rgb, alpha=0.35)
    sc = axs[1].scatter(uv[lab, 0], uv[lab, 1], s=0.15, c=s[lab], cmap="viridis",
                        linewidths=0, alpha=0.8, vmin=np.nanpercentile(s[lab], 2),
                        vmax=np.nanpercentile(s[lab], 98))
    plt.colorbar(sc, ax=axs[1], fraction=0.04)
    axs[1].set_title(f"predicted crease-prob ({key})")
    axs[2].imshow(rgb, alpha=0.35)
    pred = s >= thr
    for m, c, l in ((lab & (y == 1) & pred, "#00b000", "TP"),
                    (lab & (y == 0) & pred, "red", "FP"),
                    (lab & (y == 1) & ~pred, "#ff8c00", "FN")):
        axs[2].scatter(uv[m, 0], uv[m, 1], s=0.15, c=c, linewidths=0, alpha=0.8, label=l)
    axs[2].legend(markerscale=40, loc="lower right")
    axs[2].set_title(f"decision @ rate-matched thr\nTP green / FP red / FN orange")
    p = os.path.join(OUT, f"dexprimary_p1c_{scene}.png")
    plt.tight_layout(); plt.savefig(p, dpi=130); plt.close()
    print(f"wrote {p}")

if __name__ == "__main__":
    main()
