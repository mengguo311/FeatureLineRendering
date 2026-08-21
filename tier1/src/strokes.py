"""tier1/src/strokes.py — LINELET -> POLYLINE STROKE GRAPH (METHOD PATH, mesh-free).

HARD INVARIANT: gaussians + training RGB + cameras only. Never imports mesh_oracle.

TWO STROKE PIPELINES, deliberately asymmetric — that asymmetry IS the experiment:

  (A) OURS — chain the DT-pulled linelets in 3D. A stroke is an ordered list of 3D
      vertices, so it has a persistent OBJECT-SPACE identity: rendering it into any
      camera is just a projection, and its inter-frame motion is known exactly rather
      than estimated. Chaining is done once, off-line, for the whole scene.

  (B) BASELINE — trace strokes out of a per-frame image-space Canny map. There is no
      3D carrier, so every frame re-derives its strokes from scratch and nothing
      connects the stroke set at t to the one at t+1 except image evidence.

3D CHAINING (A): spatial NMS to collapse the many near-duplicate linelets a 0.30 seed
fraction produces, then a kNN graph in which an edge (i,j) survives only if the two
tangents agree AND the offset between the linelets is collinear with those tangents (so
neighbouring points on a parallel crease do not get stitched sideways). Each node then
keeps at most one link forward and one backward along its own tangent, which turns the
graph into disjoint paths and performs the junction split implicitly: a Y-junction keeps
its two best-aligned arms and the third arm starts a new stroke.
"""
import numpy as np
from scipy.spatial import cKDTree


# ------------------------------------------------------------------ (A) 3D chaining
def nms_3d(p, t, conf, radius, cos_thr=0.8):
    """Greedy spatial NMS over linelets, best-confidence first. Suppresses a linelet
    that is within `radius` of an already-kept one AND roughly parallel to it."""
    order = np.argsort(-np.asarray(conf))
    tree = cKDTree(p)
    kept = np.zeros(len(p), bool)
    dead = np.zeros(len(p), bool)
    for i in order:
        if dead[i]:
            continue
        kept[i] = True
        nb = tree.query_ball_point(p[i], radius)
        if nb:
            nb = np.asarray(nb)
            par = np.abs(t[nb] @ t[i]) > cos_thr
            dead[nb[par]] = True
        dead[i] = True
    return kept


def chain_linelets_3d(p, t, l, conf=None, nms_radius_mult=1.0, k=10,
                      cos_tan=0.75, cos_col=0.7, gap_mult=3.0, min_nodes=3):
    """Returns (chains, kept_idx): chains = list of int arrays indexing into the
    NMS-surviving subset, ordered along the stroke."""
    p = np.asarray(p, np.float64)
    t = np.asarray(t, np.float64)
    l = np.asarray(l, np.float64)
    conf = np.ones(len(p)) if conf is None else np.asarray(conf, np.float64)
    if len(p) < min_nodes:
        return [], np.zeros(len(p), bool)

    med_l = float(np.median(l)) if len(l) else 1.0
    keep = nms_3d(p, t, conf, radius=nms_radius_mult * med_l)
    idx = np.where(keep)[0]
    P, T = p[idx], t[idx]
    n = len(P)
    if n < min_nodes:
        return [], keep

    tree = cKDTree(P)
    kq = min(k + 1, n)
    d, nb = tree.query(P, k=kq, workers=-1)
    d, nb = np.atleast_2d(d)[:, 1:], np.atleast_2d(nb)[:, 1:]
    gap = gap_mult * med_l

    # Candidate links: j may extend i only if the tangents agree AND the offset is
    # collinear with them (so a parallel neighbouring crease is not stitched sideways).
    # Each node has two slots — one on each side of its own tangent line — so accepting
    # links greedily by score keeps every degree <= 2 and splits junctions implicitly:
    # a Y keeps its two best-aligned arms and the third arm starts a new stroke.
    cand_i, cand_j, cand_s, slot_i, slot_j = [], [], [], [], []
    for i in range(n):
        c = nb[i]
        dist = d[i]
        ok = (dist > 0) & (dist < gap) & (c >= 0) & (c < n)
        if not ok.any():
            continue
        c, dist = c[ok], dist[ok]
        off = P[c] - P[i]
        offn = off / np.maximum(dist[:, None], 1e-12)
        tan_agree = np.abs(np.einsum("kc,c->k", T[c], T[i]))
        col_i = offn @ T[i]
        good = (tan_agree > cos_tan) & (np.abs(col_i) > cos_col)
        if not good.any():
            continue
        c, dist = c[good], dist[good]
        sc = tan_agree[good] * np.abs(col_i[good]) / (1.0 + dist / gap)
        si = (col_i[good] > 0).astype(np.int64)                 # slot on i
        col_j = np.einsum("kc,kc->k", -offn[good], T[c])
        sj = (col_j > 0).astype(np.int64)                       # slot on j
        cand_i.append(np.full(len(c), i)); cand_j.append(c)
        cand_s.append(sc); slot_i.append(si); slot_j.append(sj)

    adj = [[] for _ in range(n)]
    if cand_i:
        ci = np.concatenate(cand_i); cj = np.concatenate(cand_j)
        cs = np.concatenate(cand_s); s_i = np.concatenate(slot_i); s_j = np.concatenate(slot_j)
        order = np.argsort(-cs)
        used = np.zeros((n, 2), bool)
        linked = set()
        for e in order:
            i, j = int(ci[e]), int(cj[e])
            if i == j:
                continue
            key = (i, j) if i < j else (j, i)
            if key in linked:
                continue
            a, b = int(s_i[e]), int(s_j[e])
            if used[i, a] or used[j, b]:
                continue
            used[i, a] = used[j, b] = True
            linked.add(key)
            adj[i].append(j); adj[j].append(i)

    seen = np.zeros(n, bool)
    chains = []
    deg = np.array([len(a) for a in adj])
    starts = list(np.where(deg == 1)[0]) + list(np.where(deg == 2)[0])
    for s0 in starts:
        if seen[s0]:
            continue
        chain = [int(s0)]
        seen[s0] = True
        prev, cur = -1, int(s0)
        while True:
            nxt = [j for j in adj[cur] if j != prev and not seen[j]]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            seen[cur] = True
            chain.append(cur)
        if len(chain) >= min_nodes:
            chains.append(np.array(chain, np.int64))
    return chains, keep


