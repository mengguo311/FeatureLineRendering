"""tier1/scripts/featviz_all.py — FEATURE-LAYER VISUALIZATION, all scenes, L1..L18.

Executes featviz_spec.md.  VISUALIZATION / DIAGNOSTIC ONLY: no metric is gated, nothing is
tuned, no pipeline file is touched.  *** The GT mesh is EVAL-ONLY: it draws the crease
overlays in L13/L14/L15/L17 and nothing else.  It never feeds any signal. ***

One fixed held-out TEST camera per scene, so every layer is pixel-aligned.  Every layer is
wrapped: a missing asset prints `SKIP <scene> <layer> <reason>` and the run continues.
"""
import argparse
import json
import os
import sys
import traceback

import cv2
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))

from src import common, render, visibility, view_split                  # noqa: E402

OUT = os.path.join(TIER1, "out", "featviz")
SCENES = ["cadpartA", "lego", "chair", "ficus"]        # spec priority order
VIEW, VIEW2 = 5, 15                                    # held-out TEST views
DPI, FIG = 125, 10.0                                   # -> every panel >= 800 px on both axes
SKIPS, MADE, NOTES = [], [], {}

# banked reference numbers, quoted only where they exist; never invented
BANKED_DIHEDRAL = {
    "cadpartA": ("vanilla 10.19 deg / 2DGS 40.04 deg (GEOLINE Step 2, ribbon over TRAIN)"),
    "lego": ("vanilla 23.58 deg / 2DGS 20.98 deg (DIAG2DGS, ribbon, TEST)"),
}


def save(fig, scene, layer, title):
    p = os.path.join(OUT, f"{scene}_{layer}.png")
    fig.suptitle(title, fontsize=11)
    fig.savefig(p, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    im = cv2.imread(p)
    MADE.append((scene, layer, os.path.basename(p), f"{im.shape[1]}x{im.shape[0]}"))
    print(f"  OK  {scene} {layer}  {im.shape[1]}x{im.shape[0]}", flush=True)
    return p


def skip(scene, layer, reason):
    SKIPS.append((scene, layer, reason))
    print(f"SKIP {scene} {layer} {reason}", flush=True)


def ax_img(a, img, title, cmap=None, vmin=None, vmax=None):
    a.imshow(img, cmap=cmap, vmin=vmin, vmax=vmax)
    a.set_title(title, fontsize=9)
    a.axis("off")


def normal_disc(nrm, fg):
    """Max angle (deg) between a pixel's normal and its 4-neighbours."""
    n = nrm / (np.linalg.norm(nrm, axis=2, keepdims=True) + 1e-12)
    out = np.zeros(n.shape[:2], np.float32)
    for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0)):
        m = np.roll(n, (dy, dx), axis=(0, 1))
        c = np.abs((n * m).sum(2)).clip(0, 1)
        out = np.maximum(out, np.degrees(np.arccos(c)))
    return np.where(fg, out, 0.0)


def proj2d_cov(mu, quat, scale, cam):
    """Projected 2-D covariance of each gaussian (standard 3DGS EWA splat)."""
    R = common.quat_to_rotmat(quat)
    S = scale[:, :, None] * np.eye(3)[None]
    M = R @ S
    C3 = M @ np.transpose(M, (0, 2, 1))
    W = cam.w2c[:3, :3]
    t = (W @ mu.T).T + cam.w2c[:3, 3]
    f = cam.K[0, 0]
    z = np.maximum(t[:, 2], 1e-6)
    J = np.zeros((len(mu), 2, 3))
    J[:, 0, 0] = f / z; J[:, 0, 2] = -f * t[:, 0] / z ** 2
    J[:, 1, 1] = f / z; J[:, 1, 2] = -f * t[:, 1] / z ** 2
    A = J @ W[None]
    return A @ C3 @ np.transpose(A, (0, 2, 1)), z


