"""tier1/scripts/gicosa_pilot.py — STEP 4 pilot: the dd3 pipeline, BYTE-IDENTICAL, on gicosa.

*** MESH EVAL-ONLY: faint GT crease overlay only.  P/R is not computed and not gated. ***

PRECONDITION 1, enforced in code: L_px is derived from GICOSA'S OWN TRUNK median half-length
at run time.  The cadpart constant 8.632 does not appear anywhere; the RULE travels, not the
number.  Every other constant is the frozen dd3 value: GAP_PX 3, SNAP_PX 6, MIN_ARC_MULT 4,
RANSAC_TOL_PX 2.5 / inlier 0.80, TAU_CREASE_DEG 30 (the project's shipped crease definition),
SUPPORT_FRAC 0.5, and the frozen m1b_stroke_temporal chaining defaults.

PRECONDITION 2: the gicosa DexiNed Phase-1b cloud is built first, with cadpartA's banked
arguments (n_ref 40, K 6, rho 0.2, tau 1.5, thr 0.5, native, halfpix 0.0, resid_max 1.0,
rel_eps 0.02).  The dd2 dihedral gate additionally needs a 2DGS model, which did not exist for
gicosa either and was trained with the frozen chair/lego/cadpartA recipe.
"""
import argparse, json, os, sys
import cv2, numpy as np
from scipy.spatial import cKDTree

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1); sys.path.insert(0, os.path.join(TIER1, "scripts"))
from src import common, render, view_split, strokes, render2dgs             # noqa: E402
import temporal_m1b as T                                                    # noqa: E402
import m1b_stroke_temporal as M                                             # noqa: E402
import diag2dgs                                                             # noqa: E402
from strokeviz import chain_args, N_ORBIT, STRIP0, STRIP_N, VIZ
from mergeviz import (px_to_world, straight_ok, snap_endpoints, polyline_pts,
                      GAP_PX, SNAP_PX, MIN_ARC_MULT, RANSAC_TOL_PX)
from dedebris2 import TAU_CREASE_DEG, SUPPORT_FRAC, N_SUP_VIEWS, Shim
from dd3 import project_runs, draw_runs

