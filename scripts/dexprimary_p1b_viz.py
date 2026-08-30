"""Phase 1b viz. EVAL/ANALYSIS ONLY (reads the GT-crease cache).

out/dexprimary_p1b_<scene>.png:
  (a) the TEST view
  (b) GT creases: covered by the gaussian pool (blue) vs the MISS-SET (red)
  (c) the triangulated cloud projected into this view (occlusion-culled)
  (d) THE PANEL: miss-set coloured by whether a TRIANGULATED point sits within the 3D
      1.5px-equivalent radius of it.  GREEN = recovered, RED = still missing.
  (e) localization head-to-head zoom: GT crease (black) vs Phase-0 single-view-depth points
      (orange) vs triangulated points (green) -- does triangulation snap onto the crease?
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

from src import common, render, view_split, visibility, tri_edges as T
from dexprimary_p0 import gt_labels, lift_view


def composite_white(path):
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if im.ndim == 3 and im.shape[2] == 4:
        a = im[:, :, 3:4].astype(np.float32) / 255.0
        im = (im[:, :, :3].astype(np.float32) * a + 255.0 * (1 - a)).astype(np.uint8)
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="chair")
    ap.add_argument("--tag", default="")
    ap.add_argument("--view", type=int, default=None)
    ap.add_argument("--sup", type=int, default=2)
    ap.add_argument("--tau", type=float, default=1.5)
    args = ap.parse_args()
    scene, views = args.scene, view_split.TEST

    z = np.load(os.path.join(OUT, f"dexprimary_p1b_cloud_{scene}{args.tag}.npz"))
    cfg = json.load(open(os.path.join(OUT, f"dexprimary_p1b_{scene}{args.tag}.json")))
    rad = cfg["radii"]["px1.5_equiv"]
    keep = (z["support"] >= args.sup) & z["surface_keep"] & (z["resid"] <= cfg["args"]["resid_max"])
    P_tri = z["P"][keep]
    print(f"[viz] triangulated cloud (sup>={args.sup}, culled): {len(P_tri)}  radius {rad:.5f}")

    crease_pts, gt, _ = gt_labels(scene, views)
    cams, rgb_paths = common.load_cameras(scene)
    g = common.load_gaussians(scene)
    kg = render.defloat_mask(g["mu"], g["opacity"])
    X_pool = g["mu"][kg]

    # Phase-0 single-view cloud from the same reference views, for the head-to-head panel
    refs = cfg["refs"]
    dex = os.path.join(OUT, f"dexined_edges_{scene}")
    P_sv = []
    for r in refs:
        gb = render.render_gbuffer(g, kg, cams[r], with_median_depth=True)
        P_sv.append(lift_view(dex, r, cams[r], gb, cfg["args"]["thr"], cfg["args"]["key"],
                              arms=("median",), halfpix=cfg["args"]["halfpix"])["median"][0])
        del gb
        torch.cuda.empty_cache()
    P_sv = np.concatenate(P_sv)

    tree_tri = cKDTree(P_tri)

    def analyse(v):
        gb = render.render_gbuffer(g, kg, cams[v], with_median_depth=True)
        d = gb["depth"]
        idx, uvq = gt[v]
        vis, uvg, _ = visibility.visible_mask(X_pool, cams[v], d)
        miss = cKDTree(uvg[vis]).query(uvq, k=1)[0] > args.tau
        rec = tree_tri.query(crease_pts[idx], k=1)[0] <= rad      # 3D recovery
        vt, uvt, _ = visibility.visible_mask(P_tri, cams[v], d)
        vs, uvs, _ = visibility.visible_mask(P_sv, cams[v], d)
        del gb
        torch.cuda.empty_cache()
        return idx, uvq, miss, rec, uvt[vt], uvs[vs]

    if args.view is None:
        best, bv = -1, views[0]
        for v in views:
            _, _, m, r_, _, _ = analyse(v)
            if int((m & r_).sum()) > best:
                best, bv = int((m & r_).sum()), v
        v = bv
    else:
        v = args.view
    idx, uvq, miss, rec, uvt, uvs = analyse(v)
    print(f"[viz] {scene} view {v}: gt_vis {len(idx)}  miss {int(miss.sum())} "
          f"({miss.mean():.3f})  3D-recovered-of-miss {int((miss&rec).sum())} "
          f"({(miss&rec).sum()/max(miss.sum(),1):.3f})", flush=True)

    rgb = composite_white(rgb_paths[v])[:, :, ::-1]

    def scat(ax, uv, c, s=0.06, a=0.7):
        if len(uv):
            ax.scatter(uv[:, 0], uv[:, 1], s=s, c=c, marker=".", linewidths=0, alpha=a)

    fig, axs = plt.subplots(1, 5, figsize=(26, 5.6))
    for ax in axs:
        ax.set_xlim(0, 800); ax.set_ylim(800, 0); ax.set_xticks([]); ax.set_yticks([])
    axs[0].imshow(rgb); axs[0].set_title(f"{scene} TEST view {v}")

    axs[1].imshow(rgb, alpha=0.35)
    scat(axs[1], uvq[~miss], "#1f77b4"); scat(axs[1], uvq[miss], "red", 0.09, 0.85)
    axs[1].set_title(f"GT creases: gaussian-covered (blue)\nvs MISS-SET (red)  "
                     f"{miss.mean():.3f}")

    axs[2].imshow(rgb, alpha=0.3); scat(axs[2], uvt, "#8000c0", 0.10, 0.6)
    axs[2].set_title(f"TRIANGULATED cloud (sup>={args.sup}), occlusion-culled\n"
                     f"{len(uvt)} pts visible here / {len(P_tri)} total")

    axs[3].imshow(rgb, alpha=0.3)
    scat(axs[3], uvq[miss & ~rec], "red", 0.09, 0.9)
    scat(axs[3], uvq[miss & rec], "#00d000", 0.09, 0.9)
    axs[3].set_title(f"MISS-SET recovered in 3D by triangulation\n"
                     f"GREEN = {(miss&rec).sum()/max(miss.sum(),1):.3f} "
                     f"(radius {rad:.4f} = 1.5px-equiv)")

    q = uvq[miss & rec]
    if len(q) > 50:
        Hh, _, _ = np.histogram2d(q[:, 1], q[:, 0], bins=16, range=[[0, 800], [0, 800]])
        r_, c_ = np.unravel_index(Hh.argmax(), Hh.shape)
        cy, cx = (r_ + 0.5) * 50, (c_ + 0.5) * 50
    else:
        cy = cx = 400
    hw = 70
    axs[4].imshow(rgb, alpha=0.5)
    scat(axs[4], uvq, "black", 5.0, 0.55)
    scat(axs[4], uvs, "#ff8c00", 5.0, 0.8)
    scat(axs[4], uvt, "#00b000", 5.0, 0.8)
    axs[4].set_xlim(cx - hw, cx + hw); axs[4].set_ylim(cy + hw, cy - hw)
    axs[4].set_title(f"LOCALIZATION zoom @({int(cx)},{int(cy)})\n"
                     f"GT crease (black) / Phase-0 single-view (orange) / triangulated (green)")

    p = os.path.join(OUT, f"dexprimary_p1b_{scene}.png")
    plt.tight_layout(); plt.savefig(p, dpi=125); plt.close()
    print(f"wrote {p}")
    json.dump({"scene": scene, "view": int(v), "sup": args.sup, "radius": rad,
               "n_tri": int(len(P_tri)), "n_gt_vis": int(len(idx)),
               "n_miss": int(miss.sum()), "miss_fraction": float(miss.mean()),
               "n_recovered_of_miss_3D": int((miss & rec).sum()),
               "R_miss_this_view_3D": float((miss & rec).sum() / max(miss.sum(), 1))},
              open(os.path.join(OUT, f"dexprimary_p1b_{scene}_viz.json"), "w"), indent=2)


if __name__ == "__main__":
    main()
