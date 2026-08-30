"""Plan #1 STEP B — anatomy of the drawn ink: WHERE does each pipeline put its lines?

*** EVAL-ONLY DIAGNOSTIC (imports tune_lib.Harness -> mesh_oracle). ***

WHY.  On TEST views Plan #1 scores LOWER precision than the vanilla-3DGS M1b baseline
(0.597 vs 0.727 points @1.5px at matched linelet count), yet the 3-panel visualisation
shows the opposite of what that implies: the vanilla pipeline sprays linelets across the
green fabric print, while the 2DGS-gated one hugs the wooden frame and the object contours.
Both cannot be true unless "precision" is crediting something other than what we care about.

The suspicion this file tests: the crease oracle labels a pixel a crease only if a GT MESH
edge with dihedral >= 30 deg projects within 2px of it. An OCCLUDING CONTOUR -- the outline
of a smooth surface against the background -- is a real, drawable feature line but is NOT a
mesh crease, so ink placed there is scored as a false positive. The 2DGS normal gate fires
strongly at contours (the normal turns away from the camera), so Plan #1 would be punished
for a behaviour that is correct for line rendering.

WHAT IS MEASURED, per TEST view, on the rasterised segment mask each pipeline actually draws:
    ink_fabric    drawn px per 1000 px of FLAT PRINTED region
                  (interior, >4px from the silhouette, >3px from any GT crease)
                  -- this is the number Plan #1 is supposed to drive down
    ink_crease    drawn px within 1.5px of a GT crease, per 1000 GT crease px
                  -- the recall side; must not collapse with it
    fp_contour    fraction of FALSE-POSITIVE drawn px that are within 3px of the silhouette
    fp_fabric     fraction of FALSE-POSITIVE drawn px that are interior flat print
If the suspicion is right, Plan #1 shows lower ink_fabric and a higher fp_contour share.
"""
import argparse
import json
import os
import sys

import cv2
import numpy as np
import torch

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))

from src import common, render, render2dgs, view_split
import run_m1b as RM

