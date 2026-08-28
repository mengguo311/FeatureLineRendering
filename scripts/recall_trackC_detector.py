"""TRACK C.2 — THE DETECTOR GO/NO-GO.  Canny -> TEED, measured in 2D, before any pipeline.

*** EVAL-ONLY DIAGNOSTIC. NOT A METHOD MODULE. ***

This is the cheap decision the spec asks for FIRST: does swapping the M1a photometric edge
source from blurred Canny to learned TEED edges actually move RECALL, and does it do so
without drowning in hallucinated texture?  Nothing downstream is run until this passes.

THE SPEC'S RULE, implemented verbatim
    GO     dRecall = R_GT(TEED) - R_GT(Canny) >= +0.18
       AND recovers >= 35% of Canny's miss-set
       AND seed count < 2.5x Canny            (measured in recall_trackC_seeds.py)
    NO-GO  dRecall < +0.10  OR  GT-edge precision drops > 25% ("texture hallucination
           dominates")

WHY THE PRECISION GUARD NEEDS A DECOMPOSITION TO BE READABLE
    P_GT counts an edge pixel as correct only if a visible GT crease (mesh dihedral >= 30
    deg) sits within tau px.  A detector that draws a COMPLETE line drawing is therefore
    punished for every occluding contour and every shallow fold it gets RIGHT, because
    neither is in the 30-deg crease set.  The M1a Canny is blurred and high-threshold, so
    it simply never draws those — which inflates its P_GT rather than reflecting restraint.
    A bare "precision dropped 26%" verdict cannot tell those two situations apart, and the
    guard's stated intent is specifically "texture hallucination dominates".
    So every non-GT-crease edge pixel is triaged, with the SAME mesh oracle, into:
        occluding     within tau of a mesh-depth discontinuity (silhouette OR interior
                      self-occlusion) -> a real feature line, just not a crease
        shallow_fold  within tau of a >=10-deg mesh crease but not a >=30-deg one
                      -> real geometry below the oracle's arbitrary 30-deg cutoff
        hallucination neither -> fires on flat, non-contour surface.  THIS is texture.
    The identical triage is run on the Canny baseline, so the comparison is symmetric and
    the guard can be read for what it was meant to measure.

PROTOCOL
    Thresholds are chosen ON VAL and reported on VAL and held-out TEST.  Both edge sources
    are scored on identical pixels, identical GT, identical tau.
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
from src.mesh_oracle import MeshOracle          # EVAL ONLY — GT labelling + FP triage
import final_recipe as FR

OUT = os.path.join(TIER1, "out")
TEED_CACHE = os.path.join(OUT, "teed_edges_chair")

THRS = (0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.92,
        0.94, 0.95, 0.96, 0.97, 0.98, 0.985, 0.99, 0.995)
KEYS = ("native", "ms")
TAUS = (1, 1.5, 2, 3)   # 1.5 = the tau the published "Canny edge purity" is quoted at
TAU_MAIN = 2
SHALLOW_DEG = 10.0            # dihedral floor for "real but sub-oracle" folds
DEPTH_STEP_REL = 0.02         # relative depth jump that marks an occluding contour


def nms_thin(p, blur=1.0):
    """Canonical edge NMS: keep p only where it is a local max ALONG its own gradient.

    Canny is non-maximum-suppressed by construction, so its edges are 1 px wide; a raw
    thresholded TEED map is a THICK blob.  Comparing their pixel counts without this step
    measures stroke width, not how many edges each detector found — and every "px/view" and
    "precision" number inherits that confound.  This is the standard BSDS/BIPED evaluation
    pre-step, implemented with the same remap-based NMS final_recipe.crease_ridge_dt uses.
    """
    ps = cv2.GaussianBlur(p, (0, 0), blur) if blur > 0 else p
    gx = cv2.Sobel(ps, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(ps, cv2.CV_32F, 0, 1, ksize=3)
    n = np.sqrt(gx * gx + gy * gy)
    flat = n < 1e-9
    dx = np.where(flat, 1.0, gx / np.maximum(n, 1e-9)).astype(np.float32)
    dy = np.where(flat, 0.0, gy / np.maximum(n, 1e-9)).astype(np.float32)
    Hh, Wd = p.shape
    xs, ys = np.meshgrid(np.arange(Wd, dtype=np.float32),
                         np.arange(Hh, dtype=np.float32), indexing="xy")
    keep = np.ones((Hh, Wd), bool)
    for sgn in (1.0, -1.0):
        q = cv2.remap(p, np.clip(xs + sgn * dx, 0, Wd - 1),
                      np.clip(ys + sgn * dy, 0, Hh - 1), cv2.INTER_LINEAR)
        keep &= p >= q - 1e-6
    return np.where(keep, p, 0.0).astype(np.float32)


def dil(mask, tau):
    if tau <= 0:
        return mask.astype(bool)
    d = cv2.distanceTransform((~mask.astype(bool)).astype(np.uint8), cv2.DIST_L2, 5)
    return d <= tau


def crease_mask(oracle, cam, v, H, W):
    uv = oracle.visible_crease_uv(cam, view_key=int(v))
    m = np.zeros((H, W), bool)
    if len(uv):
        u = np.round(uv[:, 0]).astype(np.int64)
        w = np.round(uv[:, 1]).astype(np.int64)
        ok = (u >= 0) & (u < W) & (w >= 0) & (w < H)
        m[w[ok], u[ok]] = True
    return m


def occluding_mask(mesh_depth):
    """Pixels at a mesh-depth discontinuity: silhouette OR interior self-occlusion."""
    d = np.asarray(mesh_depth, np.float32)
    solid = d < 1e8
    dd = np.where(solid, d, np.nan)
    k = np.ones((3, 3), np.uint8)
    filled = np.where(solid, d, 0.0).astype(np.float32)
    mx = cv2.dilate(filled, k)
    mn = -cv2.dilate(-np.where(solid, d, 1e9).astype(np.float32), k)
    step = np.zeros_like(d, bool)
    ok = solid & (mn < 1e8)
    step[ok] = (mx[ok] - mn[ok]) / np.maximum(d[ok], 1e-6) > DEPTH_STEP_REL
    # silhouette: solid pixel adjacent to empty
    sil = solid & (cv2.dilate((~solid).astype(np.uint8), k) > 0)
    _ = dd
    return step | sil


def alpha_fg(rgb_path):
    im = cv2.imread(rgb_path, cv2.IMREAD_UNCHANGED)
    if im.ndim == 3 and im.shape[2] == 4:
        return im[:, :, 3] > 127
    return np.ones(im.shape[:2], bool)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="chair")
    ap.add_argument("--splits", nargs="*", default=["val", "test"])
    ap.add_argument("--teed_cache", default=None,
                    help="TEED npz cache dir; default out/teed_edges_<scene>")
    ap.add_argument("--canny_variants", action="store_true",
                    help="also score RE-TUNED (un-blurred, permissive) Canny arms. On a "
                         "scene with HIGH native Canny purity this is the arm that decides "
                         "whether a LEARNED detector was needed at all.")
    # CMEPI: the same script now scores MORE THAN ONE learned detector per scene, so the
    # output path must carry which one.  Default "" reproduces the historical file name
    # trackC_detector_<scene>.json bit-for-bit.  Without this the second detector silently
    # destroys the first (it already happened once -- see trackC_detector_chair_ORIG.json).
    ap.add_argument("--tag", default="",
                    help="suffix for out/trackC_detector_<scene><tag>.json")
    # The historical THRS grid (0.50..0.995) was read off TEED, whose raw sigmoid FLOORS at
    # ~0.4377 and never goes near 0.  A detector whose map spans the full [0,1] is already
    # very sparse at 0.5, so that grid cannot bracket its operating point.  Default is the
    # historical tuple, so an un-flagged run is bit-identical.
    ap.add_argument("--thrs", type=float, nargs="*", default=None,
                    help="override the raw-probability threshold grid")
    ap.add_argument("--det_name", default="TEED",
                    help="which learned detector fed --teed_cache. RECORDED AS METADATA "
                         "ONLY: the arm keys stay teed_/nms_/union_ because they name the "
                         "ROLE (raw / NMS-thinned / additive-union-with-Canny), not the "
                         "detector, and the VAL selection rule keys off those prefixes.")
    args = ap.parse_args()
    global TEED_CACHE, THRS
    if args.thrs:
        THRS = tuple(args.thrs)
    TEED_CACHE = args.teed_cache or os.path.join(OUT, f"teed_edges_{args.scene}")
    print(f"[trackC] TEED cache: {TEED_CACHE}", flush=True)

    cams, rgb_paths = common.load_cameras(args.scene)
    H, W = cams[0].H, cams[0].W
    o30 = MeshOracle(args.scene, angle_deg=30.0, ds=0.0015)
    o10 = MeshOracle(args.scene, angle_deg=SHALLOW_DEG, ds=0.003)
    print(f"[trackC] GT creases: {len(o30.crease_pts)} @30deg, "
          f"{len(o10.crease_pts)} @{SHALLOW_DEG}deg", flush=True)

    res = {"scene": args.scene, "taus": list(TAUS), "tau_main": TAU_MAIN,
           "thrs": list(THRS), "keys": list(KEYS),
           "detector": args.det_name, "detector_cache": TEED_CACHE,
           "per_split": {}}

    for sp in args.splits:
        views = getattr(view_split, sp.upper())
        acc = {}

        def A(tau):
            return acc.setdefault(tau, {
                "n_gt": 0, "n_miss": 0, "n_fg": 0,
                "tp": {}, "n_mask": {}, "rec_gt": {}, "rec_miss": {},
                "fp_occ": {}, "fp_shallow": {}, "fp_hall": {}, "n_fp": {},
                "pv_P": {}, "pv_R": {},          # per-view, for the guard's variance
            })

        for v in views:
            cam = cams[v]
            fg = alpha_fg(rgb_paths[v])
            reg = dil(fg, 2)                                # object region incl. silhouette
            gt = crease_mask(o30, cam, v, H, W)
            gt10 = crease_mask(o10, cam, v, H, W)
            md = o30.render_depth(cam, view_key=int(v)).detach().cpu().numpy()
            occ = occluding_mask(md)
            canny = FR.photo_edge_map(rgb_paths[v]) > 0

            masks = {"canny_m1a": canny}
            if args.canny_variants:
                for nm, cfgs in (("cannysharp", ((0, 50, 150),)),
                                 ("cannysharplow", ((0, 20, 60),))):
                    masks[nm] = FR.photo_edge_map(rgb_paths[v], cfgs) > 0
            z = np.load(os.path.join(TEED_CACHE, f"v{v:03d}.npz"))
            for key in KEYS:
                te = z[key].astype(np.float32)
                tn = nms_thin(te)
                for t in THRS:
                    masks[f"teed_{key}_{t:g}"] = te >= t
                    masks[f"nms_{key}_{t:g}"] = tn >= t
                    # ADDITIVE formulation: keep every Canny edge, ADD the TEED ones.
                    # The spec's own framing is that orthogonal recall must be spent
                    # additively, not as a replacement; this arm measures that directly.
                    masks[f"union_{key}_{t:g}"] = canny | (tn >= t)

            for tau in TAUS:
                a = A(tau)
                dgt = dil(gt, tau)
                docc = dil(occ, tau)
                dsh = dil(gt10, tau)
                dcanny = dil(canny, tau)
                miss = gt & ~dcanny
                a["n_gt"] += int(gt.sum())
                a["n_miss"] += int(miss.sum())
                a["n_fg"] += int(reg.sum())
                for name, m in masks.items():
                    mf = m & reg
                    dm = dil(m, tau)
                    tp = mf & dgt
                    fp = mf & ~dgt
                    a["tp"][name] = a["tp"].get(name, 0) + int(tp.sum())
                    a["n_mask"][name] = a["n_mask"].get(name, 0) + int(mf.sum())
                    a["n_fp"][name] = a["n_fp"].get(name, 0) + int(fp.sum())
                    a["rec_gt"][name] = a["rec_gt"].get(name, 0) + int((gt & dm).sum())
                    a["rec_miss"][name] = a["rec_miss"].get(name, 0) + int((miss & dm).sum())
                    f_occ = fp & docc
                    f_sh = fp & ~docc & dsh
                    f_h = fp & ~docc & ~dsh
                    a["fp_occ"][name] = a["fp_occ"].get(name, 0) + int(f_occ.sum())
                    a["fp_shallow"][name] = a["fp_shallow"].get(name, 0) + int(f_sh.sum())
                    a["fp_hall"][name] = a["fp_hall"].get(name, 0) + int(f_h.sum())
                    a["pv_P"].setdefault(name, []).append(
                        float(tp.sum()) / max(int(mf.sum()), 1))
                    a["pv_R"].setdefault(name, []).append(
                        float((gt & dm).sum()) / max(int(gt.sum()), 1))
            print(f"  [{sp}] v{v}: gt={int(gt.sum())} miss@{TAU_MAIN}="
                  f"{int((gt & ~dil(canny, TAU_MAIN)).sum())} occ={int(occ.sum())}", flush=True)

        table = {}
        for tau, a in acc.items():
            rows = {}
            nv = max(len(views), 1)
            for name in a["n_mask"]:
                nm = max(a["n_mask"][name], 1)
                nfp = max(a["n_fp"][name], 1)
                rows[name] = {
                    "R_GT": a["rec_gt"][name] / max(a["n_gt"], 1),
                    "P_GT": a["tp"][name] / nm,
                    "rec_miss": a["rec_miss"][name] / max(a["n_miss"], 1),
                    "px_per_view": a["n_mask"][name] / nv,
                    "fp_frac_occluding": a["fp_occ"][name] / nfp,
                    "fp_frac_shallow_fold": a["fp_shallow"][name] / nfp,
                    "fp_frac_hallucination": a["fp_hall"][name] / nfp,
                    # precision against ALL legitimate feature lines (crease | occluding |
                    # shallow fold) -- a diagnostic, NOT a substitute for the spec's P_GT
                    "P_line": (a["tp"][name] + a["fp_occ"][name] + a["fp_shallow"][name]) / nm,
                    "hallucinated_px_per_view": a["fp_hall"][name] / nv,
                    "P_per_view": a["pv_P"][name],
                    "R_per_view": a["pv_R"][name],
                }
            table[f"tau{tau}"] = {"n_gt": a["n_gt"], "n_miss": a["n_miss"], "arms": rows}
        res["per_split"][sp] = {"views": [int(x) for x in views], "table": table}

    # ---------------------------------------------------------------- selection ON VAL
    val = res["per_split"]["val"]["table"][f"tau{TAU_MAIN}"]["arms"]
    base = val["canny_m1a"]
    teed_names = [n for n in val
                  if n.startswith("nms_") or n.startswith("union_")]  # thinned = fair
    # (a) matched pixel budget
    matched = min(teed_names, key=lambda n: abs(val[n]["px_per_view"] - base["px_per_view"]))
    # (b) the spec's admissible set: precision drop <= 25%, then max recall
    admissible = [n for n in teed_names
                  if (base["P_GT"] - val[n]["P_GT"]) / base["P_GT"] <= 0.25]
    spec_pick = max(admissible, key=lambda n: val[n]["R_GT"]) if admissible else None
    # (c) max recall overall (upper bound on the lever)
    maxrec = max(teed_names, key=lambda n: val[n]["R_GT"])

    def verdict_for(name, split):
        t = res["per_split"][split]["table"][f"tau{TAU_MAIN}"]["arms"]
        b, x = t["canny_m1a"], t[name]
        dR = x["R_GT"] - b["R_GT"]
        pdrop = (b["P_GT"] - x["P_GT"]) / b["P_GT"]
        # the guard's per-view distribution: a 25% bar read off 10 views is only
        # meaningful if the between-view spread is smaller than the bar.
        pv = np.array(x["P_per_view"], float)
        bv = np.array(b["P_per_view"], float)
        drop_pv = (bv - pv) / np.maximum(bv, 1e-9)
        return {
            "arm": name, "split": split,
            "precision_drop_per_view_mean": float(drop_pv.mean()),
            "precision_drop_per_view_std": float(drop_pv.std(ddof=1)),
            "precision_drop_per_view_min": float(drop_pv.min()),
            "precision_drop_per_view_max": float(drop_pv.max()),
            "n_views_drop_gt_25pct": int((drop_pv > 0.25).sum()),
            "n_views": int(len(drop_pv)),
            "R_GT_canny": b["R_GT"], "R_GT_teed": x["R_GT"], "dRecall": dR,
            "rec_miss": x["rec_miss"],
            "P_GT_canny": b["P_GT"], "P_GT_teed": x["P_GT"], "precision_drop_frac": pdrop,
            "px_ratio": x["px_per_view"] / b["px_per_view"],
            "px_per_view_teed": x["px_per_view"], "px_per_view_canny": b["px_per_view"],
            "P_line_canny": b["P_line"], "P_line_teed": x["P_line"],
            "fp_hallucination_teed": x["fp_frac_hallucination"],
            "fp_hallucination_canny": b["fp_frac_hallucination"],
            "hall_px_per_view_teed": x["hallucinated_px_per_view"],
            "hall_px_per_view_canny": b["hallucinated_px_per_view"],
            "GO_dRecall_ge_0.18": bool(dR >= 0.18),
            "GO_recmiss_ge_0.35": bool(x["rec_miss"] >= 0.35),
            "NOGO_dRecall_lt_0.10": bool(dR < 0.10),
            "NOGO_precdrop_gt_0.25": bool(pdrop > 0.25),
        }

    res["selection"] = {"matched_budget": matched, "spec_admissible": spec_pick,
                        "max_recall": maxrec, "n_admissible": len(admissible)}
    res["verdicts"] = {}
    for nm in dict.fromkeys([x for x in (matched, spec_pick, maxrec) if x]):
        for sp in res["per_split"]:
            res["verdicts"][f"{nm}@{sp}"] = verdict_for(nm, sp)

    jp = os.path.join(OUT, f"trackC_detector_{args.scene}{args.tag}.json")
    json.dump(res, open(jp, "w"), indent=2)

    # ---------------------------------------------------------------- report
    for sp in res["per_split"]:
        t = res["per_split"][sp]["table"][f"tau{TAU_MAIN}"]
        print(f"\n===== {sp.upper()} / tau={TAU_MAIN} (GT={t['n_gt']} "
              f"canny-miss={t['n_miss']}) =====", flush=True)
        print(f"{'arm':>20} {'R_GT':>7} {'dRec':>7} {'P_GT':>7} {'Pdrop':>7} "
              f"{'recmiss':>8} {'px/view':>9} {'xCanny':>7} | "
              f"{'FP:occ':>7} {'FP:fold':>8} {'FP:HALL':>8} {'P_line':>7}", flush=True)
        b = t["arms"]["canny_m1a"]
        for name in ["canny_m1a"] + sorted(
                [n for n in t["arms"] if n != "canny_m1a"],
                key=lambda n: -t["arms"][n]["R_GT"]):
            r = t["arms"][name]
            dR = r["R_GT"] - b["R_GT"]
            pd = (b["P_GT"] - r["P_GT"]) / b["P_GT"]
            print(f"{name:>20} {r['R_GT']:7.3f} {dR:+7.3f} {r['P_GT']:7.3f} {pd:+7.3f} "
                  f"{r['rec_miss']:8.3f} {r['px_per_view']:9.0f} "
                  f"{r['px_per_view']/b['px_per_view']:7.2f} | "
                  f"{r['fp_frac_occluding']:7.3f} {r['fp_frac_shallow_fold']:8.3f} "
                  f"{r['fp_frac_hallucination']:8.3f} {r['P_line']:7.3f}", flush=True)

    print("\n############ TRACK C — DETECTOR GO/NO-GO ############", flush=True)
    print(f"selected on VAL: matched_budget={matched}  spec_admissible={spec_pick}  "
          f"max_recall={maxrec}", flush=True)
    for k, v in res["verdicts"].items():
        go = v["GO_dRecall_ge_0.18"] and v["GO_recmiss_ge_0.35"]
        nogo = v["NOGO_dRecall_lt_0.10"] or v["NOGO_precdrop_gt_0.25"]
        print(f"\n--- {k} ---", flush=True)
        print(f"  dRecall {v['dRecall']:+.3f} (canny {v['R_GT_canny']:.3f} -> "
              f"teed {v['R_GT_teed']:.3f})   [GO needs >= +0.18]  "
              f"{'PASS' if v['GO_dRecall_ge_0.18'] else 'fail'}", flush=True)
        print(f"  miss-set recovery {v['rec_miss']:.3f}   [GO needs >= 0.35]  "
              f"{'PASS' if v['GO_recmiss_ge_0.35'] else 'fail'}", flush=True)
        print(f"  P_GT {v['P_GT_canny']:.3f} -> {v['P_GT_teed']:.3f}  "
              f"drop {v['precision_drop_frac']:+.3f}   [NO-GO if > 0.25]  "
              f"{'TRIPPED' if v['NOGO_precdrop_gt_0.25'] else 'ok'}", flush=True)
        print(f"  edge px {v['px_ratio']:.2f}x canny   "
              f"FP-hallucination frac: teed {v['fp_hallucination_teed']:.3f} vs "
              f"canny {v['fp_hallucination_canny']:.3f}  "
              f"({v['hall_px_per_view_teed']:.0f} vs {v['hall_px_per_view_canny']:.0f} px/view)",
              flush=True)
        print(f"  P_line (crease|occluding|fold) {v['P_line_canny']:.3f} -> "
              f"{v['P_line_teed']:.3f}", flush=True)
        print(f"  precision drop PER VIEW: mean {v['precision_drop_per_view_mean']:+.3f} "
              f"sd {v['precision_drop_per_view_std']:.3f} "
              f"range [{v['precision_drop_per_view_min']:+.3f},"
              f"{v['precision_drop_per_view_max']:+.3f}]  "
              f"{v['n_views_drop_gt_25pct']}/{v['n_views']} views exceed the 25% bar",
              flush=True)
        print(f"  => {'GO' if (go and not nogo) else ('NO-GO' if nogo else 'INCONCLUSIVE')}",
              flush=True)
    print(f"\n[trackC] wrote {jp}", flush=True)


if __name__ == "__main__":
    main()
