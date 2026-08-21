"""tier1/scripts/m1b_ablation_carrier.py — HONEST ABLATION (not a headline result, and
not a fix for the falsified separation gates).

CARRIER-PERSISTENCE PRUNE: before chaining, drop linelets whose 3D carrier does not
project stably across at least k views (n_vis >= k AND multi-view inlier ratio >= r).
Measured on two axes:

  (i)  chair FP-LINE-DENSITY inside GT-verified-FLAT regions   (mesh EVAL-ONLY, mask only)
  (ii) the STEP-06 popping metric P_pop and the Frechet residual

This is a persistence filter on an already-extracted carrier. It cannot separate a
printed line from a crease — a fabric print is static geometry in this reconstruction and
therefore persists perfectly well — so any FP reduction here comes from removing weakly
supported carriers, NOT from recognising texture. Texture false positives are reported as
false positives throughout; they are never reframed as intentional hatching.
"""
import argparse
import json
import os
import subprocess
import sys

import cv2
import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))

from src import common, render, visibility, view_split
import run_m1b
from m1b_headline import _Shim

OUT = os.path.join(TIER1, "out")


def flat_fp(scene, masks, crease_clear=(5.0, 8.0), sil_clear=4.0):
    """FP line px per kilopixel of GT-flat region, for each named keep-mask."""
    from src.mesh_oracle import MeshOracle                     # EVAL ONLY (mask only)
    cams, _ = common.load_cameras(scene)
    g = common.load_gaussians(scene)
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    o = MeshOracle(scene)
    z = np.load(os.path.join(OUT, f"linelets_{scene}_ungated_test.npz"))
    acc = {n: {c: {"px": 0, "cent": 0, "area": 0} for c in crease_clear} for n in masks}
    for v in view_split.TEST:
        cam = cams[v]
        md = o.render_depth(cam, view_key=int(v)).cpu().numpy()
        mfg = md < 1e8
        sil = mfg ^ (cv2.erode(mfg.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)
        sdt = cv2.distanceTransform((~sil).astype(np.uint8), cv2.DIST_L2, 5)
        uvq = o.visible_crease_uv(cam, view_key=int(v))
        cm = np.zeros(mfg.shape, bool)
        cm[np.clip(np.round(uvq[:, 1]).astype(int), 0, cam.H - 1),
           np.clip(np.round(uvq[:, 0]).astype(int), 0, cam.W - 1)] = True
        cdt = cv2.distanceTransform((~cm).astype(np.uint8), cv2.DIST_L2, 5)
        gb = render.render_gbuffer(g, keep_g, cam)
        for name, km in masks.items():
            Lv = {"p": z["p"], "t": z["t"], "l": z["l"], "keep": km}
            mask, _ = run_m1b.raster_segments(_Shim(cam, gb["depth"]), 0, Lv["p"],
                                             Lv["t"], Lv["l"], keep=km)
            vis, uv, _ = visibility.visible_mask(z["p"], cam, gb["depth"])
            sel = vis & km
            cu = np.clip(np.round(uv[sel, 0]).astype(int), 0, cam.W - 1)
            cv_ = np.clip(np.round(uv[sel, 1]).astype(int), 0, cam.H - 1)
            for c in crease_clear:
                flat = mfg & (cdt > c) & (sdt > sil_clear)
                a = acc[name][c]
                a["area"] += int(flat.sum())
                a["px"] += int((mask & flat).sum())
                a["cent"] += int(flat[cv_, cu].sum())
        del gb
    out = {}
    for c in crease_clear:
        rec = {}
        for name in masks:
            a = acc[name][c]
            kpx = max(a["area"], 1) / 1000.0
            rec[name] = {"n_linelets": int(masks[name].sum()),
                         "fp_line_px_per_kpx": a["px"] / kpx,
                         "fp_linelets_per_kpx": a["cent"] / kpx,
                         "flat_area_px": a["area"]}
        out[f"crease_clear_{c:g}px"] = rec
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="chair")
    ap.add_argument("--cp_ratio", type=float, default=0.8)
    ap.add_argument("--cp_views", type=int, default=20)
    ap.add_argument("--frames", type=int, default=120)
    args = ap.parse_args()

    z = np.load(os.path.join(OUT, f"linelets_{args.scene}_ungated_test.npz"))
    base = z["keep"].astype(bool)
    cp = base & (z["inlier_ratio"] >= args.cp_ratio) & (z["n_vis"] >= args.cp_views)
    print(f"[ablation] {args.scene}: keep {base.sum()} -> carrier-persistence "
          f"(inlier>={args.cp_ratio}, n_vis>={args.cp_views}) {cp.sum()} "
          f"({100.0*cp.sum()/max(base.sum(),1):.1f}%)", flush=True)

    res = {"scene": args.scene, "cp_ratio": args.cp_ratio, "cp_views": args.cp_views,
           "n_keep_base": int(base.sum()), "n_keep_cp": int(cp.sum())}
    print("(i) chair FP density inside GT-flat regions ...", flush=True)
    res["flat_fp"] = flat_fp(args.scene, {"base": base, "carrier_persistence": cp})
    for k, rec in res["flat_fp"].items():
        b, c = rec["base"], rec["carrier_persistence"]
        d = 100.0 * (c["fp_line_px_per_kpx"] / max(b["fp_line_px_per_kpx"], 1e-9) - 1)
        print(f"   {k}: {b['fp_line_px_per_kpx']:.2f} -> {c['fp_line_px_per_kpx']:.2f} "
              f"FP line px/kpx  ({d:+.1f}%)", flush=True)

    print("(ii) popping metric with and without the prune ...", flush=True)
    res["stroke_temporal"] = {}
    for name, extra in (("base", []), ("carrier_persistence", ["--carrier_persistence",
                                                               "--cp_ratio", str(args.cp_ratio),
                                                               "--cp_views", str(args.cp_views)])):
        tag = f"_abl_{name}"
        cmd = [sys.executable, os.path.join(TIER1, "scripts", "m1b_stroke_temporal.py"),
               "--scenes", args.scene, "--frames", str(args.frames), "--tag", tag] + extra
        subprocess.run(cmd, check=True, env=dict(os.environ, CUDA_VISIBLE_DEVICES="1"),
                       stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        t = json.load(open(os.path.join(OUT, f"m1b_stroke_temporal_table{tag}.json")))
        m = t["scenes"][args.scene]["by_frames"][str(args.frames)]
        res["stroke_temporal"][name] = {
            "chain": t["scenes"][args.scene]["chain"],
            "OURS": {k: m["A"][k] for k in ("frechet_median", "P_pop", "unmatched_frac",
                                            "cut_frac", "n_strokes_per_frame")},
            "BASELINE": {k: m["B"][k] for k in ("frechet_median", "P_pop")},
        }
        o = res["stroke_temporal"][name]["OURS"]
        print(f"   {name}: OURS frechet_med {o['frechet_median']:.3f} "
              f"P_pop {o['P_pop']:.3f} strokes/frame {o['n_strokes_per_frame']:.0f}",
              flush=True)

    p = os.path.join(OUT, f"m1b_ablation_carrier_{args.scene}.json")
    json.dump(res, open(p, "w"), indent=2)
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
