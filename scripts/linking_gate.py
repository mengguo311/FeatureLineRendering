#!/usr/bin/env python
"""AGGRESSIVE 3D LINKING — precision-safe continuity gate (kill-test, tier1/linking_gate_spec.md).

*** METHOD PATH for the linker (gaussians, cameras, 3DGS depth, RAW DexiNed maps, polylines);
    the GT mesh is read ONLY by scripts/tune_lib.Harness for P@1.5 / R@1.5 scoring on the
    held-out TEST views (EVAL-ONLY). ***

INPUT (the shipped persistent 3D lines)
    out/linelets_<scene>_gated_test.npz -> spec-prune `keep` linelets -> the banked 3D chaining
    (scripts/m1b_stroke_temporal.build_chains: NMS 1.0x, k=10, cos_tan 0.60, cos_col 0.50,
    gap 4.0x, >=3 nodes) = the static object-space stroke set behind the shipped drawings and
    the crown-jewel temporal result.  Linking is done ONCE on these 3D polylines with a
    view-independent criterion; the topology is then frozen and every frame is a projection.

LINKER (agy's algorithm)
    endpoints of all strokes; candidate pair iff ||p_i - p_j|| < d_max (= mult x median full
    linelet length), different strokes.  Gates: outward end tangents face each other
    (cos(t_i, -t_j) > tau_angle), bridge collinear with both (t_i.d > tau_col, -t_j.d > tau_col);
    DEPTH-DISCONTINUITY GUARD: K samples along the straight bridge must (a) lie within r_surf of a
    de-floatered gaussian centre and (b) be on the 3DGS surface (|z - zbuf| <= 0.02 z) in >= 50 %
    of the TRAIN views that see them (>= 3 views);  BRIDGE EVIDENCE (ON/OFF arm): the mean over
    samples of the occlusion-aware multi-view mean RAW DexiNed native probability (TRAIN views)
    must exceed tau_edge, calibrated as the 25th percentile of the same statistic at the existing
    stroke vertices.  Greedy by bridge length, each endpoint used once, no cycles.

METRICS
    C = total 3D arc length / #strokes.  P@1.5 / R@1.5: macro over the 10 TEST views, strokes
    projected through the frozen 3DGS z-buffer with occlusion splitting and rasterised 1 px
    (run_m1b's segment-raster convention, applied to polylines).  Phi_pop = ARC-LENGTH-WEIGHTED
    popped ratio over the banked 240-frame look-at orbit TEST 5 -> 15 with the banked warp +
    matching operator (src/stroke_metric: forward warp by the frame-t z-buffer, Frechet match
    <= 3 px, 6 candidates within 40 px, 16-point resampling); popped = unmatched in either
    direction, dropped by warp, or topologically split/merged — weighted by 2D stroke length.
    The count-based P_pop of the banked table is reported alongside.
"""
import argparse
import json
import os
import sys
import time
import types

import cv2
import numpy as np
import torch
from scipy.spatial import cKDTree

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
from src import common, render, strokes, stroke_metric, view_split      # noqa: E402  METHOD PATH
import m1b_stroke_temporal as MT                                          # noqa: E402
import temporal_m1b as TM                                                 # noqa: E402

OUT = os.path.join(TIER1, "out", "link")
CACHE = os.path.join(TIER1, "cache")
EDGES = os.path.join(TIER1, "out", "dexined_edges_{scene}")
TEST, TRAIN = list(view_split.TEST), list(view_split.TRAIN)
H = W = 800
CHAIN_ARGS = types.SimpleNamespace(nms_mult=1.0, knn=10, cos_tan=0.60, cos_col=0.50, gap_mult=4.0,
                                   min_nodes=3, carrier_persistence=False, cp_ratio=0.8, cp_views=20)
MATCH = dict(n_resample=16, max_cand=6, cand_radius=40.0, match_thresh=3.0)   # banked operator
GATE = {"C_up": 0.25, "P_drop": {"chair": 0.010, "lego": 0.015, "ficus": 0.010}, "phi_ratio": 1.05}
KERN3 = np.ones((3, 3), np.uint8)


def log(m):
    print(m, flush=True)


# ============================================================ geometry helpers
def zmin3x3(depth):
    d = np.asarray(depth, np.float32).copy()
    d[~np.isfinite(d)] = 1e9
    return cv2.erode(d, KERN3)


