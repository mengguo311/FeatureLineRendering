"""tier1/scripts/bufedge_lift_viz.py — render the lifted buffer-edge clouds.

VISUALIZATION ONLY.  No metric is computed here; every P/R in a tile title is read from
out/bufedge_lift.json, produced by the run that also wrote the clouds being drawn, so the
picture and the number describe the same points.

*** MESH EVAL-ONLY: the faint GT crease overlay, nothing else. ***
"""
import json, os, sys
import cv2, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1); sys.path.insert(0, os.path.join(TIER1, "scripts"))
from src import common, render, visibility, view_split                  # noqa: E402

OUT = os.path.join(TIER1, "out")
VIZ = os.path.join(OUT, "featviz")
VIEW = 5
ARMS = ["2dgs_normal", "normal_disc", "depth_disc", "UNION", "UNION_no2dgs", "NULL"]
MADE = []


def draw(P, cam, depth_t, crease_mask, rgb, title):
    """White canvas, faint red GT crease underneath, dark dots for visible cloud points."""
    H, W = cam.H, cam.W
    img = np.ones((H, W, 3), np.float32)
    img[crease_mask] = (1.0, 0.80, 0.80)
    n_vis = 0
    if P is not None and len(P):
        vis, uv, _ = visibility.visible_mask(P, cam, depth_t)
        q = uv[vis]
        u = np.round(q[:, 0]).astype(int); v = np.round(q[:, 1]).astype(int)
        ok = (u >= 0) & (u < W) & (v >= 0) & (v < H)
        u, v = u[ok], v[ok]
        n_vis = len(u)
        acc = np.zeros((H, W), np.float32)
        np.add.at(acc, (v, u), 1.0)
        ink = np.clip(acc / max(np.percentile(acc[acc > 0], 90) if (acc > 0).any() else 1, 1), 0, 1)
        img *= (1.0 - 0.92 * ink)[..., None]
    return img, n_vis


def main():
    d = json.load(open(os.path.join(OUT, "bufedge_lift.json")))
    os.makedirs(VIZ, exist_ok=True)
    for scene in ["cadpartA", "lego"]:
        cams, rgb_paths = common.load_cameras(scene)
        g = common.load_gaussians(scene)
        keep_g = render.defloat_mask(g["mu"], g["opacity"])
        cam = cams[VIEW]
        gb = render.render_gbuffer(g, keep_g, cam, with_albedo=True)
        alpha = gb["alpha"].detach().cpu().numpy()
        alb = np.clip(gb["albedo"].detach().cpu().numpy(), 0, 1)
        fg = alpha > 0.5
        rgb = np.where(fg[..., None], alb, 1.0)

        from src.mesh_oracle import MeshOracle                          # EVAL ONLY
        o = MeshOracle(scene, angle_deg=30.0)
        uvq = o.visible_crease_uv(cam, view_key=("liftviz", scene, VIEW))
        cmask = np.zeros((cam.H, cam.W), bool)
        cu = np.clip(np.round(uvq[:, 0]).astype(int), 0, cam.W - 1)
        cv_ = np.clip(np.round(uvq[:, 1]).astype(int), 0, cam.H - 1)
        cmask[cv_, cu] = True

        tiles = []
        for arm in ARMS:
            f = os.path.join(OUT, f"bufedge_cloud_{scene}_{arm}.npz")
            if not os.path.exists(f):
                tiles.append((arm, None, f"{arm}: cloud missing"))
                print(f"SKIP {scene} {arm} cloud npz missing", flush=True)
                continue
            P = np.load(f)["P"]
            a = d["scenes"][scene]["arms"].get(arm, {})
            im, nv = draw(P, cam, gb["depth"], cmask, rgb, arm)
            t = (f"{arm}   P {a.get('precision_3D_px1.5_equiv', float('nan')):.4f}  "
                 f"R {a.get('recall_3D_px1.5_equiv', float('nan')):.4f}\n"
                 f"{a.get('n_total', 0)} pts kept, {nv} visible here")
            tiles.append((arm, im, t))
            p = os.path.join(VIZ, f"liftarm_{scene}_{arm}.png")
            plt.imsave(p, np.clip(im, 0, 1)); MADE.append(p)
            print(f"  OK {scene} {arm}  {nv} visible", flush=True)

        # reference tile: the banked DexiNed triangulated cloud
        dp = os.path.join(OUT, f"dexprimary_p1b_cloud_{scene}_ref40.npz")
        if os.path.exists(dp):
            z = np.load(dp)
            P = z["P"]
            if "surface_keep" in z.files:
                P = P[z["surface_keep"].astype(bool)]
            im, nv = draw(P, cam, gb["depth"], cmask, rgb, "dexined")
            t = ("REFERENCE banked DexiNed triangulated cloud\n"
                 "P 0.7302  R 0.8431 (banked)   "
                 f"{len(P)} pts, {nv} visible here")
            tiles.append(("dexined_ref", im, t))
            p = os.path.join(VIZ, f"liftarm_{scene}_dexined_ref.png")
            plt.imsave(p, np.clip(im, 0, 1)); MADE.append(p)
            print(f"  OK {scene} dexined_ref  {nv} visible", flush=True)
        else:
            tiles.append(("dexined_ref", None,
                          "REFERENCE DexiNed cloud\nSKIP: no p1b cloud banked for this scene"))
            print(f"SKIP {scene} dexined_ref no banked p1b cloud for this scene", flush=True)

        tiles.append(("rgb", rgb, f"RGB context (3DGS albedo), held-out view {VIEW}"))

        fig, ax = plt.subplots(2, 4, figsize=(4 * 6.4, 2 * 6.8))
        for k, (nm, im, t) in enumerate(tiles[:8]):
            a_ = ax[k // 4, k % 4]
            if im is None:
                a_.text(0.5, 0.5, t, ha="center", va="center", fontsize=11, wrap=True)
            else:
                a_.imshow(np.clip(im, 0, 1))
            a_.set_title(t, fontsize=9)
            a_.axis("off")
        fig.suptitle(f"{scene} — lifted buffer-edge clouds, held-out TEST view {VIEW}; "
                     f"faint red = GT crease (EVAL-ONLY). P/R are 3-D at px1.5-equiv "
                     f"from bufedge_lift.json.", fontsize=12)
        pp = os.path.join(VIZ, f"bufedge_lift_{scene}_panel.png")
        fig.savefig(pp, dpi=125, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        im = cv2.imread(pp)
        MADE.append(pp)
        print(f"  PANEL {pp}  {im.shape[1]}x{im.shape[0]}", flush=True)
    print(f"\n=== {len(MADE)} files", flush=True)
    for p in MADE:
        print("  " + p)


if __name__ == "__main__":
    main()
