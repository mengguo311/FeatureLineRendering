"""TRACK A — 2DGS-ridge REDUNDANCY GATE (bury or justify the 2DGS additive seeder).

*** EVAL-ONLY DIAGNOSTIC. NOT A METHOD MODULE. ***
The GT mesh appears here only to define the GT crease pixel set (labelling). No 3D seeder
code is written; this is a pure 2D pixel-mask intersection on the eval views.

THE QUESTION
    Post-hoc line extraction is RECALL-capped: ~half the GT crease pixels have no
    photometric Canny edge within tau px.  Does the 2DGS normal-ridge — a texture-blind
    GEOMETRIC 2D signal — recover that MISS-set?  If it recovers < 25%, the whole
    "2DGS-ridge as an additive recall seeder" route is dead and gets buried permanently.

PARTITION (per eval view, tau px tolerance)
    GT            = visible GT crease pixels (MeshOracle, dihedral >= 30 deg, depth-culled)
    S_photo_hit   = GT  n  dilate(Canny_M1a, tau)
    S_photo_miss  = GT \\ S_photo_hit                       (expected ~50% of GT)
    Recall_miss(X)= |S_photo_miss n dilate(mask_X, tau)| / |S_photo_miss|

ARMS
    2dgs_q<Q>     ||grad N||_F of the rendered 2DGS normal map, thresholded at the Q-th
                  percentile over foreground.  Q is swept 50..99 so the verdict is taken at
                  2DGS's BEST, not at one arbitrary threshold — a KILL must be decisive.
    canny_low_*   a SECOND Canny at lower thresholds.  THE CONTROL THAT MATTERS: if cheap
                  photometric re-tuning already recovers the miss-set, the miss-set was
                  never geometric and 2DGS is redundant by construction.
    depth_ridge   |grad depth| ridge from the same 2DGS buffer (2nd geometric arm, free).

THE THREE CONTROLS WITHOUT WHICH THE NUMBER IS MEANINGLESS
    1. CHANCE.  A mask covering p% of the foreground recovers ~p% of ANY pixel set by
       accident.  We report cover = |dilate(mask,tau) n fg| / |fg| and
       LIFT = Recall_miss / cover.  "25% recovery" from a mask covering 25% of the object
       is worth exactly nothing.
    2. MATCHED DENSITY.  The Q sweep is also read at the Q whose dilated foreground cover
       equals Canny's, so 2DGS cannot win by painting more pixels.
    3. SANITY / HIT-SET.  Recall_hit(2DGS) on S_photo_hit must be high: creases that ARE
       photometrically visible are the easy ones, and a ridge mask that misses those is
       broken rather than complementary.

    Also reported: INTERIOR-only (>4 px from the alpha silhouette).  ||grad N|| explodes at
    the silhouette where normals graze, which would hand 2DGS free credit on exactly the
    creases the photometric detector already sees; the interior number is the honest one.

GATE
    Recall_miss(2DGS best, all-GT, tau=2) < 25%  ->  PERMANENTLY KILL 2DGS-ridge seeding.
"""
import os
import sys
import json
import argparse

import cv2
import numpy as np
import torch

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
sys.path.insert(0, os.path.join(TIER1, "scripts/explore/syn"))

from src import common, render2dgs, view_split
from src.mesh_oracle import MeshOracle          # EVAL ONLY — GT crease labelling
import final_recipe as FR

OUT = os.path.join(TIER1, "out")

QS = (50, 60, 70, 80, 85, 90, 92, 95, 97, 99)       # ||grad N|| percentile sweep
TEED_THR = (0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90)   # raw-sigmoid thresholds
TEED_CACHE = os.path.join(OUT, "teed_edges_chair")
TAUS = (1, 2, 3)
TAU_MAIN = 2
INTERIOR_PX = 4.0                                    # distance from silhouette
UNIQ_REF = "canny_sharp_low"                         # cheap-photometric reference arm