def run_scene(scene, args):
    print(f"\n===== {scene}", flush=True)
    NOTES[scene] = {}
    try:
        cams, rgb_paths = common.load_cameras(scene)
        g = common.load_gaussians(scene)
    except Exception as e:
        for L in range(1, 19):
            skip(scene, f"L{L}", f"scene load failed: {e}")
        return
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    X, mu = g["mu"][keep_g], g["mu"]
    cam = cams[VIEW]
    H, W = cam.H, cam.W
    gb = render.render_gbuffer(g, keep_g, cam, with_albedo=True, with_median_depth=True)
    alpha = gb["alpha"].detach().cpu().numpy()
    depth = gb["depth"].detach().cpu().numpy()
    nrm = gb["normal"].detach().cpu().numpy()
    alb = np.clip(gb["albedo"].detach().cpu().numpy(), 0, 1)
    fg = alpha > 0.5
    rgbv = np.where(fg[..., None], alb, 1.0)
    NOTES[scene]["n_gaussians_total"] = int(len(mu))
    NOTES[scene]["n_gaussians_defloatered"] = int(len(X))
    NOTES[scene]["median_max_axis_world"] = float(np.median(g["scale"][keep_g].max(1)))
    NOTES[scene]["view"] = VIEW

    # ---- mesh oracle, EVAL-ONLY overlay ------------------------------------------------
    cuv = None
    try:
        from src.mesh_oracle import MeshOracle                          # EVAL ONLY
        o = MeshOracle(scene, angle_deg=30.0)
        cuv = o.visible_crease_uv(cam, view_key=("featviz", scene, VIEW))
        cm = np.zeros((H, W), bool)
        cu = np.clip(np.round(cuv[:, 0]).astype(int), 0, W - 1)
        cv_ = np.clip(np.round(cuv[:, 1]).astype(int), 0, H - 1)
        cm[cv_, cu] = True
        cdt = cv2.distanceTransform((~cm).astype(np.uint8), cv2.DIST_L2, 5)
    except Exception as e:
        cm = cdt = None
        print(f"  (mesh overlay unavailable: {e})", flush=True)

    # ---- 2DGS, if a model exists -------------------------------------------------------
    n2 = None
    m2 = os.path.join(TIER1, "out", f"2dgs_{scene}")
    if os.path.isdir(m2):
        try:
            from src import render2dgs
            import torch
            g2, pipe2, meta2 = render2dgs.load_2dgs(m2)
            gb2 = render2dgs.render_gbuffer_2dgs(g2, pipe2, cam,
                                                 bg_white=meta2.get("white_background", True))
            n2 = gb2["normal"].detach().cpu().numpy()
            del g2, gb2
            torch.cuda.empty_cache()
        except Exception as e:
            print(f"  (2DGS load failed: {e})", flush=True)

    uv, zc = common.project(X, cam)
    inb = (uv[:, 0] >= 0) & (uv[:, 0] < W) & (uv[:, 1] >= 0) & (uv[:, 1] < H) & (zc > 1e-6)

    def L(n):
        return f"L{n:02d}"

    # ================= L1 rendered RGB =================================================
    try:
        fig, a = plt.subplots(figsize=(FIG, FIG))
        ax_img(a, rgbv, "3DGS albedo render (SH deg-0, view-independent)")
        save(fig, scene, L(1), f"{scene} L1 rendered RGB  view {VIEW} (held-out TEST)")
    except Exception as e:
        skip(scene, L(1), f"render failed: {e}")

    # ================= L2 GT source image ==============================================
    try:
        p = rgb_paths[VIEW]
        if not os.path.exists(p):
            raise FileNotFoundError(p)
        im = cv2.imread(p, cv2.IMREAD_UNCHANGED)
        if im.ndim == 3 and im.shape[2] == 4:
            aa = im[:, :, 3:4].astype(np.float32) / 255.0
            im = (im[:, :, :3] * aa + 255.0 * (1 - aa)).astype(np.uint8)
        gt = im[:, :, ::-1]
        fig, ax = plt.subplots(1, 2, figsize=(2 * FIG, FIG))
        ax_img(ax[0], gt, "GT source photograph")
        ax_img(ax[1], rgbv, "3DGS albedo render")
        save(fig, scene, L(2), f"{scene} L2 GT vs render  view {VIEW}")
    except Exception as e:
        skip(scene, L(2), f"source image unavailable: {e}")

    # ================= L3 gaussian-centre lattice ======================================
    try:
        fig, a = plt.subplots(figsize=(FIG, FIG))
        a.imshow(np.ones_like(rgbv) * 0.12)
        s = a.scatter(uv[inb, 0], uv[inb, 1], c=zc[inb], s=0.35, cmap="turbo", linewidths=0)
        a.set_xlim(0, W); a.set_ylim(H, 0); a.axis("off")
        plt.colorbar(s, ax=a, fraction=0.046, label="depth (world)")
        a.set_title(f"{int(inb.sum())} projected gaussian centres, coloured by depth",
                    fontsize=9)
        save(fig, scene, L(3),
             f"{scene} L3 gaussian-centre lattice  ({len(X)} de-floatered of {len(mu)})")
    except Exception as e:
        skip(scene, L(3), f"lattice failed: {e}")

    # ================= L4 anisotropic ellipses =========================================
    try:
        sc = g["scale"][keep_g]
        aniso = sc.max(1) / np.maximum(sc.min(1), 1e-12)
        idx = np.where(inb)[0]
        if len(idx) > 8000:
            idx = idx[np.linspace(0, len(idx) - 1, 8000).astype(int)]
        C2, _ = proj2d_cov(X[idx], g["quat"][keep_g][idx], sc[idx], cam)
        fig, a = plt.subplots(figsize=(FIG, FIG))
        a.imshow(np.ones_like(rgbv))
        needle = aniso[idx] > 10.0
        for j, i in enumerate(idx):
            w_, V = np.linalg.eigh(C2[j])
            w_ = np.maximum(w_, 1e-8)
            ang = np.degrees(np.arctan2(V[1, 1], V[0, 1]))
            a.add_patch(Ellipse((uv[i, 0], uv[i, 1]), 2 * np.sqrt(w_[1]), 2 * np.sqrt(w_[0]),
                                angle=ang, fill=False, lw=0.35,
                                edgecolor=("#ff2d00" if needle[j] else "#2060c0"),
                                alpha=0.85 if needle[j] else 0.30))
        a.set_xlim(0, W); a.set_ylim(H, 0); a.axis("off")
        a.set_title(f"projected covariance ellipses, n={len(idx)} subsampled; "
                    f"RED = anisotropy>10 ({100*needle.mean():.1f}%) = crease-seed candidates",
                    fontsize=9)
        NOTES[scene]["frac_needle_aniso_gt10"] = float((aniso > 10).mean())
        NOTES[scene]["median_anisotropy"] = float(np.median(aniso))
        save(fig, scene, L(4), f"{scene} L4 anisotropic ellipses  view {VIEW}")
    except Exception as e:
        skip(scene, L(4), f"ellipse plot failed: {e}")

    # ================= L5 opacity + floaters ===========================================
    try:
        uva, za = common.project(mu, cam)
        ib = ((uva[:, 0] >= 0) & (uva[:, 0] < W) & (uva[:, 1] >= 0) & (uva[:, 1] < H)
              & (za > 1e-6))
        fl = ib & (~keep_g)
        fig, a = plt.subplots(figsize=(FIG, FIG))
        a.imshow(np.ones_like(rgbv) * 0.12)
        s = a.scatter(uva[ib & keep_g, 0], uva[ib & keep_g, 1],
                      c=g["opacity"][ib & keep_g], s=0.35, cmap="viridis", linewidths=0)
        a.scatter(uva[fl, 0], uva[fl, 1], s=1.6, c="#ff2d00", linewidths=0,
                  label=f"de-floatered out ({int(fl.sum())})")
        a.set_xlim(0, W); a.set_ylim(H, 0); a.axis("off"); a.legend(fontsize=8, loc="lower right")
        plt.colorbar(s, ax=a, fraction=0.046, label="opacity")
        save(fig, scene, L(5),
             f"{scene} L5 opacity + floaters  (removed {len(mu)-len(X)} of {len(mu)})")
    except Exception as e:
        skip(scene, L(5), f"opacity plot failed: {e}")

    # ================= L6 scale distribution ===========================================
    try:
        mx = g["scale"][keep_g].max(1)
        fig, ax = plt.subplots(1, 2, figsize=(2 * FIG, FIG * 0.85))
        ax[0].hist(mx, bins=120, color="#2060c0")
        ax[0].axvline(np.median(mx), color="r",
                      label=f"median {np.median(mx):.5f} world")
        ax[0].set_yscale("log"); ax[0].legend(fontsize=9)
        ax[0].set_xlabel("max-axis length (world)"); ax[0].set_title(
            "gaussian size histogram", fontsize=9)
        nb = 64
        gy = np.clip((uv[inb, 1] / H * nb).astype(int), 0, nb - 1)
        gx = np.clip((uv[inb, 0] / W * nb).astype(int), 0, nb - 1)
        acc = np.full((nb, nb), np.nan)
        vals = mx[inb]
        for yy in range(nb):
            sel = gy == yy
            if sel.any():
                for xx in np.unique(gx[sel]):
                    acc[yy, xx] = np.median(vals[sel & (gx == xx)])
        im = ax[1].imshow(acc, cmap="magma")
        ax[1].axis("off"); ax[1].set_title("local median gaussian size", fontsize=9)
        plt.colorbar(im, ax=ax[1], fraction=0.046)
        save(fig, scene, L(6),
             f"{scene} L6 gaussian scale  median max-axis {np.median(mx):.5f} world")
    except Exception as e:
        skip(scene, L(6), f"scale plot failed: {e}")

    # ================= L7..L11 render buffers ==========================================
    try:
        dv = np.where(np.isfinite(depth) & fg, depth, np.nan)
        fig, a = plt.subplots(figsize=(FIG, FIG))
        im = a.imshow(dv, cmap="turbo"); a.axis("off")
        plt.colorbar(im, ax=a, fraction=0.046, label="depth")
        save(fig, scene, L(7), f"{scene} L7 depth / z-buffer  view {VIEW}")
    except Exception as e:
        skip(scene, L(7), f"depth failed: {e}")
    try:
        fig, a = plt.subplots(figsize=(FIG, FIG))
        ax_img(a, np.where(fg[..., None], nrm * 0.5 + 0.5, 1.0), "vanilla 3DGS normal buffer")
        save(fig, scene, L(8), f"{scene} L8 rendered normal map  view {VIEW}")
    except Exception as e:
        skip(scene, L(8), f"normal failed: {e}")
    try:
        fig, a = plt.subplots(figsize=(FIG, FIG))
        im = a.imshow(alpha, cmap="gray", vmin=0, vmax=1); a.axis("off")
        plt.colorbar(im, ax=a, fraction=0.046, label="alpha")
        save(fig, scene, L(9), f"{scene} L9 alpha / accumulation  view {VIEW}")
    except Exception as e:
        skip(scene, L(9), f"alpha failed: {e}")
    try:
        d0 = np.where(np.isfinite(depth) & fg, depth, 0.0)
        gyy, gxx = np.gradient(d0)
        dmag = np.where(fg, np.hypot(gyy, gxx), 0.0)
        fig, a = plt.subplots(figsize=(FIG, FIG))
        im = a.imshow(dmag, cmap="inferno",
                      vmax=float(np.percentile(dmag[fg], 99)) if fg.any() else None)
        a.axis("off"); plt.colorbar(im, ax=a, fraction=0.046, label="|grad depth|")
        save(fig, scene, L(10), f"{scene} L10 depth-discontinuity (silhouettes)  view {VIEW}")
    except Exception as e:
        skip(scene, L(10), f"depth-grad failed: {e}")
    nd = None
    try:
        nd = normal_disc(nrm, fg)
        fig, a = plt.subplots(figsize=(FIG, FIG))
        im = a.imshow(nd, cmap="inferno", vmin=0, vmax=90)
        a.axis("off"); plt.colorbar(im, ax=a, fraction=0.046, label="deg")
        save(fig, scene, L(11), f"{scene} L11 normal-discontinuity  view {VIEW}")
    except Exception as e:
        skip(scene, L(11), f"normal-disc failed: {e}")

    # ================= L12 image-space edge detectors ==================================
    try:
        base = cv2.imread(rgb_paths[VIEW], cv2.IMREAD_UNCHANGED)
        if base is None:
            raise FileNotFoundError(rgb_paths[VIEW])
        if base.ndim == 3 and base.shape[2] == 4:
            aa = base[:, :, 3:4].astype(np.float32) / 255.0
            base = (base[:, :, :3] * aa + 255.0 * (1 - aa)).astype(np.uint8)
        gry = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY)
        can = cv2.Canny(cv2.GaussianBlur(gry, (0, 0), 2.0), 100, 200) > 0
        learned, lname = None, None
        for d, nmm in ((f"teed_edges_{scene}", "TEED"), (f"dexined_edges_{scene}", "DexiNed")):
            fp = os.path.join(TIER1, "out", d, f"v{VIEW:03d}.npz")
            if os.path.exists(fp):
                z = np.load(fp)
                learned = z["native"] if "native" in z.files else z[z.files[0]]
                learned = np.asarray(learned, np.float32) > 0.5
                lname = nmm
                break
        ov = np.dstack([base[:, :, 2], base[:, :, 1], base[:, :, 0]]).astype(np.float32) / 255
        ov = ov * 0.45 + 0.55
        ov[can] = [0.0, 0.35, 1.0]
        if learned is not None:
            ov[learned] = [1.0, 0.1, 0.0]
        fig, a = plt.subplots(figsize=(FIG, FIG))
        ax_img(a, np.clip(ov, 0, 1),
               f"BLUE Canny (the pull field's detector)"
               + (f"   RED {lname}" if lname else "   (no learned detector cached)"))
        save(fig, scene, L(12), f"{scene} L12 image-space edges on the source photo")
        NOTES[scene]["learned_detector"] = lname or "none cached"
    except Exception as e:
        skip(scene, L(12), f"edge overlay failed: {e}")

    # ================= L13 GT crease projection (EVAL-ONLY) ============================
    if cm is None:
        skip(scene, L(13), "mesh oracle unavailable")
    else:
        try:
            ov = rgbv * 0.55 + 0.45
            ov[cm] = [1.0, 0.0, 0.0]
            fig, a = plt.subplots(figsize=(FIG, FIG))
            ax_img(a, np.clip(ov, 0, 1), f"{int(cm.sum())} visible GT crease pixels (EVAL-ONLY)")
            save(fig, scene, L(13), f"{scene} L13 GT-mesh creases  view {VIEW}")
        except Exception as e:
            skip(scene, L(13), f"crease overlay failed: {e}")

    # ================= L14 seeds vs GT crease ==========================================
    try:
        lp = os.path.join(TIER1, "out", f"linelets_{scene}_gated_test.npz")
        if not os.path.exists(lp):
            raise FileNotFoundError(lp)
        zz = np.load(lp)
        sp = X[zz["seed_idx"]] if "seed_idx" in zz.files else zz["p0"]
        vis, suv, _ = visibility.visible_mask(sp, cam, gb["depth"])
        su = suv[vis]
        prec = None
        if cdt is not None and len(su):
            uu = np.clip(np.round(su[:, 0]).astype(int), 0, W - 1)
            vv = np.clip(np.round(su[:, 1]).astype(int), 0, H - 1)
            prec = float((cdt[vv, uu] <= 1.5).mean())
            NOTES[scene]["seed_precision_this_view@1.5px"] = prec
        ov = rgbv * 0.5 + 0.5
        if cm is not None:
            ov[cm] = [1.0, 0.0, 0.0]
        fig, a = plt.subplots(figsize=(FIG, FIG))
        a.imshow(np.clip(ov, 0, 1))
        a.scatter(su[:, 0], su[:, 1], s=1.2, c="#00b050", linewidths=0,
                  label=f"M1a seeds visible here ({len(su)})")
        a.axis("off"); a.legend(fontsize=8, loc="lower right")
        a.set_title("RED = GT crease (eval-only)   GREEN = our seeds" +
                    (f"   |   seed precision @1.5px = {prec:.3f}" if prec is not None else ""),
                    fontsize=9)
        save(fig, scene, L(14), f"{scene} L14 seeds vs GT crease  view {VIEW}")
    except Exception as e:
        skip(scene, L(14), f"seed overlay failed: {e}")

    # ================= L15 geometric cue vs GT crease ==================================
    if nd is None or cm is None:
        skip(scene, L(15), "normal-discontinuity or mesh overlay unavailable")
    else:
        try:
            hm = plt.get_cmap("inferno")(np.clip(nd / 90.0, 0, 1))[:, :, :3]
            hm[cm] = [0.0, 1.0, 0.2]
            med_on = float(np.median(nd[cm])) if cm.any() else float("nan")
            off = fg & (cdt > 5.0)
            med_off = float(np.median(nd[off])) if off.any() else float("nan")
            NOTES[scene]["normal_disc_median_on_crease_deg"] = med_on
            NOTES[scene]["normal_disc_median_off_crease_deg"] = med_off
            fig, a = plt.subplots(figsize=(FIG, FIG))
            ax_img(a, hm, f"heat = normal-discontinuity; GREEN = GT crease   |   "
                          f"median on-crease {med_on:.1f} deg vs off-crease {med_off:.1f} deg")
            save(fig, scene, L(15), f"{scene} L15 geometric cue vs GT crease  view {VIEW}")
        except Exception as e:
            skip(scene, L(15), f"alignment panel failed: {e}")

    # ================= L16 vanilla vs 2DGS normal ======================================
    if n2 is None:
        skip(scene, L(16), "no 2DGS model for this scene")
    else:
        try:
            nd2 = normal_disc(n2, fg)
            m1 = float(np.median(nd[cm])) if (nd is not None and cm is not None and cm.any()) else float("nan")
            m2v = float(np.median(nd2[cm])) if cm is not None and cm.any() else float("nan")
            NOTES[scene]["normal_disc_on_crease_vanilla_deg"] = m1
            NOTES[scene]["normal_disc_on_crease_2dgs_deg"] = m2v
            fig, ax = plt.subplots(1, 2, figsize=(2 * FIG, FIG))
            ax_img(ax[0], np.where(fg[..., None], nrm * 0.5 + 0.5, 1.0),
                   f"vanilla 3DGS normal   median disc on GT crease {m1:.1f} deg")
            ax_img(ax[1], np.where(fg[..., None], n2 * 0.5 + 0.5, 1.0),
                   f"2DGS surfel normal   median disc on GT crease {m2v:.1f} deg")
            bank = BANKED_DIHEDRAL.get(scene, "no banked ribbon-dihedral pair for this scene")
            save(fig, scene, L(16),
                 f"{scene} L16 vanilla vs 2DGS normal   |   banked ribbon dihedral: {bank}")
        except Exception as e:
            skip(scene, L(16), f"2DGS comparison failed: {e}")

    # ================= L17 extracted line drawing ======================================
    try:
        lp = os.path.join(TIER1, "out", f"linelets_{scene}_gated_test.npz")
        if not os.path.exists(lp):
            raise FileNotFoundError(lp)
        zz = np.load(lp)
        from src import linelet
        P1, T1, L1_, K1 = zz["p"], zz["t"], zz["l"], zz["keep"]
        visl, uvl, _ = visibility.visible_mask(P1, cam, gb["depth"])
        sel = visl & K1
        a_, b_ = linelet.endpoints(P1, T1, L1_)
        ua, _ = common.project(a_, cam)
        ub, _ = common.project(b_, cam)
        canvas = np.ones((H, W, 3), np.float32)
        if cm is not None:
            canvas[cm] = [1.0, 0.80, 0.80]
        img = (canvas * 255).astype(np.uint8)
        S = 16
        n_drawn = 0
        for i in np.where(sel)[0]:
            pa = (int(np.clip(ua[i, 0], -1e4, 1e4) * S), int(np.clip(ua[i, 1], -1e4, 1e4) * S))
            pb = (int(np.clip(ub[i, 0], -1e4, 1e4) * S), int(np.clip(ub[i, 1], -1e4, 1e4) * S))
            cv2.line(img, pa, pb, (10, 10, 10), 1, cv2.LINE_8, 4)
            n_drawn += 1
        fig, a = plt.subplots(figsize=(FIG, FIG))
        ax_img(a, img, f"our shipped line drawing ({n_drawn} linelets drawn); "
                       f"faint red = GT crease")
        save(fig, scene, L(17), f"{scene} L17 extracted lines vs GT  view {VIEW}")
        NOTES[scene]["linelets_kept"] = int(K1.sum())
        NOTES[scene]["linelets_total"] = int(len(K1))
    except Exception as e:
        skip(scene, L(17), f"line drawing failed: {e}")

    # ================= L18 contact sheet ===============================================
    try:
        want = [1, 3, 4, 7, 8, 11, 14, 16]
        tiles = [(n, os.path.join(OUT, f"{scene}_{L(n)}.png")) for n in want]
        tiles = [(n, p) for n, p in tiles if os.path.exists(p)]
        if not tiles:
            raise RuntimeError("no component panels exist")
        fig, ax = plt.subplots(2, 4, figsize=(4 * 6.0, 2 * 6.0))
        for k, (n, p) in enumerate(tiles):
            im = cv2.imread(p)[:, :, ::-1]
            ax_img(ax[k // 4, k % 4], im, L(n))
        for k in range(len(tiles), 8):
            ax[k // 4, k % 4].axis("off")
        save(fig, scene, L(18),
             f"{scene} L18 contact sheet  ({len(tiles)} of 8 panels present)")
    except Exception as e:
        skip(scene, L(18), f"montage failed: {e}")

    # ---- optional second view for chair/lego normal panels -----------------------------
    if scene in ("chair", "lego"):
        try:
            c2 = cams[VIEW2]
            gv = render.render_gbuffer(g, keep_g, c2)
            a2 = gv["alpha"].detach().cpu().numpy() > 0.5
            nv = gv["normal"].detach().cpu().numpy()
            fig, ax = plt.subplots(1, 2, figsize=(2 * FIG, FIG))
            ax_img(ax[0], np.where(a2[..., None], nv * 0.5 + 0.5, 1.0),
                   f"normal buffer, view {VIEW2}")
            ax_img(ax[1], normal_disc(nv, a2), f"normal-discontinuity, view {VIEW2}",
                   cmap="inferno", vmin=0, vmax=90)
            save(fig, scene, "L08b_view2", f"{scene} second held-out view {VIEW2}")
        except Exception as e:
            skip(scene, "L08b_view2", f"second view failed: {e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", nargs="+", default=SCENES)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    for s in args.scenes:
        try:
            run_scene(s, args)
        except Exception:
            traceback.print_exc()
            skip(s, "ALL", "unhandled scene error")

    lines = ["# FEATVIZ MANIFEST — per-layer feature visualization, L1..L18",
             "",
             "Produced by `scripts/featviz_all.py` from `featviz_spec.md`. "
             "**VISUALIZATION / DIAGNOSTIC ONLY**: no metric is gated, nothing is tuned, "
             "no pipeline file was modified, nothing committed.",
             "",
             "**MESH EVAL-ONLY.** The GT mesh draws the crease overlays in L13, L14, L15 and "
             "L17 and nothing else. It never feeds any signal.",
             "",
             f"One fixed held-out TEST camera per scene (view {VIEW}); every layer is "
             f"pixel-aligned. chair and lego also get a second view ({VIEW2}) for the normal "
             "panels.", "",
             f"## Files ({len(MADE)} PNGs)", "",
             "| scene | layer | file | pixels |", "|---|---|---|---|"]
    for s, l, f, px in MADE:
        lines.append(f"| {s} | {l} | `{f}` | {px} |")
    lines += ["", f"## Skips ({len(SKIPS)})", ""]
    if SKIPS:
        lines += ["| scene | layer | reason |", "|---|---|---|"]
        lines += [f"| {s} | {l} | {r} |" for s, l, r in SKIPS]
    else:
        lines.append("None.")
    lines += ["", "## Per-scene annotations", ""]
    for s in args.scenes:
        if s not in NOTES:
            continue
        lines.append(f"### {s}")
        for k, v in NOTES[s].items():
            lines.append(f"- **{k}**: {v}")
        lines.append("")
    lines += ["## Reading notes", "",
              "- L4 red ellipses are gaussians with 3-D anisotropy above 10, the needle-like "
              "primitives the seed stage treats as crease carriers.",
              "- L6 is the textureless-means-large-gaussians effect; compare the median "
              "max-axis across scenes.",
              "- L11/L15 are the geometric cue. The on-crease versus off-crease medians in "
              "L15 say whether it separates at all in this view.",
              "- L16's in-panel numbers are the median normal-discontinuity at GT crease "
              "pixels measured HERE, in this single view. They are a different estimator "
              "from the banked ribbon dihedrals quoted in the same title, which were "
              "measured over many views; the two are not interchangeable and are labelled "
              "separately.",
              "- L14's seed precision is for THIS VIEW only and is not the banked "
              "multi-view seed precision."]
    mp = os.path.join(OUT, "FEATVIZ_MANIFEST.md")
    open(mp, "w").write("\n".join(lines) + "\n")
    print(f"\n=== {len(MADE)} PNGs, {len(SKIPS)} skips -> {mp}", flush=True)


if __name__ == "__main__":
    main()
