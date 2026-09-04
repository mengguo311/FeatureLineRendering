"""EXPERIMENT X — PRIZE-POOL SIZING for the 3DGS-retraining pivot.

*** EVAL / ANALYSIS ONLY.  Reads the GT mesh + GT renders for LABELS and SCORES.
    Defines no method, modifies no method-path file. ***

QUESTION (frozen spec)
    Of the GT creases the frozen pipeline MISSES, what fraction g is RETRAINABLE geometric
    crease vs UNRECOVERABLE appearance-only decal?  g bounds the entire retraining upside.
    Frozen rule: g < 0.25 on lego -> strong kill;  g > 0.40 -> proceed to Experiment Y.

WHAT WE FOUND BEFORE MEASURING ANYTHING — the spec-literal split is a TAUTOLOGY
    src/mesh_oracle.py DEFINES the GT crease set as
        sel = m.face_adjacency_edges[m.face_adjacency_angles >= deg2rad(30)]
    so EVERY GT crease point sits on a >=30 deg dihedral edge BY CONSTRUCTION.  The miss-set
    is a subset of the GT crease set.  Therefore the literal test "is the dihedral above
    threshold (geometric) or ~0 (decal)?" returns GEOMETRIC for 100% of the miss-set on every
    scene, with zero measurement performed.  g_literal == 1.000 identically.

    This is not a bug in the spec's intent, it is a category error the spec inherited: in THIS
    project "decal" was never defined on the miss-set.  It was defined on the PRECISION side.
    scripts/diag2dgs.py:409-411 (the source of the "GT-mesh dihedral AUC 0.3964" result):
        crease = seen & (dmed <= 1.5)                  # linelet lands ON a GT crease
        decal  = seen & (dmed > 3.0) & teed_hi         # strong image edge FAR from any crease
    A decal is a DETECTOR FALSE POSITIVE.  It cannot appear in the miss-set, because the
    miss-set contains only GT creases.  So the spec's question, asked literally, cannot
    discriminate anything.  We report g_literal = 1.000 and flag it as vacuous.

THE NON-VACUOUS QUESTION, and what this script actually measures
    The decision the spec wants to settle is: could RETRAINING 3DGS put a carrier on these
    missed creases?  3DGS is optimised by a purely PHOTOMETRIC loss (0.8*L1 + 0.2*(1-SSIM)
    against the training renders; see ~/cglib/vfsdgs/train_static.py).  It has exactly one
    source of gradient.  So a missed GT crease is retrainable ONLY IF it leaves a photometric
    trace in the images.  If a GT crease is INVISIBLE in every render, no photometric-loss
    method - frozen post-hoc extraction OR any retraining scheme - can ever place a carrier
    there.  That is the true, information-theoretic generalisation of agy's decal wall, and it
    is directly measurable on the very images 3DGS trains on.

    So we split the miss-set into
      (i)   PHOTOMETRICALLY PRESENT  -> a real image edge exists  -> RETRAINABLE  (counts in g)
      (ii)  PHOTOMETRICALLY ABSENT   -> no image edge in any view -> UNRECOVERABLE (excluded)
    and we report the geometric MECHANISM behind (ii) so the result is explained, not just
    asserted: per crease edge we measure the maximal locally-planar patch (connected component
    of faces joined across <3 deg edges) on each side.  Two large flat sheets meeting = a real
    line.  Two slivers = one facet of a tessellated curved surface, which Blender renders
    SMOOTH-SHADED, i.e. with no image edge at all.

CALIBRATION (nothing is assumed)
    The photometric threshold is not hand-picked.  It is calibrated on the scene's own controls:
      - null   : uniformly random FOREGROUND pixels (what "no edge here" looks like)
      - hit-set: the GT creases the frozen pipeline DID recover (what "a findable edge" looks like)
    We report the full distributions and sweep the threshold, so the verdict can be read off at
    any operating point rather than resting on one number.
"""
import argparse
import json
import os
import sys
import time

