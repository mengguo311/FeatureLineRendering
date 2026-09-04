#!/usr/bin/env python
"""EPIPOLAR ACCUMULATION TEST — closed-form kill-test for the LINE-BUFFER pivot.

*** EVAL / ANALYSIS ONLY.  The GT mesh is read for LABELS (M_miss / M_flat point sets and
    their TEST-view visibility) and never enters the feature.  The FEATURE (occlusion-aware
    multi-view accumulation of RAW DexiNed probability through the frozen 3DGS depth) is
    mesh-free by construction. ***

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
                          threshold, NO NMS, NO contrast stretch.  Verified continuous here.
    * M_miss            : Experiment X's banked miss-set (out/xy/xy_expX_<scene><tag>.npz:
                          seen_idx / rec3 / theta0_pt) over cache/dexp0_gt_<scene>_a30.npz.
                          = GT crease points visible in >=1 TEST view with NO point of the
                          frozen triangulated cloud (DexiNed native >= 0.5, NMS, K=6
                          neighbours, support>=2) within the 1.5px-equivalent radius.
    * cameras / proj    : src.common.load_cameras / project.
    * 3DGS depth        : src.render.render_gbuffer (transmittance-weighted mean depth + the
                          median depth), de-floatered exactly as the pipeline does.
    * visibility rule   : src.visibility.visible_mask's rule, re-implemented vectorised over
                          [N,100]:  visible iff  z <= min3x3(zbuf) + eps_rel * z.  The
                          pipeline's eps_rel = 0.02 is the headline; 0.005 is the tight arm.
    * pixel convention  : src.tri_edges' photo-index = K-projection - 0.5 (halfpix).  It is
                          not assumed: the offset is CALIBRATED on the HIT-set (recovered
                          creases, disjoint from both test classes) by maximising their mean
                          DexiNed response over a 5x5 grid of sub-pixel offsets.

LABELS (mesh EVAL-ONLY)
    M_flat = area-uniform samples of the GT mesh surface that are (i) farther than
    margin_px (default 3 px-equiv = the project's 2*tau negative-class convention) from
    ANY mesh edge with dihedral >= 10 deg -- a strict superset of "far from any GT crease"
    (GT creases are the >= 30 deg edges) so weak non-GT shading edges cannot contaminate the
    negative class -- and (ii) visible in >= 1 TEST view under the SAME mesh-depth rule that
    defined M_miss's visibility (3x3 min |dz| < 0.015, scripts/dexprimary_p0.gt_labels).
    |M_flat| = |M_miss| (balanced), so Recall@85%Precision has a fixed meaning.

FEATURE
    For every x in M_miss u M_flat and every one of the 100 views k:
        (u,v) = pi_k(x) (photo-index), z_k(x); vis_k = 3DGS depth test; P_k = RAW DexiNed
        sampled BILINEARLY at (u,v)  [headline]  and  max over the 3x3 pixel neighbourhood
        (= within 1.5 px) [dilated arm].
    S_bar(x) = mean_{k: vis_k} P_k          [headline]
    Robust arms: median, 10% trimmed mean, top-quartile mean, max (= any-view), mean of
    logits, and mean excluding views where x projects within 3 px of a 3DGS depth
    discontinuity (silhouette peel, mesh-free).

USAGE
    python scripts/epi_accum.py --scene lego --stage all
    stages: labels -> gbuf -> accum -> eval  (each caches its output; rerun any one)
"""
import argparse
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
DS, ANGLE = 0.0015, 30.0            # mesh_oracle sampling step / crease threshold
FLAT_EDGE_DEG = 10.0                # "flat" = far from ANY edge >= this dihedral
MESH_VIS_EPS = 0.015                # gt_labels' mesh-depth visibility eps (same rule)
TAGS = {"lego": "_p1c", "chair": "_ref40"}
TEST, TRAIN = list(view_split.TEST), list(view_split.TRAIN)
H = W = 800
NV = 100
GO = {"auc": 0.80, "r85": 0.55}
NOGO = {"auc": 0.65, "r85": 0.42}
KERN3 = np.ones((3, 3), np.uint8)
TAG = ""                            # label-arm tag (e.g. _m8 for the strict 8px flat margin)


def log(msg):
    print(msg, flush=True)


