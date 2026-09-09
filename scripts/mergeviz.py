"""tier1/scripts/mergeviz.py — STEP3 trunk + DexiNed gap-fill, visual-first.

Executes out/MERGE_RESULTS.md (plan frozen before this ran).

*** MESH EVAL-ONLY: faint GT crease overlay, plus P/R quoted from banked runs and REPORTED,
    NEVER GATED. ***

Reuse: clustering is the frozen strokes.chain_linelets_3d; per-frame projection with occlusion
splitting and the Canny baseline are the frozen m1b_stroke_temporal.frame_data; the temporal
numbers come from the frozen m1b_stroke_temporal.sequence_metrics. Only the merge and the
stroke rendering are new.
"""
import argparse, json, os, sys, types
import cv2, numpy as np
from scipy.spatial import cKDTree

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1); sys.path.insert(0, os.path.join(TIER1, "scripts"))
from src import common, render, view_split, strokes                     # noqa: E402
import temporal_m1b as T                                                # noqa: E402
import m1b_stroke_temporal as M                                         # noqa: E402
from strokeviz import (chain_args, draw_strokes, L_PX, CORE_W, TIP_W,    # noqa: E402
                       TAPER_PX, N_ORBIT, STRIP0, STRIP_N, VIZ, SCENE)

OUT = os.path.join(TIER1, "out")
L_PX_TRUNKSCALE = 8.632      # cadpart's OWN native pipeline half-length, matching the trunk
GAP_PX = 3.0                 # vertex-level gap fill, set from stroke width (px equivalent)
SNAP_PX = 6.0                # 3-D endpoint snap radius, px equivalent
SNAP_COS = 0.85              # snap only if endpoint tangents are NON-parallel (|cos| < this)
MIN_ARC_MULT = 4.0           # min-length: stroke must span >= 4 carrier lengths
RANSAC_INLIER = 0.80         # straightness: >= 80% of vertices within tol of the fitted line
RANSAC_TOL_PX = 2.5


def px_to_world(px, z, f):
    return px * z / f


def polyline_pts(chains):
    return np.concatenate(chains, 0) if chains else np.zeros((0, 3))


def straight_ok(V, tol):
    """RANSAC-lite straightness: fit the principal line, count inliers.
    DECLARED POLYHEDRON-SCOPE ASSUMPTION (see the plan)."""
    if len(V) < 3:
        return True
    c = V.mean(0)
    u, s, vt = np.linalg.svd(V - c, full_matrices=False)
    d = vt[0]
    r = (V - c) - np.outer((V - c) @ d, d)
    return float((np.linalg.norm(r, axis=1) <= tol).mean()) >= RANSAC_INLIER


