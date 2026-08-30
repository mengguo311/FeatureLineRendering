"""DexiNed-primary PHASE 0 — the coverage-ceiling gatekeeper.

*** EVAL / ANALYSIS SCRIPT.  It reads the GT mesh (via src.mesh_oracle) to build LABELS and
    to SCORE.  The METHOD PATH it measures -- DexiNed 2D edges + 3DGS rendered depth -- never
    touches the mesh: the lifted cloud is produced by lift_view() below from
    out/dexined_edges_<scene>/ + render.render_gbuffer only. ***

THE QUESTION
    Every method so far re-ranks a FIXED pool of vanilla-3DGS gaussians, so its recall is
    bounded by whether a gaussian exists near each GT crease at all.  On lego many GT creases
    are FLAT DECALS with no geometric signal, and gaussians seed on geometry, so they are
    structurally uncoverable.  DexiNed SEES those creases (they are photometric).  Does
    backprojecting DexiNed edges through the 3DGS rendered depth put 3D points where the
    gaussian pool has none?

WHAT IS MEASURED (held-out TEST views {5,15,...,95}, no tuning)
  1. GAUSSIAN MISS-SET.  visible GT crease point q in view v is COVERED iff some VISIBLE
     de-floatered gaussian centre projects within tau px of q's projection in v.
       miss-set (2D, per (q,v) pair)  -- the metric space the 0.56/0.79 ceiling lives in
       miss-set (3D, per q)           -- q covered in NO test view where it is visible
  2. DEXINED -> 3D LIFT.  nms_thin(dexined prob) >= thr, backprojected with 5 depth arms
     (naive / naive_fill / fgmin / median / medmin -- see DEPTH_ARMS).
  3. RECOVERY.
       R_miss_2D_own : missed (q,v) with a lifted point from view v within delta px.
                       *** DEGENERATE BY CONSTRUCTION *** -- lifting with v's own depth
                       reprojects exactly onto v's edge pixels, so this measures only
                       "does DexiNed SEE it in 2D".  Reported as the 2D CEILING, not as
                       evidence that the depth lift works.
       R_miss_2D_loo : missed (q,v) with a lifted point from views != v, occlusion-culled
                       against v's gaussian z-buffer, within delta px.  THIS one tests the
                       3D placement in pixel space.  PRIMARY 2D number.
       R_miss_3D     : 3D-miss-set q with a lifted point within a 3D chamfer radius
                       (1.5% of the mesh bbox diagonal, plus tighter sensitivity radii).
     Plus OVERALL lifted recall over ALL visible GT creases (vs the fixed-pool ceiling)
     and raw precision of the lifted cloud (sanity only -- precision is Phase 1's job).
"""
import os
import sys
import json
import time
import argparse

import cv2
import numpy as np
import torch
from scipy import ndimage
from scipy.spatial import cKDTree

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
OUT = os.path.join(TIER1, "out")
CACHE = os.path.join(TIER1, "cache")

from src import common, render, view_split, visibility          # METHOD PATH
from src.epipolar_consensus import nms_thin, fill_depth         # METHOD PATH

TAUS = (1.5, 2.5)
DEPTH_ARMS = ("naive", "naive_fill", "fgmin", "median", "medmin")
ROBUST_ARM = "medmin"
NAIVE_ARM = "naive"


# ----------------------------------------------------------------- METHOD PATH (mesh-free)
def edge_mask(cache_dir, v, thr, key, nms=True):
    """DexiNed prob map -> thinned binary edge mask + the (blurred) prob for normals."""
    z = np.load(os.path.join(cache_dir, f"v{v:03d}.npz"))
    p = z[key].astype(np.float32)
    pt = nms_thin(p) if nms else p
    return pt >= thr, p