OUT = os.path.join(TIER1, "out")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="chair")
    ap.add_argument("--model", default=os.path.join(OUT, "2dgs_chair"))
    ap.add_argument("--variants", nargs="*",
                    default=["gated:vanilla", "ungated:vanilla", "plan1:2dgs"])
    ap.add_argument("--tau", type=float, default=1.5)
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    from tune_lib import Harness
    ev = list(view_split.TEST)
    h = Harness(args.scene, views=tuple(ev))
    cams, rgb_paths = common.load_cameras(args.scene)

    # both z-buffer families, so each pipeline is occlusion-tested on its own geometry
    gb_van = {v: h.gbufs[v] for v in ev}
    g2, pipe, meta2 = render2dgs.load_2dgs(args.model)
    gb_2dgs = {}
    for v in ev:
        gb = render2dgs.render_gbuffer_2dgs(g2, pipe, h.cams[v],
                                            bg_white=meta2.get("white_background", True))
        gb_2dgs[v] = {"depth": gb["depth"], "alpha": gb["alpha"]}
    del g2
    torch.cuda.empty_cache()

    # GT-derived region masks (EVAL ONLY)
    regions = {}
    for v in ev:
        im = cv2.imread(rgb_paths[v], cv2.IMREAD_UNCHANGED)
        gt_fg = (im[:, :, 3].astype(np.float32) / 255.0) > 0.5
        sil = gt_fg ^ (cv2.erode(gt_fg.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)
        sdt = cv2.distanceTransform((~sil).astype(np.uint8), cv2.DIST_L2, 5)
        cu, cv_, cdt = h.crease[v]
        interior = gt_fg & (sdt > 4)
        regions[v] = {"fg": gt_fg, "sdt": sdt, "cdt": cdt, "interior": interior,
                      "fabric": interior & (cdt > 3.0),
                      "cu": cu, "cv": cv_}

    out = {}
    for spec in args.variants:
        variant, geom = spec.split(":")
        p = os.path.join(OUT, f"linelets_{args.scene}_{variant}_test.npz")
        if not os.path.exists(p):
            print(f"  [skip] missing {p}")
            continue
        z = np.load(p)
        keep = z["keep"].astype(bool)
        for v in ev:
            h.gbufs[v] = gb_2dgs[v] if geom == "2dgs" else gb_van[v]
        acc = {"ink_fab": 0, "n_fab": 0, "ink_cre": 0, "n_cre": 0,
               "fp": 0, "fp_contour": 0, "fp_fabric": 0, "tp": 0, "drawn": 0}
        for v in ev:
            mask, _ = RM.raster_segments(h, v, z["p"], z["t"], z["l"], keep=keep)
            R = regions[v]
            ys, xs = np.nonzero(mask)
            acc["drawn"] += len(ys)
            acc["ink_fab"] += int(R["fabric"][ys, xs].sum())
            acc["n_fab"] += int(R["fabric"].sum())
            tp = R["cdt"][ys, xs] <= args.tau
            acc["tp"] += int(tp.sum())
            fp = ~tp
            acc["fp"] += int(fp.sum())
            acc["fp_contour"] += int((fp & (R["sdt"][ys, xs] <= 3.0)).sum())
            acc["fp_fabric"] += int((fp & R["fabric"][ys, xs]).sum())
            # crease coverage
            sdt_draw = (cv2.distanceTransform((~mask).astype(np.uint8), cv2.DIST_L2, 5)
                        if mask.any() else np.full(mask.shape, 1e9, np.float32))
            acc["ink_cre"] += int((sdt_draw[R["cv"], R["cu"]] <= args.tau).sum())
            acc["n_cre"] += len(R["cu"])
        out[spec] = {
            "n_linelets": int(keep.sum()),
            "drawn_px_per_view": acc["drawn"] / len(ev),
            "ink_fabric_per_kpx": 1000.0 * acc["ink_fab"] / max(acc["n_fab"], 1),
            "ink_crease_frac": acc["ink_cre"] / max(acc["n_cre"], 1),
            "precision": acc["tp"] / max(acc["drawn"], 1),
            "fp_share_contour": acc["fp_contour"] / max(acc["fp"], 1),
            "fp_share_fabric": acc["fp_fabric"] / max(acc["fp"], 1),
        }
        print(f"  [{spec}] done", flush=True)

    print("\n" + "=" * 100)
    print(f"INK ANATOMY — {args.scene}, TEST views {ev}, tau={args.tau}px")
    print(f"{'pipeline':<20} {'n':>7} {'ink_fabric':>11} {'ink_crease':>11} "
          f"{'precision':>10} {'FP@contour':>11} {'FP@fabric':>10}")
    print("-" * 100)
    for spec, r in out.items():
        print(f"{spec:<20} {r['n_linelets']:>7} {r['ink_fabric_per_kpx']:>11.2f} "
              f"{r['ink_crease_frac']:>11.4f} {r['precision']:>10.4f} "
              f"{r['fp_share_contour']:>11.4f} {r['fp_share_fabric']:>10.4f}")
    print("-" * 100)
    print("  ink_fabric = drawn px per 1000 px of flat printed region  (LOWER = the fabric")
    print("               print is no longer being drawn -- the Plan #1 objective)")
    print("  ink_crease = fraction of GT crease px covered within tau (HIGHER = better)")
    print("  FP@contour = share of false-positive ink sitting on the occluding contour,")
    print("               which the mesh-dihedral oracle does not count as a crease")
    print("=" * 100, flush=True)

    tag = f"_{args.tag}" if args.tag else ""
    pj = os.path.join(OUT, f"plan1_ink_anatomy_{args.scene}{tag}.json")
    json.dump({"scene": args.scene, "views": ev, "tau": args.tau, "rows": out},
              open(pj, "w"), indent=1, default=float)
    print(f"wrote {pj}")


if __name__ == "__main__":
    main()
