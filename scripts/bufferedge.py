"""tier1/scripts/bufferedge.py — BUFFER-EDGE MISS-SET DETECTABILITY.

Executes out/BUFFEREDGE_RESULTS.md (plan frozen before this ran).

*** MESH EVAL-ONLY.  The mesh supplies the GT crease labels, the miss set, and the
    perfect-geometry ORACLE arm.  No mesh quantity enters any mesh-free buffer. ***

One frozen operator, one frozen threshold rule (FPR = 10% by construction on off-crease
foreground), no per-scene tuning, no combine weights.
"""
import argparse, json, os, sys
import cv2, numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1); sys.path.insert(0, os.path.join(TIER1, "scripts"))
from src import common, render, view_split                              # noqa: E402
import run_m1b                                                          # noqa: E402

OUT = os.path.join(TIER1, "out")
FPR, TOL, CREASE_FAR = 0.10, 1.5, 3.0
BAR = {"cadpartA": 0.25, "lego": 0.15}
JACCARD_MAX = 0.70


def sobel_mag(x):
    """The ONE frozen operator.  Multi-channel -> L2 across channels."""
    a = np.asarray(x, np.float32)
    if a.ndim == 2:
        a = a[..., None]
    tot = np.zeros(a.shape[:2], np.float32)
    for c in range(a.shape[2]):
        gx = cv2.Sobel(a[..., c], cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(a[..., c], cv2.CV_32F, 0, 1, ksize=3)
        tot += gx * gx + gy * gy
    return np.sqrt(tot)


def normal_disc(n, fg):
    n = n / (np.linalg.norm(n, axis=2, keepdims=True) + 1e-12)
    out = np.zeros(n.shape[:2], np.float32)
    for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0)):
        m = np.roll(n, (dy, dx), axis=(0, 1))
        out = np.maximum(out, np.degrees(np.arccos(np.abs((n * m).sum(2)).clip(0, 1))))
    return np.where(fg, out, 0.0)


def depth_disc(d, fg):
    d0 = np.where(fg & np.isfinite(d), d, 0.0).astype(np.float32)
    gy, gx = np.gradient(d0)
    return np.where(fg, np.hypot(gy, gx), 0.0)


