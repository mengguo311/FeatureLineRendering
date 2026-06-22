# -*- coding: utf-8 -*-
"""Image-space vs object-space line drawing on a REAL 3DGS scene.
Usage: experiment.py <scene.splat> [view=mid] [dist=1.35] [opacity_cut=0.18]
                     [max_splats=220000] [fov=45]
- image-space : Sobel on the rendered (real, noisy) depth+normal G-buffer.
- object-space: silhouette/crease/corner candidates straight from the Gaussian
  covariance field (per-Gaussian normal + anisotropy filter + KNN normal
  smoothing + local normal-structure tensor). NO mesh.
"""
import sys, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.ndimage import (convolve, binary_dilation, binary_erosion,
                           grey_dilation, grey_erosion, gaussian_filter)
from scipy.spatial import cKDTree
from render import load_scene, build_geometry, render

scene = sys.argv[1] if len(sys.argv) > 1 else "nike.splat"
view_axis = sys.argv[2] if len(sys.argv) > 2 else "mid"
dist_mul = float(sys.argv[3]) if len(sys.argv) > 3 else 1.35
opacity_cut = float(sys.argv[4]) if len(sys.argv) > 4 else 0.18
max_splats = int(sys.argv[5]) if len(sys.argv) > 5 else 220000
fov = float(sys.argv[6]) if len(sys.argv) > 6 else 45.0
stem = os.path.splitext(os.path.basename(scene))[0]
OUT = "outputs"
os.makedirs("%s/comparison" % OUT, exist_ok=True)
os.makedirs("%s/gbuffer" % OUT, exist_ok=True)

# ---------------------------------------------------------------- load
pos, scl, quat, rgb, opa = load_scene(scene)
keep = opa > opacity_cut
pos, scl, quat, rgb, opa = [a[keep] for a in (pos, scl, quat, rgb, opa)]
if len(pos) > max_splats:
    idx = np.argsort(opa)[-max_splats:]
    pos, scl, quat, rgb, opa = [a[idx] for a in (pos, scl, quat, rgb, opa)]
cov3d, normal = build_geometry(pos, scl, quat)
print("[%s] scene: %d gaussians" % (stem, len(pos)))

center = np.median(pos, axis=0)
C = np.cov((pos - center).T)
ev_, evec = np.linalg.eigh(C)
axes = {"thin": (evec[:, 0], evec[:, 1]), "mid": (evec[:, 1], evec[:, 0]),
        "long": (evec[:, 2], evec[:, 1])}
d_, up_ = axes[view_axis]
scale = np.linalg.norm(np.percentile(pos, 95, 0) - np.percentile(pos, 5, 0))

W = H = 780
eye = center + d_ * scale * dist_mul
gb = render(pos, cov3d, normal, rgb, opa, eye, center, up_, W=W, H=H, fov=fov)
print("[%s] coverage %.1f%%" % (stem, 100 * gb["mask"].mean()))

# ---------------------------------------------------------------- image-space
def sobel_mag(img):
    if img.ndim == 2:
        img = img[..., None]
    Kx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], float); Ky = Kx.T
    gx = sum(convolve(img[..., c], Kx, mode="nearest") for c in range(img.shape[2]))
    gy = sum(convolve(img[..., c], Ky, mode="nearest") for c in range(img.shape[2]))
    return np.hypot(gx, gy)

mask = gb["mask"]; bg = ~mask; depth = gb["depth"]
# normalized depth (for the G-buffer visualization only)
dfin = depth.copy(); dfin[bg] = np.nanmax(depth[mask])
dn = (dfin - np.nanmin(dfin)); dn /= (dn.max() + 1e-9)

