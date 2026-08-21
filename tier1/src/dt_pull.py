"""tier1/src/dt_pull.py — sub-pixel DT PULL of 3D linelets (METHOD PATH, the M1b hero).

HARD INVARIANT: gaussians + training RGBs + cameras ONLY. Never imports mesh_oracle.

WHAT THIS SOLVES
    M1a's seeds are a high-recall region proposal: their centres sit inside a 5px basin
    of the true crease (measured on chair f=0.30: 58%/66% of visible seeds are already
    <1.5px from a GT crease, another ~25% sit in the [1.5,5)px JITTER band, and ~9-17%
    are >5px away = genuine false positives). The jitter is not a ranking problem — no
    re-scoring can fix it, because it is smaller than one splat. It is a REFINEMENT
    problem, and the only sub-pixel signal available mesh-free is the photograph.
    So: attach a linelet to every seed and slide it, in 3D, until its projection lands
    on the image edge in EVERY view at once. Multi-view agreement is what makes a 2D
    edge correction into a consistent 3D one.

WHICH EDGE MAP (measured — this is the single most important knob)
    M1a scores seeds with a heavily blurred two-scale Canny union, EDGE_M1A =
    ((2.0,100,200),(2.5,75,150)). That is right for RANKING (it wants a smooth, ~3%-dense
    regional field) and WRONG for PULLING: a sigma=2..2.5 blur displaces the edge from
    the geometry that caused it. Measured on chair, "is the correct target even present
    inside the 5px trust region" (best achievable P@1.5 of any 5px pull, per view):
        EDGE_M1A   (blurred)  : target present 0.85/0.83   ceiling P@1.5 = 0.726/0.746
        EDGE_SHARP (unblurred): target present 0.96/0.99   ceiling P@1.5 = 0.842/0.940
    The blur costs ~0.2 of achievable precision. DEFAULT IS THEREFORE EDGE_SHARP; pass
    edge_cfgs=EDGE_M1A to reproduce the M1a field as an ablation.

THE THREE GUARDS
  1. TRUST REGION delta_max=5px, anchored on the frozen seed p0 and enforced exactly by
     re-projecting after every Adam step: max over visible views of ||pi_k(p)-pi_k(p0)||
     is clamped to 5px by shrinking the world-space offset. 5px is the MEASURED jitter
     radius; a linelet that wants more is crossing to a different image feature.
  2. 3-POINT DIRECTIONAL SAMPLING: the loss reads the DT at p-l*t, p and p+l*t and
     averages BEFORE the Huber. A whole segment must lie on a linear 2D feature, so an
     isolated texture blob cannot capture the linelet the way it can capture a point.
  MEASURED DEFAULTS (chair f=0.30, swept one factor at a time, 87 runs): edge='sharp',
  100 views (25 views costs -0.020 P@1.5, so multi-view consensus really does buy
  precision), 100 steps (the cosine anneal converges to 4.6e-4 px of projected motion in
  the last 10 steps; 200-400 steps buy <=+0.003), delta_max=5 (2 pins 48% of linelets at
  the cap and costs -0.013; 8 gains +0.002 but is a spec deviation), lr_t=0.30 (free:
  +0.006 segment recall for -0.0005 precision). lam_s=lam_t is a PROTOCOL TRADE, not a
  win: 0.10 gives +0.010 point precision but -0.010 SEGMENT precision at matched segment
  recall, and a linelet is drawn as a segment, so the default stays 0.02. Switching
  smoothness off entirely costs -0.021, so it is doing real work. huber_delta is NOT
  an independent knob: it only rescales the data gradient, so the real axis is
  lam_s*huber_delta (optimum ~0.2-0.3). dir_weight (+0.0001) and require_fg (+0.0007) are
  measured NO-OPS on this scene and are kept only as ablation switches. view_chunk is not
  numerically neutral (float associativity): 10 vs 25 moves P@1.5 by ~0.001 and segment
  recall by ~0.003, which is enough to flip a knife-edge threshold — pin it when
  comparing configurations.

  3. VISIBILITY GATING from the gaussian z-buffer (never the mesh): a view whose linelet
     is occluded contributes zero weight, so it cannot drag the linelet onto the edge of
     whatever is in front of it. Two-sided |z - D_k| < rel_tol*z, 3x3-min z-buffer.
"""
import os
import cv2
import numpy as np
import torch
import torch.nn.functional as F

