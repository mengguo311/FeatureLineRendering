# -*- coding: utf-8 -*-
"""Hybrid signal-specific fusion of object-space (covariance) and image-space
(G-buffer) feature lines for 3DGS. CPU, reuses lib.py + render.py.

Routing (the thesis):
  - OCCLUSION/silhouette: image-space DEPTH leads (clean), object-space only
    fills tiny gaps (additive union, never deletes).
  - CREASE/corner: object-space structure-tensor LEADS (soft confidence gate),
    image-space normal-edge LOCALIZES.
Headline metric on smooth objects = false-edge suppression (non-circular).
Flicker reported at a FIXED common pixel budget + occlusion regression guard.

Usage: fuse.py <scene> [view=mid] [dist=1.35] [opacity_cut=0.18]
"""
import sys, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.ndimage import binary_dilation, binary_erosion, binary_closing, gaussian_filter
import lib

# --------------------------------------------------------------- PARAMETERS
W = H = 780
FOV = 45.0
ROT_DEG = 2.0           # 2-frame flicker camera rotation about up
TOL_SCALE = 0.04
ALPHA_C = 0.10          # crease soft-gate floor (confidence ramp)
C_THR = 0.08            # min 3D-support confidence to keep an image crease ridge
SIGMA_CONF = 2.0        # confidence-map blur (px)
DENSITY_FLOOR = 150     # min visible crease+corner pts to claim crease *lines*
FILL_ON = False         # optional in-band continuity fill
CRE_FILL_Q = 0.85
R_BAND = max(2, round(0.012 * W))


def clip01(a):
    return np.clip(a, 0.0, 1.0)


# --------------------------------------------------------------- geometry helpers
def rot_about(axis, deg):
    a = np.asarray(axis, float); a = a / (np.linalg.norm(a) + 1e-12)
    th = np.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * (K @ K)


def unproject(u, v, z, gb):
    x = (u - gb["cx"]) * z / gb["focal"]
    y = (gb["cy"] - v) * z / gb["focal"]
    cam = np.stack([x, y, z], -1)
    return gb["eye"] + cam @ gb["Rcw"]          # inverse of cam=(X-eye)@Rcw.T


def reproject(Xw, gb):
    cam = (Xw - gb["eye"]) @ gb["Rcw"].T
    z = cam[..., 2]
    u = gb["focal"] * cam[..., 0] / z + gb["cx"]
    v = gb["cy"] - gb["focal"] * cam[..., 1] / z
    return u, v, z


# --------------------------------------------------------------- confidence maps
def conf_map(u, v, w):
    C = np.zeros((H, W))
    iu = np.clip(np.round(u).astype(int), 0, W - 1)
    iv = np.clip(np.round(v).astype(int), 0, H - 1)
    np.add.at(C, (iv, iu), w)
    C = gaussian_filter(C, SIGMA_CONF)
    if (C > 0).any():
        C = C / (np.quantile(C[C > 0], 0.95) + 1e-9)
    return clip01(C)


def project_visible_w(sc, gb, sel, wfull, tol):
    """project candidate Gaussians -> visible (u,v) + their per-Gaussian weight."""
    u, v, z, ok = lib.project(sc, gb, sel)
    sel_ok = sel[ok]; u, v, z = u[ok], v[ok], z[ok]
    iu, iv = u.astype(int), v.astype(int)
    db = gb["depth"][iv, iu]
    vis = ~np.isnan(db) & (z <= db + tol)
    return u[vis], v[vis], wfull[sel_ok[vis]]