# --- IMAGE-SPACE OCCLUSION CONTOURS (the robust depth-based signal) ---
# (a) outer silhouette = coverage-mask boundary  -> uniform & complete,
#     independent of how far the surface is there (it's a discontinuity, not a magnitude).
outer = binary_dilation(mask, iterations=1) & ~binary_erosion(mask, iterations=1)
# (b) internal occlusion = large *relative* depth jump inside the object.
interior = binary_erosion(mask, iterations=1)
lmax = grey_dilation(np.where(mask, depth, -1e9), size=3)
lmin = grey_erosion(np.where(mask, depth, 1e9), size=3)
rel = (lmax - lmin) / np.maximum(depth, 1e-6)
internal = interior & (rel > 0.05)
occlusion = outer | internal

# --- IMAGE-SPACE CREASE LINES (normal discontinuity; denoise the noisy
#     normal buffer first, then keep only the strongest responses) ---
nrm = gb["normal"]
nrm_s = np.stack([gaussian_filter(np.where(mask, nrm[..., c], 0.0), 1.3) for c in range(3)], -1)
cre = sobel_mag(nrm_s)
thr_c = np.quantile(cre[interior], 0.965) if interior.any() else 1.0
crease_im = interior & (cre > thr_c)
print("[%s] occlusion px=%d  crease px=%d" % (stem, int(occlusion.sum()), int(crease_im.sum())))

# ---------------------------------------------------------------- object-space
ssort = np.sort(scl, axis=1)
smin, smid = ssort[:, 0], ssort[:, 1]
ratio = smin / (smid + 1e-9)                            # smaller = flatter/more reliable
flat = ratio < np.quantile(ratio, 0.6)                 # adaptive: keep flattest 60%
print("[%s] flat (reliable-normal): %d / %d" % (stem, int(flat.sum()), len(pos)))

K = 10
tree = cKDTree(pos)
dist, nbr = tree.query(pos, k=K + 1)
nbr = nbr[:, 1:]; dist = dist[:, 1:]
sig = np.median(dist) + 1e-6
wts = np.exp(-(dist ** 2) / (2 * sig ** 2))

nn = normal[nbr]
sgn = np.sign(np.einsum('nki,ni->nk', nn, normal)); sgn[sgn == 0] = 1
nn = nn * sgn[..., None]
nsm = np.einsum('nk,nki->ni', wts, nn)
nsm /= (np.linalg.norm(nsm, axis=1, keepdims=True) + 1e-9)
nn2 = nsm[nbr]
sgn2 = np.sign(np.einsum('nki,ni->nk', nn2, nsm)); sgn2[sgn2 == 0] = 1
nn2 = nn2 * sgn2[..., None]
T = np.einsum('nk,nki,nkj->nij', wts, nn2, nn2) / wts.sum(1)[:, None, None]
ev = np.linalg.eigvalsh(T)
l3, l2, l1 = ev[:, 0], ev[:, 1], ev[:, 2]
r2 = l2 / (l1 + 1e-9); r3 = l3 / (l1 + 1e-9)

vdir = pos - eye; vdir /= (np.linalg.norm(vdir, axis=1, keepdims=True) + 1e-9)
ndotv = np.abs(np.einsum('ni,ni->n', nsm, vdir))

I = np.arange(len(pos))
crease_sel = I[flat & (r2 > 0.40) & (r3 < 0.15)]
corner_sel = I[flat & (r3 > 0.30)]
silh_sel = I[flat & (ndotv < 0.18) & (r2 < 0.40)]
print("[%s] candidates: silh=%d crease=%d corner=%d"
      % (stem, len(silh_sel), len(crease_sel), len(corner_sel)))

def topk(sel, score, k):
    return sel if len(sel) <= k else sel[np.argsort(score[sel])[-k:]]
crease_sel = topk(crease_sel, r2 * (1 - r3), 3000)
corner_sel = topk(corner_sel, r3, 1500)
silh_sel = topk(silh_sel, 1 - ndotv, 2500)