# ============================================================ STAGE A — LABELS (mesh EVAL-ONLY)
def sample_edges_vec(V, pairs, ds):
    """Vectorised replica of mesh_oracle._sample_edges (linspace(0,1,max(2,int(L/ds)+1)))."""
    A, B = V[pairs[:, 0]], V[pairs[:, 1]]
    L = np.linalg.norm(B - A, axis=1)
    n = np.maximum(2, (L / ds).astype(int) + 1)
    eid = np.repeat(np.arange(len(n)), n)
    start = np.concatenate([[0], np.cumsum(n)[:-1]])
    local = np.arange(n.sum()) - start[eid]
    t = local / (n[eid] - 1)
    return A[eid] + t[:, None] * (B[eid] - A[eid])


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
    log(f"[A:{scene}] crease_pts={len(crease)} seen={len(seen_idx)} miss={len(miss_idx)} "
        f"hit={len(hit_idx)} radius={radius:.6f} px_world={px_world:.6f}")

    # TEST-view mesh visibility of the miss-set, from the banked idx{v}
    pos = -np.ones(len(crease), np.int64)
    pos[miss_idx] = np.arange(len(miss_idx))
    tv_miss = np.zeros((len(miss_idx), len(TEST)), bool)
    for j, v in enumerate(TEST):
        p = pos[gt[f"idx{v}"]]
        tv_miss[p[p >= 0], j] = True
    assert tv_miss.any(1).all(), "every miss point must be TEST-visible by construction"

    # hit-set subsample (offset calibration only; disjoint from both test classes)
    rng = np.random.default_rng(args.seed)
    hs = np.sort(rng.choice(len(hit_idx), size=min(args.n_hit, len(hit_idx)), replace=False))
    hit_sub = hit_idx[hs]
    pos[:] = -1
    pos[hit_sub] = np.arange(len(hit_sub))
    tv_hit = np.zeros((len(hit_sub), len(TEST)), bool)
    for j, v in enumerate(TEST):
        p = pos[gt[f"idx{v}"]]
        tv_hit[p[p >= 0], j] = True

    # ---- mesh: >=10 deg edge samples (superset of the GT crease set) for the flat margin
    m = trimesh.load(os.path.join(os.path.expanduser("~/3dgs_line/bcr/meshes/NeRF_Mesh"),
                                  f"{scene}_new.obj"), process=True)
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate([g for g in m.geometry.values()])
    V = np.asarray(m.vertices, np.float64)
    adjE = np.asarray(m.face_adjacency_edges)
    deg = np.degrees(np.asarray(m.face_adjacency_angles))
    sel10 = np.where(deg >= FLAT_EDGE_DEG)[0]
    E10 = sample_edges_vec(V, adjE[sel10], DS)
    tree10 = cKDTree(E10)
    tree30 = cKDTree(crease)
    margin = args.margin_px * px_world
    log(f"[A:{scene}] mesh V={len(V)} F={len(m.faces)} edges>={FLAT_EDGE_DEG:g}deg={len(sel10)} "
        f"-> {len(E10)} samples; margin={args.margin_px}px = {margin:.5f} world "
        f"({time.time()-t0:.0f}s)")

    # ---- TEST-view GT-mesh depth (same rasteriser that defined M_miss's visibility)
    cams, _ = common.load_cameras(scene)
    oracle = MeshOracle(scene, angle_deg=179.0, device=args.device)   # depth only
    tdepth = {}
    for v in TEST:
        tdepth[v] = oracle.render_depth(cams[v]).detach().cpu().numpy()
        oracle._depth_cache.clear()
        torch.cuda.empty_cache()
    log(f"[A:{scene}] GT-mesh depth for {len(TEST)} TEST views ({time.time()-t0:.0f}s)")

    # ---- area-uniform surface sampling -> margin -> TEST visibility
    need = len(miss_idx)
    coll, total, it, rounds = [], 0, 0, []
    n_have = 0
    while n_have < need and total < args.max_sample:
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
        log(f"[A:{scene}]   round {it}: sampled {len(pts)} -> margin {k1.sum()} "
            f"({k1.mean():.3f}) -> TEST-visible {k2.sum()} | have {n_have}/{need} "
            f"({time.time()-t0:.0f}s)")
    P_pool = np.concatenate([c[0] for c in coll])
    f_pool = np.concatenate([c[1] for c in coll])
    d10_pool = np.concatenate([c[2] for c in coll])
    tv_pool = np.concatenate([c[3] for c in coll])
    perm = rng.permutation(len(P_pool))[:need]
    P_flat, face_flat, d10_flat, tv_flat = P_pool[perm], f_pool[perm], d10_pool[perm], tv_pool[perm]
    n_miss_full = len(P_miss)
    if len(P_flat) < need:                      # strict-margin arms: keep the classes BALANCED
        sub = np.sort(rng.choice(len(P_miss), size=len(P_flat), replace=False))
        log(f"[A:{scene}] flat pool {len(P_flat)} < miss {need}: subsampling M_miss to "
            f"{len(P_flat)} (uniform, seed {args.seed}) to keep the classes balanced")
        P_miss, th_miss, tv_miss, miss_idx = P_miss[sub], th_miss[sub], tv_miss[sub], miss_idx[sub]
    d30_flat = tree30.query(P_flat, k=1, workers=-1)[0]
    d10_miss = tree10.query(P_miss, k=1, workers=-1)[0]      # sanity: ~0 (they ARE edges)
    log(f"[A:{scene}] M_miss={len(P_miss)}  M_flat={len(P_flat)} (pool {len(P_pool)} from "
        f"{total} surface samples)  flat d(GT crease) p5={np.percentile(d30_flat,5):.4f} "
        f"p50={np.percentile(d30_flat,50):.4f}  flat TEST-vis views p50="
        f"{np.median(tv_flat.sum(1)):.0f}  miss TEST-vis views p50={np.median(tv_miss.sum(1)):.0f}")

    os.makedirs(OUT, exist_ok=True)
    np.savez_compressed(
        os.path.join(OUT, f"epi_labels_{scene}{TAG}.npz"),
        P_miss=P_miss.astype(np.float64), miss_idx=miss_idx, th_miss=th_miss.astype(np.float32),
        tv_miss=tv_miss, d10_miss=d10_miss.astype(np.float32),
        P_flat=P_flat.astype(np.float64), face_flat=face_flat, d10_flat=d10_flat.astype(np.float32),
        d30_flat=d30_flat.astype(np.float32), tv_flat=tv_flat,
        P_hit=crease[hit_sub].astype(np.float64), hit_idx=hit_sub, tv_hit=tv_hit,
        px_world=px_world, radius=radius, margin=margin, margin_px=args.margin_px,
        flat_edge_deg=FLAT_EDGE_DEG, test_views=np.array(TEST))
    meta = {"scene": scene, "n_miss": int(len(P_miss)), "n_flat": int(len(P_flat)),
            "n_miss_full": int(n_miss_full), "tag": TAG,
            "n_hit_calib": int(len(hit_sub)), "n_flat_pool": int(len(P_pool)),
            "n_surface_samples": int(total), "rounds": rounds,
            "margin_px": args.margin_px, "margin_world": margin, "px_world": px_world,
            "flat_rule": f"d(any mesh edge with dihedral >= {FLAT_EDGE_DEG:g} deg) > margin "
                         f"AND visible in >=1 TEST view (mesh depth, 3x3 min |dz| < {MESH_VIS_EPS})",
            "flat_d_to_GT_crease_quantiles": {f"p{q}": float(np.percentile(d30_flat, q))
                                              for q in (1, 5, 25, 50, 75, 95)},
            "miss_d_to_edge10_quantiles": {f"p{q}": float(np.percentile(d10_miss, q))
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
        dev = args.device
        try:
            gb = render.render_gbuffer(g, keep, cams[v], device=dev, with_median_depth=True)
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
            log(f"[B:{scene}] view {v:3d}  fg={float((al[v] > 0.5).mean()):.3f}  "
                f"({time.time()-t0:.0f}s)")
    np.savez_compressed(os.path.join(CACHE, f"epi_gbuf_{scene}.npz"), depth=dm,
                        depth_median=dmed, alpha=al, n_gauss=len(g["mu"]),
                        n_keep=int(keep.sum()), n_cpu_fallback=n_cpu)
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
    they are visible, for each candidate (du,dv) photo-index offset.  Photometric alignment
    calibration; uses no M_miss / M_flat point."""
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
    t0 = time.time()
    lab = np.load(os.path.join(OUT, f"epi_labels_{scene}{TAG}.npz"))
    gb = np.load(os.path.join(CACHE, f"epi_gbuf_{scene}.npz"))
    depth_all = gb["depth"]
    alpha_all = gb["alpha"]
    cams, _ = common.load_cameras(scene)
    P_all = np.concatenate([lab["P_miss"], lab["P_flat"]])
    N, Nm = len(P_all), len(lab["P_miss"])

    # ---- RAW-map verification (the whole test hinges on this)
    probe = load_map(scene, TEST[0], "native")
    nuniq = len(np.unique(probe[::3, ::3]))
    sub = float(((probe > 0.02) & (probe < 0.5)).mean())
    assert nuniq > 500 and probe.max() <= 1.0 and probe.min() >= 0.0, "map is not continuous"
    log(f"[C:{scene}] RAW-map check v{TEST[0]}: unique values (1/9 sub-grid) = {nuniq}, "
        f"frac in (0.02,0.5) = {sub:.4f}, frac>=0.5 = {float((probe >= 0.5).mean()):.4f} "
        f"-> CONTINUOUS probability, not a thresholded mask")

    # ---- photo-index offset calibration on the HIT set
    grid = [(a, b) for a in (-1.0, -0.5, 0.0, 0.5, 1.0) for b in (-1.0, -0.5, 0.0, 0.5, 1.0)]
    tab = calibrate_offset(scene, lab, cams, grid)
    best = max(tab, key=tab.get)
    if args.offset == "auto":
        off = best
    else:
        off = tuple(float(t) for t in args.offset.split(","))
    log(f"[C:{scene}] offset calibration (mean RAW P at hit-set creases): "
        + "  ".join(f"({a:+.1f},{b:+.1f})={tab[(a, b)]:.4f}" for (a, b) in
                    [(-0.5, -0.5), (0.0, 0.0), (-1.0, -1.0), (0.5, 0.5), best]))
    log(f"[C:{scene}] best offset = {best}  (tri_edges halfpix convention = (-0.5,-0.5)); "
        f"USING {off}")

    keys = ["nat_bil", "nat_dil", "ms_bil", "ms_dil"]
    S = {k: np.zeros((N, NV), np.float16) for k in keys}
    VIS = {"loose": np.zeros((N, NV), bool), "tight": np.zeros((N, NV), bool)}
    INB = np.zeros((N, NV), bool)
    NOGEO = np.zeros((N, NV), bool)
    DZ = np.zeros((N, NV), np.float16)
    Z = np.zeros((N, NV), np.float16)
    SILD = np.zeros((N, NV), np.uint8)
    n_geom_pix = []
    for k in range(NV):
        cam = cams[k]
        dep = depth_all[k].copy()
        dep[~np.isfinite(dep)] = 1e9
        zmin = cv2.erode(dep, KERN3)                       # 3x3 min z-buffer (pipeline rule)
        zmax = cv2.dilate(dep, KERN3)
        has = zmin < 1e8
        jump = has & ((zmax - zmin) > 0.02 * zmin)         # depth discontinuity incl. silhouette
        sdt = cv2.distanceTransform((~jump).astype(np.uint8), cv2.DIST_L2, 5)
        uv, z = common.project(P_all, cam)
        u, vv = uv[:, 0] + off[0], uv[:, 1] + off[1]
        inb = (z > 1e-6) & (u >= 0) & (u <= W - 1) & (vv >= 0) & (vv <= H - 1)
        ur = np.clip(np.round(u).astype(np.int64), 0, W - 1)
        vr = np.clip(np.round(vv).astype(np.int64), 0, H - 1)
        zb = zmin[vr, ur]
        dz = z - zb
        VIS["loose"][:, k] = inb & (dz <= args.eps_loose * z)
        VIS["tight"][:, k] = inb & (dz <= args.eps_tight * z)
        INB[:, k] = inb
        NOGEO[:, k] = inb & (zb > 1e8)
        DZ[:, k] = np.clip(dz, -8.0, 8.0)
        Z[:, k] = z
        SILD[:, k] = np.clip(sdt[vr, ur], 0, 255).astype(np.uint8)
        for key, tag in (("native", "nat"), ("ms", "ms")):
            mp = load_map(scene, k, key)
            mpd = cv2.dilate(mp, KERN3)                    # max within the 3x3 = within 1.5 px
            sb = remap(mp, u, vv, cv2.INTER_LINEAR)
            sd = remap(mpd, u, vv, cv2.INTER_NEAREST)
            sb[~inb] = 0.0
            sd[~inb] = 0.0
            S[f"{tag}_bil"][:, k] = sb
            S[f"{tag}_dil"][:, k] = sd
        n_geom_pix.append(float(has.mean()))
        if k % 20 == 0:
            vl = VIS["loose"][:, k]
            log(f"[C:{scene}] view {k:3d}: in-frame {inb.mean():.3f} vis(loose) {vl.mean():.3f} "
                f"vis(tight) {VIS['tight'][:, k].mean():.3f} | mean P miss={S['nat_bil'][:Nm, k][vl[:Nm]].astype(np.float32).mean():.4f} "
                f"flat={S['nat_bil'][Nm:, k][vl[Nm:]].astype(np.float32).mean():.4f} ({time.time()-t0:.0f}s)")
    np.savez_compressed(
        os.path.join(OUT, f"epi_samples_{scene}{TAG}.npz"),
        **S, vis_loose=VIS["loose"], vis_tight=VIS["tight"], inb=INB, nogeo=NOGEO, dz=DZ, z=Z,
        sild=SILD, n_miss=Nm, n_flat=N - Nm, offset=np.array(off), offset_best=np.array(best),
        offset_table=np.array([[a, b, tab[(a, b)]] for (a, b) in grid]),
        eps_loose=args.eps_loose, eps_tight=args.eps_tight)
    log(f"[C:{scene}] accumulated {N} points x {NV} views ({time.time()-t0:.0f}s)")


# ============================================================ STAGE D — EVALUATION
def metrics(s, y):
    from sklearn.metrics import roc_auc_score, precision_recall_curve
    s = np.asarray(s, np.float64)
    y = np.asarray(y, bool)
    auc = float(roc_auc_score(y, s))
    p, r, _ = precision_recall_curve(y, s)
    ok = p >= 0.85
    r85 = float(r[ok].max()) if ok.any() else 0.0
    ok2 = r >= 0.55
    p55 = float(p[ok2].max()) if ok2.any() else 0.0
    return {"auc": auc, "r85": r85, "p_at_r55": p55, "n_pos": int(y.sum()), "n_neg": int((~y).sum())}


def aggregate(S, vis, sild=None, sil_r=3):
    """Per-row aggregates over the visible views.  S [N,K] any float, vis [N,K] bool."""
    S = S.astype(np.float32)
    N, K = S.shape
    ar = np.arange(N)
    n = vis.sum(1)
    Sm = np.where(vis, S, 0.0)
    mean = Sm.sum(1) / np.maximum(n, 1)
    Ss = np.where(vis, S, -1.0)
    Ss.sort(axis=1)
    Ss = Ss[:, ::-1]                                       # descending, valid first n
    cs = np.cumsum(Ss, axis=1, dtype=np.float64)

    def sum_top(kk):
        kk = np.asarray(kk)
        return np.where(kk > 0, cs[ar, np.clip(kk - 1, 0, K - 1)], 0.0)

    n1 = np.maximum(n, 1)
    mx = np.where(n > 0, Ss[:, 0], 0.0)
    kq = np.ceil(0.25 * n).astype(int)
    topq = np.where(n > 0, sum_top(kq) / np.maximum(kq, 1), 0.0)
    med = np.where(n > 0, 0.5 * (Ss[ar, (n1 - 1) // 2] + Ss[ar, n1 // 2]), 0.0)
    t = (0.1 * n).astype(int)
    mtr = n - 2 * t
    trim = np.where(mtr > 0, (sum_top(n - t) - sum_top(t)) / np.maximum(mtr, 1), mean)
    L = np.log(np.clip(S, 1e-4, 1 - 1e-4) / (1 - np.clip(S, 1e-4, 1 - 1e-4)))
    mlog = np.where(vis, L, 0.0).sum(1) / n1
    out = {"mean": mean, "median": med, "trim10": trim, "topq25": topq, "max": mx,
           "mean_logit": mlog, "n_vis": n}
    if sild is not None:
        v2 = vis & (sild > sil_r)
        n2 = v2.sum(1)
        out[f"mean_nosil{sil_r}"] = np.where(v2, S, 0.0).sum(1) / np.maximum(n2, 1)
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
    return {f"p{q}": float(np.percentile(a, q)) for q in qs} if len(a) else {}


def stage_eval(scene, args):
    t0 = time.time()
    lab = np.load(os.path.join(OUT, f"epi_labels_{scene}{TAG}.npz"))
    smp = np.load(os.path.join(OUT, f"epi_samples_{scene}{TAG}.npz"))
    Nm, Nf = int(smp["n_miss"]), int(smp["n_flat"])
    N = Nm + Nf
    y = np.r_[np.ones(Nm, bool), np.zeros(Nf, bool)]
    th = lab["th_miss"]
    rng = np.random.default_rng(args.seed)
    S = {k: smp[k] for k in ("nat_bil", "nat_dil", "ms_bil", "ms_dil")}
    VIS = {"loose": smp["vis_loose"], "tight": smp["vis_tight"]}
    SILD, DZ, Z, NOGEO, INB = smp["sild"], smp["dz"].astype(np.float32), smp["z"].astype(np.float32), smp["nogeo"], smp["inb"]
    views = {"all100": np.arange(NV), "train80": np.array(TRAIN)}
    res = {"scene": scene, "n_miss": Nm, "n_flat": Nf,
           "offset_used": smp["offset"].tolist(), "offset_best": smp["offset_best"].tolist(),
           "offset_table": {f"({a:+.1f},{b:+.1f})": float(v) for a, b, v in smp["offset_table"]},
           "eps_loose_rel": float(smp["eps_loose"]), "eps_tight_rel": float(smp["eps_tight"]),
           "labels_meta": json.load(open(os.path.join(OUT, f"epi_labels_{scene}{TAG}.json"))),
           "frozen_rule": {"GO": GO, "NOGO": NOGO}}

    # ---- eps calibration: 3DGS-vs-mesh depth residual where the MESH says the point is visible
    tv = np.concatenate([lab["tv_miss"], lab["tv_flat"]])
    cal = {}
    for nm, sl in (("miss", slice(0, Nm)), ("flat", slice(Nm, N))):
        dzs, zs, ng = [], [], []
        for j, v in enumerate(TEST):
            m = tv[sl, j]
            dzs.append(DZ[sl, v][m])
            zs.append(Z[sl, v][m])
            ng.append(NOGEO[sl, v][m])
        dzs, zs, ng = np.concatenate(dzs), np.concatenate(zs), np.concatenate(ng)
        rel = dzs / np.maximum(zs, 1e-6)
        cal[nm] = {"n": int(len(dzs)), "frac_3dgs_no_geometry": float(ng.mean()),
                   "dz_world_quantiles": qdict(dzs[~ng]),
                   "dz_over_z_quantiles": qdict(rel[~ng]),
                   "pass_frac_by_eps_rel": {str(e): float((rel <= e).mean())
                                            for e in (0.0025, 0.005, 0.01, 0.02, 0.05)}}
    res["eps_calibration_mesh_visible_points"] = cal
    # agreement of 3DGS visibility with mesh visibility on TEST views (both classes)
    agree = {}
    for en in ("loose", "tight"):
        tp = fn = fp = tn = 0
        for j, v in enumerate(TEST):
            a, b = tv[:, j], VIS[en][:, v] & INB[:, v]
            tp += int((a & b).sum()); fn += int((a & ~b).sum())
            fp += int((~a & b & INB[:, v]).sum()); tn += int((~a & ~b & INB[:, v]).sum())
        agree[en] = {"mesh_vis_kept_by_3dgs": tp / max(tp + fn, 1),
                     "mesh_occluded_passed_by_3dgs": fp / max(fp + tn, 1)}
    res["visibility_agreement_TEST_views"] = agree

    # ---- the full grid of arms
    grid = {}
    aggs_cache = {}
    for mk, sk, en, vn in itertools.product(("nat", "ms"), ("bil", "dil"), ("loose", "tight"),
                                            ("all100", "train80")):
        key = f"{mk}|{sk}|{en}|{vn}"
        vw = views[vn]
        agg = aggregate(S[f"{mk}_{sk}"][:, vw], VIS[en][:, vw], SILD[:, vw], 3)
        aggs_cache[key] = agg
        grid[key] = {a: metrics(agg[a], y) for a in
                     ("mean", "median", "trim10", "topq25", "max", "mean_logit", "mean_nosil3")}
        grid[key]["n_vis_quantiles_miss"] = qdict(agg["n_vis"][:Nm], (5, 50, 95))
        grid[key]["n_vis_quantiles_flat"] = qdict(agg["n_vis"][Nm:], (5, 50, 95))
        grid[key]["frac_zero_vis"] = float((agg["n_vis"] == 0).mean())
    res["grid"] = grid
    HK = "nat|bil|loose|all100"
    head = grid[HK]["mean"]
    res["headline"] = {"config": HK + "|mean", "auc": head["auc"], "r85": head["r85"],
                       "p_at_r55": head["p_at_r55"], "verdict": verdict_of(head["auc"], head["r85"])}
    log(f"[D:{scene}] HEADLINE S_bar ({HK}|mean): AUC={head['auc']:.4f} "
        f"Recall@85%P={head['r85']:.4f}  -> {res['headline']['verdict']}   ({time.time()-t0:.0f}s)")
    for a in ("max", "median", "topq25", "trim10", "mean_logit", "mean_nosil3"):
        g_ = grid[HK][a]
        log(f"[D:{scene}]   arm {a:12s}: AUC={g_['auc']:.4f} R@85P={g_['r85']:.4f}")
    for k2 in ("nat|dil|loose|all100", "ms|bil|loose|all100", "nat|bil|tight|all100", "nat|bil|loose|train80"):
        g_ = grid[k2]["mean"]
        log(f"[D:{scene}]   cfg {k2:22s} mean: AUC={g_['auc']:.4f} R@85P={g_['r85']:.4f}")

    # ---- S_bar distribution (headline) + the dead-zero question
    agg_h = aggs_cache[HK]
    sbar = agg_h["mean"]
    mx_dil = aggregate(S["nat_dil"], VIS["loose"])["max"]     # any-view thresholded detection
    dist = {}
    for nm, sl in (("miss", slice(0, Nm)), ("flat", slice(Nm, N))):
        s_ = sbar[sl]
        dist[nm] = {"S_bar_quantiles": qdict(s_), "mean": float(s_.mean()),
                    "frac_S_bar<0.01": float((s_ < 0.01).mean()),
                    "frac_S_bar<0.02": float((s_ < 0.02).mean()),
                    "frac_S_bar_in[0.05,0.5)": float(((s_ >= 0.05) & (s_ < 0.5)).mean()),
                    "frac_S_bar>=0.5": float((s_ >= 0.5).mean()),
                    "frac_anyview_dil>=0.5": float((mx_dil[sl] >= 0.5).mean()),
                    "frac_anyview_dil<0.5(sub-threshold everywhere)": float((mx_dil[sl] < 0.5).mean()),
                    "n_vis_quantiles": qdict(agg_h["n_vis"][sl], (5, 25, 50, 75, 95))}
    res["S_bar_distribution"] = dist

    # ---- subsets of the miss-set (balanced negatives each time)
    subsets = {"ALL (spec-literal a30)": np.ones(Nm, bool),
               "theta>=30.05 (drop 30.000deg tessellation family)": th >= 30.05,
               "theta in [29.9,30.1) (the 30.000deg family)": (th >= 29.9) & (th < 30.1),
               "theta>=45": th >= 45,
               "theta exactly 90 (box corners)": (th >= 89.9) & (th < 90.1),
               "sub-threshold everywhere (max over views of 1.5px-max P < 0.5)": mx_dil[:Nm] < 0.5,
               "above threshold in >=1 view (lost by triangulation)": mx_dil[:Nm] >= 0.5,
               "n_vis>=20 (well-observed)": agg_h["n_vis"][:Nm] >= 20}
    sub_res = {}
    flat_idx = np.arange(Nm, N)
    for nm, msk in subsets.items():
        pos = np.where(msk)[0]
        if len(pos) < 100:
            sub_res[nm] = {"n_pos": int(len(pos)), "skipped": True}
            continue
        idx, yb = balanced(pos, flat_idx, rng)
        r = {"n_pos": int(len(pos)), "frac_of_missset": float(len(pos) / Nm),
             "S_bar_miss_quantiles": qdict(sbar[pos], (10, 50, 90))}
        for a in ("mean", "max", "median", "topq25", "mean_nosil3"):
            r[a] = metrics(agg_h[a][idx], yb)
        r["verdict_if_headline"] = verdict_of(r["mean"]["auc"], r["mean"]["r85"])
        sub_res[nm] = r
        log(f"[D:{scene}]   subset {nm[:52]:52s} n={len(pos):7d}  mean: AUC={r['mean']['auc']:.4f} "
            f"R@85P={r['mean']['r85']:.4f}  max: AUC={r['max']['auc']:.4f}")
    res["subsets"] = sub_res

    # ---- single-view baseline: each view on its own (balanced), RAW bilinear native
    pv = []
    for k in range(NV):
        vk = VIS["loose"][:, k]
        pos = np.where(vk & y)[0]
        neg = np.where(vk & ~y)[0]
        if len(pos) < 100 or len(neg) < 100:
            continue
        idx, yb = balanced(pos, neg, rng)
        m = metrics(S["nat_bil"][idx, k].astype(np.float32), yb)
        m.update({"view": k, "n_vis_miss": int(len(pos)), "n_vis_flat": int(len(neg)),
                  "det_rate_miss_at_0.5_dil": float((S["nat_dil"][pos, k].astype(np.float32) >= 0.5).mean()),
                  "fa_rate_flat_at_0.5_dil": float((S["nat_dil"][neg, k].astype(np.float32) >= 0.5).mean()),
                  "mean_P_miss": float(S["nat_bil"][pos, k].astype(np.float32).mean()),
                  "mean_P_flat": float(S["nat_bil"][neg, k].astype(np.float32).mean())})
        pv.append(m)
    aucs = np.array([m["auc"] for m in pv])
    r85s = np.array([m["r85"] for m in pv])
    best_v = pv[int(np.argmax(r85s))]
    res["single_view_baseline"] = {
        "definition": "per view k: AUC / Recall@85%P of RAW bilinear DexiNed native P_k over the "
                      "M_miss u M_flat points 3DGS-visible in k (balanced)",
        "n_views": len(pv), "auc_mean": float(aucs.mean()), "auc_median": float(np.median(aucs)),
        "auc_min": float(aucs.min()), "auc_max": float(aucs.max()),
        "r85_mean": float(r85s.mean()), "r85_median": float(np.median(r85s)),
        "r85_min": float(r85s.min()), "r85_max": float(r85s.max()),
        "best_view_by_r85": best_v,
        "det_rate_miss_at_0.5_dil_mean": float(np.mean([m["det_rate_miss_at_0.5_dil"] for m in pv])),
        "fa_rate_flat_at_0.5_dil_mean": float(np.mean([m["fa_rate_flat_at_0.5_dil"] for m in pv])),
        "anyview_det_rate_miss_at_0.5_dil": dist["miss"]["frac_anyview_dil>=0.5"],
        "anyview_fa_rate_flat_at_0.5_dil": dist["flat"]["frac_anyview_dil>=0.5"],
        "per_view": pv}
    lift = {"auc_multi_minus_single_mean": head["auc"] - float(aucs.mean()),
            "auc_multi_minus_single_best": head["auc"] - float(aucs.max()),
            "r85_multi_minus_single_mean": head["r85"] - float(r85s.mean()),
            "r85_multi_minus_single_best": head["r85"] - float(r85s.max()),
            "auc_maxview_minus_single_mean": grid[HK]["max"]["auc"] - float(aucs.mean())}
    res["lift"] = lift
    log(f"[D:{scene}] single-view baseline: AUC mean={aucs.mean():.4f} (min {aucs.min():.4f} max "
        f"{aucs.max():.4f})  R@85P mean={r85s.mean():.4f} max={r85s.max():.4f}  | multi-view lift "
        f"AUC {lift['auc_multi_minus_single_mean']:+.4f} R@85P {lift['r85_multi_minus_single_mean']:+.4f}")
    log(f"[D:{scene}] thresholded(0.5, 1.5px) single-view detection of M_miss: per-view mean "
        f"{res['single_view_baseline']['det_rate_miss_at_0.5_dil_mean']:.4f}, any-view "
        f"{dist['miss']['frac_anyview_dil>=0.5']:.4f}; M_flat false-alarm per-view "
        f"{res['single_view_baseline']['fa_rate_flat_at_0.5_dil_mean']:.4f}, any-view "
        f"{dist['flat']['frac_anyview_dil>=0.5']:.4f}")

    res["seconds"] = time.time() - t0
    jp = os.path.join(OUT, f"epi_accum_{scene}{TAG}.json")
    json.dump(res, open(jp, "w"), indent=1, default=float)
    np.savez_compressed(os.path.join(OUT, f"epi_scores_{scene}{TAG}.npz"), y=y, S_bar=sbar,
                        S_max=agg_h["max"], S_median=agg_h["median"], S_topq25=agg_h["topq25"],
                        S_nosil3=agg_h["mean_nosil3"], n_vis=agg_h["n_vis"], mx_dil=mx_dil,
                        th_miss=th, best_view=best_v["view"])
    log(f"[D:{scene}] wrote {jp} ({time.time()-t0:.0f}s)")
    make_plots(scene, res, y, agg_h, S, VIS, best_v["view"], mx_dil)
    write_md(scene, res)
    return res


# ============================================================ PLOTS + REPORT
C_MISS, C_FLAT, C_SINGLE, C_MAX = "#2a78d6", "#eb6834", "#1baf7a", "#4a3aa7"   # validated slots 1,2,3,7
C_TXT, C_TXT2, C_GRID = "#0b0b0b", "#52514e", "#e6e5e1"


def make_plots(scene, res, y, agg, S, VIS, best_view, mx_dil):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.metrics import roc_curve, precision_recall_curve
    Nm = int(y.sum())
    sbar = agg["mean"]
    head = res["headline"]
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

    # (a) S_bar distributions
    a = ax[0, 0]
    bins = np.linspace(0, 1, 51)
    a.hist(sbar[:Nm], bins=bins, density=True, histtype="step", linewidth=2, color=C_MISS,
           label=f"M_miss (n={Nm:,})")
    a.hist(sbar[Nm:], bins=bins, density=True, histtype="step", linewidth=2, color=C_FLAT,
           label=f"M_flat (n={int((~y).sum()):,})")
    sub = np.where(mx_dil[:Nm] < 0.5)[0]
    if len(sub) > 100:
        a.hist(sbar[sub], bins=bins, density=True, histtype="step", linewidth=1.4, color=C_MISS,
               linestyle="--", label=f"M_miss, sub-threshold in every view (n={len(sub):,})")
    a.set_yscale("log")
    a.set_xlabel("S_bar = occlusion-aware multi-view mean of RAW DexiNed P", color=C_TXT2)
    a.set_ylabel("density (log)", color=C_TXT2)
    a.set_title(f"{scene}: S_bar distributions", color=C_TXT, fontsize=11, loc="left")
    a.legend(frameon=False, fontsize=8.5, labelcolor=C_TXT)

    # (b) ROC
    a = ax[0, 1]
    curves = [("S_bar (multi-view mean)", sbar, C_MISS, "-"),
              ("max over views (any-view)", agg["max"], C_MAX, "-"),
              ("median over views", agg["median"], C_MISS, ":")]
    vk = VIS["loose"][:, best_view]
    sv = S["nat_bil"][:, best_view].astype(np.float32)
    for nm, s, c, ls in curves:
        fpr, tpr, _ = roc_curve(y, s)
        a.plot(fpr, tpr, color=c, linestyle=ls, linewidth=2,
               label=f"{nm}  AUC={res['grid']['nat|bil|loose|all100'][ {'S_bar (multi-view mean)':'mean','max over views (any-view)':'max','median over views':'median'}[nm] ]['auc']:.3f}")
    fpr, tpr, _ = roc_curve(y[vk], sv[vk])
    bv = res["single_view_baseline"]["best_view_by_r85"]
    a.plot(fpr, tpr, color=C_SINGLE, linewidth=2,
           label=f"best single view (v{best_view})  AUC={bv['auc']:.3f}")
    a.plot([0, 1], [0, 1], color=C_GRID, linewidth=1)
    a.set_xlabel("false positive rate (M_flat)", color=C_TXT2)
    a.set_ylabel("recall of M_miss", color=C_TXT2)
    a.set_title("ROC: missed creases vs flat surface", color=C_TXT, fontsize=11, loc="left")
    a.legend(frameon=False, fontsize=8.5, labelcolor=C_TXT, loc="lower right")

    # (c) PR
    a = ax[1, 0]
    for nm, s, c, ls in curves:
        p, r, _ = precision_recall_curve(y, s)
        a.plot(r, p, color=c, linestyle=ls, linewidth=2, label=nm)
    p, r, _ = precision_recall_curve(y[vk], sv[vk])
    a.plot(r, p, color=C_SINGLE, linewidth=2, label=f"best single view (v{best_view})")
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

    # (d) per-view single-view AUC vs multi-view
    a = ax[1, 1]
    pv = res["single_view_baseline"]["per_view"]
    va = np.array(sorted(m["auc"] for m in pv))
    a.plot(np.arange(len(va)), va, color=C_SINGLE, linewidth=2, label="single view AUC (sorted)")
    a.axhline(head["auc"], color=C_MISS, linewidth=2, label=f"S_bar multi-view AUC {head['auc']:.3f}")
    a.axhline(res["grid"]["nat|bil|loose|all100"]["max"]["auc"], color=C_MAX, linewidth=2,
              label=f"max-over-views AUC {res['grid']['nat|bil|loose|all100']['max']['auc']:.3f}")
    a.axhline(GO["auc"], color=C_GRID, linewidth=1)
    a.axhline(NOGO["auc"], color=C_GRID, linewidth=1)
    a.text(1, GO["auc"] + 0.005, f"GO AUC>={GO['auc']}", color=C_TXT2, fontsize=8)
    a.text(1, NOGO["auc"] - 0.02, f"NO-GO AUC<={NOGO['auc']}", color=C_TXT2, fontsize=8)
    a.set_ylim(0.4, 1.0)
    a.set_xlabel("view rank", color=C_TXT2)
    a.set_ylabel("AUC (M_miss vs M_flat)", color=C_TXT2)
    a.set_title("single-view ceiling vs multi-view accumulation", color=C_TXT, fontsize=11, loc="left")
    a.legend(frameon=False, fontsize=8.5, labelcolor=C_TXT, loc="lower right")

    fig.suptitle(f"EPIPOLAR ACCUMULATION TEST — {scene}: AUC {head['auc']:.3f}, "
                 f"Recall@85%P {head['r85']:.3f}  ->  {head['verdict']}",
                 color=C_TXT, fontsize=13, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    p = os.path.join(OUT, f"epi_accum_{scene}{TAG}.png")
    fig.savefig(p, dpi=140)
    plt.close(fig)
    log(f"[D:{scene}] plot -> {p}")

    # ---- inspection overlay on one TEST view: RAW map + M_miss coloured by S_bar + top flat
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
    P_all = np.concatenate([lab["P_miss"], lab["P_flat"]])
    off = res["offset_used"]
    uv, z = common.project(P_all, cams[v])
    u, vv = uv[:, 0] + off[0], uv[:, 1] + off[1]
    vis = VIS["loose"][:, v]
    fig, ax = plt.subplots(1, 2, figsize=(16, 8), facecolor="#fcfcfb")
    ax[0].imshow(bgr[:, :, ::-1])
    ax[0].set_title(f"view {v}: M_miss (3DGS-visible) coloured by S_bar", color=C_TXT, loc="left")
    mm = vis[:Nm]
    sc = ax[0].scatter(u[:Nm][mm], vv[:Nm][mm], c=sbar[:Nm][mm], s=1.2, cmap="viridis", vmin=0, vmax=0.6)
    plt.colorbar(sc, ax=ax[0], fraction=0.035, label="S_bar")
    ax[1].imshow(1 - mp, cmap="gray", vmin=0, vmax=1)
    ax[1].set_title("RAW DexiNed native P (dark = high); orange = top-2% S_bar flat points",
                    color=C_TXT, loc="left")
    fl = np.arange(Nm, len(y))
    top = fl[np.argsort(-sbar[Nm:])[:int(0.02 * (len(y) - Nm))]]
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
    L = []
    L.append(f"# EPIPOLAR ACCUMULATION TEST — {scene}\n")
    L.append(f"**VERDICT ({scene}): {h['verdict']}** — S_bar AUC-ROC = **{h['auc']:.4f}**, "
             f"Recall@85%Precision = **{h['r85']:.4f}** against the frozen rule "
             f"(GO: AUC>={GO['auc']} AND R@85P>={GO['r85']}; NO-GO: AUC<={NOGO['auc']} OR R@85P<={NOGO['r85']}).\n")
    L.append(f"- |M_miss| = **{res['n_miss']:,}**, |M_flat| = **{res['n_flat']:,}** (balanced). "
             f"Flat rule: {res['labels_meta']['flat_rule']}; margin {res['labels_meta']['margin_px']} px-equiv "
             f"= {res['labels_meta']['margin_world']:.5f} world; flat points' distance to the nearest GT crease "
             f"p5 = {res['labels_meta']['flat_d_to_GT_crease_quantiles']['p5']:.4f}, "
             f"p50 = {res['labels_meta']['flat_d_to_GT_crease_quantiles']['p50']:.4f}.")
    L.append(f"- RAW DexiNed maps: `out/dexined_edges_{scene}/v###.npz[native]` — sigmoid probability, "
             f"float16, no threshold / NMS / stretch (continuity asserted at run time).")
    L.append(f"- Occlusion: 3DGS mean depth (de-floatered gaussians), 3x3-min z-buffer, "
             f"visible iff z <= zbuf + eps*z with **eps = {res['eps_loose_rel']}** (the pipeline's rule); "
             f"tight arm eps = {res['eps_tight_rel']}. Pixel offset (photo-index) used = {res['offset_used']} "
             f"(calibrated on the hit-set; best = {res['offset_best']}).")
    cal = res["eps_calibration_mesh_visible_points"]
    L.append(f"- Depth-test calibration on mesh-visible TEST-view points: |3DGS - mesh| dz/z p50/p95 = "
             f"{cal['miss']['dz_over_z_quantiles']['p50']:+.4f}/{cal['miss']['dz_over_z_quantiles']['p95']:+.4f} (miss), "
             f"{cal['flat']['dz_over_z_quantiles']['p50']:+.4f}/{cal['flat']['dz_over_z_quantiles']['p95']:+.4f} (flat); "
             f"pass fraction at eps 0.02: miss {cal['miss']['pass_frac_by_eps_rel']['0.02']:.3f}, "
             f"flat {cal['flat']['pass_frac_by_eps_rel']['0.02']:.3f}; at 0.005: "
             f"{cal['miss']['pass_frac_by_eps_rel']['0.005']:.3f} / {cal['flat']['pass_frac_by_eps_rel']['0.005']:.3f}.\n")
    L.append("## Headline and arms (native map, bilinear at pi_k(x), eps 0.02, all 100 views)\n")
    L.append("| aggregator over visible views | AUC | Recall@85%P | precision@R=0.55 |")
    L.append("|---|---|---|---|")
    for a in ("mean", "median", "trim10", "topq25", "max", "mean_logit", "mean_nosil3"):
        m = g["nat|bil|loose|all100"][a]
        tag = " **(headline S_bar)**" if a == "mean" else ""
        L.append(f"| {a}{tag} | {m['auc']:.4f} | {m['r85']:.4f} | {m['p_at_r55']:.4f} |")
    L.append("\n## Sensitivity grid (mean aggregator)\n")
    L.append("| map | sampling | eps | views | AUC | Recall@85%P | n_vis p50 miss/flat |")
    L.append("|---|---|---|---|---|---|---|")
    for k, v in g.items():
        mk, sk, en, vn = k.split("|")
        m = v["mean"]
        L.append(f"| {mk} | {sk} | {en} | {vn} | {m['auc']:.4f} | {m['r85']:.4f} | "
                 f"{v['n_vis_quantiles_miss']['p50']:.0f}/{v['n_vis_quantiles_flat']['p50']:.0f} |")
    d = res["S_bar_distribution"]
    L.append("\n## S_bar distribution (headline)\n")
    L.append("| class | mean | p10 | p50 | p90 | frac S_bar<0.02 | frac in [0.05,0.5) | frac >=0.5 | any-view P(1.5px)>=0.5 | sub-threshold in EVERY view |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for nm in ("miss", "flat"):
        q = d[nm]["S_bar_quantiles"]
        L.append(f"| M_{nm} | {d[nm]['mean']:.4f} | {q['p10']:.4f} | {q['p50']:.4f} | {q['p90']:.4f} | "
                 f"{d[nm]['frac_S_bar<0.02']:.3f} | {d[nm]['frac_S_bar_in[0.05,0.5)']:.3f} | "
                 f"{d[nm]['frac_S_bar>=0.5']:.3f} | {d[nm]['frac_anyview_dil>=0.5']:.3f} | "
                 f"{d[nm]['frac_anyview_dil<0.5(sub-threshold everywhere)']:.3f} |")
    L.append("\n## Miss-set subsets (each vs an equal-count random M_flat subset)\n")
    L.append("| subset | n | share | S_bar p50 | AUC (mean) | R@85P (mean) | AUC (max) | R@85P (max) | rule |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for nm, r in res["subsets"].items():
        if r.get("skipped"):
            L.append(f"| {nm} | {r['n_pos']} | — | — | — | — | — | — | skipped (<100) |")
            continue
        L.append(f"| {nm} | {r['n_pos']:,} | {r['frac_of_missset']:.3f} | {r['S_bar_miss_quantiles']['p50']:.4f} | "
                 f"{r['mean']['auc']:.4f} | {r['mean']['r85']:.4f} | {r['max']['auc']:.4f} | {r['max']['r85']:.4f} | "
                 f"{r['verdict_if_headline']} |")
    L.append("\n## Single-view baseline and the multi-view lift\n")
    L.append(f"- Per-view (RAW bilinear P_k, balanced, {sv['n_views']} views): AUC mean **{sv['auc_mean']:.4f}** "
             f"(median {sv['auc_median']:.4f}, min {sv['auc_min']:.4f}, max {sv['auc_max']:.4f}); "
             f"Recall@85%P mean **{sv['r85_mean']:.4f}** (max {sv['r85_max']:.4f}, view {sv['best_view_by_r85']['view']}).")
    L.append(f"- Thresholded single-view detection (P within 1.5 px >= 0.5) of M_miss: per-view mean "
             f"**{sv['det_rate_miss_at_0.5_dil_mean']:.4f}**, any of 100 views {sv['anyview_det_rate_miss_at_0.5_dil']:.4f}; "
             f"M_flat false-alarm per-view {sv['fa_rate_flat_at_0.5_dil_mean']:.4f}, any-view {sv['anyview_fa_rate_flat_at_0.5_dil']:.4f}.")
    lf = res["lift"]
    L.append(f"- **Lift** S_bar minus single-view mean: AUC {lf['auc_multi_minus_single_mean']:+.4f}, "
             f"R@85P {lf['r85_multi_minus_single_mean']:+.4f}; minus best single view: AUC "
             f"{lf['auc_multi_minus_single_best']:+.4f}, R@85P {lf['r85_multi_minus_single_best']:+.4f}.")
    L.append(f"\nArtefacts: `out/epi/epi_accum_{scene}.json`, `out/epi/epi_accum_{scene}.png`, "
             f"`out/epi/epi_accum_{scene}_inspect_v*.png`, arrays `out/epi/epi_{{labels,samples,scores}}_{scene}.npz`.\n")
    p = os.path.join(OUT, f"EPI_ACCUM_{scene}{TAG}.md")
    open(p, "w").write("\n".join(L))
    log(f"[D:{scene}] report -> {p}")


# ============================================================ MAIN
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="lego", choices=sorted(TAGS))
    ap.add_argument("--stage", default="all", choices=["labels", "gbuf", "accum", "eval", "all"])
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--margin_px", type=float, default=3.0, help="flat margin, px-equiv (2*tau)")
    ap.add_argument("--n_hit", type=int, default=60000)
    ap.add_argument("--chunk", type=int, default=4_000_000)
    ap.add_argument("--max_sample", type=int, default=60_000_000)
    ap.add_argument("--eps_loose", type=float, default=0.02, help="pipeline visibility rel eps")
    ap.add_argument("--eps_tight", type=float, default=0.005)
    ap.add_argument("--offset", default="auto", help="'auto' (calibrate on hit-set) or 'du,dv'")
    ap.add_argument("--tag", default="", help="suffix for label/sample/result files (sensitivity arms)")
    args = ap.parse_args()
    global TAG
    TAG = args.tag
    os.makedirs(OUT, exist_ok=True)
    if args.device.startswith("cuda") and not torch.cuda.is_available():
        args.device = "cpu"
    stages = ["labels", "gbuf", "accum", "eval"] if args.stage == "all" else [args.stage]
    for s in stages:
        {"labels": stage_labels, "gbuf": stage_gbuf, "accum": stage_accum, "eval": stage_eval}[s](args.scene, args)


if __name__ == "__main__":
    main()
