"""tier1/src/stroke_metric.py — FORWARD-WARPED STROKE TEMPORAL RESIDUAL (mesh-free).

HARD INVARIANT: cameras + gaussian z-buffer + polylines only. No mesh, ever.

THE METRIC
    For adjacent frames t, t+1 on a camera path, every stroke of frame t is FORWARD
    WARPED into frame t+1 by the scene's own motion W(t->t+1) — each vertex is
    un-projected with the frame-t gaussian z-buffer and re-projected into frame t+1 —
    and then matched to the strokes actually produced at t+1:

      residual   = discrete FRECHET distance (px) between a warped stroke and its best
                   match at t+1, reported as median / mean / p90 over matched strokes.
                   Chamfer is reported alongside as a shape-only cross-check.
      P_pop      = fraction of strokes that have NO match, counting both directions
                   (a stroke of t that vanishes, and a stroke of t+1 that appears from
                   nothing), plus the TOPOLOGICAL CUT rate: strokes whose match is
                   many-to-one or one-to-many, i.e. a stroke that split or merged
                   between frames. Those are the events a viewer perceives as popping.

WHY THE SAME WARP FOR BOTH PIPELINES
    The object-space pipeline knows its own inter-frame motion exactly (its strokes are
    projections of static 3D polylines), while the image-space baseline knows nothing.
    Giving our pipeline its exact carrier motion and the baseline only an estimate would
    build the conclusion into the metric. So BOTH are warped with the identical
    depth-based operator, which is what any renderer could actually compute. That is
    deliberately conservative for us: it charges our strokes for warp resampling error
    they would not really suffer.
"""
import numpy as np
from scipy.spatial import cKDTree


# ------------------------------------------------------------------------- warping
def warp_points(uv, depth, cam_from, cam_to):
    """[N,2] pixel coords -> forward-warped [N,2] and a validity mask."""
    uv = np.asarray(uv, np.float64)
    H, W = depth.shape
    u = np.clip(np.round(uv[:, 0]).astype(np.int64), 0, W - 1)
    v = np.clip(np.round(uv[:, 1]).astype(np.int64), 0, H - 1)
    z = depth[v, u]
    ok = np.isfinite(z) & (z > 1e-6) & (z < 1e8)
    z = np.where(ok, z, 1.0)                      # keep the arithmetic finite; ok masks
    f = cam_from.f
    cx, cy = cam_from.K[0, 2], cam_from.K[1, 2]
    campt = np.stack([(uv[:, 0] - cx) * z / f, (uv[:, 1] - cy) * z / f, z], 1)
    R, t = cam_from.w2c[:3, :3], cam_from.w2c[:3, 3]
    world = (R.T @ (campt - t).T).T
    R2, t2 = cam_to.w2c[:3, :3], cam_to.w2c[:3, 3]
    c2 = (R2 @ world.T).T + t2
    zz = c2[:, 2]
    ok &= zz > 1e-6
    out = np.full_like(uv, np.nan)
    good = ok
    out[good, 0] = cam_to.f * c2[good, 0] / zz[good] + cam_to.K[0, 2]
    out[good, 1] = cam_to.f * c2[good, 1] / zz[good] + cam_to.K[1, 2]
    return out, ok


def warp_strokes(polys, depth, cam_from, cam_to, min_pts=2):
    """Warp a list of polylines; a stroke survives only if >=min_pts vertices warp."""
    out, survived = [], []
    for q in polys:
        w, ok = warp_points(q, depth, cam_from, cam_to)
        if ok.sum() >= min_pts:
            out.append(w[ok])
            survived.append(True)
        else:
            survived.append(False)
    return out, np.array(survived, bool)


# --------------------------------------------------------------- polyline distances
def resample(q, n=16):
    """Arc-length resample a polyline to exactly n points."""
    q = np.asarray(q, np.float64)
    if len(q) == 1:
        return np.repeat(q, n, axis=0)
    seg = np.linalg.norm(np.diff(q, axis=0), axis=1)
    cs = np.concatenate([[0.0], np.cumsum(seg)])
    total = cs[-1]
    if total <= 1e-12:
        return np.repeat(q[:1], n, axis=0)
    s = np.linspace(0.0, total, n)
    x = np.interp(s, cs, q[:, 0])
    y = np.interp(s, cs, q[:, 1])
    return np.stack([x, y], 1)


