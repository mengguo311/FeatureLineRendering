"""SPLAT-CENTER POSITION-PCA falsification: can the raw gaussian CENTRES separate baked
texture geometry from a real crease, where normals and rendered depth could not?

*** EVAL-ONLY DIAGNOSTIC *** The GT mesh labels pixels fabric-print vs true-crease and
does nothing else; both scores are computed from gaussians / the G-buffer alone.

HYPOTHESIS. C_N (covariance of NORMALS) is dead because shingled splats kink their
normals freely to fake a colour edge. Splat CENTRES are different: moving a centre off
the true surface plane costs cross-view reprojection mismatch on high-frequency albedo, a
real photometric penalty, so centres should stay pinned to the surface. Prediction: at a
flat fabric print the centres stay COPLANAR (lambda3 ~ 0) even though the normals are
kinked, while at a genuine dihedral crease the centres span a 3D wedge (lambda3 > 0).

TWO SCORES (crease is predicted HIGHER on both):
  (a) 3D CENTRE PCA — gather the K nearest splat centres to the rendered surface point,
      keep those within `rad_mult` x the median splat spacing, covariance of the centres,
      S_center = lambda3 / (lambda1+lambda2+lambda3). Also reported: sqrt(lambda3) in
      px-equivalents, the absolute out-of-plane thickness.
  (b) SCREEN-SPACE CROSS-CHECK — plane fit over a (2w+1)^2 window of the RENDERED depth,
      RMSE point-to-plane residual in px-equivalents. NOTE this consumes the rendered
      depth, which the STEP-0 falsification already showed is albedo-contaminated; it is
      here as the control that (a) is meant to beat.

Labelling is identical to scripts/explore/gate_falsify.py (fabric = on-object Canny pixel
with NO GT crease within 3px; crease = one WITH a GT crease within 2px; interior only,
>4px from the silhouette) and on the same spread views, so the numbers are directly
comparable with that experiment's dihedral result.
"""
import json
import os
import sys

import cv2
import numpy as np
from scipy.spatial import cKDTree

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
sys.path.insert(0, os.path.join(TIER1, "scripts/explore"))

from src import common, render, dt_pull
from src.mesh_oracle import MeshOracle          # EVAL ONLY — labelling only
import gate_falsify as GF                        # reuse pct() and the labelling constants

OUT = os.path.join(TIER1, "out")
K_NN = 128         # candidate centres gathered per pixel (large enough that the ball is
                   # not truncated: at rad 6x spacing only 2.4% of pixels saturate K)
RAD_MULTS = (3.0, 4.0, 6.0)   # MEASURED: the 8th nearest centre sits at ~3.4x the median
                   # 1-NN spacing, so a 2x ball holds a median of ONE centre and admits
                   # only 7% of pixels. Anything <=3x scores a dense-region subsample.
MIN_PTS = 8
W_DEPTH = 4        # (2w+1)^2 = 81 px depth window for score (b)


def auc(s, y):
    """P(score[crease] > score[fabric]); 0.5 = no information."""
    s = np.asarray(s, float); y = np.asarray(y, bool)
    ok = np.isfinite(s); s, y = s[ok], y[ok]
    n1 = int(y.sum()); n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return float("nan")
    r = np.empty(len(s)); r[np.argsort(s, kind="stable")] = np.arange(len(s))
    return float((r[y].sum() - n1 * (n1 - 1) / 2) / (n1 * n0))


def unproject(u, v, z, cam):
    f, cx, cy = cam.f, cam.K[0, 2], cam.K[1, 2]
    Xc = np.stack([(u - cx) * z / f, (v - cy) * z / f, z], -1)
    R, t = cam.w2c[:3, :3], cam.w2c[:3, 3]
    return (R.T @ (Xc - t).T).T


def center_pca(P3, tree, radius, d=None, idx=None):
    """(a) covariance of the nearby SPLAT CENTRES. Returns S_center, sqrt(l3), n_used."""
    if d is None:
        d, idx = tree.query(P3, k=K_NN, workers=-1)
    pts = tree.data[idx]                                  # [M,K,3]
    m = (d < radius)
    cnt = m.sum(1)
    w = m.astype(np.float64)
    n = np.maximum(cnt, 1)[:, None]
    mu = (pts * w[..., None]).sum(1) / n
    dv = (pts - mu[:, None, :]) * w[..., None]
    C = np.einsum("mki,mkj->mij", dv, dv) / np.maximum(cnt, 1)[:, None, None]
    ev = np.linalg.eigvalsh(C)                            # ascending: l3,l2,l1
    l3 = np.clip(ev[:, 0], 0, None)
    tot = np.clip(ev.sum(1), 1e-30, None)
    return l3 / tot, np.sqrt(l3), cnt


