"""EXPERIMENT Y — retrain ideal-ceiling falsification on the pure-geometry CAD part.

*** EVAL ONLY.  The GT mesh LABELS and SCORES; it never enters the extraction path. ***
*** Condition B (scene cadpartB) was TRAINED WITH GROUND-TRUTH MESH CREASES.  It is a  ***
*** SIMULATED IDEAL UPPER BOUND, NOT a proposed method.  Labelled ORACLE everywhere.   ***

For each condition (A vanilla / B oracle / B' honest) this scores the SAME frozen DexiNed
multi-view triangulation run on that condition's 3DGS, against the CAD part's real dihedral
creases:
    3D recall@1.5px-equiv, precision@1.5px-equiv, F1, Chamfer (both directions)
and then, on a 120-frame HELD-OUT orbit that no condition trained on, the project's own
crown-jewel temporal metric (src/stroke_metric.py: forward-warp -> Frechet match -> P_pop),
computed with a byte-identical operator for every condition, alongside the per-frame Canny
baseline the 7-13x banked win is measured against.

FROZEN DECISION RULE (pre-registered, not adjustable here)
    B must beat A by >= +0.15 F1 on geometric creases AND must not worsen temporal coherence.
    Otherwise retraining is KILLED permanently.
"""
import argparse
import json
import os
import sys
import time

import cv2
import numpy as np
import torch
from scipy.spatial import cKDTree

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
OUT = os.path.join(TIER1, "out", "xy")
CGLIB = os.path.expanduser("~/cglib")
W = H = 800


def load_traj(scene, split):
    """cameras from transforms_<split>.json, same convention as src.common.load_cameras."""
    from src.common import Camera
    meta = json.load(open(f"{CGLIB}/data/full/{scene}/transforms_{split}.json"))
    f = 0.5 * W / np.tan(0.5 * meta["camera_angle_x"])
    K = np.array([[f, 0, W / 2], [0, f, H / 2], [0, 0, 1]], np.float64)
    flip = np.diag([1.0, -1.0, -1.0, 1.0])
    out = []
    for fr in meta["frames"]:
        c2w = np.array(fr["transform_matrix"], np.float64) @ flip
        out.append(Camera(K, np.linalg.inv(c2w), H, W, name=os.path.basename(fr["file_path"])))
    return out


def tangents_pca(P, k=12):
    """local principal direction of the extracted cloud -> linelet tangents for chaining."""
    tr = cKDTree(P)
    d, idx = tr.query(P, k=min(k + 1, len(P)), workers=-1)
    Q = P[idx[:, 1:]] - P[:, None, :]
    C = np.einsum("nkc,nkd->ncd", Q, Q)
    w, V = np.linalg.eigh(C)
    return V[:, :, 2], float(np.median(d[:, 1]))


