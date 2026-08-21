"""tier1/scripts/viz_gated.py — 3-panel {RGB | raw-Canny linelets | geom-gated linelets}
so the effect of the geometry gate on fabric contamination is directly visible.
EVAL-adjacent visualisation only; it loads two finished linelet sets and draws them."""
import argparse
import os
import sys

import cv2
import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
from src import common, render, visibility, linelet, view_split

OUT = os.path.join(TIER1, "out")


def draw(rgb, cam, depth, z, color_by_inlier=True):
    p, t, l = z["p"], z["t"], z["l"]
    keep = z["keep"].astype(bool)
    inl = z["inlier_ratio"]
    img = rgb.copy()
    vis, _, _ = visibility.visible_mask(p, cam, depth)
    sel = np.where(vis & keep)[0]
    a, b = linelet.endpoints(p, t, l)
    uva, _ = common.project(a, cam)
    uvb, _ = common.project(b, cam)
    S = 16
    for i in sel[np.argsort(inl[sel])]:
        c = cv2.applyColorMap(np.uint8([[np.clip(inl[i], 0, 1) * 255]]),
                              cv2.COLORMAP_JET)[0, 0] if color_by_inlier else (0, 0, 255)
        cv2.line(img, (int(np.clip(uva[i, 0], -1e4, 1e4) * S),
                       int(np.clip(uva[i, 1], -1e4, 1e4) * S)),
                 (int(np.clip(uvb[i, 0], -1e4, 1e4) * S),
                  int(np.clip(uvb[i, 1], -1e4, 1e4) * S)),
                 (int(c[0]), int(c[1]), int(c[2])), 1, cv2.LINE_8, 4)
    return img, len(sel)


def panel(img, label):
    o = img.copy()
    cv2.rectangle(o, (0, 0), (o.shape[1] - 1, 26), (0, 0, 0), -1)
    cv2.putText(o, label, (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1,
                cv2.LINE_AA)
    return o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="chair")
    ap.add_argument("--views", type=int, nargs="+", default=None,
                    help="default: first two TEST views")
    args = ap.parse_args()
    views = args.views or view_split.TEST[:2]

    cams, rgb_paths = common.load_cameras(args.scene)
    g = common.load_gaussians(args.scene)
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    zu = np.load(os.path.join(OUT, f"linelets_{args.scene}_ungated_test.npz"))
    zg = np.load(os.path.join(OUT, f"linelets_{args.scene}_gated_test.npz"))

    for v in views:
        cam = cams[v]
        gb = render.render_gbuffer(g, keep_g, cam)
        im = cv2.imread(rgb_paths[v], cv2.IMREAD_UNCHANGED)
        a4 = im[:, :, 3:4].astype(np.float32) / 255.0
        rgb = (im[:, :, :3].astype(np.float32) * a4 + 255.0 * (1 - a4)).astype(np.uint8)
        iu, nu = draw(rgb, cam, gb["depth"], zu)
        ig, ng = draw(rgb, cam, gb["depth"], zg)
        out = cv2.hconcat([panel(rgb, f"RGB  v{v} (TEST split)"),
                           panel(iu, f"raw-Canny DT linelets  n={nu}"),
                           panel(ig, f"GEOM-GATED DT linelets  n={ng}")])
        p = os.path.join(OUT, f"m1b_gated_{args.scene}_v{v}.png")
        cv2.imwrite(p, out)
        print(f"wrote {p}   (ungated {nu} vs gated {ng} drawn linelets)")
        del gb


if __name__ == "__main__":
    main()