# lower-threshold Canny control arms (sigma, lo, hi)
CANNY_LOW = {
    "canny_low_1": ((2.0, 50, 100), (2.5, 40, 80)),      # ~half the M1a thresholds
    "canny_low_2": ((2.0, 25, 50), (2.5, 20, 40)),       # very permissive
    "canny_sharp": ((0, 50, 150),),                       # dt_pull.EDGE_SHARP, unblurred
    "canny_sharp_low": ((0, 20, 60),),                    # unblurred + permissive
}


def load_teed(v, key="native"):
    f = os.path.join(TEED_CACHE, f"v{v:03d}.npz")
    if not os.path.exists(f):
        return None
    return np.load(f)[key].astype(np.float32)


def dil(mask, tau):
    """Binary dilation by an L2 ball of radius tau px (exact, via DT)."""
    if tau <= 0:
        return mask.astype(bool)
    d = cv2.distanceTransform((~mask.astype(bool)).astype(np.uint8), cv2.DIST_L2, 5)
    return d <= tau


def gt_crease_mask(oracle, cam, v, H, W):
    uv = oracle.visible_crease_uv(cam, view_key=int(v))          # EVAL ONLY
    m = np.zeros((H, W), bool)
    if len(uv):
        u = np.round(uv[:, 0]).astype(np.int64)
        vv = np.round(uv[:, 1]).astype(np.int64)
        ok = (u >= 0) & (u < W) & (vv >= 0) & (vv < H)
        m[vv[ok], u[ok]] = True
    return m


