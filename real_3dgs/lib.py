# -*- coding: utf-8 -*-
"""Reusable pipeline primitives shared by experiment.py and fuse.py.
Approach-agnostic: load -> object-space scalars -> camera -> G-buffer ->
image-space occlusion/crease -> project candidates. No mesh, no retrain, CPU.
"""
import numpy as np
from scipy.ndimage import (convolve, binary_dilation, binary_erosion,
                           grey_dilation, grey_erosion, gaussian_filter)
from scipy.spatial import cKDTree
from render import load_scene, build_geometry, render


# ----------------------------------------------------------------- scene
def load_scene_ctx(path, opacity_cut=0.18, max_splats=220000):
    pos, scl, quat, rgb, opa = load_scene(path)
    keep = opa > opacity_cut
    pos, scl, quat, rgb, opa = [a[keep] for a in (pos, scl, quat, rgb, opa)]
    if len(pos) > max_splats:
        idx = np.argsort(opa)[-max_splats:]
        pos, scl, quat, rgb, opa = [a[idx] for a in (pos, scl, quat, rgb, opa)]
    cov3d, normal = build_geometry(pos, scl, quat)
    center = np.median(pos, axis=0)
    evec = np.linalg.eigh(np.cov((pos - center).T))[1]
    scale = np.linalg.norm(np.percentile(pos, 95, 0) - np.percentile(pos, 5, 0))
    return dict(pos=pos, scl=scl, quat=quat, rgb=rgb, opa=opa, cov3d=cov3d,
                normal=normal, center=center, evec=evec, scale=scale)


# ------------------------------------------- object-space (view-independent)
def compute_object_space(sc, k=10, tensor_smooth=True):
    """Per-Gaussian: anisotropy flat-filter, KNN-smoothed normal, structure-tensor ratios.
    tensor_smooth=True  : build the structure tensor on KNN-smoothed normals
                          (denoises heavily-noisy REAL scans).
    tensor_smooth=False : build it on RAW normals (preserves sharp normal jumps ->
                          recovers genuine creases on clean/CAD-like geometry)."""
    pos, scl, normal = sc["pos"], sc["scl"], sc["normal"]
    ssort = np.sort(scl, axis=1)
    ratio = ssort[:, 0] / (ssort[:, 1] + 1e-9)
    flat = ratio <= np.quantile(ratio, 0.6)                # keep flattest 60% (<= so uniform-scale synthetic objects keep all, not none)

    tree = cKDTree(pos)
    dist, nbr = tree.query(pos, k=k + 1)
    nbr, dist = nbr[:, 1:], dist[:, 1:]
    wts = np.exp(-(dist ** 2) / (2 * (np.median(dist) + 1e-6) ** 2))

    nn = normal[nbr]                                        # raw, sign-corrected
    sgn = np.sign(np.einsum('nki,ni->nk', nn, normal)); sgn[sgn == 0] = 1
    nn = nn * sgn[..., None]
    nsm = np.einsum('nk,nki->ni', wts, nn)                  # smoothed per-Gaussian normal
    nsm /= (np.linalg.norm(nsm, axis=1, keepdims=True) + 1e-9)

    if tensor_smooth:
        src = nsm[nbr]
        sgn2 = np.sign(np.einsum('nki,ni->nk', src, nsm)); sgn2[sgn2 == 0] = 1
        src = src * sgn2[..., None]
    else:
        src = nn                                           # raw -> keeps crease discontinuity
    T = np.einsum('nk,nki,nkj->nij', wts, src, src) / wts.sum(1)[:, None, None]
    ev = np.linalg.eigvalsh(T)
    l3, l2, l1 = ev[:, 0], ev[:, 1], ev[:, 2]
    sc.update(nsm=nsm, r2=l2 / (l1 + 1e-9), r3=l3 / (l1 + 1e-9), flat=flat, tree=tree, nbr=nbr)
    return sc


