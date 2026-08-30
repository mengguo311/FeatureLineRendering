"""tier1/src/hybrid_gate.py — the HYBRID gate: VANILLA seeds x 2DGS geometric support.

*** METHOD PATH. Mesh-free. This file must NEVER import mesh_oracle or read the GT mesh. ***

WHY THIS FILE EXISTS
    Two measured facts (see PLAN1_RESULTS.md):
      * VANILLA 3DGS gaussians CONCENTRATE at creases, so the tuned M1a OVERALL recipe on
        them is the best seed set we have (chair M1b seg P@1.5 = 0.657 / R = 0.596), but
        vanilla geometry is albedo-contaminated (fabric normal-theta p95 38.5 deg) so it
        cannot reject printed-texture seeds.
      * 2DGS geometry is texture-BLIND on GT-flat printed surface (normal-theta p50 1.80,
        p95 7.29, AUC 0.967) but surfels tile every surface uniformly, so 2DGS-SEEDED
        pipelines lose the crease-concentration prior (2DGS-seed+2DGS-gate: seg P@1.5 0.503).
    So: keep the vanilla seeds, and use 2DGS only as a texture-blind VETO.

THE ALIGNMENT PROBLEM THIS MODULE IS BUILT AROUND
    Vanilla and 2DGS are two independent trainings. Their surfaces agree on flat regions
    and DIVERGE exactly at creases (vanilla shingles needles across the fold, 2DGS chamfers
    it). Querying a 2DGS geometric-edge map at the EXACT reprojection of a vanilla seed can
    therefore land on the adjacent flat facet and veto a true crease seed. The fix offered
    here is the DILATED REGION gate

        G_r(u,v) = OR over ||delta||_2 <= r of [ C_2dgs(u+delta, v+delta) >= tau ]

    with r measured on VAL by scripts/hybrid_step1_align.py. r absorbs the cross-
    representation misalignment; too large an r lets printed texture leak back in.

    A second, projection-immune gate is also provided (`surfel_dihedral_gate`): take each
    vanilla seed's 3D point, find its k nearest 2DGS surfels, and pass the seed if the
    maximum pairwise angle between their disc normals exceeds theta. This never
    reprojects anything, so a 2D misalignment cannot veto anything.

PIXEL GRID.  render2dgs.render_gbuffer_2dgs(half_pixel=True) resamples the 2DGS raster at
(i-0.5, j-0.5), i.e. it applies the calibrated -0.5 px shift and hands back a buffer that
is indexed with tier1 integer pixel coordinates (u = f*X/Z + W/2). Vanilla seed
reprojections computed with common.project can then be rounded and used as direct indices.
Keep half_pixel=True unless you are deliberately measuring the shift's effect.
"""
import os

import cv2
import numpy as np
import torch

from . import geom_gate, render2dgs

# STEP-B operating point picked on VAL by scripts/tune_tau_geom_2dgs.py (patch mode).
TAU_GEOM = 12.0
GMAG_MIN = geom_gate.GMAG_MIN
DP = geom_gate.DP


# --------------------------------------------------------------- per-view raw signals
def normal_grad_mag(normal, depth, alpha):
    """C(u,v) = || grad N ||_F on the rendered 2DGS normal buffer (the literal signal the
    hybrid spec names). Zero off-object. This is a LOCAL first-difference statistic: it
    fires on any normal variation, including the smooth curvature of a cylindrical leg,
    which is why the two-cluster dihedral below is usually the better discriminator."""
    fg = (alpha > 0.5) & np.isfinite(depth)
    n = np.where(fg[..., None], normal, 0.0).astype(np.float32)
    gy, gx = np.gradient(n, axis=(0, 1))
    g = np.sqrt((gx ** 2).sum(-1) + (gy ** 2).sum(-1)).astype(np.float32)
    return np.where(fg, g, 0.0)


def dihedral_deg(normal, depth, alpha, dp=DP, gmag_min=GMAG_MIN):
    """Two-cluster patch dihedral (deg) of the 2DGS normal buffer — geom_gate.dihedral_map
    imported, not re-implemented, so this measures exactly what STEP A falsified."""
    return geom_gate.dihedral_map(normal, depth, alpha, dp=dp, gmag_min=gmag_min)


SIGNALS = {"dihedral": dihedral_deg, "gradn": normal_grad_mag}


def signal_map(gb2, signal="dihedral"):
    dep = gb2["depth"].detach().cpu().numpy().astype(np.float32)
    nrm = gb2["normal"].detach().cpu().numpy()
    alp = gb2["alpha"].detach().cpu().numpy()
    return SIGNALS[signal](nrm, dep, alp), (alp > 0.5) & np.isfinite(dep)


