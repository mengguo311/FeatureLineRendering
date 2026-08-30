"""TRACK C viz — {RGB | Canny linelets | TEED linelets} on held-out TEST views.

*** EVAL-ONLY (loads tune_lib.Harness for the cameras/G-buffers + the GT crease overlay). ***

The point of the panel is to SEE the recovered subtle creases, so the fourth panel colours
the drawn linelets by whether they land on a GT crease pixel that the Canny arm's linelets
MISSED -- i.e. the recall the learned detector actually bought, rather than a generic
"more lines" impression that thicker drawing would also produce.
"""
import os
import sys
import argparse

import cv2
import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))

from src import common, render, visibility, linelet, view_split
from src.mesh_oracle import MeshOracle          # EVAL ONLY — the GT overlay

OUT = os.path.join(TIER1, "out")
S = 16          # cv2 line shift


def load_rgb_white(p):
    im = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    if im.ndim == 3 and im.shape[2] == 4:
        a = im[:, :, 3:4].astype(np.float32) / 255.0
        return (im[:, :, :3].astype(np.float32) * a + 255.0 * (1 - a)).astype(np.uint8)
    return im[:, :, :3]


def panel(img, text):
    o = img.copy()
    cv2.rectangle(o, (0, 0), (o.shape[1], 34), (255, 255, 255), -1)
    cv2.putText(o, text, (8, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 0, 0), 2)
    return cv2.copyMakeBorder(o, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=(40, 40, 40))


def draw_mask(z, cam, depth, H, W):
    """Rasterise an arm's kept, visible linelets into a binary image mask."""
    p, t, l, keep = z["p"], z["t"], z["l"], z["keep"]
    vis, _, _ = visibility.visible_mask(p, cam, depth)
    sel = np.where(vis & keep)[0]
    a, b = linelet.endpoints(p, t, l)
    uva, _ = common.project(a, cam)
    uvb, _ = common.project(b, cam)
    m = np.zeros((H, W), np.uint8)
    for i in sel:
        cv2.line(m, (int(np.clip(uva[i, 0], -1e4, 1e4) * S), int(np.clip(uva[i, 1], -1e4, 1e4) * S)),
                 (int(np.clip(uvb[i, 0], -1e4, 1e4) * S), int(np.clip(uvb[i, 1], -1e4, 1e4) * S)),
                 255, 1, cv2.LINE_8, 4)
    return m > 0, len(sel)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="chair")
    ap.add_argument("--canny", required=True)
    ap.add_argument("--teed", required=True)
    ap.add_argument("--views", type=int, nargs="*", default=[5, 25])
    ap.add_argument("--tau", type=float, default=2.0)
    ap.add_argument("--out_prefix", default="teed_chair")
    args = ap.parse_args()

    cams, rgb_paths = common.load_cameras(args.scene)
    g = common.load_gaussians(args.scene)
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    zc = np.load(os.path.join(OUT, args.canny))
    zt = np.load(os.path.join(OUT, args.teed))
    oracle = MeshOracle(args.scene)

    for v in args.views:
        cam = cams[v]
        H, W = cam.H, cam.W
        gb = render.render_gbuffer(g, keep_g, cam)
        rgb = load_rgb_white(rgb_paths[v])
        mc, nc = draw_mask(zc, cam, gb["depth"], H, W)
        mt, nt = draw_mask(zt, cam, gb["depth"], H, W)

        # GT creases, and which of them each arm covers
        uv = oracle.visible_crease_uv(cam, view_key=int(v))
        gt = np.zeros((H, W), bool)
        if len(uv):
            u = np.round(uv[:, 0]).astype(np.int64)
            w = np.round(uv[:, 1]).astype(np.int64)
            ok = (u >= 0) & (u < W) & (w >= 0) & (w < H)
            gt[w[ok], u[ok]] = True

        def cov(m):
            d = cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5)
            return d <= args.tau
        cc, ct = cov(mc), cov(mt)
        r_c = float((gt & cc).sum()) / max(int(gt.sum()), 1)
        r_t = float((gt & ct).sum()) / max(int(gt.sum()), 1)

        pc = rgb.copy(); pc[mc] = (0, 0, 220)
        pt = rgb.copy(); pt[mt] = (0, 0, 220)

        # The money panel. Only GT CREASE pixels are painted -- overlaying the linelets as
        # well drowns the signal, since both arms draw over most of the object.
        #   grey  = GT crease both arms already covered
        #   GREEN = GT crease ONLY the TEED arm covers  <- the recall this bought
        #   red   = GT crease still missed by both      <- the residual ceiling
        faint = cv2.addWeighted(rgb, 0.35, np.full_like(rgb, 255), 0.65, 0)
        gain = faint.copy()
        def stamp(mask, col):
            yy, xx = np.nonzero(mask)
            for y, x in zip(yy, xx):
                cv2.circle(gain, (int(x), int(y)), 1, col, -1)
        stamp(gt & cc, (170, 170, 170))
        stamp(gt & ~cc & ~ct, (0, 0, 255))
        stamp(gt & ct & ~cc, (0, 200, 0))

        # crop every panel to the object bbox so the detail is actually visible
        ys, xs = np.nonzero(cv2.dilate((gt | mc | mt).astype(np.uint8),
                                       np.ones((3, 3), np.uint8)))
        if len(ys):
            y0, y1 = max(int(ys.min()) - 12, 0), min(int(ys.max()) + 12, H)
            x0, x1 = max(int(xs.min()) - 12, 0), min(int(xs.max()) + 12, W)
        else:
            y0, y1, x0, x1 = 0, H, 0, W
        crop = lambda a: a[y0:y1, x0:x1]

        img = cv2.hconcat([
            panel(crop(rgb), f"RGB  TEST v{v}"),
            panel(crop(pc), f"CANNY linelets  n={nc}  GTcov={r_c:.3f}"),
            panel(crop(pt), f"TEED linelets  n={nt}  GTcov={r_t:.3f}"),
            panel(crop(gain), f"GREEN=recovered by TEED ({r_t-r_c:+.3f})  "
                              f"red=missed by both  grey=already covered"),
        ])
        p = os.path.join(OUT, f"{args.out_prefix}_v{v}.png")
        cv2.imwrite(p, img)
        print(f"v{v}: canny n={nc} GTcov={r_c:.4f} | teed n={nt} GTcov={r_t:.4f} "
              f"(dGTcov {r_t-r_c:+.4f}) -> {p}", flush=True)


if __name__ == "__main__":
    main()
