"""DexiNed-primary PHASE 1b — multi-view epipolar triangulation on CHAIR + the ceiling test.

*** EVAL / ANALYSIS SCRIPT.  Reads the GT mesh (via scripts.dexprimary_p0.gt_labels) to build
    LABELS and to SCORE only.  The METHOD PATH is src/tri_edges.py (DexiNed cache + multi-view
    geometry + 3DGS depth as init/occlusion prior) and imports no mesh. ***

URS-LEGAL: every candidate is triangulated from TRAIN views only; the 10 TEST views are used
for scoring and are never lifted from (Phase 0 ARM C showed own-view lifting is circular).

CLOUDS SCORED, all on the identical measurement:
  tri_sup1 / tri_sup2 / tri_sup3   triangulated, >=1 / >=2 / >=3 supporting NEIGHBOUR views
                                   (= 2-view / K>=3-view bundle / stricter), after the
                                   free-space+occlusion cull and a residual cull.
  tri_sup2_nocull                  the same without the free-space cull (isolates its effect)
  p0_singleview                    Phase 0's winning arm: the SAME DexiNed edge pixels from the
                                   SAME reference views, placed by 3DGS median depth. The
                                   head-to-head this phase exists to run.
  ctrl_tri_randpix                 the identical triangulator seeded from RANDOM FOREGROUND
                                   pixels instead of DexiNed edges -> does the DETECTOR matter,
                                   or only the machinery?
  ctrl_randfg                      random foreground points at matched count, median depth
                                   -> chance on the same surface (Phase 0's control)
  gauss_pool                       the visible gaussian centres -> calibrates every radius
"""
import os
import sys
import json
import time
import argparse

import numpy as np
import torch
from scipy.spatial import cKDTree

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
OUT = os.path.join(TIER1, "out")

from src import common, render, view_split, visibility, tri_edges as T
from dexprimary_p0 import gt_labels, lift_view, ctrl_random_fg, voxel_budget

TAUS = (1.5, 2.5)


