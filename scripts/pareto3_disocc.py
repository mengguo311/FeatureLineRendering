"""PARETO-3 — disocclusion decomposition of the accumulated-baseline residual
(pareto3_disocc_spec.md).

*** EVAL / ANALYSIS. NO mesh anywhere in this script — the disocclusion mask uses only the
    rendered depth + camera poses (method-path-clean geometry); precision numbers are quoted
    from out/pareto2_lego_T3_spline.json, not recomputed. ***

FIXED OPERATING POINT (the PARETO-2 1.72x cell, frozen by the three-way):
  scene=lego, traj=T3_spline, 240 frames
  baseline = CANNY 50/150 @ alpha=0.85 (oracle-flow EMA, occlusion-aware)  pop>2px 0.05952
  OURS     = f=0.22 (the unique row with P >= baseline and px <= baseline) pop>2px 0.03462
  advantage 1.719x -- the number being decomposed.

DECOMPOSITION. For every pooled warped line pixel (frame-t ON pixel, finite depth,
warp lands in frame -- the exact population PARETO-2's pop-rate was computed on):
  DISOCC  iff the landing pixel is outside frame-(t+1)'s eroded interior, OR the warped
          depth z1 exceeds frame-(t+1)'s rendered depth at the landing pixel by more than
          EPS (the surface seen at t is occluded at t+1 -- its correspondence is gone).
  INTERIOR otherwise.
  EPS is FROZEN A PRIORI = 2% of the median finite scene depth over the trajectory,
  computed and printed BEFORE any tally.
Tally per method: fraction of pop>2px pixels in each class AND per-class pop RATES.
Consistency check: the recomputed overall pop>2px must match the PARETO-2 json.

FROZEN GATE: GO >= 60% of the BASELINE's pop>2px pixels lie in DISOCC; NO-GO < 40%;
GRAY 40-60%.
"""
import os
import sys
import json
import time

import cv2
import numpy as np
import torch

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
for p in (TIER1, os.path.join(TIER1, "scripts"), os.path.join(TIER1, "scripts/explore"),
          os.path.join(TIER1, "scripts/explore/syn")):
    sys.path.insert(0, p)
OUT = os.path.join(TIER1, "out")

from src import common, render, strokes                              # noqa: E402
import track_o_temporal as TO                                        # noqa: E402
import pareto_coherence as P1                                        # noqa: E402
import pareto2_flowacc as P2                                         # noqa: E402

SCENE, TNAME, NF = "lego", "T3_spline", 240
BASE_NAME, OURS_F = "CANNY 50/150 a=0.85", "0.22"
CANNY_LO, CANNY_HI, ALPHA = 50, 150, 0.85
POP_T = 2.0


def warp_with_depth(mask, fb0, cam0, cam1):
    """P1.warp_pixels + the warped camera-space depth z1 (needed for the occlusion test).
    Returns (uv int [M,2] in-frame, z1 [M], n_total_finite, n_oob)."""
    vv, uu = np.nonzero(mask)
    z = fb0["depth"][vv, uu]
    ok = np.isfinite(z) & (z > 1e-6) & (z < 1e8)
    u = uu[ok].astype(np.float64)
    v_ = vv[ok].astype(np.float64)
    zk = z[ok].astype(np.float64)
    f, cx, cy = cam0.f, cam0.K[0, 2], cam0.K[1, 2]
    Xc = np.stack([zk * (u - cx) / f, zk * (v_ - cy) / f, zk], 1)
    R0, t0 = cam0.w2c[:3, :3], cam0.w2c[:3, 3]
    Xw = (Xc - t0) @ R0
    Xc1 = (cam1.w2c[:3, :3] @ Xw.T).T + cam1.w2c[:3, 3]
    z1 = Xc1[:, 2]
    u1 = cam1.f * Xc1[:, 0] / np.clip(z1, 1e-9, None) + cam1.K[0, 2]
    v1 = cam1.f * Xc1[:, 1] / np.clip(z1, 1e-9, None) + cam1.K[1, 2]
    inb = (z1 > 1e-6) & (u1 >= 0) & (u1 < cam1.W - 0.5) & (v1 >= 0) & (v1 < cam1.H - 0.5)
    w = np.stack([np.round(u1[inb]), np.round(v1[inb])], 1).astype(np.int64)
    return w, z1[inb], int(ok.sum()), int(ok.sum() - inb.sum())


