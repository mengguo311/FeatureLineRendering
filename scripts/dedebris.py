"""tier1/scripts/dedebris.py — de-debris the merge FILL strokes with an object-space support
gate.  The trunk is never touched.

Executes out/DEDEBRIS_SPEC.md.  *** MESH EVAL-ONLY: faint GT crease overlay only. ***

DESIGN NOTE, pushing back on one half of the spec.  The spec offers two support tests,
"local DexiNed-cloud density" AND/OR "lies on a depth or normal discontinuity".  The density
test is weak here by construction: the fill vertices ARE DexiNed cloud points, so it measures
the cloud's density around its own members, and a flat-face stub only exists because DexiNed
fired there in enough views to survive triangulation and 3-view support.  The discontinuity
test is the physically motivated one and is backed by measurement: on cadpartA the 2DGS normal
buffer detects 98.7% of the shipped pipeline's miss set while every vanilla buffer detects
under 9%.  So the DISCONTINUITY test is primary and density is computed and REPORTED beside
it, not used to gate.

THE THRESHOLD, and why it is not a fitted per-scene number.  The reference is the TRUNK, which
is already in the drawing and already trusted (STEP3 zero-knob, P 0.8139).  A fill stroke is
kept iff at least HALF its vertices carry as much geometric support as the MEDIAN TRUNK VERTEX
does.  Both halves are scale-relative: the level comes from the trusted set in the same scene,
and 0.5 is a majority-of-its-own-length rule -- what we draw must have evidence under most of
it.  No hand-set magnitude, nothing tuned to the picture.

RANSAC is left UNCHANGED at 0.80.  The wavy front-face stroke is not special-cased; if the
support gate does not remove it, that is reported as a negative.
"""
import argparse, json, os, sys
import cv2, numpy as np
from scipy.spatial import cKDTree

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1); sys.path.insert(0, os.path.join(TIER1, "scripts"))
from src import common, render, view_split, strokes, visibility, render2dgs   # noqa: E402
import temporal_m1b as T                                                # noqa: E402
import m1b_stroke_temporal as M                                         # noqa: E402
from strokeviz import chain_args, draw_strokes, N_ORBIT, STRIP0, STRIP_N, VIZ, SCENE
from mergeviz import (px_to_world, straight_ok, snap_endpoints, polyline_pts,
                      L_PX_TRUNKSCALE, GAP_PX, SNAP_PX, MIN_ARC_MULT, RANSAC_TOL_PX)

OUT = os.path.join(TIER1, "out")
SUPPORT_VIEWS = 20          # evenly spaced TRAIN views for the support field
SUPPORT_FRAC = 0.50         # majority-of-its-own-length rule
DENS_PX = 6.0               # reported-only density radius, pixel-anchored


def normal_disc(n, fg):
    n = n / (np.linalg.norm(n, axis=2, keepdims=True) + 1e-12)
    o = np.zeros(n.shape[:2], np.float32)
    for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0)):
        m = np.roll(n, (dy, dx), axis=(0, 1))
        o = np.maximum(o, np.degrees(np.arccos(np.abs((n * m).sum(2)).clip(0, 1))))
    return np.where(fg, o, 0.0)


