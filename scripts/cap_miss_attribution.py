"""CAP — Coverage Attribution Probe: WHERE does the recall ceiling come from?

*** EVAL / ANALYSIS ONLY.  It reads the GT mesh (via tune_lib.Harness -> mesh_oracle), which
    the spec explicitly permits for a diagnostic.  It defines NO new method and NO new score,
    and no METHOD-PATH file is added or modified. ***

WHY THIS EXISTS
    ECO established that every arm re-ranks ONE identical candidate pool (n_seeds is
    bit-identical across arms at matched f), so the f=1.00 point -- which keeps every gaussian
    -- bounds the recall of every possible re-ranking.  On lego that bound is R@1.5 = 0.5572.
    The binding constraint there is POOL COVERAGE.  This probe attributes the miss-set before
    any new method is designed.

    CORRECTION (2026-09-04, out/LEGO_THRESHOLD_AUDIT.md).  This docstring used to add
    "i.e. R >= 0.65 is unreachable by ANY ranking method".  That sentence is WITHDRAWN: it is
    false.  The bound 0.5572 is stated at the oracle's 30 deg crease definition, and lego's
    mesh carries one family of ~213,711 edges at exactly 30.000 deg that the threshold splits
    roughly in half through the .obj's 6-decimal vertex quantisation.  Re-scoring this same
    probe at higher thresholds gives R@1.5 = 0.6408 (30.05 deg), 0.6467 (45 deg) and -- past
    the audited sweep -- 0.6650 (60 deg) and 0.6716 (80 deg), so the 0.65 line IS crossed.
    What survives, and is what this probe is actually for, is the CONCLUSION: recall plateaus
    near 0.67, a third of crease pixels stay unreachable by any re-ranking at every threshold,
    precision over the same segments falls 0.6360 -> 0.3004 as the threshold rises, and the
    frozen joint operating gate P@1.5 >= 0.85 AND R@1.5 >= 0.65 is met at NO threshold on
    either scene.  Quote 0.5572 with its 30 deg definition; never as a method-independent
    impossibility claim.  (The separate NGMEC-v2 statement that no lego frontier point reaches
    R = 0.65 concerns the re-ranked operating frontier, whose lego maximum is 0.4080 -- a
    different and still-correct quantity, unaffected by this correction.)

THE MEASUREMENT, using the SAME harness that produces the published P@1.5 / R@1.5
    run_m1b.eval_segments computes recall as
        sdt = distanceTransform(~raster_segments(...));  R = mean(sdt[crease] <= tau)
    so the MISS-SET is exactly the GT crease pixels with sdt > 1.5 at the headline stage
    `AFTER pull+prune[tuned+len]`, f=1.00, aggregated over the 10 held-out TEST views.  The
    same rasteriser, the same crease pixels, the same tau -- nothing re-invented.

    For each missed crease pixel, in the same projected 2D image space of the same view:
        d_pool = min distance to the PRE-SCORING candidate pool  (the de-floatered gaussian
                 centres -- the set the M1a score ranks, i.e. every candidate seed at f=1.00)
        d_raw  = min distance to RAW UNPRUNED 3DGS gaussian centres (the whole .ply, floaters
                 included)
    Both are exact continuous nearest-neighbour distances (cKDTree over the projected uv), not
    pixel-quantised, because the classifier's thresholds are 1.5 and 3.0 px and a DT would
    round them.  The DT-quantised variant is computed too and reported as a cross-check.

    Since pool is a SUBSET of raw, d_raw <= d_pool always.

CLASSES (spec)
    A   d_pool <= 1.5                      a candidate existed; pull+prune discarded it
    B   d_pool >  1.5, split by d_raw:
        B1  1.5 < d_raw <= 3.0             a gaussian exists nearby, sub-pixel off-registration
        B2  d_raw >  3.0                   true void: no gaussian ever placed near this crease

    ONE CASE THE SPEC DOES NOT NAME, AND IT IS REPORTED SEPARATELY RATHER THAN FOLDED SILENTLY:
        B0  d_pool > 1.5 AND d_raw <= 1.5  a gaussian IS within 1.5 px in the raw .ply but is
                                           not in the scored pool -- i.e. DE-FLOATERING removed
                                           it.  Representation is present and recoverable, so
                                           it belongs with B1 in spirit, but the spec's
                                           rho_B2 = |B2| / (|B1| + |B2|) does not mention it.
    rho_B2 is therefore reported BOTH WAYS: spec-literal (B0 excluded from the denominator,
    which INFLATES rho_B2) and with B0 folded into B1 (which DEFLATES it).  If the two readings
    straddle the 0.30 gate that fact is the headline, not an implementation detail.
"""
import os
import sys
import json
import argparse

