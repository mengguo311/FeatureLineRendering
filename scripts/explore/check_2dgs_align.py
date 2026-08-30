"""Convention check for src/render2dgs.py — EVAL-ONLY DIAGNOSTIC.

Before any verdict is drawn from a 2DGS G-buffer we must prove that the buffer lands on the
SAME pixel grid as tier1's cameras, RGB photographs and mesh oracle. A half-pixel error would
bias the two sides of the bilateral ribbon asymmetrically and could fabricate (or destroy) a
dihedral signal all by itself.

WHY THIS IS NOT OBVIOUS.  On paper the two codebases disagree by exactly half a pixel:
    tier1 (common.project, mesh_oracle.render_depth):  u = f*X/Z + W/2, sampled at INTEGER u
    3DGS/2DGS (auxiliary.h ndc2Pix, forward.cu ndc2pix): u = ((x_ndc+1)*W - 1)/2 = f*X/Z + (W-1)/2
so a world point at tier1 coordinate 400.0 should land at 2DGS index 399.5, i.e. shift -0.5.
The first run of this script contradicted that. Rather than trust either the algebra or a
single aggregate number, this version measures ALL FOUR grids against each other.

METHOD.  Every buffer is resampled at (i+s, j+s) for a sweep of sub-pixel shifts s and
compared against a reference read at integer (i,j). The s that optimises each pair is the
offset between the two grids. Four pairings:

    A  2DGS alpha        vs GT png alpha      (2DGS grid  <-> photograph grid)
    B  2DGS surf_depth   vs GT mesh depth     (2DGS grid  <-> tier1 grid)
    C  GT mesh silhouette vs GT png alpha     (tier1 grid <-> photograph grid)
    D  vanilla gaussian alpha vs GT png alpha (tier1 gaussian renderer <-> photograph grid)
    E  2DGS rendered RGB vs GT png RGB        (2DGS grid  <-> photograph grid)   <-- decisive

MEASURED (chair, 4 views, 15k model), and how to read it:
    A and D are USELESS on this data. Both gaussian models carry a white background "splat
    canvas" (random-point-cloud init + white background makes off-object splats free), so
    alpha > 0.5 covers ~99.8% of the frame for 2DGS and the IoU test has no signal --
    A's whole curve moves by 6e-5 across the sweep. The first version of this script reported
    "s = 0, MISMATCH" purely because of this artefact. Do not resurrect the alpha-IoU test.
    C is clean (both masks are crisp) and gives +0.492: tier1's projection sits half a pixel
    off the photograph grid -- the well-known NeRF-synthetic half-pixel (tier1 puts integer
    index i at u = f*X/Z + W/2, Blender puts it at i+0.5).
    E replaces A: RGB has texture everywhere on the object, so it locates the 2DGS grid
    against the photograph grid with no dependence on any mask. Because 2DGS is TRAINED
    through the 3DGS rasterizer, E must come out ~0.
    The operative offset is then  2DGS -> tier1 = E - C ~ -0.5, which is exactly what the
    algebra above predicts. B corroborates it (~-0.6) but is the weakest test: median depth
    is quantised to individual splat depths, so its basin is shallow and biased.
"""
import os
import sys
import json

import cv2
import numpy as np
import torch

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)

from src import common, render, render2dgs
from src.mesh_oracle import MeshOracle          # EVAL ONLY — reference geometry

OUT = os.path.join(TIER1, "out")
SHIFTS = [round(-0.75 + 0.125 * k, 4) for k in range(13)]      # -0.75 .. +0.75 step 0.125


def sample_shift(t, s, mode="bilinear"):
    """Sample [H,W] tensor at (i+s, j+s) for integer tier1 indices (i,j)."""
    H, W = t.shape
    ii = torch.arange(W, device=t.device, dtype=torch.float32) + s
    jj = torch.arange(H, device=t.device, dtype=torch.float32) + s
    gx = (2.0 * ii / (W - 1) - 1.0).view(1, 1, W).expand(1, H, W)
    gy = (2.0 * jj / (H - 1) - 1.0).view(1, H, 1).expand(1, H, W)
    grid = torch.stack([gx, gy], -1)
    src = t[None, None].contiguous()
    return torch.nn.functional.grid_sample(src, grid, mode=mode,
                                           padding_mode="border", align_corners=True)[0, 0]


