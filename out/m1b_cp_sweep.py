"""out/m1b_cp_sweep.py — carrier-persistence Pareto sweep (CHEAP axes only).

Turns the ad-hoc cp_ratio=0.8 point into a frontier. For each threshold, on held-out
TEST views only, measures the two cheap axes:
  (1) texture false-positive line density inside GT-VERIFIED-FLAT regions
      (fp_line_px_per_kpx and fp_linelets_per_kpx, at crease-clear 5px and 8px), reusing
      the flat-region mask definition of scripts/m1b_ablation_carrier.py, and
  (2) true-crease recall R@1.5 of the retained linelets.
The expensive forward-warp/Frechet/P_pop pipeline is deliberately NOT run in the loop.

MESH IS EVAL-ONLY: it builds the flat-region mask and supplies the GT crease pixels.
Nothing in the method path sees it. One pass over the views; every threshold is scored
inside that pass so the G-buffer and the mesh depth are rendered once per view.
"""
import json
import os
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
CP_GRID = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
CP_VIEWS = 20          # held fixed at the ablation's value; only cp_ratio is swept
CLEAR = (5.0, 8.0)
SIL_CLEAR = 4.0
TAU_R = 1.5


def main(scene="chair"):
    from src.mesh_oracle import MeshOracle                  # EVAL ONLY
    sfx = "" if scene == "chair" else f"_{scene}"
    z = np.load(os.path.join(OUT, f"linelets_{scene}_ungated_test.npz"))
    base = z["keep"].astype(bool)
    p, t, l = z["p"], z["t"], z["l"]
    masks = {"base": base}
    for cp in CP_GRID:
        masks[f"{cp:.2f}"] = base & (z["inlier_ratio"] >= cp) & (z["n_vis"] >= CP_VIEWS)

    cams, _ = common.load_cameras(scene)
    g = common.load_gaussians(scene)
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    o = MeshOracle(scene)

    acc = {k: {"fp_px": {c: 0 for c in CLEAR}, "fp_cent": {c: 0 for c in CLEAR},
               "area": {c: 0 for c in CLEAR}, "rec_hit": 0} for k in masks}
    n_crease_tot = 0

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
        cy, cx = np.nonzero(cm)
        n_crease_tot += len(cy)
        flats = {c: (mfg & (cdt > c) & (sdt > SIL_CLEAR)) for c in CLEAR}
        gb = render.render_gbuffer(g, keep_g, cam)
        vis, uv, _ = visibility.visible_mask(p, cam, gb["depth"])
        for name, km in masks.items():
            raster, _ = run_m1b.raster_segments(_Shim(cam, gb["depth"]), 0, p, t, l,
                                                keep=km)
            sel = vis & km
            cu = np.clip(np.round(uv[sel, 0]).astype(int), 0, cam.W - 1)
            cv_ = np.clip(np.round(uv[sel, 1]).astype(int), 0, cam.H - 1)
            a = acc[name]
            for c in CLEAR:
                a["fp_px"][c] += int((raster & flats[c]).sum())
                a["fp_cent"][c] += int(flats[c][cv_, cu].sum())
                a["area"][c] += int(flats[c].sum())
            sdt2 = (cv2.distanceTransform((~raster).astype(np.uint8), cv2.DIST_L2, 5)
                    if raster.any() else np.full(raster.shape, 1e9, np.float32))
            a["rec_hit"] += int((sdt2[cy, cx] <= TAU_R).sum())
        del gb
        print(f"  view {v} done", flush=True)

    rows = []
    for name, km in masks.items():
        a = acc[name]
        r = {"cp_ratio": (0.0 if name == "base" else float(name)),
             "label": name, "n_keep": int(km.sum()),
             "crease_R@1.5": a["rec_hit"] / max(n_crease_tot, 1)}
        for c in CLEAR:
            kpx = max(a["area"][c], 1) / 1000.0
            r[f"fp_line_px_per_kpx@{c:g}"] = a["fp_px"][c] / kpx
            r[f"fp_linelets_per_kpx@{c:g}"] = a["fp_cent"][c] / kpx
            r[f"flat_area_px@{c:g}"] = int(a["area"][c])
        rows.append(r)
    b = rows[0]
    for r in rows:
        r["recall_frac_of_base"] = r["crease_R@1.5"] / max(b["crease_R@1.5"], 1e-12)
        r["recall_delta_vs_base"] = r["crease_R@1.5"] - b["crease_R@1.5"]
        r["fp_reduction_pct@5"] = 100.0 * (r["fp_line_px_per_kpx@5"] /
                                           max(b["fp_line_px_per_kpx@5"], 1e-12) - 1)

    # KNEE: maximise FP reduction subject to keeping >=90% of the base crease recall.
    # (The smallest cp_ratio trivially satisfies the recall floor but reduces nothing, so
    #  the operative choice is the LARGEST threshold still inside the floor.)
    ok = [r for r in rows if r["label"] != "base" and r["recall_frac_of_base"] >= 0.90]
    knee = min(ok, key=lambda r: r["fp_line_px_per_kpx@5"]) if ok else None

    out = {"scene": scene, "views": list(view_split.TEST), "cp_views_fixed": CP_VIEWS,
           "flat_area_px_total": {f"{c:g}": int(acc["base"]["area"][c]) for c in CLEAR},
           "tau_recall_px": TAU_R, "n_gt_crease_px_total": int(n_crease_tot),
           "knee_rule": "largest cp_ratio with crease recall >= 90% of base "
                        "(i.e. max FP reduction under the recall floor)",
           "knee": knee, "rows": rows}
    json.dump(out, open(os.path.join(OUT, f"m1b_cp_sweep{sfx}.json"), "w"), indent=2)

    L = [f"# M1b — carrier-persistence Pareto sweep ({scene}, held-out TEST views)\n",
         f"Cheap axes only. cp_views fixed at {CP_VIEWS}; only cp_ratio is swept. "
         f"Flat regions are GT-verified (mesh EVAL-ONLY): on the mesh, >c px from any "
         f"visible GT crease and >{SIL_CLEAR:g} px from the silhouette. Recall is the "
         f"fraction of visible GT crease pixels within {TAU_R} px of a drawn linelet.\n",
         "| cp_ratio | n_keep | FP px/kpx @5 | FP px/kpx @8 | FP linelets/kpx @5 | "
         "crease R@1.5 | recall delta vs base | % of base recall |",
         "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lab = "base (cp=0)" if r["label"] == "base" else f"{r['cp_ratio']:.2f}"
        star = "  **<-- KNEE**" if knee and r["label"] == knee["label"] else ""
        L.append(f"| {lab}{star} | {r['n_keep']} | {r['fp_line_px_per_kpx@5']:.2f} | "
                 f"{r['fp_line_px_per_kpx@8']:.2f} | {r['fp_linelets_per_kpx@5']:.2f} | "
                 f"{r['crease_R@1.5']:.4f} | {r['recall_delta_vs_base']:+.4f} | "
                 f"{100*r['recall_frac_of_base']:.1f}% |")
    if knee:
        L.append(f"\n**KNEE = cp_ratio {knee['cp_ratio']:.2f}**: FP density "
                 f"{b['fp_line_px_per_kpx@5']:.2f} -> {knee['fp_line_px_per_kpx@5']:.2f} "
                 f"px/kpx at crease-clear 5px ({knee['fp_reduction_pct@5']:+.1f}%), "
                 f"keeping {100*knee['recall_frac_of_base']:.1f}% of base true-crease "
                 f"recall ({b['crease_R@1.5']:.4f} -> {knee['crease_R@1.5']:.4f}).")
    open(os.path.join(OUT, f"m1b_cp_sweep{sfx}.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))
    print(f"\nwrote {OUT}/m1b_cp_sweep{sfx}.json + .md")
    return knee


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "chair")
