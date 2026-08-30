"""DexiNed-primary PHASE 0 — visualisation.  EVAL/ANALYSIS ONLY (reads the GT-crease cache).

out/dexprimary_phase0_<scene>.png:
  (a) the TEST-view image DexiNed sees
  (b) ALL visible GT creases (blue) with the GAUSSIAN MISS-SET on top (red)
  (c) the DexiNed NMS-thinned edge map
  (d) THE PANEL THAT MATTERS: the miss-set coloured by whether the DexiNed-lifted 3D cloud
      -- built from the OTHER nine TEST views and occlusion-culled into this one -- lands
      within delta px of it.  GREEN = recovered, RED = still missing.
  (e) a zoom on the densest recovered region, so decals are actually legible.
"""
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
from scipy.spatial import cKDTree

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
OUT = os.path.join(TIER1, "out")

from src import common, render, view_split, visibility
from dexprimary_p0 import gt_labels, lift_view, DEPTH_ARMS
from src.epipolar_consensus import nms_thin


def composite_white(path):
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if im.ndim == 3 and im.shape[2] == 4:
        a = im[:, :, 3:4].astype(np.float32) / 255.0
        im = (im[:, :, :3].astype(np.float32) * a + 255.0 * (1 - a)).astype(np.uint8)
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", required=True, choices=["lego", "chair"])
    ap.add_argument("--view", type=int, default=None)
    ap.add_argument("--arm", default="median")
    ap.add_argument("--key", default="native")
    ap.add_argument("--thr", type=float, default=0.5)
    ap.add_argument("--tau", type=float, default=1.5)
    ap.add_argument("--delta", type=float, default=1.5)
    args = ap.parse_args()

    scene, views = args.scene, view_split.TEST
    dex = os.path.join(OUT, f"dexined_edges_{scene}")
    crease_pts, gt, _ = gt_labels(scene, views)
    cams, rgb_paths = common.load_cameras(scene)
    g = common.load_gaussians(scene)
    keep = render.defloat_mask(g["mu"], g["opacity"])
    X_pool = g["mu"][keep]

    # lift every TEST view once (method path)
    gbufs, P, U = {}, {}, {}
    for v in views:
        gb = render.render_gbuffer(g, keep, cams[v], with_median_depth=True)
        gbufs[v] = {"depth": gb["depth"].detach().cpu().numpy(),
                    "depth_t": gb["depth"]}
        L = lift_view(dex, v, cams[v], gb, args.thr, args.key, arms=(args.arm,))
        P[v], U[v] = L[args.arm][0], L[args.arm][1]
        del gb
        torch.cuda.empty_cache()

    # miss-set per view, then choose the view with the most RECOVERED miss-set to show
    def analyse(v):
        cam = cams[v]
        idx, uvq = gt[v]
        vis, uvg, _ = visibility.visible_mask(X_pool, cam, gbufs[v]["depth_t"])
        d_pool = cKDTree(uvg[vis]).query(uvq, k=1)[0]
        miss = d_pool > args.tau
        Pv = np.concatenate([P[u] for u in views if u != v], 0)
        vl, uvl_all, _ = visibility.visible_mask(Pv, cam, gbufs[v]["depth_t"])
        uvl = uvl_all[vl]
        d_l = cKDTree(uvl).query(uvq, k=1)[0]
        return idx, uvq, miss, d_l <= args.delta, uvl

    if args.view is None:
        best, bv = -1, views[0]
        for v in views:
            _, _, miss, rec, _ = analyse(v)
            n = int((miss & rec).sum())
            if n > best:
                best, bv = n, v
        v = bv
    else:
        v = args.view
    idx, uvq, miss, rec, uvl = analyse(v)
    print(f"[viz] {scene} view {v}: gt_vis {len(idx)}  miss {int(miss.sum())} "
          f"({miss.mean():.3f})  recovered-of-miss {int((miss&rec).sum())} "
          f"({(miss&rec).sum()/max(miss.sum(),1):.3f})", flush=True)

    rgb = composite_white(rgb_paths[v])[:, :, ::-1]
    z = np.load(os.path.join(dex, f"v{v:03d}.npz"))
    ed = nms_thin(z[args.key].astype(np.float32)) >= args.thr

    def scat(ax, uv, c, s=0.05, a=0.6):
        ax.scatter(uv[:, 0], uv[:, 1], s=s, c=c, marker=".", linewidths=0, alpha=a)

    fig, axs = plt.subplots(1, 5, figsize=(26, 5.6))
    for ax in axs:
        ax.set_xlim(0, 800); ax.set_ylim(800, 0); ax.set_xticks([]); ax.set_yticks([])
    axs[0].imshow(rgb); axs[0].set_title(f"{scene} TEST view {v}\n(what DexiNed sees)")

    axs[1].imshow(rgb, alpha=0.35)
    scat(axs[1], uvq[~miss], "#1f77b4"); scat(axs[1], uvq[miss], "red", 0.08, 0.8)
    axs[1].set_title(f"GT creases: covered by gaussians (blue)\nvs MISS-SET (red)  "
                     f"|miss|/|GT| = {miss.mean():.3f}  (tau={args.tau})")

    axs[2].imshow(1.0 - ed.astype(np.float32), cmap="gray")
    axs[2].set_title(f"DexiNed (frozen, zero-shot) NMS-thinned\n"
                     f"thr={args.thr}  {int(ed.sum())} edge px")

    axs[3].imshow(rgb, alpha=0.3)
    scat(axs[3], uvq[miss & ~rec], "red", 0.08, 0.85)
    scat(axs[3], uvq[miss & rec], "#00d000", 0.08, 0.85)
    axs[3].set_title(f"MISS-SET recovered by the DexiNed-lifted cloud\n"
                     f"(other 9 views, occlusion-culled)  GREEN={(miss&rec).sum()/max(miss.sum(),1):.3f}")

    # zoom on the densest recovered-miss region
    q = uvq[miss & rec]
    if len(q) > 50:
        Hh, _, _ = np.histogram2d(q[:, 1], q[:, 0], bins=16, range=[[0, 800], [0, 800]])
        r, c = np.unravel_index(Hh.argmax(), Hh.shape)
        cy, cx = (r + 0.5) * 50, (c + 0.5) * 50
    else:
        cy = cx = 400
    hw = 90
    axs[4].imshow(rgb, alpha=0.55)
    scat(axs[4], uvq[miss & ~rec], "red", 3.0, 0.9)
    scat(axs[4], uvq[miss & rec], "#00d000", 3.0, 0.9)
    axs[4].set_xlim(cx - hw, cx + hw); axs[4].set_ylim(cy + hw, cy - hw)
    axs[4].set_title(f"zoom @({int(cx)},{int(cy)}) — the creases the\ngaussian pool has no carrier for")

    p = os.path.join(OUT, f"dexprimary_phase0_{scene}.png")
    plt.tight_layout(); plt.savefig(p, dpi=125); plt.close()
    print(f"wrote {p}")
    json.dump({"scene": scene, "view": int(v), "arm": args.arm, "tau": args.tau,
               "delta": args.delta, "n_gt_vis": int(len(idx)),
               "n_miss": int(miss.sum()), "miss_fraction": float(miss.mean()),
               "n_recovered_of_miss": int((miss & rec).sum()),
               "R_miss_this_view": float((miss & rec).sum() / max(miss.sum(), 1))},
              open(os.path.join(OUT, f"dexprimary_phase0_{scene}_viz.json"), "w"), indent=2)


if __name__ == "__main__":
    main()