from . import render

CACHE_DIR = os.path.expanduser("~/3dgs_line/tier1/cache")

# unblurred Canny: the sub-pixel PULL target (see module docstring)
EDGE_SHARP = ((0, 50, 150),)
# the M1a ranking field, kept for the ablation
EDGE_M1A = ((2.0, 100, 200), (2.5, 75, 150))
EDGE_SETS = {"sharp": EDGE_SHARP, "m1a": EDGE_M1A,
             "sharp_lo": ((0, 20, 60),),
             "sharp_multi": ((0, 50, 150), (1.0, 100, 200))}


# --------------------------------------------------------------------- edge + DT
def edge_map(rgb_path, cfgs=EDGE_SHARP):
    """Union of Canny edge maps of one training photograph (RGBA over white)."""
    im = cv2.imread(rgb_path, cv2.IMREAD_UNCHANGED)
    if im is None:
        raise FileNotFoundError(rgb_path)
    if im.ndim == 3 and im.shape[2] == 4:
        a = im[:, :, 3:4].astype(np.float32) / 255.0
        bgr = (im[:, :, :3].astype(np.float32) * a + 255.0 * (1 - a)).astype(np.uint8)
    else:
        bgr = im[:, :, :3]
    g0 = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    e = np.zeros(g0.shape, np.uint8)
    for sig, lo, hi in cfgs:
        g = cv2.GaussianBlur(g0, (0, 0), sig) if sig > 0 else g0
        e |= cv2.Canny(g, lo, hi)
    return e > 0


def _dt(mask):
    return cv2.distanceTransform((~mask).astype(np.uint8), cv2.DIST_L2, 5)


def build_dt_cache(scene, rgb_paths, views, cfg_name="sharp", force=False,
                   cache_dir=CACHE_DIR):
    """Per-view distance transform of the pull edge map. [V,H,W] float16."""
    os.makedirs(cache_dir, exist_ok=True)
    p = os.path.join(cache_dir, f"pulldt_{scene}_{cfg_name}_v{len(views)}.npz")
    if os.path.exists(p) and not force:
        return np.load(p)["dt"]
    cfgs = EDGE_SETS[cfg_name]
    out = np.stack([_dt(edge_map(rgb_paths[v], cfgs)).astype(np.float16) for v in views])
    np.savez(p, dt=out)
    return out


def build_gated_dt_cache(scene, rgb_paths, g, keep, cams, views, cfg_name="sharp",
                         theta=20.0, tau_depth=0.015, dilate_px=2, soft=False,
                         force=False, cache_dir=CACHE_DIR, device="cuda", verbose=True):
    """DT of the GEOMETRY-GATED edge field (see src/geom_gate.py, and read its docstring
    for the measured evidence that this gate does NOT work on vanilla 3DGS). Returns
    (dt[V,H,W] f16, stats dict with the before/after edge-pixel counts the spec asks for)."""
    from . import geom_gate
    os.makedirs(cache_dir, exist_ok=True)
    tag = f"{cfg_name}_th{theta:g}_dd{tau_depth:g}{'_soft' if soft else ''}"
    p = os.path.join(cache_dir, f"pullgdt_{scene}_{tag}_v{len(views)}.npz")
    if os.path.exists(p) and not force:
        z = np.load(p)
        return z["dt"], {"n_before": int(z["n_before"]), "n_after": int(z["n_after"])}
    cfgs = EDGE_SETS[cfg_name]
    out, nb, na = [], 0, 0
    for i, v in enumerate(views):
        gb = render.render_gbuffer(g, keep, cams[v], device=device)
        sup = geom_gate.geom_support(gb, theta_thresh=theta, tau_depth=tau_depth, soft=soft)
        del gb
        torch.cuda.empty_cache()
        e = edge_map(rgb_paths[v], cfgs)
        d, ge = geom_gate.gated_dt(e, sup, dilate_px=dilate_px)
        nb += int(e.sum())
        na += int(ge.sum())
        out.append(d.astype(np.float16))
        if verbose and i % 20 == 0:
            print(f"    [gated dt] view {i}/{len(views)}", flush=True)
    out = np.stack(out)
    np.savez(p, dt=out, n_before=nb, n_after=na)
    return out, {"n_before": nb, "n_after": na}


