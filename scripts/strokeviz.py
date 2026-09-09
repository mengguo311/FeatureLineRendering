"""tier1/scripts/strokeviz.py — VISUAL-FIRST stroke rendering on cadpartA, two carriers.

Executes out/STROKEVIZ_RESULTS.md (plan frozen before this ran).

*** MESH EVAL-ONLY: faint GT crease overlay only.  P/R is quoted from banked numbers and is
    REPORTED, NEVER GATED. ***

Reuse, not reimplementation: the 3-D clustering is the frozen `strokes.chain_linelets_3d`
via `m1b_stroke_temporal.build_chains`, and the per-frame projection with occlusion splitting
plus the Canny baseline are the frozen `m1b_stroke_temporal.frame_data`, so the pictures show
exactly what the temporal metric measures.  Only the stroke RENDERING is new.

Rendering rules, as converged: piecewise-linear polylines, NO spline smoothing; width constant
in SCREEN space; taper ONLY at true endpoints (a silhouette / occlusion boundary), never at a
chain break; gaps bridged in 3-D by the chainer FIRST, hidden-line removal SECOND by the
projection, which is the required order.
"""
import argparse, json, os, sys, types
import cv2, numpy as np
from scipy.spatial import cKDTree

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1); sys.path.insert(0, os.path.join(TIER1, "scripts"))
from src import common, render, view_split                              # noqa: E402
import temporal_m1b as T                                                # noqa: E402
import m1b_stroke_temporal as M                                         # noqa: E402

OUT = os.path.join(TIER1, "out")
VIZ = os.path.join(OUT, "featviz")
SCENE = "cadpartA"
L_PX = 2.681            # chair-calibrated pixel-anchored half-length, frozen and disclosed
CORE_W, TIP_W, TAPER_PX = 2.6, 0.5, 14.0
N_ORBIT, STRIP0, STRIP_N = 240, 100, 7
BANKED_PR = {"svdexined": "banked P 0.7302 / R 0.8431 (Phase-1b cloud)",
             "svstep3": "banked P 0.8139 / R 0.4206 (STEP3 zero-knob)"}


def chain_args():
    """The frozen m1b_stroke_temporal chaining defaults, so viz chains == metric chains."""
    return types.SimpleNamespace(nms_mult=1.0, knn=10, cos_tan=0.60, cos_col=0.50,
                                 gap_mult=4.0, min_nodes=3, carrier_persistence=False,
                                 cp_ratio=0.0, cp_views=0, fg_only=False, fg_erode=0,
                                 canny_lo=50, canny_hi=150, min_len=4, approx_eps=1.0)


def build_carriers(cams):
    """Write the two carrier npz files the frozen build_chains consumes."""
    f = cams[0].K[0, 0]
    tv = list(view_split.TRAIN)
    made = {}
    # ---- carrier 1: banked DexiNed triangulated cloud -> add tangents/length/conf -------
    z = np.load(os.path.join(OUT, f"dexprimary_p1b_cloud_{SCENE}_ref40.npz"))
    P = z["P"]
    if "surface_keep" in z.files:
        P = P[z["surface_keep"].astype(bool)]
        sup = z["support"][z["surface_keep"].astype(bool)]
    else:
        sup = np.ones(len(P))
    tree = cKDTree(P)
    _, nb = tree.query(P, k=11)
    Q = P[nb[:, 1:]] - P[:, None, :]
    Tg = np.zeros_like(P)
    for i in range(len(P)):                       # PCA principal direction over the kNN ball
        u, s, vt = np.linalg.svd(Q[i] - Q[i].mean(0), full_matrices=False)
        Tg[i] = vt[0]
    zs = []
    for v in tv:
        c = cams[v]
        zc = (c.w2c[:3, :3] @ P.T).T[:, 2] + c.w2c[2, 3]
        zs.append(np.where(zc > 1e-6, zc, np.nan))
    zmed = np.nanmedian(np.stack(zs, 1), axis=1)
    zmed = np.where(np.isfinite(zmed), zmed, np.nanmedian(zmed))
    L = L_PX * zmed / f
    conf = (sup - sup.min()) / max(sup.max() - sup.min(), 1e-9)
    p = os.path.join(OUT, f"linelets_{SCENE}_svdexined_test.npz")
    np.savez(p, p=P, t=Tg, l=L, keep=np.ones(len(P), bool), inlier_ratio=conf,
             n_vis=np.full(len(P), 80, np.int64))
    made["svdexined"] = (p, len(P))
    print(f"  [carrier] svdexined {len(P)} pts, median l {np.median(L):.5f} world "
          f"({L_PX} px)", flush=True)
    # ---- carrier 2: STEP3 geometric ranker, already has tangents ------------------------
    z3 = np.load(os.path.join(OUT, f"linelets_{SCENE}_step3pool.npz"))
    p3 = os.path.join(OUT, f"linelets_{SCENE}_svstep3_test.npz")
    np.savez(p3, p=z3["p"], t=z3["t"], l=z3["l"], keep=z3["keep"],
             inlier_ratio=z3["inlier_ratio"], n_vis=z3["n_vis"])
    made["svstep3"] = (p3, int(z3["keep"].sum()))
    print(f"  [carrier] svstep3 {int(z3['keep'].sum())} kept of {len(z3['keep'])}",
          flush=True)
    return made