def dilate_disk(mask, r):
    """Binary dilation by a EUCLIDEAN disk of radius r (r=0 -> identity).

    cv2.MORPH_ELLIPSE with an odd side is an approximate disk; for exactness (the radii
    here are tiny and the difference at r=2,3 is visible) the element is built explicitly
    from ||delta||_2 <= r."""
    if r <= 0:
        return mask.astype(bool)
    d = np.arange(-r, r + 1)
    dx, dy = np.meshgrid(d, d)
    k = ((dx * dx + dy * dy) <= r * r + 1e-9).astype(np.uint8)
    return cv2.dilate(mask.astype(np.uint8), k) > 0


def region_gate(sig, tau, r):
    """G_r = dilate(C >= tau, disk r). Bool [H,W]."""
    return dilate_disk(sig >= tau, r)


# ------------------------------------------------------------------ 3D surfel gate
def load_surfel_frames(model_path, opa_min=0.1):
    """2DGS surfel centres + DISC NORMALS, de-floatered by opacity.

    A 2DGS primitive is a flat disc whose local frame is the rotation quaternion; the two
    tangent axes carry the two scales and the third column of R is the disc normal (this is
    exactly what diff-surfel-rasterization splats into `rend_normal`, which is why the
    caller can cross-check these against the rendered normal buffer)."""
    g2, pipe, meta = render2dgs.load_2dgs(model_path)
    with torch.no_grad():
        mu = g2.get_xyz.detach().cpu().numpy().astype(np.float64)
        op = g2.get_opacity.detach().cpu().numpy().astype(np.float64).ravel()
        sc = g2.get_scaling.detach().cpu().numpy().astype(np.float64)
        q = g2.get_rotation.detach()                       # already normalised
        from utils.general_utils import build_rotation      # 2DGS ext, on sys.path
        R = build_rotation(q).cpu().numpy().astype(np.float64)
    n = R[:, :, 2]                                          # disc normal
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-30)
    del g2
    torch.cuda.empty_cache()
    keep = op > opa_min
    return {"mu": mu[keep], "normal": n[keep], "scale": sc[keep], "opacity": op[keep],
            "meta": meta, "n_all": len(op), "n_keep": int(keep.sum())}


def surfel_dihedral(seed_pos, mu2, n2, k=8, radius=None, tree=None):
    """Max pairwise angle (deg) between the disc normals of each seed's k nearest 2DGS
    surfels. Projection-immune: no camera, no reprojection, no pixel grid.

    radius: if given, neighbours further than this are dropped (a seed with fewer than 2
    valid neighbours gets angle 0 and n_nb < 2, so the caller can treat it as unmeasurable).
    Returns (theta_max[S], n_nb[S], d1[S]) with d1 = distance to the nearest surfel."""
    from scipy.spatial import cKDTree
    tree = tree or cKDTree(mu2)
    d, idx = tree.query(seed_pos, k=k, workers=-1)
    if k == 1:
        d, idx = d[:, None], idx[:, None]
    ok = np.isfinite(d) if radius is None else (np.isfinite(d) & (d <= radius))
    N = n2[np.clip(idx, 0, len(n2) - 1)]                    # [S,k,3]
    # sign-agnostic pairwise angle: normals of a disc have arbitrary orientation
    C = np.abs(np.einsum("ski,sji->skj", N, N)).clip(0, 1)
    ang = np.degrees(np.arccos(C))                          # [S,k,k]
    m = ok[:, :, None] & ok[:, None, :]
    ang = np.where(m, ang, -1.0)
    theta = ang.reshape(len(seed_pos), -1).max(1)
    theta = np.where(ok.sum(1) >= 2, theta, 0.0)
    return theta, ok.sum(1), d[:, 0]


# --------------------------------------------------------- vote aggregation over views
def vote_keep(pass_mat, vis_mat, frac=0.5, min_vis=1):
    """A seed survives if it passes the gate in >= frac of the views where it is VISIBLE.

    pass_mat[V,S] bool, vis_mat[V,S] bool. Seeds visible in fewer than min_vis views are
    KEPT (unmeasurable -> the gate abstains rather than deleting evidence it never saw)."""
    nv = vis_mat.sum(0)
    npass = (pass_mat & vis_mat).sum(0)
    with np.errstate(invalid="ignore", divide="ignore"):
        fr = np.where(nv > 0, npass / np.maximum(nv, 1), 1.0)
    return (fr >= frac) | (nv < min_vis), fr, nv