def build_geom_cache(scene, g, keep, cams, views, force=False, cache_dir=CACHE_DIR,
                     device="cuda", verbose=True):
    """Per-view gaussian 3x3-min z-buffer + foreground mask (METHOD PATH: no mesh).

    The 3x3 min is baked in here (not at query time) so the optimiser only ever holds
    one [V,H,W] depth tensor. Returns (depthmin[V,H,W] f16, fg[V,H,W] uint8)."""
    os.makedirs(cache_dir, exist_ok=True)
    p = os.path.join(cache_dir, f"pullgeom_{scene}_v{len(views)}.npz")
    if os.path.exists(p) and not force:
        z = np.load(p)
        return z["depthmin"], z["fg"]
    D, Fg = [], []
    for i, v in enumerate(views):
        gb = render.render_gbuffer(g, keep, cams[v], device=device)
        d = torch.nan_to_num(gb["depth"], posinf=1e9).float()[None, None]
        dmin = (-F.max_pool2d(-d, 3, stride=1, padding=1))[0, 0]
        D.append(dmin.clamp(max=60000.0).cpu().numpy().astype(np.float16))
        Fg.append((gb["alpha"] > 0.5).cpu().numpy().astype(np.uint8))
        del gb
        torch.cuda.empty_cache()
        if verbose and i % 20 == 0:
            print(f"    [geom cache] view {i}/{len(views)}", flush=True)
    D = np.stack(D)
    Fg = np.stack(Fg)
    np.savez(p, depthmin=D, fg=Fg)
    return D, Fg


# --------------------------------------------------------------------- the field
class PullField:
    """Per-view DT / z-buffer / camera bundle, resident on the GPU as float16."""

    def __init__(self, cams, views, dt, depthmin, fg, device="cuda"):
        self.device = torch.device(device)
        self.views = list(views)
        self.V = len(views)
        c0 = cams[views[0]]
        self.H, self.W = c0.H, c0.W
        self.f = float(c0.f)
        self.cx = float(c0.K[0, 2])
        self.cy = float(c0.K[1, 2])
        R = np.stack([cams[v].w2c[:3, :3] for v in views])
        t = np.stack([cams[v].w2c[:3, 3] for v in views])
        self.R = torch.tensor(R, dtype=torch.float32, device=self.device)
        self.tv = torch.tensor(t, dtype=torch.float32, device=self.device)
        self.dt = torch.tensor(np.ascontiguousarray(dt), device=self.device)      # f16
        self.depth = torch.tensor(np.ascontiguousarray(depthmin), device=self.device)
        self.fg = torch.tensor(np.ascontiguousarray(fg), device=self.device)      # u8
        self.cam_centers = torch.tensor(
            np.stack([cams[v].center for v in views]), dtype=torch.float32,
            device=self.device)

    # ---- projection (differentiable) ----
    def project(self, P, k0=0, k1=None):
        """P[M,3] float32 -> uv[Vc,M,2], z[Vc,M]. Gradients flow to P."""
        k1 = self.V if k1 is None else k1
        cam = torch.einsum("vij,mj->vmi", self.R[k0:k1], P) + self.tv[k0:k1, None, :]
        z = cam[..., 2]
        zc = z.clamp(min=1e-6)
        u = self.f * cam[..., 0] / zc + self.cx
        v = self.f * cam[..., 1] / zc + self.cy
        return torch.stack([u, v], -1), z

    def sample(self, buf, uv, k0=0, k1=None):
        """Bilinear sample of buf[V,H,W] at uv[Vc,M,2]; gradients flow to uv."""
        k1 = self.V if k1 is None else k1
        img = buf[k0:k1].float().unsqueeze(1)                       # [Vc,1,H,W]
        gx = 2.0 * uv[..., 0] / (self.W - 1) - 1.0
        gy = 2.0 * uv[..., 1] / (self.H - 1) - 1.0
        grid = torch.stack([gx, gy], -1).unsqueeze(2)               # [Vc,M,1,2]
        o = F.grid_sample(img, grid, mode="bilinear", padding_mode="border",
                          align_corners=True)
        return o[:, 0, :, 0]                                        # [Vc,M]

    def sample_dt(self, uv, k0=0, k1=None):
        return self.sample(self.dt, uv, k0, k1)

    # ---- visibility (no gradient) ----
    def visibility(self, P, rel_tol=0.02, two_sided=True, require_fg=False,
                   chunk=25):
        """[V,M] float32 weights in {0,1}: is this world point visible in this view?"""
        M = len(P)
        out = torch.zeros((self.V, M), device=self.device)
        with torch.no_grad():
            for k0 in range(0, self.V, chunk):
                k1 = min(k0 + chunk, self.V)
                uv, z = self.project(P, k0, k1)
                u = uv[..., 0].round().long()
                v = uv[..., 1].round().long()
                inb = (z > 1e-6) & (u >= 0) & (u < self.W) & (v >= 0) & (v < self.H)
                uc = u.clamp(0, self.W - 1)
                vc = v.clamp(0, self.H - 1)
                vidx = torch.arange(k0, k1, device=self.device)[:, None].expand_as(uc)
                zb = self.depth[vidx, vc, uc].float()
                if two_sided:
                    ok = (zb - z).abs() < rel_tol * z
                else:
                    ok = z <= zb + rel_tol * z
                ok = ok & inb
                if require_fg:
                    ok = ok & (self.fg[vidx, vc, uc] > 0)
                out[k0:k1] = ok.float()
        return out


