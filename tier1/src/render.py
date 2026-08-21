"""tier1/src/render.py — lean gaussian G-buffer (METHOD PATH: gaussians only, NO mesh).

Splats each de-floatered gaussian as a small screen-space disc with gaussian falloff,
then does exact front-to-back alpha compositing per pixel via a fragment sort +
segmented exclusive cumsum of log(1-alpha) (T_i = prod(1-alpha_prev) within the pixel).
Outputs {"depth":[H,W], "normal":[H,W,3], "alpha":[H,W]} torch tensors.
depth is the transmittance-weighted mean sum(T a z)/sum(T a) (inf where alpha==0),
which is the stable form of the spec's D = sum(T a z) for the visibility z-buffer.
"""
import numpy as np
import torch
from scipy.spatial import cKDTree


def defloat_mask(mu, opacity, k=8, dist_factor=3.0, opa_min=0.1):
    """De-floater: opacity>0.1 AND kNN-mean-dist < 3x median(kNN-mean-dist)."""
    keep = opacity > opa_min
    idx = np.where(keep)[0]
    tree = cKDTree(mu[idx])
    d, _ = tree.query(mu[idx], k=k + 1)  # first neighbor is self
    md = d[:, 1:].mean(1)
    ok = md < dist_factor * np.median(md)
    mask = np.zeros(len(mu), bool)
    mask[idx[ok]] = True
    return mask


