"""tier1/scripts/bufedge_lift.py — BUFFER-EDGE LIFT MEASUREMENT.

Executes out/BUFEDGE_LIFT_RESULTS.md (plan frozen before this ran).  No pipeline work: no
DT-pull, no prune, no chaining, no temporal.

*** MESH EVAL-ONLY.  The mesh supplies the GT crease points and the 3-D P/R metric only.
    The detection threshold is calibrated MESH-FREE (90th percentile over all foreground) so
    the candidate source contains no mesh leak; the realized off-crease FPR is reported. ***
"""
import argparse, json, os, sys
import cv2, numpy as np
from scipy.spatial import cKDTree

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1); sys.path.insert(0, os.path.join(TIER1, "scripts"))
from src import common, render, visibility, view_split                  # noqa: E402

OUT = os.path.join(TIER1, "out")
KEEP_Q, TOL, REL_EPS, MIN_SUP = 0.90, 1.5, 0.02, 3      # all frozen / already-shipped
LIFT_EVERY, CAP_PER_VIEW, SEED = 4, 12000, 0   # budget comparable to the banked
# DexiNed cloud (220k pts). A FIXED per-arm cap was the first pass's flaw: it gave the
# union the same budget as a single buffer, destroying the union's only mechanism
# (more coverage) and mechanically forcing it at or below the best single.
CREASE_FAR = 3.0


def sobel_mag(x):
    a = np.asarray(x, np.float32)
    if a.ndim == 2:
        a = a[..., None]
    t = np.zeros(a.shape[:2], np.float32)
    for c in range(a.shape[2]):
        gx = cv2.Sobel(a[..., c], cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(a[..., c], cv2.CV_32F, 0, 1, ksize=3)
        t += gx * gx + gy * gy
    return np.sqrt(t)


def normal_disc(n, fg):
    n = n / (np.linalg.norm(n, axis=2, keepdims=True) + 1e-12)
    o = np.zeros(n.shape[:2], np.float32)
    for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0)):
        m = np.roll(n, (dy, dx), axis=(0, 1))
        o = np.maximum(o, np.degrees(np.arccos(np.abs((n * m).sum(2)).clip(0, 1))))
    return np.where(fg, o, 0.0)


def depth_disc(d, fg):
    d0 = np.where(fg & np.isfinite(d), d, 0.0).astype(np.float32)
    gy, gx = np.gradient(d0)
    return np.where(fg, np.hypot(gy, gx), 0.0)


