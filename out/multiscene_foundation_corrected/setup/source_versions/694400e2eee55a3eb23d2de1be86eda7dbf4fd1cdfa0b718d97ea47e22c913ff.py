"""tier1/src/gate2dgs.py — Plan #1 STEP B: geometry gate on the 2DGS G-buffer (METHOD PATH).

HARD INVARIANT: gaussians/surfels + training RGBs + cameras only. This file must NEVER
import mesh_oracle or read the GT mesh.

WHY THIS EXISTS, AND WHY IT USES NORMALS AND NOT DEPTH
    src/geom_gate.py is the same idea on vanilla 3DGS, and its own docstring records that it
    does not work: vanilla bakes printed fabric into geometry, so the dihedral at a print is
    as large as at a crease (fabric theta_p95 79.3 deg vs crease theta_p05 4.9 deg).
    STEP A (scripts/explore/gate_falsify_2dgs.py) re-ran that falsification on 2DGS with a
    GT-mesh ceiling arm and an added subset restricted to pixels the mesh says are FLAT.
    Measured on chair, 8 views, FLAT-fabric vs SHARP-crease:

        arm / signal                          fabric p50   fabric p95   AUC
        vanilla-3DGS  ribbon dihedral, DEPTH      33.8         82.9      0.443
        2DGS          ribbon dihedral, DEPTH      10.7         75.6      0.740
        vanilla-3DGS  ribbon dihedral, NORMAL     11.9         38.5      0.696
        2DGS          ribbon dihedral, NORMAL      1.80         7.29     0.967   <== this
        GT mesh       ribbon dihedral, DEPTH       0.82         4.04     1.000

    So the gate is built on the 2DGS *rendered normal* map. 2DGS depth is much better than
    vanilla depth but still far from clean (AUC 0.740) because the median-depth buffer is
    quantised per surfel; ORing a depth-step term into the support would inject exactly the
    false positives the gate exists to remove. `use_depth` is therefore False by default,
    and the flag is kept only so the choice can be re-measured rather than assumed.

    Threshold intuition from the same table: flat printed surface sits under ~7 deg
    (p95 7.29), genuine creases sit around 24.5 deg (p50), so tau_geom lives in ~8-15 deg.
    It is swept on the VAL split by scripts/tune_tau_geom_2dgs.py -- never on TEST.

FOREGROUND.  2DGS trained on a white background keeps a "splat canvas" of off-object
surfels (random-point init + white bg makes them free), so `alpha > 0.5` covers ~99.8% of
the frame and is NOT an object mask. That is harmless here and deliberately left alone:
the gate is ANDed with the Canny edge map, the background is uniform white and carries no
Canny edges, and `dihedral_map` skips any pixel whose normal gradient is below gmag_min, so
the canvas costs neither false positives nor compute. At the silhouette the chair/canvas
depth jump does produce support -- which is correct, an occluding contour IS a feature line.
"""
import os

import cv2
import numpy as np
import torch
import torch.nn.functional as F

from . import geom_gate, render2dgs
from .dt_pull import edge_map, EDGE_SETS, CACHE_DIR

# frozen operating point, picked on VAL (see scripts/tune_tau_geom_2dgs.py)
TAU_GEOM = 10.0
DILATE_PX = 2
DP = geom_gate.DP
GMAG_MIN = geom_gate.GMAG_MIN


def geom_support_2dgs(gb2, tau_geom=TAU_GEOM, dp=DP, gmag_min=GMAG_MIN,
                      use_depth=False, tau_depth=0.015, rad=3, soft=False, tau_soft=4.0):
    """Texture-blind geometric-crease support G_v from ONE 2DGS G-buffer.

    gb2: dict from render2dgs.render_gbuffer_2dgs (torch tensors).
    Returns bool [H,W] (or float32 in [0,1] when soft=True).
    The dihedral estimator is geom_gate.dihedral_map, imported not re-implemented, so the
    gate measures exactly what STEP A falsified.
    """
    dep = gb2["depth"].detach().cpu().numpy().astype(np.float32)
    nrm = gb2["normal"].detach().cpu().numpy()
    alp = gb2["alpha"].detach().cpu().numpy()
    A = geom_gate.dihedral_map(nrm, dep, alp, dp=dp, gmag_min=gmag_min)
    if soft:
        w = 1.0 / (1.0 + np.exp(-(A - tau_geom) / max(tau_soft, 1e-6)))
        if use_depth:
            D = geom_gate.depth_step_map(dep, alp, rad=rad)
            w = np.maximum(w, 1.0 / (1.0 + np.exp(-(D - tau_depth) /
                                                  max(tau_depth * 0.5, 1e-6))))
        return w.astype(np.float32)
    m = A >= tau_geom
    if use_depth:
        m = m | (geom_gate.depth_step_map(dep, alp, rad=rad) >= tau_depth)
    return m