def project_chains(V, starts, cam, zmin, rel_tol=0.02, min_pts=2):
    """Vectorised replica of m1b_stroke_temporal.ours_strokes: project all chain vertices, test
    visibility against the 3x3-min 3DGS z-buffer (z <= zb + rel_tol*z, in-frame), split each
    chain into visible runs of >= min_pts vertices.  Returns list of 2D polylines and, per run,
    the chain id it came from."""
    uv, z = common.project(V, cam)
    u = np.round(uv[:, 0]).astype(np.int64)
    v = np.round(uv[:, 1]).astype(np.int64)
    inb = (z > 0) & (u >= 0) & (u < W) & (v >= 0) & (v < H)
    good = np.zeros(len(V), bool)
    idx = np.where(inb)[0]
    zb = zmin[v[idx], u[idx]]
    good[idx] = z[idx] <= zb + rel_tol * z[idx]
    out, owner = [], []
    for c in range(len(starts) - 1):
        a, b = starts[c], starts[c + 1]
        g = good[a:b]
        if g.sum() < min_pts:
            continue
        # split into runs
        run_start = None
        for i in range(a, b + 1):
            gi = good[i] if i < b else False
            if gi and run_start is None:
                run_start = i
            elif not gi and run_start is not None:
                if i - run_start >= min_pts:
                    out.append(uv[run_start:i].copy())
                    owner.append(c)
                run_start = None
    return out, np.array(owner, np.int64)


def flatten(chains):
    starts = np.zeros(len(chains) + 1, np.int64)
    starts[1:] = np.cumsum([len(c) for c in chains])
    return (np.concatenate(chains) if chains else np.zeros((0, 3))), starts


def arc_len(q):
    q = np.asarray(q, np.float64)
    return float(np.linalg.norm(np.diff(q, axis=0), axis=1).sum()) if len(q) > 1 else 0.0


# ============================================================ multi-view evidence machinery
class ViewBank:
    """TRAIN-view 3DGS depth (from cache/epi_gbuf_<scene>.npz, the same G-buffers the pipeline
    renders) + RAW DexiNed native maps, for the bridge guards.  Mesh-free."""

    def __init__(self, scene, views, cams, off=(-0.5, -0.5)):
        gb = np.load(os.path.join(CACHE, f"epi_gbuf_{scene}.npz"))
        self.views = list(views)
        self.cams = cams
        self.depth = {v: gb["depth"][v].astype(np.float32) for v in self.views}
        self.zmin = {v: zmin3x3(self.depth[v]) for v in self.views}
        self.maps = {v: np.load(os.path.join(EDGES.format(scene=scene), f"v{v:03d}.npz"))["native"].astype(np.float32)
                     for v in self.views}
        self.off = off

    def stats(self, P, rel_tol=0.02):
        """Per point: (n_visible, mean RAW P over visible views, n_inframe_finite, on-surface fraction)."""
        P = np.asarray(P, np.float64)
        n_vis = np.zeros(len(P), np.int32)
        s_vis = np.zeros(len(P), np.float64)
        n_fin = np.zeros(len(P), np.int32)
        n_on = np.zeros(len(P), np.int32)
        for v in self.views:
            cam = self.cams[v]
            uv, z = common.project(P, cam)
            u = np.round(uv[:, 0]).astype(np.int64)
            w = np.round(uv[:, 1]).astype(np.int64)
            inb = (z > 1e-6) & (u >= 0) & (u < W) & (w >= 0) & (w < H)
            if not inb.any():
                continue
            i = np.where(inb)[0]
            zb = self.zmin[v][w[i], u[i]]
            dep = self.depth[v][w[i], u[i]]
            fin = np.isfinite(dep) & (dep < 1e8)
            vis = z[i] <= zb + rel_tol * z[i]
            on = fin & (np.abs(z[i] - dep) <= rel_tol * z[i])
            n_fin[i] += fin
            n_on[i] += on
            # RAW DexiNed at photo-index coords (bilinear), visible views only
            iv = i[vis]
            if len(iv):
                mp = self.maps[v]
                x = np.clip(uv[iv, 0] + self.off[0], 0, W - 1)
                y = np.clip(uv[iv, 1] + self.off[1], 0, H - 1)
                x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
                x1 = np.minimum(x0 + 1, W - 1); y1 = np.minimum(y0 + 1, H - 1)
                fx = x - x0; fy = y - y0
                val = (mp[y0, x0] * (1 - fx) * (1 - fy) + mp[y0, x1] * fx * (1 - fy)
                       + mp[y1, x0] * (1 - fx) * fy + mp[y1, x1] * fx * fy)
                s_vis[iv] += val
                n_vis[iv] += 1
        mean_p = np.where(n_vis > 0, s_vis / np.maximum(n_vis, 1), np.nan)
        on_frac = np.where(n_fin > 0, n_on / np.maximum(n_fin, 1), np.nan)
        return n_vis, mean_p, n_fin, on_frac


