# -*- coding: utf-8 -*-
"""Minimal CPU EWA splatter for a real .splat 3DGS scene -> color/depth/normal G-buffer.
No GPU/CUDA. Produces the G-buffers the line-drawing experiments consume.
"""
import sys, time
import numpy as np

# ----------------------------------------------------------------------
def load_splat(path):
    raw = np.fromfile(path, dtype=np.uint8).reshape(-1, 32)
    pos = raw[:, 0:12].copy().view(np.float32).reshape(-1, 3).astype(np.float64)
    scl = raw[:, 12:24].copy().view(np.float32).reshape(-1, 3).astype(np.float64)
    rgba = raw[:, 24:28].astype(np.float64) / 255.0
    quat = (raw[:, 28:32].astype(np.float64) - 128.0) / 128.0   # [w,x,y,z]
    return pos, scl, quat, rgba[:, :3], rgba[:, 3]


def load_ply(path):
    """Standard 3DGS .ply (scale in log-space, opacity as logit, DC-only SH ok)."""
    from plyfile import PlyData
    v = PlyData.read(path)['vertex']
    pos = np.stack([v['x'], v['y'], v['z']], 1).astype(np.float64)
    scl = np.exp(np.stack([v['scale_0'], v['scale_1'], v['scale_2']], 1)).astype(np.float64)
    quat = np.stack([v['rot_0'], v['rot_1'], v['rot_2'], v['rot_3']], 1).astype(np.float64)
    opa = (1.0 / (1.0 + np.exp(-np.asarray(v['opacity'], np.float64))))
    C0 = 0.28209479177387814
    rgb = np.clip(0.5 + C0 * np.stack([v['f_dc_0'], v['f_dc_1'], v['f_dc_2']], 1), 0, 1).astype(np.float64)
    return pos, scl, quat, rgb, opa


def load_scene(path):
    return load_ply(path) if path.lower().endswith(".ply") else load_splat(path)


def quats_to_R(q):
    q = q / (np.linalg.norm(q, axis=1, keepdims=True) + 1e-12)
    w, x, y, z = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
    R = np.empty((len(q), 3, 3))
    R[:, 0, 0] = 1 - 2 * (y * y + z * z); R[:, 0, 1] = 2 * (x * y - w * z); R[:, 0, 2] = 2 * (x * z + w * y)
    R[:, 1, 0] = 2 * (x * y + w * z); R[:, 1, 1] = 1 - 2 * (x * x + z * z); R[:, 1, 2] = 2 * (y * z - w * x)
    R[:, 2, 0] = 2 * (x * z - w * y); R[:, 2, 1] = 2 * (y * z + w * x); R[:, 2, 2] = 1 - 2 * (x * x + y * y)
    return R


def build_geometry(pos, scl, quat):
    R = quats_to_R(quat)
    S2 = scl ** 2
    cov3d = np.einsum('nij,nj,nkj->nik', R, S2, R)              # R diag(s^2) R^T
    idx = np.argmin(scl, axis=1)                               # thin axis = normal
    normal = R[np.arange(len(R)), :, idx]
    return cov3d, normal


def camera_basis(eye, target, up):
    f = np.asarray(target, float) - np.asarray(eye, float); f /= np.linalg.norm(f)
    r = np.cross(f, np.asarray(up, float)); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return np.array([r, u, f]), np.asarray(eye, float)         # R_cw rows = r,u,f ; z_cam>0 forward


