"""score_gline.py — family `gline`: agreement of a seed with the RENDERED G-buffer lines.

MESH-FREE.  Uses only: the gaussians (via render.render_gbuffer), the cameras, and the
per-seed object-space frame from the normal structure tensor.  No photographs, no mesh.

For a spread of views it renders the gaussian G-buffer and, at each seed's projection
(only in views where the seed is VISIBLE against that view's gaussian z-buffer), measures

  crease  q10 over visible views of `nang_sd`: the largest angle between the rendered
          normal at the seed pixel and any 8-neighbour normal that lies on the SAME
          surface (normalised inverse-depth step < 0.02).  The same-depth gate is what
          separates a genuine normal crease from an occlusion boundary.  5x5 max-pooled
          so a 1-2px projection error still lands on the ridge.  q10 = "the crease must
          be visible from (almost) every viewpoint".
  dihed   trimmed mean over visible views of the angle between the mean rendered normal
          +-2px either side of the projection ALONG THE PROJECTED e1 (across-crease)
          direction.  Geometry-aware version of the same quantity.
  nogmag  NEGATED trimmed mean of the Sobel magnitude of normalised inverse depth
          (3x3 max-pooled).  Empirically ANTI-correlated with being a real crease: the
          depth-gradient channel of the image-space line baseline fires on silhouettes
          and occlusion boundaries, which are NOT dihedral creases, so seeds sitting on
          strong depth steps are preferentially FALSE.

The three are globally rank-normalised and combined 1.5 / 0.75 / 1.5.

compute()            -> the best single score (the 3-term fusion above)
compute_crease()     -> the `crease` term alone
compute_dihed()      -> the `dihed` term alone
compute_nogmag()     -> the `nogmag` term alone
compute_ridgeval()   -> peak ||grad N|| along the across-crease profile
compute_pair()       -> nogmag + ridgeval (highest AUC variant)
"""
import os
import sys
import numpy as np
import cv2
import torch
from scipy.stats import rankdata

sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
from src import render, visibility  # noqa: E402

H = Wd = 800
DEFAULT_VIEWS = tuple(range(0, 100, 8))
OFFS = np.arange(-4.0, 4.01, 0.5)