def snap_endpoints(chains, rad, cos_max=SNAP_COS):
    """One 3-D pass over the WHOLE merged set. Endpoints within `rad` are snapped to their
    centroid, but ONLY when their tangents are non-parallel, so parallel chamfer edges are
    never welded together."""
    if not chains:
        return chains
    ends, meta = [], []
    for ci, V in enumerate(chains):
        if len(V) < 2:
            continue
        for k, tan in ((0, V[0] - V[1]), (len(V) - 1, V[-1] - V[-2])):
            n = np.linalg.norm(tan)
            ends.append(V[k]); meta.append((ci, k, tan / max(n, 1e-12)))
    if not ends:
        return chains
    E = np.array(ends)
    tree = cKDTree(E)
    groups = tree.query_ball_point(E, rad)
    out = [V.copy() for V in chains]
    done = np.zeros(len(E), bool)
    n_snap = 0
    for i, gset in enumerate(groups):
        if done[i] or len(gset) < 2:
            continue
        sel = [j for j in gset if not done[j]
               and abs(float(meta[i][2] @ meta[j][2])) < cos_max or j == i]
        if len(sel) < 2:
            continue
        c = E[sel].mean(0)
        for j in sel:
            ci, k, _ = meta[j]
            out[ci][k] = c
            done[j] = True
        n_snap += 1
    return out, n_snap


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no_temporal", action="store_true")
    args_cli = ap.parse_args()
    ca = chain_args()
    cams, _ = common.load_cameras(SCENE)
    g = common.load_gaussians(SCENE)
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    f = cams[0].K[0, 0]
    rep = {"scene": SCENE, "stages": {}}

    # ---- trunk: STEP3, untouched -------------------------------------------------------
    trunk, tinfo = M.build_chains(SCENE, "svstep3", ca)
    rep["stages"]["trunk_step3"] = tinfo
    print(f"  [trunk] {tinfo['n_strokes']} strokes", flush=True)

    # ---- stage 1: re-chain DexiNed at the TRUNK's object-space scale --------------------
    z = np.load(os.path.join(OUT, f"linelets_{SCENE}_svdexined_test.npz"))
    P, Tg, conf = z["p"], z["t"], z["inlier_ratio"]
    zmed = np.median([np.median((c.w2c[:3, :3] @ P.T).T[:, 2] + c.w2c[2, 3])
                      for c in [cams[v] for v in view_split.TRAIN]])
    Lbig = np.full(len(P), px_to_world(L_PX_TRUNKSCALE, zmed, f))
    ch, kept = strokes.chain_linelets_3d(P, Tg, Lbig, conf=conf, nms_radius_mult=ca.nms_mult,
                                         k=ca.knn, cos_tan=ca.cos_tan, cos_col=ca.cos_col,
                                         gap_mult=ca.gap_mult, min_nodes=ca.min_nodes)
    Pk = P[kept]
    dex = [Pk[c] for c in ch]
    rep["stages"]["dexined_rechained"] = {
        "L_px": L_PX_TRUNKSCALE, "median_l_world": float(Lbig[0]),
        "n_nms": int(kept.sum()), "n_strokes": len(dex),
        "median_vertices": float(np.median([len(c) for c in dex])) if dex else 0.0}
    print(f"  [stage1] DexiNed re-chained at L_px {L_PX_TRUNKSCALE}: "
          f"NMS {int(kept.sum())} -> {len(dex)} strokes "
          f"(was 29673 -> 4007)", flush=True)

    # ---- stage 2: min-length + straightness (DECLARED polyhedron scope) -----------------
    tol = px_to_world(RANSAC_TOL_PX, zmed, f)
    minarc = MIN_ARC_MULT * float(Lbig[0])
    dex2 = [V for V in dex
            if float(np.sum(np.linalg.norm(np.diff(V, axis=0), axis=1))) >= minarc
            and straight_ok(V, tol)]
    rep["stages"]["dexined_filtered"] = {"n_strokes": len(dex2),
                                         "min_arc_world": minarc,
                                         "ransac_tol_world": tol}
    print(f"  [stage2] min-length+straightness: {len(dex)} -> {len(dex2)} strokes", flush=True)

    # ---- stage 3: vertex-level gap fill against the untouched trunk --------------------
    tr_pts = polyline_pts(trunk)
    ttree = cKDTree(tr_pts) if len(tr_pts) else None
    gapw = px_to_world(GAP_PX, zmed, f)
    keepv, tot = [], 0
    for V in dex2:
        tot += len(V)
        if ttree is None:
            keepv.append(V); continue
        d, _ = ttree.query(V, k=1)
        m = d > gapw
        if m.any():
            keepv.append(V[m])
    Vfill = np.concatenate(keepv, 0) if keepv else np.zeros((0, 3))
    print(f"  [stage3] gap fill > {GAP_PX}px: {len(Vfill)} of {tot} DexiNed vertices kept",
          flush=True)
    fill = []
    if len(Vfill) >= ca.min_nodes:
        tf = cKDTree(Vfill)
        _, nb = tf.query(Vfill, k=min(11, len(Vfill)))
        Tf = np.zeros_like(Vfill)
        for i in range(len(Vfill)):
            Q = Vfill[nb[i, 1:]] - Vfill[i]
            _, _, vt = np.linalg.svd(Q - Q.mean(0), full_matrices=False)
            Tf[i] = vt[0]
        Lf = np.full(len(Vfill), float(Lbig[0]))
        ch2, k2 = strokes.chain_linelets_3d(Vfill, Tf, Lf, nms_radius_mult=ca.nms_mult,
                                            k=ca.knn, cos_tan=ca.cos_tan,
                                            cos_col=ca.cos_col, gap_mult=ca.gap_mult,
                                            min_nodes=ca.min_nodes)
        Vk = Vfill[k2]
        fill = [Vk[c] for c in ch2]
        fill = [V for V in fill
                if float(np.sum(np.linalg.norm(np.diff(V, axis=0), axis=1))) >= minarc
                and straight_ok(V, tol)]
    rep["stages"]["fill"] = {"n_vertices_kept": int(len(Vfill)), "n_strokes": len(fill)}
    print(f"  [stage3] filler strokes: {len(fill)}", flush=True)

    # ---- stage 4: one 3-D endpoint snap over the WHOLE merged set ----------------------
    merged = [V.copy() for V in trunk] + [V.copy() for V in fill]
    merged, n_snap = snap_endpoints(merged, px_to_world(SNAP_PX, zmed, f))
    arc = float(sum(np.sum(np.linalg.norm(np.diff(V, axis=0), axis=1)) for V in merged))
    arc_t = float(sum(np.sum(np.linalg.norm(np.diff(V, axis=0), axis=1)) for V in trunk))
    rep["stages"]["merged"] = {
        "n_strokes": len(merged), "n_trunk": len(trunk), "n_fill": len(fill),
        "median_vertices": float(np.median([len(c) for c in merged])),
        "n_endpoint_snaps": int(n_snap),
        "total_arc_world": arc, "trunk_arc_world": arc_t,
        "arc_gain_vs_trunk": arc / max(arc_t, 1e-9)}
    print(f"  [stage4] merged {len(merged)} strokes ({len(trunk)} trunk + {len(fill)} fill), "
          f"{n_snap} endpoint snaps, arc {arc:.3f} vs trunk {arc_t:.3f} "
          f"({arc/max(arc_t,1e-9):.2f}x)", flush=True)

    # ---- render: identical camera + identical stroke settings --------------------------
    from src.mesh_oracle import MeshOracle                              # EVAL ONLY
    o = MeshOracle(SCENE, angle_deg=30.0)
    target = np.median(g["mu"][keep_g], axis=0)
    path = T.orbit_cameras(cams[5], cams[15], N_ORBIT, target)
    idx = list(range(STRIP0, STRIP0 + STRIP_N))
    imgs = []
    for k in idx:
        cam = path[k]
        fd = M.frame_data(g, keep_g, cam, merged, ca)
        uvq = o.visible_crease_uv(cam, view_key=("mg", SCENE, k))
        cm = np.zeros((cam.H, cam.W), bool)
        cm[np.clip(np.round(uvq[:, 1]).astype(int), 0, cam.H - 1),
           np.clip(np.round(uvq[:, 0]).astype(int), 0, cam.W - 1)] = True
        imgs.append(draw_strokes(fd["A"], cam, fd["depth"], crease=cm))
    h = 460
    band = np.concatenate([cv2.resize((np.clip(im, 0, 1) * 255).astype(np.uint8), (h, h))
                           for im in imgs], 1)
    pad = np.full((44, band.shape[1], 3), 255, np.uint8)
    band = np.concatenate([pad, band], 0)
    cv2.putText(band, f"{SCENE} MERGE (STEP3 trunk + DexiNed gap-fill)  consecutive orbit "
                      f"frames {idx[0]}-{idx[-1]}/{N_ORBIT}   {len(merged)} strokes",
                (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (0, 0, 0), 2, cv2.LINE_AA)
    p_strip = os.path.join(VIZ, f"stroke_{SCENE}_merge_strip.png")
    cv2.imwrite(p_strip, band[:, :, ::-1])
    p_still = os.path.join(VIZ, f"stroke_{SCENE}_merge_still.png")
    cv2.imwrite(p_still, (np.clip(cv2.resize(imgs[0], (1700, 1700)), 0, 1) * 255
                          ).astype(np.uint8)[:, :, ::-1])
    a_, b_ = imgs[0], imgs[1]
    ia, ib = (a_.min(2) < 0.6), (b_.min(2) < 0.6)
    diff = np.ones(a_.shape, np.float32)
    diff[ia] = (0.85, 0.15, 0.15); diff[ib] = (0.15, 0.25, 0.85); diff[ia & ib] = (0.15,) * 3
    p_diff = os.path.join(VIZ, f"stroke_{SCENE}_merge_diff.png")
    cv2.imwrite(p_diff, (np.clip(cv2.resize(diff, (1700, 1700)), 0, 1) * 255
                         ).astype(np.uint8)[:, :, ::-1])
    print(f"  wrote {p_strip}\n  wrote {p_still}\n  wrote {p_diff}", flush=True)

    # ---- temporal, frozen operator -----------------------------------------------------
    if not args_cli.no_temporal:
        ca.n_resample, ca.max_cand, ca.cand_radius, ca.match_thresh = 16, 6, 40.0, 3.0
        frames = [M.frame_data(g, keep_g, c, merged, ca)
                  for c in T.orbit_cameras(cams[5], cams[15], N_ORBIT, target)]
        m = M.sequence_metrics(frames, ca)
        rep["temporal_240"] = m
        A, B = m["A"], m["B"]
        print(f"\n  MERGE temporal: P_pop {A['P_pop']:.4f} = unmatched "
              f"{A['unmatched_frac']:.4f} + cut {A['cut_frac']:.4f} | BASE "
              f"{B['P_pop']:.4f} | ratio {B['P_pop']/A['P_pop']:.2f}x", flush=True)
        rep["gate_cut_bar"] = 0.0102
        rep["gate_cut_pass"] = bool(A["cut_frac"] <= 0.0102)
        print(f"  cut {A['cut_frac']:.4f} vs bar 0.0102 -> "
              f"{'PASS' if rep['gate_cut_pass'] else 'FAIL'}", flush=True)
    json.dump(rep, open(os.path.join(OUT, "mergeviz.json"), "w"), indent=1)
    print(f"  -> {os.path.join(OUT, 'mergeviz.json')}", flush=True)


if __name__ == "__main__":
    main()
