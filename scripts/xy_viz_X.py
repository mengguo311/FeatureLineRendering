"""EXPERIMENT X viz — where the frozen pipeline's misses actually are, on lego.

*** EVAL / ANALYSIS ONLY. ***
The spec asks for "missed creases coloured geometric-vs-decal".  That colouring cannot be
drawn, because it does not exist: the GT crease set is DEFINED as dihedral>=30deg edges, so
100% of the miss-set is "geometric" and 0% is "decal" by construction (g_literal = 1.000).
What CAN be drawn, and is what the decision actually turns on, is where the misses sit in the
dihedral spectrum -- in particular the huge spike at EXACTLY 30.0 deg, which is where a
12-sided tessellation of a round lego stud lands precisely on the oracle's threshold.
"""
import argparse
import json
import os
import sys

import cv2
import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
OUT = os.path.join(TIER1, "out", "xy")
CGLIB = os.path.expanduser("~/cglib")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="lego")
    ap.add_argument("--tag", default="_p1c")
    ap.add_argument("--views", default="5,25")
    ap.add_argument("--rad", type=int, default=1)
    args = ap.parse_args()
    z = np.load(os.path.join(OUT, f"xy_expX_{args.scene}{args.tag}.npz"))
    seen_idx, rec3, th = z["seen_idx"], z["rec3"], z["theta0_pt"]
    gt = np.load(os.path.join(TIER1, "cache", f"dexp0_gt_{args.scene}_a30.npz"))
    pos = -np.ones(int(gt["crease_pts"].shape[0]), np.int64)
    pos[seen_idx] = np.arange(len(seen_idx))
    # BGR
    COL = {"hit": (90, 200, 90), "miss30": (60, 60, 255), "miss_other": (0, 165, 255)}
    for v in [int(x) for x in args.views.split(",")]:
        im = cv2.imread(f"{CGLIB}/data/full/{args.scene}/train/r_{v}.png", cv2.IMREAD_UNCHANGED)
        rgb = im[..., :3].astype(np.float32) / 255.0
        a = im[..., 3:4].astype(np.float32) / 255.0
        base = (rgb * a + 1.0 * (1 - a))
        canvas = (base * 0.45 + 0.55).clip(0, 1)          # faded plate so dots read clearly
        canvas = (canvas * 255).astype(np.uint8)
        idx, uv = gt[f"idx{v}"], gt[f"uv{v}"]
        p = pos[idx]
        ok = p >= 0
        idx, uv, p = idx[ok], uv[ok], p[ok]
        r, t = rec3[p], th[p]
        cls = np.where(r, 0, np.where((t >= 29.9) & (t < 30.1), 1, 2))
        u = np.clip(np.round(uv[:, 0]).astype(int), 0, 799)
        w = np.clip(np.round(uv[:, 1]).astype(int), 0, 799)
        lay = canvas.copy()
        for c, key in ((2, "miss_other"), (1, "miss30"), (0, "hit")):
            m = cls == c
            for du in range(-args.rad, args.rad + 1):
                for dv in range(-args.rad, args.rad + 1):
                    lay[np.clip(w[m] + dv, 0, 799), np.clip(u[m] + du, 0, 799)] = COL[key]
        n = len(cls)
        txt = [f"{args.scene} view {v}   GT crease px: {n}",
               f"GREEN  recovered by frozen pipeline : {int((cls==0).sum())} ({(cls==0).mean()*100:.1f}%)",
               f"RED    MISSED, dihedral EXACTLY 30.0 deg : {int((cls==1).sum())} ({(cls==1).mean()*100:.1f}%)",
               f"ORANGE MISSED, other dihedral : {int((cls==2).sum())} ({(cls==2).mean()*100:.1f}%)",
               "NOTE: 0% of the miss-set is a 'decal' -- the GT crease set is dihedral>=30 by construction."]
        pad = np.full((22 * len(txt) + 14, 800, 3), 255, np.uint8)
        for i, s in enumerate(txt):
            cv2.putText(pad, s, (8, 20 + 22 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.46,
                        (0, 0, 0) if i == 0 else
                        (0, 130, 0) if i == 1 else (0, 0, 200) if i == 2 else
                        (0, 120, 200) if i == 3 else (90, 90, 90), 1, cv2.LINE_AA)
        out = np.vstack([np.hstack([canvas, lay]), np.hstack([pad, pad])])
        p_out = os.path.join(OUT, f"xy_X_missmap_{args.scene}_v{v}.png")
        cv2.imwrite(p_out, out)
        print(f"wrote {p_out}  hit={(cls==0).mean():.3f} miss30={(cls==1).mean():.3f} "
              f"miss_other={(cls==2).mean():.3f}")


if __name__ == "__main__":
    main()
