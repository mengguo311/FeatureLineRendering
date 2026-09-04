"""EXPERIMENT Y — the TRUE limit of "retrain the 3DGS to be line-favourable".

*** EVAL ONLY.  Substitutes GT-mesh depth into the frozen cull to BOUND retraining. ***

The 3DGS reaches the frozen extractor as a depth buffer consumed by tri_edges.surface_cull
(free-space / occlusion vote, rel_eps=0.02, min_frac=0.5).  The best a line-favourable retrain
could ever do to that buffer is make it EXACT.  So replace it with the ground-truth mesh depth
-- a 3DGS with literally perfect geometry -- keep the frozen cull rule byte-for-byte, and read
off the resulting F1.  That is the ceiling on every retraining scheme, oracle or not, at any
strength, for this extractor.  (This is a BOUND, not a method: it uses the GT mesh.)
"""
import json
import os
import sys

import numpy as np
import torch
from scipy.spatial import cKDTree

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
OUT = os.path.join(TIER1, "out", "xy")
REL_EPS, MIN_FRAC = 0.02, 0.5
VIEWS_TEST = [5, 15, 25, 35, 45, 55, 65, 75, 85, 95]


def main():
    from src import common, view_split
    from src.mesh_oracle import MeshOracle
    dev = torch.device("cuda:0")
    scene = "cadpartA"
    cams, _ = common.load_cameras(scene)
    gb_views = view_split.TRAIN
    rad = json.load(open(os.path.join(OUT, "xy_expY.json")))["radius_world"]
    gt = np.load(os.path.join(TIER1, "cache", f"dexp0_gt_{scene}_a30.npz"))
    cp = gt["crease_pts"]
    seen = np.zeros(len(cp), bool)
    for v in VIEWS_TEST:
        seen[gt[f"idx{v}"]] = True
    si = np.where(seen)[0]
    tg = cKDTree(cp)
    o = MeshOracle(scene, angle_deg=30.0, device="cuda")

    res = {"rel_eps": REL_EPS, "min_frac": MIN_FRAC, "n_gbuf_views": len(gb_views),
           "radius_world": rad,
           "note": ("GT-mesh depth substituted into the FROZEN tri_edges.surface_cull. "
                    "Bounds every retraining scheme: the best a retrain can do to the depth "
                    "buffer the extractor consumes is make it exact.")}
    for sc, lab in [("cadpartA", "A_vanilla"), ("cadpartB", "B_ORACLE")]:
        z = np.load(os.path.join(TIER1, "out", f"dexprimary_p1b_cloud_{sc}_ref40.npz"))
        P = z["P"]
        Pt = torch.tensor(P, dtype=torch.float64, device=dev)
        n_on = torch.zeros(len(P), dtype=torch.float64, device=dev)
        n_vis = torch.zeros(len(P), dtype=torch.float64, device=dev)
        for v in gb_views:
            cam = cams[v]
            d = o.render_depth(cam).double()                  # EXACT GT mesh depth
            R = torch.tensor(cam.w2c[:3, :3], dtype=torch.float64, device=dev)
            t = torch.tensor(cam.w2c[:3, 3], dtype=torch.float64, device=dev)
            Xc = Pt @ R.T + t
            zc = Xc[:, 2]
            u = cam.f * Xc[:, 0] / zc.clamp(min=1e-6) + cam.K[0, 2]
            vv = cam.f * Xc[:, 1] / zc.clamp(min=1e-6) + cam.K[1, 2]
            ui = u.round().long().clamp(0, cam.W - 1)
            vi = vv.round().long().clamp(0, cam.H - 1)
            inb = (zc > 1e-6) & (u >= 0) & (u <= cam.W - 1) & (vv >= 0) & (vv <= cam.H - 1)
            dm = d[vi, ui]
            occluded = zc > dm * (1.0 + REL_EPS)
            on_surf = (zc - dm).abs() <= REL_EPS * zc
            counts = inb & torch.isfinite(dm) & ~occluded
            n_vis += counts.double()
            n_on += (counts & on_surf).double()
            o._depth_cache.clear()
            torch.cuda.empty_cache()
        keep_gt = ((n_vis > 0) & (n_on >= MIN_FRAC * n_vis)).cpu().numpy()

        def score(k):
            Q = P[k]
            R_ = float((cKDTree(Q).query(cp[si], k=1, workers=-1)[0] <= rad).mean())
            P_ = float((tg.query(Q, k=1, workers=-1)[0] <= rad).mean())
            return {"n": int(k.sum()), "recall": round(R_, 4), "precision": round(P_, 4),
                    "F1": round(2 * R_ * P_ / (R_ + P_), 4)}

        base = (z["support"] >= 2) & z["surface_keep"] & (z["resid"] <= 1.0)
        gtc = (z["support"] >= 2) & keep_gt & (z["resid"] <= 1.0)
        res[lab] = {"frozen_3dgs_cull": score(base), "EXACT_GT_DEPTH_cull": score(gtc)}
        print(lab, json.dumps(res[lab]), flush=True)
    a = res["A_vanilla"]
    res["delta_F1_perfect_geometry_over_A"] = round(
        a["EXACT_GT_DEPTH_cull"]["F1"] - a["frozen_3dgs_cull"]["F1"], 4)
    res["rule_required"] = 0.15
    json.dump(res, open(os.path.join(OUT, "xy_gtdepth_limit.json"), "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
