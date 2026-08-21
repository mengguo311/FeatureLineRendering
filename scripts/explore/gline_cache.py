"""Build a per-seed x per-view feature cache for the `gline` family (MESH-FREE features).

Renders G-buffers over a spread of views, computes image-space line evidence fields
(inverse-depth Sobel magnitude, normal Laplacian kappa_N, same-depth normal angle),
samples them at each seed's projection, and stores everything to an npz so the
sweep is cheap.  Nothing here touches the mesh.
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

TAU_D = [0.05, 0.10, 0.20]
TAU_N = [0.5, 1.0, 2.0]
NQ = 101


def fields_from_gbuf(gbuf):
    """All mesh-free image-space line-evidence fields for one G-buffer."""
    depth = gbuf["depth"].detach().cpu().numpy().astype(np.float32)
    normal = gbuf["normal"].detach().cpu().numpy().astype(np.float32)
    alpha = gbuf["alpha"].detach().cpu().numpy().astype(np.float32)

    fg = alpha > 0.5
    inv = np.zeros_like(depth)
    finite = np.isfinite(depth) & (depth > 1e-6)
    inv[finite] = 1.0 / depth[finite]
    if fg.any():
        lo, hi = np.percentile(inv[fg], [1, 99])
        inv = np.clip((inv - lo) / max(hi - lo, 1e-9), 0.0, 1.0)
    gx = cv2.Sobel(inv, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(inv, cv2.CV_32F, 0, 1, ksize=3)
    gmag = np.sqrt(gx * gx + gy * gy)

    lap = np.stack([cv2.Laplacian(normal[..., c], cv2.CV_32F, ksize=3)
                    for c in range(3)], -1)
    kappa = np.linalg.norm(lap, axis=-1).astype(np.float32)

    # --- normal-angle discontinuity, with and without a same-depth gate ---
    # 8-neighbour shifts; a neighbour only counts if it is foreground.
    nang = np.zeros((H, Wd), np.float32)      # max angle to any fg neighbour
    nang_sd = np.zeros((H, Wd), np.float32)   # ... and neighbour on the same surface
    fgf = fg.astype(np.float32)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            ns = np.roll(np.roll(normal, dy, axis=0), dx, axis=1)
            fs = np.roll(np.roll(fgf, dy, axis=0), dx, axis=1)
            invs = np.roll(np.roll(inv, dy, axis=0), dx, axis=1)
            dot = np.clip((normal * ns).sum(-1), -1.0, 1.0)
            ang = np.nan_to_num(np.arccos(dot).astype(np.float32))
            valid = (fs > 0.5) & fg
            nang = np.maximum(nang, np.where(valid, ang, 0.0))
            # same-depth gate: normalized inverse-depth step small => same surface
            sd = valid & (np.abs(inv - invs) < 0.02)
            nang_sd = np.maximum(nang_sd, np.where(sd, ang, 0.0))

    gmag = gmag * fg
    kappa = kappa * fg
    return {"gmag": gmag, "kappa": kappa, "nang": nang, "nang_sd": nang_sd,
            "fg": fg, "inv": inv}


def sample_modes(field, su, sv):
    """nearest, 3x3 max, 5x5 max at integer pixel coords."""
    k3 = cv2.dilate(field, np.ones((3, 3), np.uint8))
    k5 = cv2.dilate(field, np.ones((5, 5), np.uint8))
    return field[sv, su], k3[sv, su], k5[sv, su]


def main(views_step=8, extra_views=(25,)):
    t0 = time.time()
    h = Harness("chair")
    st = structure_tensor(h.X, h.N, 8)
    cand = np.where(st["s_crease"] > 0.05)[0]
    sel = nms_along_e1(h.X, cand, st["s_crease"], st["e1"], st["knn"])
    P = h.X[sel]
    M = len(sel)
    print(f"[{time.time()-t0:.1f}s] harness ready, {M} seeds")

    views = sorted(set(list(range(0, 100, views_step)) + list(extra_views)))
    V = len(views)
    print("views:", views)

    names = ["gmag", "kappa", "nang", "nang_sd"]
    modes = ["p0", "p3", "p5"]
    raw = {f"{n}_{m}": np.zeros((V, M), np.float32) for n in names for m in modes}
    qgrid = {n: np.zeros((V, NQ), np.float32) for n in names}
    vis_all = np.zeros((V, M), bool)
    inb_all = np.zeros((V, M), bool)
    ndt = len(TAU_D) * len(TAU_N)
    linedt = np.zeros((ndt, V, M), np.float32)
    linefrac = np.zeros((ndt, V), np.float32)

    for vi, v in enumerate(views):
        if v in h.gbufs:
            gbuf = h.gbufs[v]
        else:
            gbuf = render.render_gbuffer(h.g, h.keep, h.cams[v])
        F = fields_from_gbuf(gbuf)
        vis, uv, z = visibility.visible_mask(P, h.cams[v], gbuf["depth"])
        u = np.round(uv[:, 0]).astype(np.int64)
        w_ = np.round(uv[:, 1]).astype(np.int64)
        inb = (z > 0) & (u >= 0) & (u < Wd) & (w_ >= 0) & (w_ < H)
        su = np.clip(u, 0, Wd - 1)
        sv = np.clip(w_, 0, H - 1)
        vis_all[vi] = vis
        inb_all[vi] = inb

        fg = F["fg"]
        for n in names:
            f = F[n]
            a, b, c = sample_modes(f, su, sv)
            raw[f"{n}_p0"][vi] = a
            raw[f"{n}_p3"][vi] = b
            raw[f"{n}_p5"][vi] = c
            vals = f[fg] if fg.any() else f.ravel()
            qgrid[n][vi] = np.percentile(vals, np.linspace(0, 100, NQ)).astype(np.float32)

        j = 0
        for td in TAU_D:
            for tn in TAU_N:
                mask = ((F["gmag"] > td) | (F["kappa"] > tn)) & fg
                linefrac[j, vi] = mask.mean()
                dt = cv2.distanceTransform((~mask).astype(np.uint8), cv2.DIST_L2, 5)
                linedt[j, vi] = dt[sv, su]
                j += 1
        del gbuf
        torch.cuda.empty_cache()
        print(f"  [{time.time()-t0:6.1f}s] view {v:3d} vis={vis.sum():6d} "
              f"fg={fg.sum():6d} linefrac={linefrac[0, vi]:.3f}")

    os.makedirs(CACHE, exist_ok=True)
    out = {"views": np.array(views), "sel": sel, "vis": vis_all, "inb": inb_all,
           "linedt": linedt, "linefrac": linefrac,
           "tau_d": np.array(TAU_D), "tau_n": np.array(TAU_N)}
    out.update({f"raw_{k}": v for k, v in raw.items()})
    out.update({f"q_{k}": v for k, v in qgrid.items()})
    np.savez(os.path.join(CACHE, f"feat_chair_s{views_step}.npz"), **out)
    print(f"[{time.time()-t0:.1f}s] wrote cache")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8)