def gradn_mag(normal, fg):
    gy, gx = np.gradient(normal.astype(np.float32), axis=(0, 1))
    g = np.sqrt((gx ** 2).sum(-1) + (gy ** 2).sum(-1)).astype(np.float32)
    g[~fg] = 0.0
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="chair")
    ap.add_argument("--model", default=os.path.join(OUT, "2dgs_chair"))
    ap.add_argument("--split", default="val", choices=["val", "test", "both"])
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    cams, rgb_paths = common.load_cameras(args.scene)
    H, W = cams[0].H, cams[0].W
    splits = ["val", "test"] if args.split == "both" else [args.split]

    print(f"[trackA] scene={args.scene} model={args.model} splits={splits}", flush=True)
    g2, pipe, meta = render2dgs.load_2dgs(args.model)
    print(f"[trackA] 2DGS loaded: {meta['n_gauss']} gaussians, iter {meta['iteration']}, "
          f"depth_ratio={meta['depth_ratio']}, white_bg={meta['white_background']}", flush=True)
    oracle = MeshOracle(args.scene)
    print(f"[trackA] mesh oracle: {len(oracle.crease_pts)} GT crease samples", flush=True)

    results = {"scene": args.scene, "model": args.model, "meta": meta,
               "taus": list(TAUS), "tau_main": TAU_MAIN, "qs": list(QS),
               "edge_cfg_m1a": [list(c) for c in FR.EDGE_CFGS], "per_split": {}}

    for sp in splits:
        views = getattr(view_split, sp.upper())
        # accumulators: per (region, tau) -> counts
        acc = {}

        def A(region, tau):
            return acc.setdefault((region, tau), {
                "n_gt": 0, "n_hit": 0, "n_miss": 0, "n_fg": 0,
                "rec_miss": {}, "rec_hit": {}, "cover": {}, "n_mask": {},
                "tp_mask": {}, "uniq_miss": {},
            })

        viz_pack = None
        for vi, v in enumerate(views):
            cam = cams[v]
            # ---- photometric M1a Canny
            canny = FR.photo_edge_map(rgb_paths[v]) > 0
            # ---- 2DGS G-buffer
            with torch.no_grad():
                gb = render2dgs.render_gbuffer_2dgs(
                    g2, pipe, cam, bg_white=meta["white_background"], half_pixel=True)
                nrm = gb["normal"].cpu().numpy()
                alpha = gb["alpha"].cpu().numpy()
                depth = gb["depth"].cpu().numpy()
            del gb
            torch.cuda.empty_cache()
            fg = alpha > 0.5
            gmag = gradn_mag(nrm, fg)
            dep = np.where(np.isfinite(depth) & fg, depth, 0.0).astype(np.float32)
            dgy, dgx = np.gradient(dep, axis=(0, 1))
            dmag = np.sqrt(dgx ** 2 + dgy ** 2).astype(np.float32)
            dmag[~fg] = 0.0
            # ---- GT + interior
            gt = gt_crease_mask(oracle, cam, v, H, W)
            dsil = cv2.distanceTransform(fg.astype(np.uint8), cv2.DIST_L2, 5)
            interior = fg & (dsil > INTERIOR_PX)

            # ---- candidate masks
            masks = {}
            fgv = gmag[fg]
            for q in QS:
                thr = np.percentile(fgv, q) if fgv.size else 0.0
                masks[f"2dgs_q{q}"] = fg & (gmag >= thr)
            dfgv = dmag[fg]
            for q in (90, 95, 99):
                thr = np.percentile(dfgv, q) if dfgv.size else 0.0
                masks[f"depth_q{q}"] = fg & (dmag >= thr)
            for name, cfg in CANNY_LOW.items():
                masks[name] = FR.photo_edge_map(rgb_paths[v], cfgs=cfg) > 0
            masks["canny_m1a"] = canny
            for key in ("native", "ms"):
                te = load_teed(v, key)
                if te is not None:
                    for t in TEED_THR:
                        masks[f"teed_{key}_{t:.2f}"] = te >= t

            for region, rmask in (("all", np.ones((H, W), bool)), ("interior", interior)):
                for tau in TAUS:
                    dcanny = dil(canny, tau)
                    hit = gt & dcanny & rmask
                    miss = gt & ~dcanny & rmask
                    a = A(region, tau)
                    a["n_gt"] += int((gt & rmask).sum())
                    a["n_hit"] += int(hit.sum())
                    a["n_miss"] += int(miss.sum())
                    fgr = fg & rmask
                    a["n_fg"] += int(fgr.sum())
                    dgt = dil(gt, tau)                       # GT-crease neighbourhood
                    ref = dil(masks[UNIQ_REF], tau)          # cheap-photometric reference
                    for name, m in masks.items():
                        dm = dil(m, tau)
                        mf = m & fgr                          # mask pixels, this region only
                        a["rec_miss"][name] = a["rec_miss"].get(name, 0) + int((miss & dm).sum())
                        a["rec_hit"][name] = a["rec_hit"].get(name, 0) + int((hit & dm).sum())
                        a["cover"][name] = a["cover"].get(name, 0) + int((dm & fgr).sum())
                        a["n_mask"][name] = a["n_mask"].get(name, 0) + int(mf.sum())
                        a["tp_mask"][name] = a["tp_mask"].get(name, 0) + int((mf & dgt).sum())
                        a["uniq_miss"][name] = a["uniq_miss"].get(name, 0) + \
                            int((miss & dm & ~ref).sum())

            if vi == 0:
                dcanny = dil(canny, TAU_MAIN)
                viz_pack = dict(v=int(v), rgb=rgb_paths[v], gt=gt,
                                miss=gt & ~dcanny, hit=gt & dcanny,
                                canny=canny, gmag=gmag, fg=fg, interior=interior)
            print(f"  [{sp}] view {v}: gt={int(gt.sum())} miss@2={int((gt & ~dil(canny,2)).sum())}",
                  flush=True)

        # ---- reduce
        out = {}
        for (region, tau), a in acc.items():
            key = f"{region}_tau{tau}"
            nm = max(a["n_miss"], 1)
            nh = max(a["n_hit"], 1)
            nf = max(a["n_fg"], 1)
            rows = {}
            for name in a["rec_miss"]:
                cover = a["cover"][name] / nf
                rm = a["rec_miss"][name] / nm
                nmask = max(a["n_mask"][name], 1)
                rows[name] = {
                    "recall_miss": rm,
                    "recall_hit": a["rec_hit"][name] / nh,
                    "cover_fg": cover,
                    "lift_over_chance": (rm / cover) if cover > 1e-9 else float("nan"),
                    "mask_px_per_view": a["n_mask"][name] / max(len(views), 1),
                    "prec_gt": a["tp_mask"][name] / nmask,
                    "uniq_miss_vs_ref": a["uniq_miss"][name] / nm,
                    "recall_gt_total": (a["rec_miss"][name] + a["rec_hit"][name]) /
                                       max(a["n_gt"], 1),
                }
            out[key] = {
                "n_gt": a["n_gt"], "n_hit": a["n_hit"], "n_miss": a["n_miss"],
                "photo_recall_canny_m1a": a["n_hit"] / max(a["n_gt"], 1),
                "arms": rows,
            }
        results["per_split"][sp] = {"views": [int(x) for x in views], "table": out}

        # ---- viz (first view of the split)
        if viz_pack is not None:
            im = cv2.imread(viz_pack["rgb"], cv2.IMREAD_UNCHANGED)
            a4 = im[:, :, 3:4].astype(np.float32) / 255.0
            base = (im[:, :, :3].astype(np.float32) * a4 + 255.0 * (1 - a4)).astype(np.uint8)
            best_q = max(QS, key=lambda q: out[f"all_tau{TAU_MAIN}"]["arms"][f"2dgs_q{q}"]["recall_miss"]
                         if out[f"all_tau{TAU_MAIN}"]["arms"][f"2dgs_q{q}"]["cover_fg"] <= 0.25 else -1)
            thr = np.percentile(viz_pack["gmag"][viz_pack["fg"]], best_q)
            ridge = viz_pack["fg"] & (viz_pack["gmag"] >= thr)
            dridge = dil(ridge, TAU_MAIN)
            canvas = base.copy()
            canvas[viz_pack["canny"]] = (0, 255, 255)                       # canny = yellow
            miss = viz_pack["miss"]
            canvas[miss & ~dridge] = (0, 0, 255)                            # miss NOT recovered = red
            canvas[miss & dridge] = (0, 255, 0)                             # miss recovered = green
            canvas[viz_pack["hit"]] = (255, 128, 0)                         # photo-hit = blue
            pr = os.path.join(OUT, f"trackA_{args.scene}_{sp}_v{viz_pack['v']}{args.tag}.png")
            side = np.concatenate([base, canvas], 1)
            cv2.imwrite(pr, side)
            results["per_split"][sp]["viz"] = pr
            results["per_split"][sp]["viz_q"] = int(best_q)

    jp = os.path.join(OUT, f"trackA_redundancy_{args.scene}{args.tag}.json")
    json.dump(results, open(jp, "w"), indent=2)
    print(f"\n[trackA] wrote {jp}", flush=True)

    # ------------------------------------------------------------------ report
    for sp, sd in results["per_split"].items():
        for region in ("all", "interior"):
            key = f"{region}_tau{TAU_MAIN}"
            t = sd["table"][key]
            print(f"\n===== {sp.upper()} / {region} / tau={TAU_MAIN} "
                  f"(GT={t['n_gt']} hit={t['n_hit']} miss={t['n_miss']}; "
                  f"Canny photo-recall={t['photo_recall_canny_m1a']:.3f}) =====", flush=True)
            print(f"{'arm':>20} {'Rec_miss':>9} {'R_GTall':>8} {'Rec_hit':>8} "
                  f"{'cover_fg':>9} {'lift':>6} {'prec_GT':>8} {'uniqREF':>8} "
                  f"{'px/view':>9}", flush=True)
            for name, r in sorted(t["arms"].items(),
                                  key=lambda kv: -kv[1]["recall_miss"]):
                print(f"{name:>20} {r['recall_miss']:9.3f} {r['recall_gt_total']:8.3f} "
                      f"{r['recall_hit']:8.3f} {r['cover_fg']:9.3f} "
                      f"{r['lift_over_chance']:6.2f} {r['prec_gt']:8.3f} "
                      f"{r['uniq_miss_vs_ref']:8.3f} {r['mask_px_per_view']:9.0f}",
                      flush=True)

    # ------------------------------------------------------------------ VERDICT
    sp0 = "val" if "val" in results["per_split"] else splits[0]
    t = results["per_split"][sp0]["table"][f"all_tau{TAU_MAIN}"]["arms"]
    ti = results["per_split"][sp0]["table"][f"interior_tau{TAU_MAIN}"]["arms"]
    unbounded = max(((q, t[f"2dgs_q{q}"]) for q in QS), key=lambda kv: kv[1]["recall_miss"])
    # (1) MATCHED-DENSITY: the 2DGS q whose dilated fg cover is closest to canny_m1a's.
    #     A seeder must live inside a comparable pixel budget; this is the honest number.
    ccov = t["canny_m1a"]["cover_fg"]
    mq = min(QS, key=lambda q: abs(t[f"2dgs_q{q}"]["cover_fg"] - ccov))
    # (2) DOMINANCE: at every 2DGS operating point, is there a CHEAP photometric arm that
    #     recovers at least as much of the miss-set with no more fg cover?
    dom = []
    for q in QS:
        r2 = t[f"2dgs_q{q}"]
        beat = [k for k in list(CANNY_LOW) + ["canny_m1a"]
                if t[k]["recall_miss"] >= r2["recall_miss"] and t[k]["cover_fg"] <= r2["cover_fg"]]
        dom.append({"q": q, "recall_miss": r2["recall_miss"], "cover_fg": r2["cover_fg"],
                    "dominated_by": beat})
    n_dom = sum(1 for d in dom if d["dominated_by"])
    verdict = {
        "split": sp0, "tau": TAU_MAIN,
        "canny_photo_recall": results["per_split"][sp0]["table"][f"all_tau{TAU_MAIN}"]["photo_recall_canny_m1a"],
        "PRIMARY_matched_density_2dgs": {"q": mq, **t[f"2dgs_q{mq}"], "canny_cover_fg": ccov},
        "unbounded_argmax_2dgs_DEGENERATE": {"q": unbounded[0], **unbounded[1]},
        "best_2dgs_interior_unbounded": {"q": max(((q, ti[f"2dgs_q{q}"]) for q in QS),
                                                  key=lambda kv: kv[1]["recall_miss"])[0]},
        "dominance_by_cheap_canny": dom,
        "n_2dgs_points_dominated": n_dom, "n_2dgs_points": len(QS),
        "best_canny_low": max(((k, t[k]) for k in CANNY_LOW), key=lambda kv: kv[1]["recall_miss"])[0],
        "best_canny_low_recall_miss": max(t[k]["recall_miss"] for k in CANNY_LOW),
        "KILL_2DGS_RIDGE_SEEDING": bool(t[f"2dgs_q{mq}"]["recall_miss"] < 0.25),
        "KILL_reason_matched_density": f"Recall_miss(2DGS @ matched px budget, q{mq}) = "
                                       f"{t[f'2dgs_q{mq}']['recall_miss']:.3f}",
    }
    results["verdict"] = verdict
    json.dump(results, open(jp, "w"), indent=2)
    print("\n############ TRACK A VERDICT ############", flush=True)
    print(json.dumps(verdict, indent=2), flush=True)
    mm = t[f"2dgs_q{mq}"]
    print(f"\n>>> PRIMARY (matched pixel budget vs Canny, cover {mm['cover_fg']:.3f} "
          f"vs canny {ccov:.3f}): Recall_miss(2DGS q{mq}) = {mm['recall_miss']:.3f} "
          f"(lift {mm['lift_over_chance']:.2f}x chance, prec_GT {mm['prec_gt']:.3f})", flush=True)
    print(f">>> UNBOUNDED argmax (DEGENERATE, reported only to be dismissed): "
          f"q{unbounded[0]} Recall_miss {unbounded[1]['recall_miss']:.3f} at cover "
          f"{unbounded[1]['cover_fg']:.3f} — a mask painted over "
          f"{100*unbounded[1]['cover_fg']:.0f}% of the object", flush=True)
    print(f">>> DOMINANCE: {n_dom}/{len(QS)} 2DGS operating points are matched-or-beaten "
          f"by a CHEAP re-tuned Canny at no more fg cover", flush=True)
    print(f">>> GATE (<0.25 => KILL): "
          f"{'KILL 2DGS-ridge additive seeding' if verdict['KILL_2DGS_RIDGE_SEEDING'] else 'KEEP — real complementarity'}",
          flush=True)


if __name__ == "__main__":
    main()