def edge_normals(p, blur=1.0):
    """Unit image gradient of the edge probability = the 2D edge normal at each pixel."""
    ps = cv2.GaussianBlur(p, (0, 0), blur) if blur > 0 else p
    gx = cv2.Sobel(ps, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(ps, cv2.CV_32F, 0, 1, ksize=3)
    n = np.sqrt(gx * gx + gy * gy)
    flat = n < 1e-9
    dx = np.where(flat, 1.0, gx / np.maximum(n, 1e-9)).astype(np.float32)
    dy = np.where(flat, 0.0, gy / np.maximum(n, 1e-9)).astype(np.float32)
    return dx, dy


def _sample_min_along_normal(D, u, v_, dx, dy, half=2.0, step=0.5):
    """min over a +-half px window along the 2D edge normal of depth map D (inf-safe)."""
    H, W = D.shape
    best = np.full(len(u), np.inf, np.float64)
    offs = np.arange(-half, half + 1e-9, step)
    for s in offs:
        uu = np.clip(np.round(u + s * dx).astype(np.int64), 0, W - 1)
        vv = np.clip(np.round(v_ + s * dy).astype(np.int64), 0, H - 1)
        d = D[vv, uu]
        ok = np.isfinite(d)
        best = np.where(ok & (d < best), d, best)
    return best


def unproject(u, v_, z, cam):
    """pixel (u,v) + CAMERA-SPACE Z depth -> world XYZ.  render_gbuffer's depth is campts[:,2]
    (a z-depth, not a ray length), so X = z*(u-cx)/f, Y = z*(v-cy)/f, Z = z."""
    f, cx, cy = cam.f, cam.K[0, 2], cam.K[1, 2]
    Xc = np.stack([z * (u - cx) / f, z * (v_ - cy) / f, z], 1)
    R, t = cam.w2c[:3, :3], cam.w2c[:3, 3]
    return (Xc - t) @ R                      # R^T (Xc - t)


def lift_view(cache_dir, v, cam, gbuf, thr, key, arms=DEPTH_ARMS, halfpix=0.0):
    """DexiNed edge pixels of view v -> {arm: (P[world,3], uv[N,2])}.  MESH-FREE.

    halfpix: added to (u,v) before unprojection AND before 2D scoring.  The cached DexiNed
    maps were computed on the GT Blender PNGs, whose pixel grid sits +0.5 px from tier1's
    projection grid (scripts/explore/check_2dgs_align.py measured +0.492 px): tier1 puts
    index i at u = f*X/Z + W/2, Blender puts it at i+0.5.  Uncorrected (halfpix=0) is what
    every prior repo number used (URS 0.7617, R@1.5 0.5572) and is the comparable arm;
    halfpix=0.5 is the geometrically correct one.  Both are reported."""
    m, p = edge_mask(cache_dir, v, thr, key)
    dmean = gbuf["depth"].detach().cpu().numpy().astype(np.float64)
    dmed = gbuf["depth_median"].detach().cpu().numpy().astype(np.float64)
    dmean[~np.isfinite(dmean)] = np.inf
    dmed[~np.isfinite(dmed)] = np.inf
    dfill = fill_depth(np.where(np.isfinite(dmean), dmean, np.nan)).astype(np.float64)
    dx, dy = edge_normals(p)
    vv, uu = np.nonzero(m)
    u = uu.astype(np.float64)          # integer photo index -- used to SAMPLE the buffers
    v_ = vv.astype(np.float64)
    uo, vo = u + halfpix, v_ + halfpix  # tier1 continuous coords -- used for GEOMETRY
    ndx, ndy = dx[vv, uu].astype(np.float64), dy[vv, uu].astype(np.float64)
    cand = {
        "naive": dmean[vv, uu],
        "naive_fill": dfill[vv, uu],
        "fgmin": _sample_min_along_normal(dmean, u, v_, ndx, ndy),
        "median": dmed[vv, uu],
        "medmin": _sample_min_along_normal(dmed, u, v_, ndx, ndy),
    }
    out = {}
    for a in arms:
        z = cand[a]
        ok = np.isfinite(z) & (z > 1e-6)
        out[a] = (unproject(uo[ok], vo[ok], z[ok], cam),
                  np.stack([uo[ok], vo[ok]], 1),
                  int(m.sum()), int(ok.sum()))
    return out


# ----------------------------------------------------------------- EVAL (mesh) -- labels
def gt_labels(scene, views, angle_deg=30.0, force=False):
    """Per TEST view: indices into crease_pts of the VISIBLE GT crease points + their uv.
    Cached; the mesh is read only here."""
    p = os.path.join(CACHE, f"dexp0_gt_{scene}_a{int(angle_deg)}.npz")
    if os.path.exists(p) and not force:
        z = np.load(p)
        return (z["crease_pts"], {int(v): (z[f"idx{v}"], z[f"uv{v}"]) for v in views},
                float(z["bbox_diag"]))
    from src.mesh_oracle import MeshOracle          # EVAL ONLY
    cams, _ = common.load_cameras(scene)
    o = MeshOracle(scene, angle_deg=angle_deg)
    q = o.crease_pts
    diag = float(np.linalg.norm(o.V.max(0) - o.V.min(0)))
    store = {"crease_pts": q, "bbox_diag": np.float64(diag)}
    res = {}
    for v in views:
        t0 = time.time()
        cam = cams[v]
        depth = o.render_depth(cam).detach().cpu().numpy()
        campts = (cam.w2c[:3, :3] @ q.T).T + cam.w2c[:3, 3]
        zq = campts[:, 2]
        uv = (cam.K @ campts.T).T
        uv = uv[:, :2] / np.clip(uv[:, 2:3], 1e-9, None)
        ui = np.round(uv[:, 0]).astype(np.int64)
        vi = np.round(uv[:, 1]).astype(np.int64)
        inb = (zq > 0) & (ui >= 0) & (ui < cam.W) & (vi >= 0) & (vi < cam.H)
        idx = np.where(inb)[0]
        best = np.full(len(idx), 1e9)
        for du in (-1, 0, 1):                       # 3x3 min |dz| cull, eps 0.015
            for dv in (-1, 0, 1):
                uu = np.clip(ui[idx] + du, 0, cam.W - 1)
                vv2 = np.clip(vi[idx] + dv, 0, cam.H - 1)
                best = np.minimum(best, np.abs(zq[idx] - depth[vv2, uu]))
        keep = idx[best < 0.015]
        res[int(v)] = (keep.astype(np.int64), uv[keep])
        store[f"idx{v}"], store[f"uv{v}"] = res[int(v)]
        o._depth_cache.clear()
        torch.cuda.empty_cache()
        print(f"  [gt] {scene} v{v:3d}: visible crease pts {len(keep):8d}  "
              f"({time.time()-t0:.1f}s)", flush=True)
    np.savez(p, **store)
    print(f"  [gt] wrote {p}", flush=True)
    return q, res, diag


# ----------------------------------------------------------------- CONTROLS
def ctrl_random_fg(gbuf, cam, n, rng, alpha_min=0.5):
    """n random FOREGROUND pixels lifted with the same median depth -> the chance cloud at
    matched density on the same surface. Answers: how much of the miss-set does ANY
    equally-dense point set on the 3DGS surface 'recover' by accident?"""
    a = gbuf["alpha"].detach().cpu().numpy()
    d = gbuf["depth_median"].detach().cpu().numpy().astype(np.float64)
    fg = np.argwhere((a >= alpha_min) & np.isfinite(d))
    if len(fg) == 0:
        return np.zeros((0, 3)), np.zeros((0, 2))
    sel = fg[rng.choice(len(fg), size=min(n, len(fg)), replace=False)]
    u = sel[:, 1].astype(np.float64)
    v_ = sel[:, 0].astype(np.float64)
    return unproject(u, v_, d[sel[:, 0], sel[:, 1]], cam), np.stack([u, v_], 1)


def ctrl_shuffle_depth(P, uv, cam, rng):
    """SAME DexiNed edge pixels, depths randomly permuted among them. Isolates whether the
    DEPTH LIFT does any work, or whether the 2D edge locations alone explain the score."""
    if len(P) == 0:
        return P, uv
    campts = (cam.w2c[:3, :3] @ P.T).T + cam.w2c[:3, 3]
    z = campts[:, 2].copy()
    rng.shuffle(z)
    return unproject(uv[:, 0], uv[:, 1], z, cam), uv


def voxel_budget(P, budget, iters=30):
    """Voxel-dedup P down to ~budget points by bisecting the voxel size -- the protocol
    URS_RESULTS.md used to cap its carrier at a 3x budget (89,748 pts on lego).  Applying the
    SAME cap to every cloud, including the controls, is what makes a coverage number a
    statement about the cloud rather than about how many points it has."""
    if budget <= 0 or len(P) <= budget:
        return np.arange(len(P))
    mn = P.min(0)
    def keep_at(vs):
        q = np.floor((P - mn) / vs).astype(np.int64)
        M = np.int64(1 << 21)
        key = (q[:, 0] % M) * M * M + (q[:, 1] % M) * M + (q[:, 2] % M)
        _, idx = np.unique(key, return_index=True)
        return np.sort(idx)
    lo, hi = 1e-5, float(np.linalg.norm(P.max(0) - mn))
    best = keep_at(hi)
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        k = keep_at(mid)
        if len(k) > budget:
            lo = mid
        else:
            hi = mid
            best = k
        if abs(len(k) - budget) <= 0.01 * budget:
            return k
    return best


# ----------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", required=True, choices=["lego", "chair"])
    ap.add_argument("--thr", type=float, default=0.5)
    ap.add_argument("--key", default="native", choices=["native", "ms"])
    ap.add_argument("--delta", type=float, default=1.5, help="2D recovery radius (px)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--force_gt", action="store_true")
    ap.add_argument("--halfpix", type=float, default=0.0,
                    help="0.0 = repo-comparable (URS/R@1.5 convention); 0.5 = grid-correct")
    ap.add_argument("--src", default="test", choices=["test", "train"],
                    help="which views the DexiNed cloud is lifted FROM. 'train' = URS-legal, "
                         "zero contact with the scored TEST views.")
    ap.add_argument("--n_src", type=int, default=20, help="how many TRAIN views when src=train")
    ap.add_argument("--tag", default="")
    ap.add_argument("--budget", type=int, default=0,
                    help="voxel-dedup EVERY cloud (controls included) to this many points, "
                         "so coverage is a claim about the cloud and not about its density. "
                         "URS used 89748 on lego.")
    args = ap.parse_args()

    scene = args.scene
    views = view_split.TEST                       # views SCORED on (always held-out TEST)
    if args.src == "train":
        tr = view_split.TRAIN
        lift_views = [tr[i] for i in np.linspace(0, len(tr) - 1, args.n_src).astype(int)]
    else:
        lift_views = list(views)                  # views LIFTED from
    dex = os.path.join(OUT, f"dexined_edges_{scene}")
    assert os.path.isdir(dex), dex

    print(f"[p0] {scene}  score_views(TEST)={views}\n[p0] lift_views({args.src}, n={len(lift_views)})={lift_views}\n[p0] key={args.key} thr={args.thr} halfpix={args.halfpix}", flush=True)
    crease_pts, gt, bbox_diag = gt_labels(scene, views, force=args.force_gt)
    print(f"[p0] crease_pts {len(crease_pts)}  bbox_diag {bbox_diag:.4f}", flush=True)

    cams, _ = common.load_cameras(scene)
    g = common.load_gaussians(scene)
    keep = render.defloat_mask(g["mu"], g["opacity"])
    X_pool, X_raw = g["mu"][keep], g["mu"]
    print(f"[p0] gaussians raw {len(X_raw)}  pool(de-floatered) {len(X_pool)}", flush=True)

    # ---- per-view: gbuffer, gaussian coverage, dexined lift
    covered = {t: {} for t in TAUS}          # tau -> view -> bool over gt idx
    covered_raw = {t: {} for t in TAUS}
    lifted = {a: {} for a in DEPTH_ARMS}     # arm -> view -> world P
    lifted_uv = {a: {} for a in DEPTH_ARMS}
    depth_np, edge_stats = {}, []
    for v in sorted(set(views) | set(lift_views)):
        t0 = time.time()
        cam = cams[v]
        gb = render.render_gbuffer(g, keep, cam, with_median_depth=True)
        row = {"view": int(v)}
        if v in views:                                    # ---- SCORING view (mesh labels)
            depth_np[v] = gb["depth"].detach().cpu().numpy()
            idx, uvq = gt[v]
            vis, uvg, _ = visibility.visible_mask(X_pool, cam, gb["depth"])
            d_pool = cKDTree(uvg[vis]).query(uvq, k=1)[0]
            visr, uvr, _ = visibility.visible_mask(X_raw, cam, gb["depth"])
            d_raw = cKDTree(uvr[visr]).query(uvq, k=1)[0]
            for t in TAUS:
                covered[t][v] = d_pool <= t
                covered_raw[t][v] = d_raw <= t
            row.update({"n_gt_vis": int(len(idx)),
                        "cov_pool_1.5": float(covered[1.5][v].mean()),
                        "cov_raw_1.5": float(covered_raw[1.5][v].mean())})
        if v in lift_views:                               # ---- SOURCE view (method path)
            L = lift_view(dex, v, cam, gb, args.thr, args.key, halfpix=args.halfpix)
            for a in DEPTH_ARMS:
                lifted[a][v], lifted_uv[a][v] = L[a][0], L[a][1]
            row.update({"n_edge_px": L[ROBUST_ARM][2],
                        "n_lifted": {a: L[a][3] for a in DEPTH_ARMS}})
        edge_stats.append(row)
        print(f"  v{v:3d}: " +
              (f"gt_vis {row.get('n_gt_vis', 0):7d} cov_pool@1.5 "
               f"{row.get('cov_pool_1.5', float('nan')):.4f}  " if v in views else " " * 34) +
              (f"edge_px {row.get('n_edge_px', 0):6d} lifted[{ROBUST_ARM}] "
               f"{row.get('n_lifted', {}).get(ROBUST_ARM, 0):6d}" if v in lift_views else "") +
              f"  ({time.time()-t0:.1f}s)", flush=True)
        del gb
        torch.cuda.empty_cache()

    # ---------------------------------------------------------------- MISS-SET
    res = {"scene": scene, "views": [int(v) for v in views], "split": "test",
           "key": args.key, "thr": args.thr, "delta_px": args.delta,
           "n_crease_pts": int(len(crease_pts)), "bbox_diag": bbox_diag,
           "n_gauss_raw": int(len(X_raw)), "n_gauss_pool": int(len(X_pool)),
           "per_view": edge_stats}

    miss2d, gt2d = {}, {}
    for t in TAUS:
        nmiss = sum(int((~covered[t][v]).sum()) for v in views)
        ntot = sum(int(len(gt[v][0])) for v in views)
        nmiss_r = sum(int((~covered_raw[t][v]).sum()) for v in views)
        miss2d[t] = {v: ~covered[t][v] for v in views}
        gt2d[t] = ntot
        res[f"missset_2d_tau{t}"] = {
            "n_gt_pairs": ntot, "n_miss": nmiss, "miss_fraction": nmiss / max(ntot, 1),
            "cover_fraction_pool": 1 - nmiss / max(ntot, 1),
            "cover_fraction_raw": 1 - nmiss_r / max(ntot, 1),
            "per_view_miss_fraction": [float((~covered[t][v]).mean()) for v in views],
        }

    # 3D miss-set: crease point covered in NO test view where it is visible
    for t in TAUS:
        seen = np.zeros(len(crease_pts), bool)
        cov_any = np.zeros(len(crease_pts), bool)
        for v in views:
            idx, _ = gt[v]
            seen[idx] = True
            cov_any[idx] |= covered[t][v]
        miss3d = seen & ~cov_any
        res[f"missset_3d_tau{t}"] = {
            "n_visible_pts": int(seen.sum()), "n_miss": int(miss3d.sum()),
            "miss_fraction": float(miss3d.sum() / max(seen.sum(), 1))}
        if t == 1.5:
            miss3d_15, seen_15 = miss3d, seen
        if t == 2.5:
            miss3d_25, seen_25 = miss3d, seen

    # pixel-level dedup cross-check (comparable to LEGO_CEILING_AUTOPSY figure B)
    px = {}
    for t in TAUS:
        npx = nmisspx = 0
        for v in views:
            idx, uvq = gt[v]
            ui = np.clip(np.round(uvq[:, 0]).astype(int), 0, 799)
            vi = np.clip(np.round(uvq[:, 1]).astype(int), 0, 799)
            lin = vi * 800 + ui
            uniq, first = np.unique(lin, return_index=True)
            # a PIXEL is covered if ANY crease point landing on it is covered
            cvp = np.zeros(800 * 800, bool)
            np.logical_or.at(cvp, lin, covered[t][v])
            npx += len(uniq)
            nmisspx += int((~cvp[uniq]).sum())
        px[t] = {"n_gt_px": npx, "n_miss_px": nmisspx,
                 "miss_fraction": nmisspx / max(npx, 1)}
    res["missset_2d_pixeldedup"] = {str(t): px[t] for t in TAUS}

    print("\n" + "=" * 88)
    print(f"STEP 1 — GAUSSIAN MISS-SET  ({scene}, held-out TEST, {len(views)} views)")
    print("=" * 88)
    for t in TAUS:
        a, b, c = res[f"missset_2d_tau{t}"], res[f"missset_3d_tau{t}"], px[t]
        print(f"  tau={t}:  2D point-level  |miss|/|GT| = {a['miss_fraction']:.4f}"
              f"   ({a['n_miss']}/{a['n_gt_pairs']})   pool-cover {a['cover_fraction_pool']:.4f}"
              f"  raw-cover {a['cover_fraction_raw']:.4f}")
        print(f"           2D pixel-dedup  |miss|/|GT| = {c['miss_fraction']:.4f}"
              f"   ({c['n_miss_px']}/{c['n_gt_px']})")
        print(f"           3D any-view     |miss|/|GT| = {b['miss_fraction']:.4f}"
              f"   ({b['n_miss']}/{b['n_visible_pts']})")

    # ---------------------------------------------------------------- RECOVERY
    r3_radii = {"chamfer_1.5pct_bbox": 0.015 * bbox_diag,
                "chamfer_0.5pct_bbox": 0.005 * bbox_diag}
    # 1.5 px-equivalent at the median GT-crease depth, per scene
    zmed = float(np.median(np.concatenate(
        [((cams[v].w2c[:3, :3] @ crease_pts[gt[v][0]].T).T + cams[v].w2c[:3, 3])[:, 2]
         for v in views])))
    r3_radii["px1.5_equiv"] = args.delta * zmed / cams[views[0]].f
    res["chamfer_radii"] = r3_radii
    res["median_crease_depth"] = zmed
    print(f"\n  3D radii: " + "  ".join(f"{k}={vv:.5f}" for k, vv in r3_radii.items()))

    depth_t = {v: torch.tensor(depth_np[v], device="cuda") for v in views}
    tree_gt3 = cKDTree(crease_pts)                       # for 3D precision
    seen_idx = np.where(seen_15)[0]
    miss_local = miss3d_15[seen_idx]
    miss_local25 = miss3d_25[seen_idx]

    # -------- assemble every cloud to be scored, ALL on the identical measurement --------
    rng = np.random.default_rng(0)
    clouds = {a: (lifted[a], lifted_uv[a], lift_views) for a in DEPTH_ARMS}
    cr_P, cr_uv, cs_P, cs_uv, gp_P, gp_uv = {}, {}, {}, {}, {}, {}
    for v in sorted(set(views) | set(lift_views)):
        cam = cams[v]
        gb = render.render_gbuffer(g, keep, cam, with_median_depth=True)
        if v in lift_views:
            cr_P[v], cr_uv[v] = ctrl_random_fg(gb, cam, len(lifted["median"][v]), rng)
            cs_P[v], cs_uv[v] = ctrl_shuffle_depth(lifted["median"][v],
                                                   lifted_uv["median"][v], cam, rng)
        if v in views:
            vis, uvg, _ = visibility.visible_mask(X_pool, cam, gb["depth"])
            gp_P[v], gp_uv[v] = X_pool[vis], uvg[vis]
        del gb
        torch.cuda.empty_cache()
    clouds["ctrl_randfg"] = (cr_P, cr_uv, lift_views)
    clouds["ctrl_shufz"] = (cs_P, cs_uv, lift_views)
    clouds["gauss_pool"] = (gp_P, gp_uv, list(views))

    rec, sanity = {}, {}
    for a, (Pd, Ud, Vd) in clouds.items():
        P_all = np.concatenate([Pd[v] for v in Vd], 0)
        vtag = np.concatenate([np.full(len(Pd[v]), v) for v in Vd])
        if args.budget:
            U_all = np.concatenate([Ud[v] for v in Vd], 0)
            sel = voxel_budget(P_all, args.budget)
            P_all, vtag, U_all = P_all[sel], vtag[sel], U_all[sel]
            Pd = {v: P_all[vtag == v] for v in Vd}
            Ud = {v: U_all[vtag == v] for v in Vd}
            print(f"    [budget] {a}: -> {len(P_all)} pts", flush=True)
        tree3 = cKDTree(P_all) if len(P_all) else None
        arm = {"n_total": int(len(P_all)),
               "n_per_view_mean": float(np.mean([len(Pd[v]) for v in Vd]))}

        # ---- REPROJECTION SANITY (spec pitfall): project the world points BACK into their
        # source view and check they land on the pixels they came from.
        rp = np.concatenate([np.linalg.norm(common.project(Pd[v], cams[v])[0] - Ud[v], axis=1)
                             for v in Vd if len(Pd[v])])
        inb_bbox = ((P_all >= X_raw.min(0) - 0.05).all(1) &
                    (P_all <= X_raw.max(0) + 0.05).all(1)) if len(P_all) else np.zeros(0, bool)
        sanity[a] = {"reproj_px_median": float(np.median(rp)) if len(rp) else None,
                     "reproj_px_p99": float(np.percentile(rp, 99)) if len(rp) else None,
                     "reproj_px_max": float(rp.max()) if len(rp) else None,
                     "frac_inside_gaussian_bbox": float(inb_bbox.mean()) if len(P_all) else None}

        # ---- 2D own-view (DEGENERATE for the lift arms = 2D ceiling) and LOO (primary 2D)
        for mode in ("own", "loo"):
            hit_all = n_all = 0
            cov_fg_num = cov_fg_den = 0
            hm = {t: 0 for t in TAUS}
            nm = {t: 0 for t in TAUS}
            for v in views:
                cam = cams[v]
                idx, uvq = gt[v]
                if mode == "own":
                    uvl = Ud[v] if v in Vd else np.zeros((0, 2))
                else:
                    sel = vtag != v
                    Pv = P_all[sel]
                    if len(Pv):
                        vis, uvl_all, _ = visibility.visible_mask(Pv, cam, depth_t[v])
                        uvl = uvl_all[vis]
                        inb = ((uvl[:, 0] >= -2) & (uvl[:, 0] < cam.W + 2) &
                               (uvl[:, 1] >= -2) & (uvl[:, 1] < cam.H + 2))
                        uvl = uvl[inb]
                    else:
                        uvl = np.zeros((0, 2))
                n_all += len(idx)
                for t in TAUS:
                    nm[t] += int(miss2d[t][v].sum())
                fgm = np.isfinite(depth_np[v])
                cov_fg_den += int(fgm.sum())
                if len(uvl) == 0:
                    continue
                tr = cKDTree(uvl)
                d = tr.query(uvq, k=1)[0]
                ok = d <= args.delta
                hit_all += int(ok.sum())
                for t in TAUS:
                    hm[t] += int((ok & miss2d[t][v]).sum())
                # cover_fg: fraction of FOREGROUND pixels within delta of the cloud -> the
                # density null.  lift = R_miss / cover_fg  (RECALL_RESULTS.md TRACK A rule).
                fv, fu = np.nonzero(fgm)
                q = np.stack([fu.astype(np.float64), fv.astype(np.float64)], 1)
                cov_fg_num += int((tr.query(q, k=1)[0] <= args.delta).sum())
            for t in TAUS:
                arm[f"R_miss_2D_{mode}_tau{t}"] = hm[t] / max(nm[t], 1)
            arm[f"R_miss_2D_{mode}"] = arm[f"R_miss_2D_{mode}_tau1.5"]
            arm[f"recall_2D_{mode}"] = hit_all / max(n_all, 1)
            arm[f"cover_fg_{mode}"] = cov_fg_num / max(cov_fg_den, 1)
            arm[f"lift_{mode}"] = (arm[f"R_miss_2D_{mode}"] /
                                   max(arm[f"cover_fg_{mode}"], 1e-9))

        # ---- 3D chamfer (query once, threshold at several radii)
        if tree3 is not None:
            d3 = tree3.query(crease_pts[seen_idx], k=1)[0]
            dprec = tree_gt3.query(P_all, k=1)[0]
            for rname, rad in r3_radii.items():
                hit = d3 <= rad
                arm[f"R_miss_3D_{rname}"] = float(hit[miss_local].mean())
                arm[f"R_miss_3D_{rname}_tau2.5"] = float(hit[miss_local25].mean())
                arm[f"recall_3D_{rname}"] = float(hit.mean())
                arm[f"precision_3D_{rname}"] = float((dprec <= rad).mean())
            arm["chamfer_d3_median"] = float(np.median(d3))
            arm["chamfer_d3_miss_median"] = float(np.median(d3[miss_local]))
        rec[a] = arm
        print(f"  [{a:12s}] n={len(P_all):7d} | R_miss2D own {arm['R_miss_2D_own']:.4f}"
              f" loo {arm['R_miss_2D_loo']:.4f} (cov_fg {arm['cover_fg_loo']:.3f},"
              f" lift {arm['lift_loo']:.2f}) | rec2D own {arm['recall_2D_own']:.4f}"
              f" loo {arm['recall_2D_loo']:.4f} | 3D@px1.5eq Rm "
              f"{arm.get('R_miss_3D_px1.5_equiv', float('nan')):.4f} rec "
              f"{arm.get('recall_3D_px1.5_equiv', float('nan')):.4f} pr "
              f"{arm.get('precision_3D_px1.5_equiv', float('nan')):.4f}", flush=True)
    res["recovery"] = rec
    res["lift_sanity"] = sanity

    print("\n  LIFT SANITY (reprojection of lifted points into their source view):")
    for a in sanity:
        sa = sanity[a]
        print(f"    [{a:12s}] reproj err px: med {sa['reproj_px_median']:.4f} "
              f"p99 {sa['reproj_px_p99']:.4f} max {sa['reproj_px_max']:.4f}   "
              f"inside gaussian bbox {sa['frac_inside_gaussian_bbox']:.4f}")

    res["src"] = args.src
    res["budget"] = args.budget
    res["lift_views"] = [int(v) for v in lift_views]
    res["halfpix"] = args.halfpix
    jp = args.out or os.path.join(
        OUT, f"dexprimary_p0_{scene}_{args.key}{args.tag}.json")
    json.dump(res, open(jp, "w"), indent=2)
    print(f"\nwrote {jp}")


if __name__ == "__main__":
    main()