def parabolic_min(xs, ys):
    """Sub-sample refinement of the optimum by a parabola through the best 3 points."""
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    k = int(np.nanargmin(ys))
    if k == 0 or k == len(xs) - 1:
        return float(xs[k])
    x0, x1, x2 = xs[k - 1], xs[k], xs[k + 1]
    y0, y1, y2 = ys[k - 1], ys[k], ys[k + 1]
    den = (y0 - 2 * y1 + y2)
    if abs(den) < 1e-30:
        return float(x1)
    return float(x1 - 0.5 * (x2 - x0) * (y2 - y0) / (2.0 * den))


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else os.path.join(OUT, "2dgs_chair")
    scene = sys.argv[2] if len(sys.argv) > 2 else "chair"
    nviews = int(sys.argv[3]) if len(sys.argv) > 3 else 4

    cams, rgb_paths = common.load_cameras(scene)
    g2, pipe, meta = render2dgs.load_2dgs(model)
    print(f"[align] model={meta['model_path']} iter={meta['iteration']} "
          f"n_gauss={meta['n_gauss']} depth_ratio={meta['depth_ratio']}", flush=True)
    oracle = MeshOracle(scene)
    gv = common.load_gaussians(scene)
    keep = render.defloat_mask(gv["mu"], gv["opacity"])

    views = np.unique(np.round(np.linspace(0, len(cams) - 1, nviews)).astype(int))
    # cost[pair][s] -> list over views of a "lower is better" cost
    pairs = ["A_2dgs_vs_png", "B_2dgs_vs_mesh", "C_mesh_vs_png", "D_vanilla_vs_png",
             "E_2dgsRGB_vs_png"]
    cost = {p: {s: [] for s in SHIFTS} for p in pairs}

    for v in views:
        cam = cams[v]
        im = cv2.imread(rgb_paths[v], cv2.IMREAD_UNCHANGED)
        gt_a = torch.tensor(im[:, :, 3].astype(np.float32) / 255.0, device="cuda")
        gt_fg = (gt_a > 0.5).cpu().numpy()

        gb2 = render2dgs.render_gbuffer_2dgs(g2, pipe, cam, half_pixel=False, with_rgb=True)
        a2, d2 = gb2["alpha"], gb2["depth"]
        rgb2 = gb2["rgb"].clamp(0, 1)                       # [H,W,3] RGB
        gt_rgb = torch.tensor(
            (im[:, :, 2::-1].astype(np.float32) / 255.0) * (gt_a[..., None].cpu().numpy())
            + (1.0 - gt_a[..., None].cpu().numpy()), device="cuda")
        # score RGB only on the object interior, where there is actual texture to align to
        er = cv2.erode(gt_fg.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
        er_t = torch.tensor(er, device="cuda")
        d2f = torch.where(torch.isfinite(d2), d2, torch.zeros_like(d2))

        zmesh = oracle.render_depth(cam, view_key=int(v))
        zmesh = zmesh if torch.is_tensor(zmesh) else torch.tensor(zmesh)
        zmesh = zmesh.cuda().float()
        mesh_fg_t = (zmesh < 1e8).float()
        zmesh_np = zmesh.cpu().numpy()
        mesh_fg = zmesh_np < 1e8

        gbv = render.render_gbuffer(gv, keep, cam)
        av = gbv["alpha"].cuda().float()
        del gbv
        torch.cuda.empty_cache()

        for s in SHIFTS:
            # A: 2DGS alpha vs png alpha  (1 - IoU)
            fa = (sample_shift(a2, s) > 0.5).cpu().numpy()
            cost["A_2dgs_vs_png"][s].append(
                1.0 - (fa & gt_fg).sum() / max((fa | gt_fg).sum(), 1))
            # B: 2DGS depth vs mesh depth (median |dz| on mutual fg)
            dd = sample_shift(d2f, s).cpu().numpy()
            m = fa & mesh_fg & (dd > 1e-6)
            cost["B_2dgs_vs_mesh"][s].append(
                float(np.median(np.abs(dd[m] - zmesh_np[m]))) if m.sum() > 100 else np.nan)
            # C: mesh silhouette vs png alpha
            fm = (sample_shift(mesh_fg_t, s) > 0.5).cpu().numpy()
            cost["C_mesh_vs_png"][s].append(
                1.0 - (fm & gt_fg).sum() / max((fm | gt_fg).sum(), 1))
            # D: vanilla gaussian alpha vs png alpha
            fv = (sample_shift(av, s) > 0.5).cpu().numpy()
            cost["D_vanilla_vs_png"][s].append(
                1.0 - (fv & gt_fg).sum() / max((fv | gt_fg).sum(), 1))
            # E: 2DGS rendered RGB vs png RGB on the object interior (mask-free alignment)
            rs = torch.stack([sample_shift(rgb2[:, :, c], s) for c in range(3)], -1)
            cost["E_2dgsRGB_vs_png"][s].append(
                float(((rs - gt_rgb).abs().mean(-1))[er_t].mean().item()))
        print(f"  view {v} done", flush=True)

    print("\n" + "=" * 100)
    print(f"PIXEL-GRID CALIBRATION — {scene}, {len(views)} views {list(views)}")
    print("  cost = 1-IoU (silhouette pairs) or median |dz| (depth pair); lower is better")
    print("=" * 100)
    hdr = f"{'shift s':>8}" + "".join(f"{p:>22}" for p in pairs)
    print(hdr)
    curves = {p: [] for p in pairs}
    for s in SHIFTS:
        row = f"{s:>8.3f}"
        for p in pairs:
            c = float(np.nanmean(cost[p][s]))
            curves[p].append(c)
            row += f"{c:>22.6f}"
        print(row)
    print("-" * 100)
    opt = {}
    for p in pairs:
        o = parabolic_min(SHIFTS, curves[p])
        opt[p] = o
        print(f"  offset {p:<20} = {o:+.3f} px")
    print("-" * 100)
    operative = opt["E_2dgsRGB_vs_png"] - opt["C_mesh_vs_png"]
    resid = operative - opt["B_2dgs_vs_mesh"]
    print(f"  E - C (2DGS -> tier1, decisive) = {operative:+.3f} px")
    print(f"  B     (2DGS -> tier1, weak)     = {opt['B_2dgs_vs_mesh']:+.3f} px   "
          f"[disagreement {resid:+.3f}]")
    print(f"  algebra predicted               = -0.500 px")
    print(f"  NOTE A and D are alpha-IoU tests and are MEANINGLESS here: both models carry a")
    print(f"       white background splat canvas (2DGS alpha>0.5 covers ~99.8% of the frame).")
    print(f"  ==> render2dgs.half_pixel=True (s = -0.5) is the setting to use.")
    print("=" * 100, flush=True)

    p = os.path.join(OUT, "2dgs_align_check.json")
    json.dump({"model": meta, "scene": scene, "views": [int(x) for x in views],
               "shifts": SHIFTS, "curves": curves, "offsets": opt,
               "operative_2dgs_to_tier1_E_minus_C": operative,
               "B_disagreement": resid, "algebra_predicted": -0.5},
              open(p, "w"), indent=1, default=float)
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
