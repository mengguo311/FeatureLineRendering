"""tier1/scripts/dd3.py — adopt dd2 as carrier of record, then
Part A: null-controlled redundant-duplicate removal.
Part B: constant screen-space width, taper ONLY at true open endpoints, sharp corners.

Executes out/dd3_spec.md.  *** MESH EVAL-ONLY: faint GT crease overlay only. ***
Object space only, no per-scene tuning.

TWO IMPLEMENTATION POINTS SETTLED HONESTLY BEFORE CODING
1. "RANSAC straightness residual exceeds the polyhedron-straight threshold already used".
   Every fill stroke ALREADY passed straight_ok at inlier fraction 0.80, so the inlier test
   can never fire again.  The threshold "already used" that CAN fire is the tolerance,
   RANSAC_TOL_PX = 2.5 px.  A polyhedron edge is straight, so the strict reading is taken:
   a stroke is non-straight iff its MAXIMUM perpendicular residual to its own fitted line
   exceeds 2.5 px equivalent.  No new constant is introduced.
2. R_dedup = 3 x the drawn stroke width (3 x CORE_W = 7.8 px equivalent).  Below about three
   widths, two parallel strokes read as one thickened line, so a second stroke there adds no
   information.  Pixel-anchored, set once, not per scene.  F = 0.5, the same majority rule
   used in dd2.

NULL CONTROL uses this codebase's own shift-control idiom (final_recipe.MASK_SHIFT): the
trunk is replaced by the SAME strokes rigidly ROTATED about the object centre, which keeps
count, shape, length distribution and spatial statistics identical and destroys only the
registration.  5 random rotations, fixed seed.
"""
import argparse, json, os, sys
import cv2, numpy as np
from scipy.spatial import cKDTree

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1); sys.path.insert(0, os.path.join(TIER1, "scripts"))
from src import common, render, view_split, strokes, visibility, render2dgs, linelet  # noqa
import temporal_m1b as T                                                # noqa: E402
import m1b_stroke_temporal as M                                         # noqa: E402
import diag2dgs                                                         # noqa: E402
from strokeviz import chain_args, N_ORBIT, STRIP0, STRIP_N, VIZ, SCENE, CORE_W, TIP_W
from mergeviz import (px_to_world, straight_ok, snap_endpoints, polyline_pts,
                      L_PX_TRUNKSCALE, GAP_PX, SNAP_PX, MIN_ARC_MULT, RANSAC_TOL_PX)
from dedebris2 import TAU_CREASE_DEG, SUPPORT_FRAC, N_SUP_VIEWS, Shim

OUT = os.path.join(TIER1, "out")
R_DEDUP_PX = 3.0 * CORE_W        # three drawn stroke widths
F_DEDUP = 0.50                   # same majority rule as dd2
N_NULL = 5
TAPER_PX = 14.0


def max_resid(V):
    if len(V) < 3:
        return 0.0
    c = V.mean(0)
    _, _, vt = np.linalg.svd(V - c, full_matrices=False)
    d = vt[0]
    r = (V - c) - np.outer((V - c) @ d, d)
    return float(np.linalg.norm(r, axis=1).max())


def dedup_drop(fill, ref_pts, r_dedup, tol_world):
    """Drop iff redundant (>= F of vertices within r_dedup of a reference stroke) AND
    non-straight (max residual > tol)."""
    if ref_pts is None or not len(ref_pts):
        return [], list(range(len(fill)))
    tree = cKDTree(ref_pts)
    drop, keep = [], []
    for i, V in enumerate(fill):
        d, _ = tree.query(V, k=1)
        redundant = float((d <= r_dedup).mean()) >= F_DEDUP
        bent = max_resid(V) > tol_world
        (drop if (redundant and bent) else keep).append(i)
    return drop, keep


def rot_about(P, c, R):
    return (P - c) @ R.T + c


def project_runs(chain3d, open_end, cam, depth):
    """Mirror of m1b_stroke_temporal.ours_strokes, but also returns per-run whether each end
    should TAPER. Taper at an OPEN 3-D chain endpoint or at an occlusion boundary; never at a
    JOIN (an endpoint snapped to a shared corner)."""
    out = []
    for ci, V in enumerate(chain3d):
        vis, uv, _ = visibility.visible_mask(V, cam, depth)
        inb = ((uv[:, 0] >= 0) & (uv[:, 0] < cam.W) & (uv[:, 1] >= 0) & (uv[:, 1] < cam.H))
        good = vis & inb
        run, start = [], None
        for i, gd in enumerate(good):
            if gd:
                if not run:
                    start = i
                run.append(uv[i])
            elif len(run) >= 2:
                ts = open_end[ci][0] if start == 0 else True     # occlusion boundary -> taper
                te = True                                        # ended by occlusion
                out.append((np.array(run), ts, te)); run = []
            else:
                run = []
        if len(run) >= 2:
            ts = open_end[ci][0] if start == 0 else True
            te = open_end[ci][1]
            out.append((np.array(run), ts, te))
    return out


