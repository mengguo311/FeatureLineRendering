"""NG-MEC Stage 1 — what does the epipolar gate actually DELETE?

*** EVAL-ONLY DIAGNOSTIC (imports mesh_oracle). NOT a method module. ***

The spec's own NO-GO language names the failure mode: "consensus is culling true creases =
localization not selectivity". That is directly measurable and does not need the 3D pipeline.
Partition the TEED edge set of each eval view into KEPT (>= m neighbours support it) and
CULLED, and measure the GT-crease purity of each part, plus the same FP triage
recall_trackC_detector.py uses (occluding contour / sub-30-deg fold / hallucination).

  purity(CULLED) << purity(KEPT)  -> the gate is selective: it deletes junk.
  purity(CULLED) ~= purity(KEPT)  -> the gate is blind: it deletes at random w.r.t. creases.
  purity(CULLED) >  purity(KEPT)  -> the gate is ANTI-selective: it preferentially deletes
                                     true creases, which is localization failure.
"""
import os
import sys
import json
import argparse

import cv2
import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
sys.path.insert(0, os.path.join(TIER1, "scripts/explore/syn"))

from src import common, view_split
from src.mesh_oracle import MeshOracle              # EVAL ONLY
from recall_trackC_detector import (dil, crease_mask, occluding_mask, alpha_fg,
                                    SHALLOW_DEG)    # EVAL-ONLY helpers, reused verbatim

OUT = os.path.join(TIER1, "out")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", required=True)
    ap.add_argument("--arms", nargs="+", required=True, help="epi cache tags, e.g. t1.5_r0_m3")
    ap.add_argument("--teed_cache", default=None)
    ap.add_argument("--tau", type=float, default=2.0)
    ap.add_argument("--splits", nargs="*", default=["val", "test"])
    args = ap.parse_args()

    teed_cache = args.teed_cache or os.path.join(OUT, f"teed_edges_{args.scene}")
    cams, rgb_paths = common.load_cameras(args.scene)
    o30 = MeshOracle(args.scene, angle_deg=30.0, ds=0.0015)
    o10 = MeshOracle(args.scene, angle_deg=SHALLOW_DEG, ds=0.003)
    H, W = cams[0].H, cams[0].W

    from src.epipolar_consensus import teed_binary
    res = {"scene": args.scene, "tau": args.tau, "arms": {}}
    for sp in args.splits:
        views = getattr(view_split, sp.upper())
        acc = {a: {"kept": 0, "kept_gt": 0, "cull": 0, "cull_gt": 0,
                   "cull_occ": 0, "cull_fold": 0, "cull_hall": 0,
                   "kept_occ": 0, "kept_fold": 0, "kept_hall": 0} for a in args.arms}
        n_teed = n_teed_gt = 0
        for v in views:
            cam = cams[v]
            reg = dil(alpha_fg(rgb_paths[v]), 2)
            gt = dil(crease_mask(o30, cam, v, H, W), args.tau)
            gt10 = dil(crease_mask(o10, cam, v, H, W), args.tau)
            md = o30.render_depth(cam, view_key=int(v)).detach().cpu().numpy()
            occ = dil(occluding_mask(md), args.tau)
            E = teed_binary(teed_cache, v) & reg
            n_teed += int(E.sum()); n_teed_gt += int((E & gt).sum())
            for a in args.arms:
                z = np.load(os.path.join(OUT, f"epi_edges_{args.scene}_{a}", f"v{v:03d}.npz"))
                Kp = (z["native"].astype(np.float32) > 0.5) & reg
                Cu = E & ~Kp
                A = acc[a]
                A["kept"] += int(Kp.sum()); A["kept_gt"] += int((Kp & gt).sum())
                A["cull"] += int(Cu.sum()); A["cull_gt"] += int((Cu & gt).sum())
                for nm, msk in (("cull", Cu), ("kept", Kp)):
                    fp = msk & ~gt
                    A[f"{nm}_occ"] += int((fp & occ).sum())
                    A[f"{nm}_fold"] += int((fp & ~occ & gt10).sum())
                    A[f"{nm}_hall"] += int((fp & ~occ & ~gt10).sum())
        row = {}
        for a in args.arms:
            A = acc[a]
            k, c = max(A["kept"], 1), max(A["cull"], 1)
            row[a] = {
                "n_kept": A["kept"], "n_culled": A["cull"],
                "frac_culled": A["cull"] / max(A["kept"] + A["cull"], 1),
                "purity_teed": n_teed_gt / max(n_teed, 1),
                "purity_kept": A["kept_gt"] / k,
                "purity_culled": A["cull_gt"] / c,
                "crease_recall_kept": A["kept_gt"] / max(n_teed_gt, 1),
                "culled_fp_occluding": A["cull_occ"] / max(c - A["cull_gt"], 1),
                "culled_fp_fold": A["cull_fold"] / max(c - A["cull_gt"], 1),
                "culled_fp_hallucination": A["cull_hall"] / max(c - A["cull_gt"], 1),
                "kept_fp_hallucination": A["kept_hall"] / max(k - A["kept_gt"], 1),
            }
        res["arms"][sp] = row
        print(f"\n===== {args.scene} / {sp.upper()} / tau={args.tau} "
              f"(TEED purity {n_teed_gt / max(n_teed,1):.3f}) =====")
        print(f"{'arm':>16} {'%culled':>8} {'pur(KEPT)':>10} {'pur(CULLED)':>12} "
              f"{'ratio':>7} {'creaseRec(kept)':>16} {'culled FP: occ':>15} {'fold':>7} "
              f"{'HALL':>7}")
        for a in args.arms:
            r = row[a]
            ratio = r["purity_culled"] / max(r["purity_kept"], 1e-9)
            print(f"{a:>16} {r['frac_culled'] * 100:7.1f}% {r['purity_kept']:10.3f} "
                  f"{r['purity_culled']:12.3f} {ratio:7.2f} "
                  f"{r['crease_recall_kept']:16.3f} {r['culled_fp_occluding']:15.3f} "
                  f"{r['culled_fp_fold']:7.3f} {r['culled_fp_hallucination']:7.3f}")
    jp = os.path.join(OUT, f"ngmec_s1_cullprobe_{args.scene}.json")
    json.dump(res, open(jp, "w"), indent=2)
    print(f"\nwrote {jp}")


if __name__ == "__main__":
    main()