# ============================================================ the pipeline seed gate
CACHE_DIR = os.path.expanduser("~/3dgs_line/tier1/cache")


def build_seed_gate(scene, model_path, seeds, cams, views, depthmin,
                    signal="gradn", tau=None, tau_q=90.0, r=0, vote_frac=0.75,
                    rel_tol=0.02, half_pixel=True, force=False, verbose=True,
                    cache_dir=CACHE_DIR):
    """Which VANILLA seeds keep 2DGS geometric support?  (METHOD PATH, mesh-free.)

    For every view: render the 2DGS G-buffer, threshold the chosen geometric signal,
    dilate by r, and read it at each seed's reprojection. Occlusion is decided by the
    VANILLA z-buffer (`depthmin`, the same 3x3-min buffer the DT pull uses), because the
    seed is a vanilla gaussian and its visibility is a property of the vanilla surface --
    using the 2DGS z-buffer here would let one representation's holes delete the other's
    seeds. A seed survives if it passes in >= vote_frac of the views where it is visible.

    tau_q: when `tau` is None the threshold is the tau_q-th percentile of the signal over
    that view's on-object pixels. Per-view adaptive, still mesh-free -- it reads only the
    2DGS render. `tau` overrides it with a fixed absolute value (degrees, for `dihedral`).

    The operating point is chosen on VAL by scripts/hybrid_step1_align.py +
    hybrid_step1c_frontier.py; TEST views are never passed in here.

    Returns (keep[S] bool, info dict).
    """
    os.makedirs(cache_dir, exist_ok=True)
    mtag = os.path.basename(os.path.normpath(model_path))
    ttag = f"t{tau:g}" if tau is not None else f"q{tau_q:g}"
    p = os.path.join(cache_dir, f"seedgate_{scene}_{mtag}_{signal}_{ttag}_r{r}"
                                f"_hp{int(half_pixel)}_S{len(seeds)}_v{len(views)}.npz")
    if os.path.exists(p) and not force:
        z = np.load(p)
        P, VIS = z["pass"], z["vis"]
    else:
        g2, pipe, meta = render2dgs.load_2dgs(model_path)
        P = np.zeros((len(views), len(seeds)), bool)
        VIS = np.zeros((len(views), len(seeds)), bool)
        for k, v in enumerate(views):
            cam = cams[v]
            gb2 = render2dgs.render_gbuffer_2dgs(
                g2, pipe, cam, bg_white=meta.get("white_background", True),
                half_pixel=half_pixel)
            sig, fg2 = signal_map(gb2, signal)
            del gb2
            torch.cuda.empty_cache()
            t = tau
            if t is None:
                on = sig[fg2 & (sig > 0)]
                t = float(np.percentile(on, tau_q)) if len(on) else 0.0
            G = region_gate(sig, t, r)

            campts = (cam.w2c[:3, :3] @ seeds.T).T + cam.w2c[:3, 3]
            z = campts[:, 2]
            uv = (cam.K @ campts.T).T
            uv = uv[:, :2] / np.clip(uv[:, 2:3], 1e-9, None)
            u = np.round(uv[:, 0]).astype(np.int64)
            w = np.round(uv[:, 1]).astype(np.int64)
            inb = (z > 0) & (u >= 0) & (u < cam.W) & (w >= 0) & (w < cam.H)
            uc = np.clip(u, 0, cam.W - 1); wc = np.clip(w, 0, cam.H - 1)
            zb = depthmin[k].astype(np.float32)[wc, uc]
            VIS[k] = inb & (z <= zb + rel_tol * z)
            P[k] = G[wc, uc]
            if verbose and k % 20 == 0:
                print(f"    [seedgate] view {k}/{len(views)}", flush=True)
        del g2
        torch.cuda.empty_cache()
        np.savez_compressed(p, **{"pass": P, "vis": VIS})

    keep, fr, nv = vote_keep(P, VIS, frac=vote_frac)
    info = {"cache": p, "n_seeds": int(len(seeds)), "n_keep": int(keep.sum()),
            "keep_frac": float(keep.mean()), "vote_frac": float(vote_frac),
            "signal": signal, "tau": tau, "tau_q": tau_q, "r": int(r),
            "model": model_path, "n_views": len(views),
            "median_pass_frac": float(np.median(fr)),
            "n_never_visible": int((nv == 0).sum())}
    if verbose:
        print(f"  [seedgate] {mtag}/{signal} {ttag} r={r} vote={vote_frac}: "
              f"{info['n_keep']}/{info['n_seeds']} seeds survive "
              f"({100 * info['keep_frac']:.1f}%)", flush=True)
    return keep, info
