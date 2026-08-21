"""tier1/scripts/m1b_make_video.py — side-by-side temporal-coherence VIDEO deliverable.

OURS (left)     static 3D polyline strokes, projected per frame.
BASELINE (right) per-frame image-space Canny, re-traced from scratch every frame.

Same camera trajectory, same frame index, same line width, white background, black
strokes. No metric is computed here — this only renders what the STEP-06 table already
measured, reusing scripts/m1b_stroke_temporal.py for both stroke sources and
src/strokes.py for rasterisation. Chaining is untouched.

MESH-NEVER-IN-METHOD: nothing in this file (or anything it imports for the render path)
touches the GT mesh.
"""
import argparse
import os
import sys

import cv2
import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))

from src import common, render, strokes
import m1b_stroke_temporal as M
import temporal_m1b as TT
from temporal_m1b import orbit_cameras

OUT = os.path.join(TIER1, "out")
HEADER = 48
FONT = cv2.FONT_HERSHEY_SIMPLEX


def panel(poly, H, W, thickness):
    m = strokes.raster_polylines(poly, H, W, thickness=thickness)
    img = np.full((H, W, 3), 255, np.uint8)
    img[m] = (0, 0, 0)
    return img


def compose(A, B, scene, i, n, nA, nB, thickness):
    H, W = A.shape[:2]
    canvas = np.full((H + HEADER, 2 * W + 2, 3), 255, np.uint8)
    canvas[HEADER:, :W] = A
    canvas[HEADER:, W + 2:] = B
    canvas[HEADER:, W:W + 2] = (170, 170, 170)          # divider
    cv2.rectangle(canvas, (0, 0), (2 * W + 2, HEADER - 1), (28, 28, 28), -1)
    cv2.putText(canvas, "OURS - object-space carrier (static 3D strokes)",
                (12, 30), FONT, 0.62, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(canvas, "BASELINE - per-frame image-space Canny re-trace",
                (W + 14, 30), FONT, 0.62, (255, 255, 255), 1, cv2.LINE_AA)
    lab = f"{scene}   frame {i+1:3d}/{n}"
    (tw, _), _ = cv2.getTextSize(lab, FONT, 0.62, 1)
    cv2.putText(canvas, lab, (2 * W + 2 - tw - 14, 30), FONT, 0.62,
                (120, 220, 255), 1, cv2.LINE_AA)
    for x0, nn in ((0, nA), (W + 2, nB)):
        cv2.putText(canvas, f"{nn} strokes", (x0 + 12, HEADER + H - 14), FONT, 0.55,
                    (90, 90, 90), 1, cv2.LINE_AA)
    return canvas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", nargs="+", default=["chair", "lego"])
    ap.add_argument("--frames", type=int, default=240)
    ap.add_argument("--view_a", type=int, default=5)
    ap.add_argument("--view_b", type=int, default=15)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--thickness", type=int, default=2)
    ap.add_argument("--variant", default="ungated")
    ap.add_argument("--gif", action="store_true")
    ap.add_argument("--raw_path", action="store_true",
                    help="use the uncorrected interp_cameras path (the one the STEP-06 "
                         "table was measured on); default is the look-at-corrected orbit")
    ap.add_argument("--gif_stride", type=int, default=3)
    ap.add_argument("--gif_scale", type=float, default=0.40)
    # chaining / baseline params: identical to the STEP-06 table defaults
    ap.add_argument("--nms_mult", type=float, default=1.0)
    ap.add_argument("--knn", type=int, default=10)
    ap.add_argument("--cos_tan", type=float, default=0.60)
    ap.add_argument("--cos_col", type=float, default=0.50)
    ap.add_argument("--gap_mult", type=float, default=4.0)
    ap.add_argument("--min_nodes", type=int, default=3)
    ap.add_argument("--canny_lo", type=int, default=50)
    ap.add_argument("--canny_hi", type=int, default=150)
    ap.add_argument("--min_len", type=int, default=4)
    ap.add_argument("--approx_eps", type=float, default=1.0)
    ap.add_argument("--fg_only", action="store_true")
    ap.add_argument("--fg_erode", type=int, default=2)
    ap.add_argument("--carrier_persistence", action="store_true")
    ap.add_argument("--cp_ratio", type=float, default=0.8)
    ap.add_argument("--cp_views", type=int, default=20)
    args = ap.parse_args()

    import imageio.v2 as imageio
    for scene in args.scenes:
        cams, _ = common.load_cameras(scene)
        g = common.load_gaussians(scene)
        keep_g = render.defloat_mask(g["mu"], g["opacity"])
        chain3d, cinfo = M.build_chains(scene, args.variant, args)
        target = np.median(g["mu"][keep_g], axis=0)          # mesh-free scene centre
        if args.raw_path:
            path = TT.interp_cameras(cams[args.view_a], cams[args.view_b], args.frames)
        else:
            path = orbit_cameras(cams[args.view_a], cams[args.view_b], args.frames,
                                 target)
        print(f"  [{scene}] trajectory: "
              f"{'raw interp_cameras (metric path)' if args.raw_path else 'look-at-corrected orbit'}"
              f" about {np.round(target, 3)}", flush=True)
        mp4 = os.path.join(OUT, f"m1b_temporal_sidebyside_{scene}.mp4")
        w = imageio.get_writer(mp4, fps=args.fps, codec="libx264", quality=9,
                               macro_block_size=1)
        gif_frames = []
        nA_t = nB_t = 0
        for i, cam in enumerate(path):
            fr = M.frame_data(g, keep_g, cam, chain3d, args)
            H, W = fr["depth"].shape
            A = panel(fr["A"], H, W, args.thickness)
            B = panel(fr["B"], H, W, args.thickness)
            nA_t += len(fr["A"])
            nB_t += len(fr["B"])
            cv_img = compose(A, B, scene, i, args.frames, len(fr["A"]), len(fr["B"]),
                             args.thickness)
            w.append_data(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))
            if args.gif and i % args.gif_stride == 0:
                small = cv2.resize(cv_img, None, fx=args.gif_scale, fy=args.gif_scale,
                                   interpolation=cv2.INTER_AREA)
                gif_frames.append(cv2.cvtColor(small, cv2.COLOR_BGR2RGB))
            if i % 40 == 0:
                print(f"  [{scene}] frame {i}/{args.frames} "
                      f"(OURS {len(fr['A'])} / BASE {len(fr['B'])} strokes)", flush=True)
        w.close()
        print(f"  wrote {mp4}  ({os.path.getsize(mp4)/1e6:.1f} MB, {args.frames} frames "
              f"@{args.fps}fps, mean strokes OURS {nA_t/args.frames:.0f} / "
              f"BASE {nB_t/args.frames:.0f})", flush=True)
        if args.gif and gif_frames:
            gif = os.path.join(OUT, f"m1b_temporal_sidebyside_{scene}.gif")
            imageio.mimsave(gif, gif_frames,
                            duration=args.gif_stride / float(args.fps), loop=0)
            print(f"  wrote {gif}  ({os.path.getsize(gif)/1e6:.1f} MB, "
                  f"{len(gif_frames)} frames)", flush=True)


if __name__ == "__main__":
    main()