def backproject(uu, vv, d, cam):
    f, cx, cy = cam.K[0, 0], cam.K[0, 2], cam.K[1, 2]
    pc = np.stack([(uu - cx) * d / f, (vv - cy) * d / f, d], 1)
    R, t = cam.w2c[:3, :3], cam.w2c[:3, 3]
    return (pc - t) @ R


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", nargs="+", default=["cadpartA", "lego"])
    args = ap.parse_args()
    from src.mesh_oracle import MeshOracle                              # EVAL ONLY
    rng = np.random.default_rng(SEED)
    res = {"frozen": {"keep_quantile": KEEP_Q, "tol_px": TOL, "rel_eps": REL_EPS,
                      "min_support_views": MIN_SUP, "cap_per_view": CAP_PER_VIEW,
                      "lift_every_nth_train_view": LIFT_EVERY},
           "buffer_set": ["2dgs_normal", "normal_disc", "depth_disc"],
           "mesh_eval_only": "GT crease points + 3D metric only; threshold is mesh-free",
           "banked_context": {"dexined_cloud_cadpartA": {"P": 0.7302, "R": 0.8431},
                              "step3_pool_oracle_cadpartA": {"P": 0.7274, "R": 0.7271}},
           "scenes": {}}

    for scene in args.scenes:
        print(f"\n===== {scene}", flush=True)
        cams, _ = common.load_cameras(scene)
        g = common.load_gaussians(scene)
        keep_g = render.defloat_mask(g["mu"], g["opacity"])
        tv = list(view_split.TRAIN)
        o = MeshOracle(scene, angle_deg=30.0)
        C = np.asarray(o.crease_pts, np.float64)
        tree_gt = cKDTree(C)

        m2 = os.path.join(OUT, f"2dgs_{scene}")
        g2 = pipe2 = meta2 = None
        if os.path.isdir(m2):
            from src import render2dgs
            g2, pipe2, meta2 = render2dgs.load_2dgs(m2)

        # ---- pass 1: render + cache buffers, build detection masks --------------------
        DET, DEPTH, FGM = {}, {}, {}
        fpr_acc = {}
        print(f"  rendering {len(tv)} TRAIN views", flush=True)
        for j, v in enumerate(tv):
            cam = cams[v]
            gb = render.render_gbuffer(g, keep_g, cam)
            al = gb["alpha"].detach().cpu().numpy()
            dp = gb["depth"].detach().cpu().numpy()
            nr = gb["normal"].detach().cpu().numpy()
            fg = (al > 0.5) & np.isfinite(dp)
            R = {"normal_disc": normal_disc(nr, fg), "depth_disc": depth_disc(dp, fg)}
            if g2 is not None:
                gb2 = render2dgs.render_gbuffer_2dgs(
                    g2, pipe2, cam, bg_white=meta2.get("white_background", True))
                R["2dgs_normal"] = sobel_mag(np.where(
                    fg[..., None], gb2["normal"].detach().cpu().numpy(), 0.0))
                del gb2
            uvq = o.visible_crease_uv(cam, view_key=("bufliftfpr", scene, v))
            cmask = np.zeros(fg.shape, bool)
            cu = np.clip(np.round(uvq[:, 0]).astype(int), 0, fg.shape[1] - 1)
            cv_ = np.clip(np.round(uvq[:, 1]).astype(int), 0, fg.shape[0] - 1)
            cmask[cv_, cu] = True
            cdt = cv2.distanceTransform((~cmask).astype(np.uint8), cv2.DIST_L2, 5)
            offc = fg & (cdt > CREASE_FAR)
            d = {}
            for nm, r in R.items():
                thr = float(np.quantile(r[fg], KEEP_Q)) if fg.any() else np.inf
                d[nm] = fg & (r >= thr)
                fpr_acc.setdefault(nm, []).append(
                    float(d[nm][offc].mean()) if offc.any() else np.nan)
            d["UNION"] = np.zeros_like(fg)
            for nm in R:
                d["UNION"] |= d[nm]
            d["UNION_no2dgs"] = d["normal_disc"] | d["depth_disc"]
            nfg = int(fg.sum())
            nrand = int(round((1.0 - KEEP_Q) * nfg))
            fv, fu = np.nonzero(fg)
            pick = rng.choice(nfg, size=min(nrand, nfg), replace=False)
            rm = np.zeros_like(fg); rm[fv[pick], fu[pick]] = True
            d["NULL"] = rm
            DET[v], DEPTH[v], FGM[v] = d, dp.astype(np.float32), fg
            if (j + 1) % 20 == 0:
                print(f"    {j+1}/{len(tv)}", flush=True)
        if g2 is not None:
            import torch
            del g2; torch.cuda.empty_cache()

        arms = ["2dgs_normal", "normal_disc", "depth_disc",
                "UNION", "UNION_no2dgs", "NULL"]
        arms = [a for a in arms if a in DET[tv[0]]]
        # ---- radius, matching the p1b definition --------------------------------------
        zs = []
        for v in view_split.TEST:
            cam = cams[v]
            zc = (cam.w2c[:3, :3] @ C.T).T[:, 2] + cam.w2c[2, 3]
            zs.append(zc[zc > 1e-6])
        zmed = float(np.median(np.concatenate(zs)))
        f0 = cams[view_split.TEST[0]].K[0, 0]
        bb = float(np.linalg.norm(C.max(0) - C.min(0)))
        radii = {"px1.5_equiv": 1.5 * zmed / f0,
                 "chamfer_0.5pct_bbox": 0.005 * bb, "chamfer_1.5pct_bbox": 0.015 * bb}
        # GT crease points visible in >=1 TEST view
        seen = np.zeros(len(C), bool)
        from tune_lib import Harness                                    # EVAL ONLY
        h = Harness(scene, views=tuple(view_split.TEST))
        for v in view_split.TEST:
            vis, _, _ = visibility.visible_mask(C, h.cams[v], h.gbufs[v]["depth"])
            seen |= vis
        print(f"  radius px1.5_equiv {radii['px1.5_equiv']:.5f}  "
              f"GT crease pts {len(C)} seen {int(seen.sum())}", flush=True)

        out = {"n_crease_pts": int(len(C)), "n_seen": int(seen.sum()),
               "radii": radii, "bbox_diag": bb,
               "realized_offcrease_FPR": {k: float(np.nanmean(v))
                                          for k, v in fpr_acc.items()},
               "arms": {}}
        lift_views = tv[::LIFT_EVERY]
        for arm in arms:
            pts = []
            for v in lift_views:
                vv, uu = np.nonzero(DET[v][arm])
                if len(uu) == 0:
                    continue
                if len(uu) > CAP_PER_VIEW:
                    k = rng.choice(len(uu), size=CAP_PER_VIEW, replace=False)
                    uu, vv = uu[k], vv[k]
                dd = DEPTH[v][vv, uu]
                ok = np.isfinite(dd) & (dd > 1e-6)
                pts.append(backproject(uu[ok].astype(np.float64),
                                       vv[ok].astype(np.float64), dd[ok], cams[v]))
            if not pts:
                out["arms"][arm] = {"n_total": 0}
                continue
            P = np.concatenate(pts, 0)
            sup = np.zeros(len(P), np.int32)
            for v in tv:
                cam = cams[v]
                uv, zc = common.project(P, cam)
                u = np.round(uv[:, 0]).astype(int); w_ = np.round(uv[:, 1]).astype(int)
                inb = ((u >= 0) & (u < cam.W) & (w_ >= 0) & (w_ < cam.H) & (zc > 1e-6))
                uc = np.clip(u, 0, cam.W - 1); wc = np.clip(w_, 0, cam.H - 1)
                zb = DEPTH[v][wc, uc]
                unocc = inb & np.isfinite(zb) & (np.abs(zb - zc) < REL_EPS * zc)
                dt = cv2.distanceTransform((~DET[v][arm]).astype(np.uint8), cv2.DIST_L2, 5)
                sup += (unocc & (dt[wc, uc] <= TOL)).astype(np.int32)
            Pk = P[sup >= MIN_SUP]
            # persist the kept cloud so the visualization renders EXACTLY the arms these
            # numbers describe (additive; identical seed and constants, numbers unchanged)
            np.savez_compressed(os.path.join(OUT, f"bufedge_cloud_{scene}_{arm}.npz"), P=Pk)
            a = {"n_lifted": int(len(P)), "n_total": int(len(Pk))}
            if len(Pk):
                t3 = cKDTree(Pk)
                d3 = t3.query(C[seen], k=1)[0]
                dp_ = tree_gt.query(Pk, k=1)[0]
                for rn, rad in radii.items():
                    a[f"recall_3D_{rn}"] = float((d3 <= rad).mean())
                    a[f"precision_3D_{rn}"] = float((dp_ <= rad).mean())
                a["chamfer_median"] = float(np.median(d3))
            out["arms"][arm] = a
            r = a.get("recall_3D_px1.5_equiv", float("nan"))
            p_ = a.get("precision_3D_px1.5_equiv", float("nan"))
            print(f"    {arm:14s} lifted {a['n_lifted']:7d} kept {a['n_total']:7d}  "
                  f"P {p_:.4f}  R {r:.4f}", flush=True)
        res["scenes"][scene] = out
        del DET, DEPTH, FGM, h

    # ---- verdict -----------------------------------------------------------------------
    def R(s, a):
        return res["scenes"][s]["arms"].get(a, {}).get("recall_3D_px1.5_equiv", float("nan"))
    singles = ["2dgs_normal", "normal_disc", "depth_disc"]
    v = {}
    for s in args.scenes:
        av = [a for a in singles if a in res["scenes"][s]["arms"]]
        best = max(av, key=lambda a: R(s, a))
        v[s] = {"best_single": best, "best_single_R": R(s, best),
                "union_R": R(s, "UNION"), "union_no2dgs_R": R(s, "UNION_no2dgs"),
                "null_R": R(s, "NULL"),
                "delta_union_vs_best": R(s, "UNION") - R(s, best),
                "null_below_best_by": R(s, best) - R(s, "NULL")}
    no_reg = all(v[s]["delta_union_vs_best"] >= -0.02 for s in args.scenes)
    gain = any(v[s]["delta_union_vs_best"] >= 0.05 for s in args.scenes)
    nullok = all(v[s]["null_below_best_by"] >= 0.15 for s in args.scenes)
    res["verdict"] = {"per_scene": v, "no_regression": bool(no_reg),
                      "real_gain": bool(gain), "null_floor_ok": bool(nullok),
                      "GO": bool(no_reg and gain and nullok)}
    p = os.path.join(OUT, "bufedge_lift.json")
    json.dump(res, open(p, "w"), indent=1)
    print("\n  === VERDICT ===")
    for s in args.scenes:
        d = v[s]
        print(f"  {s:9s} best_single {d['best_single']} R {d['best_single_R']:.4f} | "
              f"UNION R {d['union_R']:.4f} (d {d['delta_union_vs_best']:+.4f}) | "
              f"no2dgs R {d['union_no2dgs_R']:.4f} | NULL R {d['null_R']:.4f} "
              f"(below best by {d['null_below_best_by']:.4f})")
    print(f"  no_regression {no_reg} | real_gain {gain} | null_floor {nullok} "
          f"-> {'GO' if res['verdict']['GO'] else 'NO-GO'}")
    print(f"  -> {p}", flush=True)


if __name__ == "__main__":
    main()