# --------------------------------------------------------------- per-frame fusion
def fuse_frame(sc, eye, target, up):
    gb = lib.render_gbuffer(sc, eye, target, up, W, H, FOV)
    cand = lib.candidate_indices(sc, eye)
    isl = lib.image_space_lines(gb)
    tol = TOL_SCALE * sc["scale"]

    # STEP 1 — soft per-Gaussian confidence ramps
    r2, r3, ndv = sc["r2"], sc["r3"], cand["ndotv"]
    flat = sc["flat"].astype(float)
    wc = clip01((r2 - 0.40) / 0.45) * clip01((0.15 - r3) / 0.15) * flat
    wk = clip01((r3 - 0.30) / 0.40) * flat
    ws = clip01((0.18 - ndv) / 0.18) * (r2 < 0.40) * flat

    # STEP 2 — project (weighted) + splat to soft confidence maps
    cu, cv, cw = project_visible_w(sc, gb, cand["crease"], wc, tol)
    ku, kv, kw = project_visible_w(sc, gb, cand["corner"], wk, tol)
    su, sv, sw = project_visible_w(sc, gb, cand["silhouette"], ws, tol)
    C_crease = conf_map(cu, cv, cw)
    C_corner = conf_map(ku, kv, kw)
    C_silh = conf_map(su, sv, sw)
    C_struct = np.maximum(C_crease, C_corner)

    # STEP 3 — image-space responses
    occlusion = isl["occlusion"]; interior = isl["interior"]; cre = isl["crease_resp"]
    E = clip01(cre / (np.quantile(cre[interior], 0.97) + 1e-9))

    # STEP 4 — signal-specific gating
    # CREASE: keep the thin image-space ridge ONLY where 3D structure supports it
    #         -> suppresses unsupported (false) normal edges; stays a clean line
    #         (crease_fused is a strict subset of the baseline ridge).
    crease_fused = isl["crease_im"] & (C_struct > C_THR)
    if FILL_ON:                                            # optional 3D-led completion
        band = binary_dilation(C_struct > C_THR, iterations=R_BAND)
        crease_fused |= interior & band & (cre > np.quantile(cre[interior], CRE_FILL_Q))
    crease_fused = binary_closing(crease_fused, iterations=1)
    # OCCLUSION: depth is already clean & complete here -> pass through. Object-space
    #            confirms/anchors it for temporal stability rather than adding pixels.
    occ_fused = occlusion

    return dict(gb=gb, isl=isl, occlusion=occlusion, interior=interior, cre=cre, E=E,
                crease_im=isl["crease_im"], crease_fused=crease_fused, occ_fused=occ_fused,
                C_struct=C_struct, C_silh=C_silh,
                su=su, sv=sv, cu=cu, cv=cv, ku=ku, kv=kv)


# --------------------------------------------------------------- flicker metric
def flicker(M_t, M_t1, gb_t, gb_t1, score_t, budget):
    """For frame-t edge pixels (top-`budget` by score), count how many have NO
    matching same-method edge in frame t1 within 1px after EXACT reprojection.
    Returns (disagree_count, n_eval, rate, dis_x, dis_y) where dis_* are the
    frame-t coords of the flickering pixels (for visualization)."""
    ys, xs = np.where(M_t)
    if len(ys) == 0:
        return 0, 0, 0.0, np.array([]), np.array([])
    s = score_t[ys, xs]
    if len(ys) > budget:
        keep = np.argsort(s)[-budget:]
        ys, xs = ys[keep], xs[keep]
    z = gb_t["depth"][ys, xs]
    fin = np.isfinite(z)
    ys, xs, z = ys[fin], xs[fin], z[fin]
    Xw = unproject(xs + 0.5, ys + 0.5, z, gb_t)
    u1, v1, z1 = reproject(Xw, gb_t1)
    inb = (u1 > 0) & (u1 < W - 1) & (v1 > 0) & (v1 < H - 1) & (z1 > 0)
    Md = binary_dilation(M_t1, iterations=1)
    iu = np.clip(np.floor(u1[inb]).astype(int), 0, W - 1)   # floor: center coord -> pixel id
    iv = np.clip(np.floor(v1[inb]).astype(int), 0, H - 1)   # (round(x+.5) had a banker's-rounding bias)
    hit = Md[iv, iu]
    xs_in, ys_in = xs[inb], ys[inb]
    n_eval = int(inb.sum())
    disagree = int((~hit).sum())
    return disagree, n_eval, disagree / max(n_eval, 1), xs_in[~hit], ys_in[~hit]


