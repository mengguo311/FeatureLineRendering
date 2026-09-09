"""tier1/scripts/dedebris2.py — DE-DEBRIS v2: cross-stroke dihedral gate on the merge fill.

Executes out/DEDEBRIS_V2_SPEC.md, frozen before this ran.  Trunk byte-identical, never gated.
*** MESH EVAL-ONLY: faint GT crease overlay only. ***

The v1 gate failed because it measured evidence STRENGTH, and the fill exists precisely
because its evidence is weak.  This measures WHAT THE STROKE SITS ON: the frozen two-sided
ribbon estimator samples the surface normal on BOTH sides of the stroke, so a flat face reads
near zero however bright the edge response was.  Threshold is the project's own shipped crease
definition, 30 deg, which lies below every named feature's GT dihedral (40.89 minimum) and far
above a flat face (0).
"""
import argparse, json, os, sys, types
import cv2, numpy as np
from scipy.spatial import cKDTree

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1); sys.path.insert(0, os.path.join(TIER1, "scripts"))
from src import common, render, view_split, strokes, render2dgs          # noqa: E402
import temporal_m1b as T                                                 # noqa: E402
import m1b_stroke_temporal as M                                          # noqa: E402
import diag2dgs                                                          # noqa: E402
from strokeviz import chain_args, draw_strokes, N_ORBIT, STRIP0, STRIP_N, VIZ, SCENE
from mergeviz import (px_to_world, straight_ok, snap_endpoints, polyline_pts,
                      L_PX_TRUNKSCALE, GAP_PX, SNAP_PX, MIN_ARC_MULT, RANSAC_TOL_PX)

OUT = os.path.join(TIER1, "out")
TAU_CREASE_DEG = 30.0      # the project's shipped crease definition (mesh_oracle angle_deg)
SUPPORT_FRAC = 0.50
N_SUP_VIEWS = 20