def _batched_frechet(A, B):
    """Discrete Frechet distance for M polyline pairs, each resampled to n points.
    A,B: [M,n,2]. Returns [M]. Also returns the direction-reversed minimum, since a
    stroke's vertex order is arbitrary."""
    def _one(A, B):
        M, n, _ = A.shape
        D = np.linalg.norm(A[:, :, None, :] - B[:, None, :, :], axis=-1)   # [M,n,n]
        ca = np.full((M, n, n), np.inf)
        ca[:, 0, 0] = D[:, 0, 0]
        for i in range(1, n):
            ca[:, i, 0] = np.maximum(ca[:, i - 1, 0], D[:, i, 0])
        for j in range(1, n):
            ca[:, 0, j] = np.maximum(ca[:, 0, j - 1], D[:, 0, j])
        for i in range(1, n):
            prev = ca[:, i - 1, :]
            for j in range(1, n):
                m = np.minimum(np.minimum(prev[:, j], prev[:, j - 1]), ca[:, i, j - 1])
                ca[:, i, j] = np.maximum(m, D[:, i, j])
        return ca[:, -1, -1]
    return np.minimum(_one(A, B), _one(A, B[:, ::-1]))


def _batched_chamfer(A, B):
    D = np.linalg.norm(A[:, :, None, :] - B[:, None, :, :], axis=-1)
    return 0.5 * (D.min(2).mean(1) + D.min(1).mean(1))


# ------------------------------------------------------------------------- matching
def match_strokes(warped, target, n_resample=16, max_cand=6, cand_radius=40.0,
                  match_thresh=3.0):
    """Match each warped stroke to its nearest target stroke.

    Returns dict with per-stroke Frechet/Chamfer for matched strokes, the unmatched
    counts in BOTH directions, and the topological split/merge counts."""
    res = {"frechet": np.zeros(0), "chamfer": np.zeros(0),
           "n_warped": len(warped), "n_target": len(target),
           "n_unmatched_warped": len(warped), "n_unmatched_target": len(target),
           "n_split": 0, "n_merge": 0, "match_idx": np.zeros(0, np.int64)}
    if not len(warped) or not len(target):
        return res
    Aw = np.stack([resample(q, n_resample) for q in warped])
    Bt = np.stack([resample(q, n_resample) for q in target])
    cw = Aw.mean(1)
    ct = Bt.mean(1)
    tree = cKDTree(ct)
    k = min(max_cand, len(ct))
    dist, idx = tree.query(cw, k=k, distance_upper_bound=cand_radius, workers=-1)
    dist = np.atleast_2d(dist.reshape(len(cw), -1))
    idx = np.atleast_2d(idx.reshape(len(cw), -1))
    rows, cols = np.nonzero(np.isfinite(dist))
    if not len(rows):
        return res
    cand_t = idx[rows, cols]
    fre = _batched_frechet(Aw[rows], Bt[cand_t])
    cha = _batched_chamfer(Aw[rows], Bt[cand_t])
    best = np.full(len(Aw), np.inf)
    best_c = np.full(len(Aw), np.inf)
    best_j = np.full(len(Aw), -1, np.int64)
    for r, j, f, c in zip(rows, cand_t, fre, cha):
        if f < best[r]:
            best[r], best_c[r], best_j[r] = f, c, j
    matched = np.isfinite(best) & (best <= match_thresh)
    tgt_hit = np.zeros(len(Bt), bool)
    tgt_hit[best_j[matched]] = True
    # topology: one warped stroke covering several targets (split) and several warped
    # strokes collapsing onto one target (merge)
    cnt = np.bincount(best_j[matched], minlength=len(Bt))
    n_merge = int((cnt > 1).sum())
    close = (fre <= match_thresh)
    per_w = {}
    for r, j, ok in zip(rows, cand_t, close):
        if ok:
            per_w.setdefault(r, set()).add(int(j))
    n_split = int(sum(1 for v in per_w.values() if len(v) > 1))
    res.update({
        "frechet": best[matched], "chamfer": best_c[matched],
        "n_unmatched_warped": int((~matched).sum()),
        "n_unmatched_target": int((~tgt_hit).sum()),
        "n_split": n_split, "n_merge": n_merge,
        "match_idx": best_j,
    })
    return res


def pop_penalty(m, n_dropped_by_warp=0):
    """P_pop = unmatched fraction (both directions) + topological-cut rate."""
    nw = m["n_warped"] + n_dropped_by_warp
    nt = m["n_target"]
    denom = max(nw + nt, 1)
    unmatched = (m["n_unmatched_warped"] + n_dropped_by_warp + m["n_unmatched_target"])
    cuts = m["n_split"] + m["n_merge"]
    return {"P_pop": float((unmatched + cuts) / denom),
            "unmatched_frac": float(unmatched / denom),
            "cut_frac": float(cuts / denom),
            "n_unmatched": int(unmatched), "n_cuts": int(cuts),
            "n_warped_total": int(nw), "n_target": int(nt),
            "n_dropped_by_warp": int(n_dropped_by_warp)}
