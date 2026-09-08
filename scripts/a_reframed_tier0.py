#!/usr/bin/env python
"""A-REFRAMED TIER-0 — does a JUNCTION response discriminate lego's brick geometry
(theta=90.000 band) from its 12-gon stud TESSELLATION (theta=30.000 band), at the CARRIER
level, better than the ranking evidence we already use?

*** Mechanism being tested: stud barrels are tessellations of a smooth cylinder, so their
    facet edges run parallel along the barrel with NO junctions. Brick geometry is
    junction-dense. A junction response should separate them. ***

*** HONESTY, up front: even a PASS is UNACTIONABLE under the frozen theta=30 oracle,
    because tessellation edges are INSIDE the GT crease set and drawing them scores as true
    positives. Suppressing them lowers both measured recall and precision. This is run as a
    finding about lego's asset structure, NOT as a build gate. ***

Split hygiene: runs on VAL views, so TEST stays untouched. Diagnostic only, selects nothing.
Mesh EVAL-ONLY (banked crease points + banked per-point dihedral). No pull. Banked TEED maps.

Arms      J_lambda2 (primary): small eigenvalue of the structure tensor of the TEED map --
                     large where two orientations coexist, i.e. a junction.
          J_harris (sensitivity): det - k*trace^2, k=0.04.
Controls  teed_mean: mean raw TEED probability at the projection (what J must beat).
          teed_seedscore: the banked M1a seed score we actually rank with.

FROZEN go/no-go, positive class = theta=90.000 band:
  GO      AUC(J) >= 0.65 AND AUC(J) - max(AUC(controls)) >= 0.05
  NO-GO   AUC(J) <= 0.58 OR the margin over the best control is < 0.05
  MIDDLE  otherwise -> report, do not act
"""
import json, os, sys

import cv2
import numpy as np
from scipy.spatial import cKDTree

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
for p in (TIER1, os.path.join(TIER1, "scripts"), os.path.join(TIER1, "scripts/explore"),
          os.path.join(TIER1, "scripts/explore/syn")):
    if p not in sys.path:
        sys.path.insert(0, p)

from src import view_split, visibility            # noqa: E402
from tune_lib import Harness                      # noqa: E402

OUT = os.path.join(TIER1, "out")
SIGMA = 2.0
HARRIS_K = 0.04
BAND90 = (89.95, 90.05)
BAND30 = (30.00, 30.05)