def score_cloud(name, P, cams, views, gt, covered, miss2d, miss3d_15, seen_idx, crease_pts,
                tree_gt3, depth_t, depth_np, radii, delta=1.5):
    """The Phase-0 measurement, applied to an arbitrary 3D cloud. All views are TEST views the
    cloud was never lifted from, so there is no own-view degeneracy here."""
    arm = {"n_total": int(len(P))}
    if len(P) == 0:
        return arm
    hit_all = n_all = cov_num = cov_den = 0
    hm = {t: 0 for t in TAUS}
    nm = {t: 0 for t in TAUS}
    for v in views:
        cam = cams[v]
        idx, uvq = gt[v]
        vis, uvl_all, _ = visibility.visible_mask(P, cam, depth_t[v])
        uvl = uvl_all[vis]
        inb = ((uvl[:, 0] >= -2) & (uvl[:, 0] < cam.W + 2) &
               (uvl[:, 1] >= -2) & (uvl[:, 1] < cam.H + 2))
        uvl = uvl[inb]
        n_all += len(idx)
        for t in TAUS:
            nm[t] += int(miss2d[t][v].sum())
        fgm = np.isfinite(depth_np[v])
        cov_den += int(fgm.sum())
        if len(uvl) == 0:
            continue
        tr = cKDTree(uvl)
        ok = tr.query(uvq, k=1)[0] <= delta
        hit_all += int(ok.sum())
        for t in TAUS:
            hm[t] += int((ok & miss2d[t][v]).sum())
        fv, fu = np.nonzero(fgm)
        q = np.stack([fu.astype(np.float64), fv.astype(np.float64)], 1)
        cov_num += int((tr.query(q, k=1)[0] <= delta).sum())
    arm["recall_2D"] = hit_all / max(n_all, 1)
    for t in TAUS:
        arm[f"R_miss_2D_tau{t}"] = hm[t] / max(nm[t], 1)
    arm["R_miss_2D"] = arm["R_miss_2D_tau1.5"]
    arm["cover_fg"] = cov_num / max(cov_den, 1)
    arm["lift"] = arm["R_miss_2D"] / max(arm["cover_fg"], 1e-9)

    tree3 = cKDTree(P)
    d3 = tree3.query(crease_pts[seen_idx], k=1)[0]
    dprec = tree_gt3.query(P, k=1)[0]
    ml = miss3d_15[seen_idx]
    for rn, rad in radii.items():
        h = d3 <= rad
        arm[f"recall_3D_{rn}"] = float(h.mean())
        arm[f"R_miss_3D_{rn}"] = float(h[ml].mean())
        arm[f"precision_3D_{rn}"] = float((dprec <= rad).mean())
    arm["chamfer_median"] = float(np.median(d3))
    return arm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="chair")
    ap.add_argument("--n_ref", type=int, default=20)
    ap.add_argument("--K", type=int, default=6)
    ap.add_argument("--rho", type=float, default=0.2)
    ap.add_argument("--tau", type=float, default=1.5)
    ap.add_argument("--thr", type=float, default=0.5)
    ap.add_argument("--key", default="native")
    ap.add_argument("--halfpix", type=float, default=0.5)
    ap.add_argument("--resid_max", type=float, default=1.0)
    ap.add_argument("--rel_eps", type=float, default=0.02)
    ap.add_argument("--budget", type=int, default=0)
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    scene = args.scene
    views = view_split.TEST
    dex = os.path.join(OUT, f"dexined_edges_{scene}")
    TR = view_split.TRAIN
    refs = [TR[i] for i in np.linspace(0, len(TR) - 1, args.n_ref).astype(int)]
    print(f"[p1b] {scene}  score=TEST{views}\n[p1b] refs(TRAIN,{len(refs)})={refs}\n"
          f"[p1b] K={args.K} rho={args.rho} tau={args.tau} thr={args.thr} key={args.key} "
          f"halfpix={args.halfpix} resid_max={args.resid_max} budget={args.budget}", flush=True)

    # ---------------------------------------------------------------- METHOD (mesh-free)
    t0 = time.time()
    tri, tstats = T.build(scene, refs, TR, dex, thr=args.thr, key=args.key, K=args.K,
                          rho=args.rho, tau=args.tau, halfpix=args.halfpix,
                          rel_eps=args.rel_eps)
    print(f"[p1b] triangulation {time.time()-t0:.1f}s  {tstats}", flush=True)

    # control: identical triangulator seeded from RANDOM FOREGROUND pixels
    cams, _ = common.load_cameras(scene)
    g = common.load_gaussians(scene)
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    rng = np.random.default_rng(0)
    Pr, Sr = [], []
    dts_r = {}
    for r in refs:
        nbrs = T.neighbor_views(cams, r, args.K, TR)
        for n in nbrs + [r]:
            if n not in dts_r:
                _, dt = T.edge_dt(dex, n, args.thr, args.key)
                dts_r[n] = torch.tensor(dt, dtype=torch.float32, device="cuda")
        gb = render.render_gbuffer(g, keep_g, cams[r], with_median_depth=True)
        a = gb["alpha"].cpu().numpy()
        dmed = gb["depth_median"].cpu().numpy().astype(np.float64)
        n_edge = int((tri["ref"] == r).sum())
        fg = np.argwhere((a >= 0.5) & np.isfinite(dmed))
        sel = fg[rng.choice(len(fg), size=min(n_edge, len(fg)), replace=False)]
        uv = np.stack([sel[:, 1], sel[:, 0]], 1).astype(np.float64)
        rr = T.triangulate_view(cams, r, nbrs, dts_r, dmed[sel[:, 0], sel[:, 1]], uv,
                                halfpix=args.halfpix, rho=args.rho, tau=args.tau)
        Pr.append(rr["P"]); Sr.append(rr["support"])
        del gb
        torch.cuda.empty_cache()
    P_randtri = np.concatenate(Pr); S_randtri = np.concatenate(Sr)
    for k in list(dts_r):
        del dts_r[k]
    torch.cuda.empty_cache()

    # Phase-0 single-view arm from the SAME reference views + matched-count chance cloud
    P_sv, P_rfg = [], []
    for r in refs:
        gb = render.render_gbuffer(g, keep_g, cams[r], with_median_depth=True)
        L = lift_view(dex, r, cams[r], gb, args.thr, args.key, arms=("median",),
                      halfpix=args.halfpix)
        P_sv.append(L["median"][0])
        pr, _ = ctrl_random_fg(gb, cams[r], len(L["median"][0]), rng)
        P_rfg.append(pr)
        del gb
        torch.cuda.empty_cache()
    P_sv = np.concatenate(P_sv); P_rfg = np.concatenate(P_rfg)

    # ---------------------------------------------------------------- EVAL (mesh labels)
    crease_pts, gt, bbox_diag = gt_labels(scene, views)
    X_pool = g["mu"][keep_g]
    covered, miss2d, depth_np, depth_t, gp = {t: {} for t in TAUS}, {t: {} for t in TAUS}, {}, {}, {}
    for v in views:
        gb = render.render_gbuffer(g, keep_g, cams[v], with_median_depth=True)
        depth_np[v] = gb["depth"].cpu().numpy()
        depth_t[v] = gb["depth"].clone()
        idx, uvq = gt[v]
        vis, uvg, _ = visibility.visible_mask(X_pool, cams[v], gb["depth"])
        d_pool = cKDTree(uvg[vis]).query(uvq, k=1)[0]
        for t in TAUS:
            covered[t][v] = d_pool <= t
            miss2d[t][v] = ~covered[t][v]
        gp[v] = X_pool[vis]
        del gb
        torch.cuda.empty_cache()
    seen = np.zeros(len(crease_pts), bool); cov_any = np.zeros(len(crease_pts), bool)
    for v in views:
        idx, _ = gt[v]
        seen[idx] = True
        cov_any[idx] |= covered[1.5][v]
    miss3d_15 = seen & ~cov_any
    seen_idx = np.where(seen)[0]
    zmed = float(np.median(np.concatenate(
        [((cams[v].w2c[:3, :3] @ crease_pts[gt[v][0]].T).T + cams[v].w2c[:3, 3])[:, 2]
         for v in views])))
    radii = {"px1.5_equiv": 1.5 * zmed / cams[views[0]].f,
             "chamfer_0.5pct_bbox": 0.005 * bbox_diag,
             "chamfer_1.5pct_bbox": 0.015 * bbox_diag}
    tree_gt3 = cKDTree(crease_pts)
    n_gt = sum(len(gt[v][0]) for v in views)
    n_miss = sum(int(miss2d[1.5][v].sum()) for v in views)
    print(f"[p1b] miss-set: {n_miss}/{n_gt} = {n_miss/n_gt:.4f}   "
          f"pool cover {1-n_miss/n_gt:.4f}   radii "
          + "  ".join(f"{k}={v:.5f}" for k, v in radii.items()), flush=True)

    sk = tri["surface_keep"]
    rr_ok = tri["resid"] <= args.resid_max
    clouds = {
        "tri_sup1": tri["P"][(tri["support"] >= 1) & sk & rr_ok],
        "tri_sup2": tri["P"][(tri["support"] >= 2) & sk & rr_ok],
        "tri_sup3": tri["P"][(tri["support"] >= 3) & sk & rr_ok],
        "tri_sup2_nocull": tri["P"][(tri["support"] >= 2) & rr_ok],
        "p0_singleview": P_sv,
        "ctrl_tri_randpix": P_randtri[(S_randtri >= 2)],
        "ctrl_randfg": P_rfg,
        "gauss_pool": np.concatenate([gp[v] for v in views]),
    }
    if args.budget:
        clouds = {k: (v[voxel_budget(v, args.budget)] if len(v) else v)
                  for k, v in clouds.items()}

    res = {"scene": scene, "phase": "1b", "views": [int(v) for v in views],
           "refs": [int(r) for r in refs], "args": vars(args),
           "tri_stats": tstats, "bbox_diag": bbox_diag, "radii": radii,
           "n_gt_pairs": n_gt, "n_miss": n_miss, "miss_fraction": n_miss / n_gt,
           "pool_cover_2D": 1 - n_miss / n_gt,
           "n_miss3d": int(miss3d_15.sum()), "n_seen3d": int(seen.sum()),
           "clouds": {}}
    print(f"\n{'cloud':18s} {'n':>8s} | {'rec2D':>7s} {'Rm2D':>7s} {'covfg':>6s} {'lift':>5s}"
          f" | {'rec3D':>7s} {'Rm3D':>7s} {'pr3D':>7s}  (3D @1.5px-equiv)", flush=True)
    for name, P in clouds.items():
        a = score_cloud(name, P, cams, views, gt, covered, miss2d, miss3d_15, seen_idx,
                        crease_pts, tree_gt3, depth_t, depth_np, radii)
        res["clouds"][name] = a
        if a.get("recall_2D") is None:
            print(f"{name:18s} EMPTY"); continue
        print(f"{name:18s} {a['n_total']:8d} | {a['recall_2D']:7.4f} {a['R_miss_2D']:7.4f} "
              f"{a['cover_fg']:6.3f} {a['lift']:5.2f} | {a['recall_3D_px1.5_equiv']:7.4f} "
              f"{a['R_miss_3D_px1.5_equiv']:7.4f} {a['precision_3D_px1.5_equiv']:7.4f}",
              flush=True)

    np.savez(os.path.join(OUT, f"dexprimary_p1b_cloud_{scene}{args.tag}.npz"),
             P=tri["P"], support=tri["support"], resid=tri["resid"], ref=tri["ref"],
             surface_keep=tri["surface_keep"], moved=tri["moved"])
    jp = os.path.join(OUT, f"dexprimary_p1b_{scene}{args.tag}.json")
    json.dump(res, open(jp, "w"), indent=2)
    print(f"\nwrote {jp}")


if __name__ == "__main__":
    main()