def depth_plane_rmse(px, py, depth, fg, cam, w=W_DEPTH):
    """(b) point-to-plane RMSE over a depth window, in px-equivalents."""
    H, W = depth.shape
    off = np.arange(-w, w + 1)
    ou, ov = np.meshgrid(off, off, indexing="xy")
    ou, ov = ou.ravel(), ov.ravel()
    qu = np.clip(px[:, None] + ou[None], 0, W - 1).astype(np.int64)
    qv = np.clip(py[:, None] + ov[None], 0, H - 1).astype(np.int64)
    z = depth[qv, qu]
    good = fg[qv, qu] & np.isfinite(z) & (z > 1e-6)
    z = np.where(good, z, 1.0)
    f, cx, cy = cam.f, cam.K[0, 2], cam.K[1, 2]
    X = np.stack([(qu - cx) * z / f, (qv - cy) * z / f, z], -1)   # camera coords
    wgt = good.astype(np.float64)
    cnt = wgt.sum(1)
    n = np.maximum(cnt, 1)[:, None]
    mu = (X * wgt[..., None]).sum(1) / n
    dv = (X - mu[:, None, :]) * wgt[..., None]
    C = np.einsum("mki,mkj->mij", dv, dv) / np.maximum(cnt, 1)[:, None, None]
    l3 = np.clip(np.linalg.eigvalsh(C)[:, 0], 0, None)
    zc = depth[np.clip(py, 0, H - 1).astype(np.int64), np.clip(px, 0, W - 1).astype(np.int64)]
    return np.sqrt(l3) * cam.f / np.maximum(zc, 1e-9), cnt