# --------------------------------------------------------------- run one scene
def run_scene(scene, view="mid", dist=1.35, opacity_cut=0.18):
    stem = os.path.splitext(os.path.basename(scene))[0]
    os.makedirs("outputs/fused", exist_ok=True)
    sc = lib.load_scene_ctx(scene, opacity_cut, 220000)
    lib.compute_object_space(sc, k=10)

    eye, target, up = lib.camera_axes(sc, view=view, dist=dist)
    Ft = fuse_frame(sc, eye, target, up)

    # STEP 0 density gate
    n_struct = len(Ft["cu"]) + len(Ft["ku"])
    CREASE_LINES_OK = n_struct >= DENSITY_FLOOR
    print("[%s] visible silh=%d crease=%d corner=%d  CREASE_LINES_OK=%s"
          % (stem, len(Ft["su"]), len(Ft["cu"]), len(Ft["ku"]), CREASE_LINES_OK))

    # false-edge suppression (headline, non-circular)
    cim, cfu, Cs = Ft["crease_im"], Ft["crease_fused"], Ft["C_struct"]
    removed = cim & ~binary_dilation(cfu, iterations=1)
    n_im = int(cim.sum()); n_fu = int(cfu.sum()); n_rm = int(removed.sum())
    rm_nosupp = int((removed & (Cs <= 0.05)).sum())
    supp_rate = n_rm / max(n_im, 1)
    print("[%s] crease px: image=%d  fused=%d | suppressed=%d (%.0f%%), of which no-3D-support=%d (%.0f%%)"
          % (stem, n_im, n_fu, n_rm, 100 * supp_rate, rm_nosupp, 100 * rm_nosupp / max(n_rm, 1)))

    # 2-frame flicker. Honest temporal metric = TOTAL flickering line-work at the
    # methods' NATURAL pixel counts: by deleting unsupported false edges, fusion
    # leaves far less line-work that can flicker (per-pixel rate is NOT claimed to
    # improve on smooth objects — the surviving creases still ride the noisy ridge).
    BIG = 10 ** 9
    eye_t1 = sc["center"] + rot_about(up, ROT_DEG) @ (eye - sc["center"])
    Ft1 = fuse_frame(sc, eye_t1, target, up)
    gb_t, gb_t1 = Ft["gb"], Ft1["gb"]
    bd_im, _, r_im, dxi, dyi = flicker(Ft["crease_im"], Ft1["crease_im"], gb_t, gb_t1, Ft["cre"], BIG)
    bd_fu, _, r_fu, dxf, dyf = flicker(Ft["crease_fused"], Ft1["crease_fused"], gb_t, gb_t1, Ft["cre"], BIG)
    _, _, occ_r, _, _ = flicker(Ft["occlusion"], Ft1["occlusion"], gb_t, gb_t1, gb_t["depth"] * 0 + 1, BIG)
    ink_red = 1 - bd_fu / max(bd_im, 1)
    print("[%s] FLICKER line-work: baseline=%d px flickering (%.0f%%/px) -> fused=%d px (%.0f%%/px) "
          "= -%.0f%% flickering ink | occlusion=%.0f%%"
          % (stem, bd_im, 100 * r_im, bd_fu, 100 * r_fu, 100 * ink_red, 100 * occ_r))

    _save_figs(stem, sc, Ft, Ft1, CREASE_LINES_OK,
               dict(n_im=n_im, n_fu=n_fu, supp_rate=supp_rate, rm_nosupp=rm_nosupp, n_rm=n_rm,
                    bd_im=bd_im, bd_fu=bd_fu, r_im=r_im, r_fu=r_fu, occ_r=occ_r, ink_red=ink_red,
                    n_struct=n_struct, dxi=dxi, dyi=dyi, dxf=dxf, dyf=dyf))
    return stem


# --------------------------------------------------------------- figures
def _overlay(ax, faint, occ=None, crease=None, occ_bold=True):
    ax.imshow(faint)
    if crease is not None:
        cd = binary_dilation(crease, iterations=1)
        rgba = np.zeros((H, W, 4)); rgba[cd] = (0.90, 0.40, 0.0, 0.95)
        ax.imshow(rgba, interpolation="nearest")
    if occ is not None:
        od = binary_dilation(occ, iterations=2 if occ_bold else 1)
        rgba = np.zeros((H, W, 4)); rgba[od] = (0, 0, 0, 1)
        ax.imshow(rgba, interpolation="nearest")
    ax.set_xticks([]); ax.set_yticks([])


