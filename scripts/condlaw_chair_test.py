#!/usr/bin/env python
"""CONDLAW — exact chair DRR@80 with PER-LOCUS ARRAYS, on the frozen TEST split.

WHY THIS EXISTS.  scripts/explore/gate_falsify_2dgs.py produced the published chair
"refined 2DGS normal-theta AUC 0.967", but (a) it dumps only summary percentiles, so no
exact ROC / DRR@80 can be recovered from out/2dgs_falsify_chair_full.json, and (b) it
picks views with np.linspace(0, 99, 8) -> [0,14,28,42,57,71,85,99], which is NOT the
frozen split of src/view_split.py (TEST = {5,15,...,95}); 6 of those 8 views are TRAIN.

This script changes NOTHING about the measurement.  It imports the estimator, the arms,
the labelling and the refinement thresholds from gate_falsify_2dgs VERBATIM and only
(1) lets the view list be chosen and (2) dumps the per-locus arrays.

ANALYSIS/DIAGNOSTIC ONLY.  Pure inference - no training, no method-path file, mesh used
solely as the label + flatness oracle (mesh_oracle), exactly as the parent script does.
Outputs are condlaw_-prefixed and overwrite nothing.

  --views test    the frozen TEST split (the honest number)
  --views repro   [0,14,28,42,57,71,85,99] - reproduces the published 0.9668 and so
                  proves this harness is faithful before the TEST number is believed
"""
import argparse
import json
import os
import sys

import cv2
import numpy as np
import torch

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
for p in (TIER1, os.path.join(TIER1, "scripts"), os.path.join(TIER1, "scripts/explore")):
    if p not in sys.path:
        sys.path.insert(0, p)

from src import common, dt_pull                                  # noqa: E402
from src.mesh_oracle import MeshOracle                           # EVAL ONLY  # noqa: E402
from src.view_split import TEST as TEST_VIEWS                    # noqa: E402
import gate_falsify as GF                                        # noqa: E402
import gate_falsify_2dgs as G2                                   # verbatim reuse  # noqa: E402
from condlaw_drr import drr_at_recall, auc_mw                    # noqa: E402

REPRO_VIEWS = [0, 14, 28, 42, 57, 71, 85, 99]        # what the published run used