def draw_runs(runs, cam, crease=None):
    """Constant SCREEN-SPACE width; taper only where flagged; piecewise-linear, sharp corners."""
    H, W = cam.H, cam.W
    img = np.ones((H, W, 3), np.float32)
    if crease is not None:
        img[crease] = (1.0, 0.82, 0.82)
    lay = np.zeros((H, W), np.float32)
    for poly, ts, te in runs:
        n = len(poly)
        d = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(poly, axis=0), axis=1))]
        w = np.full(n, CORE_W)
        if ts:
            w = np.minimum(w, TIP_W + (CORE_W - TIP_W) * np.clip(d / TAPER_PX, 0, 1))
        if te:
            w = np.minimum(w, TIP_W + (CORE_W - TIP_W) *
                           np.clip((d[-1] - d) / TAPER_PX, 0, 1))
        for i in range(n - 1):
            a, b = poly[i], poly[i + 1]
            e = b - a
            L = np.linalg.norm(e)
            if L < 1e-9:
                continue
            nv = np.array([-e[1], e[0]]) / L
            q = np.array([a + nv * w[i] / 2, b + nv * w[i + 1] / 2,
                          b - nv * w[i + 1] / 2, a - nv * w[i] / 2])
            cv2.fillPoly(lay, [np.round(q * 16).astype(np.int32)], 1.0,
                         lineType=cv2.LINE_AA, shift=4)
    return img * (1.0 - lay[..., None] * 0.9)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no_temporal", action="store_true")
    A = ap.parse_args()
    ca = chain_args()
    rng = np.random.default_rng(0)
    cams, _ = common.load_cameras(SCENE)
    g = common.load_gaussians(SCENE)
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    f = cams[0].K[0, 0]
    rep = {"scene": SCENE, "carrier_of_record": "dd2 (v2 cross-stroke dihedral gate)",
           "R_dedup_px": R_DEDUP_PX, "F_dedup": F_DEDUP,
           "straight_rule": "max perpendicular residual > RANSAC_TOL_PX 2.5 px equivalent "
                            "(the threshold already used; the 0.80 inlier test cannot fire "
                            "again because every fill stroke already passed it)"}

    # ================= rebuild the dd2 carrier =========================================
    trunk, tinfo = M.build_chains(SCENE, "svstep3", ca)
    z = np.load(os.path.join(OUT, f"linelets_{SCENE}_svdexined_test.npz"))
    P, Tg, conf = z["p"], z["t"], z["inlier_ratio"]
    zmed = np.median([np.median((c.w2c[:3, :3] @ P.T).T[:, 2] + c.w2c[2, 3])
                      for c in [cams[v] for v in view_split.TRAIN]])
    lw = px_to_world(L_PX_TRUNKSCALE, zmed, f)
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
    keepv = []
    for V in dex2:
        d, _ = ttree.query(V, k=1)
        if (d > px_to_world(GAP_PX, zmed, f)).any():
            keepv.append(V[d > px_to_world(GAP_PX, zmed, f)])
    Vfill = np.concatenate(keepv, 0)
    tf = cKDTree(Vfill)
    _, nb = tf.query(Vfill, k=min(11, len(Vfill)))
    Tf = np.zeros_like(Vfill)
    for i in range(len(Vfill)):
        Q = Vfill[nb[i, 1:]] - Vfill[i]
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
    # dd2 dihedral gate
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
    off, dd2fill = 0, []
    for c in fidx:
        n = len(c); s = th[off:off + n]; off += n
        if float(np.nanmean(s >= TAU_CREASE_DEG)) >= SUPPORT_FRAC:
            dd2fill.append(Vk[c])
    print(f"  [dd2 carrier] trunk {len(trunk)} + fill {len(dd2fill)} = "
          f"{len(trunk)+len(dd2fill)} strokes", flush=True)

    # ================= PART A: null-controlled dedup ===================================
    r_ded = px_to_world(R_DEDUP_PX, zmed, f)
    tr_pts = polyline_pts(trunk)
    drop, keepi = dedup_drop(dd2fill, tr_pts, r_ded, tol_w)
    ctr = np.median(g["mu"][keep_g], axis=0)
    nulls = []
    for _ in range(N_NULL):
        Q, _r = np.linalg.qr(rng.normal(size=(3, 3)))
        if np.linalg.det(Q) < 0:
            Q[:, 0] *= -1
        npts = np.concatenate([rot_about(V, ctr, Q) for V in trunk], 0)
        nd, _ = dedup_drop(dd2fill, npts, r_ded, tol_w)
        nulls.append(len(nd))
    # per-stroke diagnostic: WHICH leg of the AND blocked each stroke
    _t = cKDTree(tr_pts)
    diag = []
    for V in dd2fill:
        dd_, _ = _t.query(V, k=1)
        diag.append({"redundant_frac": float((dd_ <= r_ded).mean()),
                     "max_resid_px": float(max_resid(V) * f / zmed),
                     "arc_px": float(np.sum(np.linalg.norm(np.diff(V, axis=0), axis=1))
                                     * f / zmed)})
    rep["partA_per_stroke"] = diag
    rep["partA_diag"] = {
        "n_redundant": int(sum(d["redundant_frac"] >= F_DEDUP for d in diag)),
        "n_bent": int(sum(d["max_resid_px"] > RANSAC_TOL_PX for d in diag)),
        "max_redundant_frac": float(max(d["redundant_frac"] for d in diag)),
        "max_resid_px_seen": float(max(d["max_resid_px"] for d in diag)),
        "R_dedup_px": R_DEDUP_PX, "resid_bar_px": RANSAC_TOL_PX}
    print(f"  [PART A diag] strokes meeting REDUNDANT leg: "
          f"{rep['partA_diag']['n_redundant']}/{len(diag)} (max frac "
          f"{rep['partA_diag']['max_redundant_frac']:.3f} vs bar {F_DEDUP}) | "
          f"meeting BENT leg: {rep['partA_diag']['n_bent']}/{len(diag)} (max resid "
          f"{rep['partA_diag']['max_resid_px_seen']:.2f} px vs bar {RANSAC_TOL_PX})",
          flush=True)
    # per-LEG null: is "within R_dedup of a trunk stroke" a real registration signal, or
    # just a density artefact? The AND never fires, so the AND-null cannot discriminate.
    nred_real = int(sum(d["redundant_frac"] >= F_DEDUP for d in diag))
    nred_null = []
    for _ in range(N_NULL):
        Q, _r = np.linalg.qr(rng.normal(size=(3, 3)))
        if np.linalg.det(Q) < 0:
            Q[:, 0] *= -1
        tt = cKDTree(np.concatenate([rot_about(V, ctr, Q) for V in trunk], 0))
        nred_null.append(int(sum(float((tt.query(V, k=1)[0] <= r_ded).mean()) >= F_DEDUP
                                 for V in dd2fill)))
    rep["partA_leg_null"] = {"redundant_leg_real": nred_real,
                             "redundant_leg_null": nred_null,
                             "redundant_leg_null_mean": float(np.mean(nred_null))}
    print(f"  [PART A per-leg null] REDUNDANT leg: real trunk {nred_real}/{len(dd2fill)} vs "
          f"rotated-trunk null {nred_null} mean {np.mean(nred_null):.1f}", flush=True)
    rep["partA"] = {"n_fill_dd2": len(dd2fill), "n_dropped_real_trunk": len(drop),
                    "null_drops": nulls, "null_mean": float(np.mean(nulls)),
                    "selective": bool(len(drop) > 2 * np.mean(nulls) or
                                      (len(drop) >= 1 and np.mean(nulls) == 0))}
    print(f"  [PART A] dedup vs REAL trunk drops {len(drop)} of {len(dd2fill)} | "
          f"NULL (rotated trunk, {N_NULL} draws) drops {nulls} mean {np.mean(nulls):.1f}",
          flush=True)
    if not rep["partA"]["selective"]:
        print("  [PART A] NOT SELECTIVE -> rule NOT APPLIED, reported only", flush=True)
        fill = dd2fill
    else:
        fill = [dd2fill[i] for i in keepi]
        print(f"  [PART A] selective -> applied, fill {len(dd2fill)} -> {len(fill)}",
              flush=True)
    rep["partA"]["applied"] = bool(rep["partA"]["selective"])

    # ================= assemble + join-aware endpoint flags ============================
    merged_raw = [V.copy() for V in trunk] + [V.copy() for V in fill]
    merged, n_snap = snap_endpoints(merged_raw, px_to_world(SNAP_PX, zmed, f))
    # an endpoint is a JOIN iff the snap moved it onto a shared centroid
    open_end = []
    for V0, V1 in zip(merged_raw, merged):
        open_end.append((bool(np.allclose(V0[0], V1[0])), bool(np.allclose(V0[-1], V1[-1]))))
    n_join = sum(2 - int(a) - int(b) for a, b in open_end)
    arc = float(sum(np.sum(np.linalg.norm(np.diff(V, axis=0), axis=1)) for V in merged))
    prev = json.load(open(os.path.join(OUT, "dedebris2.json")))["merged"]
    rep["merged"] = {"n_strokes": len(merged), "n_trunk": len(trunk), "n_fill": len(fill),
                     "n_endpoint_snaps": int(n_snap), "n_join_endpoints": int(n_join),
                     "total_arc_world": arc, "dd2_arc": prev["total_arc_world"],
                     "trunk_arc": prev["trunk_arc"],
                     "arc_vs_trunk": arc / prev["trunk_arc"],
                     "arc_vs_dd2": arc / prev["total_arc_world"]}
    # persist the carrier of record so downstream renders draw EXACTLY these strokes
    np.savez(os.path.join(OUT, f"carrier_dd3_{SCENE}.npz"),
             pts=np.concatenate(merged, 0),
             offs=np.cumsum([0] + [len(V) for V in merged]),
             open_end=np.array(open_end, bool))
    print(f"  [assemble] {len(merged)} strokes, {n_join} join endpoints (no taper), "
          f"arc {arc:.3f} vs dd2 {prev['total_arc_world']:.3f} "
          f"(trunk {prev['trunk_arc']:.3f})", flush=True)

    # ================= PART B render ===================================================
    from src.mesh_oracle import MeshOracle                               # EVAL ONLY
    o = MeshOracle(SCENE, angle_deg=30.0)
    path = T.orbit_cameras(cams[5], cams[15], N_ORBIT, ctr)
    idx = list(range(STRIP0, STRIP0 + STRIP_N))
    imgs = []
    for k in idx:
        cam = path[k]
        gb = render.render_gbuffer(g, keep_g, cam)
        uvq = o.visible_crease_uv(cam, view_key=("dd3", SCENE, k))
        cm = np.zeros((cam.H, cam.W), bool)
        cm[np.clip(np.round(uvq[:, 1]).astype(int), 0, cam.H - 1),
           np.clip(np.round(uvq[:, 0]).astype(int), 0, cam.W - 1)] = True
        imgs.append(draw_runs(project_runs(merged, open_end, cam, gb["depth"]), cam, cm))
        del gb
    h = 460
    band = np.concatenate([cv2.resize((np.clip(im, 0, 1) * 255).astype(np.uint8), (h, h))
                           for im in imgs], 1)
    band = np.concatenate([np.full((44, band.shape[1], 3), 255, np.uint8), band], 0)
    cv2.putText(band, f"{SCENE} dd3  frames {idx[0]}-{idx[-1]}/{N_ORBIT}  {len(merged)} "
                      f"strokes  constant screen-space width, taper only at open endpoints",
                (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 0, 0), 2, cv2.LINE_AA)
    p = lambda n: os.path.join(VIZ, f"stroke_{SCENE}_{n}.png")
    cv2.imwrite(p("dd3_strip"), band[:, :, ::-1])
    cv2.imwrite(p("dd3_still"), (np.clip(cv2.resize(imgs[0], (1700, 1700)), 0, 1) * 255
                                 ).astype(np.uint8)[:, :, ::-1])
    dd2 = cv2.imread(p("dd2_still"))
    cur = (np.clip(cv2.resize(imgs[0], (1700, 1700)), 0, 1) * 255).astype(np.uint8)[:, :, ::-1]
    if dd2 is not None:
        a_ = cv2.resize(dd2, (1700, 1700)).min(2) < 150
        b_ = cur.min(2) < 150
        d = np.ones((1700, 1700, 3), np.float32)
        d[a_] = (0.85, 0.15, 0.15); d[b_] = (0.15, 0.25, 0.85); d[a_ & b_] = (0.15,) * 3
        cv2.imwrite(p("dd3_diff_vs_dd2"), (d * 255).astype(np.uint8)[:, :, ::-1])
    print("  wrote dd3_still / dd3_strip / dd3_diff_vs_dd2", flush=True)

    if not A.no_temporal:
        ca.n_resample, ca.max_cand, ca.cand_radius, ca.match_thresh = 16, 6, 40.0, 3.0
        frames = [M.frame_data(g, keep_g, c, merged, ca) for c in path]
        m = M.sequence_metrics(frames, ca)
        rep["temporal_240"] = m
        a2, b2 = m["A"], m["B"]
        print(f"\n  dd3 temporal: P_pop {a2['P_pop']:.4f} = unmatched {a2['unmatched_frac']:.4f}"
              f" + cut {a2['cut_frac']:.4f} | ratio {b2['P_pop']/a2['P_pop']:.2f}x", flush=True)
    json.dump(rep, open(os.path.join(OUT, "dd3.json"), "w"), indent=1)
    print(f"  -> {os.path.join(OUT, 'dd3.json')}", flush=True)


if __name__ == "__main__":
    main()