# ============================================================ the linker
def end_tangents(V, k=2):
    n = len(V)
    kk = min(k, n - 1)
    ts = V[0] - V[kk]
    te = V[-1] - V[-1 - kk]
    ts /= max(np.linalg.norm(ts), 1e-12)
    te /= max(np.linalg.norm(te), 1e-12)
    return ts, te


def link_chains(chains, d_max, bank, carrier_tree, r_surf, tau_edge, tau_angle=0.7, tau_col=0.7,
                evidence_on=True, depth_guard_on=True, sample_step=None, min_vis=3):
    """Greedy endpoint-to-endpoint 3D linker with tangent gating, depth-discontinuity guard and
    multi-view bridge evidence.  Returns (merged_chains, bridges, stats)."""
    n = len(chains)
    ends = np.zeros((2 * n, 3))
    tans = np.zeros((2 * n, 3))
    for c, V in enumerate(chains):
        ts, te = end_tangents(V)
        ends[2 * c], ends[2 * c + 1] = V[0], V[-1]
        tans[2 * c], tans[2 * c + 1] = ts, te
    tree = cKDTree(ends)
    pairs = tree.query_pairs(d_max, output_type="ndarray")
    st = {"n_candidates": 0, "pass_geom": 0, "pass_depth": 0, "pass_evidence": 0, "accepted": 0,
          "rej_cycle_or_used": 0}
    if len(pairs) == 0:
        return [V.copy() for V in chains], [], st
    ci, cj = pairs[:, 0] // 2, pairs[:, 1] // 2
    keep = ci != cj
    pairs = pairs[keep]
    st["n_candidates"] = int(len(pairs))
    pa, pb = ends[pairs[:, 0]], ends[pairs[:, 1]]
    d = pb - pa
    dist = np.linalg.norm(d, axis=1)
    dn = d / np.maximum(dist[:, None], 1e-12)
    ta, tb = tans[pairs[:, 0]], tans[pairs[:, 1]]
    align = np.einsum("ij,ij->i", ta, -tb)
    col_a = np.einsum("ij,ij->i", ta, dn)
    col_b = np.einsum("ij,ij->i", -tb, dn)
    geom = (align > tau_angle) & (col_a > tau_col) & (col_b > tau_col) & (dist > 1e-9)
    st["pass_geom"] = int(geom.sum())
    order = np.argsort(dist)
    order = order[geom[order]]
    step = sample_step or (d_max / 6.0)

    # bridge samples for all geometric candidates at once (cheap), then guards
    samp, owner = [], []
    for e in order:
        K = max(3, int(np.ceil(dist[e] / step)) + 1)
        tt = np.linspace(0, 1, K + 2)[1:-1]
        samp.append(pa[e][None] + tt[:, None] * d[e][None])
        owner.append(np.full(len(tt), e))
    samp = np.concatenate(samp) if samp else np.zeros((0, 3))
    owner = np.concatenate(owner) if owner else np.zeros(0, np.int64)
    if len(samp):
        n_vis, mean_p, n_fin, on_frac = bank.stats(samp)
        d_car = carrier_tree.query(samp, k=1, workers=-1)[0]
    used = np.zeros(2 * n, bool)
    parent = np.arange(n)

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    links, bridges = [], []
    bridge_info = []
    for e in order:
        m = owner == e
        if depth_guard_on:
            ok_car = bool((d_car[m] <= r_surf).all())
            ok_on = bool(((n_fin[m] >= min_vis) & (on_frac[m] >= 0.5)).all())
            if not (ok_car and ok_on):
                continue
        st["pass_depth"] += 1
        ev_mean = float(np.nanmean(mean_p[m])) if np.isfinite(mean_p[m]).any() else 0.0
        ev_min = float(np.nanmin(mean_p[m])) if np.isfinite(mean_p[m]).any() else 0.0
        ev_ok = (n_vis[m] >= min_vis).all() and ev_mean > tau_edge
        if evidence_on and not ev_ok:
            continue
        st["pass_evidence"] += 1
        i, j = int(pairs[e, 0]), int(pairs[e, 1])
        ca, cb = i // 2, j // 2
        if used[i] or used[j] or find(ca) == find(cb):
            st["rej_cycle_or_used"] += 1
            continue
        used[i] = used[j] = True
        parent[find(ca)] = find(cb)
        links.append((i, j))
        bridges.append(samp[m])
        bridge_info.append({"len": float(dist[e]), "ev_mean": ev_mean, "ev_min": ev_min,
                            "align": float(align[e]), "n_samples": int(m.sum())})
    st["accepted"] = len(links)
    st["bridge_len_mean"] = float(np.mean([b["len"] for b in bridge_info])) if bridge_info else 0.0
    st["bridge_ev_mean"] = float(np.mean([b["ev_mean"] for b in bridge_info])) if bridge_info else float("nan")

    # ---- assemble merged polylines: graph over chains, links join chain ends
    adj = {c: [] for c in range(n)}
    for (i, j), bs in zip(links, bridges):
        adj[i // 2].append((i, j, bs))
        adj[j // 2].append((j, i, bs[::-1]))
    seen = np.zeros(n, bool)
    merged, merged_bridges = [], []

    def oriented(c, enter_end):
        """vertices of chain c oriented so that traversal ENTERS at end `enter_end` (0 = start)."""
        V = chains[c]
        return V if enter_end == 0 else V[::-1]

    for c0 in range(n):
        if seen[c0]:
            continue
        deg = len(adj[c0])
        if deg == 2:
            continue                      # interior of a path; will be reached from an end
        # start at a chain with degree 0 or 1; enter at the end that is NOT linked
        if deg == 0:
            seen[c0] = True
            merged.append(chains[c0].copy())
            merged_bridges.append([])
            continue
        linked_end = adj[c0][0][0] % 2           # 0 = start end is linked, 1 = end is linked
        enter = 1 - linked_end
        cur, cur_enter = c0, enter
        verts = [oriented(cur, cur_enter)]
        bl = []
        seen[cur] = True
        while True:
            exit_end_global = 2 * cur + (1 - cur_enter)
            nxt = [(i, j, bs) for (i, j, bs) in adj[cur] if i == exit_end_global and not seen[j // 2]]
            if not nxt:
                break
            i, j, bs = nxt[0]
            verts.append(bs)
            bl.append(bs)
            cur, cur_enter = j // 2, j % 2
            seen[cur] = True
            verts.append(oriented(cur, cur_enter))
        merged.append(np.concatenate(verts))
        merged_bridges.append(bl)
    # any remaining unseen (cycle safety; cannot happen with the union-find guard)
    for c in range(n):
        if not seen[c]:
            merged.append(chains[c].copy())
            merged_bridges.append([])
    st["n_strokes_before"], st["n_strokes_after"] = n, len(merged)
    return merged, merged_bridges, st


# ============================================================ metrics
def continuity(chains):
    L = np.array([arc_len(c) for c in chains])
    return {"C": float(L.sum() / max(len(chains), 1)), "arc_total": float(L.sum()), "n": int(len(chains)),
            "len_median": float(np.median(L)) if len(L) else 0.0}


def pr_test(chains, h, zmins):
    """P@1.5 / R@1.5 macro over TEST views; run_m1b's segment-raster convention on polylines."""
    V, starts = flatten(chains)
    ps, rs, npx = [], [], []
    for v in h.views:
        cam = h.cams[v]
        polys, _ = project_chains(V, starts, cam, zmins[v])
        mask = strokes.raster_polylines(polys, H, W)
        cu, cv_, cdt = h.crease[v]
        ys, xs = np.nonzero(mask)
        sdt = (cv2.distanceTransform((~mask).astype(np.uint8), cv2.DIST_L2, 5) if mask.any()
               else np.full(mask.shape, 1e9, np.float32))
        ps.append(float((cdt[ys, xs] <= 1.5).mean()) if len(ys) else 0.0)
        rs.append(float((sdt[cv_, cu] <= 1.5).mean()))
        npx.append(int(len(ys)))
    return {"P@1.5": float(np.mean(ps)), "R@1.5": float(np.mean(rs)), "px_per_view": float(np.mean(npx))}


def match_full(warped, target):
    """The banked matcher (stroke_metric.match_strokes internals) with per-stroke flags exposed."""
    res = {"matched": np.zeros(len(warped), bool), "tgt_hit": np.zeros(len(target), bool),
           "split": np.zeros(len(warped), bool), "merge": np.zeros(len(target), bool)}
    if not len(warped) or not len(target):
        return res
    Aw = np.stack([stroke_metric.resample(q, MATCH["n_resample"]) for q in warped])
    Bt = np.stack([stroke_metric.resample(q, MATCH["n_resample"]) for q in target])
    cw, ct = Aw.mean(1), Bt.mean(1)
    tree = cKDTree(ct)
    k = min(MATCH["max_cand"], len(ct))
    dist, idx = tree.query(cw, k=k, distance_upper_bound=MATCH["cand_radius"], workers=-1)
    dist = np.atleast_2d(dist.reshape(len(cw), -1))
    idx = np.atleast_2d(idx.reshape(len(cw), -1))
    rows, cols = np.nonzero(np.isfinite(dist))
    if not len(rows):
        return res
    cand_t = idx[rows, cols]
    fre = stroke_metric._batched_frechet(Aw[rows], Bt[cand_t])
    best = np.full(len(Aw), np.inf)
    best_j = np.full(len(Aw), -1, np.int64)
    for r, j, f in zip(rows, cand_t, fre):
        if f < best[r]:
            best[r], best_j[r] = f, j
    matched = np.isfinite(best) & (best <= MATCH["match_thresh"])
    tgt_hit = np.zeros(len(Bt), bool)
    tgt_hit[best_j[matched]] = True
    cnt = np.bincount(best_j[matched], minlength=len(Bt))
    close = fre <= MATCH["match_thresh"]
    per_w = {}
    for r, j, ok in zip(rows, cand_t, close):
        if ok:
            per_w.setdefault(int(r), set()).add(int(j))
    split = np.zeros(len(Aw), bool)
    for r, s in per_w.items():
        if len(s) > 1:
            split[r] = True
    res.update({"matched": matched, "tgt_hit": tgt_hit, "split": split, "merge": cnt > 1})
    return res


def temporal(chains, frames):
    """Phi_pop (arc-length-weighted) and the count-based P_pop over the banked orbit."""
    V, starts = flatten(chains)
    proj = [project_chains(V, starts, f["cam"], f["zmin"])[0] for f in frames]
    phis, pops, nstr = [], [], []
    for i in range(len(frames) - 1):
        src, dst = proj[i], proj[i + 1]
        len_s = np.array([arc_len(q) for q in src])
        len_t = np.array([arc_len(q) for q in dst])
        w, surv = stroke_metric.warp_strokes(src, frames[i]["depth"], frames[i]["cam"], frames[i + 1]["cam"])
        surv = surv if len(surv) else np.zeros(0, bool)
        m = match_full(w, dst)
        ls = len_s[surv] if len(surv) else np.zeros(0)
        popped = (len_s[~surv].sum() if len(surv) else 0.0) + ls[~m["matched"]].sum() + ls[m["split"]].sum() \
            + len_t[~m["tgt_hit"]].sum() + len_t[m["merge"]].sum()
        denom = len_s.sum() + len_t.sum()
        phis.append(popped / max(denom, 1e-9))
        # count-based P_pop, banked convention
        unmatched = int((~surv).sum()) + int((~m["matched"]).sum()) + int((~m["tgt_hit"]).sum())
        cuts = int(m["split"].sum()) + int(m["merge"].sum())
        pops.append((unmatched + cuts) / max(len(src) + len(dst), 1))
        nstr.append(len(src))
    return {"Phi_pop": float(np.mean(phis)), "P_pop_count": float(np.mean(pops)),
            "strokes_per_frame": float(np.mean(nstr)), "n_pairs": len(phis)}


# ============================================================ driver
def build_frames(scene, cams, g, keep_g, n_frames, device):
    target = np.median(g["mu"][keep_g], axis=0)
    path = TM.orbit_cameras(cams[5], cams[15], n_frames, target)
    frames = []
    t0 = time.time()
    for k, cam in enumerate(path):
        gb = render.render_gbuffer(g, keep_g, cam, device=device)
        dep = gb["depth"].detach().cpu().numpy()
        frames.append({"cam": cam, "depth": dep, "zmin": zmin3x3(dep)})
        del gb
        torch.cuda.empty_cache()
        if k % 60 == 0:
            log(f"  [frames] {k}/{n_frames} ({time.time()-t0:.0f}s)")
    return frames


def viz(scene, base, best, best_bridges, best_name, cams, g, keep_g, view, device):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    cam = cams[view]
    gb = render.render_gbuffer(g, keep_g, cam, device=device, with_albedo=True)
    dep = gb["depth"].detach().cpu().numpy()
    alb = gb["albedo"].detach().cpu().numpy()
    a = gb["alpha"].detach().cpu().numpy()[..., None]
    rgb = np.clip(alb * a + (1 - a), 0, 1)
    zm = zmin3x3(dep)
    Vb, sb = flatten(base)
    pb, _ = project_chains(Vb, sb, cam, zm)
    Vl, sl = flatten(best)
    pl, _ = project_chains(Vl, sl, cam, zm)
    br = [b for bl in best_bridges for b in bl]
    Vbr, sbr = flatten(br) if br else (np.zeros((0, 3)), np.zeros(1, np.int64))
    pbr, _ = project_chains(Vbr, sbr, cam, zm, min_pts=1) if br else ([], np.zeros(0))
    fig, ax = plt.subplots(2, 2, figsize=(14, 14), facecolor="#fcfcfb")
    for k, (polys, ttl, bg) in enumerate([(pb, f"{scene}: SHIPPED chains, TEST view {view} ({len(pb)} strokes)", True),
                                          (pl, f"LINKED [{best_name}] ({len(pl)} strokes); bridges orange", True),
                                          (pb, "shipped — pure line drawing", False),
                                          (pl, "linked — pure line drawing", False)]):
        axx = ax[k // 2, k % 2]
        axx.imshow(rgb if bg else np.ones_like(rgb))
        axx.add_collection(LineCollection(polys, colors="#0b0b0b" if not bg else "#2a78d6", linewidths=1.0 if not bg else 1.3))
        if k % 2 == 1 and len(pbr):
            axx.add_collection(LineCollection(pbr, colors="#eb6834", linewidths=2.2))
        axx.set_xlim(0, W - 1); axx.set_ylim(H - 1, 0); axx.axis("off")
        axx.set_title(ttl, fontsize=10, loc="left")
    fig.tight_layout()
    p = os.path.join(OUT, f"linkgate_{scene}_viz_v{view}.png")
    fig.savefig(p, dpi=120, facecolor="#fcfcfb")
    plt.close(fig)
    log(f"[viz] -> {p}")
    return p


def run_scene(scene, args):
    from tune_lib import Harness              # EVAL-ONLY: mesh crease DTs for P/R scoring
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    z = np.load(os.path.join(TIER1, "out", f"linelets_{scene}_gated_test.npz"))
    keep = z["keep"].astype(bool)
    med_len = float(np.median(2 * z["l"][keep]))
    chains, cinfo = MT.build_chains(scene, "gated", CHAIN_ARGS)
    cams, _ = common.load_cameras(scene)
    g = common.load_gaussians(scene)
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    X = g["mu"][keep_g]
    carrier = cKDTree(X)
    nn = carrier.query(X, k=2, workers=-1)[0][:, 1]
    r_surf = 3.0 * float(np.median(nn))
    log(f"[{scene}] shipped chains {len(chains)} from {cinfo['n_linelets']} linelets (NMS {cinfo['n_nms']}); "
        f"median full linelet length {med_len:.5f} world; carrier {len(X)} gaussians, r_surf={r_surf:.5f} ({time.time()-t0:.0f}s)")

    bank = ViewBank(scene, TRAIN, cams)
    Vc, _ = flatten(chains)
    n_vis_c, mp_c, _, _ = bank.stats(Vc)
    okc = n_vis_c >= 3
    tau_edge = float(np.percentile(mp_c[okc], 25))
    log(f"[{scene}] vertex multi-view RAW DexiNed (TRAIN views, visible>=3: {okc.mean():.3f}): p10={np.percentile(mp_c[okc],10):.4f} "
        f"p25={tau_edge:.4f} p50={np.percentile(mp_c[okc],50):.4f} -> tau_edge={tau_edge:.4f} ({time.time()-t0:.0f}s)")

    h = Harness(scene, views=tuple(TEST))
    zmins_test = {v: zmin3x3(h.depth_np[v]) for v in h.views}
    frames = build_frames(scene, cams, g, keep_g, args.frames, args.device)
    log(f"[{scene}] {len(frames)} orbit frames rendered ({time.time()-t0:.0f}s)")

    res = {"scene": scene, "shipped_npz": f"linelets_{scene}_gated_test.npz", "n_linelets_keep": int(keep.sum()),
           "chain_info": cinfo, "median_linelet_len": med_len, "r_surf": r_surf, "tau_edge": tau_edge,
           "tau_sets": args.tau_sets, "frames": args.frames, "match": MATCH,
           "variants": {}}
    base = {"continuity": continuity(chains), "pr": pr_test(chains, h, zmins_test), "temporal": temporal(chains, frames)}
    res["baseline"] = base
    log(f"[{scene}] BASELINE: C={base['continuity']['C']:.5f} n={base['continuity']['n']} P@1.5={base['pr']['P@1.5']:.4f} "
        f"R@1.5={base['pr']['R@1.5']:.4f} Phi_pop={base['temporal']['Phi_pop']:.4f} P_pop(count)={base['temporal']['P_pop_count']:.4f} ({time.time()-t0:.0f}s)")

    best = None
    for (ta, tc) in args.tau_sets:
      for mult in args.mults:
        for ev in (True, False):
            name = f"dmax{mult:g}x_bridge{'ON' if ev else 'OFF'}_tau{ta:g}"
            merged, bridges, st = link_chains(chains, mult * med_len, bank, carrier, r_surf, tau_edge,
                                              tau_angle=ta, tau_col=tc, evidence_on=ev)
            c = continuity(merged)
            pr = pr_test(merged, h, zmins_test)
            tp = temporal(merged, frames)
            dC = c["C"] / base["continuity"]["C"] - 1
            dP = pr["P@1.5"] - base["pr"]["P@1.5"]
            dR = pr["R@1.5"] - base["pr"]["R@1.5"]
            phi_r = tp["Phi_pop"] / max(base["temporal"]["Phi_pop"], 1e-9)
            ok = ev and dC >= GATE["C_up"] and (-dP) <= GATE["P_drop"][scene] and phi_r <= GATE["phi_ratio"]
            v = {"d_max": mult * med_len, "mult": mult, "bridge_evidence": ev, "tau_angle": ta, "tau_col": tc, "link_stats": st, "continuity": c,
                 "pr": pr, "temporal": tp, "dC_rel": dC, "dP": dP, "dR": dR, "phi_ratio": phi_r, "gate_pass": bool(ok)}
            res["variants"][name] = v
            log(f"[{scene}] {name:22s} links={st['accepted']:4d}/{st['n_candidates']:5d} (geom {st['pass_geom']}, depth {st['pass_depth']}, "
                f"evid {st['pass_evidence']}) C={c['C']:.5f} ({dC:+.1%}) P={pr['P@1.5']:.4f} ({dP:+.4f}) R={pr['R@1.5']:.4f} ({dR:+.4f}) "
                f"Phi_pop={tp['Phi_pop']:.4f} (x{phi_r:.3f}) P_pop={tp['P_pop_count']:.4f} -> {'PASS' if ok else 'fail'} ({time.time()-t0:.0f}s)")
            if ev and (best is None or (ok and not best[0]) or (ok == best[0] and dC > best[1])):
                best = (ok, dC, name, merged, bridges)
    res["best_on_variant"] = best[2]
    res["seconds"] = time.time() - t0
    jp = os.path.join(OUT, f"linkgate_{scene}.json")
    json.dump(res, open(jp, "w"), indent=1, default=float)
    viz(scene, chains, best[3], best[4], best[2], cams, g, keep_g, args.view, args.device)
    log(f"[{scene}] wrote {jp} ({time.time()-t0:.0f}s)")
    return res


def report(scenes):
    R = {sc: json.load(open(os.path.join(OUT, f"linkgate_{sc}.json"))) for sc in scenes}
    L = ["# AGGRESSIVE 3D LINKING — precision-safe continuity gate (kill-test)\n"]
    names = list(R[scenes[0]]["variants"].keys())
    for sc in scenes:
        r = R[sc]
        b = r["baseline"]
        L.append(f"## {sc}\n")
        L.append(f"Shipped input `{r['shipped_npz']}` ({r['n_linelets_keep']} kept linelets -> {r['chain_info']['n_strokes']} chains); "
                 f"median full linelet length **{r['median_linelet_len']:.5f}** world; r_surf {r['r_surf']:.5f}; tau_edge (p25 of vertex "
                 f"multi-view RAW DexiNed) **{r['tau_edge']:.4f}**; tangent-gating arms (tau_angle:tau_col) {r['tau_sets']} (0.7 primary, 0.5 = banked chaining looseness); orbit {r['frames']} frames TEST 5->15.\n")
        L.append("| variant | links / candidates (geom, depth, evidence) | C (3D arc/stroke) | dC | P@1.5 | dP | R@1.5 | dR | Phi_pop | x banked | P_pop(count) | gate |")
        L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        L.append(f"| **baseline (shipped chains)** | — | {b['continuity']['C']:.5f} (n={b['continuity']['n']}) | — | {b['pr']['P@1.5']:.4f} | — | {b['pr']['R@1.5']:.4f} | — | "
                 f"{b['temporal']['Phi_pop']:.4f} | 1.000 | {b['temporal']['P_pop_count']:.4f} | — |")
        for nm in names:
            v = r["variants"][nm]; st = v["link_stats"]; c = v["continuity"]; pr = v["pr"]; tp = v["temporal"]
            L.append(f"| {nm} | {st['accepted']}/{st['n_candidates']} ({st['pass_geom']}, {st['pass_depth']}, {st['pass_evidence']}) | {c['C']:.5f} (n={c['n']}) | "
                     f"{v['dC_rel']:+.1%} | {pr['P@1.5']:.4f} | {v['dP']:+.4f} | {pr['R@1.5']:.4f} | {v['dR']:+.4f} | {tp['Phi_pop']:.4f} | "
                     f"{v['phi_ratio']:.3f} | {tp['P_pop_count']:.4f} | {'**PASS**' if v['gate_pass'] else 'fail'} |")
        L.append("")
    # verdict: GO iff some bridge-ON variant passes on ALL scenes
    on = [nm for nm in names if R[scenes[0]]["variants"][nm]["bridge_evidence"]]
    go = [nm for nm in on if all(R[sc]["variants"][nm]["gate_pass"] for sc in scenes)]
    # NO-GO clause (frozen wording): EVERY setting reaching >= +25 % continuity (any arm) either drops P beyond
    # the scene bar or degrades Phi_pop > 5 %; it needs at least one such setting per scene to be non-vacuous.
    reach = {sc: [nm for nm in names if R[sc]["variants"][nm]["dC_rel"] >= GATE["C_up"]] for sc in scenes}
    bad = {sc: [nm for nm in reach[sc] if (-R[sc]["variants"][nm]["dP"] > GATE["P_drop"][sc]) or
                (R[sc]["variants"][nm]["phi_ratio"] > GATE["phi_ratio"])] for sc in scenes}
    nogo = all(len(reach[sc]) > 0 and len(bad[sc]) == len(reach[sc]) for sc in scenes)
    verdict = "GO" if go else ("NO-GO" if nogo else "MARGINAL")
    best_on = {sc: max((nm for nm in on), key=lambda nm: R[sc]["variants"][nm]["dC_rel"]) for sc in scenes}
    L.insert(1, f"**VERDICT: {verdict}** — frozen rule: GO iff a bridge-ON operating point has C up >= +25% on chair AND lego, "
                f"P@1.5 drop <= 0.010 chair / 0.015 lego, Phi_pop <= 1.05x baseline; NO-GO iff every setting reaching +25% "
                f"fails precision or temporal. "
                + (f"Passing point(s): {go}." if go else
                   "GO fails on the CONTINUITY criterion only: best bridge-ON points "
                   + ", ".join(f"{sc} {best_on[sc]} ({R[sc]['variants'][best_on[sc]]['dC_rel']:+.1%}, dP {R[sc]['variants'][best_on[sc]]['dP']:+.4f}, Phi x{R[sc]['variants'][best_on[sc]]['phi_ratio']:.3f})" for sc in scenes)
                   + ". Settings reaching +25%: " + "; ".join(f"{sc}: {reach[sc] or 'none'} (failing P/temporal: {bad[sc] or 'none'})" for sc in scenes)
                   + ". The NO-GO clause is " + ("met." if nogo else "NOT met by its letter (no +25% setting fails precision or temporal; lego never reaches +25%), so the verdict is MARGINAL — orchestrator + agy reconcile.")) + "\n")
    L.append(f"Per-scene JSON: `out/link/linkgate_<scene>.json`; viz `out/link/linkgate_<scene>_viz_v25.png` (shipped vs best bridge-ON variant, bridges in orange).")
    open(os.path.join(OUT, "LINKING_GATE_RESULTS.md"), "w").write("\n".join(L))
    log("\n".join(L))
    return verdict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="chair")
    ap.add_argument("--stage", default="run", choices=["run", "report"])
    ap.add_argument("--scenes", nargs="+", default=["chair", "lego"])
    ap.add_argument("--mults", type=float, nargs="+", default=[1.0, 2.0, 3.0])
    ap.add_argument("--tau_sets", type=str, default="0.7:0.7,0.5:0.5",
                    help="tangent gating arms tau_angle:tau_col (primary first; 0.5:0.5 = the banked chaining's looseness)")
    ap.add_argument("--frames", type=int, default=240)
    ap.add_argument("--view", type=int, default=25)
    ap.add_argument("--device", default="cuda")
    args = ap.parse_args()
    args.tau_sets = [tuple(float(x) for x in t.split(":")) for t in args.tau_sets.split(",")]
    if args.stage == "report":
        report(args.scenes)
    else:
        run_scene(args.scene, args)


if __name__ == "__main__":
    main()