def temporal(chain3d, cams, g, keep_g, args, do_baseline=True):
    """P_pop + Frechet over a camera path, for OURS (object-space chains) and, optionally,
    the per-frame Canny BASELINE.  Identical warp operator for both (stroke_metric.py)."""
    from src import render, stroke_metric, strokes
    from m1b_stroke_temporal import ours_strokes, baseline_strokes
    frames = []
    for c in cams:
        gb = render.render_gbuffer(g, keep_g, c, with_albedo=True)
        depth = gb["depth"].detach().cpu().numpy()
        gray = np.clip(gb["albedo"].detach().cpu().numpy().mean(2) * 255, 0, 255).astype(np.uint8)
        A = ours_strokes(chain3d, c, gb["depth"])
        B = (strokes.trace_polylines(cv2.Canny(gray, args.canny_lo, args.canny_hi) > 0,
                                     min_len=args.min_len, approx_eps=args.approx_eps)
             if do_baseline else [])
        frames.append({"depth": depth, "A": A, "B": B, "cam": c})
        del gb
        torch.cuda.empty_cache()
    acc = {p: {"fre": [], "pop": [], "unm": [], "cut": [], "n": [], "drop": []}
           for p in ("A", "B")}
    for i in range(len(frames) - 1):
        f0, f1 = frames[i], frames[i + 1]
        for p in ("A", "B"):
            src, dst = f0[p], f1[p]
            if not do_baseline and p == "B":
                continue
            acc[p]["n"].append(len(src))
            w_, surv = stroke_metric.warp_strokes(src, f0["depth"], f0["cam"], f1["cam"])
            dropped = int((~surv).sum()) if len(surv) else 0
            m = stroke_metric.match_strokes(w_, dst, n_resample=args.n_resample,
                                            max_cand=args.max_cand,
                                            cand_radius=args.cand_radius,
                                            match_thresh=args.match_thresh)
            pp = stroke_metric.pop_penalty(m, n_dropped_by_warp=dropped)
            if len(m["frechet"]):
                acc[p]["fre"].append(m["frechet"])
            acc[p]["pop"].append(pp["P_pop"])
            acc[p]["unm"].append(pp["unmatched_frac"])
            acc[p]["cut"].append(pp["cut_frac"])
            acc[p]["drop"].append(dropped / max(len(src), 1))
    res = {}
    for p in ("A", "B"):
        if not acc[p]["pop"]:
            continue
        fre = np.concatenate(acc[p]["fre"]) if acc[p]["fre"] else np.zeros(0)
        res["OURS" if p == "A" else "canny_baseline"] = {
            "P_pop": float(np.mean(acc[p]["pop"])),
            "frechet_median": float(np.median(fre)) if len(fre) else float("nan"),
            "frechet_p90": float(np.percentile(fre, 90)) if len(fre) else float("nan"),
            "unmatched_frac": float(np.mean(acc[p]["unm"])),
            "cut_frac": float(np.mean(acc[p]["cut"])),
            "warp_dropped_frac": float(np.mean(acc[p]["drop"])),
            "n_strokes_per_frame": float(np.mean(acc[p]["n"])),
        }
    return res