import cv2
import numpy as np
import trimesh
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
OUT = os.path.join(TIER1, "out", "xy")
CACHE = os.path.join(TIER1, "cache")
MESH_DIR = os.path.expanduser("~/3dgs_line/bcr/meshes/NeRF_Mesh")
CGLIB = os.path.expanduser("~/cglib")
DS = 0.0015          # mesh_oracle sampling step -- must match exactly
ANGLE = 30.0         # mesh_oracle crease threshold -- must match exactly
FLAT_DEG = 3.0       # "locally planar" edge threshold for the patch decomposition


def grad_mag(scene, v):
    """Sobel gradient magnitude of the GT training render, RGBA composited over white
    exactly as cmepi_cache_edges.py / train_static.py do."""
    p = f"{CGLIB}/data/full/{scene}/train/r_{v}.png"
    im = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    assert im is not None, p
    rgb = im[..., :3].astype(np.float32) / 255.0
    a = im[..., 3:4].astype(np.float32) / 255.0 if im.shape[2] == 4 else 1.0
    comp = rgb * a + 1.0 * (1.0 - a)
    g = cv2.cvtColor((comp * 255).astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, 3)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, 3)
    m = np.sqrt(gx * gx + gy * gy) / 4.0        # /4 -> comparable to a centred difference
    fg = (a[..., 0] > 0.5) if im.shape[2] == 4 else np.ones(g.shape, bool)
    return m, fg