OUT = os.path.join(TIER1, "out")
SCENE = "gicosa"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no_temporal", action="store_true")
    A = ap.parse_args()
    ca = chain_args()
    cams, _ = common.load_cameras(SCENE)
    g = common.load_gaussians(SCENE)
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    f = cams[0].K[0, 0]
    rep = {"scene": SCENE, "pipeline": "dd3 byte-identical", "preconditions": {}}

    # ---- trunk = Step-4 zero-knob carrier ---------------------------------------------
    z4 = np.load(os.path.join(OUT, f"linelets_{SCENE}_step4.npz"))
    tp = os.path.join(OUT, f"linelets_{SCENE}_svstep3_test.npz")
    np.savez(tp, p=z4["p"], t=z4["t"], l=z4["l"], keep=z4["keep"],
             inlier_ratio=z4["inlier_ratio"], n_vis=z4["n_vis"])
    trunk, tinfo = M.build_chains(SCENE, "svstep3", ca)
    print(f"  [trunk] Step-4 zero-knob carrier -> {tinfo['n_strokes']} strokes", flush=True)

    # ---- PRECONDITION 1: L_px from GICOSA'S OWN trunk ---------------------------------
    k4 = z4["keep"].astype(bool)
    zs = [np.median((c.w2c[:3, :3] @ z4["p"][k4].T).T[:, 2] + c.w2c[2, 3])
          for c in [cams[v] for v in view_split.TRAIN]]
    zmed = float(np.median(zs))
    L_PX = float(np.median(z4["l"][k4]) * f / zmed)
    lw = px_to_world(L_PX, zmed, f)
    rep["preconditions"]["L_px_from_own_trunk"] = L_PX
    rep["preconditions"]["cadpart_constant_not_used"] = 8.632
    print(f"  [precond 1] L_px from gicosa's OWN trunk = {L_PX:.4f} "
          f"(cadpart's 8.632 NOT used)", flush=True)

    # ---- carrier 2: gicosa DexiNed Phase-1b cloud -------------------------------------
    cp = os.path.join(OUT, f"dexprimary_p1b_cloud_{SCENE}_ref40.npz")
    zc = np.load(cp)
    P = zc["P"]
    sup = zc["support"]
    if "surface_keep" in zc.files:
        m_ = zc["surface_keep"].astype(bool)
        P, sup = P[m_], sup[m_]
    tree = cKDTree(P)
    _, nb = tree.query(P, k=11)
    Tg = np.zeros_like(P)
    for i in range(len(P)):
        Q = P[nb[i, 1:]] - P[i]
        _, _, vt = np.linalg.svd(Q - Q.mean(0), full_matrices=False)
        Tg[i] = vt[0]
    conf = (sup - sup.min()) / max(sup.max() - sup.min(), 1e-9)
    print(f"  [precond 2] gicosa p1b cloud {len(P)} pts", flush=True)

    # ---- dd3 chain, byte-identical -----------------------------------------------------
    ch, kept = strokes.chain_linelets_3d(P, Tg, np.full(len(P), lw), conf=conf,
                                         nms_radius_mult=ca.nms_mult, k=ca.knn,
                                         cos_tan=ca.cos_tan, cos_col=ca.cos_col,
                                         gap_mult=ca.gap_mult, min_nodes=ca.min_nodes)
    Pk = P[kept]
    tol_w, minarc = px_to_world(RANSAC_TOL_PX, zmed, f), MIN_ARC_MULT * lw
    dex2 = [V for V in (Pk[c] for c in ch)
            if float(np.sum(np.linalg.norm(np.diff(V, axis=0), axis=1))) >= minarc
            and straight_ok(V, tol_w)]
    ttree = cKDTree(polyline_pts(trunk))
    gapw = px_to_world(GAP_PX, zmed, f)
    keepv = []
    for V in dex2:
        d, _ = ttree.query(V, k=1)
        if (d > gapw).any():
            keepv.append(V[d > gapw])
    Vfill = np.concatenate(keepv, 0)
    tf = cKDTree(Vfill)
    _, nb2 = tf.query(Vfill, k=min(11, len(Vfill)))
    Tf = np.zeros_like(Vfill)
    for i in range(len(Vfill)):
        Q = Vfill[nb2[i, 1:]] - Vfill[i]
        _, _, vt = np.linalg.svd(Q - Q.mean(0), full_matrices=False)
        Tf[i] = vt[0]
    ch2, k2 = strokes.chain_linelets_3d(Vfill, Tf, np.full(len(Vfill), lw),
                                        nms_radius_mult=ca.nms_mult, k=ca.knn,
                                        cos_tan=ca.cos_tan, cos_col=ca.cos_col,
                                        gap_mult=ca.gap_mult, min_nodes=ca.min_nodes)
    Vk, Tk = Vfill[k2], Tf[k2]
    fidx = [c for c in ch2
            if float(np.sum(np.linalg.norm(np.diff(Vk[c], axis=0), axis=1))) >= minarc
            and straight_ok(Vk[c], tol_w)]
    print(f"  [chain] cloud -> NMS {int(kept.sum())} -> {len(ch)} -> filtered {len(dex2)} "
          f"-> fill candidates {len(fidx)}", flush=True)

    # ---- dd2 dihedral gate (needs the gicosa 2DGS) ------------------------------------
    g2, pipe2, meta2 = render2dgs.load_2dgs(os.path.join(OUT, f"2dgs_{SCENE}"))
    tv = list(view_split.TRAIN)[::max(1, 80 // N_SUP_VIEWS)][:N_SUP_VIEWS]
    sh = Shim(); sh.cams = cams; sh.gbufs = {}
    n2, fgm = {}, {}
    for v in tv:
        gb = render.render_gbuffer(g, keep_g, cams[v])
        sh.gbufs[v] = {"depth": gb["depth"]}
        fgm[v] = (gb["alpha"].detach().cpu().numpy() > 0.5)
        gb2 = render2dgs.render_gbuffer_2dgs(g2, pipe2, cams[v],
                                             bg_white=meta2.get("white_background", True))
        n2[v] = gb2["normal"].detach().cpu().numpy().astype(np.float32)
        del gb, gb2
    Vall = np.concatenate([Vk[c] for c in fidx], 0)
    Tall = np.concatenate([Tk[c] for c in fidx], 0)
    th, nok = diag2dgs.ribbon_dihedral(Vall, Tall, sh, tv, n2, fgm)
    import torch
    del g2, n2, fgm, sh
    torch.cuda.empty_cache()
    th = np.where(nok > 0, th, 0.0)
    off, fill = 0, []
    for c in fidx:
        n = len(c); s = th[off:off + n]; off += n
        if float(np.nanmean(s >= TAU_CREASE_DEG)) >= SUPPORT_FRAC:
            fill.append(Vk[c])
    print(f"  [dd2 gate] tau {TAU_CREASE_DEG} deg -> fill {len(fidx)} -> kept {len(fill)} "
          f"(median theta {np.nanmedian(th):.2f} deg)", flush=True)

    merged_raw = [V.copy() for V in trunk] + [V.copy() for V in fill]
    merged, n_snap = snap_endpoints(merged_raw, px_to_world(SNAP_PX, zmed, f))
    open_end = [(bool(np.allclose(a[0], b[0])), bool(np.allclose(a[-1], b[-1])))
                for a, b in zip(merged_raw, merged)]
    tr_open = [(True, True)] * len(trunk)
    arc = float(sum(np.sum(np.linalg.norm(np.diff(V, axis=0), axis=1)) for V in merged))
    arc_t = float(sum(np.sum(np.linalg.norm(np.diff(V, axis=0), axis=1)) for V in trunk))
    rep["result"] = {"n_trunk": len(trunk), "n_fill": len(fill), "n_strokes": len(merged),
                     "median_vertices": float(np.median([len(c) for c in merged])),
                     "n_endpoint_snaps": int(n_snap),
                     "arc": arc, "arc_trunk_fallback": arc_t, "arc_vs_trunk": arc / arc_t}
    print(f"  [merged] {len(merged)} strokes ({len(trunk)} trunk + {len(fill)} fill), "
          f"arc {arc:.3f} vs fallback trunk {arc_t:.3f} ({arc/arc_t:.2f}x)", flush=True)

    # ---- render ------------------------------------------------------------------------
    from src.mesh_oracle import MeshOracle                                  # EVAL ONLY
    o = MeshOracle(SCENE, angle_deg=30.0)
    ctr = np.median(g["mu"][keep_g], axis=0)
    path = T.orbit_cameras(cams[5], cams[15], N_ORBIT, ctr)
    idx = list(range(STRIP0, STRIP0 + STRIP_N))
    imgs, fbs = [], []
    for k in idx:
        cam = path[k]
        gb = render.render_gbuffer(g, keep_g, cam)
        uvq = o.visible_crease_uv(cam, view_key=("gp", SCENE, k))
        cm = np.zeros((cam.H, cam.W), bool)
        cm[np.clip(np.round(uvq[:, 1]).astype(int), 0, cam.H - 1),
           np.clip(np.round(uvq[:, 0]).astype(int), 0, cam.W - 1)] = True
        imgs.append(draw_runs(project_runs(merged, open_end, cam, gb["depth"]), cam, cm))
        if k == idx[0]:
            fbs.append(draw_runs(project_runs(trunk, tr_open, cam, gb["depth"]), cam, cm))
        del gb
    h = 460
    band = np.concatenate([cv2.resize((np.clip(im, 0, 1) * 255).astype(np.uint8), (h, h))
                           for im in imgs], 1)
    band = np.concatenate([np.full((44, band.shape[1], 3), 255, np.uint8), band], 0)
    cv2.putText(band, f"{SCENE} dd3 pilot  frames {idx[0]}-{idx[-1]}/{N_ORBIT}  "
                      f"{len(merged)} strokes  L_px {L_PX:.2f} from its OWN trunk",
                (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 0, 0), 2, cv2.LINE_AA)
    p = lambda n: os.path.join(VIZ, f"stroke_{SCENE}_{n}.png")
    cv2.imwrite(p("pilot_strip"), band[:, :, ::-1])
    cv2.imwrite(p("pilot_still"), (np.clip(cv2.resize(imgs[0], (1700, 1700)), 0, 1) * 255
                                   ).astype(np.uint8)[:, :, ::-1])
    cv2.imwrite(p("pilot_fallback_still"),
                (np.clip(cv2.resize(fbs[0], (1700, 1700)), 0, 1) * 255
                 ).astype(np.uint8)[:, :, ::-1])
    a_ = (cv2.resize((np.clip(fbs[0], 0, 1) * 255).astype(np.uint8), (1700, 1700)).min(2) < 150)
    b_ = (cv2.resize((np.clip(imgs[0], 0, 1) * 255).astype(np.uint8), (1700, 1700)).min(2) < 150)
    d = np.ones((1700, 1700, 3), np.float32)
    d[a_] = (0.85, 0.15, 0.15); d[b_] = (0.15, 0.25, 0.85); d[a_ & b_] = (0.15,) * 3
    cv2.imwrite(p("pilot_diff_vs_fallback"), (d * 255).astype(np.uint8)[:, :, ::-1])
    print("  wrote pilot_still / pilot_strip / pilot_fallback_still / "
          "pilot_diff_vs_fallback", flush=True)

    if not A.no_temporal:
        ca.n_resample, ca.max_cand, ca.cand_radius, ca.match_thresh = 16, 6, 40.0, 3.0
        frames = [M.frame_data(g, keep_g, c, merged, ca) for c in path]
        m = M.sequence_metrics(frames, ca)
        rep["temporal_240"] = m
        a2, b2 = m["A"], m["B"]
        print(f"\n  gicosa pilot temporal: P_pop {a2['P_pop']:.4f} = unmatched "
              f"{a2['unmatched_frac']:.4f} + cut {a2['cut_frac']:.4f} | BASE "
              f"{b2['P_pop']:.4f} | ratio {b2['P_pop']/a2['P_pop']:.2f}x", flush=True)
    json.dump(rep, open(os.path.join(OUT, "gicosa_pilot.json"), "w"), indent=1)
    print(f"  -> {os.path.join(OUT,'gicosa_pilot.json')}", flush=True)


if __name__ == "__main__":
    main()
