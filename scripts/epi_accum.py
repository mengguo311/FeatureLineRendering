#!/usr/bin/env python
"""EPIPOLAR ACCUMULATION TEST — closed-form kill-test for the LINE-BUFFER pivot.

*** EVAL / ANALYSIS ONLY.  The GT mesh is read for LABELS (M_miss / M_flat point sets, their
    TEST-view visibility, and the image-space crease distance used ONLY to define a clean
    negative-class arm) and never enters the feature.  The FEATURE (occlusion-aware multi-view
    accumulation of RAW DexiNed probability through the frozen 3DGS depth) is mesh-free. ***

QUESTION (frozen, tier1/epipolar_accum_spec.md)
    A line-buffer trained on DexiNed edges can at best learn what the multi-view projection
    loss can see.  Its mathematical upper bound is the occlusion-aware multi-view MEAN of the
    RAW, UN-thresholded DexiNed probability at the true 3D crease location.  So: at the GT
    creases the frozen single-view-thresholded pipeline MISSED (M_miss), does that mean
    separate them from genuinely flat GT surface (M_flat)?
        GO      AUC >= 0.80 AND Recall@85%Prec >= 0.55
        NO-GO   AUC <= 0.65 OR  Recall@85%Prec <= 0.42
        else    MARGINAL

WHAT IS REUSED (nothing re-invented)
    * RAW DexiNed maps  : out/dexined_edges_<scene>/v###.npz, keys native / ms. Written by
                          scripts/cmepi_cache_edges.py as sigmoid(fused logits), float16, NO
                          threshold, NO NMS, NO contrast stretch.  Continuity asserted here.
    * M_miss            : Experiment X's banked miss-set (out/xy/xy_expX_<scene><tag>.npz:
                          seen_idx / rec3 / theta0_pt) over cache/dexp0_gt_<scene>_a30.npz.
                          = GT crease points visible in >=1 TEST view with NO point of the
                          frozen triangulated cloud (DexiNed native >= 0.5, NMS, K=6
                          neighbours, support>=2) within the 1.5px-equivalent radius.
    * cameras / proj    : src.common.load_cameras / project.
    * 3DGS depth        : src.render.render_gbuffer (mean depth + median depth), de-floatered
                          exactly as the pipeline does.
    * visibility rule   : src.visibility.visible_mask's rule, vectorised over [N,100]:
                          visible iff z <= min3x3(zbuf) + eps_rel * z, zbuf looked up at
                          round(K-projection) (the G-buffer's own pixel convention).  The
                          pipeline's eps_rel = 0.02 is the headline; 0.005 is the tight arm.
    * pixel convention  : src.tri_edges' photo-index = K-projection - 0.5 (halfpix) for the
                          DexiNed maps.  Not assumed: CALIBRATED on the HIT-set (recovered
                          creases, disjoint from both test classes) by maximising their mean
                          DexiNed response over a 5x5 grid of sub-pixel offsets.
    * detection proxy   : src.tri_edges.edge_dt (NMS-thinned native >= 0.5, L2 distance
                          transform) sampled at the point, <= 1.5 px — EXACTLY the frozen 2D
                          stage's detection rule.

LABELS (mesh EVAL-ONLY) — and the topology trap they must avoid
    The NeRF-synthetic OBJs carry v/vt/vn triplets; trimesh keeps one vertex per unique
    triplet, so every hard-shaded crease / UV seam is an OPEN BOUNDARY edge with NO face
    adjacency.  A flat rule built on face_adjacency alone (the first version of this script)
    let 71% (lego) / 59% (chair) of the "flat" points sit within 3 px of a real sharp edge.
    The flat exclusion set is therefore built on a POSITION-MERGED copy of the mesh:
        E_geo10 = merged-mesh edges with dihedral >= 10 deg  U  boundary (1-face) edges
                  U  non-manifold (>2-face) edges           (superset of any GT crease)
    M_flat = area-uniform surface samples with d(E_geo10) > margin (default 3 px-equiv = the
    project's 2*tau negative convention), visible in >=1 TEST view under the SAME mesh-depth
    rule that defined M_miss (3x3 min |dz| < 0.015).  A larger pool is kept so the margin can
    be SWEPT (3 / 4.5 / 6 / 8 px) and an IMAGE-SPACE arm (per-view distance to any projected
    crease-like edge > m px) can be evaluated.  |M_flat| = |M_miss| for the headline.
    The same artefact means the banked a30 crease set is the subset of geometric >=30 deg
    edges that share vertex indices across the crease (~40%).  The pre-registered positive
    class is kept as the headline; a GEOMETRIC-a30 miss-set arm (merged mesh, same visibility
    and recall rule as scripts/xy_expX.py against the same frozen cloud) is reported beside it.

FEATURE
    For every point and every one of the 100 views k: (u,v) = pi_k(x), z_k(x); vis_k = 3DGS
    depth test; P_k = RAW DexiNed sampled BILINEARLY at (u,v) [headline] and max over the 3x3
    pixel neighbourhood (= within 1.5 px) [dilated arm].   S_bar(x) = mean_{k: vis_k} P_k.
    Robust arms: median, 10% trimmed mean, top-quartile mean, max (= any-view), mean of
    logits, and mean excluding views where x projects within 3 px of a 3DGS depth
    discontinuity (mesh-free silhouette peel).

USAGE
    python scripts/epi_accum.py --scene lego --stage all     (labels -> gbuf -> accum -> eval)
"""
import argparse
import hashlib
import itertools
import json
import os
import sys
import time

import cv2
import numpy as np
import torch
from scipy.spatial import cKDTree

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
from src import common, render, view_split          # noqa: E402  METHOD-PATH, mesh-free

OUT = os.path.join(TIER1, "out", "epi")
CACHE = os.path.join(TIER1, "cache")
XY = os.path.join(TIER1, "out", "xy")
EDGES = os.path.join(TIER1, "out", "dexined_edges_{scene}")
MESH_DIR = os.path.expanduser("~/3dgs_line/bcr/meshes/NeRF_Mesh")
DS, ANGLE = 0.0015, 30.0            # mesh_oracle sampling step / crease threshold
FLAT_EDGE_DEG = 10.0                # "flat" = far from ANY geometric edge >= this dihedral
MESH_VIS_EPS = 0.015                # gt_labels' mesh-depth visibility eps (same rule)
TAGS = {"lego": "_p1c", "chair": "_ref40"}
CLOUDS = {"lego": "dexprimary_p1c_cloud_lego.npz", "chair": "dexprimary_p1b_cloud_chair_ref40.npz"}
TEST, TRAIN = list(view_split.TEST), list(view_split.TRAIN)
H = W = 800
NV = 100
GO = {"auc": 0.80, "r85": 0.55}
NOGO = {"auc": 0.65, "r85": 0.42}
KERN3 = np.ones((3, 3), np.uint8)
MARGINS_PX = (3.0, 4.5, 6.0, 8.0)   # 3D flat-margin sweep (px-equiv at crease median depth)
IMG_MARGINS_PX = (3, 5, 8)          # image-space clean-negative arm (per-view, all 100 views)
TAG = ""


def log(msg):
    print(msg, flush=True)


def script_md5():
    return hashlib.md5(open(os.path.abspath(__file__), "rb").read()).hexdigest()


# ============================================================ STAGE A — LABELS (mesh EVAL-ONLY)
def sample_edges_vec(V, pairs, ds, weights=None):
    """Vectorised replica of mesh_oracle._sample_edges (linspace(0,1,max(2,int(L/ds)+1))).
    Returns the samples and, if weights is given, the per-sample repeat of weights."""
    if len(pairs) == 0:
        return (np.zeros((0, 3)), np.zeros(0)) if weights is not None else np.zeros((0, 3))
    A, B = V[pairs[:, 0]], V[pairs[:, 1]]
    L = np.linalg.norm(B - A, axis=1)
    n = np.maximum(2, (L / ds).astype(int) + 1)
    eid = np.repeat(np.arange(len(n)), n)
    start = np.concatenate([[0], np.cumsum(n)[:-1]])
    local = np.arange(n.sum()) - start[eid]
    t = local / (n[eid] - 1)
    pts = A[eid] + t[:, None] * (B[eid] - A[eid])
    if weights is None:
        return pts
    return pts, np.repeat(weights, n)


def mesh_visible(pts, cam, depth, eps=MESH_VIS_EPS):
    """EXACTLY scripts/dexprimary_p0.gt_labels' rule: round(uv) in-bounds and 3x3 min |dz|<eps."""
    c = (cam.w2c[:3, :3] @ pts.T).T + cam.w2c[:3, 3]
    z = c[:, 2]
    uv = (cam.K @ c.T).T
    uv = uv[:, :2] / np.clip(uv[:, 2:3], 1e-9, None)
    ui = np.round(uv[:, 0]).astype(np.int64)
    vi = np.round(uv[:, 1]).astype(np.int64)
    inb = (z > 0) & (ui >= 0) & (ui < W) & (vi >= 0) & (vi < H)
    idx = np.where(inb)[0]
    best = np.full(len(idx), 1e9)
    for du in (-1, 0, 1):
        for dv in (-1, 0, 1):
            uu = np.clip(ui[idx] + du, 0, W - 1)
            vv = np.clip(vi[idx] + dv, 0, H - 1)
            best = np.minimum(best, np.abs(z[idx] - depth[vv, uu]))
    vis = np.zeros(len(pts), bool)
    vis[idx] = best < eps
    return vis


def merged_edge_sets(m):
    """Position-merged topology of the OBJ.  Returns (V2, adjE2, deg2, boundary_pairs,
    nonmanifold_pairs) so that hard-shaded creases / UV seams are real edges, not holes."""
    m2 = m.copy()
    m2.merge_vertices(merge_tex=True, merge_norm=True)
    V2 = np.asarray(m2.vertices, np.float64)
    adjE2 = np.asarray(m2.face_adjacency_edges)
    deg2 = np.degrees(np.asarray(m2.face_adjacency_angles))
    eu = np.asarray(m2.edges_unique)
    cnt = np.bincount(np.asarray(m2.edges_unique_inverse), minlength=len(eu))
    return V2, adjE2, deg2, eu[cnt == 1], eu[cnt > 2]