def render(pos, cov3d, normal, rgb, opacity, eye, target, up,
           W=480, H=480, fov=45.0, wmin=0.02, verbose=True):
    Rcw, eye = camera_basis(eye, target, up)
    cam = (pos - eye) @ Rcw.T                                  # (N,3): x,y,z(forward)
    z = cam[:, 2]
    front = z > 0.05
    focal = 0.5 * W / np.tan(np.radians(fov) / 2)
    cx, cy = W / 2.0, H / 2.0
    upx = focal * cam[:, 0] / np.where(z != 0, z, 1) + cx
    vpx = cy - focal * cam[:, 1] / np.where(z != 0, z, 1)

    # 2D covariance via EWA Jacobian
    cov_cam = np.einsum('ij,njk,lk->nil', Rcw, cov3d, Rcw)
    x, y, zz = cam[:, 0], cam[:, 1], np.where(z != 0, z, 1)
    J = np.zeros((len(pos), 2, 3))
    J[:, 0, 0] = focal / zz; J[:, 0, 2] = -focal * x / zz ** 2
    J[:, 1, 1] = -focal / zz; J[:, 1, 2] = focal * y / zz ** 2
    cov2d = np.einsum('nij,njk,nlk->nil', J, cov_cam, J)
    cov2d[:, 0, 0] += 0.3; cov2d[:, 1, 1] += 0.3
    a = cov2d[:, 0, 0]; b = cov2d[:, 0, 1]; c = cov2d[:, 1, 1]
    det = a * c - b * b
    valid = front & (det > 1e-6) & (upx > -30) & (upx < W + 30) & (vpx > -30) & (vpx < H + 30)
    tr = a + c
    maxeig = 0.5 * (tr + np.sqrt(np.maximum(tr * tr - 4 * det, 0)))
    radius = np.clip(3.0 * np.sqrt(np.maximum(maxeig, 1e-6)), 1, 24)
    inv = det.copy(); inv[inv == 0] = 1e-6
    ca = c / inv; cb = -b / inv; cc = a / inv                  # conic (inverse 2D cov)

    # camera-space normals, flipped to face camera
    n_cam = normal @ Rcw.T
    flip = (np.einsum('ni,ni->n', n_cam, -cam) < 0)
    n_cam[flip] *= -1

    order = np.argsort(z)                                      # front -> back
    order = order[valid[order]]

    col = np.zeros((H, W, 3)); dep = np.zeros((H, W)); nrm = np.zeros((H, W, 3))
    wsum = np.zeros((H, W)); T = np.ones((H, W))

    t0 = time.time()
    for k, i in enumerate(order):
        r = int(radius[i])
        x0 = max(int(upx[i]) - r, 0); x1 = min(int(upx[i]) + r + 1, W)
        y0 = max(int(vpx[i]) - r, 0); y1 = min(int(vpx[i]) + r + 1, H)
        if x0 >= x1 or y0 >= y1:
            continue
        Tsub = T[y0:y1, x0:x1]
        if Tsub.max() < 0.01:
            continue
        gx = np.arange(x0, x1) - upx[i]; gy = np.arange(y0, y1) - vpx[i]
        dx, dy = np.meshgrid(gx, gy)
        power = -0.5 * (ca[i] * dx * dx + 2 * cb[i] * dx * dy + cc[i] * dy * dy)
        w = np.exp(np.clip(power, -50, 0))
        ae = np.clip(opacity[i] * w, 0, 0.99)
        contrib = ae * Tsub
        col[y0:y1, x0:x1] += contrib[..., None] * rgb[i]
        dep[y0:y1, x0:x1] += contrib * z[i]
        nrm[y0:y1, x0:x1] += contrib[..., None] * n_cam[i]
        wsum[y0:y1, x0:x1] += contrib
        T[y0:y1, x0:x1] = Tsub * (1 - ae)
        if verbose and k % 60000 == 0 and k:
            print("  composited %d/%d  (%.1fs)" % (k, len(order), time.time() - t0))

    alpha = 1 - T
    m = wsum > 1e-4
    depth = np.full((H, W), np.nan); depth[m] = dep[m] / wsum[m]
    nn = np.zeros((H, W, 3)); nn[m] = nrm[m] / wsum[m][:, None]
    nn /= (np.linalg.norm(nn, axis=2, keepdims=True) + 1e-9)
    if verbose:
        print("  render done: %d splats, %.1fs" % (len(order), time.time() - t0))
    return dict(color=np.clip(col, 0, 1), depth=depth, normal=nn,
                alpha=alpha, mask=m, upx=upx, vpx=vpx, z=z, valid=valid,
                Rcw=Rcw, eye=eye, focal=focal, cx=cx, cy=cy, W=W, H=H)


# ----------------------------------------------------------------------
if __name__ == "__main__":
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    pos, scl, quat, rgb, opa = load_splat("nike.splat")
    print("loaded", len(pos), "splats")
    # subsample by opacity for the preview (speed)
    keep = opa > 0.25
    pos, scl, quat, rgb, opa = pos[keep], scl[keep], quat[keep], rgb[keep], opa[keep]
    print("kept", len(pos), "after opacity cull")
    cov3d, normal = build_geometry(pos, scl, quat)

    center = np.median(pos, axis=0)
    lo, hi = np.percentile(pos, 5, axis=0), np.percentile(pos, 95, axis=0)
    scale = np.linalg.norm(hi - lo)
    # PCA axes
    C = np.cov((pos - center).T)
    evals, evecs = np.linalg.eigh(C)                            # ascending
    thin = evecs[:, 0]; mid = evecs[:, 1]; long = evecs[:, 2]
    print("center", center.round(2), "scale", round(scale, 2))

    # render 3 candidate views (look along each PCA axis)
    views = {"along_thin": (thin, mid), "along_mid": (mid, thin), "along_long": (long, mid)}
    fig, ax = plt.subplots(1, 3, figsize=(13, 4.6))
    for j, (name, (dir_, up_)) in enumerate(views.items()):
        eye = center + dir_ * scale * 1.6
        out = render(pos, cov3d, normal, rgb, opa, eye, center, up_,
                     W=420, H=420, fov=45, verbose=False)
        img = out["color"].copy(); img[~out["mask"]] = 1.0
        ax[j].imshow(img); ax[j].set_title(name, fontsize=11)
        ax[j].set_xticks([]); ax[j].set_yticks([])
        print(name, "-> coverage %.1f%%" % (100 * out["mask"].mean()))
    plt.tight_layout(); plt.savefig("preview_views.png", dpi=130, bbox_inches="tight")
    print("saved preview_views.png")