# --------------------------------------------------------------------------- fields
def _fields(gbuf):
    depth = gbuf["depth"].detach().cpu().numpy().astype(np.float32)
    normal = gbuf["normal"].detach().cpu().numpy().astype(np.float32)
    alpha = gbuf["alpha"].detach().cpu().numpy().astype(np.float32)
    fg = alpha > 0.5
    inv = np.zeros_like(depth)
    fin = np.isfinite(depth) & (depth > 1e-6)
    inv[fin] = 1.0 / depth[fin]
    if fg.any():
        lo, hi = np.percentile(inv[fg], [1, 99])
        inv = np.clip((inv - lo) / max(hi - lo, 1e-9), 0.0, 1.0)

    gx = cv2.Sobel(inv, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(inv, cv2.CV_32F, 0, 1, ksize=3)
    gmag = (np.sqrt(gx * gx + gy * gy) * fg).astype(np.float32)

    nang_sd = np.zeros((H, Wd), np.float32)
    fgf = fg.astype(np.float32)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            ns = np.roll(np.roll(normal, dy, 0), dx, 1)
            fs = np.roll(np.roll(fgf, dy, 0), dx, 1)
            ivs = np.roll(np.roll(inv, dy, 0), dx, 1)
            dot = np.clip((normal * ns).sum(-1), -1.0, 1.0)
            ang = np.nan_to_num(np.arccos(dot).astype(np.float32))
            same = (fs > 0.5) & fg & (np.abs(inv - ivs) < 0.02)
            nang_sd = np.maximum(nang_sd, np.where(same, ang, 0.0))

    ng = np.zeros((H, Wd), np.float32)
    for c in range(3):
        a = cv2.Sobel(normal[..., c], cv2.CV_32F, 1, 0, ksize=3)
        b = cv2.Sobel(normal[..., c], cv2.CV_32F, 0, 1, ksize=3)
        ng += a * a + b * b
    ngrad = (np.sqrt(ng) * fg).astype(np.float32)

    k3 = np.ones((3, 3), np.uint8)
    k5 = np.ones((5, 5), np.uint8)
    return {"normal": normal, "inv": inv, "fg": fg,
            "nang_sd5": cv2.dilate(nang_sd, k5), "gmag3": cv2.dilate(gmag, k3),
            "ngrad": ngrad}


def _samp(field, u, v):
    ui = np.clip(np.round(u).astype(np.int64), 0, Wd - 1)
    vi = np.clip(np.round(v).astype(np.int64), 0, H - 1)
    return field[vi, ui]


# ----------------------------------------------------------------------- aggregation
def _agg(A, vis, how):
    """A[V,M] aggregated over the views where the seed is visible."""
    V, M = A.shape
    n = vis.sum(0)
    idx = np.arange(M)
    out = np.zeros(M, np.float64)
    ok = n > 0
    if how == "mean":
        s = np.where(vis, A, 0.0).sum(0)
        out[ok] = s[ok] / n[ok]
        return out
    S = np.sort(np.where(vis, A.astype(np.float32), np.inf), axis=0)
    if how.startswith("q"):
        q = float(how[1:]) / 100.0
        pos = np.clip(np.ceil(q * (n - 1)).astype(int), 0, V - 1)
        out[ok] = S[pos[ok], idx[ok]]
        return out
    if how == "trim":
        lo = np.clip(np.ceil(0.2 * (n - 1)).astype(int), 0, V - 1)
        hi = np.clip(np.floor(0.8 * (n - 1)).astype(int), 0, V - 1)
        ar = np.arange(V)[:, None]
        m = (ar >= lo[None]) & (ar <= hi[None]) & np.isfinite(S)
        c = m.sum(0)
        out[c > 0] = np.where(m, S, 0.0).sum(0)[c > 0] / c[c > 0]
        return out
    raise ValueError(how)


def _gnorm(s):
    return (rankdata(s) - 0.5) / len(s)


# -------------------------------------------------------------------------- gather
def _gather(h, sel, st, views=DEFAULT_VIEWS):
    """Raw per-view per-seed measurements.  Returns dict of [V,M] plus vis[V,M]."""
    P = h.X[sel]
    E1 = st["e1"][sel]
    M, V = len(sel), len(views)
    keys = ["nang_sd", "dihed", "gmag", "ridge_val"]
    raw = {k: np.zeros((V, M), np.float32) for k in keys}
    vis_all = np.zeros((V, M), bool)

    for vi, v in enumerate(views):
        gb = h.gbufs[v] if getattr(h, "gbufs", None) and v in h.gbufs else \
            render.render_gbuffer(h.g, h.keep, h.cams[v])
        F = _fields(gb)
        cam = h.cams[v]
        vis, uv, z = visibility.visible_mask(P, cam, gb["depth"])
        u0 = uv[:, 0].astype(np.float32)
        v0 = uv[:, 1].astype(np.float32)
        inb = (z > 0) & (u0 >= 0) & (u0 < Wd) & (v0 >= 0) & (v0 < H)
        vis_all[vi] = vis & inb

        # projected across-crease direction (2px probe in world units)
        d = (2.0 * np.abs(z) / cam.f)[:, None]
        pp = (cam.K @ ((cam.w2c[:3, :3] @ (P + d * E1).T).T + cam.w2c[:3, 3]).T).T
        pp = pp[:, :2] / np.clip(pp[:, 2:3], 1e-9, None)
        pm = (cam.K @ ((cam.w2c[:3, :3] @ (P - d * E1).T).T + cam.w2c[:3, 3]).T).T
        pm = pm[:, :2] / np.clip(pm[:, 2:3], 1e-9, None)
        D1 = pp - pm
        D1 /= (np.linalg.norm(D1, axis=1, keepdims=True) + 1e-12)

        t = 2.0
        na = _samp(F["normal"], u0 + t * D1[:, 0], v0 + t * D1[:, 1])
        nb = _samp(F["normal"], u0 - t * D1[:, 0], v0 - t * D1[:, 1])
        fa = _samp(F["fg"].astype(np.float32), u0 + t * D1[:, 0], v0 + t * D1[:, 1])
        fb = _samp(F["fg"].astype(np.float32), u0 - t * D1[:, 0], v0 - t * D1[:, 1])
        ang = np.nan_to_num(np.arccos(np.clip((na * nb).sum(1), -1, 1)))
        raw["dihed"][vi] = np.where((fa > 0.5) & (fb > 0.5), ang, 0.0)

        raw["nang_sd"][vi] = _samp(F["nang_sd5"], u0, v0)
        raw["gmag"][vi] = _samp(F["gmag3"], u0, v0)

        su = (u0[None] + OFFS[:, None] * D1[None, :, 0]).astype(np.float32)
        sv = (v0[None] + OFFS[:, None] * D1[None, :, 1]).astype(np.float32)
        prof = cv2.remap(F["ngrad"], su, sv, cv2.INTER_LINEAR,
                         borderValue=0).reshape(len(OFFS), M)
        raw["ridge_val"][vi] = prof.max(0)

        del gb
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    return raw, vis_all


def _terms(h, sel, st, views=DEFAULT_VIEWS):
    raw, vis = _gather(h, sel, st, views)
    return {
        "crease": _agg(raw["nang_sd"], vis, "q10"),
        "dihed": _agg(raw["dihed"], vis, "trim"),
        "nogmag": -_agg(raw["gmag"], vis, "trim"),
        "ridgeval": _agg(raw["ridge_val"], vis, "trim"),
    }


# --------------------------------------------------------------------------- public
def compute(h, sel, st, views=DEFAULT_VIEWS):
    """returns float np.ndarray [len(sel)], higher = more likely a true crease seed.
    MUST be mesh-free."""
    t = _terms(h, sel, st, views)
    return (1.5 * _gnorm(t["crease"]) + 0.75 * _gnorm(t["dihed"])
            + 1.5 * _gnorm(t["nogmag"]))


def compute_all(h, sel, st, views=DEFAULT_VIEWS):
    """All variants at once (one render pass).  dict name -> score."""
    t = _terms(h, sel, st, views)
    g = {k: _gnorm(v) for k, v in t.items()}
    return {
        "crease": t["crease"],
        "dihed": t["dihed"],
        "nogmag": t["nogmag"],
        "ridgeval": t["ridgeval"],
        "pair": g["nogmag"] + g["ridgeval"],
        "fusion3": 1.5 * g["crease"] + 0.75 * g["dihed"] + 1.5 * g["nogmag"],
        "fusion4": g["crease"] + g["dihed"] + g["nogmag"] + g["ridgeval"],
    }


def compute_crease(h, sel, st, views=DEFAULT_VIEWS):
    return _terms(h, sel, st, views)["crease"]


def compute_dihed(h, sel, st, views=DEFAULT_VIEWS):
    return _terms(h, sel, st, views)["dihed"]


def compute_nogmag(h, sel, st, views=DEFAULT_VIEWS):
    return _terms(h, sel, st, views)["nogmag"]


def compute_ridgeval(h, sel, st, views=DEFAULT_VIEWS):
    return _terms(h, sel, st, views)["ridgeval"]


def compute_pair(h, sel, st, views=DEFAULT_VIEWS):
    t = _terms(h, sel, st, views)
    return _gnorm(t["nogmag"]) + _gnorm(t["ridgeval"])


if __name__ == "__main__":
    import time
    sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
    from tune_lib import Harness, structure_tensor, nms_along_e1
    t0 = time.time()
    h = Harness("chair")
    st = structure_tensor(h.X, h.N, 8)
    cand = np.where(st["s_crease"] > 0.05)[0]
    sel = nms_along_e1(h.X, cand, st["s_crease"], st["e1"], st["knn"])
    s = compute(h, sel, st)
    P = h.X[sel]
    print(f"score: {len(s)} seeds, {time.time()-t0:.1f}s")
    for f in [1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2]:
        keep = np.zeros(len(sel), bool)
        keep[np.argsort(-s)[:int(f * len(sel))]] = True
        p, r, n = h.evaluate(P, extra_mask=keep)
        print(f"  f={f:.1f}  precision={p:.4f}  recall={r:.4f}  n_vis={n}")
