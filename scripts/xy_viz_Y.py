"""EXPERIMENT Y viz — Condition A vs B(ORACLE) vs B'(honest) line drawings, side by side,
plus the FLOATER-HALO inspection panel.

*** EVAL ONLY.  Condition B was trained with GT-mesh creases: ORACLE UPPER BOUND, NOT a method. ***
"""
import argparse
import json
import os
import sys

import cv2
import numpy as np
from scipy.spatial import cKDTree

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
OUT = os.path.join(TIER1, "out", "xy")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--conditions", default="cadpartA:A_vanilla,cadpartB:B_ORACLE,cadpartH:Bp_honest")
    ap.add_argument("--tag", default="_ref40")
    ap.add_argument("--views", default="0,30")
    args = ap.parse_args()
    from src import common, render, strokes, visibility
    from xy_expY import tangents_pca, load_traj

    conds = [c.split(":") for c in args.conditions.split(",")]
    for v in [int(x) for x in args.views.split(",")]:
        panels, halos = [], []
        for scene, label in conds:
            cloud = os.path.join(TIER1, "out", f"dexprimary_p1b_cloud_{scene}{args.tag}.npz")
            if not os.path.exists(cloud):
                print(f"skip {label}: no {cloud}")
                continue
            z = np.load(cloud)
            keep = (z["support"] >= 2) & z["surface_keep"] & (z["resid"] <= 1.0)
            P = z["P"][keep]
            t, sp = tangents_pca(P)
            ch, kept = strokes.chain_linelets_3d(P, t, np.full(len(P), sp),
                                                 nms_radius_mult=1.0, k=10, cos_tan=0.60,
                                                 cos_col=0.50, gap_mult=4.0, min_nodes=3)
            Pk = P[kept]
            g = common.load_gaussians(scene)
            keep_g = render.defloat_mask(g["mu"], g["opacity"])
            cam = load_traj(scene, "orbit")[v]
            gb = render.render_gbuffer(g, keep_g, cam, with_albedo=True)
            depth = gb["depth"]
            alpha = gb["alpha"].detach().cpu().numpy()
            alb = np.clip(gb["albedo"].detach().cpu().numpy() * 255, 0, 255).astype(np.uint8)
            canvas = np.full((cam.H, cam.W, 3), 255, np.uint8)
            npoly = 0
            for c in ch:
                V = Pk[c]
                vis, uv, _ = visibility.visible_mask(V, cam, depth)
                inb = (uv[:, 0] >= 0) & (uv[:, 0] < cam.W) & (uv[:, 1] >= 0) & (uv[:, 1] < cam.H)
                good = vis & inb
                run = []
                for i, gd in enumerate(good):
                    if gd:
                        run.append(uv[i])
                    else:
                        if len(run) >= 2:
                            cv2.polylines(canvas, [np.round(np.array(run)).astype(np.int32)],
                                          False, (25, 25, 25), 1, cv2.LINE_AA)
                            npoly += 1
                        run = []
                if len(run) >= 2:
                    cv2.polylines(canvas, [np.round(np.array(run)).astype(np.int32)],
                                  False, (25, 25, 25), 1, cv2.LINE_AA)
                    npoly += 1
            bar = np.full((52, cam.W, 3), 255, np.uint8)
            cv2.putText(bar, f"{label}", (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.62,
                        (0, 0, 180) if "ORACLE" in label else (0, 0, 0), 2, cv2.LINE_AA)
            cv2.putText(bar, f"cloud {len(P)}  chains {len(ch)}  drawn polylines {npoly}",
                        (8, 44), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (70, 70, 70), 1, cv2.LINE_AA)
            panels.append(np.vstack([bar, canvas]))
            # FLOATER-HALO panel: alpha stretched into [0,0.35] so faint floaters glow
            hb = np.full((52, cam.W, 3), 255, np.uint8)
            frac = float(((alpha > 0.02) & (alpha < 0.35)).mean())
            cv2.putText(hb, f"{label}  low-alpha halo check", (8, 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.62,
                        (0, 0, 180) if "ORACLE" in label else (0, 0, 0), 2, cv2.LINE_AA)
            cv2.putText(hb, f"frac px with 0.02<alpha<0.35 = {frac:.5f}", (8, 44),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.48, (70, 70, 70), 1, cv2.LINE_AA)
            hm = cv2.applyColorMap((np.clip(alpha / 0.35, 0, 1) * 255).astype(np.uint8),
                                   cv2.COLORMAP_INFERNO)
            halos.append(np.vstack([hb, np.hstack([alb[..., ::-1]])[:, :cam.W] // 2 + hm // 2]))
            del gb
        if panels:
            p = os.path.join(OUT, f"xy_Y_lines_v{v}.png")
            cv2.imwrite(p, np.hstack(panels))
            print("wrote", p)
        if halos:
            p = os.path.join(OUT, f"xy_Y_halo_v{v}.png")
            cv2.imwrite(p, np.hstack(halos))
            print("wrote", p)


if __name__ == "__main__":
    main()