def main():
    scene = sys.argv[1] if len(sys.argv) > 1 else "chair"
    nviews = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    cams, rgb_paths = common.load_cameras(scene)
    g = common.load_gaussians(scene)
    keep = render.defloat_mask(g["mu"], g["opacity"])
    X = g["mu"][keep]
    tree = cKDTree(X)
    spacing = float(np.median(tree.query(X, k=2, workers=-1)[0][:, 1]))
    oracle = MeshOracle(scene)
    views = np.unique(np.round(np.linspace(0, len(cams) - 1, nviews)).astype(int))
    print(f"[{scene}] centre-PCA falsification, {len(views)} views {list(views)}")
    print(f"  {len(X)} de-floatered splats, median 1-NN spacing {spacing:.5f}, "
          f"gather radii {RAD_MULTS} x spacing (K={K_NN})", flush=True)

    keys = [f"a@{r:g}" for r in RAD_MULTS] + [f"at@{r:g}" for r in RAD_MULTS] + ["b"]
    acc = {c: {k: [] for k in keys} for c in ("fab", "cre")}
    cov = {f"a@{r:g}": [0, 0] for r in RAD_MULTS}
    for v in views:
        cam = cams[v]
        gb = render.render_gbuffer(g, keep, cam)
        depth = gb["depth"].cpu().numpy().astype(np.float64)
        alpha = gb["alpha"].cpu().numpy()
        del gb
        fg = (alpha > 0.5) & np.isfinite(depth)
        uvq = oracle.visible_crease_uv(cam, view_key=int(v))
        cm = np.zeros(fg.shape, bool)
        cm[np.clip(np.round(uvq[:, 1]).astype(int), 0, cam.H - 1),
           np.clip(np.round(uvq[:, 0]).astype(int), 0, cam.W - 1)] = True
        cdt = cv2.distanceTransform((~cm).astype(np.uint8), cv2.DIST_L2, 5)
        sil = fg ^ (cv2.erode(fg.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)
        sdt = cv2.distanceTransform((~sil).astype(np.uint8), cv2.DIST_L2, 5)
        interior = fg & (sdt > 4)
        edge = dt_pull.edge_map(rgb_paths[v], dt_pull.EDGE_SHARP)
        for cls, m in (("fab", edge & interior & (cdt > 3.0)),
                       ("cre", edge & interior & (cdt <= 2.0))):
            ys, xs = np.nonzero(m)
            if not len(ys):
                continue
            if len(ys) > 20000:
                sel = np.random.RandomState(0).choice(len(ys), 20000, False)
                ys, xs = ys[sel], xs[sel]
            P3 = unproject(xs.astype(np.float64), ys.astype(np.float64),
                           depth[ys, xs], cam)
            dk, ik = tree.query(P3, k=K_NN, workers=-1)
            s_b, cnt_b = depth_plane_rmse(xs.astype(np.float64), ys.astype(np.float64),
                                          depth, fg, cam)
            zc = np.maximum(depth[ys, xs], 1e-9)
            for rm in RAD_MULTS:
                s_a, thick, cnt_a = center_pca(P3, tree, rm * spacing, d=dk, idx=ik)
                ok = (cnt_a >= MIN_PTS) & (cnt_b >= 20)
                acc[cls][f"a@{rm:g}"].append(s_a[ok])
                acc[cls][f"at@{rm:g}"].append(thick[ok] * cam.f / zc[ok])
                cov[f"a@{rm:g}"][0] += int(ok.sum()); cov[f"a@{rm:g}"][1] += int(len(ok))
            acc[cls]["b"].append(s_b[cnt_b >= 20])
        print(f"  view {v} done", flush=True)

    res = {"scene": scene, "views": [int(v) for v in views], "K_NN": K_NN,
           "rad_mults": list(RAD_MULTS), "median_splat_spacing": spacing,
           "depth_window_px": 2 * W_DEPTH + 1, "scores": {}}
    NAMES = {}
    for rm in RAD_MULTS:
        NAMES[f"a@{rm:g}"] = f"(a) centre PCA S_center, gather {rm:g}x spacing"
    for rm in RAD_MULTS:
        NAMES[f"at@{rm:g}"] = f"(a') centre thickness sqrt(l3) px, gather {rm:g}x"
    NAMES["b"] = "(b) rendered-depth window plane RMSE [px-equiv]"
    res["pixel_coverage"] = {k: v[0] / max(v[1], 1) for k, v in cov.items()}
    print("\n" + "=" * 104)
    print(f"CENTRE-PCA RESULT — {scene}   (crease is predicted to score HIGHER on all)")
    print("=" * 104)
    print(f"{'score':52s} {'n_fab':>7s} {'n_cre':>7s} {'fab_p95':>9s} {'cre_p05':>9s} "
          f"{'cre_p50':>9s} {'sep':>8s} {'AUC':>6s}")
    for k, nm in NAMES.items():
        f_ = np.concatenate(acc["fab"][k]); c_ = np.concatenate(acc["cre"][k])
        y = np.concatenate([np.zeros(len(f_), bool), np.ones(len(c_), bool)])
        a = auc(np.concatenate([f_, c_]), y)
        f95, c05, c50 = GF.pct(f_, 95), GF.pct(c_, 5), GF.pct(c_, 50)
        res["scores"][k] = {"name": nm, "n_fabric": int(len(f_)), "n_crease": int(len(c_)),
                            "fabric_p05": GF.pct(f_, 5), "fabric_p50": GF.pct(f_, 50),
                            "fabric_p95": f95, "crease_p05": c05, "crease_p50": c50,
                            "crease_p95": GF.pct(c_, 95), "separation": c05 - f95,
                            "auc": a}
        print(f"{nm:52s} {len(f_):7d} {len(c_):7d} {f95:9.5f} {c05:9.5f} {c50:9.5f} "
              f"{c05 - f95:+8.5f} {a:6.3f}")
        res["scores"][k]["_f"], res["scores"][k]["_c"] = f_, c_

    best = max((f"a@{r:g}" for r in RAD_MULTS), key=lambda k: res["scores"][k]["auc"])
    res["gate_score_key"] = best
    pa = res["scores"][best]
    A, f95, c05, c50 = pa["auc"], pa["fabric_p95"], pa["crease_p05"], pa["crease_p50"]
    if A >= 0.95 and f95 < c05:
        verdict = "GO — position-PCA saves precision; 2DGS can be skipped"
    elif A < 0.85 or f95 >= c50:
        verdict = "NO-GO — 2DGS (or equivalent geometry-regularised training) is MANDATORY"
    else:
        verdict = "MARGINAL"
    res["verdict"] = verdict
    print("\n  pixel coverage per gather radius: " +
          "  ".join(f"{k} {100*v:.1f}%" for k, v in res["pixel_coverage"].items()))
    print("\n" + "#" * 104)
    print(f"# DECISION GATE on the BEST variant of score (a) [{best}]: AUC = {A:.3f}, "
          f"fabric_p95 = {f95:.5f}, "
          f"crease_p05 = {c05:.5f}, crease_p50 = {c50:.5f}")
    print(f"#   GO needs AUC>=0.95 AND fabric_p95<crease_p05 | NO-GO if AUC<0.85 OR "
          f"fabric_p95>=crease_p50")
    print(f"#   ==> VERDICT: {verdict}")
    print("#" * 104, flush=True)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(19, 5))
    for ax, k in zip(axes, (best, best.replace("a@", "at@"), "b")):
        r = res["scores"][k]
        f_, c_ = r["_f"], r["_c"]
        hi = np.percentile(np.concatenate([f_, c_]), 99)
        bins = np.linspace(0, hi, 80)
        ax.hist(f_, bins=bins, alpha=0.6, density=True, color="tab:red",
                label=f"FABRIC print (n={len(f_)})")
        ax.hist(c_, bins=bins, alpha=0.6, density=True, color="tab:blue",
                label=f"TRUE crease (n={len(c_)})")
        ax.axvline(r["fabric_p95"], color="tab:red", ls="--",
                   label=f"fabric p95={r['fabric_p95']:.4f}")
        ax.axvline(r["crease_p05"], color="tab:blue", ls="--",
                   label=f"crease p05={r['crease_p05']:.4f}")
        ax.set_title(f"{scene} — {r['name']}\nAUC={r['auc']:.3f}", fontsize=10)
        ax.legend(fontsize=7)
    plt.tight_layout()
    p = os.path.join(OUT, f"m1b_center_pca_{scene}.png")
    plt.savefig(p, dpi=110)
    for k in res["scores"]:
        res["scores"][k].pop("_f", None); res["scores"][k].pop("_c", None)
    json.dump(res, open(os.path.join(OUT, f"m1b_center_pca_{scene}.json"), "w"), indent=2)
    print(f"wrote {p} + .json")


if __name__ == "__main__":
    main()