def stage_labels(scene, args):
    import trimesh
    from src.mesh_oracle import MeshOracle          # EVAL ONLY (labels)
    t0 = time.time()
    gt = np.load(os.path.join(CACHE, f"dexp0_gt_{scene}_a30.npz"))
    x = np.load(os.path.join(XY, f"xy_expX_{scene}{TAGS[scene]}.npz"))
    crease = gt["crease_pts"]
    seen_idx, rec3, th = x["seen_idx"], x["rec3"], x["theta0_pt"]
    radius = float(x["radius"])
    px_world = radius / 1.5                          # 1 px-equiv at the crease median depth
    miss_idx, hit_idx = seen_idx[~rec3], seen_idx[rec3]
    P_miss, th_miss = crease[miss_idx], th[~rec3]
    log(f"[A:{scene}] banked: crease_pts={len(crease)} seen={len(seen_idx)} miss={len(miss_idx)} "
        f"hit={len(hit_idx)} radius={radius:.6f} px_world={px_world:.6f}")

    pos = -np.ones(len(crease), np.int64)
    pos[miss_idx] = np.arange(len(miss_idx))
    tv_miss = np.zeros((len(miss_idx), len(TEST)), bool)
    for j, v in enumerate(TEST):
        p = pos[gt[f"idx{v}"]]
        tv_miss[p[p >= 0], j] = True
    assert tv_miss.any(1).all(), "every miss point must be TEST-visible by construction"

    rng = np.random.default_rng(args.seed)
    hs = np.sort(rng.choice(len(hit_idx), size=min(args.n_hit, len(hit_idx)), replace=False))
    hit_sub = hit_idx[hs]
    pos[:] = -1
    pos[hit_sub] = np.arange(len(hit_sub))
    tv_hit = np.zeros((len(hit_sub), len(TEST)), bool)
    for j, v in enumerate(TEST):
        p = pos[gt[f"idx{v}"]]
        tv_hit[p[p >= 0], j] = True

    # ---- mesh: split-vertex load (as mesh_oracle) + position-merged topology
    m = trimesh.load(os.path.join(MESH_DIR, f"{scene}_new.obj"), process=True)
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate([g for g in m.geometry.values()])
    n_adj_topo = len(m.face_adjacency_edges)
    n10_topo = int((np.degrees(np.asarray(m.face_adjacency_angles)) >= FLAT_EDGE_DEG).sum())
    V2, adjE2, deg2, bnd, nonm = merged_edge_sets(m)
    sel10 = deg2 >= FLAT_EDGE_DEG
    sel30 = deg2 >= ANGLE
    E_bn = np.concatenate([sample_edges_vec(V2, bnd, DS), sample_edges_vec(V2, nonm, DS)])
    E10 = np.concatenate([sample_edges_vec(V2, adjE2[sel10], DS), E_bn])
    E30, th30 = sample_edges_vec(V2, adjE2[sel30], DS, deg2[sel30])
    E_cl = np.concatenate([E30, E_bn])                 # crease-like: image-space negative gate
    tree10, tree_cl = cKDTree(E10), cKDTree(E_cl)
    tree_bank = cKDTree(crease)
    margin = args.margin_px * px_world
    log(f"[A:{scene}] mesh V={len(m.vertices)} F={len(m.faces)}; topological adj edges "
        f"{n_adj_topo} (>=10deg {n10_topo}) | MERGED: adj edges {len(adjE2)} (>=10deg "
        f"{int(sel10.sum())}, >=30deg {int(sel30.sum())}), boundary {len(bnd)}, non-manifold "
        f"{len(nonm)} -> E_geo10 {len(E10)} samples, E_geo30 {len(E30)}, crease-like {len(E_cl)}; "
        f"base margin {args.margin_px}px = {margin:.5f} world ({time.time()-t0:.0f}s)")
    d_bank_in_geo = cKDTree(E30).query(crease, k=1, workers=-1)[0]
    d_geo_in_bank = tree_bank.query(E30, k=1, workers=-1)[0]
    cov = {"n_banked_a30_samples": int(len(crease)), "n_geometric_a30_samples": int(len(E30)),
           "frac_banked_within_1e-4_of_geometric": float((d_bank_in_geo < 1e-4).mean()),
           "frac_geometric_within_1e-4_of_banked": float((d_geo_in_bank < 1e-4).mean())}
    log(f"[A:{scene}] banked a30 vs geometric a30: banked-in-geo {cov['frac_banked_within_1e-4_of_geometric']:.4f}, "
        f"geo-in-banked {cov['frac_geometric_within_1e-4_of_banked']:.4f}")

    # ---- TEST-view GT-mesh depth (same rasteriser that defined M_miss's visibility)
    cams, _ = common.load_cameras(scene)
    oracle = MeshOracle(scene, angle_deg=179.0, device=args.device)   # depth only
    tdepth = {}
    for v in TEST:
        tdepth[v] = oracle.render_depth(cams[v]).detach().cpu().numpy()
        oracle._depth_cache.clear()
        torch.cuda.empty_cache()
    log(f"[A:{scene}] GT-mesh depth for {len(TEST)} TEST views ({time.time()-t0:.0f}s)")

    # ---- GEOMETRIC-a30 miss-set arm: same visibility + recall rule as xy_expX.py, same cloud
    tv30 = np.stack([mesh_visible(E30, cams[v], tdepth[v]) for v in TEST], 1)
    seen30 = tv30.any(1)
    zc = np.load(os.path.join(TIER1, "out", CLOUDS[scene]))
    keep = (zc["support"] >= 2) & zc["surface_keep"] & (zc["resid"] <= 1.0)
    P_cloud = zc["P"][keep]
    n_kept_banked = int(json.load(open(os.path.join(XY, f"xy_expX_{scene}{TAGS[scene]}.json")))["n_cloud_kept"])
    assert len(P_cloud) == n_kept_banked, ("cloud keep rule drifted", len(P_cloud), n_kept_banked)
    d3g = cKDTree(P_cloud).query(E30[seen30], k=1, workers=-1)[0]
    rec3g = d3g <= radius
    in_bank = d_geo_in_bank[seen30] < 1e-4
    geo = {"n_seen": int(seen30.sum()), "recall_3D": float(rec3g.mean()), "n_miss": int((~rec3g).sum()),
           "recall_3D_on_banked_subset": float(rec3g[in_bank].mean()) if in_bank.any() else None,
           "recall_3D_on_non_banked_subset": float(rec3g[~in_bank].mean()) if (~in_bank).any() else None,
           "frac_seen_in_banked": float(in_bank.mean())}
    gi = np.where(seen30)[0][~rec3g]
    if len(gi) > args.n_geo:
        gi = np.sort(rng.choice(gi, size=args.n_geo, replace=False))
    P_geo, th_geo, tv_geo = E30[gi], th30[gi], tv30[gi]
    geo["n_arm"] = int(len(gi))
    log(f"[A:{scene}] GEOMETRIC a30: seen {geo['n_seen']} recall_3D {geo['recall_3D']:.4f} "
        f"(banked subset {geo['recall_3D_on_banked_subset']}, non-banked {geo['recall_3D_on_non_banked_subset']}) "
        f"miss {geo['n_miss']} -> arm {geo['n_arm']} ({time.time()-t0:.0f}s)")

    # ---- M_flat: area-uniform surface sampling -> geometric margin -> TEST visibility
    need = len(miss_idx)
    want = int(args.pool_mult * need)
    coll, total, it, rounds, n_have = [], 0, 0, [], 0
    while n_have < want and total < args.max_sample:
        pts, fidx = trimesh.sample.sample_surface(m, args.chunk, seed=args.seed * 1000 + it)
        it += 1
        pts = np.asarray(pts, np.float64)
        fidx = np.asarray(fidx)
        total += len(pts)
        d10 = tree10.query(pts, k=1, workers=-1)[0]
        k1 = d10 > margin
        pts1, f1, d1 = pts[k1], fidx[k1], d10[k1]
        tv = np.stack([mesh_visible(pts1, cams[v], tdepth[v]) for v in TEST], 1)
        k2 = tv.any(1)
        coll.append((pts1[k2], f1[k2], d1[k2], tv[k2]))
        n_have += int(k2.sum())
        rounds.append({"sampled": int(len(pts)), "pass_margin": int(k1.sum()),
                       "pass_margin_and_testvis": int(k2.sum())})
        log(f"[A:{scene}]   round {it}: sampled {len(pts)} -> geo-margin {k1.sum()} "
            f"({k1.mean():.4f}) -> TEST-visible {k2.sum()} | pool {n_have}/{want} "
            f"({time.time()-t0:.0f}s)")
    P_pool = np.concatenate([c[0] for c in coll])
    f_pool = np.concatenate([c[1] for c in coll])
    d10_pool = np.concatenate([c[2] for c in coll])
    tv_pool = np.concatenate([c[3] for c in coll])
    perm = rng.permutation(len(P_pool))
    P_flat, face_flat, d10_flat, tv_flat = P_pool[perm], f_pool[perm], d10_pool[perm], tv_pool[perm]
    dcl_flat = tree_cl.query(P_flat, k=1, workers=-1)[0]     # distance to crease-like edges
    dbank_flat = tree_bank.query(P_flat, k=1, workers=-1)[0]  # distance to the banked GT creases
    n_base = min(need, len(P_flat))
    n_miss_full = len(P_miss)
    if len(P_flat) < need:
        sub = np.sort(rng.choice(len(P_miss), size=len(P_flat), replace=False))
        log(f"[A:{scene}] flat pool {len(P_flat)} < miss {need}: subsampling M_miss to "
            f"{len(P_flat)} (uniform, seed {args.seed}) to keep the classes balanced")
        P_miss, th_miss, tv_miss, miss_idx = P_miss[sub], th_miss[sub], tv_miss[sub], miss_idx[sub]
    d10_miss = tree10.query(P_miss, k=1, workers=-1)[0]
    log(f"[A:{scene}] M_miss={len(P_miss)}  flat pool={len(P_flat)} (headline uses first {n_base}) "
        f"from {total} samples; flat d(E_geo10) px p5={np.percentile(d10_flat,5)/px_world:.2f} "
        f"p50={np.percentile(d10_flat,50)/px_world:.2f}; d(banked crease) px p5="
        f"{np.percentile(dbank_flat,5)/px_world:.2f}; pool by margin: "
        + ", ".join(f">={mp:g}px:{int((d10_flat > mp * px_world).sum())}" for mp in MARGINS_PX))

    os.makedirs(OUT, exist_ok=True)
    np.savez_compressed(
        os.path.join(OUT, f"epi_labels_{scene}{TAG}.npz"),
        P_miss=P_miss.astype(np.float64), miss_idx=miss_idx, th_miss=th_miss.astype(np.float32),
        tv_miss=tv_miss, d10_miss=d10_miss.astype(np.float32),
        P_flat=P_flat.astype(np.float64), face_flat=face_flat, d10_flat=d10_flat.astype(np.float32),
        dcl_flat=dcl_flat.astype(np.float32), dbank_flat=dbank_flat.astype(np.float32), tv_flat=tv_flat,
        n_base=n_base,
        P_geo=P_geo.astype(np.float64), th_geo=th_geo.astype(np.float32), tv_geo=tv_geo,
        P_hit=crease[hit_sub].astype(np.float64), hit_idx=hit_sub, tv_hit=tv_hit,
        E_cl=E_cl.astype(np.float32),
        px_world=px_world, radius=radius, margin=margin, margin_px=args.margin_px,
        flat_edge_deg=FLAT_EDGE_DEG, test_views=np.array(TEST))
    meta = {"scene": scene, "tag": TAG, "n_miss": int(len(P_miss)), "n_miss_full": int(n_miss_full),
            "n_flat_pool": int(len(P_flat)), "n_base": int(n_base), "n_geo_arm": int(len(P_geo)),
            "n_hit_calib": int(len(hit_sub)), "n_surface_samples": int(total), "rounds": rounds,
            "margin_px": args.margin_px, "margin_world": margin, "px_world": px_world,
            "flat_rule": f"d(merged-mesh edge with dihedral >= {FLAT_EDGE_DEG:g} deg, or boundary, or "
                         f"non-manifold edge) > margin AND visible in >=1 TEST view (mesh depth, 3x3 "
                         f"min |dz| < {MESH_VIS_EPS})",
            "mesh_topology": {"V_split": int(len(m.vertices)), "V_merged": int(len(V2)),
                              "adj_edges_split": int(n_adj_topo), "adj_edges_merged": int(len(adjE2)),
                              "edges_ge10_split": n10_topo, "edges_ge10_merged": int(sel10.sum()),
                              "edges_ge30_merged": int(sel30.sum()), "boundary_edges_merged": int(len(bnd)),
                              "nonmanifold_edges_merged": int(len(nonm))},
            "banked_vs_geometric_a30": cov, "geometric_a30_missset": geo,
            "flat_pool_by_margin_px": {f"{mp:g}": int((d10_flat > mp * px_world).sum()) for mp in MARGINS_PX},
            "flat_d_to_banked_crease_px_quantiles": {f"p{q}": float(np.percentile(dbank_flat, q) / px_world)
                                                     for q in (1, 5, 25, 50, 75, 95)},
            "flat_d_to_geo10_px_quantiles": {f"p{q}": float(np.percentile(d10_flat, q) / px_world)
                                             for q in (1, 5, 25, 50, 75, 95)},
            "miss_d_to_geo10_px_quantiles": {f"p{q}": float(np.percentile(d10_miss, q) / px_world)
                                             for q in (50, 95, 99)},
            "miss_theta_bands": {"exactly30": int(((th_miss >= 29.9) & (th_miss < 30.1)).sum()),
                                 ">=30.05": int((th_miss >= 30.05).sum()),
                                 ">=45": int((th_miss >= 45).sum()),
                                 "exactly90": int(((th_miss >= 89.9) & (th_miss < 90.1)).sum())},
            "seconds": time.time() - t0}
    json.dump(meta, open(os.path.join(OUT, f"epi_labels_{scene}{TAG}.json"), "w"), indent=1)
    log(f"[A:{scene}] wrote labels ({time.time()-t0:.0f}s)")