def support_field(V, cams, views, g, keep_g, g2):
    """Median over visible TRAIN views of the 2DGS normal-discontinuity under each vertex."""
    acc = [[] for _ in range(len(V))]
    for v in views:
        cam = cams[v]
        gb = render.render_gbuffer(g, keep_g, cam)
        fg = (gb["alpha"].detach().cpu().numpy() > 0.5)
        gb2 = render2dgs.render_gbuffer_2dgs(g2[0], g2[1], cam, bg_white=g2[2])
        S = normal_disc(gb2["normal"].detach().cpu().numpy(), fg)
        vis, uv, _ = visibility.visible_mask(V, cam, gb["depth"])
        idx = np.where(vis)[0]
        if len(idx):
            u = np.clip(np.round(uv[idx, 0]).astype(int), 0, cam.W - 1)
            w = np.clip(np.round(uv[idx, 1]).astype(int), 0, cam.H - 1)
            s = S[w, u]
            for j, i in enumerate(idx):
                acc[i].append(s[j])
        del gb, gb2
    return np.array([np.median(a) if a else 0.0 for a in acc])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no_temporal", action="store_true")
    A = ap.parse_args()
    ca = chain_args()
    cams, _ = common.load_cameras(SCENE)
    g = common.load_gaussians(SCENE)
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    f = cams[0].K[0, 0]
    rep = {"scene": SCENE, "support_test": "2DGS normal-discontinuity, median over visible "
           "TRAIN views", "support_frac": SUPPORT_FRAC,
           "threshold_rule": "fill stroke kept iff >= 50% of its vertices carry support >= "
                             "the MEDIAN TRUNK VERTEX support (reference is the trusted "
                             "trunk in the same scene; nothing hand-set)"}

    trunk, tinfo = M.build_chains(SCENE, "svstep3", ca)
    print(f"  [trunk] {tinfo['n_strokes']} strokes (byte-identical, never gated)", flush=True)

    # ---- rebuild the merge fill exactly as before --------------------------------------
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
    dex = [Pk[c] for c in ch]
    tol = px_to_world(RANSAC_TOL_PX, zmed, f)
    minarc = MIN_ARC_MULT * lw
    dex2 = [V for V in dex
            if float(np.sum(np.linalg.norm(np.diff(V, axis=0), axis=1))) >= minarc
            and straight_ok(V, tol)]
    tr_pts = polyline_pts(trunk)
    ttree = cKDTree(tr_pts)
    gapw = px_to_world(GAP_PX, zmed, f)
    keepv = []
    for V in dex2:
        d, _ = ttree.query(V, k=1)
        m = d > gapw
        if m.any():
            keepv.append(V[m])
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
    Vk = Vfill[k2]
    fill = [V for V in (Vk[c] for c in ch2)
            if float(np.sum(np.linalg.norm(np.diff(V, axis=0), axis=1))) >= minarc
            and straight_ok(V, tol)]
    print(f"  [merge] fill strokes before gate: {len(fill)}", flush=True)

    # ---- the support gate ---------------------------------------------------------------
    g2r = render2dgs.load_2dgs(os.path.join(OUT, f"2dgs_{SCENE}"))
    g2 = (g2r[0], g2r[1], g2r[2].get("white_background", True))
    tv = list(view_split.TRAIN)[::max(1, len(view_split.TRAIN) // SUPPORT_VIEWS)][:SUPPORT_VIEWS]
    S_tr = support_field(tr_pts, cams, tv, g, keep_g, g2)
    ref = float(np.median(S_tr))
    lens = [len(V) for V in fill]
    S_fi = support_field(np.concatenate(fill, 0), cams, tv, g, keep_g, g2)
    off, fracs, keptf, dropf = 0, [], [], []
    for V, n in zip(fill, lens):
        s = S_fi[off:off + n]; off += n
        fr = float((s >= ref).mean())
        fracs.append(fr)
        (keptf if fr >= SUPPORT_FRAC else dropf).append(V)
    # reported-only: local cloud density
    dtree = cKDTree(Pk)
    dr = px_to_world(DENS_PX, zmed, f)
    dens_k = [float(np.mean([len(b) for b in dtree.query_ball_point(V, dr)])) for V in keptf]
    dens_d = [float(np.mean([len(b) for b in dtree.query_ball_point(V, dr)])) for V in dropf]
    rep["support"] = {"trunk_median_deg": ref,
                      "n_fill_before": len(fill), "n_kept": len(keptf), "n_dropped": len(dropf),
                      "kept_frac_median": float(np.median([f_ for f_, V in zip(fracs, fill)
                                                           if f_ >= SUPPORT_FRAC]) or 0),
                      "dropped_frac_median": float(np.median([f_ for f_, V in zip(fracs, fill)
                                                              if f_ < SUPPORT_FRAC]) or 0),
                      "reported_density_kept": float(np.median(dens_k)) if dens_k else None,
                      "reported_density_dropped": float(np.median(dens_d)) if dens_d else None}
    print(f"  [gate] trunk median support {ref:.2f} deg -> fill {len(fill)} -> "
          f"kept {len(keptf)}, dropped {len(dropf)}", flush=True)
    print(f"  [gate] REPORTED density kept {rep['support']['reported_density_kept']} vs "
          f"dropped {rep['support']['reported_density_dropped']}", flush=True)

    merged, n_snap = snap_endpoints([V.copy() for V in trunk] + [V.copy() for V in keptf],
                                    px_to_world(SNAP_PX, zmed, f))
    arc = float(sum(np.sum(np.linalg.norm(np.diff(V, axis=0), axis=1)) for V in merged))
    prev = json.load(open(os.path.join(OUT, "mergeviz.json")))["stages"]["merged"]
    rep["merged"] = {"n_strokes": len(merged), "n_trunk": len(trunk), "n_fill_kept": len(keptf),
                     "median_vertices": float(np.median([len(c) for c in merged])),
                     "n_endpoint_snaps": int(n_snap), "total_arc_world": arc,
                     "prev_merge_arc": prev["total_arc_world"],
                     "prev_merge_strokes": prev["n_strokes"],
                     "arc_vs_prev_merge": arc / prev["total_arc_world"],
                     "trunk_arc_world": prev["trunk_arc_world"],
                     "arc_vs_trunk": arc / prev["trunk_arc_world"]}
    print(f"  [merged] {len(merged)} strokes, arc {arc:.3f} "
          f"(prev merge {prev['total_arc_world']:.3f}, trunk {prev['trunk_arc_world']:.3f})",
          flush=True)

    # ---- render, identical camera + stroke settings -------------------------------------
    from src.mesh_oracle import MeshOracle                              # EVAL ONLY
    o = MeshOracle(SCENE, angle_deg=30.0)
    target = np.median(g["mu"][keep_g], axis=0)
    path = T.orbit_cameras(cams[5], cams[15], N_ORBIT, target)
    idx = list(range(STRIP0, STRIP0 + STRIP_N))
    imgs = []
    for k in idx:
        cam = path[k]
        fd = M.frame_data(g, keep_g, cam, merged, ca)
        uvq = o.visible_crease_uv(cam, view_key=("dd", SCENE, k))
        cm = np.zeros((cam.H, cam.W), bool)
        cm[np.clip(np.round(uvq[:, 1]).astype(int), 0, cam.H - 1),
           np.clip(np.round(uvq[:, 0]).astype(int), 0, cam.W - 1)] = True
        imgs.append(draw_strokes(fd["A"], cam, fd["depth"], crease=cm))
    h = 460
    band = np.concatenate([cv2.resize((np.clip(im, 0, 1) * 255).astype(np.uint8), (h, h))
                           for im in imgs], 1)
    band = np.concatenate([np.full((44, band.shape[1], 3), 255, np.uint8), band], 0)
    cv2.putText(band, f"{SCENE} DE-DEBRISED MERGE  consecutive orbit frames "
                      f"{idx[0]}-{idx[-1]}/{N_ORBIT}   {len(merged)} strokes "
                      f"({len(dropf)} fill strokes dropped by the support gate)",
                (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.68, (0, 0, 0), 2, cv2.LINE_AA)
    cv2.imwrite(os.path.join(VIZ, f"stroke_{SCENE}_merge_strip.png"), band[:, :, ::-1])
    cv2.imwrite(os.path.join(VIZ, f"stroke_{SCENE}_merge_still.png"),
                (np.clip(cv2.resize(imgs[0], (1700, 1700)), 0, 1) * 255
                 ).astype(np.uint8)[:, :, ::-1])
    # dedebris diff: kept black, DROPPED red, same camera
    cam0 = path[idx[0]]
    fd0 = M.frame_data(g, keep_g, cam0, merged, ca)
    fdd = M.frame_data(g, keep_g, cam0, dropf, ca) if dropf else {"A": []}
    base = draw_strokes(fd0["A"], cam0, fd0["depth"])
    dd = draw_strokes(fdd["A"], cam0, fd0["depth"], colour=(0.90, 0.10, 0.10), canvas=base)
    cv2.imwrite(os.path.join(VIZ, f"stroke_{SCENE}_dedebris_diff.png"),
                (np.clip(cv2.resize(dd, (1700, 1700)), 0, 1) * 255
                 ).astype(np.uint8)[:, :, ::-1])
    print("  wrote still / strip / dedebris_diff", flush=True)

    if not A.no_temporal:
        ca.n_resample, ca.max_cand, ca.cand_radius, ca.match_thresh = 16, 6, 40.0, 3.0
        frames = [M.frame_data(g, keep_g, c, merged, ca) for c in path]
        m = M.sequence_metrics(frames, ca)
        rep["temporal_240"] = m
        a_, b_ = m["A"], m["B"]
        rep["gate_cut_pass"] = bool(a_["cut_frac"] <= 0.0102)
        print(f"\n  DE-DEBRIS temporal: P_pop {a_['P_pop']:.4f} = unmatched "
              f"{a_['unmatched_frac']:.4f} + cut {a_['cut_frac']:.4f} | BASE {b_['P_pop']:.4f}"
              f" | ratio {b_['P_pop']/a_['P_pop']:.2f}x | cut bar 0.0102 -> "
              f"{'PASS' if rep['gate_cut_pass'] else 'FAIL'}", flush=True)
    json.dump(rep, open(os.path.join(OUT, "dedebris.json"), "w"), indent=1)
    print(f"  -> {os.path.join(OUT, 'dedebris.json')}", flush=True)


if __name__ == "__main__":
    main()