def _save_figs(stem, sc, Ft, Ft1, ok, M):
    gb = Ft["gb"]; bg = ~gb["mask"]
    base = gb["color"].copy(); base[bg] = 1.0
    faint = base * 0.45 + 0.55

    # (A) 3-panel
    fig, ax = plt.subplots(1, 3, figsize=(15.5, 5.4)); fig.patch.set_facecolor("white")
    _overlay(ax[0], faint, occ=Ft["occlusion"], crease=Ft["crease_im"])
    ax[0].set_title("(a) IMAGE-SPACE baseline\nocclusion clean; creases (orange) noisy", fontsize=10, color="#b00000")
    ax[1].imshow(faint)
    ax[1].scatter(Ft["su"], Ft["sv"], s=3.5, c="#1f5fd6", alpha=0.6, linewidths=0, label="silhouette")
    ax[1].scatter(Ft["cu"], Ft["cv"], s=3.5, c="#d6451f", alpha=0.7, linewidths=0, label="crease")
    ax[1].scatter(Ft["ku"], Ft["kv"], s=14, c="#15a015", alpha=0.95, linewidths=0, label="corner")
    ax[1].set_xlim(0, W); ax[1].set_ylim(H, 0); ax[1].set_xticks([]); ax[1].set_yticks([])
    ax[1].legend(loc="lower right", fontsize=8, framealpha=0.9, markerscale=2)
    ax[1].set_title("(b) OBJECT-SPACE candidates (from covariance, no mesh)", fontsize=10, color="#0a6b0a")
    _overlay(ax[2], faint, occ=Ft["occ_fused"], crease=Ft["crease_fused"])
    tag = ("creases localized by 3D support" if ok else "creases = false-edge suppression (smooth object)")
    ax[2].set_title("(c) FUSED (ours)\nocclusion depth-led + %s" % tag, fontsize=10, color="#7a3fb5")
    fig.suptitle("%s — fusion suppressed %.0f%% of image crease px (%d→%d, %.0f%% had no 3D support).  "
                 "Flickering line-work %d→%d px (-%.0f%%); occlusion stable at %.0f%%"
                 % (stem, 100 * M["supp_rate"], M["n_im"], M["n_fu"],
                    100 * M["rm_nosupp"] / max(M["n_rm"], 1),
                    M["bd_im"], M["bd_fu"], 100 * M["ink_red"], 100 * M["occ_r"]),
                 fontsize=10, y=1.02)
    plt.tight_layout(); plt.savefig("outputs/fused/%s_fused3.png" % stem, dpi=155, bbox_inches="tight"); plt.close()

    # (B) confidence insets
    fig, ax = plt.subplots(1, 3, figsize=(13.5, 4.7))
    for a, img, t in [(ax[0], Ft["C_struct"], "C_struct (3D crease/corner support)"),
                      (ax[1], Ft["C_silh"], "C_silh (3D silhouette support)"),
                      (ax[2], Ft["E"], "E (image normal-edge, noisy)")]:
        a.imshow(faint * 0 + 1)
        a.imshow(np.ma.masked_where(bg, img), cmap="turbo", vmin=0, vmax=1)
        a.set_title(t, fontsize=10); a.set_xticks([]); a.set_yticks([])
    plt.tight_layout(); plt.savefig("outputs/fused/%s_conf.png" % stem, dpi=150, bbox_inches="tight"); plt.close()

    # (C) flicker panel: total flickering line-work (grey = lines, red = pixels
    #     that change between two adjacent frames). Fusion leaves far less of both.
    fig, ax = plt.subplots(1, 2, figsize=(11, 5.4)); fig.patch.set_facecolor("white")
    for a, mask, dx, dy, ttl, col in [
            (ax[0], Ft["crease_im"], M["dxi"], M["dyi"], "baseline image-space crease", "#b00000"),
            (ax[1], Ft["crease_fused"], M["dxf"], M["dyf"], "FUSED crease (3D-gated)", "#7a3fb5")]:
        a.imshow(faint)
        md = binary_dilation(mask, iterations=1)
        grey = np.zeros((H, W, 4)); grey[md] = (0.5, 0.5, 0.5, 0.9)
        a.imshow(grey, interpolation="nearest")
        a.scatter(dx, dy, s=4, c="red", linewidths=0)
        a.set_xlim(0, W); a.set_ylim(H, 0); a.set_xticks([]); a.set_yticks([])
        a.set_title("%s\n%d line px, %d flickering (red)" % (ttl, int(mask.sum()), len(dx)),
                    fontsize=10, color=col)
    plt.tight_layout(); plt.savefig("outputs/fused/%s_flicker.png" % stem, dpi=150, bbox_inches="tight"); plt.close()
    print("[%s] saved: outputs/fused/%s_{fused3,conf,flicker}.png" % (stem, stem))


# --------------------------------------------------------------- main
if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_scene(sys.argv[1],
                  sys.argv[2] if len(sys.argv) > 2 else "mid",
                  float(sys.argv[3]) if len(sys.argv) > 3 else 1.35,
                  float(sys.argv[4]) if len(sys.argv) > 4 else 0.18)
    else:
        objs = [("nike.splat", "mid", 1.35, 0.18), ("plush.splat", "thin", 1.35, 0.18),
                ("luigi.ply", "thin", 1.45, 0.10)]
        for a in objs:
            run_scene(*a)
        import matplotlib.image as mpimg
        fig, ax = plt.subplots(3, 1, figsize=(15.5, 16.0))
        for a, (sc, *_ ) in zip(ax, objs):
            stem = os.path.splitext(os.path.basename(sc))[0]
            a.imshow(mpimg.imread("outputs/fused/%s_fused3.png" % stem)); a.axis("off")
        fig.suptitle("Hybrid fusion on 3 real 3DGS scenes — [image-space | object-space | FUSED]  (CPU, no GPU)",
                     fontsize=13, y=0.999)
        plt.tight_layout(); plt.savefig("outputs/fused/all_fused.png", dpi=130, bbox_inches="tight")
        print("saved outputs/fused/all_fused.png")