# ============================================================ STAGE B — 3DGS G-BUFFERS (method path)
def stage_gbuf(scene, args):
    t0 = time.time()
    g = common.load_gaussians(scene)
    keep = render.defloat_mask(g["mu"], g["opacity"])
    cams, _ = common.load_cameras(scene)
    dm = np.zeros((NV, H, W), np.float32)
    dmed = np.zeros((NV, H, W), np.float32)
    al = np.zeros((NV, H, W), np.float32)
    n_cpu = 0
    for v in range(NV):
        try:
            gb = render.render_gbuffer(g, keep, cams[v], device=args.device, with_median_depth=True)
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            n_cpu += 1
            gb = render.render_gbuffer(g, keep, cams[v], device="cpu", with_median_depth=True)
        dm[v] = gb["depth"].detach().cpu().numpy()
        dmed[v] = gb["depth_median"].detach().cpu().numpy()
        al[v] = gb["alpha"].detach().cpu().numpy()
        del gb
        torch.cuda.empty_cache()
        if v % 20 == 0:
            log(f"[B:{scene}] view {v:3d}  fg={float((al[v] > 0.5).mean()):.3f}  ({time.time()-t0:.0f}s)")
    np.savez_compressed(os.path.join(CACHE, f"epi_gbuf_{scene}.npz"), depth=dm, depth_median=dmed,
                        alpha=al, n_gauss=len(g["mu"]), n_keep=int(keep.sum()), n_cpu_fallback=n_cpu)
    log(f"[B:{scene}] gaussians {len(g['mu'])} kept {int(keep.sum())}; {NV} G-buffers "
        f"({n_cpu} on CPU) ({time.time()-t0:.0f}s)")


# ============================================================ STAGE C — ACCUMULATION (method path)
def load_map(scene, v, key):
    return np.load(os.path.join(EDGES.format(scene=scene), f"v{v:03d}.npz"))[key].astype(np.float32)


def remap(img, u, v, interp, cols=4096):
    """Sample img at continuous photo-index coords (u=column, v=row); integer coords are pixel
    centres in cv2.remap.  cv2.remap needs every map dimension < 32767, so the N points are
    laid out on a [rows, 4096] grid and padded with out-of-bounds coords (-> borderValue 0)."""
    n = len(u)
    rows = (n + cols - 1) // cols
    mu = np.full(rows * cols, -10.0, np.float32)
    mv = np.full(rows * cols, -10.0, np.float32)
    mu[:n] = u
    mv[:n] = v
    out = cv2.remap(img, mu.reshape(rows, cols), mv.reshape(rows, cols), interp,
                    borderMode=cv2.BORDER_CONSTANT, borderValue=0.0)
    return out.reshape(-1)[:n]


def calibrate_offset(scene, lab, cams, offsets):
    """Mean RAW DexiNed (bilinear) at the HIT-set creases in the TEST views where the mesh says
    they are visible, for each candidate (du,dv) photo-index offset.  Uses no test-class point."""
    P, tv = lab["P_hit"], lab["tv_hit"]
    maps = {v: load_map(scene, v, "native") for v in TEST}
    table = {}
    for (ou, ov) in offsets:
        num, den = 0.0, 0
        for j, v in enumerate(TEST):
            sel = tv[:, j]
            uv, z = common.project(P[sel], cams[v])
            u, vv = uv[:, 0] + ou, uv[:, 1] + ov
            inb = (z > 0) & (u >= 0) & (u <= W - 1) & (vv >= 0) & (vv <= H - 1)
            s = remap(maps[v], u, vv, cv2.INTER_LINEAR)
            num += float(s[inb].sum())
            den += int(inb.sum())
        table[(ou, ov)] = num / max(den, 1)
    return table


def stage_accum(scene, args):
    from src import tri_edges                        # METHOD PATH (mesh-free): edge_dt = NMS+thr+DT
    t0 = time.time()
    lab = np.load(os.path.join(OUT, f"epi_labels_{scene}{TAG}.npz"))
    gb = np.load(os.path.join(CACHE, f"epi_gbuf_{scene}.npz"))
    depth_all = gb["depth"]
    cams, _ = common.load_cameras(scene)
    P_all = np.concatenate([lab["P_miss"], lab["P_flat"], lab["P_geo"]])
    Nm, Nf, Ng = len(lab["P_miss"]), len(lab["P_flat"]), len(lab["P_geo"])
    N = len(P_all)
    cls = np.r_[np.ones(Nm, np.int8), np.zeros(Nf, np.int8), np.full(Ng, 2, np.int8)]
    E_cl = lab["E_cl"].astype(np.float64)

    probe = load_map(scene, TEST[0], "native")
    nuniq = len(np.unique(probe[::3, ::3]))
    sub = float(((probe > 0.02) & (probe < 0.5)).mean())
    assert nuniq > 500 and probe.max() <= 1.0 and probe.min() >= 0.0, "map is not continuous"
    log(f"[C:{scene}] RAW-map check v{TEST[0]}: unique values (1/9 sub-grid) = {nuniq}, "
        f"frac in (0.02,0.5) = {sub:.4f}, frac>=0.5 = {float((probe >= 0.5).mean()):.4f} "
        f"-> CONTINUOUS probability, not a thresholded mask")

    grid = [(a, b) for a in (-1.0, -0.5, 0.0, 0.5, 1.0) for b in (-1.0, -0.5, 0.0, 0.5, 1.0)]
    tab = calibrate_offset(scene, lab, cams, grid)
    best = max(tab, key=tab.get)
    off = best if args.offset == "auto" else tuple(float(t) for t in args.offset.split(","))
    log(f"[C:{scene}] offset calibration (mean RAW P at hit-set creases): "
        + "  ".join(f"({a:+.1f},{b:+.1f})={tab[(a, b)]:.4f}" for (a, b) in
                    [(-0.5, -0.5), (0.0, 0.0), (-1.0, -1.0), (0.5, 0.5), best]))
    log(f"[C:{scene}] best offset = {best} (tri_edges halfpix = (-0.5,-0.5)); USING {off}")

    keys = ["nat_bil", "nat_dil", "ms_bil", "ms_dil"]
    S = {k: np.zeros((N, NV), np.float16) for k in keys}
    VIS = {"loose": np.zeros((N, NV), bool), "tight": np.zeros((N, NV), bool)}
    INB = np.zeros((N, NV), bool)
    NOGEO = np.zeros((N, NV), bool)
    DET = np.zeros((N, NV), bool)                      # pipeline detection: NMS>=0.5 DT <= 1.5px
    DZ = np.zeros((N, NV), np.float16)
    Z = np.zeros((N, NV), np.float16)
    SILD = np.zeros((N, NV), np.uint8)                 # px to 3DGS depth discontinuity (mesh-free)
    CDT = np.zeros((N, NV), np.uint8)                  # px to any projected crease-like mesh edge (LABEL gate only)
    for k in range(NV):
        cam = cams[k]
        dep = depth_all[k].copy()
        dep[~np.isfinite(dep)] = 1e9
        zmin = cv2.erode(dep, KERN3)                   # 3x3 min z-buffer (pipeline rule)
        zmax = cv2.dilate(dep, KERN3)
        has = zmin < 1e8
        jump = has & ((zmax - zmin) > 0.02 * zmin)     # depth discontinuity incl. silhouette
        sdt = cv2.distanceTransform((~jump).astype(np.uint8), cv2.DIST_L2, 5)
        uv, z = common.project(P_all, cam)
        u, vv = uv[:, 0] + off[0], uv[:, 1] + off[1]             # DexiNed photo-index coords
        inb = (z > 1e-6) & (u >= 0) & (u <= W - 1) & (vv >= 0) & (vv <= H - 1)
        ur0 = np.clip(np.round(uv[:, 0]).astype(np.int64), 0, W - 1)   # G-buffer convention
        vr0 = np.clip(np.round(uv[:, 1]).astype(np.int64), 0, H - 1)
        zb = zmin[vr0, ur0]
        dz = z - zb
        VIS["loose"][:, k] = inb & (dz <= args.eps_loose * z)
        VIS["tight"][:, k] = inb & (dz <= args.eps_tight * z)
        INB[:, k] = inb
        NOGEO[:, k] = inb & (zb > 1e8)
        DZ[:, k] = np.clip(dz, -8.0, 8.0)
        Z[:, k] = z
        SILD[:, k] = np.minimum(np.round(sdt[vr0, ur0]), 255).astype(np.uint8)
        for key, tag in (("native", "nat"), ("ms", "ms")):
            mp = load_map(scene, k, key)
            mpd = cv2.dilate(mp, KERN3)                # max within the 3x3 = within 1.5 px
            sb = remap(mp, u, vv, cv2.INTER_LINEAR)
            sd = remap(mpd, u, vv, cv2.INTER_NEAREST)
            sb[~inb] = 0.0
            sd[~inb] = 0.0
            S[f"{tag}_bil"][:, k] = sb
            S[f"{tag}_dil"][:, k] = sd
        # the frozen 2D stage's own detection rule (NMS-thinned native >= 0.5, DT <= 1.5 px)
        _, dt = tri_edges.edge_dt(EDGES.format(scene=scene), k, thr=0.5, key="native", nms=True)
        DET[:, k] = inb & (remap(dt.astype(np.float32), u, vv, cv2.INTER_NEAREST) <= 1.5)
        # LABEL gate: image distance to any projected crease-like mesh edge (no cull; conservative)
        uvc, zc_ = common.project(E_cl, cam)
        uc = np.round(uvc[:, 0] + off[0]).astype(np.int64)
        vc = np.round(uvc[:, 1] + off[1]).astype(np.int64)
        okc = (zc_ > 1e-6) & (uc >= 0) & (uc < W) & (vc >= 0) & (vc < H)
        cm = np.zeros((H, W), np.uint8)
        cm[vc[okc], uc[okc]] = 1
        cdt = cv2.distanceTransform(1 - cm, cv2.DIST_L2, 5) if cm.any() else np.full((H, W), 255.0, np.float32)
        CDT[:, k] = np.minimum(np.round(remap(cdt.astype(np.float32), u, vv, cv2.INTER_NEAREST)), 255).astype(np.uint8)
        if k % 20 == 0:
            vl = VIS["loose"][:, k]
            log(f"[C:{scene}] view {k:3d}: vis(loose) {vl.mean():.3f} vis(tight) {VIS['tight'][:, k].mean():.3f} "
                f"| mean P miss={S['nat_bil'][:Nm, k][vl[:Nm]].astype(np.float32).mean():.4f} "
                f"flat={S['nat_bil'][Nm:Nm+Nf, k][vl[Nm:Nm+Nf]].astype(np.float32).mean():.4f} "
                f"| det miss={DET[:Nm, k][vl[:Nm]].mean():.3f} flat={DET[Nm:Nm+Nf, k][vl[Nm:Nm+Nf]].mean():.3f} "
                f"({time.time()-t0:.0f}s)")
    np.savez_compressed(
        os.path.join(OUT, f"epi_samples_{scene}{TAG}.npz"),
        **S, vis_loose=VIS["loose"], vis_tight=VIS["tight"], inb=INB, nogeo=NOGEO, det=DET, dz=DZ, z=Z,
        sild=SILD, cdt=CDT, cls=cls, n_miss=Nm, n_flat=Nf, n_geo=Ng, offset=np.array(off),
        offset_best=np.array(best), offset_table=np.array([[a, b, tab[(a, b)]] for (a, b) in grid]),
        eps_loose=args.eps_loose, eps_tight=args.eps_tight)
    log(f"[C:{scene}] accumulated {N} points ({Nm} miss / {Nf} flat-pool / {Ng} geo-arm) x {NV} views "
        f"({time.time()-t0:.0f}s)")