def main():
    t00 = time.time()
    cams, _ = common.load_cameras(SCENE)
    g = common.load_gaussians(SCENE)
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    target = np.median(g["mu"][keep_g], axis=0)
    traj = TO.traj_spline(cams, target, NF)
    print(f"[p3] {SCENE} {TNAME} {NF}f — decomposing '{BASE_NAME}' vs OURS f={OURS_F}",
          flush=True)

    fbs = []
    dsamp = []
    for i, cam in enumerate(traj):
        fb = P1.frame_buffers(g, keep_g, cam)
        fbs.append(fb)
        d = fb["depth"]
        dsamp.append(d[np.isfinite(d)][::37])
        if i % 80 == 0:
            print(f"  frame {i}/{NF} ({time.time()-t00:.0f}s)", flush=True)

    # ---- FREEZE epsilon BEFORE any tally
    med_depth = float(np.median(np.concatenate(dsamp)))
    EPS = 0.02 * med_depth
    print(f"[p3] FROZEN: median scene depth {med_depth:.4f} -> EPS = 2% = {EPS:.4f} "
          f"(pop threshold {POP_T} px)", flush=True)

    # ---- the two fixed line-mask sequences (exact PARETO-2 constructions)
    z = np.load(os.path.join(OUT, f"linelets_{SCENE}_tc_teed_native_0.5_f{OURS_F}.npz"))
    keep = z["keep"].astype(bool)
    p, t_, l = z["p"][keep], z["t"][keep], z["l"][keep]
    ch, kept = strokes.chain_linelets_3d(p, t_, l, conf=z["inlier_ratio"][keep],
                                         **P1.CHAIN_KW)
    P3 = p[kept]
    chain3d = [P3[c] for c in ch]
    cat = (np.concatenate(chain3d, 0), np.cumsum([0] + [len(c) for c in chain3d]))
    ours = [P1.ours_mask(chain3d, traj[i], fbs[i], _cat=cat)[0] for i in range(NF)]
    E = [P1.canny_mask(fb, CANNY_LO, CANNY_HI) for fb in fbs]
    base, disf, ghost = P2.accumulate_masks(E, fbs, traj, ALPHA)
    print(f"[p3] masks ready ({time.time()-t00:.0f}s)  baseline disocc_frac {disf:.4f} "
          f"ghost {ghost:.4f}", flush=True)

    # ---- tally
    res = {}
    best_overlay = (-1, None)
    for name, masks in (("baseline", base), ("ours", ours)):
        n = {k: 0 for k in ("pool", "pop", "disocc", "interior",
                            "pop_disocc", "pop_interior", "oob")}
        for t in range(NF - 1):
            L0, L1 = masks[t], masks[t + 1]
            if not L0.any() or not L1.any():
                continue
            dt1 = cv2.distanceTransform((~L1).astype(np.uint8), cv2.DIST_L2, 5)
            w, z1, n_fin, n_oob = warp_with_depth(L0, fbs[t], traj[t], traj[t + 1])
            n["oob"] += n_oob
            if not len(w):
                continue
            d_land = fbs[t + 1]["depth"][w[:, 1], w[:, 0]]
            off_int = ~fbs[t + 1]["fg"][w[:, 1], w[:, 0]]
            occl = np.isfinite(d_land) & (z1 > d_land + EPS)
            no_depth = ~np.isfinite(d_land)                  # landed on empty background
            dis = off_int | occl | no_depth
            pop = dt1[w[:, 1], w[:, 0]] > POP_T
            n["pool"] += len(w)
            n["pop"] += int(pop.sum())
            n["disocc"] += int(dis.sum())
            n["interior"] += int((~dis).sum())
            n["pop_disocc"] += int((pop & dis).sum())
            n["pop_interior"] += int((pop & ~dis).sum())
            if name == "baseline" and int((pop & dis).sum()) > best_overlay[0]:
                best_overlay = (int((pop & dis).sum()),
                                (t, w.copy(), pop.copy(), dis.copy()))
        r = {
            "n_pooled_px": n["pool"], "n_oob_dropped": n["oob"],
            "pop_gt2px_overall": n["pop"] / max(n["pool"], 1),
            "n_pop": n["pop"],
            "frac_px_disocc": n["disocc"] / max(n["pool"], 1),
            "frac_POP_in_disocc": n["pop_disocc"] / max(n["pop"], 1),
            "frac_POP_in_interior": n["pop_interior"] / max(n["pop"], 1),
            "pop_RATE_disocc": n["pop_disocc"] / max(n["disocc"], 1),
            "pop_RATE_interior": n["pop_interior"] / max(n["interior"], 1),
        }
        res[name] = r
        print(f"\n  [{name}] pooled {n['pool']}  pop>2 {r['pop_gt2px_overall']:.4f} "
              f"(json check: 0.0595 base / 0.0346 ours)")
        print(f"    px in disocc {r['frac_px_disocc']:.4f} | POP in disocc "
              f"{r['frac_POP_in_disocc']:.4f} | RATE disocc {r['pop_RATE_disocc']:.4f} "
              f"vs interior {r['pop_RATE_interior']:.4f}", flush=True)

    frac = res["baseline"]["frac_POP_in_disocc"]
    verdict = "GO" if frac >= 0.60 else ("NO-GO" if frac < 0.40 else "GRAY")
    out = {"scene": SCENE, "traj": TNAME, "frames": NF,
           "operating_point": {"baseline": BASE_NAME, "ours": f"OURS f={OURS_F}",
                               "advantage_pop2": 1.719},
           "frozen": {"eps": EPS, "eps_rule": "2% of median finite scene depth",
                      "median_scene_depth": med_depth, "pop_threshold_px": POP_T},
           "baseline": res["baseline"], "ours": res["ours"],
           "gate": {"frac_baseline_pop_in_disocc": frac,
                    "GO>=": 0.60, "NO-GO<": 0.40, "verdict": verdict}}
    jp = os.path.join(OUT, "pareto3_lego_T3_disocc.json")
    json.dump(out, open(jp, "w"), indent=2)
    print(f"\nFROZEN GATE: baseline pop-in-disocc fraction {frac:.4f} -> {verdict}")
    print(f"wrote {jp}  ({time.time()-t00:.0f}s)")

    # ---- overlay
    if best_overlay[1] is not None:
        t, w, pop, dis = best_overlay[1]
        img = cv2.cvtColor(fbs[t + 1]["gray"], cv2.COLOR_GRAY2BGR)
        img = (img * 0.55).astype(np.uint8)
        band = (~fbs[t + 1]["fg"])
        img[..., 0] = np.where(band, np.minimum(img[..., 0] + 40, 255), img[..., 0])
        for m, col in (((pop & ~dis), (0, 165, 255)),        # interior pop = orange
                       ((pop & dis), (0, 0, 255))):          # disocc pop = red
            img[w[m, 1], w[m, 0]] = col
        cv2.putText(img, f"baseline pop>2px @ transition {t}->{t+1}: "
                    f"RED=disocclusion  ORANGE=interior", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        po = os.path.join(OUT, "pareto3_disocc_overlay.png")
        cv2.imwrite(po, img)
        print(f"wrote {po}")


if __name__ == "__main__":
    main()