def halo_probe(g, keep_g, P_gt, cams, scene, tag):
    """agy's predicted failure mode: does the intervention spawn a low-opacity FLOATER HALO
    around the creases instead of a sharp 1D curve?  Measured, and rendered for inspection."""
    from src import render
    mu, opa = g["mu"], g["opacity"]
    sc = g["scale"]
    d = cKDTree(P_gt).query(mu, k=1, workers=-1)[0]
    px = 4.031128875572954 / (0.5 * 800 / np.tan(0.5 * 0.6911112070083618))
    near = d <= 3.0 * px
    shell = (d > 3.0 * px) & (d <= 10.0 * px)
    out = {"n_gauss": int(len(mu)),
           "n_kept_by_defloat": int(keep_g.sum()),
           "defloat_removed_frac": round(float(1 - keep_g.mean()), 4),
           "n_within_3px_of_GT_crease": int(near.sum()),
           "n_in_3to10px_shell": int(shell.sum()),
           "halo_ratio_shell_over_near": round(float(shell.sum() / max(near.sum(), 1)), 4),
           "frac_of_near_crease_surviving_defloat":
               round(float(keep_g[near].mean()), 4) if near.sum() else None}
    for nm, msk in (("near_crease", near), ("shell_3to10px", shell), ("all", np.ones(len(mu), bool))):
        if msk.sum() == 0:
            continue
        out[nm] = {"opacity_p50": round(float(np.median(opa[msk])), 4),
                   "opacity_frac_below_0.1": round(float((opa[msk] < 0.1).mean()), 4),
                   "min_scale_px_p50": round(float(np.median(sc[msk].min(1)) / px), 3),
                   "aniso_p50": round(float(np.median(sc[msk].max(1) / np.clip(sc[msk].min(1), 1e-9, None))), 2)}
    for v in (0, 5):
        gb = render.render_gbuffer(g, keep_g, cams[v], with_albedo=True)
        a = gb["alpha"].detach().cpu().numpy()
        alb = gb["albedo"].detach().cpu().numpy()
        img = np.clip(alb * 255, 0, 255).astype(np.uint8)[..., ::-1]
        cv2.imwrite(os.path.join(OUT, f"halo_{tag}_v{v}_render.png"), img)
        # low-alpha halo visualiser: stretch alpha in [0, 0.35] so faint floaters glow
        cv2.imwrite(os.path.join(OUT, f"halo_{tag}_v{v}_alpha_lowstretch.png"),
                    cv2.applyColorMap(np.clip(a / 0.35, 0, 1).astype(np.float32).__mul__(255)
                                      .astype(np.uint8), cv2.COLORMAP_INFERNO))
        out[f"view{v}_alpha_frac_in_0.02_0.35"] = round(float(((a > 0.02) & (a < 0.35)).mean()), 5)
        del gb
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--conditions", default="cadpartA:A_vanilla,cadpartB:B_ORACLE,cadpartH:Bp_honest")
    ap.add_argument("--tag", default="_ref40")
    ap.add_argument("--tau_px", type=float, default=1.5)
    ap.add_argument("--min_support", type=int, default=2)
    ap.add_argument("--resid_max", type=float, default=1.0)
    ap.add_argument("--n_orbit", type=int, default=60)
    ap.add_argument("--budget", type=int, default=20000,
                    help="voxel-dedup every condition's cloud to a COMMON size before "
                         "chaining, so the temporal comparison is a statement about the "
                         "cloud and not about how many points it has (dexprimary_p0 protocol)")
    ap.add_argument("--min_nodes", type=int, default=8)
    ap.add_argument("--canny_lo", type=int, default=50)
    ap.add_argument("--canny_hi", type=int, default=150)
    ap.add_argument("--min_len", type=int, default=4)
    ap.add_argument("--approx_eps", type=float, default=1.0)
    ap.add_argument("--n_resample", type=int, default=16)
    ap.add_argument("--max_cand", type=int, default=6)
    ap.add_argument("--cand_radius", type=float, default=40.0)
    ap.add_argument("--match_thresh", type=float, default=3.0)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    from src import common, render, view_split, strokes
    from dexprimary_p0 import gt_labels

    VIEWS = view_split.TEST
    conds = [c.split(":") for c in args.conditions.split(",")]
    base_scene = conds[0][0]
    crease_pts, gtvis, bbox_diag = gt_labels(base_scene, VIEWS)
    res_all, t0 = {}, time.time()
    cams0, _ = common.load_cameras(base_scene)
    seen = np.zeros(len(crease_pts), bool)
    zs = []
    for v in VIEWS:
        idx = gtvis[int(v)][0]
        seen[idx] = True
        q = crease_pts[idx]
        zs.append((cams0[v].w2c[:3, :3] @ q.T).T[:, 2] + cams0[v].w2c[2, 3])
    seen_idx = np.where(seen)[0]
    rad = args.tau_px * float(np.median(np.concatenate(zs))) / cams0[VIEWS[0]].f
    tree_gt = cKDTree(crease_pts)
    print(f"[Y] GT crease pts={len(crease_pts)} seen in TEST={len(seen_idx)} "
          f"radius={rad:.6f} ({rad/ (4.031128875572954/cams0[VIEWS[0]].f):.2f} px-equiv)",
          flush=True)

    for scene, label in conds:
        cloud = os.path.join(TIER1, "out", f"dexprimary_p1b_cloud_{scene}{args.tag}.npz")
        if not os.path.exists(cloud):
            print(f"[Y] MISSING {cloud} -- run dexprimary_p1b for {scene} first", flush=True)
            continue
        z = np.load(cloud)
        keep = (z["support"] >= args.min_support) & z["surface_keep"] & \
               (z["resid"] <= args.resid_max)
        P = z["P"][keep]
        d_rec = cKDTree(P).query(crease_pts[seen_idx], k=1, workers=-1)[0]
        d_pre = tree_gt.query(P, k=1, workers=-1)[0]
        R = float((d_rec <= rad).mean())
        Pr = float((d_pre <= rad).mean())
        F1 = 0.0 if (R + Pr) == 0 else 2 * R * Pr / (R + Pr)
        row = {"label": label, "scene": scene, "cloud": os.path.basename(cloud),
               "n_cloud_raw": int(len(z["P"])), "n_cloud_kept": int(len(P)),
               "recall_3D": round(R, 4), "precision_3D": round(Pr, 4), "F1_3D": round(F1, 4),
               "chamfer_gt_to_pred_median": round(float(np.median(d_rec)), 6),
               "chamfer_pred_to_gt_median": round(float(np.median(d_pre)), 6),
               "chamfer_symmetric_median": round(float(0.5 * (np.median(d_rec) +
                                                              np.median(d_pre))), 6)}
        g = common.load_gaussians(scene)
        keep_g = render.defloat_mask(g["mu"], g["opacity"])
        row["n_gaussians"] = int(len(g["mu"]))
        # budget-matched cloud: identical point count for every condition, so P_pop is not
        # just reading off which condition happened to produce more carriers.
        from dexprimary_p0 import voxel_budget
        bidx = voxel_budget(P, args.budget)
        Pb = P[bidx]
        row["n_cloud_budget_matched"] = int(len(Pb))
        db_r = cKDTree(Pb).query(crease_pts[seen_idx], k=1, workers=-1)[0]
        db_p = tree_gt.query(Pb, k=1, workers=-1)[0]
        Rb = float((db_r <= rad).mean())
        Pr_b = float((db_p <= rad).mean())
        row["recall_3D_budget"] = round(Rb, 4)
        row["precision_3D_budget"] = round(Pr_b, 4)
        row["F1_3D_budget"] = round(0.0 if (Rb + Pr_b) == 0 else 2 * Rb * Pr_b / (Rb + Pr_b), 4)
        t, spacing = tangents_pca(Pb)
        l = np.full(len(Pb), spacing)
        ch, kept = strokes.chain_linelets_3d(Pb, t, l, nms_radius_mult=1.0, k=10,
                                             cos_tan=0.60, cos_col=0.50, gap_mult=4.0,
                                             min_nodes=args.min_nodes)
        Pk = Pb[kept]
        chain3d = [Pk[c] for c in ch]
        row["n_chains"] = len(chain3d)
        row["n_chain_pts"] = int(sum(len(c) for c in chain3d))
        print(f"[Y] {label}: cloud {len(P)} -> {len(chain3d)} chains "
              f"(R={R:.4f} P={Pr:.4f} F1={F1:.4f}) ({time.time()-t0:.0f}s)", flush=True)
        orb = load_traj(scene, "orbit")[:args.n_orbit]
        row["temporal_heldout_orbit"] = temporal(chain3d, orb, g, keep_g, args)
        row["floater_halo"] = halo_probe(g, keep_g, crease_pts, cams0, scene, label)
        res_all[label] = row
        print(f"[Y] {label} temporal: " + json.dumps(row["temporal_heldout_orbit"]), flush=True)

    # ---- the frozen decision rule ------------------------------------------------------
    verdict = {}
    if "A_vanilla" in res_all and "B_ORACLE" in res_all:
        A, B = res_all["A_vanilla"], res_all["B_ORACLE"]
        dF1 = B["F1_3D"] - A["F1_3D"]
        dF1b = B["F1_3D_budget"] - A["F1_3D_budget"]
        ap_ = A["temporal_heldout_orbit"]["OURS"]["P_pop"]
        bp_ = B["temporal_heldout_orbit"]["OURS"]["P_pop"]
        af_ = A["temporal_heldout_orbit"]["OURS"]["frechet_median"]
        bf_ = B["temporal_heldout_orbit"]["OURS"]["frechet_median"]
        worse = (bp_ > ap_) or (bf_ > af_)
        verdict = {"delta_F1_B_minus_A": round(dF1, 4),
                   "delta_F1_B_minus_A_budget_matched": round(dF1b, 4),
                   "F1_A": A["F1_3D"], "F1_B": B["F1_3D"],
                   "rule_F1_gain_required": 0.15,
                   "F1_gate_passed": bool(dF1 >= 0.15),
                   "P_pop_A": round(ap_, 5), "P_pop_B": round(bp_, 5),
                   "frechet_median_A": round(af_, 5), "frechet_median_B": round(bf_, 5),
                   "temporal_worsened_by_B": bool(worse),
                   "Y_DECISION": ("PROCEED (scoped second contribution)"
                                  if (dF1 >= 0.15 and not worse) else
                                  "KILL retraining permanently"),
                   "note": ("Condition B is a GT-mesh-supervised ORACLE UPPER BOUND. A failure "
                            "here bounds every non-oracle retraining scheme from above.")}
    out = {"experiment": "Y", "radius_world": rad, "tau_px": args.tau_px,
           "views_TEST": list(map(int, VIEWS)), "n_orbit_frames": args.n_orbit,
           "conditions": res_all, "verdict": verdict}
    jp = os.path.join(OUT, "xy_expY.json")
    json.dump(out, open(jp, "w"), indent=1)
    print(json.dumps({"verdict": verdict}, indent=1))
    print(f"[Y] wrote {jp} ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