def dilate_max(m, tau_px):
    """max gradient within tau_px -- the recall tolerance is tau px, so a crease counts as
    photometrically present if an edge lies within the same tolerance."""
    k = int(2 * np.ceil(tau_px) + 1)
    return cv2.dilate(m, np.ones((k, k), np.uint8))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", required=True)
    ap.add_argument("--cloud", required=True, help="npz with P/support/surface_keep/resid")
    ap.add_argument("--resid_max", type=float, default=1.0)
    ap.add_argument("--min_support", type=int, default=2)
    ap.add_argument("--tau_px", type=float, default=1.5)
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    from src import common, view_split                            # noqa: E402
    VIEWS = view_split.TEST

    # ---------- 1. GT crease points + per-TEST-view visibility (cached, mesh-free) --------
    gt = np.load(os.path.join(CACHE, f"dexp0_gt_{args.scene}_a{int(ANGLE)}.npz"))
    crease_pts = gt["crease_pts"]
    bbox_diag = float(gt["bbox_diag"])
    vis_idx = {v: gt[f"idx{v}"] for v in VIEWS}
    vis_uv = {v: gt[f"uv{v}"] for v in VIEWS}
    M = len(crease_pts)
    seen = np.zeros(M, bool)
    for v in VIEWS:
        seen[vis_idx[v]] = True
    seen_idx = np.where(seen)[0]
    print(f"[X:{args.scene}] crease_pts={M}  seen in >=1 TEST view={len(seen_idx)}  "
          f"bbox_diag={bbox_diag:.4f}", flush=True)

    # ---------- 2. reconstruct point -> source EDGE map + per-edge geometry ---------------
    m = trimesh.load(f"{MESH_DIR}/{args.scene}_new.obj", process=True)
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate([g for g in m.geometry.values()])
    V = np.asarray(m.vertices, np.float64)
    FA = np.asarray(m.area_faces, np.float64)
    adj = np.asarray(m.face_adjacency)
    adjE = np.asarray(m.face_adjacency_edges)
    deg = np.degrees(np.asarray(m.face_adjacency_angles))
    sel = np.where(deg >= ANGLE)[0]
    A, B = V[adjE[sel, 0]], V[adjE[sel, 1]]
    L = np.linalg.norm(B - A, axis=1)
    npt = np.maximum(2, (L / DS).astype(int) + 1)
    edge_of_pt = np.repeat(np.arange(len(sel)), npt)
    assert len(edge_of_pt) == M, (len(edge_of_pt), M, "sampling map mismatch")
    # byte-level verification that we reproduced mesh_oracle._sample_edges exactly
    chk = np.random.default_rng(0).choice(len(sel), size=min(2000, len(sel)), replace=False)
    off = np.concatenate([[0], np.cumsum(npt)])
    err = 0.0
    for i in chk:
        ts = np.linspace(0, 1, npt[i])
        rec = A[i][None] + ts[:, None] * (B[i] - A[i])[None]
        err = max(err, float(np.abs(rec - crease_pts[off[i]:off[i + 1]]).max()))
    assert err < 1e-9, f"sampling reconstruction mismatch {err}"
    print(f"[X:{args.scene}] point->edge map verified on {len(chk)} edges (max err {err:.2e})",
          flush=True)
    theta0 = deg[sel]

    # locally-planar patch decomposition: connected components of faces joined across <3 deg
    flat = deg < FLAT_DEG
    F = len(FA)
    G = coo_matrix((np.ones(flat.sum(), np.int8), (adj[flat, 0], adj[flat, 1])), shape=(F, F))
    ncomp, lab = connected_components(G, directed=False)
    patch_area = np.bincount(lab, weights=FA, minlength=ncomp)
    a1 = patch_area[lab[adj[sel, 0]]]
    a2 = patch_area[lab[adj[sel, 1]]]
    # characteristic half-width of the SMALLER adjacent flat sheet, in pixels
    px_world = 4.031128875572954 / (0.5 * 800 / np.tan(0.5 * 0.6911112070083618))
    sheet_px = np.sqrt(np.minimum(a1, a2)) / px_world
    print(f"[X:{args.scene}] flat patches (<{FLAT_DEG}deg) = {ncomp};  smaller-sheet width "
          f"px: p10={np.percentile(sheet_px,10):.2f} p50={np.percentile(sheet_px,50):.2f} "
          f"p90={np.percentile(sheet_px,90):.2f}", flush=True)

    # ---------- 3. frozen-pipeline coverage -> MISS-SET -----------------------------------
    z = np.load(args.cloud)
    keep = (z["support"] >= args.min_support) & z["surface_keep"] & (z["resid"] <= args.resid_max)
    P = z["P"][keep]
    cams, _ = common.load_cameras(args.scene)
    zs = []
    for v in VIEWS:
        q = crease_pts[vis_idx[v]]
        zs.append((cams[v].w2c[:3, :3] @ q.T).T[:, 2] + cams[v].w2c[2, 3])
    zmed = float(np.median(np.concatenate(zs)))
    rad = args.tau_px * zmed / cams[VIEWS[0]].f
    d3 = cKDTree(P).query(crease_pts[seen_idx], k=1, workers=-1)[0]
    rec3 = d3 <= rad
    print(f"[X:{args.scene}] cloud {args.cloud}: raw={len(z['P'])} kept={len(P)}  "
          f"radius(px{args.tau_px}_equiv)={rad:.6f}  3D recall={rec3.mean():.4f}  "
          f"miss={int((~rec3).sum())}", flush=True)

    # 2D image-space cross-check, exactly the published tau=1.5px convention
    rec2 = np.zeros(len(seen_idx), bool)
    pos_in_seen = -np.ones(M, np.int64)
    pos_in_seen[seen_idx] = np.arange(len(seen_idx))
    photo_max = np.zeros(M, np.float32)
    photo_raw = np.zeros(M, np.float32)
    photo_n = np.zeros(M, np.int32)
    null_stats, null_raw_stats = [], []
    for v in VIEWS:
        cam = cams[v]
        pv = (cam.w2c[:3, :3] @ P.T).T + cam.w2c[:3, 3]
        ok = pv[:, 2] > 1e-6
        uvp = (cam.K @ pv[ok].T).T
        uvp = uvp[:, :2] / uvp[:, 2:3]
        q = vis_uv[v]
        dd = cKDTree(uvp).query(q, k=1, workers=-1)[0] if len(uvp) else np.full(len(q), 1e9)
        rec2[pos_in_seen[vis_idx[v]]] |= (dd <= args.tau_px)
        g, fg = grad_mag(args.scene, v)
        gd = dilate_max(g, args.tau_px)
        u = np.clip(np.round(q[:, 0]).astype(int), 0, 799)
        vv = np.clip(np.round(q[:, 1]).astype(int), 0, 799)
        i = vis_idx[v]
        photo_max[i] = np.maximum(photo_max[i], gd[vv, u])
        photo_raw[i] = np.maximum(photo_raw[i], g[vv, u])
        photo_n[i] += 1
        fgi = np.argwhere(fg)
        rng = np.random.default_rng(v)
        sub = fgi[rng.choice(len(fgi), size=min(len(fgi), 20000), replace=False)]
        null_stats.append(gd[sub[:, 0], sub[:, 1]])
        null_raw_stats.append(g[sub[:, 0], sub[:, 1]])
    null = np.concatenate(null_stats)
    null_raw = np.concatenate(null_raw_stats)
    print(f"[X:{args.scene}] 2D recall(any TEST view, tau={args.tau_px}px) = {rec2.mean():.4f}",
          flush=True)

    # ---------- 4. classify the miss-set ---------------------------------------------------
    pm = photo_max[seen_idx]
    pr = photo_raw[seen_idx]
    th = theta0[edge_of_pt[seen_idx]]
    sw = sheet_px[edge_of_pt[seen_idx]]
    miss = ~rec3
    res = {"scene": args.scene, "cloud": os.path.basename(args.cloud),
           "n_cloud_raw": int(len(z["P"])), "n_cloud_kept": int(len(P)),
           "tau_px": args.tau_px, "radius_world": rad, "bbox_diag": bbox_diag,
           "views_TEST": list(map(int, VIEWS)),
           "n_crease_pts": int(M), "n_seen": int(len(seen_idx)),
           "recall_3D": float(rec3.mean()), "recall_2D_anyview": float(rec2.mean()),
           "n_miss_3D": int(miss.sum()), "miss_fraction_3D": float(miss.mean()),
           "n_miss_2D": int((~rec2).sum()), "miss_fraction_2D": float((~rec2).mean())}

    # 4a. the SPEC-LITERAL split (tautological -- reported, not hidden)
    res["spec_literal"] = {
        "definition": "geometric = dihedral >= 30 deg on GT mesh; decal = dihedral ~0 (flat)",
        "n_geometric": int((th[miss] >= ANGLE).sum()),
        "n_decal": int((th[miss] < ANGLE).sum()),
        "g_literal": float((th[miss] >= ANGLE).mean()),
        "TAUTOLOGY": ("the GT crease set IS defined as dihedral>=30 edges, so every miss is "
                      "'geometric' by construction; g_literal is 1.000 with no measurement"),
    }

    # 4b. photometric calibration + the honest split
    qs = [1, 5, 10, 25, 50, 75, 90, 95, 99]
    res["photometric_calibration"] = {
        "stat": f"max Sobel |grad| of the GT render within {args.tau_px}px, max over TEST views",
        "null_random_fg_pixels": {f"p{q}": round(float(np.percentile(null, q)), 3) for q in qs},
        "hit_set_recovered_creases": {f"p{q}": round(float(np.percentile(pm[rec3], q)), 3)
                                      for q in qs} if rec3.any() else {},
        "miss_set": {f"p{q}": round(float(np.percentile(pm[miss], q)), 3) for q in qs},
    }
    sweep = []
    for T in [2, 4, 6, 8, 10, 12, 16, 20, 25, 30, 40]:
        sweep.append({"thresh": T,
                      "null_frac_above": round(float((null >= T).mean()), 4),
                      "hit_frac_above": round(float((pm[rec3] >= T).mean()), 4) if rec3.any() else None,
                      "miss_frac_above_g": round(float((pm[miss] >= T).mean()), 4)})
    res["g_photometric_sweep"] = sweep

    def auc(pos, neg, n=200000):
        """threshold-free separation; 0.5 = no information. Rank-based (Mann-Whitney)."""
        rg = np.random.default_rng(0)
        a = pos if len(pos) <= n else pos[rg.choice(len(pos), n, replace=False)]
        b = neg if len(neg) <= n else neg[rg.choice(len(neg), n, replace=False)]
        if not len(a) or not len(b):
            return None
        allv = np.concatenate([a, b])
        r = np.argsort(np.argsort(allv)) + 1.0
        return round(float((r[:len(a)].sum() - len(a) * (len(a) + 1) / 2) / (len(a) * len(b))), 4)

    res["photometric_AUC"] = {
        "note": ("threshold-free. >0.5 means the first group has HIGHER image gradient. "
                 "'raw' reads the pixel itself; 'dil' takes the max within tau_px."),
        "AUC_hit_vs_miss_dil": auc(pm[rec3], pm[miss]),
        "AUC_hit_vs_miss_raw": auc(pr[rec3], pr[miss]),
        "AUC_allcrease_vs_randomfg_dil": auc(pm, null),
        "AUC_allcrease_vs_randomfg_raw": auc(pr, null_raw),
        "AUC_missset_vs_randomfg_raw": auc(pr[miss], null_raw),
        "AUC_hitset_vs_randomfg_raw": auc(pr[rec3], null_raw),
    }
    res["photometric_raw_undilated"] = {
        "null_random_fg": {f"p{q}": round(float(np.percentile(null_raw, q)), 3) for q in qs},
        "hit_set": {f"p{q}": round(float(np.percentile(pr[rec3], q)), 3) for q in qs}
                   if rec3.any() else {},
        "miss_set": {f"p{q}": round(float(np.percentile(pr[miss], q)), 3) for q in qs},
    }
    # operating point: the threshold at which the NULL false-positive rate is 5%
    T5 = float(np.percentile(null, 95))
    res["operating_point"] = {
        "rule": "threshold = p95 of the random-foreground null (5% null FP rate)",
        "threshold": round(T5, 3),
        "hit_set_frac_above": round(float((pm[rec3] >= T5).mean()), 4) if rec3.any() else None,
        "g_honest": round(float((pm[miss] >= T5).mean()), 4),
        "n_retrainable": int((pm[miss] >= T5).sum()),
        "n_unrecoverable": int((pm[miss] < T5).sum()),
    }

    # 4c. mechanism: cross-tab by dihedral band and flat-sheet width
    bands = [(29.9, 30.1, "EXACTLY 30 deg (12-gon tessellation)"),
             (30.1, 44.0, "30-44 deg"), (44.0, 60.0, "44-60 deg"),
             (60.0, 89.9, "60-90 deg"), (89.9, 90.1, "EXACTLY 90 deg (box corner)"),
             (90.1, 181.0, ">90 deg")]
    tab = []
    for lo, hi, nm in bands:
        b = (th >= lo) & (th < hi)
        if b.sum() == 0:
            continue
        bm = b & miss
        tab.append({"band": nm, "n_seen": int(b.sum()),
                    "frac_of_seen": round(float(b.mean()), 4),
                    "recall_3D": round(float(rec3[b].mean()), 4),
                    "n_miss": int(bm.sum()),
                    "frac_of_missset": round(float(bm.sum() / max(miss.sum(), 1)), 4),
                    "photo_p50": round(float(np.median(pm[b])), 3),
                    "photo_raw_p50": round(float(np.median(pr[b])), 3),
                    "photo_frac_above_T5": round(float((pm[b] >= T5).mean()), 4),
                    "flat_sheet_px_p50": round(float(np.median(sw[b])), 3)})
    res["dihedral_band_crosstab"] = tab

    for nm, msk in (("all_seen", np.ones(len(seen_idx), bool)), ("miss_set", miss)):
        res[f"flat_sheet_px_{nm}"] = {f"p{q}": round(float(np.percentile(sw[msk], q)), 3)
                                      for q in qs}

    np.savez_compressed(os.path.join(OUT, f"xy_expX_{args.scene}{args.tag}.npz"),
                        seen_idx=seen_idx, rec3=rec3, rec2=rec2, d3=d3.astype(np.float32),
                        photo_max=pm, photo_raw=pr, null_raw=null_raw.astype(np.float32),
                        theta0_pt=th.astype(np.float32),
                        sheet_px_pt=sw.astype(np.float32), null=null.astype(np.float32),
                        radius=rad, T5=T5)
    jp = os.path.join(OUT, f"xy_expX_{args.scene}{args.tag}.json")
    json.dump(res, open(jp, "w"), indent=1)
    print(json.dumps(res, indent=1))
    print(f"[X:{args.scene}] wrote {jp}  ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
