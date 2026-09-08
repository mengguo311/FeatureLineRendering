"""tier1/scripts/geoline_step1.py — GEOLINE STEP 1.

Does 3-D surface geometry separate TRUE CREASES from OFF-CREASE loci on a CLEAN,
TEXTURELESS GEOMETRIC SOLID, where it demonstrably could NOT on lego?

*** EVAL / DIAGNOSTIC.  Reads the GT mesh (tune_lib.Harness -> mesh_oracle) for LABELS
    ONLY.  Defines no method, adds no method-path file, modifies nothing committed. ***

THE HYPOTHESIS UNDER TEST (user's, stated adversarially)
    DIAG-2DGS measured that the dihedral gate is BELOW CHANCE on lego (surfel3d AUC 0.4110,
    median gap -17.33 deg; ribbon3dgs_vanilla AUC 0.3875, gap -5.94) and diagnosed the cause
    as a FALSE PREMISE rather than a blurred reconstruction: under 1% of lego's surface is
    flat at the ball scale, so "paint is flat, creases bend" has no flat class to stand on,
    and the GT-MESH arm failed too (mesh3d 0.3964, spreadmesh 0.4675 with a 0.32 deg class
    gap).  On a textureless solid with exactly-planar faces that premise is restored BY
    CONSTRUCTION.  If K_geom really revives on clean solids, the SAME estimator with the SAME
    frozen constants must clear the SAME bars lego failed.

WHAT IS REUSED VERBATIM
    The estimators are IMPORTED from scripts/diag2dgs.py, not reimplemented:
    diag2dgs.surfel3d_dihedral (arm 1), diag2dgs.ribbon_dihedral (arms 2/3),
    diag2dgs.auc, diag2dgs.visible_mask_cloud.  Frozen constants rho=4.0, xi=0.25, n_min=5
    are the lego headline values (out/diag2dgs_lego_test.json); NOTHING is retuned per scene.
    The lego headline was computed WITHOUT --visible_only (that key is absent from its json),
    so the primary run here is also without it and the filtered variant is a sensitivity.

TWO DECLARED SUBSTITUTIONS (neither touches the estimator; both are forced by the asset)
  1. CLOUD.  diag2dgs arm (1) feeds the estimator a 2DGS SURFEL cloud.  No 2DGS model exists
     for any cadpart scene (out/2dgs_* covers chair and lego only) and training one is out of
     scope for this step, so the 3-D arm is fed the VANILLA 3DGS de-floatered cloud: centres
     h.X, UNORIENTED normals h.N (shortest covariance axis, exactly what common.load_gaussians
     returns), opacity weights h.opa.  The arm is therefore reported as
     `surfel3d_vanilla3dgs`, NOT as `surfel3d`, and it is NOT comparable to lego's 0.4110 on
     the reconstruction axis.  It IS comparable to lego's `ribbon3dgs_vanilla` in substrate.
  2. DISTRACTOR LABEL.  lego's negative class is "d > 3.0 px AND TEED-high", where the TEED
     condition exists to make the negatives HARD (printed decals).  cadpart has one uniform
     albedo and zero decals by construction, so that class may not exist.  Both are reported:
       offcrease      d > 3.0 px                       (PRIMARY, the user's phrasing)
       offcrease_dexhi  d > 3.0 px AND DexiNed prob > 0.5 in >= half the visible views
                        (the lego rule with the repo's cadpart DexiNed cache standing in for
                         the TEED cache, which was never built for this scene)
     The gate is read on BOTH.  If they disagree the run is inconclusive and says so.

FROZEN GO/NO-GO (pre-registered by the user before any number was looked at)
    GO   iff  AUC >= 0.80  AND  median dihedral gap >= +25.0 deg
    NO-GO otherwise.  These are the identical bars lego failed.
"""
import argparse
import json
import os
import sys

import numpy as np
from scipy.spatial import cKDTree

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))

from src import common, visibility, view_split                      # noqa: E402
import diag2dgs                                                     # noqa: E402  VERBATIM

OUT = os.path.join(TIER1, "out")
BAR_AUC = 0.80
BAR_GAP = 25.0


def dexined_frac(P, h, views, cache, thr=0.5):
    """Fraction of the split's visible views in which the DexiNed probability at the
    linelet's projected centre exceeds `thr`.  The analogue of lego's E_frac_0p5."""
    hi = np.zeros(len(P)); nv = np.zeros(len(P))
    for v in views:
        f = os.path.join(cache, f"v{v:03d}.npz")
        if not os.path.exists(f):
            continue
        pr = np.load(f)["native"].astype(np.float32)
        vis, uv, _ = visibility.visible_mask(P, h.cams[v], h.gbufs[v]["depth"])
        idx = np.where(vis)[0]
        if not len(idx):
            continue
        u = np.clip(np.round(uv[idx, 0]).astype(int), 0, pr.shape[1] - 1)
        w = np.clip(np.round(uv[idx, 1]).astype(int), 0, pr.shape[0] - 1)
        hi[idx] += (pr[w, u] > thr); nv[idx] += 1
    return hi / np.maximum(nv, 1), nv