# ---- the ribbon estimator STEP A actually validated -------------------------------
# Identical geometry to scripts/explore/gate_falsify_2dgs.ribbon_normal_measure (which is
# what produced the AUC 0.967 row above); duplicated here rather than imported because that
# file is EVAL-side and this one is METHOD-side and may not depend on it.
OFF_ACROSS = (2.0, 3.0, 4.0)                 # ribbon centre +-3px, 3px thick
OFF_ALONG = np.arange(-4.5, 5.0, 1.0)        # 10px long
MIN_VALID = 8


def edge_normals_dir(rgb_path):
    """Across-edge direction at every pixel, from the image gradient (METHOD PATH).

    The ribbon needs to know which way is 'across the edge'. The Canny edge itself does not
    carry an orientation, but the smoothed intensity gradient does, and it is exactly what
    gate_falsify used, so the gate measures what STEP A falsified.
    """
    im = cv2.imread(rgb_path, cv2.IMREAD_UNCHANGED)
    if im.ndim == 3 and im.shape[2] == 4:
        a = im[:, :, 3:4].astype(np.float32) / 255.0
        bgr = (im[:, :, :3].astype(np.float32) * a + 255.0 * (1 - a)).astype(np.uint8)
    else:
        bgr = im[:, :, :3]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gb1 = cv2.GaussianBlur(gray, (0, 0), 1.0)
    gx = cv2.Sobel(gb1, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(gb1, cv2.CV_64F, 0, 1, ksize=3)
    gm = np.sqrt(gx * gx + gy * gy)
    dirx = np.where(gm > 1e-9, gx / np.maximum(gm, 1e-9), 1.0)
    diry = np.where(gm > 1e-9, gy / np.maximum(gm, 1e-9), 0.0)
    return dirx, diry


# cv2.remap requires every map dimension < SHRT_MAX; a whole view's Canny set is larger
# than that, so the ribbon is evaluated in blocks. (gate_falsify_2dgs never hit this because
# it caps at 20000 px per view and class.)
REMAP_CHUNK = 20000


def ribbon_normal_theta(px, py, dirx, diry, normal, fg, chunk=REMAP_CHUNK):
    """Angle (deg) between the mean rendered normal of the two ribbon sides, at pixels
    (px,py). Returns (theta[N], ok[N]). Pure numpy/cv2; no mesh, no GT."""
    n = len(px)
    if n > chunk:
        th = np.empty(n, np.float64)
        ok = np.empty(n, bool)
        for a in range(0, n, chunk):
            b = min(a + chunk, n)
            th[a:b], ok[a:b] = _ribbon_normal_theta(px[a:b], py[a:b], dirx[a:b],
                                                    diry[a:b], normal, fg)
        return th, ok
    return _ribbon_normal_theta(px, py, dirx, diry, normal, fg)


def _ribbon_normal_theta(px, py, dirx, diry, normal, fg):
    H, W = fg.shape
    ax, ay = dirx, diry
    lx, ly = -diry, dirx
    nrm = np.ascontiguousarray(normal, np.float32)
    val = fg.astype(np.float32)
    sides = {}
    for sgn, key in ((-1.0, "L"), (+1.0, "R")):
        acc = np.zeros((len(px), 3), np.float64)
        wsum = np.zeros(len(px), np.float64)
        for da in OFF_ACROSS:
            for dl in OFF_ALONG:
                qx = np.clip(px + sgn * da * ax + dl * lx, 0, W - 1).astype(np.float32)
                qy = np.clip(py + sgn * da * ay + dl * ly, 0, H - 1).astype(np.float32)
                w = cv2.remap(val, qx, qy, cv2.INTER_NEAREST).ravel()
                for c in range(3):
                    acc[:, c] += w * cv2.remap(nrm[:, :, c], qx, qy,
                                               cv2.INTER_LINEAR).ravel()
                wsum += w
        n = acc / np.maximum(wsum, 1e-9)[:, None]
        nn = np.linalg.norm(n, axis=1, keepdims=True)
        sides[key] = (n / np.maximum(nn, 1e-30), wsum >= MIN_VALID, nn[:, 0])
    nL, okL, mL = sides["L"]
    nR, okR, mR = sides["R"]
    theta = np.degrees(np.arccos(np.clip(np.abs((nL * nR).sum(1)), -1, 1)))
    ok = okL & okR & np.isfinite(theta) & (mL > 0.2) & (mR > 0.2)
    return theta, ok


def ribbon_gate_edges(edge, gb2, dirx, diry, tau_geom=TAU_GEOM, keep_unmeasurable=False):
    """E_v = Canny pixels whose BILATERAL-RIBBON normal dihedral clears tau_geom.

    This is the STEP-A-validated estimator used as the gate. Because the ribbon is
    evaluated exactly AT each Canny pixel (oriented by that pixel's own image gradient),
    there is nothing to dilate -- unlike the patch-based `geom_support_2dgs` map, which is
    computed on a grid and therefore needs a 2px dilation to reach the edge.

    keep_unmeasurable: what to do with a pixel whose ribbon could not be fitted (too few
    valid samples, e.g. right at the frame border). False = drop it, which is the
    conservative choice for a gate.
    """
    ys, xs = np.nonzero(edge)
    out = np.zeros_like(edge, dtype=bool)
    if not len(ys):
        return out, np.zeros(0), np.zeros(0, bool)
    nrm = gb2["normal"].detach().cpu().numpy()
    alp = gb2["alpha"].detach().cpu().numpy()
    dep = gb2["depth"].detach().cpu().numpy()
    fg = (alp > 0.5) & np.isfinite(dep)
    theta, ok = ribbon_normal_theta(xs.astype(np.float64), ys.astype(np.float64),
                                    dirx[ys, xs], diry[ys, xs], nrm, fg)
    sel = (theta >= tau_geom) & ok if not keep_unmeasurable else \
          ((theta >= tau_geom) & ok) | (~ok)
    out[ys[sel], xs[sel]] = True
    return out, theta, ok


def _dt(mask):
    return cv2.distanceTransform((~mask).astype(np.uint8), cv2.DIST_L2, 5)


def build_2dgs_caches(scene, model_path, rgb_paths, cams, views, cfg_name="sharp",
                      tau_geom=TAU_GEOM, dilate_px=DILATE_PX, use_depth=False,
                      soft=False, half_pixel=True, force=False, cache_dir=CACHE_DIR,
                      verbose=True, keep_support=False, mode="ribbon"):
    """One pass over `views`: gated-edge DT + visibility z-buffer + fg, all from 2DGS.

    Returns (dt[V,H,W] f16, depthmin[V,H,W] f16, fg[V,H,W] u8, stats).
    stats carries the per-view before/after edge-pixel counts the spec asks for.
    Both products come from the SAME G-buffer render, so the pull's DT target and its
    occlusion test are guaranteed consistent (the spec's "visibility from the 2DGS depth").
    """
    os.makedirs(cache_dir, exist_ok=True)
    mtag = os.path.basename(os.path.normpath(model_path))
    tag = (f"{scene}_{mtag}_{mode}_{cfg_name}_tg{tau_geom:g}_dl{dilate_px}"
           f"{'_d' if use_depth else ''}{'_soft' if soft else ''}"
           f"{'_hp' if half_pixel else '_nohp'}_v{len(views)}")
    p = os.path.join(cache_dir, f"plan1_{tag}.npz")
    if os.path.exists(p) and not force:
        z = np.load(p, allow_pickle=True)
        st = {"n_before": int(z["n_before"]), "n_after": int(z["n_after"]),
              "per_view_before": z["pvb"].tolist(), "per_view_after": z["pva"].tolist(),
              "cache": p}
        if verbose:
            print(f"  [gate2dgs] reusing {os.path.basename(p)}  "
                  f"edge px {st['n_before']} -> {st['n_after']} "
                  f"({100.0 * st['n_after'] / max(st['n_before'], 1):.1f}% survive)",
                  flush=True)
        return z["dt"], z["depthmin"], z["fg"], st

    g2, pipe, meta = render2dgs.load_2dgs(model_path)
    cfgs = EDGE_SETS[cfg_name]
    DT, DM, FG = [], [], []
    pvb, pva = [], []
    sup_out = [] if keep_support else None
    for i, v in enumerate(views):
        gb2 = render2dgs.render_gbuffer_2dgs(g2, pipe, cams[v],
                                             bg_white=meta.get("white_background", True),
                                             half_pixel=half_pixel)
        e = edge_map(rgb_paths[v], cfgs)
        if mode == "ribbon":
            dirx, diry = edge_normals_dir(rgb_paths[v])
            ge, _, _ = ribbon_gate_edges(e, gb2, dirx, diry, tau_geom=tau_geom)
            sup = None
        else:
            sup = geom_support_2dgs(gb2, tau_geom=tau_geom, use_depth=use_depth, soft=soft)
            ge = geom_gate.gate_edges(e, sup, dilate_px=dilate_px)
        d = (_dt(ge) if ge.any() else np.full(e.shape, 1e3, np.float32))
        DT.append(d.astype(np.float16))
        pvb.append(int(e.sum()))
        pva.append(int(ge.sum()))
        if keep_support and sup is not None:
            sup_out.append(sup)

        dep = torch.nan_to_num(gb2["depth"], posinf=1e9).float()[None, None]
        dmin = (-F.max_pool2d(-dep, 3, stride=1, padding=1))[0, 0]
        DM.append(dmin.clamp(max=60000.0).cpu().numpy().astype(np.float16))
        FG.append((gb2["alpha"] > 0.5).cpu().numpy().astype(np.uint8))
        del gb2
        torch.cuda.empty_cache()
        if verbose and i % 20 == 0:
            print(f"    [gate2dgs] view {i}/{len(views)}", flush=True)

    DT = np.stack(DT); DM = np.stack(DM); FG = np.stack(FG)
    nb, na = int(np.sum(pvb)), int(np.sum(pva))
    np.savez(p, dt=DT, depthmin=DM, fg=FG, n_before=nb, n_after=na,
             pvb=np.array(pvb), pva=np.array(pva))
    st = {"n_before": nb, "n_after": na, "per_view_before": pvb,
          "per_view_after": pva, "cache": p}
    if verbose:
        print(f"  [gate2dgs] edge px {nb} -> {na} "
              f"({100.0 * na / max(nb, 1):.1f}% survive)  tau_geom={tau_geom}", flush=True)
    if keep_support:
        st["support"] = sup_out
    return DT, DM, FG, st


def surfel_edge_evidence(P, cams, views, dt, depthmin, sigma=2.0, rel_tol=0.02,
                         chunk=200000):
    """Multi-view gated-edge evidence per 3D point -- the STEP B seed score.

    For every point and every view in which it is unoccluded, read the gated-edge DT at its
    projection and score exp(-DT^2 / 2 sigma^2); the point's score is the mean over its
    visible views, and points seen by nobody score 0.

    This is the mesh-free analogue of the M1a OVERALL recipe, but it can be this simple
    because the gate has already removed the printed-texture edges: on vanilla 3DGS the raw
    Canny DT was dominated by fabric print, which is why M1a needed a ranked multi-term
    recipe. Background "splat canvas" surfels need no special handling either -- they
    project onto uniform white, which carries no Canny edge, so they score 0 and can never
    be selected.

    Returns (score[M], n_vis[M]).
    """
    M = len(P)
    acc = np.zeros(M, np.float64)
    cnt = np.zeros(M, np.int64)
    inv2s2 = 1.0 / (2.0 * sigma * sigma)
    for k, v in enumerate(views):
        cam = cams[v]
        zb = torch.tensor(depthmin[k].astype(np.float32))
        zb_np = zb.numpy()
        d_np = dt[k].astype(np.float32)
        for a in range(0, M, chunk):
            b = min(a + chunk, M)
            Q = P[a:b]
            campts = (cam.w2c[:3, :3] @ Q.T).T + cam.w2c[:3, 3]
            z = campts[:, 2]
            uv = (cam.K @ campts.T).T
            uv = uv[:, :2] / np.clip(uv[:, 2:3], 1e-9, None)
            u = np.round(uv[:, 0]).astype(np.int64)
            w = np.round(uv[:, 1]).astype(np.int64)
            ok = (z > 0) & (u >= 0) & (u < cam.W) & (w >= 0) & (w < cam.H)
            idx = np.where(ok)[0]
            if not len(idx):
                continue
            vis = z[idx] <= zb_np[w[idx], u[idx]] + rel_tol * z[idx]
            idx = idx[vis]
            if not len(idx):
                continue
            dv = d_np[w[idx], u[idx]].astype(np.float64)
            acc[a + idx] += np.exp(-(dv * dv) * inv2s2)
            cnt[a + idx] += 1
    score = np.where(cnt > 0, acc / np.maximum(cnt, 1), 0.0)
    return score, cnt


def load_surfels(model_path, opa_min=0.1):
    """2DGS surfel centres / scales / opacity, de-floatered by opacity only.

    Returns dict(mu[N,3], scale[N,2], opacity[N], keep[N]).  NOTE 2DGS surfels carry TWO
    scales (they are discs, not ellipsoids), which linelet.init_linelets handles unchanged
    because it only takes scale.max(1).
    """
    g2, pipe, meta = render2dgs.load_2dgs(model_path)
    with torch.no_grad():
        mu = g2.get_xyz.detach().cpu().numpy().astype(np.float64)
        sc = g2.get_scaling.detach().cpu().numpy().astype(np.float64)
        op = g2.get_opacity.detach().cpu().numpy().astype(np.float64).ravel()
    del g2
    torch.cuda.empty_cache()
    return {"mu": mu, "scale": sc, "opacity": op, "keep": op > opa_min, "meta": meta}


# ----------------------------------------------------------------- M1a-style seed recipe
def surfel_evidence_matrix(P, cams, views, dt, depthmin, rel_tol=0.02, chunk=200000):
    """Per-view gated-edge DT at each point's projection.

    Returns (D[V,M] float32, vis[V,M] bool). D is 0 where not visible; read it with vis.
    """
    V, M = len(views), len(P)
    D = np.zeros((V, M), np.float32)
    VIS = np.zeros((V, M), bool)
    for k, v in enumerate(views):
        cam = cams[v]
        zb = depthmin[k].astype(np.float32)
        dv = dt[k].astype(np.float32)
        for a in range(0, M, chunk):
            b = min(a + chunk, M)
            campts = (cam.w2c[:3, :3] @ P[a:b].T).T + cam.w2c[:3, 3]
            z = campts[:, 2]
            uv = (cam.K @ campts.T).T
            uv = uv[:, :2] / np.clip(uv[:, 2:3], 1e-9, None)
            u = np.round(uv[:, 0]).astype(np.int64)
            w = np.round(uv[:, 1]).astype(np.int64)
            ok = (z > 0) & (u >= 0) & (u < cam.W) & (w >= 0) & (w < cam.H)
            idx = np.where(ok)[0]
            if not len(idx):
                continue
            vv = z[idx] <= zb[w[idx], u[idx]] + rel_tol * z[idx]
            idx = idx[vv]
            if not len(idx):
                continue
            D[k, a + idx] = dv[w[idx], u[idx]]
            VIS[k, a + idx] = True
    return D, VIS


def _rank01(v):
    from scipy.stats import rankdata
    return rankdata(v) / len(v)


def local_rank(X, s, rad_mult=2.0):
    """Fraction of neighbours within rad_mult * median-1NN-spacing that this point beats.

    Verbatim in spirit from scripts/explore/syn/final_recipe.local_rank: the multi-view
    evidence is REGIONAL (a 2px-wide crease and its immediate surroundings score almost the
    same), so a purely global ranking selects whole clusters straddling a crease. Comparing
    members of one cluster against each other is what resolves it.
    """
    from scipy.spatial import cKDTree
    tree = cKDTree(X)
    sp = float(np.median(tree.query(X, k=2)[0][:, 1]))
    balls = tree.query_ball_point(X, r=rad_mult * sp, workers=-1)
    return np.array([np.mean(s[np.asarray(b)] < s[i]) if len(b) > 1 else 1.0
                     for i, b in enumerate(balls)])


def surfel_score_overall(X, D, VIS, sigma_soft=16.0, lam_local=0.5, rad_mult=2.0):
    """The M1a OVERALL recipe structure, ported to the 2DGS surfel cloud.

        g = R(soft) + 0.5 R(-q90) + 0.5 local_rank(g)

    R = rank/len; soft = mean_v exp(-DT/sigma) over visible views (a smooth "how close to a
    gated edge, on average"); q90 = the 90th percentile of DT over visible views (a
    worst-case term that punishes a surfel which is on an edge in most views but far from
    one in a few -- i.e. a view-dependent, non-static feature).

    The first-cut score used by scripts/run_plan1.py is just the `soft` term with sigma=2px,
    and it SATURATES: at f=0.30 its selected seeds ran from 0.698 to ~1.0, so it can barely
    order them. The worst-case and local-competition terms are what M1a needed on vanilla
    3DGS, and they are needed here for the same reason -- they are about seed RANKING, not
    about texture, so the gate does not remove the need for them.
    """
    nv = np.maximum(VIS.sum(0), 1)
    never = VIS.sum(0) == 0
    soft = np.where(VIS, np.exp(-D / sigma_soft), 0.0).sum(0) / nv
    with np.errstate(all="ignore"):
        q90 = -np.nan_to_num(np.nanpercentile(np.where(VIS, D, np.nan), 90, axis=0),
                             nan=1e9)
    soft[never] = soft.min() - 1
    q90[never] = q90.min() - 1
    g = _rank01(soft) + 0.5 * _rank01(q90)
    g = g + lam_local * local_rank(X, g, rad_mult=rad_mult)
    g[never] = -1.0
    return g, VIS.sum(0)