def build_field(scene, g, keep, cams, rgb_paths, views, cfg_name="sharp",
                device="cuda", force=False, verbose=True, gate=None):
    """gate=None -> raw RGB-Canny DT. gate=dict(theta=,tau_depth=,dilate_px=,soft=) ->
    geometry-gated DT (src/geom_gate.py). The returned field carries .gate_stats."""
    if gate:
        dt, gst = build_gated_dt_cache(scene, rgb_paths, g, keep, cams, views,
                                       cfg_name=cfg_name, force=force, device=device,
                                       verbose=verbose, **gate)
    else:
        dt, gst = build_dt_cache(scene, rgb_paths, views, cfg_name=cfg_name,
                                 force=force), None
    dm, fg = build_geom_cache(scene, g, keep, cams, views, force=force,
                              device=device, verbose=verbose)
    f = PullField(cams, views, dt, dm, fg, device=device)
    f.gate_stats = gst
    return f


# --------------------------------------------------------------------- optimiser
def _huber(r, delta):
    a = r.abs()
    return torch.where(a <= delta, 0.5 * a * a / delta, a - 0.5 * delta)


def _trust_clamp(field, dp, p0_t, scale, delta_max, vis, iters=3, chunk=25):
    """GUARD 1 — hard trust region, enforced by re-projection (in place on dp.data).

    Shrinks each linelet's world offset until max over VISIBLE views of the projected
    displacement from its seed is <= delta_max px. Projection is not linear in the
    offset, so this is iterated; 3 passes is exact to <0.01px at 5px."""
    with torch.no_grad():
        anyvis = vis.sum(0) > 0
        for _ in range(iters):
            P = p0_t + dp * scale[:, None]
            dmax = torch.zeros(len(dp), device=dp.device)
            for k0 in range(0, field.V, chunk):
                k1 = min(k0 + chunk, field.V)
                uv, z = field.project(P, k0, k1)
                uv0, z0 = field.project(p0_t, k0, k1)
                d = torch.linalg.norm(uv - uv0, dim=-1)             # [Vc,M]
                w = vis[k0:k1]
                w = torch.where(anyvis[None, :].expand_as(w), w, torch.ones_like(w))
                d = torch.where(w > 0, d, torch.zeros_like(d))
                dmax = torch.maximum(dmax, d.max(0).values)
            over = dmax > delta_max
            if not over.any():
                break
            s = torch.where(over, delta_max / dmax.clamp(min=1e-9),
                            torch.ones_like(dmax))
            dp.mul_(s[:, None])


def _dir_weight(field, uva, uvb, uvc, k0, k1, eps=1e-6):
    """Optional GUARD: down-weight a view where the projected tangent is orthogonal to
    the local 2D edge direction. |grad DT| ~ 1 and points ACROSS the edge, so the edge
    direction is perpendicular to it; a linelet that crosses the edge it is sitting on
    is looking at an unrelated feature in this view."""
    with torch.no_grad():
        d = uvc - uva
        n = torch.linalg.norm(d, dim=-1, keepdim=True).clamp(min=eps)
        tdir = d / n
        off = torch.tensor([[1.0, 0.0], [0.0, 1.0]], device=uvb.device)
        gx = (field.sample_dt(uvb + off[0], k0, k1) -
              field.sample_dt(uvb - off[0], k0, k1)) * 0.5
        gy = (field.sample_dt(uvb + off[1], k0, k1) -
              field.sample_dt(uvb - off[1], k0, k1)) * 0.5
        gmag = torch.sqrt(gx * gx + gy * gy).clamp(min=eps)
        # |sin| between tangent and DT gradient == alignment with the edge direction
        cross = (tdir[..., 0] * gy - tdir[..., 1] * gx).abs() / gmag
        return torch.clamp(cross, 0.0, 1.0)


