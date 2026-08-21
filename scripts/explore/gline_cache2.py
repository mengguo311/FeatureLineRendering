"""gline feature cache v2 — geometry-aware image-space line agreement (MESH-FREE).

Adds, per view and per seed:
  * dihed_t   : angle between the mean rendered normal on the two sides of the seed,
                sampled +-t px along the PROJECTED across-crease direction e1.
  * dstep_t   : |normalized inverse-depth| difference across the same two sides
                (large => the "crease" is really an occlusion/silhouette step).
  * talign    : |cos| between the projected crease tangent e3 and the local ridge
                orientation of the normal-discontinuity field (structure tensor).
  * coh       : ridge coherence (l1-l2)/(l1+l2) of that structure tensor.
  * ngrad     : ||grad N|| (first-order normal gradient magnitude).
  * carea     : connected-component area of the line mask at the projection
                (speckle rejection).
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
TS = [2.0, 3.0, 5.0]


def build_fields(gbuf):
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
    gmag = np.sqrt(gx * gx + gy * gy) * fg

    lap = np.stack([cv2.Laplacian(normal[..., c], cv2.CV_32F, ksize=3)
                    for c in range(3)], -1)
    kappa = (np.linalg.norm(lap, axis=-1) * fg).astype(np.float32)

    ng = np.zeros((H, Wd), np.float32)
    for c in range(3):
        a = cv2.Sobel(normal[..., c], cv2.CV_32F, 1, 0, ksize=3)
        b = cv2.Sobel(normal[..., c], cv2.CV_32F, 0, 1, ksize=3)
        ng += a * a + b * b
    ngrad = (np.sqrt(ng) * fg).astype(np.float32)

    # ridge orientation / coherence of the normal-discontinuity field
    rx = cv2.Sobel(ngrad, cv2.CV_32F, 1, 0, ksize=3)
    ry = cv2.Sobel(ngrad, cv2.CV_32F, 0, 1, ksize=3)
    Jxx = cv2.GaussianBlur(rx * rx, (0, 0), 2.0)
    Jyy = cv2.GaussianBlur(ry * ry, (0, 0), 2.0)
    Jxy = cv2.GaussianBlur(rx * ry, (0, 0), 2.0)
    tr = Jxx + Jyy
    dsc = np.sqrt(np.maximum((Jxx - Jyy) ** 2 + 4 * Jxy ** 2, 0))
    l1 = 0.5 * (tr + dsc)
    l2 = 0.5 * (tr - dsc)
    coh = (dsc / np.maximum(tr, 1e-12)).astype(np.float32)
    # principal gradient direction = eigvec of l1; ridge runs perpendicular to it
    theta_g = 0.5 * np.arctan2(2 * Jxy, Jxx - Jyy)      # direction of max gradient
    ridge_th = (theta_g + np.pi / 2).astype(np.float32)  # ridge tangent angle

    mask = ((gmag > 0.10) | (kappa > 1.0)) & fg
    ncc, lab, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    areas = stats[:, cv2.CC_STAT_AREA].astype(np.float32)
    areas[0] = 0.0
    carea = areas[lab]
    carea5 = cv2.dilate(carea, np.ones((5, 5), np.uint8))

    return {"normal": normal, "inv": inv, "fg": fg, "gmag": gmag, "kappa": kappa,
            "ngrad": ngrad, "coh": coh, "ridge_th": ridge_th, "carea5": carea5,
            "l1": l1.astype(np.float32), "l2": l2.astype(np.float32)}


def samp(field, u, v):
    ui = np.clip(np.round(u).astype(np.int64), 0, Wd - 1)
    vi = np.clip(np.round(v).astype(np.int64), 0, H - 1)
    return field[vi, ui]


def main(step=8):
    t0 = time.time()
    h = Harness("chair")
    st = structure_tensor(h.X, h.N, 8)
    cand = np.where(st["s_crease"] > 0.05)[0]
    sel = nms_along_e1(h.X, cand, st["s_crease"], st["e1"], st["knn"])
    P = h.X[sel]
    E1 = st["e1"][sel]
    E3 = st["e3"][sel]
    M = len(sel)
    views = sorted(set(list(range(0, 100, step)) + [25]))
    V = len(views)
    print(f"[{time.time()-t0:.1f}s] {M} seeds, {V} views")

    out = {k: np.zeros((V, M), np.float32) for k in
           ["talign", "coh", "ngrad0", "ngrad3", "carea", "gmag0", "kappa3", "fgfrac"]}
    for t in TS:
        out[f"dihed{int(t)}"] = np.zeros((V, M), np.float32)
        out[f"dstep{int(t)}"] = np.zeros((V, M), np.float32)
    vis_all = np.zeros((V, M), bool)

    for vi, v in enumerate(views):
        gb = h.gbufs[v] if v in h.gbufs else render.render_gbuffer(h.g, h.keep, h.cams[v])
        F = build_fields(gb)
        vis, uv, z = visibility.visible_mask(P, h.cams[v], gb["depth"])
        cam = h.cams[v]
        u0, v0 = uv[:, 0], uv[:, 1]
        inb = (z > 0) & (u0 >= 0) & (u0 < Wd) & (v0 >= 0) & (v0 < H)
        vis_all[vi] = vis & inb

        # projected directions of e1 (across crease) and e3 (along crease), ~2px probe
        d = (2.0 * np.abs(z) / cam.f)[:, None]
        for E, key in ((E1, "e1"), (E3, "e3")):
            uvp = (cam.K @ ((cam.w2c[:3, :3] @ (P + d * E).T).T + cam.w2c[:3, 3]).T).T
            uvp = uvp[:, :2] / np.clip(uvp[:, 2:3], 1e-9, None)
            uvm = (cam.K @ ((cam.w2c[:3, :3] @ (P - d * E).T).T + cam.w2c[:3, 3]).T).T
            uvm = uvm[:, :2] / np.clip(uvm[:, 2:3], 1e-9, None)
            dd = uvp - uvm
            nrm = np.linalg.norm(dd, axis=1, keepdims=True) + 1e-12
            if key == "e1":
                D1 = dd / nrm
            else:
                D3 = dd / nrm

        # dihedral across the projected e1 direction
        for t in TS:
            up, vp = u0 + t * D1[:, 0], v0 + t * D1[:, 1]
            um, vm = u0 - t * D1[:, 0], v0 - t * D1[:, 1]
            na = samp(F["normal"], up, vp)
            nb = samp(F["normal"], um, vm)
            fa = samp(F["fg"].astype(np.float32), up, vp)
            fb = samp(F["fg"].astype(np.float32), um, vm)
            dot = np.clip((na * nb).sum(1), -1, 1)
            ang = np.nan_to_num(np.arccos(dot))
            ok = (fa > 0.5) & (fb > 0.5)
            out[f"dihed{int(t)}"][vi] = np.where(ok, ang, 0.0)
            out[f"dstep{int(t)}"][vi] = np.abs(samp(F["inv"], up, vp) - samp(F["inv"], um, vm))

        th = samp(F["ridge_th"], u0, v0)
        phi = np.arctan2(D3[:, 1], D3[:, 0])
        out["talign"][vi] = np.abs(np.cos(th - phi))
        out["coh"][vi] = samp(F["coh"], u0, v0)
        out["ngrad0"][vi] = samp(F["ngrad"], u0, v0)
        out["ngrad3"][vi] = samp(cv2.dilate(F["ngrad"], np.ones((3, 3), np.uint8)), u0, v0)
        out["carea"][vi] = samp(F["carea5"], u0, v0)
        out["gmag0"][vi] = samp(cv2.dilate(F["gmag"], np.ones((3, 3), np.uint8)), u0, v0)
        out["kappa3"][vi] = samp(cv2.dilate(F["kappa"], np.ones((3, 3), np.uint8)), u0, v0)
        out["fgfrac"][vi] = samp(cv2.blur(F["fg"].astype(np.float32), (7, 7)), u0, v0)
        del gb
        torch.cuda.empty_cache()
        print(f"  [{time.time()-t0:5.1f}s] v{v:3d} vis={vis_all[vi].sum()}")

    os.makedirs(CACHE, exist_ok=True)
    np.savez(os.path.join(CACHE, f"feat2_chair_s{step}.npz"),
             views=np.array(views), sel=sel, vis=vis_all, **out)
    print(f"[{time.time()-t0:.1f}s] wrote v2 cache")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8)