# ============================================================ STAGE D — EVALUATION
def metrics(s, y):
    """AUC and Recall@85%Precision; NaN scores (no visible view) are dropped and counted."""
    from sklearn.metrics import roc_auc_score, precision_recall_curve
    s = np.asarray(s, np.float64)
    y = np.asarray(y, bool)
    ok = np.isfinite(s)
    drop_pos, drop_neg = int((~ok & y).sum()), int((~ok & ~y).sum())
    s, y = s[ok], y[ok]
    auc = float(roc_auc_score(y, s))
    p, r, _ = precision_recall_curve(y, s)
    m = p >= 0.85
    r85 = float(r[m].max()) if m.any() else 0.0
    m2 = r >= 0.55
    p55 = float(p[m2].max()) if m2.any() else 0.0
    return {"auc": auc, "r85": r85, "p_at_r55": p55, "n_pos": int(y.sum()), "n_neg": int((~y).sum()),
            "dropped_no_view_pos": drop_pos, "dropped_no_view_neg": drop_neg}


def aggregate(S, vis, sild=None, sil_r=3):
    """Per-row aggregates over the visible views; rows with no visible view -> NaN."""
    S = S.astype(np.float32)
    N, K = S.shape
    ar = np.arange(N)
    n = vis.sum(1)
    nan = np.full(N, np.nan, np.float32)
    Sm = np.where(vis, S, 0.0)
    mean = np.where(n > 0, Sm.sum(1) / np.maximum(n, 1), nan)
    Ss = np.where(vis, S, -1.0)
    Ss.sort(axis=1)
    Ss = Ss[:, ::-1]                                       # descending, valid first n
    cs = np.cumsum(Ss, axis=1, dtype=np.float64)

    def sum_top(kk):
        kk = np.asarray(kk)
        return np.where(kk > 0, cs[ar, np.clip(kk - 1, 0, K - 1)], 0.0)

    n1 = np.maximum(n, 1)
    mx = np.where(n > 0, Ss[:, 0], nan)
    kq = np.ceil(0.25 * n).astype(int)
    topq = np.where(n > 0, sum_top(kq) / np.maximum(kq, 1), nan)
    med = np.where(n > 0, 0.5 * (Ss[ar, (n1 - 1) // 2] + Ss[ar, n1 // 2]), nan)
    t = (0.1 * n).astype(int)
    mtr = n - 2 * t
    trim = np.where(mtr > 0, (sum_top(n - t) - sum_top(t)) / np.maximum(mtr, 1), mean)
    Pc = np.clip(S, 1e-3, 1 - 1e-3)
    L = np.log(Pc / (1 - Pc))
    mlog = np.where(n > 0, np.where(vis, L, 0.0).sum(1) / n1, nan)
    out = {"mean": mean, "median": med, "trim10": trim, "topq25": topq, "max": mx,
           "mean_logit": mlog, "n_vis": n}
    if sild is not None:
        v2 = vis & (sild > sil_r)
        n2 = v2.sum(1)
        out[f"mean_nosil{sil_r}"] = np.where(n2 > 0, np.where(v2, S, 0.0).sum(1) / np.maximum(n2, 1), nan)
        out[f"n_vis_nosil{sil_r}"] = n2
    return out


def balanced(pos, neg, rng):
    n = min(len(pos), len(neg))
    if len(pos) > n:
        pos = rng.choice(pos, n, replace=False)
    if len(neg) > n:
        neg = rng.choice(neg, n, replace=False)
    return np.concatenate([pos, neg]), np.r_[np.ones(len(pos), bool), np.zeros(len(neg), bool)]


def verdict_of(auc, r85):
    if auc >= GO["auc"] and r85 >= GO["r85"]:
        return "GO"
    if auc <= NOGO["auc"] or r85 <= NOGO["r85"]:
        return "NO-GO"
    return "MARGINAL"


def qdict(a, qs=(1, 5, 10, 25, 50, 75, 90, 95, 99)):
    a = np.asarray(a, np.float64)
    a = a[np.isfinite(a)]
    return {f"p{q}": float(np.percentile(a, q)) for q in qs} if len(a) else {}


def mean_over(S, vis):
    n = vis.sum(1)
    return np.where(n > 0, np.where(vis, S.astype(np.float32), 0.0).sum(1) / np.maximum(n, 1), np.nan)


def stage_eval(scene, args):
    t0 = time.time()
    lab = np.load(os.path.join(OUT, f"epi_labels_{scene}{TAG}.npz"))
    lmeta = json.load(open(os.path.join(OUT, f"epi_labels_{scene}{TAG}.json")))
    smp = np.load(os.path.join(OUT, f"epi_samples_{scene}{TAG}.npz"))
    Nm, Nf, Ng = int(smp["n_miss"]), int(smp["n_flat"]), int(smp["n_geo"])
    N = Nm + Nf + Ng
    cls = smp["cls"]
    n_base = int(lab["n_base"])
    px_world = float(lab["px_world"])
    th = lab["th_miss"]
    rng = np.random.default_rng(args.seed)
    S = {k: smp[k] for k in ("nat_bil", "nat_dil", "ms_bil", "ms_dil")}
    VIS = {"loose": smp["vis_loose"], "tight": smp["vis_tight"]}
    SILD, CDT, DET, INB, NOGEO = smp["sild"], smp["cdt"], smp["det"], smp["inb"], smp["nogeo"]
    DZ, Z = smp["dz"].astype(np.float32), smp["z"].astype(np.float32)
    views = {"all100": np.arange(NV), "train80": np.array(TRAIN)}
    miss_idx = np.arange(Nm)
    flat_all = np.arange(Nm, Nm + Nf)
    flat_base = flat_all[:n_base]                          # pool is shuffled; first n_base = headline negatives
    geo_idx = np.arange(Nm + Nf, N)
    d10_flat_px = lab["d10_flat"] / px_world
    res = {"scene": scene, "tag": TAG, "script_md5": script_md5(), "cv2_version": cv2.__version__,
           "n_miss": Nm, "n_flat_base": int(len(flat_base)), "n_flat_pool": Nf, "n_geo_arm": Ng,
           "offset_used": smp["offset"].tolist(), "offset_best": smp["offset_best"].tolist(),
           "offset_table": {f"({a:+.1f},{b:+.1f})": float(v) for a, b, v in smp["offset_table"]},
           "eps_loose_rel": float(smp["eps_loose"]), "eps_tight_rel": float(smp["eps_tight"]),
           "labels_meta": lmeta, "frozen_rule": {"GO": GO, "NOGO": NOGO}}

    # ---- eps calibration on mesh-visible TEST-view samples (3DGS-vs-mesh depth residual)
    tv = np.concatenate([lab["tv_miss"], lab["tv_flat"], lab["tv_geo"]])
    cal = {}
    for nm, sl in (("miss", miss_idx), ("flat", flat_base)):
        dzs, zs, ng = [], [], []
        for j, v in enumerate(TEST):
            m = tv[sl, j]
            dzs.append(DZ[sl, v][m]); zs.append(Z[sl, v][m]); ng.append(NOGEO[sl, v][m])
        dzs, zs, ng = np.concatenate(dzs), np.concatenate(zs), np.concatenate(ng)
        rel = dzs / np.maximum(zs, 1e-6)
        cal[nm] = {"n": int(len(dzs)), "frac_3dgs_no_geometry": float(ng.mean()),
                   "dz_over_z_quantiles": qdict(rel[~ng]),
                   "pass_frac_by_eps_rel_excl_nogeo": {str(e): float((rel[~ng] <= e).mean())
                                                       for e in (0.0025, 0.005, 0.01, 0.02, 0.05)}}
    res["eps_calibration_mesh_visible_points"] = cal
    agree = {}
    for en in ("loose", "tight"):
        tp = fn = fp = tn = 0
        for j, v in enumerate(TEST):
            for sl in (miss_idx, flat_base):
                a, b = tv[sl, j], VIS[en][sl, v]
                ib = INB[sl, v]
                tp += int((a & b).sum()); fn += int((a & ~b).sum())
                fp += int((~a & b & ib).sum()); tn += int((~a & ~b & ib).sum())
        agree[en] = {"mesh_vis_kept_by_3dgs": tp / max(tp + fn, 1),
                     "mesh_occluded_passed_by_3dgs": fp / max(fp + tn, 1)}
    res["visibility_agreement_TEST_views"] = agree

    # ---- headline grid (banked M_miss vs base M_flat, balanced)
    hidx = np.concatenate([miss_idx, flat_base])
    if len(flat_base) < Nm:
        hidx = np.concatenate([rng.choice(miss_idx, len(flat_base), replace=False), flat_base])
    y = cls[hidx] == 1
    grid, aggs = {}, {}
    for mk, sk, en, vn in itertools.product(("nat", "ms"), ("bil", "dil"), ("loose", "tight"), ("all100", "train80")):
        key = f"{mk}|{sk}|{en}|{vn}"
        vw = views[vn]
        agg = aggregate(S[f"{mk}_{sk}"][:, vw], VIS[en][:, vw], SILD[:, vw], 3)
        aggs[key] = agg
        grid[key] = {a: metrics(agg[a][hidx], y) for a in
                     ("mean", "median", "trim10", "topq25", "max", "mean_logit", "mean_nosil3")}
        grid[key]["n_vis_quantiles_miss"] = qdict(agg["n_vis"][miss_idx], (5, 50, 95))
        grid[key]["n_vis_quantiles_flat"] = qdict(agg["n_vis"][flat_base], (5, 50, 95))
        grid[key]["zero_vis_frac_miss"] = float((agg["n_vis"][miss_idx] == 0).mean())
        grid[key]["zero_vis_frac_flat"] = float((agg["n_vis"][flat_base] == 0).mean())
        grid[key]["zero_vis_nosil3_frac_miss"] = float((agg["n_vis_nosil3"][miss_idx] == 0).mean())
        grid[key]["zero_vis_nosil3_frac_flat"] = float((agg["n_vis_nosil3"][flat_base] == 0).mean())
    res["grid"] = grid
    HK = "nat|bil|loose|all100"
    head = grid[HK]["mean"]
    res["headline"] = {"config": HK + "|mean", "auc": head["auc"], "r85": head["r85"], "p_at_r55": head["p_at_r55"],
                       "n_pos": head["n_pos"], "n_neg": head["n_neg"], "verdict": verdict_of(head["auc"], head["r85"])}
    log(f"[D:{scene}] HEADLINE S_bar ({HK}|mean, n={head['n_pos']}/{head['n_neg']}): AUC={head['auc']:.4f} "
        f"Recall@85%P={head['r85']:.4f} -> {res['headline']['verdict']}   ({time.time()-t0:.0f}s)")
    for a in ("max", "median", "topq25", "trim10", "mean_logit", "mean_nosil3"):
        g_ = grid[HK][a]
        log(f"[D:{scene}]   arm {a:12s}: AUC={g_['auc']:.4f} R@85P={g_['r85']:.4f}")
    for k2 in ("nat|dil|loose|all100", "ms|bil|loose|all100", "nat|bil|tight|all100", "nat|bil|loose|train80"):
        g_ = grid[k2]["mean"]
        log(f"[D:{scene}]   cfg {k2:22s} mean: AUC={g_['auc']:.4f} R@85P={g_['r85']:.4f}")

    agg_h = aggs[HK]
    sbar = agg_h["mean"]
    det_any = (DET & VIS["loose"]).any(1)                  # pipeline-rule detection in >=1 visible view
    det_rate = np.where(agg_h["n_vis"] > 0, (DET & VIS["loose"]).sum(1) / np.maximum(agg_h["n_vis"], 1), np.nan)
    dist = {}
    for nm, sl in (("miss", miss_idx), ("flat", flat_base), ("geo_arm", geo_idx)):
        if len(sl) == 0:
            continue
        s_ = sbar[sl]
        dist[nm] = {"S_bar_quantiles": qdict(s_), "mean": float(np.nanmean(s_)),
                    "frac_S_bar<0.02": float(np.nanmean(s_ < 0.02)),
                    "frac_S_bar_in[0.05,0.5)": float(np.nanmean((s_ >= 0.05) & (s_ < 0.5))),
                    "frac_S_bar>=0.5": float(np.nanmean(s_ >= 0.5)),
                    "frac_detected_by_pipeline_rule_in_any_view": float(det_any[sl].mean()),
                    "frac_undetected_by_pipeline_rule_in_every_view": float((~det_any[sl]).mean()),
                    "per_point_detection_rate_quantiles": qdict(det_rate[sl], (10, 50, 90)),
                    "n_vis_quantiles": qdict(agg_h["n_vis"][sl], (5, 25, 50, 75, 95))}
    res["S_bar_distribution"] = dist

    # ---- DexiNed spatial response at FLAT points vs distance to the nearest geometric edge
    prof = []
    for lo, hi in ((3, 4), (4, 5), (5, 6), (6, 8), (8, 12), (12, 1e9)):
        m = (d10_flat_px >= lo) & (d10_flat_px < hi)
        sel = flat_all[m]
        if len(sel) < 50:
            prof.append({"bin_px": f"[{lo:g},{hi:g})", "n": int(len(sel))})
            continue
        prof.append({"bin_px": f"[{lo:g},{hi:g})", "n": int(len(sel)), "S_bar_mean": float(np.nanmean(sbar[sel])),
                     "S_bar_p50": float(np.nanmedian(sbar[sel])), "det_rate_mean": float(np.nanmean(det_rate[sel]))})
    res["flat_response_vs_edge_distance"] = prof

    # ---- 3D margin sweep (negatives = pool with d(E_geo10) > m px; positives = banked miss, balanced)
    sweep = []
    for mp in MARGINS_PX:
        neg = flat_all[d10_flat_px > mp]
        if len(neg) < 200:
            sweep.append({"margin_px": mp, "n_neg": int(len(neg)), "skipped": True})
            continue
        idx, yb = balanced(miss_idx, neg, rng)
        r = {"margin_px": mp, "n_neg_available": int(len(neg))}
        for a in ("mean", "median", "max", "mean_nosil3"):
            r[a] = metrics(agg_h[a][idx], yb)
        r["verdict_if_headline"] = verdict_of(r["mean"]["auc"], r["mean"]["r85"])
        sweep.append(r)
        log(f"[D:{scene}]   3D margin {mp:>4g}px: n_neg={len(neg):7d}  mean AUC={r['mean']['auc']:.4f} "
            f"R@85P={r['mean']['r85']:.4f} -> {r['verdict_if_headline']}")
    res["margin_sweep_3d"] = sweep

    # ---- image-space clean-negative arm: negatives' views must be > m px from ANY projected crease-like edge
    img_arm = []
    for mp in IMG_MARGINS_PX:
        vis_neg = VIS["loose"][flat_base] & (CDT[flat_base] > mp)
        s_neg = mean_over(S["nat_bil"][flat_base], vis_neg)
        s_all = sbar.copy()
        s_all[flat_base] = s_neg
        nvn = vis_neg.sum(1)
        r = {"img_margin_px": mp, "frac_neg_with_no_clean_view": float((nvn == 0).mean()),
             "n_vis_neg_p50": float(np.median(nvn)), "mean": metrics(s_all[hidx], y),
             "note": "gate applied to negatives only; positives keep all visible views"}
        r["verdict_if_headline"] = verdict_of(r["mean"]["auc"], r["mean"]["r85"])
        img_arm.append(r)
        log(f"[D:{scene}]   image-space clean negatives >{mp}px: no-clean-view {r['frac_neg_with_no_clean_view']:.3f} "
            f"AUC={r['mean']['auc']:.4f} R@85P={r['mean']['r85']:.4f} -> {r['verdict_if_headline']}")
    res["image_space_clean_negative_arm"] = img_arm

    # ---- geometric-a30 miss-set arm (positives = merged-mesh creases missed by the same cloud)
    if Ng > 0:
        idx, yb = balanced(geo_idx, flat_base, rng)
        r = {"n_pos": int(Ng), "labels": lmeta["geometric_a30_missset"], "S_bar_quantiles": qdict(sbar[geo_idx], (10, 50, 90))}
        for a in ("mean", "median", "max", "mean_nosil3"):
            r[a] = metrics(agg_h[a][idx], yb)
        r["verdict_if_headline"] = verdict_of(r["mean"]["auc"], r["mean"]["r85"])
        thg = lab["th_geo"]
        for nm, msk in (("theta>=30.05", thg >= 30.05), ("theta_exact30", (thg >= 29.9) & (thg < 30.1)), ("theta>=45", thg >= 45)):
            p_ = geo_idx[msk]
            if len(p_) >= 100:
                i2, y2 = balanced(p_, flat_base, rng)
                r[f"subset {nm}"] = {"n_pos": int(len(p_)), "mean": metrics(agg_h["mean"][i2], y2)}
        res["geometric_a30_arm"] = r
        log(f"[D:{scene}]   GEOMETRIC-a30 miss arm n={Ng}: mean AUC={r['mean']['auc']:.4f} R@85P={r['mean']['r85']:.4f} "
            f"-> {r['verdict_if_headline']}  (recall_3D geo {lmeta['geometric_a30_missset']['recall_3D']:.4f})")

    # ---- subsets of the banked miss-set (balanced negatives from the base flat set)
    subsets = {"ALL (spec-literal a30)": np.ones(Nm, bool),
               "theta>=30.05 (drop 30.000deg tessellation family)": th >= 30.05,
               "theta in [29.9,30.1) (the 30.000deg family)": (th >= 29.9) & (th < 30.1),
               "theta>=45": th >= 45,
               "theta exactly 90 (box corners)": (th >= 89.9) & (th < 90.1),
               "undetected by pipeline rule (NMS>=0.5, 1.5px) in EVERY visible view": ~det_any[:Nm],
               "detected by pipeline rule in >=1 view (lost downstream)": det_any[:Nm],
               "n_vis>=20 (well-observed)": agg_h["n_vis"][:Nm] >= 20}
    sub_res = {}
    for nm, msk in subsets.items():
        pos = miss_idx[msk]
        if len(pos) < 100:
            sub_res[nm] = {"n_pos": int(len(pos)), "skipped": True}
            continue
        idx, yb = balanced(pos, flat_base, rng)
        r = {"n_pos": int(len(pos)), "frac_of_missset": float(len(pos) / Nm),
             "S_bar_miss_quantiles": qdict(sbar[pos], (10, 50, 90))}
        for a in ("mean", "max", "median", "topq25", "mean_nosil3"):
            r[a] = metrics(agg_h[a][idx], yb)
        r["verdict_if_headline"] = verdict_of(r["mean"]["auc"], r["mean"]["r85"])
        sub_res[nm] = r
        log(f"[D:{scene}]   subset {nm[:58]:58s} n={len(pos):7d}  mean: AUC={r['mean']['auc']:.4f} "
            f"R@85P={r['mean']['r85']:.4f}  max: AUC={r['max']['auc']:.4f}")
    res["subsets"] = sub_res

    # ---- single-view baseline, PAIRED with S_bar on the same balanced points
    pv = []
    for k in range(NV):
        vk = VIS["loose"][:, k]
        pos = miss_idx[vk[miss_idx]]
        neg = flat_base[vk[flat_base]]
        if len(pos) < 100 or len(neg) < 100:
            continue
        idx, yb = balanced(pos, neg, rng)
        m = metrics(S["nat_bil"][idx, k].astype(np.float32), yb)
        mm = metrics(sbar[idx], yb)
        m.update({"view": k, "n_vis_miss": int(len(pos)), "n_vis_flat": int(len(neg)),
                  "S_bar_auc_same_points": mm["auc"], "S_bar_r85_same_points": mm["r85"],
                  "paired_auc_lift": mm["auc"] - m["auc"], "paired_r85_lift": mm["r85"] - m["r85"],
                  "det_rate_miss_pipeline_rule": float(DET[pos, k].mean()),
                  "fa_rate_flat_pipeline_rule": float(DET[neg, k].mean()),
                  "det_rate_miss_3x3max>=0.5": float((S["nat_dil"][pos, k].astype(np.float32) >= 0.5).mean()),
                  "fa_rate_flat_3x3max>=0.5": float((S["nat_dil"][neg, k].astype(np.float32) >= 0.5).mean()),
                  "mean_P_miss": float(S["nat_bil"][pos, k].astype(np.float32).mean()),
                  "mean_P_flat": float(S["nat_bil"][neg, k].astype(np.float32).mean())})
        pv.append(m)
    aucs = np.array([m["auc"] for m in pv])
    r85s = np.array([m["r85"] for m in pv])
    lifts = np.array([m["paired_auc_lift"] for m in pv])
    best_v = pv[int(np.argmax(aucs))]
    res["single_view_baseline"] = {
        "definition": "per view k: AUC / Recall@85%P of RAW bilinear DexiNed P_k over the M_miss u M_flat "
                      "points 3DGS-visible in k (balanced); S_bar scored on the SAME points for a paired lift",
        "n_views": len(pv), "auc_mean": float(aucs.mean()), "auc_median": float(np.median(aucs)),
        "auc_min": float(aucs.min()), "auc_max": float(aucs.max()),
        "r85_mean": float(r85s.mean()), "r85_max": float(r85s.max()),
        "paired_auc_lift_mean": float(lifts.mean()), "paired_auc_lift_min": float(lifts.min()),
        "paired_auc_lift_max": float(lifts.max()),
        "paired_r85_lift_mean": float(np.mean([m["paired_r85_lift"] for m in pv])),
        "best_view_by_auc": best_v,
        "det_rate_miss_pipeline_rule_mean": float(np.mean([m["det_rate_miss_pipeline_rule"] for m in pv])),
        "fa_rate_flat_pipeline_rule_mean": float(np.mean([m["fa_rate_flat_pipeline_rule"] for m in pv])),
        "det_rate_miss_3x3max_mean": float(np.mean([m["det_rate_miss_3x3max>=0.5"] for m in pv])),
        "fa_rate_flat_3x3max_mean": float(np.mean([m["fa_rate_flat_3x3max>=0.5"] for m in pv])),
        "anyview_det_miss_pipeline_rule": dist["miss"]["frac_detected_by_pipeline_rule_in_any_view"],
        "anyview_fa_flat_pipeline_rule": dist["flat"]["frac_detected_by_pipeline_rule_in_any_view"],
        "per_view": pv}
    res["lift"] = {"auc_multi_minus_single_mean_unpaired": head["auc"] - float(aucs.mean()),
                   "auc_paired_lift_mean": float(lifts.mean()),
                   "auc_paired_lift_vs_best_view": float(best_v["paired_auc_lift"]),
                   "r85_multi_minus_single_mean": head["r85"] - float(r85s.mean())}
    log(f"[D:{scene}] single-view baseline: AUC mean={aucs.mean():.4f} (min {aucs.min():.4f} max {aucs.max():.4f} "
        f"view {best_v['view']})  R@85P mean={r85s.mean():.4f} max={r85s.max():.4f} | PAIRED multi-view AUC lift "
        f"mean {lifts.mean():+.4f} (vs best view {best_v['paired_auc_lift']:+.4f})")
    log(f"[D:{scene}] pipeline-rule detection (NMS>=0.5, <=1.5px) of M_miss: per-view mean "
        f"{res['single_view_baseline']['det_rate_miss_pipeline_rule_mean']:.4f}, any-view "
        f"{dist['miss']['frac_detected_by_pipeline_rule_in_any_view']:.4f}; M_flat false-alarm per-view "
        f"{res['single_view_baseline']['fa_rate_flat_pipeline_rule_mean']:.4f}, any-view "
        f"{dist['flat']['frac_detected_by_pipeline_rule_in_any_view']:.4f}")

    res["seconds"] = time.time() - t0
    jp = os.path.join(OUT, f"epi_accum_{scene}{TAG}.json")
    json.dump(res, open(jp, "w"), indent=1, default=float)
    np.savez_compressed(os.path.join(OUT, f"epi_scores_{scene}{TAG}.npz"), cls=cls, hidx=hidx, y_head=y,
                        S_bar=sbar, S_max=agg_h["max"], S_median=agg_h["median"], S_topq25=agg_h["topq25"],
                        S_nosil3=agg_h["mean_nosil3"], n_vis=agg_h["n_vis"], det_any=det_any,
                        th_miss=th, best_view=best_v["view"])
    log(f"[D:{scene}] wrote {jp} ({time.time()-t0:.0f}s)")
    make_plots(scene, res, hidx, y, agg_h, S, VIS, best_v["view"], det_any, geo_idx, sbar)
    write_md(scene, res)
    return res


# ============================================================ PLOTS + REPORT
C_MISS, C_FLAT, C_SINGLE, C_MAX = "#2a78d6", "#eb6834", "#1baf7a", "#4a3aa7"   # validated slots 1,2,3,7
C_TXT, C_TXT2, C_GRID = "#0b0b0b", "#52514e", "#e6e5e1"


def make_plots(scene, res, hidx, y, agg, S, VIS, best_view, det_any, geo_idx, sbar):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.metrics import roc_curve, precision_recall_curve
    head = res["headline"]
    sh = sbar[hidx]
    ok = np.isfinite(sh)
    sh, yh, hidx_ok = sh[ok], y[ok], hidx[ok]
    Nm_h = int(yh.sum())
    fig, ax = plt.subplots(2, 2, figsize=(12.5, 9.5), facecolor="#fcfcfb")
    for a in ax.ravel():
        a.set_facecolor("#fcfcfb")
        for sp in ("top", "right"):
            a.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            a.spines[sp].set_color(C_GRID)
        a.tick_params(colors=C_TXT2, labelsize=9)
        a.grid(True, color=C_GRID, linewidth=0.6)
        a.set_axisbelow(True)

    a = ax[0, 0]
    bins = np.linspace(0, 1, 51)
    a.hist(sh[yh], bins=bins, density=True, histtype="step", linewidth=2, color=C_MISS, label=f"M_miss (n={Nm_h:,})")
    a.hist(sh[~yh], bins=bins, density=True, histtype="step", linewidth=2, color=C_FLAT, label=f"M_flat (n={int((~yh).sum()):,})")
    pos_idx = hidx_ok[yh]
    sub = pos_idx[~det_any[pos_idx]]
    if len(sub) > 100:
        a.hist(sbar[sub], bins=bins, density=True, histtype="step", linewidth=1.4, color=C_MISS, linestyle="--",
               label=f"M_miss undetected by pipeline rule in every view (n={len(sub):,})")
    if len(geo_idx) > 100:
        sg = sbar[geo_idx]
        a.hist(sg[np.isfinite(sg)], bins=bins, density=True, histtype="step", linewidth=1.4, color=C_MAX, linestyle=":",
               label=f"geometric-a30 miss arm (n={len(geo_idx):,})")
    a.set_yscale("log")
    a.set_xlabel("S_bar = occlusion-aware multi-view mean of RAW DexiNed P", color=C_TXT2)
    a.set_ylabel("density (log)", color=C_TXT2)
    a.set_title(f"{scene}: S_bar distributions", color=C_TXT, fontsize=11, loc="left")
    a.legend(frameon=False, fontsize=8, labelcolor=C_TXT)

    a = ax[0, 1]
    gk = res["grid"]["nat|bil|loose|all100"]
    curves = [("S_bar (multi-view mean)", "mean", C_MISS, "-"), ("max over views (any-view)", "max", C_MAX, "-"),
              ("median over views", "median", C_MISS, ":")]
    for nm, key, c, ls in curves:
        s = agg[key][hidx]
        okk = np.isfinite(s)
        fpr, tpr, _ = roc_curve(y[okk], s[okk])
        a.plot(fpr, tpr, color=c, linestyle=ls, linewidth=2, label=f"{nm}  AUC={gk[key]['auc']:.3f}")
    vk = VIS["loose"][hidx, best_view]
    sv = S["nat_bil"][hidx, best_view].astype(np.float32)
    rng = np.random.default_rng(1)
    pos = np.where(vk & y)[0]
    neg = np.where(vk & ~y)[0]
    bi, by = balanced(pos, neg, rng)
    fpr, tpr, _ = roc_curve(by, sv[bi])
    bv = res["single_view_baseline"]["best_view_by_auc"]
    a.plot(fpr, tpr, color=C_SINGLE, linewidth=2, label=f"best single view (v{best_view})  AUC={bv['auc']:.3f}")
    a.plot([0, 1], [0, 1], color=C_GRID, linewidth=1)
    a.set_xlabel("false positive rate (M_flat)", color=C_TXT2)
    a.set_ylabel("recall of M_miss", color=C_TXT2)
    a.set_title("ROC: missed creases vs flat surface", color=C_TXT, fontsize=11, loc="left")
    a.legend(frameon=False, fontsize=8.5, labelcolor=C_TXT, loc="lower right")

    a = ax[1, 0]
    for nm, key, c, ls in curves:
        s = agg[key][hidx]
        okk = np.isfinite(s)
        p, r, _ = precision_recall_curve(y[okk], s[okk])
        a.plot(r, p, color=c, linestyle=ls, linewidth=2, label=nm)
    p, r, _ = precision_recall_curve(by, sv[bi])
    a.plot(r, p, color=C_SINGLE, linewidth=2, label=f"best single view (v{best_view}, balanced)")
    a.axhline(0.85, color=C_TXT2, linewidth=1, linestyle="--")
    a.text(0.01, 0.86, "precision 0.85 operating line", color=C_TXT2, fontsize=8)
    a.axvline(GO["r85"], color=C_GRID, linewidth=1)
    a.axvline(NOGO["r85"], color=C_GRID, linewidth=1)
    a.text(GO["r85"] + 0.005, 0.465, f"GO R>={GO['r85']}", color=C_TXT2, fontsize=8)
    a.text(NOGO["r85"] - 0.17, 0.465, f"NO-GO R<={NOGO['r85']}", color=C_TXT2, fontsize=8)
    a.set_xlim(0, 1)
    a.set_ylim(0.45, 1.02)
    a.set_xlabel("recall of M_miss", color=C_TXT2)
    a.set_ylabel("precision (balanced classes)", color=C_TXT2)
    a.set_title(f"PR: S_bar Recall@85%P = {head['r85']:.3f}", color=C_TXT, fontsize=11, loc="left")
    a.legend(frameon=False, fontsize=8.5, labelcolor=C_TXT, loc="upper right")

    a = ax[1, 1]
    sw = [r for r in res["margin_sweep_3d"] if not r.get("skipped")]
    xs = [r["margin_px"] for r in sw]
    a.plot(xs, [r["mean"]["auc"] for r in sw], color=C_MISS, linewidth=2, marker="o", markersize=6, label="S_bar AUC vs 3D flat margin")
    a.plot(xs, [r["mean"]["r85"] for r in sw], color=C_MISS, linewidth=2, marker="s", markersize=6, linestyle="--", label="S_bar Recall@85%P vs 3D flat margin")
    ia = res["image_space_clean_negative_arm"]
    a.plot([r["img_margin_px"] for r in ia], [r["mean"]["auc"] for r in ia], color=C_MAX, linewidth=2, marker="o", markersize=6, label="AUC, image-space clean negatives")
    a.plot([r["img_margin_px"] for r in ia], [r["mean"]["r85"] for r in ia], color=C_MAX, linewidth=2, marker="s", markersize=6, linestyle="--", label="R@85P, image-space clean negatives")
    a.axhline(GO["auc"], color=C_GRID, linewidth=1)
    a.axhline(NOGO["auc"], color=C_GRID, linewidth=1)
    a.axhline(GO["r85"], color=C_GRID, linewidth=1, linestyle=":")
    a.axhline(NOGO["r85"], color=C_GRID, linewidth=1, linestyle=":")
    a.text(2.6, GO["auc"] + 0.012, f"GO: AUC>={GO['auc']} (solid) / R>={GO['r85']} (dotted)", color=C_TXT2, fontsize=7.5)
    a.text(2.6, NOGO["auc"] - 0.035, f"NO-GO: AUC<={NOGO['auc']} / R<={NOGO['r85']}", color=C_TXT2, fontsize=7.5)
    for r in sw:
        a.text(r["margin_px"], r["mean"]["auc"] + 0.015, f"n={r['n_neg_available']:,}", color=C_TXT2, fontsize=7, ha="center")
    a.set_ylim(0, 1.0)
    a.set_xlim(2.5, 8.5)
    a.set_xlabel("negative-class margin from nearest geometric edge (px)", color=C_TXT2)
    a.set_ylabel("metric", color=C_TXT2)
    a.set_title("margin sensitivity of the frozen criteria", color=C_TXT, fontsize=11, loc="left")
    a.legend(frameon=False, fontsize=8, labelcolor=C_TXT, loc="lower right")

    fig.suptitle(f"EPIPOLAR ACCUMULATION TEST — {scene}: AUC {head['auc']:.3f}, Recall@85%P {head['r85']:.3f}  ->  {head['verdict']}",
                 color=C_TXT, fontsize=13, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    p = os.path.join(OUT, f"epi_accum_{scene}{TAG}.png")
    fig.savefig(p, dpi=140)
    plt.close(fig)
    log(f"[D:{scene}] plot -> {p}")

    v = 25 if scene == "lego" else 5
    cams, rgb = common.load_cameras(scene)
    im = cv2.imread(rgb[v], cv2.IMREAD_UNCHANGED)
    if im.shape[2] == 4:
        al = im[:, :, 3:4].astype(np.float32) / 255
        bgr = (im[:, :, :3].astype(np.float32) * al + 255 * (1 - al)).astype(np.uint8)
    else:
        bgr = im[:, :, :3]
    mp = load_map(scene, v, "native")
    lab = np.load(os.path.join(OUT, f"epi_labels_{scene}{TAG}.npz"))
    P_all = np.concatenate([lab["P_miss"], lab["P_flat"], lab["P_geo"]])
    off = res["offset_used"]
    uv, z = common.project(P_all, cams[v])
    u, vv = uv[:, 0] + off[0], uv[:, 1] + off[1]
    vis = VIS["loose"][:, v]
    Nm = res["n_miss"]
    fig, ax = plt.subplots(1, 2, figsize=(16, 8), facecolor="#fcfcfb")
    ax[0].imshow(bgr[:, :, ::-1])
    ax[0].set_title(f"view {v}: M_miss (3DGS-visible) coloured by S_bar", color=C_TXT, loc="left")
    mm = vis[:Nm]
    sc = ax[0].scatter(u[:Nm][mm], vv[:Nm][mm], c=np.nan_to_num(sbar[:Nm][mm]), s=1.2, cmap="viridis", vmin=0, vmax=0.6)
    plt.colorbar(sc, ax=ax[0], fraction=0.035, label="S_bar")
    ax[1].imshow(1 - mp, cmap="gray", vmin=0, vmax=1)
    ax[1].set_title("RAW DexiNed native P (dark = high); orange = top-2% S_bar of the base flat set", color=C_TXT, loc="left")
    fb = hidx[~y]
    top = fb[np.argsort(-np.nan_to_num(sbar[fb]))[:int(0.02 * len(fb))]]
    top = top[vis[top]]
    ax[1].scatter(u[top], vv[top], s=6, marker="x", color=C_FLAT, linewidths=0.8)
    for a in ax:
        a.set_xlim(0, W - 1)
        a.set_ylim(H - 1, 0)
        a.axis("off")
    fig.tight_layout()
    p2 = os.path.join(OUT, f"epi_accum_{scene}{TAG}_inspect_v{v}.png")
    fig.savefig(p2, dpi=110)
    plt.close(fig)
    log(f"[D:{scene}] inspection -> {p2}")


def write_md(scene, res):
    h = res["headline"]
    g = res["grid"]
    sv = res["single_view_baseline"]
    lm = res["labels_meta"]
    mt = lm["mesh_topology"]
    cov = lm["banked_vs_geometric_a30"]
    L = [f"# EPIPOLAR ACCUMULATION TEST — {scene}\n",
         f"**VERDICT ({scene}, pre-registered headline): {h['verdict']}** — S_bar AUC-ROC = **{h['auc']:.4f}**, "
         f"Recall@85%Precision = **{h['r85']:.4f}** (n = {h['n_pos']:,} / {h['n_neg']:,}) against the frozen rule "
         f"(GO: AUC>={GO['auc']} AND R@85P>={GO['r85']}; NO-GO: AUC<={NOGO['auc']} OR R@85P<={NOGO['r85']}). "
         f"Script md5 `{res['script_md5']}`, cv2 {res['cv2_version']}.\n",
         f"- |M_miss| = **{res['n_miss']:,}** (banked Experiment-X miss-set), |M_flat| = **{h['n_neg']:,}** (balanced; pool "
         f"{res['n_flat_pool']:,}). Flat rule: {lm['flat_rule']}; base margin {lm['margin_px']} px-equiv = "
         f"{lm['margin_world']:.5f} world. Flat points' distance to the nearest banked GT crease: p5 = "
         f"{lm['flat_d_to_banked_crease_px_quantiles']['p5']:.2f} px, p50 = {lm['flat_d_to_banked_crease_px_quantiles']['p50']:.2f} px.",
         f"- Mesh topology (why the merged mesh is needed): split-vertex adjacency edges {mt['adj_edges_split']:,} "
         f"(>=10deg {mt['edges_ge10_split']:,}) vs position-merged {mt['adj_edges_merged']:,} (>=10deg {mt['edges_ge10_merged']:,}, "
         f">=30deg {mt['edges_ge30_merged']:,}), boundary {mt['boundary_edges_merged']:,}, non-manifold {mt['nonmanifold_edges_merged']:,}. "
         f"Banked a30 crease samples within 1e-4 of a geometric a30 edge: {cov['frac_banked_within_1e-4_of_geometric']:.3f}; "
         f"geometric a30 samples covered by the banked set: **{cov['frac_geometric_within_1e-4_of_banked']:.3f}**.",
         f"- RAW DexiNed maps: `out/dexined_edges_{scene}/v###.npz[native]` — sigmoid probability, float16, no threshold / NMS / stretch "
         f"(continuity asserted at run time).",
         f"- Occlusion: 3DGS mean depth (de-floatered gaussians), 3x3-min z-buffer, visible iff z <= zbuf + eps*z with **eps = {res['eps_loose_rel']}** "
         f"(the pipeline's rule); tight arm eps = {res['eps_tight_rel']}. Photo-index offset used = {res['offset_used']} "
         f"(calibrated on the hit-set; best = {res['offset_best']})."]
    cal = res["eps_calibration_mesh_visible_points"]
    va = res["visibility_agreement_TEST_views"]["loose"]
    L.append(f"- Depth-test calibration on mesh-visible TEST-view samples (3DGS minus mesh, dz/z): p50/p95 = "
             f"{cal['miss']['dz_over_z_quantiles']['p50']:+.4f}/{cal['miss']['dz_over_z_quantiles']['p95']:+.4f} (miss), "
             f"{cal['flat']['dz_over_z_quantiles']['p50']:+.4f}/{cal['flat']['dz_over_z_quantiles']['p95']:+.4f} (flat); pass at eps 0.02: "
             f"{cal['miss']['pass_frac_by_eps_rel_excl_nogeo']['0.02']:.3f} / {cal['flat']['pass_frac_by_eps_rel_excl_nogeo']['0.02']:.3f}; "
             f"at 0.005: {cal['miss']['pass_frac_by_eps_rel_excl_nogeo']['0.005']:.3f} / {cal['flat']['pass_frac_by_eps_rel_excl_nogeo']['0.005']:.3f}. "
             f"3DGS gate vs mesh visibility (TEST views): keeps {va['mesh_vis_kept_by_3dgs']:.3f} of mesh-visible, "
             f"passes {va['mesh_occluded_passed_by_3dgs']:.3f} of mesh-occluded.\n")
    L.append("## Headline and arms (native map, bilinear at pi_k(x), eps 0.02, all 100 views)\n")
    L.append("| aggregator over visible views | AUC | Recall@85%P | precision@R=0.55 | dropped (no view) pos/neg |")
    L.append("|---|---|---|---|---|")
    for a in ("mean", "median", "trim10", "topq25", "max", "mean_logit", "mean_nosil3"):
        m = g["nat|bil|loose|all100"][a]
        tag = " **(headline S_bar)**" if a == "mean" else ""
        L.append(f"| {a}{tag} | {m['auc']:.4f} | {m['r85']:.4f} | {m['p_at_r55']:.4f} | {m['dropped_no_view_pos']}/{m['dropped_no_view_neg']} |")
    L.append("\n## Sensitivity grid (mean aggregator)\n")
    L.append("| map | sampling | eps | views | AUC | Recall@85%P | n_vis p50 miss/flat | zero-vis miss/flat |")
    L.append("|---|---|---|---|---|---|---|---|")
    for k, v in g.items():
        mk, sk, en, vn = k.split("|")
        m = v["mean"]
        L.append(f"| {mk} | {sk} | {en} | {vn} | {m['auc']:.4f} | {m['r85']:.4f} | "
                 f"{v['n_vis_quantiles_miss']['p50']:.0f}/{v['n_vis_quantiles_flat']['p50']:.0f} | "
                 f"{v['zero_vis_frac_miss']:.4f}/{v['zero_vis_frac_flat']:.4f} |")
    L.append("\n## Negative-class margin sensitivity\n")
    L.append("3D margin from the nearest geometric (merged-mesh) >=10deg / boundary / non-manifold edge; positives = banked M_miss, balanced by subsampling.\n")
    L.append("| margin px | n_neg available | AUC (mean) | R@85P (mean) | AUC (median) | R@85P (median) | AUC (max) | rule |")
    L.append("|---|---|---|---|---|---|---|---|")
    for r in res["margin_sweep_3d"]:
        if r.get("skipped"):
            L.append(f"| {r['margin_px']:g} | {r['n_neg']} | — | — | — | — | — | skipped |")
            continue
        L.append(f"| {r['margin_px']:g} | {r['n_neg_available']:,} | {r['mean']['auc']:.4f} | {r['mean']['r85']:.4f} | "
                 f"{r['median']['auc']:.4f} | {r['median']['r85']:.4f} | {r['max']['auc']:.4f} | {r['verdict_if_headline']} |")
    L.append("\nImage-space arm: a negative's view counts only if its projection is > m px from ANY projected crease-like mesh edge (no cull, conservative); positives unchanged.\n")
    L.append("| image margin px | negatives with no clean view | n_vis_neg p50 | AUC | R@85P | rule |")
    L.append("|---|---|---|---|---|---|")
    for r in res["image_space_clean_negative_arm"]:
        L.append(f"| {r['img_margin_px']} | {r['frac_neg_with_no_clean_view']:.3f} | {r['n_vis_neg_p50']:.0f} | {r['mean']['auc']:.4f} | {r['mean']['r85']:.4f} | {r['verdict_if_headline']} |")
    L.append("\nDexiNed response on FLAT points vs distance to the nearest geometric edge (S_bar mean / median, pipeline-rule detection rate):\n")
    L.append("| d(edge) bin px | n | S_bar mean | S_bar p50 | det rate |")
    L.append("|---|---|---|---|---|")
    for r in res["flat_response_vs_edge_distance"]:
        if "S_bar_mean" in r:
            L.append(f"| {r['bin_px']} | {r['n']:,} | {r['S_bar_mean']:.4f} | {r['S_bar_p50']:.4f} | {r['det_rate_mean']:.4f} |")
        else:
            L.append(f"| {r['bin_px']} | {r['n']} | — | — | — |")
    if "geometric_a30_arm" in res:
        ga = res["geometric_a30_arm"]
        gl = ga["labels"]
        L.append("\n## Geometric-a30 miss-set arm (positives from the merged mesh; same cloud, radius and visibility rule as Experiment X)\n")
        L.append(f"- Geometric >=30deg crease samples TEST-visible: {gl['n_seen']:,}; 3D recall of the frozen cloud on them **{gl['recall_3D']:.4f}** "
                 f"(banked subset {gl['recall_3D_on_banked_subset']:.4f}, non-banked subset {gl['recall_3D_on_non_banked_subset']:.4f}; "
                 f"{gl['frac_seen_in_banked']:.3f} of the seen samples are in the banked set); misses {gl['n_miss']:,}, arm size {ga['n_pos']:,}.")
        L.append(f"- vs base M_flat (balanced): AUC **{ga['mean']['auc']:.4f}**, Recall@85%P **{ga['mean']['r85']:.4f}** (median arm {ga['median']['auc']:.4f}/{ga['median']['r85']:.4f}; "
                 f"max {ga['max']['auc']:.4f}) -> {ga['verdict_if_headline']}. S_bar p10/p50/p90 = {ga['S_bar_quantiles']['p10']:.3f}/{ga['S_bar_quantiles']['p50']:.3f}/{ga['S_bar_quantiles']['p90']:.3f}.")
        for k, v in ga.items():
            if k.startswith("subset "):
                L.append(f"  - {k}: n={v['n_pos']:,} AUC {v['mean']['auc']:.4f} R@85P {v['mean']['r85']:.4f}")
    d = res["S_bar_distribution"]
    L.append("\n## S_bar distribution (headline)\n")
    L.append("| class | mean | p10 | p50 | p90 | frac S_bar<0.02 | frac in [0.05,0.5) | frac >=0.5 | detected by pipeline rule in >=1 view | undetected in EVERY view | per-point det rate p50 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for nm in ("miss", "flat", "geo_arm"):
        if nm not in d:
            continue
        q = d[nm]["S_bar_quantiles"]
        L.append(f"| {nm} | {d[nm]['mean']:.4f} | {q['p10']:.4f} | {q['p50']:.4f} | {q['p90']:.4f} | {d[nm]['frac_S_bar<0.02']:.3f} | "
                 f"{d[nm]['frac_S_bar_in[0.05,0.5)']:.3f} | {d[nm]['frac_S_bar>=0.5']:.3f} | {d[nm]['frac_detected_by_pipeline_rule_in_any_view']:.3f} | "
                 f"{d[nm]['frac_undetected_by_pipeline_rule_in_every_view']:.3f} | {d[nm]['per_point_detection_rate_quantiles'].get('p50', float('nan')):.3f} |")
    L.append("\n## Banked miss-set subsets (each vs an equal-count random subset of the base M_flat)\n")
    L.append("| subset | n | share | S_bar p50 | AUC (mean) | R@85P (mean) | AUC (max) | R@85P (max) | rule |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for nm, r in res["subsets"].items():
        if r.get("skipped"):
            L.append(f"| {nm} | {r['n_pos']} | — | — | — | — | — | — | skipped (<100) |")
            continue
        L.append(f"| {nm} | {r['n_pos']:,} | {r['frac_of_missset']:.3f} | {r['S_bar_miss_quantiles']['p50']:.4f} | {r['mean']['auc']:.4f} | "
                 f"{r['mean']['r85']:.4f} | {r['max']['auc']:.4f} | {r['max']['r85']:.4f} | {r['verdict_if_headline']} |")
    L.append("\n## Single-view baseline and the multi-view lift (paired)\n")
    L.append(f"- Per-view (RAW bilinear P_k, balanced, {sv['n_views']} views): AUC mean **{sv['auc_mean']:.4f}** (median {sv['auc_median']:.4f}, "
             f"min {sv['auc_min']:.4f}, max {sv['auc_max']:.4f} at view {sv['best_view_by_auc']['view']}); Recall@85%P mean **{sv['r85_mean']:.4f}** (max {sv['r85_max']:.4f}).")
    L.append(f"- **Paired multi-view lift** (S_bar minus single view on the same points): AUC mean {sv['paired_auc_lift_mean']:+.4f} "
             f"(range {sv['paired_auc_lift_min']:+.4f} .. {sv['paired_auc_lift_max']:+.4f}; vs the best view {res['lift']['auc_paired_lift_vs_best_view']:+.4f}); "
             f"R@85P {sv['paired_r85_lift_mean']:+.4f}.")
    L.append(f"- Frozen 2D-stage detection rule (NMS-thinned native >= 0.5, within 1.5 px): M_miss per-view mean **{sv['det_rate_miss_pipeline_rule_mean']:.4f}**, "
             f"any of 100 views {sv['anyview_det_miss_pipeline_rule']:.4f}; M_flat false-alarm per-view **{sv['fa_rate_flat_pipeline_rule_mean']:.4f}**, "
             f"any-view {sv['anyview_fa_flat_pipeline_rule']:.4f}. (3x3-max raw P >= 0.5, no NMS — a superset: miss {sv['det_rate_miss_3x3max_mean']:.4f}, flat {sv['fa_rate_flat_3x3max_mean']:.4f}.)")
    L.append(f"\nArtefacts: `out/epi/epi_accum_{scene}{TAG}.json`, `out/epi/epi_accum_{scene}{TAG}.png`, `out/epi/epi_accum_{scene}{TAG}_inspect_v*.png`, "
             f"arrays `out/epi/epi_{{labels,samples,scores}}_{scene}{TAG}.npz`.\n")
    p = os.path.join(OUT, f"EPI_ACCUM_{scene}{TAG}.md")
    open(p, "w").write("\n".join(L))
    log(f"[D:{scene}] report -> {p}")


# ============================================================ MAIN
def main():
    global TAG
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="lego", choices=sorted(TAGS))
    ap.add_argument("--stage", default="all", choices=["labels", "gbuf", "accum", "eval", "all"])
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--margin_px", type=float, default=3.0, help="base flat margin, px-equiv (2*tau)")
    ap.add_argument("--pool_mult", type=float, default=2.0, help="flat pool size as a multiple of |M_miss|")
    ap.add_argument("--n_hit", type=int, default=60000)
    ap.add_argument("--n_geo", type=int, default=300000, help="geometric-a30 miss arm size cap")
    ap.add_argument("--chunk", type=int, default=4_000_000)
    ap.add_argument("--max_sample", type=int, default=80_000_000)
    ap.add_argument("--eps_loose", type=float, default=0.02, help="pipeline visibility rel eps")
    ap.add_argument("--eps_tight", type=float, default=0.005)
    ap.add_argument("--offset", default="auto", help="'auto' (calibrate on hit-set) or 'du,dv'")
    ap.add_argument("--tag", default="", help="suffix for label/sample/result files (sensitivity arms)")
    args = ap.parse_args()
    TAG = args.tag
    os.makedirs(OUT, exist_ok=True)
    if args.device.startswith("cuda") and not torch.cuda.is_available():
        args.device = "cpu"
    log(f"[epi_accum] script md5 {script_md5()}  args {vars(args)}")
    stages = ["labels", "gbuf", "accum", "eval"] if args.stage == "all" else [args.stage]
    for s in stages:
        {"labels": stage_labels, "gbuf": stage_gbuf, "accum": stage_accum, "eval": stage_eval}[s](args.scene, args)


if __name__ == "__main__":
    main()
