"""gline feature cache v3 — "am I ON the line?" sub-pixel ridge features (MESH-FREE).

  ridge_off_t : |offset| (px) along the projected across-crease direction e1 from the
                seed's projection to the local maximum of ||grad N|| (parabola-refined).
  ridge_val   : the ridge peak value there.
  ridge_dt    : distance transform to the NMS-thinned ||grad N|| ridge.
  gdt         : distance transform to the NMS-thinned inverse-depth-gradient ridge.
"""
import os
import sys
import time
import numpy as np
import cv2
import torch

sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
from tune_lib import Harness, structure_tensor, nms_along_e1  # noqa: E402
from src import render, visibility  # noqa: E402

CACHE = os.path.expanduser("~/3dgs_line/tier1/cache/gline")
H = Wd = 800
OFFS = np.arange(-4.0, 4.01, 0.5)


def nms_thin(f, thr):
    gx = cv2.Sobel(f, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(f, cv2.CV_32F, 0, 1, ksize=3)
    ang = np.arctan2(gy, gx)
    dx = np.cos(ang)
    dy = np.sin(ang)
    yy, xx = np.mgrid[0:H, 0:Wd].astype(np.float32)
    m1 = cv2.remap(f, (xx + dx).astype(np.float32), (yy + dy).astype(np.float32),
                   cv2.INTER_LINEAR, borderValue=0)
    m2 = cv2.remap(f, (xx - dx).astype(np.float32), (yy - dy).astype(np.float32),
                   cv2.INTER_LINEAR, borderValue=0)
    return (f >= m1) & (f >= m2) & (f > thr)


def build(gbuf):
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
    ng = np.zeros((H, Wd), np.float32)
    for c in range(3):
        a = cv2.Sobel(normal[..., c], cv2.CV_32F, 1, 0, ksize=3)
        b = cv2.Sobel(normal[..., c], cv2.CV_32F, 0, 1, ksize=3)
        ng += a * a + b * b
    ngrad = (np.sqrt(ng) * fg).astype(np.float32)
    gx = cv2.Sobel(inv, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(inv, cv2.CV_32F, 0, 1, ksize=3)
    gmag = (np.sqrt(gx * gx + gy * gy) * fg).astype(np.float32)
    thr_n = float(np.percentile(ngrad[fg], 80)) if fg.any() else 0.0
    rmask = nms_thin(ngrad, thr_n) & fg
    ridge_dt = cv2.distanceTransform((~rmask).astype(np.uint8), cv2.DIST_L2, 5)
    thr_d = float(np.percentile(gmag[fg], 90)) if fg.any() else 0.0
    dmask = nms_thin(gmag, thr_d) & fg
    gdt = cv2.distanceTransform((~dmask).astype(np.uint8), cv2.DIST_L2, 5)
    return {"ngrad": ngrad, "ridge_dt": ridge_dt.astype(np.float32),
            "gdt": gdt.astype(np.float32), "fg": fg}


def main(step=8):
    t0 = time.time()
    h = Harness("chair")
    st = structure_tensor(h.X, h.N, 8)
    cand = np.where(st["s_crease"] > 0.05)[0]
    sel = nms_along_e1(h.X, cand, st["s_crease"], st["e1"], st["knn"])
    P, E1 = h.X[sel], st["e1"][sel]
    M = len(sel)
    views = sorted(set(list(range(0, 100, step)) + [25]))
    V = len(views)
    out = {k: np.zeros((V, M), np.float32)
           for k in ["ridge_off", "ridge_val", "ridge_dt", "gdt", "ngrad_at"]}
    vis_all = np.zeros((V, M), bool)

    for vi, v in enumerate(views):
        gb = h.gbufs[v] if v in h.gbufs else render.render_gbuffer(h.g, h.keep, h.cams[v])
        F = build(gb)
        vis, uv, z = visibility.visible_mask(P, h.cams[v], gb["depth"])
        cam = h.cams[v]
        u0, v0 = uv[:, 0].astype(np.float32), uv[:, 1].astype(np.float32)
        inb = (z > 0) & (u0 >= 0) & (u0 < Wd) & (v0 >= 0) & (v0 < H)
        vis_all[vi] = vis & inb
        d = (2.0 * np.abs(z) / cam.f)[:, None]
        uvp = (cam.K @ ((cam.w2c[:3, :3] @ (P + d * E1).T).T + cam.w2c[:3, 3]).T).T
        uvp = uvp[:, :2] / np.clip(uvp[:, 2:3], 1e-9, None)
        uvm = (cam.K @ ((cam.w2c[:3, :3] @ (P - d * E1).T).T + cam.w2c[:3, 3]).T).T
        uvm = uvm[:, :2] / np.clip(uvm[:, 2:3], 1e-9, None)
        D1 = uvp - uvm
        D1 /= (np.linalg.norm(D1, axis=1, keepdims=True) + 1e-12)

        # profile of ||grad N|| along the across-crease direction
        su = (u0[None, :] + OFFS[:, None] * D1[None, :, 0]).astype(np.float32)
        sv = (v0[None, :] + OFFS[:, None] * D1[None, :, 1]).astype(np.float32)
        prof = cv2.remap(F["ngrad"], su, sv, cv2.INTER_LINEAR,
                         borderValue=0).reshape(len(OFFS), M)
        k = prof.argmax(0)
        idx = np.arange(M)
        pk = prof[k, idx]
        km = np.clip(k - 1, 0, len(OFFS) - 1)
        kp = np.clip(k + 1, 0, len(OFFS) - 1)
        a, b, c = prof[km, idx], pk, prof[kp, idx]
        den = (a - 2 * b + c)
        sub = np.where(np.abs(den) > 1e-9, 0.5 * (a - c) / np.where(den == 0, 1, den), 0.0)
        sub = np.clip(sub, -1, 1)
        off = OFFS[k] + sub * 0.5
        out["ridge_off"][vi] = np.abs(off)
        out["ridge_val"][vi] = pk
        ui = np.clip(np.round(u0).astype(int), 0, Wd - 1)
        wi = np.clip(np.round(v0).astype(int), 0, H - 1)
        out["ridge_dt"][vi] = F["ridge_dt"][wi, ui]
        out["gdt"][vi] = F["gdt"][wi, ui]
        out["ngrad_at"][vi] = F["ngrad"][wi, ui]
        del gb
        torch.cuda.empty_cache()
    np.savez(os.path.join(CACHE, f"feat3_chair_s{step}.npz"),
             views=np.array(views), sel=sel, vis=vis_all, **out)
    print(f"[{time.time()-t0:.1f}s] wrote v3 cache")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8)