def collect(scene, views, arms, oracle):
    """Replicates gate_falsify_2dgs.main()'s 'sharp' field loop, keeping raw per-locus arrays."""
    cams, rgb_paths = common.load_cameras(scene)
    cfg = dt_pull.EDGE_SHARP
    acc = {a.name: {s: {"fab": [], "cre": []} for s in ("theta_depth", "theta_normal")}
           for a in arms}

    for v in views:
        cam = cams[v]
        im = cv2.imread(rgb_paths[v], cv2.IMREAD_UNCHANGED)
        a4 = im[:, :, 3:4].astype(np.float32) / 255.0
        gt_fg = a4[:, :, 0] > 0.5
        bgr = (im[:, :, :3].astype(np.float32) * a4 + 255.0 * (1 - a4)).astype(np.uint8)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        gb1 = cv2.GaussianBlur(gray, (0, 0), 1.0)
        gx = cv2.Sobel(gb1, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(gb1, cv2.CV_64F, 0, 1, ksize=3)
        gm = np.sqrt(gx * gx + gy * gy)
        dirx = np.where(gm > 1e-9, gx / np.maximum(gm, 1e-9), 1.0)
        diry = np.where(gm > 1e-9, gy / np.maximum(gm, 1e-9), 0.0)

        uvq = oracle.visible_crease_uv(cam, view_key=int(v))     # EVAL ONLY (labelling)
        cm = np.zeros((cam.H, cam.W), bool)
        cu = np.clip(np.round(uvq[:, 0]).astype(int), 0, cam.W - 1)
        cv_ = np.clip(np.round(uvq[:, 1]).astype(int), 0, cam.H - 1)
        cm[cv_, cu] = True
        cdt = cv2.distanceTransform((~cm).astype(np.uint8), cv2.DIST_L2, 5)

        sil = gt_fg ^ (cv2.erode(gt_fg.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)
        sdt = cv2.distanceTransform((~sil).astype(np.uint8), cv2.DIST_L2, 5)
        interior = gt_fg & (sdt > 4)

        gbufs = {a.name: a.gbuffer(cam, int(v)) for a in arms}
        edge = dt_pull.edge_map(rgb_paths[v], cfg)
        for cls, sel in (("fab", edge & interior & (cdt > 3.0)),
                         ("cre", edge & interior & (cdt <= 2.0))):
            ys, xs = np.nonzero(sel)
            if not len(ys):
                continue
            if len(ys) > G2.MAX_PX_PER_VIEW:                     # same RNG, same seed
                idx = np.random.RandomState(0).choice(len(ys), G2.MAX_PX_PER_VIEW, False)
                ys, xs = ys[idx], xs[idx]
            pxf, pyf = xs.astype(np.float64), ys.astype(np.float64)
            dx_, dy_ = dirx[ys, xs], diry[ys, xs]
            for a in arms:
                d, fg, nrm = gbufs[a.name]
                r = GF.ribbon_measure(pxf, pyf, dx_, dy_, d, fg, cam)
                acc[a.name]["theta_depth"][cls].append((r["theta"], r["ok"]))
                if nrm is not None:
                    rn = G2.ribbon_normal_measure(pxf, pyf, dx_, dy_, nrm, fg)
                    acc[a.name]["theta_normal"][cls].append((rn["theta"], rn["ok"]))
                else:
                    nz = len(pxf)
                    acc[a.name]["theta_normal"][cls].append(
                        (np.full(nz, np.nan), np.zeros(nz, bool)))
        del gbufs
        torch.cuda.empty_cache()
        print(f"  view {v} done", flush=True)

    def catpair(lst):
        if not lst:
            return np.array([]), np.zeros(0, bool)
        return (np.concatenate([x[0] for x in lst]), np.concatenate([x[1] for x in lst]))

    return {a.name: {s: {c: catpair(acc[a.name][s][c]) for c in ("fab", "cre")}
                     for s in ("theta_depth", "theta_normal")} for a in arms}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="chair")
    ap.add_argument("--views", default="test", choices=["test", "repro"])
    ap.add_argument("--model2dgs", default=os.path.join(TIER1, "out/2dgs_chair"))
    ap.add_argument("--no_vanilla", action="store_true")
    ap.add_argument("--target", type=float, default=0.80)
    a = ap.parse_args()

    views = list(TEST_VIEWS) if a.views == "test" else list(REPRO_VIEWS)
    print(f"[condlaw-chair] scene={a.scene} views={a.views} -> {views}")
    oracle = MeshOracle(a.scene)                                 # EVAL ONLY
    arms = []
    if not a.no_vanilla:
        arms.append(G2.VanillaArm(a.scene))
    arms.append(G2.TwoDGSArm("default", a.model2dgs))
    arms.append(G2.MeshArm(oracle))
    print(f"           arms: {[x.name for x in arms]}", flush=True)

    raw = collect(a.scene, views, arms, oracle)

    mesh_name = G2.MeshArm.name
    mtf, mof = raw[mesh_name]["theta_depth"]["fab"]
    mtc, moc = raw[mesh_name]["theta_depth"]["cre"]
    flat_fab = mof & (mtf < G2.FLAT_DEG)          # mesh says locally FLAT  (printed fabric)
    sharp_cre = moc & (mtc > G2.SHARP_DEG)        # mesh says genuinely CREASED
    print(f"\n  refinement (mesh oracle, FLAT<{G2.FLAT_DEG} / SHARP>{G2.SHARP_DEG}): "
          f"flat_fab {int(flat_fab.sum())}/{len(flat_fab)}  "
          f"sharp_cre {int(sharp_cre.sum())}/{len(sharp_cre)}")

    tag = a.views
    dump, rows = {}, {}
    for arm in raw:
        for st in ("theta_depth", "theta_normal"):
            vf, of = raw[arm][st]["fab"]
            vc, oc = raw[arm][st]["cre"]
            key = f"{arm}|{st}".replace(" ", "_")
            dump[f"{key}|fab_val"], dump[f"{key}|fab_ok"] = vf, of
            dump[f"{key}|cre_val"], dump[f"{key}|cre_ok"] = vc, oc
            for scope, (mf, mc) in (("headline", (of, oc)),
                                    ("refined", (of & flat_fab, oc & sharp_cre))):
                sf, sc_ = vf[mf], vc[mc]
                sf, sc_ = sf[np.isfinite(sf)], sc_[np.isfinite(sc_)]
                if len(sf) < 20 or len(sc_) < 20:
                    rows[f"{key}|{scope}"] = {"status": "TOO_FEW",
                                              "n_fab": len(sf), "n_cre": len(sc_)}
                    continue
                A = auc_mw(np.r_[sc_, sf],
                           np.r_[np.ones(len(sc_), bool), np.zeros(len(sf), bool)])
                D = drr_at_recall(sc_, sf, a.target)     # crease=positive, fab=distractor
                rows[f"{key}|{scope}"] = {"status": "OK", "auc": A, "drr": D["drr"],
                                          "thr": D["thr"], "recall": D["recall"],
                                          "n_cre": D["n_cre"], "n_dec": D["n_dec"]}
    dump["flat_fab"], dump["sharp_cre"] = flat_fab, sharp_cre
    np.savez_compressed(os.path.join(TIER1, f"out/condlaw_chair_{tag}.npz"), **dump)
    json.dump({"scene": a.scene, "views": views, "view_set": a.views,
               "flat_deg": G2.FLAT_DEG, "sharp_deg": G2.SHARP_DEG,
               "target_recall": a.target, "model2dgs": a.model2dgs, "rows": rows},
              open(os.path.join(TIER1, f"out/condlaw_chair_{tag}.json"), "w"),
              indent=1, default=float)

    T = round(a.target * 100)
    hdr = (f"{'arm|statistic':<48} {'scope':<9} {'AUC':>7} {'DRR@'+str(T):>7} "
           f"{'thr':>7} {'rec':>6} {'n_cre':>7} {'n_fab':>7}")
    print("\n" + hdr); print("-" * len(hdr))
    for k, r in rows.items():
        arm_st, scope = k.rsplit("|", 1)
        if r["status"] != "OK":
            print(f"{arm_st:<48} {scope:<9} {'N/A':>7}  (n_cre={r['n_cre']} n_fab={r['n_fab']})")
            continue
        print(f"{arm_st:<48} {scope:<9} {r['auc']:7.4f} {r['drr']:7.4f} "
              f"{r['thr']:7.2f} {r['recall']:6.3f} {r['n_cre']:7d} {r['n_dec']:7d}")
    print(f"\nwrote out/condlaw_chair_{tag}.{{json,npz}}")