class Shim:
    pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no_temporal", action="store_true")
    A = ap.parse_args()
    ca = chain_args()
    cams, _ = common.load_cameras(SCENE)
    g = common.load_gaussians(SCENE)
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    f = cams[0].K[0, 0]
    rep = {"scene": SCENE, "test": "two-sided cross-stroke dihedral (frozen "
           "gate2dgs.ribbon_normal_theta via diag2dgs.ribbon_dihedral) on the 2DGS normal "
           "buffer", "tau_deg": TAU_CREASE_DEG, "support_frac": SUPPORT_FRAC}

    trunk, tinfo = M.build_chains(SCENE, "svstep3", ca)
    print(f"  [trunk] {tinfo['n_strokes']} strokes, byte-identical, never gated", flush=True)

    # ---- rebuild the 70-stroke merge fill, unchanged -----------------------------------
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
    tol, minarc = px_to_world(RANSAC_TOL_PX, zmed, f), MIN_ARC_MULT * lw
    dex2 = [V for V in (Pk[c] for c in ch)
            if float(np.sum(np.linalg.norm(np.diff(V, axis=0), axis=1))) >= minarc
            and straight_ok(V, tol)]
    ttree = cKDTree(polyline_pts(trunk))
    gapw = px_to_world(GAP_PX, zmed, f)
    keepv = []
    for V in dex2:
        d, _ = ttree.query(V, k=1)
        if (d > gapw).any():
            keepv.append(V[d > gapw])
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
            and straight_ok(Vk[c], tol)]
    fill = [Vk[c] for c in fidx]
    print(f"  [merge] fill strokes before gate: {len(fill)} (the banked 70-stroke merge)",
          flush=True)

    # ---- the v2 gate: two-sided cross-stroke dihedral, frozen estimator ----------------
    g2r = render2dgs.load_2dgs(os.path.join(OUT, f"2dgs_{SCENE}"))
    g2, pipe2, meta2 = g2r
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
    off, keptf, dropf, fr_k, fr_d = 0, [], [], [], []
    for c in fidx:
        n = len(c)
        s = th[off:off + n]; off += n
        fr = float(np.nanmean(s >= TAU_CREASE_DEG))
        (keptf if fr >= SUPPORT_FRAC else dropf).append(Vk[c])
        (fr_k if fr >= SUPPORT_FRAC else fr_d).append(fr)
    rep["gate"] = {"n_fill_before": len(fill), "n_kept": len(keptf), "n_dropped": len(dropf),
                   "median_frac_kept": float(np.median(fr_k)) if fr_k else None,
                   "median_frac_dropped": float(np.median(fr_d)) if fr_d else None,
                   "median_theta_all_deg": float(np.nanmedian(th))}
    print(f"  [gate v2] tau {TAU_CREASE_DEG} deg -> fill {len(fill)} -> kept {len(keptf)}, "
          f"dropped {len(dropf)}  (median theta {np.nanmedian(th):.2f} deg)", flush=True)

    merged, n_snap = snap_endpoints([V.copy() for V in trunk] + [V.copy() for V in keptf],
                                    px_to_world(SNAP_PX, zmed, f))
    arc = float(sum(np.sum(np.linalg.norm(np.diff(V, axis=0), axis=1)) for V in merged))
    prev = json.load(open(os.path.join(OUT, "mergeviz.json")))["stages"]["merged"]
    rep["merged"] = {"n_strokes": len(merged), "n_trunk": len(trunk),
                     "n_fill_kept": len(keptf), "n_endpoint_snaps": int(n_snap),
                     "median_vertices": float(np.median([len(c) for c in merged])),
                     "total_arc_world": arc, "merge70_arc": prev["total_arc_world"],
                     "trunk_arc": prev["trunk_arc_world"],
                     "arc_vs_merge70": arc / prev["total_arc_world"],
                     "arc_vs_trunk": arc / prev["trunk_arc_world"]}
    print(f"  [merged] {len(merged)} strokes, arc {arc:.3f} vs merge70 "
          f"{prev['total_arc_world']:.3f} vs trunk {prev['trunk_arc_world']:.3f}", flush=True)

    # ---- render ------------------------------------------------------------------------
    from src.mesh_oracle import MeshOracle                               # EVAL ONLY
    o = MeshOracle(SCENE, angle_deg=30.0)
    target = np.median(g["mu"][keep_g], axis=0)
    path = T.orbit_cameras(cams[5], cams[15], N_ORBIT, target)
    idx = list(range(STRIP0, STRIP0 + STRIP_N))
    imgs = []
    for k in idx:
        cam = path[k]
        fd = M.frame_data(g, keep_g, cam, merged, ca)
        uvq = o.visible_crease_uv(cam, view_key=("d2", SCENE, k))
        cm = np.zeros((cam.H, cam.W), bool)
        cm[np.clip(np.round(uvq[:, 1]).astype(int), 0, cam.H - 1),
           np.clip(np.round(uvq[:, 0]).astype(int), 0, cam.W - 1)] = True
        imgs.append(draw_strokes(fd["A"], cam, fd["depth"], crease=cm))
    h = 460
    band = np.concatenate([cv2.resize((np.clip(im, 0, 1) * 255).astype(np.uint8), (h, h))
                           for im in imgs], 1)
    band = np.concatenate([np.full((44, band.shape[1], 3), 255, np.uint8), band], 0)
    cv2.putText(band, f"{SCENE} DE-DEBRIS v2 (cross-stroke dihedral >= {TAU_CREASE_DEG:.0f} deg)"
                      f"  frames {idx[0]}-{idx[-1]}/{N_ORBIT}  {len(merged)} strokes, "
                      f"{len(dropf)} fill dropped", (12, 30), cv2.FONT_HERSHEY_SIMPLEX,
                0.66, (0, 0, 0), 2, cv2.LINE_AA)
    p = lambda n: os.path.join(VIZ, f"stroke_{SCENE}_{n}.png")
    cv2.imwrite(p("dd2_strip"), band[:, :, ::-1])
    cv2.imwrite(p("dd2_still"), (np.clip(cv2.resize(imgs[0], (1700, 1700)), 0, 1) * 255
                                 ).astype(np.uint8)[:, :, ::-1])
    cam0 = path[idx[0]]
    fd0 = M.frame_data(g, keep_g, cam0, merged, ca)
    # diff vs the 70-stroke merge: kept black, DROPPED fill red
    fdd = M.frame_data(g, keep_g, cam0, dropf, ca) if dropf else {"A": []}
    d1 = draw_strokes(fdd["A"], cam0, fd0["depth"], colour=(0.90, 0.10, 0.10),
                      canvas=draw_strokes(fd0["A"], cam0, fd0["depth"]))
    cv2.imwrite(p("dd2_diff_vs_merge70"), (np.clip(cv2.resize(d1, (1700, 1700)), 0, 1) * 255
                                           ).astype(np.uint8)[:, :, ::-1])
    # diff vs STEP3-only: trunk black, KEPT fill green
    fdt = M.frame_data(g, keep_g, cam0, trunk, ca)
    fdk = M.frame_data(g, keep_g, cam0, keptf, ca) if keptf else {"A": []}
    d2 = draw_strokes(fdk["A"], cam0, fd0["depth"], colour=(0.05, 0.65, 0.10),
                      canvas=draw_strokes(fdt["A"], cam0, fd0["depth"]))
    cv2.imwrite(p("dd2_diff_vs_step3"), (np.clip(cv2.resize(d2, (1700, 1700)), 0, 1) * 255
                                         ).astype(np.uint8)[:, :, ::-1])
    print("  wrote dd2_still / dd2_strip / dd2_diff_vs_merge70 / dd2_diff_vs_step3",
          flush=True)

    if not A.no_temporal:
        ca.n_resample, ca.max_cand, ca.cand_radius, ca.match_thresh = 16, 6, 40.0, 3.0
        frames = [M.frame_data(g, keep_g, c, merged, ca) for c in path]
        m = M.sequence_metrics(frames, ca)
        rep["temporal_240"] = m
        a_, b_ = m["A"], m["B"]
        rep["cut_pass"] = bool(a_["cut_frac"] <= 0.0102)
        print(f"\n  v2 temporal: P_pop {a_['P_pop']:.4f} = unmatched {a_['unmatched_frac']:.4f}"
              f" + cut {a_['cut_frac']:.4f} | ratio {b_['P_pop']/a_['P_pop']:.2f}x | "
              f"cut bar 0.0102 -> {'PASS' if rep['cut_pass'] else 'FAIL'}", flush=True)
    json.dump(rep, open(os.path.join(OUT, "dedebris2.json"), "w"), indent=1)
    print(f"  -> {os.path.join(OUT, 'dedebris2.json')}", flush=True)


if __name__ == "__main__":
    main()
