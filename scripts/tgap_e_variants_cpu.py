"""tier1/scripts/tgap_e_variants_cpu.py — CPU twin of scripts/tgap_e_variants.py.

*** METHOD PATH.  Mesh-free.  No GPU. ***

Identical maths to the GPU version (same projection, same bilinear sample, same visibility
mask reused from the dump); it exists only so the robustness sweep can run while the temporal
gate is occupying the GPU.  A cross-check against the frozen E stored by tgap_pull.py is
printed for every f: if the CPU path did not reproduce the GPU path's mean@0.5 to ~1e-3 the
variants below would not be comparable with it.
"""
import argparse
import os
import sys

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))

from src import common, view_split, tgap_gate                            # noqa: E402

OUT = os.path.join(TIER1, "out")
VARIANTS = ["mean@0.5", "max@0.5", "mean@0.8", "frac@0.5"]


def bilinear(img, uv):
    H, W = img.shape
    x = np.clip(uv[:, 0], 0, W - 1)
    y = np.clip(uv[:, 1], 0, H - 1)
    x0 = np.floor(x).astype(np.int64)
    y0 = np.floor(y).astype(np.int64)
    x1 = np.minimum(x0 + 1, W - 1)
    y1 = np.minimum(y0 + 1, H - 1)
    ax, ay = x - x0, y - y0
    return ((img[y0, x0] * (1 - ax) + img[y0, x1] * ax) * (1 - ay) +
            (img[y1, x0] * (1 - ax) + img[y1, x1] * ax) * ay)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="lego")
    ap.add_argument("--f", type=float, nargs="+", required=True)
    args = ap.parse_args()
    cams, _ = common.load_cameras(args.scene)
    views = list(view_split.TRAIN)

    maps = {}
    for name in VARIANTS:
        kind, thr = name.split("@")
        E = tgap_gate.teed_edge_maps(args.scene, views, thr=float(thr)).astype(np.float32)
        maps[name] = (E > 0).astype(np.float32) if kind == "frac" else E

    for f in args.f:
        src = os.path.join(OUT, f"tgap_pull_{args.scene}_f{f:.2f}.npz")
        z = dict(np.load(src))
        P, vis = z["p"], z["vis"].astype(bool)
        acc = {n: (np.zeros(len(P)) if n.split("@")[0] != "max" else np.zeros(len(P)))
               for n in VARIANTS}
        den = np.zeros(len(P))
        for k, v in enumerate(views):
            uv, _ = common.project(P, cams[v])
            m = vis[k]
            den += m
            for n in VARIANTS:
                s = bilinear(maps[n][k], uv) * m
                if n.split("@")[0] == "max":
                    acc[n] = np.maximum(acc[n], s)
                else:
                    acc[n] += s
        for n in VARIANTS:
            v = acc[n] if n.split("@")[0] == "max" else acc[n] / np.maximum(den, 1.0)
            v = np.where(den > 0, v, 0.0).clip(0.0, 1.0)
            z["E_" + n.replace("@", "_").replace(".", "p")] = v
        d = float(np.abs(z["E_mean_0p5"] - z["E"]).max())
        print(f"  f={f:.2f}  CPU-vs-GPU max|dE| on the frozen mean@0.5 = {d:.2e}"
              f"   (mean {z['E'].mean():.4f})")
        for n in VARIANTS:
            k = "E_" + n.replace("@", "_").replace(".", "p")
            print(f"     {n:9s} mean {z[k].mean():.4f}  frac>0 {(z[k] > 0).mean():.4f}  "
                  f"q90 {np.quantile(z[k], .9):.4f}")
        np.savez(src, **z)
        print(f"  updated {src}", flush=True)


if __name__ == "__main__":
    main()