def chain_vertices(chains, P):
    """3D vertex arrays for each chain."""
    return [P[c] for c in chains]


# --------------------------------------------------- (B) image-space stroke tracing
_NB8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def trace_polylines(mask, min_len=4, approx_eps=1.0):
    """NMS'd binary edge map -> ordered 2D polylines. Junction pixels (degree>=3) are
    removed first, which splits the graph into simple paths; each path is then walked
    from an endpoint and simplified with Douglas-Peucker."""
    import cv2
    m = (np.asarray(mask) > 0).astype(np.uint8)
    if m.sum() == 0:
        return []
    k = np.ones((3, 3), np.uint8)
    k[1, 1] = 0
    deg = cv2.filter2D(m, -1, k, borderType=cv2.BORDER_CONSTANT) * m
    junction = (deg >= 3) & (m > 0)
    simple = (m > 0) & ~junction
    nlab, lab = cv2.connectedComponents(simple.astype(np.uint8), connectivity=8)
    H, W = m.shape
    out = []
    ys, xs = np.nonzero(simple)
    order = np.argsort(lab[ys, xs], kind="stable")
    ys, xs = ys[order], xs[order]
    labs = lab[ys, xs]
    bounds = np.searchsorted(labs, np.arange(1, nlab), side="left")
    bounds = list(bounds) + [len(labs)]
    for ci in range(nlab - 1):
        a, b = bounds[ci], bounds[ci + 1]
        if b - a < min_len:
            continue
        cy, cx = ys[a:b], xs[a:b]
        pix = set(zip(cy.tolist(), cx.tolist()))
        # find an endpoint (degree 1 within the component), else start anywhere (cycle)
        start = None
        for (yy, xx) in zip(cy.tolist(), cx.tolist()):
            dcount = sum(((yy + dy, xx + dx) in pix) for dy, dx in _NB8)
            if dcount == 1:
                start = (yy, xx)
                break
        if start is None:
            start = (int(cy[0]), int(cx[0]))
        path = [start]
        visited = {start}
        cur = start
        while True:
            nxt = None
            for dy, dx in _NB8:
                q = (cur[0] + dy, cur[1] + dx)
                if q in pix and q not in visited:
                    nxt = q
                    break
            if nxt is None:
                break
            visited.add(nxt)
            path.append(nxt)
            cur = nxt
        if len(path) < min_len:
            continue
        arr = np.array([[x, y] for y, x in path], np.float32)
        if approx_eps > 0 and len(arr) > 2:
            arr = cv2.approxPolyDP(arr.reshape(-1, 1, 2), approx_eps, False).reshape(-1, 2)
        if len(arr) >= 2:
            out.append(arr.astype(np.float64))
    return out


def canny_strokes(gray, lo=50, hi=150, blur=0.0, min_len=4, approx_eps=1.0):
    """BASELINE (B): naive image-space Canny -> polylines, recomputed per frame."""
    import cv2
    g = cv2.GaussianBlur(gray, (0, 0), blur) if blur > 0 else gray
    e = cv2.Canny(g.astype(np.uint8), lo, hi)
    return trace_polylines(e > 0, min_len=min_len, approx_eps=approx_eps)


# ------------------------------------------------------------------------- output
def write_svg(path, polys, W, H, stroke="#000", width=1.0, colors=None):
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="#fff"/>']
    for i, q in enumerate(polys):
        if len(q) < 2:
            continue
        pts = " ".join(f"{x:.2f},{y:.2f}" for x, y in q)
        c = stroke if colors is None else colors[i]
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{c}" '
                     f'stroke-width="{width}" stroke-linecap="round"/>')
    parts.append("</svg>")
    open(path, "w").write("\n".join(parts))
    return path


def raster_polylines(polys, H, W, thickness=1):
    import cv2
    img = np.zeros((H, W), np.uint8)
    for q in polys:
        if len(q) < 2:
            continue
        cv2.polylines(img, [np.round(q * 16).astype(np.int32).reshape(-1, 1, 2)],
                      False, 1, thickness, cv2.LINE_8, 4)
    return img > 0