import cv2
import numpy as np
from scipy.spatial import cKDTree

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
OUT = os.path.join(TIER1, "out")

TAU = 1.5
B1_HI = 3.0


def project_uv(P, cam, margin=64.0):
    """-> uv[N,2] of the points that are in FRONT of the camera and not absurdly far out."""
    from src import common
    uv, _ = common.project(P, cam)
    z = (cam.w2c[:3, :3] @ P.T).T[:, 2] + cam.w2c[2, 3]
    ok = (z > 1e-6) & np.isfinite(uv).all(1) \
        & (uv[:, 0] > -margin) & (uv[:, 0] < cam.W + margin) \
        & (uv[:, 1] > -margin) & (uv[:, 1] < cam.H + margin)
    return uv[ok]


def dt_of_points(uv, H, W):
    """Pixel-quantised distance transform to a projected point set (the cross-check route)."""
    m = np.zeros((H, W), bool)
    if len(uv):
        u = np.round(uv[:, 0]).astype(np.int64)
        v = np.round(uv[:, 1]).astype(np.int64)
        ok = (u >= 0) & (u < W) & (v >= 0) & (v < H)
        m[v[ok], u[ok]] = True
    if not m.any():
        return np.full((H, W), 1e9, np.float32)
    return cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", required=True, choices=["lego", "chair"])
    ap.add_argument("--linelets", default=None,
                    help="default out/linelets_<scene>_cap_f1.00.npz (has keep_tuned)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    from src import common, render, view_split, linelet, visibility     # noqa: E402
    from run_m1b import raster_segments                                 # EVAL harness
    from tune_lib import Harness                                        # EVAL ONLY (mesh)

    lp = args.linelets or os.path.join(OUT, f"linelets_{args.scene}_cap_f1.00.npz")
    z = np.load(lp)
    assert "keep_tuned" in z.files, (
        f"{lp} lacks keep_tuned — regenerate with run_m1b.py --dump_tuned")
    P1, t1 = z["p"], z["t"]
    keep_t, l_mod_t = z["keep_tuned"], z["l_mod_tuned"]

    h = Harness(args.scene, views=tuple(view_split.TEST))
    g = common.load_gaussians(args.scene)
    kmask = render.defloat_mask(g["mu"], g["opacity"])
    X_pool = g["mu"][kmask]                       # PRE-SCORING candidate pool
    X_raw = g["mu"]                               # RAW UNPRUNED gaussian centres
    assert len(X_pool) == len(P1), (len(X_pool), len(P1))
    print(f"[cap] {args.scene}: pool {len(X_pool)}  raw {len(X_raw)} "
          f"(floaters removed: {len(X_raw) - len(X_pool)})  "
          f"kept at tuned+len: {int(keep_t.sum())}", flush=True)

    rng = np.random.default_rng(0)
    null_acc = {"matched_d_pool": [], "rand_d_pool": [], "rand_d_raw": []}
    per_view, rec_check = [], []
    agg = {k: 0 for k in ("A", "B0", "B1", "B2")}
    d_pool_all, d_raw_all = [], []
    agg_vis = {k: 0 for k in ("A", "B0", "B1", "B2")}
    n_miss_tot = n_crease_tot = 0

    for v in h.views:
        cam = h.cams[v]
        cu, cv_, _ = h.crease[v]
        mask, _ = raster_segments(h, v, P1, t1, l_mod_t, keep=keep_t)
        sdt = (cv2.distanceTransform((~mask).astype(np.uint8), cv2.DIST_L2, 5)
               if mask.any() else np.full(mask.shape, 1e9, np.float32))
        d_seg = sdt[cv_, cu]
        rec_check.append(float((d_seg <= TAU).mean()))
        miss = d_seg > TAU
        n_crease_tot += len(cu)
        n_miss_tot += int(miss.sum())
        if not miss.any():
            per_view.append({"view": int(v), "n_crease": int(len(cu)), "n_miss": 0})
            continue

        q = np.stack([cu[miss], cv_[miss]], 1).astype(np.float64)   # (u, v) of missed loci
        uv_pool = project_uv(X_pool, cam)
        uv_raw = project_uv(X_raw, cam)
        d_pool = cKDTree(uv_pool).query(q, k=1)[0] if len(uv_pool) else np.full(len(q), 1e9)
        d_raw = cKDTree(uv_raw).query(q, k=1)[0] if len(uv_raw) else np.full(len(q), 1e9)
        d_pool_all.append(d_pool)
        d_raw_all.append(d_raw)

        A = d_pool <= TAU
        B0 = (~A) & (d_raw <= TAU)
        B1 = (~A) & (d_raw > TAU) & (d_raw <= B1_HI)
        B2 = (~A) & (d_raw > B1_HI)
        for k, m in (("A", A), ("B0", B0), ("B1", B1), ("B2", B2)):
            agg[k] += int(m.sum())

        # sensitivity: restrict both reference sets to gaussians VISIBLE in this view, so an
        # occluded back-surface gaussian cannot "cover" a front-facing crease
        vp, _, _ = visibility.visible_mask(X_pool, cam, h.gbufs[v]["depth"])
        uv_pv = project_uv(X_pool[vp], cam)
        vr, _, _ = visibility.visible_mask(X_raw, cam, h.gbufs[v]["depth"])
        uv_rv = project_uv(X_raw[vr], cam)
        dpv = cKDTree(uv_pv).query(q, k=1)[0] if len(uv_pv) else np.full(len(q), 1e9)
        drv = cKDTree(uv_rv).query(q, k=1)[0] if len(uv_rv) else np.full(len(q), 1e9)
        Av = dpv <= TAU
        agg_vis["A"] += int(Av.sum())
        agg_vis["B0"] += int(((~Av) & (drv <= TAU)).sum())
        agg_vis["B1"] += int(((~Av) & (drv > TAU) & (drv <= B1_HI)).sum())
        agg_vis["B2"] += int(((~Av) & (drv > B1_HI)).sum())

        # ---- NULL CALIBRATION.  "A candidate existed within 1.5 px" is only meaningful if
        # that is NOT true of an arbitrary pixel.  The pool projects ~100k centres into a
        # 640k-pixel frame, so the nearest-centre distance may be small everywhere.  Measure
        # the same d_pool/d_raw at (i) the MATCHED crease pixels and (ii) uniformly random
        # foreground pixels, so the discriminative power of the A test can be read off.
        qm = np.stack([cu[~miss], cv_[~miss]], 1).astype(np.float64)
        d_pool_matched = (cKDTree(uv_pool).query(qm, k=1)[0]
                          if (len(uv_pool) and len(qm)) else np.zeros(0))
        fg = np.argwhere(h.gbufs[v]["depth"].cpu().numpy() < 1e8)      # (row, col) = (v, u)
        if len(fg):
            sel = fg[rng.choice(len(fg), size=min(len(fg), 20000), replace=False)]
            qr = np.stack([sel[:, 1], sel[:, 0]], 1).astype(np.float64)
            d_pool_rand = cKDTree(uv_pool).query(qr, k=1)[0] if len(uv_pool) else np.zeros(0)
            d_raw_rand = cKDTree(uv_raw).query(qr, k=1)[0] if len(uv_raw) else np.zeros(0)
        else:
            d_pool_rand = d_raw_rand = np.zeros(0)
        null_acc["matched_d_pool"].append(d_pool_matched)
        null_acc["rand_d_pool"].append(d_pool_rand)
        null_acc["rand_d_raw"].append(d_raw_rand)

        # pixel-quantised cross-check
        dtp = dt_of_points(uv_pool, cam.H, cam.W)[cv_[miss], cu[miss]]
        dtr = dt_of_points(uv_raw, cam.H, cam.W)[cv_[miss], cu[miss]]
        per_view.append({
            "view": int(v), "n_crease": int(len(cu)), "n_miss": int(miss.sum()),
            "recall_at_1.5": rec_check[-1],
            "A": int(A.sum()), "B0": int(B0.sum()), "B1": int(B1.sum()), "B2": int(B2.sum()),
            "d_pool_median": float(np.median(d_pool)), "d_pool_p90": float(np.percentile(d_pool, 90)),
            "d_raw_median": float(np.median(d_raw)), "d_raw_p90": float(np.percentile(d_raw, 90)),
            "dtq_A": int((dtp <= TAU).sum()),
            "dtq_B2": int(((dtp > TAU) & (dtr > B1_HI)).sum()),
        })
        print(f"  v{v:3d}: crease {len(cu):7d}  miss {int(miss.sum()):7d}  "
              f"A {int(A.sum()):6d}  B0 {int(B0.sum()):5d}  B1 {int(B1.sum()):5d}  "
              f"B2 {int(B2.sum()):6d}   d_pool med {np.median(d_pool):5.2f}  "
              f"d_raw med {np.median(d_raw):5.2f}", flush=True)

    d_pool_all = np.concatenate(d_pool_all) if d_pool_all else np.zeros(0)
    d_raw_all = np.concatenate(d_raw_all) if d_raw_all else np.zeros(0)
    tot = sum(agg.values())

    def rho(a):
        den = a["B1"] + a["B2"]
        den2 = a["B0"] + a["B1"] + a["B2"]
        return (a["B2"] / den if den else float("nan"),
                a["B2"] / den2 if den2 else float("nan"))

    r_spec, r_b0 = rho(agg)
    rv_spec, rv_b0 = rho(agg_vis)
    res = {
        "scene": args.scene, "stage": "AFTER   pull+prune[tuned+len]", "f": 1.00,
        "split": "test", "views": [int(v) for v in h.views], "tau": TAU, "B1_hi": B1_HI,
        "linelets": os.path.basename(lp),
        "n_pool": int(len(X_pool)), "n_raw": int(len(X_raw)),
        "n_kept_tuned": int(keep_t.sum()),
        "recall_at_1.5_recomputed": float(np.mean(rec_check)),
        "n_crease_total": n_crease_tot, "n_miss_total": n_miss_tot,
        "miss_fraction": n_miss_tot / max(n_crease_tot, 1),
        "counts": agg, "counts_visible_only": agg_vis,
        "fractions_of_missset": {k: agg[k] / max(tot, 1) for k in agg},
        "rho_B2_spec_literal": r_spec,
        "rho_B2_with_B0_folded_into_B1": r_b0,
        "rho_B2_visible_only_spec_literal": rv_spec,
        "rho_B2_visible_only_with_B0": rv_b0,
        "d_pool": {"median": float(np.median(d_pool_all)),
                   "p90": float(np.percentile(d_pool_all, 90)),
                   "mean": float(d_pool_all.mean())},
        "d_raw": {"median": float(np.median(d_raw_all)),
                  "p90": float(np.percentile(d_raw_all, 90)),
                  "mean": float(d_raw_all.mean())},
        "per_view": per_view,
    }
    NL = {k: (np.concatenate(v) if v and sum(len(x) for x in v) else np.zeros(0))
          for k, v in null_acc.items()}
    res["null_calibration"] = {
        "note": ("Fraction of loci with d_pool <= 1.5 -- i.e. how often the Class-A test is "
                 "satisfied -- evaluated on MISSED crease px, on MATCHED crease px, and on "
                 "uniformly random FOREGROUND px. If the random rate is close to the missed "
                 "rate, the A test is near-vacuous and the informative signal is B1/B2."),
        "frac_d_pool_le_1.5_missed": float((d_pool_all <= TAU).mean()) if len(d_pool_all) else None,
        "frac_d_pool_le_1.5_matched": float((NL["matched_d_pool"] <= TAU).mean()) if len(NL["matched_d_pool"]) else None,
        "frac_d_pool_le_1.5_random_fg": float((NL["rand_d_pool"] <= TAU).mean()) if len(NL["rand_d_pool"]) else None,
        "frac_d_raw_gt_3.0_random_fg": float((NL["rand_d_raw"] > B1_HI).mean()) if len(NL["rand_d_raw"]) else None,
        "d_pool_median_missed": float(np.median(d_pool_all)) if len(d_pool_all) else None,
        "d_pool_median_matched": float(np.median(NL["matched_d_pool"])) if len(NL["matched_d_pool"]) else None,
        "d_pool_median_random_fg": float(np.median(NL["rand_d_pool"])) if len(NL["rand_d_pool"]) else None,
        "n_random_fg_sampled": int(len(NL["rand_d_pool"])),
    }
    jp = args.out or os.path.join(OUT, f"cap_miss_attribution_{args.scene}.json")
    json.dump(res, open(jp, "w"), indent=2)

    print("\n" + "=" * 92)
    print(f"CAP — {args.scene.upper()}, held-out TEST, stage tuned+len, f=1.00")
    print("=" * 92)
    print(f"  recall@1.5 recomputed here : {res['recall_at_1.5_recomputed']:.4f}")
    print(f"  GT crease px {n_crease_tot}   MISSED {n_miss_tot} "
          f"({res['miss_fraction']:.1%} of the crease set)")
    for k in ("A", "B0", "B1", "B2"):
        print(f"    {k:>3}: {agg[k]:8d}  {agg[k]/max(tot,1):6.2%}")
    print(f"  d_pool  median {res['d_pool']['median']:.2f}  p90 {res['d_pool']['p90']:.2f}")
    print(f"  d_raw   median {res['d_raw']['median']:.2f}  p90 {res['d_raw']['p90']:.2f}")
    print(f"  rho_B2  spec-literal (B0 excluded)   = {r_spec:.4f}")
    print(f"  rho_B2  with B0 folded into B1       = {r_b0:.4f}")
    print(f"  rho_B2  visible-only, spec-literal   = {rv_spec:.4f}")
    nc = res["null_calibration"]
    print(f"  NULL CALIBRATION  frac(d_pool<=1.5):  missed {nc['frac_d_pool_le_1.5_missed']:.3f}"
          f"   matched {nc['frac_d_pool_le_1.5_matched']:.3f}"
          f"   random-fg {nc['frac_d_pool_le_1.5_random_fg']:.3f}")
    print(f"                    median d_pool:      missed {nc['d_pool_median_missed']:.2f}"
          f"   matched {nc['d_pool_median_matched']:.2f}"
          f"   random-fg {nc['d_pool_median_random_fg']:.2f}")
    print(f"                    frac(d_raw>3.0) on random fg: {nc['frac_d_raw_gt_3.0_random_fg']:.3f}")
    print(f"\nwrote {jp}")


if __name__ == "__main__":
    main()