def score(th, ok, pos, neg, name):
    c, d = pos & ok, neg & ok
    if c.sum() < 10 or d.sum() < 10:
        return {"arm": name, "n_crease": int(c.sum()), "n_neg": int(d.sum()),
                "AUC": float("nan"), "median_gap": float("nan"), "gate": "UNDEFINED"}
    lab = np.concatenate([np.ones(int(c.sum()), bool), np.zeros(int(d.sum()), bool)])
    a = diag2dgs.auc(np.concatenate([th[c], th[d]]), lab)
    mc, md = float(np.median(th[c])), float(np.median(th[d]))
    return {"arm": name, "n_crease": int(c.sum()), "n_neg": int(d.sum()),
            "measurable_frac": float(ok.mean()), "AUC": float(a),
            "median_crease": mc, "median_neg": md, "median_gap": mc - md,
            "p05_crease": float(np.percentile(th[c], 5)),
            "p95_neg": float(np.percentile(th[d], 95)),
            "gate": "GO" if (a >= BAR_AUC and mc - md >= BAR_GAP) else "NO-GO"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="cadpartA")
    ap.add_argument("--split", default="test", choices=["test", "val"])
    ap.add_argument("--rho", type=float, default=4.0)      # lego-frozen
    ap.add_argument("--xi", type=float, default=0.25)      # lego-frozen
    ap.add_argument("--n_min", type=int, default=5)        # lego-frozen
    ap.add_argument("--linelets", default=None)
    ap.add_argument("--dexined", default=os.path.join(OUT, "dexined_edges_cadpart"))
    ap.add_argument("--sweep", action="store_true",
                    help="DIAGNOSTIC ONLY: score a rho grid beside the frozen value, as "
                         "diag2dgs does, so it is visible whether the verdict depends on "
                         "the radius. NEVER read as the gate.")
    ap.add_argument("--rho_list", type=float, nargs="*",
                    default=[0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0])
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    from tune_lib import Harness                                    # EVAL ONLY (mesh)
    views = {"val": view_split.VAL, "test": view_split.TEST}[args.split]
    h = Harness(args.scene, views=tuple(views))

    lp = args.linelets or os.path.join(OUT, f"linelets_{args.scene}_gated_test.npz")
    z = np.load(lp)
    P, T, L, KEEP = z["p"], z["t"], z["l"], z["keep"]
    print(f"[{args.scene}] {len(P)} linelets from {os.path.basename(lp)} "
          f"({int(KEEP.sum())} survive the prune), split={args.split} ({len(views)} views)",
          flush=True)

    res = {"scene": args.scene, "split": args.split, "views": list(views),
           "linelet_file": os.path.basename(lp), "n_linelets": int(len(P)),
           "n_keep": int(KEEP.sum()),
           "frozen": {"rho": args.rho, "xi": args.xi, "n_min": args.n_min,
                      "source": "out/diag2dgs_lego_test.json headline (no --visible_only)"},
           "bars": {"AUC": BAR_AUC, "median_gap_deg": BAR_GAP,
                    "lego_measured": {"surfel3d": {"AUC": 0.4110, "gap": -17.33},
                                      "ribbon3dgs_vanilla": {"AUC": 0.3875, "gap": -5.94}}},
           "mesh_eval_only": ("GT mesh read via tune_lib.Harness -> src.mesh_oracle for "
                              "LABELS ONLY; no mesh quantity enters any signal."),
           "linelet_median_half_length": float(np.median(L)),
           "gaussian_cloud": {"n_defloatered": int(len(h.X))}}

    # ---- labels (mesh, EVAL-ONLY) ------------------------------------------------------
    dists = [[] for _ in range(len(P))]
    nvis = np.zeros(len(P), np.int64)
    for v in views:
        vis, uv, _ = visibility.visible_mask(P, h.cams[v], h.gbufs[v]["depth"])
        cu, cv_, cdt = h.crease[v]
        u = np.clip(np.round(uv[:, 0]).astype(int), 0, cdt.shape[1] - 1)
        w = np.clip(np.round(uv[:, 1]).astype(int), 0, cdt.shape[0] - 1)
        d = cdt[w, u]
        nvis += vis
        for i in np.where(vis)[0]:
            dists[i].append(d[i])
    dmed = np.array([np.median(x) if x else np.inf for x in dists])
    seen = nvis > 0
    dexfrac, _ = dexined_frac(P, h, views, args.dexined)
    crease = seen & (dmed <= 1.5)
    offcrease = seen & (dmed > 3.0)
    offcrease_dexhi = offcrease & (dexfrac >= 0.5)
    res["labels"] = {
        "rule_pos": "TrueCrease: median over visible split views of GT-crease distance <= 1.5 px",
        "rule_neg_primary": "offcrease: median > 3.0 px",
        "rule_neg_legorule": ("offcrease_dexhi: median > 3.0 px AND DexiNed native prob > 0.5 "
                              "in >= half the visible views (TEED cache absent for cadpart)"),
        "n_seen": int(seen.sum()), "n_crease": int(crease.sum()),
        "n_offcrease": int(offcrease.sum()), "n_offcrease_dexhi": int(offcrease_dexhi.sum()),
        "n_dex_high": int((seen & (dexfrac >= 0.5)).sum())}
    print(f"  [labels] seen {int(seen.sum())} | TrueCrease {int(crease.sum())} | "
          f"offcrease {int(offcrease.sum())} | offcrease&DexiNed-hi "
          f"{int(offcrease_dexhi.sum())}", flush=True)

    # ---- signals -----------------------------------------------------------------------
    cloud = {"mu": h.X, "n": h.N, "w": h.opa}
    tree = cKDTree(cloud["mu"])
    sig = {}
    th, sp, ok = diag2dgs.surfel3d_dihedral(P, T, L, cloud, rho=args.rho, xi=args.xi,
                                            n_min=args.n_min, tree=tree,
                                            name="surfel3d_vanilla3dgs")
    sig["surfel3d_vanilla3dgs"] = (th, ok)
    sig["spread3dgs"] = (sp, ok)
    if args.sweep:
        for r in args.rho_list:
            if r == args.rho:
                continue
            t2, s2, o2 = diag2dgs.surfel3d_dihedral(P, T, L, cloud, rho=r, xi=args.xi,
                                                    n_min=args.n_min, tree=tree,
                                                    name=f"DIAG_surfel3d_rho{r:g}")
            sig[f"DIAG_surfel3d_rho{r:g}"] = (t2, o2)
            sig[f"DIAG_spread3dgs_rho{r:g}"] = (s2, o2)

    import torch
    n1, fg = {}, {}
    for v in views:
        gb = h.gbufs[v]
        n1[v] = gb["normal"].detach().cpu().numpy().astype(np.float32)
        fg[v] = (gb["alpha"].detach().cpu().numpy() > 0.5)
    thr, nok = diag2dgs.ribbon_dihedral(P, T, h, views, n1, fg)
    sig["ribbon3dgs_vanilla"] = (thr, nok > 0)
    torch.cuda.empty_cache()

    # sensitivity: front-surface-only cloud (lego's --visible_only, OFF in the headline)
    cams_all, _ = common.load_cameras(args.scene)
    tv = list(view_split.TRAIN)
    dcache = {}

    def depv(v):
        if v not in dcache:
            from src import render
            gb = render.render_gbuffer(h.g, h.keep, cams_all[v])
            dcache[v] = gb["depth"].detach().cpu().numpy()
            del gb
        return dcache[v]

    vmask = diag2dgs.visible_mask_cloud(h.X, cams_all, tv[::4], depv)
    del dcache
    torch.cuda.empty_cache()
    print(f"  [visible_only] gaussians {len(h.X)} -> {int(vmask.sum())} front-surface in "
          f">=1 of {len(tv[::4])} TRAIN views", flush=True)
    cloud_v = {"mu": h.X[vmask], "n": h.N[vmask], "w": h.opa[vmask]}
    thv, spv, okv = diag2dgs.surfel3d_dihedral(P, T, L, cloud_v, rho=args.rho, xi=args.xi,
                                               n_min=args.n_min, name="surfel3d_visonly")
    sig["surfel3d_vanilla3dgs_visibleonly"] = (thv, okv)

    common_ok = sig["surfel3d_vanilla3dgs"][1] & sig["ribbon3dgs_vanilla"][1]
    res["n_common_measurable"] = int(common_ok.sum())

    rows = {}
    for k, (s, okm) in sig.items():
        for negname, neg in (("offcrease", offcrease), ("offcrease_dexhi", offcrease_dexhi)):
            for scope, m in (("own", okm), ("common", common_ok & okm)):
                rows[f"{k}|{negname}|{scope}"] = score(s, m, crease, neg, k)
    # prune-survivor sensitivity on the gated arms only
    for k in ("surfel3d_vanilla3dgs", "ribbon3dgs_vanilla"):
        s, okm = sig[k]
        rows[f"{k}|offcrease|keep_only"] = score(s, okm & KEEP, crease, offcrease, k)
    res["signals"] = rows
    res["dexined_prevalence"] = {"frac_seen_dexhi": float((dexfrac[seen] >= 0.5).mean())}

    tag = args.tag or f"_{args.split}"
    p = os.path.join(OUT, f"geoline_step1_{args.scene}{tag}.json")
    json.dump(res, open(p, "w"), indent=1)
    print(f"\n  GATE (AUC>={BAR_AUC}, gap>=+{BAR_GAP} deg)")
    for k in ["surfel3d_vanilla3dgs|offcrease|own", "surfel3d_vanilla3dgs|offcrease_dexhi|own",
              "ribbon3dgs_vanilla|offcrease|own", "ribbon3dgs_vanilla|offcrease_dexhi|own"]:
        r = rows[k]
        print(f"    {k:48s} AUC {r['AUC']:.4f}  gap {r['median_gap']:+8.2f}  {r['gate']}")
    print(f"  -> {p}", flush=True)


if __name__ == "__main__":
    main()