Rcw, e, focal, cx, cy = gb["Rcw"], gb["eye"], gb["focal"], gb["cx"], gb["cy"]
def project_visible(sel, tol):
    p = pos[sel]; cam = (p - e) @ Rcw.T; z = cam[:, 2]
    u = focal * cam[:, 0] / z + cx; v = cy - focal * cam[:, 1] / z
    ok = (z > 0.05) & (u > 0) & (u < W - 1) & (v > 0) & (v < H - 1)
    u, v, z = u[ok], v[ok], z[ok]
    iu, iv = u.astype(int), v.astype(int)
    db = gb["depth"][iv, iu]
    vis = ~np.isnan(db) & (z <= db + tol)
    return u[vis], v[vis]

tol = 0.04 * scale
su, sv = project_visible(silh_sel, tol)
cu, cv = project_visible(crease_sel, tol)
ku, kv = project_visible(corner_sel, tol)
print("[%s] visible: silh=%d crease=%d corner=%d" % (stem, len(su), len(cu), len(ku)))

# ---------------------------------------------------------------- figures
base = gb["color"].copy(); base[bg] = 1.0
faint = base * 0.45 + 0.55

fig, ax = plt.subplots(1, 3, figsize=(13.5, 4.7))
ax[0].imshow(base); ax[0].set_title("%s — 3DGS render (CPU EWA, no GPU)" % stem, fontsize=10)
dv = np.ma.masked_where(bg, dn)
ax[1].imshow(np.ones((H, W, 3))); ax[1].imshow(dv, cmap="turbo"); ax[1].set_title("Depth buffer", fontsize=11)
nv = (gb["normal"] * 0.5 + 0.5); nv[bg] = 1
ax[2].imshow(nv); ax[2].set_title("Normal buffer (covariance thin-axis)", fontsize=11)
for a in ax: a.set_xticks([]); a.set_yticks([])
plt.tight_layout(); plt.savefig("%s/gbuffer/%s_gbuffer.png" % (OUT, stem), dpi=160, bbox_inches="tight"); plt.close()

# thicken lines for slide legibility (occlusion bolder, drawn ON TOP)
occ_disp = binary_dilation(occlusion, iterations=2)
cre_disp = binary_dilation(crease_im, iterations=1)

fig, ax = plt.subplots(1, 2, figsize=(11.5, 5.4)); fig.patch.set_facecolor("white")
ax[0].imshow(faint)
creo = np.zeros((H, W, 4)); creo[cre_disp] = (0.90, 0.40, 0.0, 0.95)      # creases first (under)
ax[0].imshow(creo, interpolation="nearest")
occo = np.zeros((H, W, 4)); occo[occ_disp] = (0.0, 0.0, 0.0, 1.0)          # occlusion bold on top
ax[0].imshow(occo, interpolation="nearest")
ax[0].set_title("(a) IMAGE-SPACE — occlusion contours (black, from depth) = CLEAN\n"
                "creases (orange, from noisy normals) = unreliable; + temporal flicker",
                fontsize=9.5, color="#b00000")
ax[1].imshow(faint)
ax[1].scatter(su, sv, s=3.5, c="#1f5fd6", alpha=0.6, linewidths=0, label="silhouette (|n·v|≈0)")
ax[1].scatter(cu, cv, s=3.5, c="#d6451f", alpha=0.7, linewidths=0, label="crease (λ₂/λ₁ high)")
ax[1].scatter(ku, kv, s=14, c="#15a015", alpha=0.95, linewidths=0, label="corner (λ₃/λ₁ high)")
ax[1].set_title("(b) OBJECT-SPACE — candidates from Gaussian covariance\n"
                "no mesh: per-Gaussian normal + KNN structure tensor",
                fontsize=10.5, color="#0a6b0a")
ax[1].legend(loc="lower right", fontsize=8, framealpha=0.9, markerscale=2)
for a in ax:
    a.set_xlim(0, W); a.set_ylim(H, 0); a.set_xticks([]); a.set_yticks([])
plt.tight_layout(); plt.savefig("%s/comparison/%s_comparison.png" % (OUT, stem), dpi=160, bbox_inches="tight"); plt.close()
print("[%s] saved: %s/gbuffer/%s_gbuffer.png  %s/comparison/%s_comparison.png" % (stem, OUT, stem, OUT, stem))