def taper_widths(poly, depth, cam):
    """Per-vertex width. Taper ONLY at a true endpoint: an end sitting on a depth
    discontinuity (silhouette / occlusion boundary).  A chain break gets a flat cap."""
    n = len(poly)
    w = np.full(n, CORE_W)
    d = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(poly, axis=0), axis=1))]
    gy, gx = np.gradient(np.where(np.isfinite(depth), depth, 0.0).astype(np.float32))
    gm = np.hypot(gy, gx)
    thr = float(np.percentile(gm[gm > 0], 97)) if (gm > 0).any() else np.inf
    for end, s in ((0, d), (n - 1, d[-1] - d)):
        u = int(np.clip(round(poly[end, 0]), 0, cam.W - 1))
        v = int(np.clip(round(poly[end, 1]), 0, cam.H - 1))
        if gm[v, u] >= thr:                                   # true endpoint -> taper
            r = np.clip(s / TAPER_PX, 0, 1)
            w = np.minimum(w, TIP_W + (CORE_W - TIP_W) * r)
    return w


def draw_strokes(polys, cam, depth, colour=(0.10, 0.10, 0.10), canvas=None, crease=None):
    H, W = cam.H, cam.W
    img = np.ones((H, W, 3), np.float32) if canvas is None else canvas
    if crease is not None:
        img[crease] = (1.0, 0.82, 0.82)
    lay = np.zeros((H, W), np.float32)
    for poly in polys:
        if len(poly) < 2:
            continue
        w = taper_widths(np.asarray(poly, np.float64), depth, cam)
        for i in range(len(poly) - 1):
            a, b = np.asarray(poly[i], np.float64), np.asarray(poly[i + 1], np.float64)
            e = b - a
            n_ = np.linalg.norm(e)
            if n_ < 1e-9:
                continue
            nvec = np.array([-e[1], e[0]]) / n_
            wa, wb = w[i] / 2.0, w[i + 1] / 2.0
            quad = np.array([a + nvec * wa, b + nvec * wb, b - nvec * wb, a - nvec * wa])
            cv2.fillPoly(lay, [np.round(quad * 16).astype(np.int32)], 1.0,
                         lineType=cv2.LINE_AA, shift=4)
    return img * (1.0 - lay[..., None] * (1.0 - np.array(colour, np.float32)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--carriers", nargs="+", default=["svdexined", "svstep3"])
    args = ap.parse_args()
    os.makedirs(VIZ, exist_ok=True)
    cams, _ = common.load_cameras(SCENE)
    g = common.load_gaussians(SCENE)
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    build_carriers(cams)

    from src.mesh_oracle import MeshOracle                              # EVAL ONLY
    o = MeshOracle(SCENE, angle_deg=30.0)
    target = np.median(g["mu"][keep_g], axis=0)
    path = T.orbit_cameras(cams[5], cams[15], N_ORBIT, target)
    frames_idx = list(range(STRIP0, STRIP0 + STRIP_N))
    ca = chain_args()
    made, info = [], {}

    def strip(imgs, out_path, title):
        h = 460
        tiles = [cv2.resize((np.clip(im, 0, 1) * 255).astype(np.uint8), (h, h)) for im in imgs]
        band = np.concatenate(tiles, 1)
        pad = np.full((44, band.shape[1], 3), 255, np.uint8)
        band = np.concatenate([pad, band], 0)
        cv2.putText(band, title, (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 0), 2,
                    cv2.LINE_AA)
        cv2.imwrite(out_path, band[:, :, ::-1])
        made.append(out_path)
        print(f"  wrote {out_path}  {band.shape[1]}x{band.shape[0]}", flush=True)

    base_frames = None
    for car in args.carriers:
        chain3d, cinfo = M.build_chains(SCENE, car, ca)
        info[car] = cinfo
        ours, base, crmasks, depths = [], [], [], []
        for k in frames_idx:
            cam = path[k]
            fd = M.frame_data(g, keep_g, cam, chain3d, ca)
            uvq = o.visible_crease_uv(cam, view_key=("sv", SCENE, k))
            cm = np.zeros((cam.H, cam.W), bool)
            cm[np.clip(np.round(uvq[:, 1]).astype(int), 0, cam.H - 1),
               np.clip(np.round(uvq[:, 0]).astype(int), 0, cam.W - 1)] = True
            ours.append(draw_strokes(fd["A"], cam, fd["depth"], crease=cm))
            base.append(draw_strokes(fd["B"], cam, fd["depth"], crease=cm))
            crmasks.append(cm); depths.append(fd["depth"])
        strip(ours, os.path.join(VIZ, f"stroke_{SCENE}_{car.replace('sv','')}_strip.png"),
              f"{SCENE} {car}  consecutive orbit frames {frames_idx[0]}-{frames_idx[-1]} "
              f"of {N_ORBIT}   {cinfo['n_strokes']} strokes   {BANKED_PR[car]}")
        # difference frame: consecutive pair, frame k RED, k+1 BLUE
        a_, b_ = ours[0], ours[1]
        ia, ib = (a_.min(2) < 0.6), (b_.min(2) < 0.6)
        diff = np.ones(a_.shape, np.float32)
        diff[ia] = (0.85, 0.15, 0.15); diff[ib] = (0.15, 0.25, 0.85)
        diff[ia & ib] = (0.15, 0.15, 0.15)
        p = os.path.join(VIZ, f"stroke_{SCENE}_{car.replace('sv','')}_diff.png")
        cv2.imwrite(p, (np.clip(cv2.resize(diff, (1700, 1700)), 0, 1) * 255
                        ).astype(np.uint8)[:, :, ::-1]); made.append(p)
        print(f"  wrote {p}", flush=True)
        p = os.path.join(VIZ, f"stroke_{SCENE}_{car.replace('sv','')}_still.png")
        cv2.imwrite(p, (np.clip(cv2.resize(ours[0], (1700, 1700)), 0, 1) * 255
                        ).astype(np.uint8)[:, :, ::-1]); made.append(p)
        print(f"  wrote {p}", flush=True)
        base_frames = base
    strip(base_frames, os.path.join(VIZ, f"stroke_{SCENE}_canny_strip.png"),
          f"{SCENE} BASELINE per-frame Canny image-space, same consecutive frames "
          f"(banked P_pop 0.72-0.88)")
    json.dump({"scene": SCENE, "frames": frames_idx, "n_orbit": N_ORBIT,
               "L_px": L_PX, "chain_info": info, "files": made,
               "note": "P/R quoted from banked runs, REPORTED not gated"},
              open(os.path.join(OUT, "strokeviz.json"), "w"), indent=1)
    print(f"\n=== {len(made)} files", flush=True)
    for p in made:
        print("  " + p)


if __name__ == "__main__":
    main()