def candidate_indices(sc, eye, topk=(2500, 3000, 1500), crease_r2=0.40):
    """Select silhouette/crease/corner candidate Gaussian indices for a camera.
    crease_r2: min lambda2/lambda1 for a crease. 0.40 fits noisy real scans; lower
    (~0.25) for clean/CAD geometry where 60-deg edges give r2~=0.33."""
    pos, nsm, r2, r3, flat = sc["pos"], sc["nsm"], sc["r2"], sc["r3"], sc["flat"]
    vdir = pos - eye; vdir /= (np.linalg.norm(vdir, axis=1, keepdims=True) + 1e-9)
    ndotv = np.abs(np.einsum('ni,ni->n', nsm, vdir))
    I = np.arange(len(pos))
    silh = I[flat & (ndotv < 0.18) & (r2 < crease_r2)]
    crease = I[flat & (r2 > crease_r2) & (r3 < 0.15)]
    corner = I[flat & (r3 > 0.30)]

    def tk(sel, score, n):
        return sel if len(sel) <= n else sel[np.argsort(score[sel])[-n:]]
    silh = tk(silh, 1 - ndotv, topk[0])
    crease = tk(crease, r2 * (1 - r3), topk[1])
    corner = tk(corner, r3, topk[2])
    return dict(silhouette=silh, crease=crease, corner=corner, ndotv=ndotv)


# ----------------------------------------------------------------- camera
def camera_axes(sc, view="mid", dist=1.35):
    e = sc["evec"]
    if view in ("iso", "iso2"):                            # oblique WORLD-space 3/4 view
        d_ = np.array([1.0, 0.8, 1.4]) if view == "iso" else np.array([1.3, 0.7, -1.1])
        d_ = d_ / np.linalg.norm(d_)
        return sc["center"] + d_ * sc["scale"] * dist, sc["center"], np.array([0.0, 1.0, 0.0])
    axes = {"thin": (e[:, 0], e[:, 1]), "mid": (e[:, 1], e[:, 0]), "long": (e[:, 2], e[:, 1])}
    d_, up_ = axes[view]
    eye = sc["center"] + d_ * sc["scale"] * dist
    return eye, sc["center"], up_


def render_gbuffer(sc, eye, target, up, W=780, H=780, fov=45):
    return render(sc["pos"], sc["cov3d"], sc["normal"], sc["rgb"], sc["opa"],
                  eye, target, up, W=W, H=H, fov=fov)


# ----------------------------------------------------------------- image-space
def sobel_mag(img):
    if img.ndim == 2:
        img = img[..., None]
    Kx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], float); Ky = Kx.T
    gx = sum(convolve(img[..., c], Kx, mode="nearest") for c in range(img.shape[2]))
    gy = sum(convolve(img[..., c], Ky, mode="nearest") for c in range(img.shape[2]))
    return np.hypot(gx, gy)


def image_space_lines(gb, rel_thr=0.05, crease_q=0.965):
    """occlusion contours (clean, depth) + crease response (noisy, normals)."""
    mask = gb["mask"]; bg = ~mask; depth = gb["depth"]
    dfin = depth.copy(); dfin[bg] = np.nanmax(depth[mask])
    dn = (dfin - np.nanmin(dfin)); dn /= (dn.max() + 1e-9)

    outer = binary_dilation(mask, iterations=1) & ~binary_erosion(mask, iterations=1)
    interior = binary_erosion(mask, iterations=1)
    lmax = grey_dilation(np.where(mask, depth, -1e9), size=3)
    lmin = grey_erosion(np.where(mask, depth, 1e9), size=3)
    rel = (lmax - lmin) / np.maximum(depth, 1e-6)
    occlusion = outer | (interior & (rel > rel_thr))

    nrm = gb["normal"]
    nrm_s = np.stack([gaussian_filter(np.where(mask, nrm[..., c], 0.0), 1.3) for c in range(3)], -1)
    cre = sobel_mag(nrm_s)
    thr_c = np.quantile(cre[interior], crease_q) if interior.any() else 1.0
    crease_im = interior & (cre > thr_c)
    return dict(occlusion=occlusion, crease_im=crease_im, crease_resp=cre,
                dn=dn, interior=interior, mask=mask, bg=bg)


# ----------------------------------------------------------------- projection
def project(sc, gb, sel):
    """Project candidate Gaussian indices -> screen (u,v), camera depth z, in-frame mask."""
    p = sc["pos"][sel]
    cam = (p - gb["eye"]) @ gb["Rcw"].T
    z = cam[:, 2]
    u = gb["focal"] * cam[:, 0] / z + gb["cx"]
    v = gb["cy"] - gb["focal"] * cam[:, 1] / z
    ok = (z > 0.05) & (u > 0) & (u < gb["W"] - 1) & (v > 0) & (v < gb["H"] - 1)
    return u, v, z, ok


def project_visible(sc, gb, sel, tol):
    u, v, z, ok = project(sc, gb, sel)
    u, v, z = u[ok], v[ok], z[ok]
    iu, iv = u.astype(int), v.astype(int)
    db = gb["depth"][iv, iu]
    vis = ~np.isnan(db) & (z <= db + tol)
    return u[vis], v[vis]