def auc_mw(score, pos):
    s = np.asarray(score, np.float64); y = np.asarray(pos, bool)
    ok = np.isfinite(s); s, y = s[ok], y[ok]
    n1, n0 = int(y.sum()), int((~y).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    order = np.argsort(s, kind="stable")
    r = np.empty(len(s)); r[order] = np.arange(len(s)) + 1.0
    # average ranks for ties
    sv = s[order]; i = 0
    while i < len(sv):
        j = i
        while j + 1 < len(sv) and sv[j + 1] == sv[i]:
            j += 1
        if j > i:
            r[order[i:j + 1]] = 0.5 * ((i + 1) + (j + 1))
        i = j + 1
    return float((r[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def junction_maps(P):
    """structure tensor of the TEED map -> (lambda2, harris)."""
    P = P.astype(np.float32)
    gx = cv2.Sobel(P, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(P, cv2.CV_32F, 0, 1, ksize=3)
    Jxx = cv2.GaussianBlur(gx * gx, (0, 0), SIGMA)
    Jyy = cv2.GaussianBlur(gy * gy, (0, 0), SIGMA)
    Jxy = cv2.GaussianBlur(gx * gy, (0, 0), SIGMA)
    tr = Jxx + Jyy
    det = Jxx * Jyy - Jxy * Jxy
    disc = np.sqrt(np.maximum((Jxx - Jyy) ** 2 + 4 * Jxy * Jxy, 0))
    lam2 = 0.5 * (tr - disc)                      # small eigenvalue
    harris = det - HARRIS_K * tr * tr
    return lam2, harris


def main():
    gt = np.load(os.path.join(TIER1, "cache/dexp0_gt_lego_a30.npz"))
    cp = gt["crease_pts"]
    xz = np.load(os.path.join(OUT, "xy/xy_expX_lego_p1c.npz"))
    theta = np.full(len(cp), np.nan, np.float32)
    theta[xz["seen_idx"]] = xz["theta0_pt"]

    h = Harness("lego", views=view_split.VAL)
    X = h.X
    sp = float(np.median(cKDTree(X).query(X, k=2)[0][:, 1]))
    print(f"pool={len(X)}  carrier NN spacing={sp:.6f}", flush=True)

    d3, idx3 = cKDTree(cp).query(X, workers=-1)
    th_c = theta[idx3]
    near = d3 <= sp
    b90 = near & (th_c >= BAND90[0]) & (th_c < BAND90[1])
    b30 = near & (th_c >= BAND30[0]) & (th_c < BAND30[1])
    print(f"carriers near a crease (<= 1 spacing): {int(near.sum())}", flush=True)
    print(f"  band90 (theta=90.000) carriers = {int(b90.sum())}", flush=True)
    print(f"  band30 (theta=30.000) carriers = {int(b30.sum())}", flush=True)

    acc = {k: np.zeros(len(X)) for k in ("lam2", "harris", "teed")}
    cnt = np.zeros(len(X))
    for v in view_split.VAL:
        z = np.load(os.path.join(OUT, f"teed_edges_lego/v{v:03d}.npz"))
        P = z["native"].astype(np.float32)
        lam2, har = junction_maps(P)
        cam = h.cams[v]
        vis, uv, _ = visibility.visible_mask(X, cam, h.gbufs[v]["depth"])
        uu = np.clip(np.round(uv[:, 0]).astype(int), 0, cam.W - 1)
        vv = np.clip(np.round(uv[:, 1]).astype(int), 0, cam.H - 1)
        acc["lam2"][vis] += lam2[vv[vis], uu[vis]]
        acc["harris"][vis] += har[vv[vis], uu[vis]]
        acc["teed"][vis] += P[vv[vis], uu[vis]]
        cnt += vis
        print(f"  view {v:3d}: visible carriers={int(vis.sum())}", flush=True)
    den = np.maximum(cnt, 1)
    feats = {k: acc[k] / den for k in acc}
    feats["teed_seedscore"] = np.load(os.path.join(
        TIER1, "scripts/explore/syn/finalscore_overall_lego__teed_native_0.5.npy"))
    for k in feats:
        feats[k] = np.where(cnt > 0, feats[k], np.nan)

    sel = b90 | b30
    y = b90[sel]
    res = {"n_band90": int(b90.sum()), "n_band30": int(b30.sum()),
           "carrier_spacing": sp, "sigma": SIGMA, "views": "VAL", "auc": {}}
    print(f"\nAUC, positive class = band90 (n={int(b90.sum())}) vs band30 (n={int(b30.sum())})")
    for k in ("lam2", "harris", "teed", "teed_seedscore"):
        a = auc_mw(feats[k][sel], y)
        res["auc"][k] = a
        print(f"  {k:16s} AUC = {a:.4f}")

    ctrl = max(res["auc"]["teed"], res["auc"]["teed_seedscore"])
    jbest = max(res["auc"]["lam2"], res["auc"]["harris"])
    margin = jbest - ctrl
    if jbest >= 0.65 and margin >= 0.05:
        verdict = "GO"
    elif jbest <= 0.58 or margin < 0.05:
        verdict = "NO-GO"
    else:
        verdict = "MIDDLE"
    res.update({"best_J": jbest, "best_control": ctrl, "margin": margin,
                "verdict": verdict,
                "actionability": ("Even a GO is UNACTIONABLE under the frozen theta=30 oracle: "
                                  "tessellation edges are inside the GT crease set, so "
                                  "suppressing them lowers measured recall AND precision.")})
    print(f"\n  best J   = {jbest:.4f}   best control = {ctrl:.4f}   margin = {margin:+.4f}")
    print(f"VERDICT: {verdict}")
    json.dump(res, open(os.path.join(OUT, "a_reframed_tier0.json"), "w"), indent=2)
    print("wrote out/a_reframed_tier0.json")


if __name__ == "__main__":
    main()