def normal_from_depth(d, cam, fg):
    """Camera-space normal from an exact depth map (used for the ORACLE mesh arm)."""
    H, W = d.shape
    f, cx, cy = cam.K[0, 0], cam.K[0, 2], cam.K[1, 2]
    u, v = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    dd = np.where(fg & np.isfinite(d), d, np.nan).astype(np.float32)
    P = np.dstack([(u - cx) * dd / f, (v - cy) * dd / f, dd])
    P = np.nan_to_num(P, nan=0.0)
    du = np.gradient(P, axis=1); dv = np.gradient(P, axis=0)
    n = np.cross(du, dv)
    n /= (np.linalg.norm(n, axis=2, keepdims=True) + 1e-12)
    return np.where(fg[..., None], n, 0.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", nargs="+", default=["cadpartA", "lego"])
    args = ap.parse_args()
    from tune_lib import Harness                                        # EVAL ONLY (mesh)
    from src.mesh_oracle import MeshOracle                              # EVAL ONLY
    res = {"fpr": FPR, "tol_px": TOL, "crease_far_px": CREASE_FAR,
           "bars": BAR, "jaccard_max": JACCARD_MAX,
           "operator": "Sobel 3x3 gradient magnitude, L2 across channels; the two DERIVED "
                       "maps (depth-disc, normal-disc) use the map value itself, with the "
                       "Sobel-on-derived variant reported as a sensitivity",
           "threshold_rule": "per buffer/scene/view, the 90th percentile of the response "
                             "over off-crease foreground -> FPR = 10% by construction",
           "mesh_eval_only": "labels + miss set + oracle arm only",
           "scenes": {}}

    for scene in args.scenes:
        print(f"\n===== {scene}", flush=True)
        cams, _ = common.load_cameras(scene)
        g = common.load_gaussians(scene)
        keep_g = render.defloat_mask(g["mu"], g["opacity"])
        h = Harness(scene, views=tuple(view_split.TEST))
        z = np.load(os.path.join(OUT, f"linelets_{scene}_gated_test.npz"))
        P, T, L, K = z["p"], z["t"], z["l"], z["keep"]
        o = MeshOracle(scene, angle_deg=30.0)

        m2 = os.path.join(OUT, f"2dgs_{scene}")
        g2 = pipe2 = meta2 = None
        if os.path.isdir(m2):
            from src import render2dgs
            g2, pipe2, meta2 = render2dgs.load_2dgs(m2)

        det = {}          # buffer -> list of per-view boolean arrays over that view's misses
        n_miss_tot = 0
        for v in view_split.TEST:
            cam = h.cams[v]
            gb = render.render_gbuffer(g, keep_g, cam)
            alpha = gb["alpha"].detach().cpu().numpy()
            depth = gb["depth"].detach().cpu().numpy()
            nrm = gb["normal"].detach().cpu().numpy()
            fg = alpha > 0.5
            cu, cv_, cdt = h.crease[v]

            mask, _ = run_m1b.raster_segments(h, v, P, T, L, keep=K)
            sdt = (cv2.distanceTransform((~mask).astype(np.uint8), cv2.DIST_L2, 5)
                   if mask.any() else np.full(mask.shape, 1e9, np.float32))
            miss = sdt[cv_, cu] > TOL
            mu_, mv_ = cu[miss], cv_[miss]
            n_miss_tot += int(miss.sum())
            offc = fg & (cdt > CREASE_FAR)

            B = {"depth": sobel_mag(np.where(fg & np.isfinite(depth), depth, 0.0)),
                 "depth_disc": depth_disc(depth, fg),
                 "normal": sobel_mag(np.where(fg[..., None], nrm, 0.0)),
                 "normal_disc": normal_disc(nrm, fg),
                 "alpha": sobel_mag(alpha),
                 "depth_disc_sobel(sens)": sobel_mag(depth_disc(depth, fg)),
                 "normal_disc_sobel(sens)": sobel_mag(normal_disc(nrm, fg))}
            if g2 is not None:
                gb2 = render2dgs.render_gbuffer_2dgs(
                    g2, pipe2, cam, bg_white=meta2.get("white_background", True))
                n2 = gb2["normal"].detach().cpu().numpy()
                B["2dgs_normal"] = sobel_mag(np.where(fg[..., None], n2, 0.0))
                B["2dgs_normal_disc"] = normal_disc(n2, fg)
                del gb2
            # ---- ORACLE arm: perfect geometry -------------------------------------------
            md = o.render_depth(cam, view_key=("bufedge", scene, v))
            md = md.detach().cpu().numpy() if hasattr(md, "detach") else np.asarray(md)
            mfg = np.isfinite(md) & (md > 0) & (md < 1e8)
            B["ORACLE_mesh_depth"] = sobel_mag(np.where(mfg, md, 0.0))
            B["ORACLE_mesh_normal"] = sobel_mag(normal_from_depth(md, cam, mfg))
            B["ORACLE_mesh_normal_disc"] = normal_disc(normal_from_depth(md, cam, mfg), mfg)

            for nm, R in B.items():
                base = mfg if nm.startswith("ORACLE") else fg
                neg = base & (cdt > CREASE_FAR)
                if neg.sum() < 50 or not len(mu_):
                    det.setdefault(nm, []).append(np.zeros(len(mu_), bool))
                    continue
                thr = float(np.quantile(R[neg], 1.0 - FPR))
                d_ = base & (R >= thr)
                ddt = (cv2.distanceTransform((~d_).astype(np.uint8), cv2.DIST_L2, 5)
                       if d_.any() else np.full(d_.shape, 1e9, np.float32))
                det.setdefault(nm, []).append(ddt[mv_, mu_] <= TOL)
            print(f"  view {v:2d}: GT crease px {len(cu):6d}  miss {int(miss.sum()):6d}",
                  flush=True)

        if g2 is not None:
            import torch
            del g2; torch.cuda.empty_cache()
        rows = {nm: np.concatenate(vs) for nm, vs in det.items()}
        frac = {nm: float(v.mean()) for nm, v in rows.items()}
        res["scenes"][scene] = {
            "n_miss_pixels": int(n_miss_tot), "n_linelets": int(len(K)),
            "n_kept_spec": int(K.sum()), "detected_fraction": frac}
        print(f"  [{scene}] miss-set pixels {n_miss_tot}", flush=True)
        for nm in sorted(frac, key=lambda k: -frac[k]):
            print(f"    {nm:26s} {frac[nm]:.4f}", flush=True)

        np.savez(os.path.join(OUT, f"bufferedge_det_{scene}.npz"), **rows)
        # full pairwise Jaccard over the detected miss subsets, all buffers
        ks = sorted(rows)
        J = {}
        for i, ka in enumerate(ks):
            for kb in ks[i + 1:]:
                a_, b_ = rows[ka], rows[kb]
                u_ = float((a_ | b_).sum())
                J[f"{ka}|{kb}"] = (float((a_ & b_).sum()) / u_) if u_ > 0 else float("nan")
        res["scenes"][scene]["jaccard_all_pairs"] = J
        # DISTINCT-buffer reading: collapse operator variants of the same parent buffer
        PARENT = {"depth": "depth", "depth_disc": "depth",
                  "depth_disc_sobel(sens)": "depth", "normal": "normal",
                  "normal_disc": "normal", "normal_disc_sobel(sens)": "normal",
                  "alpha": "alpha", "2dgs_normal": "2dgs", "2dgs_normal_disc": "2dgs"}
        best_par = {}
        for k, v in frac.items():
            if k.startswith("ORACLE"):
                continue
            par = PARENT.get(k)
            if par and (par not in best_par or v > frac[best_par[par]]):
                best_par[par] = k
        t2d = sorted(best_par.values(), key=lambda k: -frac[k])[:2]
        if len(t2d) == 2:
            a_, b_ = rows[t2d[0]], rows[t2d[1]]
            u_ = float((a_ | b_).sum())
            res["scenes"][scene]["top2_distinct_buffers"] = t2d
            res["scenes"][scene]["jaccard_top2_distinct"] = (
                float((a_ & b_).sum()) / u_) if u_ > 0 else float("nan")
            print(f"    top2 DISTINCT {t2d}  Jaccard "
                  f"{res['scenes'][scene]['jaccard_top2_distinct']:.4f}", flush=True)
        mf = {k: v for k, v in frac.items()
              if not k.startswith("ORACLE") and "(sens)" not in k}
        top2 = sorted(mf, key=lambda k: -mf[k])[:2]
        a, b = rows[top2[0]], rows[top2[1]]
        inter = float((a & b).sum()); uni = float((a | b).sum())
        res["scenes"][scene]["top2"] = top2
        res["scenes"][scene]["jaccard_top2"] = (inter / uni) if uni > 0 else float("nan")
        print(f"    top2 {top2}  Jaccard {res['scenes'][scene]['jaccard_top2']:.4f}",
              flush=True)

    # ---- verdict -----------------------------------------------------------------------
    mfrac = {s: {k: v for k, v in res["scenes"][s]["detected_fraction"].items()
                 if not k.startswith("ORACLE") and "(sens)" not in k} for s in args.scenes}
    passing = [b for b in mfrac[args.scenes[0]]
               if all(mfrac[s].get(b, 0.0) >= BAR[s] for s in args.scenes)]
    jac_ok = all(res["scenes"][s]["jaccard_top2"] <= JACCARD_MAX for s in args.scenes)
    ofrac = {s: {k: v for k, v in res["scenes"][s]["detected_fraction"].items()
                 if k.startswith("ORACLE")} for s in args.scenes}
    oracle_pass = any(all(ofrac[s].get(b, 0.0) >= BAR[s] for s in args.scenes)
                      for b in ofrac[args.scenes[0]])
    go = bool(passing) and jac_ok
    res["verdict"] = {"buffers_clearing_both_bars": passing,
                      "jaccard_ok": bool(jac_ok),
                      "GO": go,
                      "oracle_arm_clears_bars": bool(oracle_pass),
                      "UNCONDITIONAL_KILL": bool(not go and not oracle_pass)}
    p = os.path.join(OUT, "bufferedge.json")
    json.dump(res, open(p, "w"), indent=1)
    print(f"\n  buffers clearing BOTH bars: {passing or 'NONE'}")
    print(f"  Jaccard ok: {jac_ok}   ORACLE arm clears bars: {oracle_pass}")
    print(f"  === VERDICT: {'GO' if go else 'NO-GO'}"
          f"{' + UNCONDITIONAL KILL' if res['verdict']['UNCONDITIONAL_KILL'] else ''} ===")
    print(f"  -> {p}", flush=True)


if __name__ == "__main__":
    main()