def pull(field, L, steps=100, lr=0.35, lr_t=0.30, lr_l=0.02, delta_max=5.0,
         lr_final_frac=0.02, lam_a=0.0,
         huber_delta=2.0, lam_s=0.02, lam_t=0.02, opt_tangent=True, opt_length=False,
         rel_tol=0.02, two_sided=True, require_fg=False, dir_weight=False,
         view_chunk=25, vis_every=25, l_bounds=(0.5, 3.0), verbose=True, log=None):
    """Batched multi-view DT pull of ALL linelets at once. Returns a result dict.

    L: dict from linelet.init_linelets (p0/p/t/l/knn). Nothing here sees the mesh.
    """
    dev = field.device
    S = len(L["p0"])
    p0_t = torch.tensor(L["p0"], dtype=torch.float32, device=dev)
    t_init = torch.tensor(L["t"], dtype=torch.float32, device=dev)
    l_init = torch.tensor(L["l"], dtype=torch.float32, device=dev)

    # world units per pixel, per linelet: z / f at the median visible depth.
    vis = field.visibility(p0_t, rel_tol=rel_tol, two_sided=two_sided,
                           require_fg=require_fg)
    zall = []
    with torch.no_grad():
        for k0 in range(0, field.V, view_chunk):
            k1 = min(k0 + view_chunk, field.V)
            zall.append(field.project(p0_t, k0, k1)[1])
        zall = torch.cat(zall, 0)                                    # [V,S]
    zv = torch.where(vis > 0, zall, torch.full_like(zall, float("nan")))
    zmed = torch.nanmedian(zv, dim=0).values  # NaN where never visible -> fixed below
    zmed = torch.where(torch.isnan(zmed), zall.median(0).values, zmed)
    scale = (zmed / field.f).clamp(min=1e-9)                         # world units / px

    dp = torch.zeros((S, 3), device=dev, requires_grad=True)
    traw = t_init.clone().requires_grad_(opt_tangent)
    llog = torch.log(l_init.clamp(min=1e-9)).clone().requires_grad_(opt_length)

    groups = [{"params": [dp], "lr": lr}]
    if opt_tangent:
        groups.append({"params": [traw], "lr": lr_t})
    if opt_length:
        groups.append({"params": [llog], "lr": lr_l})
    opt = torch.optim.Adam(groups)
    base_lrs = [gi['lr'] for gi in opt.param_groups]

    knn = torch.tensor(L["knn"], dtype=torch.long, device=dev)
    l_lo = l_init * l_bounds[0]
    l_hi = l_init * l_bounds[1]
    W = vis.sum(0)                                                    # [S] view count
    hist = []

    for it in range(steps):
        # cosine anneal: Adam's step size is ~lr px, so a constant lr floors the
        # achievable accuracy at ~lr px. Sub-pixel alignment REQUIRES decaying it.
        if steps > 1:
            frac = lr_final_frac + (1 - lr_final_frac) * 0.5 * (
                1 + np.cos(np.pi * it / (steps - 1)))
            for gi, base in zip(opt.param_groups, base_lrs):
                gi["lr"] = base * frac
        if it > 0 and vis_every and it % vis_every == 0:
            with torch.no_grad():
                P = p0_t + dp * scale[:, None]
                vis = field.visibility(P, rel_tol=rel_tol, two_sided=two_sided,
                                       require_fg=require_fg)
                W = vis.sum(0)
        Wc = W.clamp(min=1e-6)
        opt.zero_grad(set_to_none=True)
        tot = 0.0
        for k0 in range(0, field.V, view_chunk):
            k1 = min(k0 + view_chunk, field.V)
            w = vis[k0:k1]
            if w.sum() == 0:
                continue
            tn = traw / torch.linalg.norm(traw, dim=1, keepdim=True).clamp(min=1e-9)
            ll = torch.exp(llog).clamp(min=1e-9)
            P = p0_t + dp * scale[:, None]
            d3 = (ll[:, None] * tn)
            pts = torch.cat([P - d3, P, P + d3], 0)                  # [3S,3]
            uv, _ = field.project(pts, k0, k1)                       # [Vc,3S,2]
            dts = field.sample_dt(uv, k0, k1).view(k1 - k0, 3, S)
            dt3 = dts.mean(1)                                        # GUARD 2
            ww = w
            if dir_weight:
                ww = w * _dir_weight(field, uv[:, :S], uv[:, S:2 * S],
                                     uv[:, 2 * S:], k0, k1)
            e = (ww * _huber(dt3, huber_delta)).sum(0) / Wc
            loss = e.sum() / S
            loss.backward()
            tot += float(loss.detach())

        # smoothness: neighbouring linelets move together and stay co-oriented.
        # lam_a is an ANCHOR spring to p0. It was proposed to stop the pull BREAKING the
        # 8.2%/10.8% of seeds that were already sub-pixel-correct, but it was then
        # MEASURED AND IT DOES NOT WORK: no-prune P@1.5 = 0.6806 (lam_a=0) / 0.6385
        # (0.02) / 0.6265 (0.10) / 0.6225 (0.30). It damps the jitter correction more
        # than it protects the good seeds. Kept at 0.0 as a documented negative result.
        if lam_s > 0 or lam_a > 0 or (lam_t > 0 and opt_tangent):
            opt_extra = 0.0
            if lam_a > 0:
                opt_extra = opt_extra + lam_a * (dp * dp).sum(-1).mean()
            if lam_s > 0:
                dd = dp[:, None, :] - dp[knn]
                opt_extra = opt_extra + lam_s * (dd * dd).sum(-1).mean()
            if lam_t > 0 and opt_tangent:
                tn = traw / torch.linalg.norm(traw, dim=1, keepdim=True).clamp(min=1e-9)
                cosine = (tn[:, None, :] * tn[knn]).sum(-1).abs()
                opt_extra = opt_extra + lam_t * (1.0 - cosine).mean()
            opt_extra.backward()
            tot += float(opt_extra.detach())

        opt.step()
        _trust_clamp(field, dp, p0_t, scale, delta_max, vis, chunk=view_chunk)
        if opt_length:
            with torch.no_grad():
                llog.clamp_(torch.log(l_lo), torch.log(l_hi))
        if verbose and (it % 10 == 0 or it == steps - 1):
            msg = f"    [pull] it {it:3d}  loss {tot:.4f}"
            print(msg, flush=True)
            if log is not None:
                log.append(msg)
        hist.append(tot)

    with torch.no_grad():
        tn = (traw / torch.linalg.norm(traw, dim=1, keepdim=True).clamp(min=1e-9))
        ll = torch.exp(llog)
        P = p0_t + dp * scale[:, None]
        vis = field.visibility(P, rel_tol=rel_tol, two_sided=two_sided,
                              require_fg=require_fg)
        resid = torch.zeros((field.V, S), device=dev)
        resid3 = torch.zeros((field.V, S), device=dev)
        for k0 in range(0, field.V, view_chunk):
            k1 = min(k0 + view_chunk, field.V)
            d3 = ll[:, None] * tn
            pts = torch.cat([P - d3, P, P + d3], 0)
            uv, _ = field.project(pts, k0, k1)
            dts = field.sample_dt(uv, k0, k1).view(k1 - k0, 3, S)
            resid[k0:k1] = dts[:, 1]
            resid3[k0:k1] = dts.mean(1)
        # how far did we actually move, in pixels, per view (for reporting)
        move = torch.zeros(S, device=dev)
        for k0 in range(0, field.V, view_chunk):
            k1 = min(k0 + view_chunk, field.V)
            uv, _ = field.project(P, k0, k1)
            uv0, _ = field.project(p0_t, k0, k1)
            d = torch.linalg.norm(uv - uv0, dim=-1) * (vis[k0:k1] > 0)
            move = torch.maximum(move, d.max(0).values)

    return {"p": P.cpu().numpy().astype(np.float64),
            "t": tn.cpu().numpy().astype(np.float64),
            "l": ll.cpu().numpy().astype(np.float64),
            "resid": resid.cpu().numpy(), "resid3": resid3.cpu().numpy(),
            "vis": vis.cpu().numpy().astype(bool),
            "move_px": move.cpu().numpy(), "hist": hist,
            "scale": scale.cpu().numpy()}