def render_gbuffer(g, keep_mask, cam, device="cuda", r_min=1.0, r_max=15.0,
                   frag_alpha_min=0.01, with_albedo=False):
    """g: dict from common.load_gaussians; keep_mask: bool [N] (de-floater);
    cam: common.Camera. Returns dict of torch tensors on `device`.

    with_albedo=True additionally composites the VIEW-INDEPENDENT SH degree-0 albedo
    (common.load_gaussians["albedo"]) with the same transmittance weights, giving
    out["albedo"][H,W,3] = sum(T a c) / sum(T a). Off by default so nothing else in the
    pipeline pays for it."""
    H, Wd = cam.H, cam.W
    mu = g["mu"][keep_mask]
    opa = g["opacity"][keep_mask]
    nrm = g["normal"][keep_mask]
    smax = g["scale_max"][keep_mask]
    alb = g["albedo"][keep_mask] if with_albedo else None

    # orient normal toward camera: n . (cam_center - mu) > 0
    flip = np.sum(nrm * (cam.center[None] - mu), 1) < 0
    nrm = nrm.copy()
    nrm[flip] *= -1

    dev = torch.device(device)
    w2c = torch.tensor(cam.w2c, dtype=torch.float32, device=dev)
    mu_t = torch.tensor(mu, dtype=torch.float32, device=dev)
    campts = mu_t @ w2c[:3, :3].T + w2c[:3, 3]
    z = campts[:, 2]
    f = float(cam.f)
    u = f * campts[:, 0] / z + Wd / 2
    v = f * campts[:, 1] / z + H / 2

    r = (torch.tensor(smax, dtype=torch.float32, device=dev) * f / z.clamp(min=1e-6)
         ).clamp(r_min, r_max)
    ok = (z > 0.01) & (u > -r) & (u < Wd - 1 + r) & (v > -r) & (v < H - 1 + r)
    u, v, z, r = u[ok], v[ok], z[ok], r[ok]
    a0 = torch.tensor(opa, dtype=torch.float32, device=dev)[ok]
    n_t = torch.tensor(nrm, dtype=torch.float32, device=dev)[ok]
    c_t = (torch.tensor(alb, dtype=torch.float32, device=dev)[ok]
           if with_albedo else None)

    # --- build fragments, bucketed by integer radius (variable disc size) ---
    Rint = torch.ceil(r).long().clamp(1, int(r_max))
    frag_pix, frag_z, frag_a, frag_n = [], [], [], []
    frag_c = []
    for R in torch.unique(Rint).tolist():
        sel = Rint == R
        if not sel.any():
            continue
        us, vs, zs, rs, as_, ns = u[sel], v[sel], z[sel], r[sel], a0[sel], n_t[sel]
        cs = c_t[sel] if with_albedo else None
        off = torch.arange(-R, R + 1, device=dev)
        du, dv = torch.meshgrid(off, off, indexing="xy")
        du, dv = du.reshape(-1), dv.reshape(-1)  # [P]
        px = torch.round(us)[:, None] + du[None]  # [n,P]
        py = torch.round(vs)[:, None] + dv[None]
        d2 = (px - us[:, None]) ** 2 + (py - vs[:, None]) ** 2
        sigma2 = (rs[:, None] / 2.0) ** 2
        alpha = as_[:, None] * torch.exp(-0.5 * d2 / sigma2.clamp(min=0.25))
        m = (d2 <= (rs[:, None] + 0.5) ** 2) & (alpha > frag_alpha_min) & \
            (px >= 0) & (px < Wd) & (py >= 0) & (py < H)
        if not m.any():
            continue
        gi, pi = torch.nonzero(m, as_tuple=True)
        frag_pix.append((py[gi, pi].long() * Wd + px[gi, pi].long()))
        frag_z.append(zs[gi])
        frag_a.append(alpha[gi, pi])
        frag_n.append(ns[gi])
        if with_albedo:
            frag_c.append(cs[gi])

    depth = torch.full((H * Wd,), float("inf"), device=dev)
    normal = torch.zeros((H * Wd, 3), device=dev)
    albedo = torch.zeros((H * Wd, 3), device=dev)
    alpha_buf = torch.zeros((H * Wd,), device=dev)
    if not frag_pix:
        out = {"depth": depth.view(H, Wd), "normal": normal.view(H, Wd, 3),
               "alpha": alpha_buf.view(H, Wd)}
        if with_albedo:
            out["albedo"] = albedo.view(H, Wd, 3)
        return out

    pix = torch.cat(frag_pix)
    fz = torch.cat(frag_z)
    fa = torch.cat(frag_a).clamp(max=0.999)
    fn = torch.cat(frag_n)
    fc = torch.cat(frag_c) if with_albedo else None

    # lexsort: stable sort by z, then stable sort by pixel -> per-pixel front-to-back
    o1 = torch.argsort(fz, stable=True)
    pix, fz, fa, fn = pix[o1], fz[o1], fa[o1], fn[o1]
    if with_albedo:
        fc = fc[o1]
    o2 = torch.argsort(pix, stable=True)
    pix, fz, fa, fn = pix[o2], fz[o2], fa[o2], fn[o2]
    if with_albedo:
        fc = fc[o2]

    # segmented exclusive cumsum of log(1-a): T_i within each pixel run
    l = torch.log1p(-fa)
    c = torch.cumsum(l, 0)
    excl = c - l
    seg_start = torch.ones_like(pix, dtype=torch.bool)
    seg_start[1:] = pix[1:] != pix[:-1]
    seg_id = torch.cumsum(seg_start.long(), 0) - 1
    base = excl[seg_start][seg_id]
    T = torch.exp(excl - base)
    w = T * fa

    wsum = torch.zeros((H * Wd,), device=dev).index_add_(0, pix, w)
    wz = torch.zeros((H * Wd,), device=dev).index_add_(0, pix, w * fz)
    normal.index_add_(0, pix, w[:, None] * fn)
    if with_albedo:
        albedo.index_add_(0, pix, w[:, None] * fc)

    hit = wsum > 1e-6
    depth[hit] = wz[hit] / wsum[hit]
    nn = torch.linalg.norm(normal, dim=1, keepdim=True)
    normal = torch.where(nn > 1e-6, normal / nn.clamp(min=1e-6), normal)

    out = {"depth": depth.view(H, Wd), "normal": normal.view(H, Wd, 3),
           "alpha": wsum.clamp(max=1.0).view(H, Wd)}
    if with_albedo:
        alb_n = torch.zeros_like(albedo)
        alb_n[hit] = albedo[hit] / wsum[hit][:, None]
        out["albedo"] = alb_n.view(H, Wd, 3)
    return out
