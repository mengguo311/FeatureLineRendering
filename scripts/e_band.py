#!/usr/bin/env python
"""E-BAND — per-dihedral-band miss decomposition on lego.

*** EVAL-ONLY DIAGNOSTIC. Reads the GT mesh only through the BANKED cache
    cache/dexp0_gt_lego_a30.npz (z-peeled visible crease points per TEST view) and the
    banked per-point dihedral out/xy/xy_expX_lego_p1c.npz. Builds nothing, changes no
    score, writes no linelet set. The shipped stroke sets are never touched. ***

Seed set (FIXED, pre-registered): TEED f=0.40 -- the Phase A standing point.
Population: visible GT crease POINTS on lego held-out TEST views (n = 1,748,144).

FRAME 1 (seed-level, LEGO_CEILING_AUTOPSY Fig B convention)
    UNCOVERED          no VISIBLE de-floatered carrier centre within tau=1.5 px
    COVERED-and-ranked a visible carrier within tau IS in the TEED f=0.40 seed set
    COVERED-but-culled a visible carrier within tau exists but is NOT a seed

FRAME 2 (output-level, CAP convention, computed on the MISSED subset)
    A   d_pool <= 1.5                      (candidate existed; pull+prune discarded it)
    B0  d_pool > 1.5 and d_raw <= 1.5      (removed by de-floatering)
    B1  d_pool > 1.5 and 1.5 < d_raw <= 3  (registration-recoverable)
    B2  d_pool > 1.5 and d_raw > 3         (true void)

NULL (mandatory): 20,000 uniform foreground pixels/view through the identical COVERED
test. CAP showed this test can be vacuous (0.729 missed vs 0.725 random).

CONVERSION: measured IN-RUN per band as realised / covered-and-ranked, rather than
importing the autopsy's global 0.912 (which was a different score and stage).
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

from src import common, visibility, view_split          # noqa: E402
from tune_lib import Harness                            # noqa: E402
from run_m1b import raster_segments                     # EVAL harness  # noqa: E402

OUT = os.path.join(TIER1, "out")
TAU = 1.5
B1_HI = 3.0
F_KEEP = 0.40
SCORE = os.path.join(TIER1, "scripts/explore/syn",
                     "finalscore_overall_lego__teed_native_0.5.npy")
LINELETS = os.path.join(OUT, "linelets_lego_tcteed040_test.npz")
BANDS = [("theta=30.000", 30.00, 30.05),
         ("30.05-60",     30.05, 60.00),
         ("60-89.95 CTRL", 60.00, 89.95),
         ("theta=90.000", 89.95, 90.05),
         (">=90.05",      90.05, 1e9)]
RNG = np.random.default_rng(0)
N_NULL = 20000


def proj_all(P, cam, margin=64.0):
    """Project every point; keep those in front of the camera and near the frame."""
    uv, z = common.project(P, cam)
    ok = (z > 1e-6) & (uv[:, 0] > -margin) & (uv[:, 0] < cam.W + margin) \
        & (uv[:, 1] > -margin) & (uv[:, 1] < cam.H + margin)
    return uv[ok]


def main():
    print("[E-BAND] loading banked GT cache + per-point dihedral", flush=True)
    gt = np.load(os.path.join(TIER1, "cache/dexp0_gt_lego_a30.npz"))
    n_pts = len(gt["crease_pts"])
    xz = np.load(os.path.join(OUT, "xy/xy_expX_lego_p1c.npz"))
    theta_full = np.full(n_pts, np.nan, np.float32)
    theta_full[xz["seen_idx"]] = xz["theta0_pt"]
    print(f"  crease_pts={n_pts}  seen_idx={len(xz['seen_idx'])}", flush=True)

    h = Harness("lego", views=view_split.TEST)
    X = h.X
    raw_mu = h.g["mu"]
    s = np.load(SCORE)
    assert len(s) == len(X), (len(s), len(X))
    o = np.argsort(-s, kind="stable")
    n_seed = int(round(F_KEEP * len(X)))
    seed_idx = np.sort(o[:n_seed])
    is_seed = np.zeros(len(X), bool); is_seed[seed_idx] = True
    print(f"  pool={len(X)} raw={len(raw_mu)} seeds={n_seed} (expect 39888)", flush=True)

    z = np.load(LINELETS)
    keep = z["keep"].astype(bool)
    lp, lt, ll = z["p"], z["t"], z["l"]
    print(f"  linelets spec keep={int(keep.sum())} (expect 35028)", flush=True)

    nb = len(BANDS)
    acc = {k: np.zeros(nb, np.int64) for k in
           ("n", "unc", "rank", "cull", "hit", "A", "B0", "B1", "B2", "miss")}
    null_cov = []; null_n = []
    theta_nan = 0

    for v in view_split.TEST:
        idx_v = gt[f"idx{v}"]; uv_v = gt[f"uv{v}"]
        th = theta_full[idx_v]
        theta_nan += int(np.isnan(th).sum())
        cam = h.cams[v]
        vis, uvg, _ = visibility.visible_mask(X, cam, h.gbufs[v]["depth"])
        car = uvg[vis]; sed = uvg[vis & is_seed]
        d_car = cKDTree(car).query(uv_v, workers=-1)[0] if len(car) else np.full(len(uv_v), 1e9)
        d_sed = cKDTree(sed).query(uv_v, workers=-1)[0] if len(sed) else np.full(len(uv_v), 1e9)
        unc = d_car > TAU
        rank = (~unc) & (d_sed <= TAU)
        cull = (~unc) & (d_sed > TAU)

        mask, _ = raster_segments(h, v, lp, lt, ll, keep=keep)
        sdt = (cv2.distanceTransform((~mask).astype(np.uint8), cv2.DIST_L2, 5)
               if mask.any() else np.full(mask.shape, 1e9, np.float32))
        uu = np.clip(np.round(uv_v[:, 0]).astype(int), 0, cam.W - 1)
        vv = np.clip(np.round(uv_v[:, 1]).astype(int), 0, cam.H - 1)
        hit = sdt[vv, uu] <= TAU
        miss = ~hit

        uvp = proj_all(X, cam); uvr = proj_all(raw_mu, cam)
        d_pool = cKDTree(uvp).query(uv_v, workers=-1)[0]
        d_raw = cKDTree(uvr).query(uv_v, workers=-1)[0]
        cA = d_pool <= TAU
        cB0 = (~cA) & (d_raw <= TAU)
        cB1 = (~cA) & (d_raw > TAU) & (d_raw <= B1_HI)
        cB2 = (~cA) & (d_raw > B1_HI)

        for bi, (_, lo, hi) in enumerate(BANDS):
            m = (th >= lo) & (th < hi)
            if not m.any():
                continue
            acc["n"][bi] += int(m.sum())
            acc["unc"][bi] += int((m & unc).sum())
            acc["rank"][bi] += int((m & rank).sum())
            acc["cull"][bi] += int((m & cull).sum())
            acc["hit"][bi] += int((m & hit).sum())
            mm = m & miss
            acc["miss"][bi] += int(mm.sum())
            acc["A"][bi] += int((mm & cA).sum())
            acc["B0"][bi] += int((mm & cB0).sum())
            acc["B1"][bi] += int((mm & cB1).sum())
            acc["B2"][bi] += int((mm & cB2).sum())

        # ---- null: uniform foreground pixels through the identical COVERED test
        im = cv2.imread(h.rgb_paths[v], cv2.IMREAD_UNCHANGED)
        fg = (im[:, :, 3].astype(np.float32) / 255.0) > 0.5
        fy, fx = np.nonzero(fg)
        pick = RNG.choice(len(fy), size=min(N_NULL, len(fy)), replace=False)
        nuv = np.stack([fx[pick].astype(np.float64), fy[pick].astype(np.float64)], 1)
        dn = cKDTree(car).query(nuv, workers=-1)[0] if len(car) else np.full(len(nuv), 1e9)
        null_cov.append(int((dn <= TAU).sum())); null_n.append(len(nuv))
        print(f"  view {v:3d}: n={len(uv_v):7d}  unc={unc.mean():.4f} "
              f"rank={rank.mean():.4f} cull={cull.mean():.4f} hit={hit.mean():.4f} "
              f"null_cov={(dn<=TAU).mean():.4f}", flush=True)

    res = {"seed_set": "TEED f=0.40", "n_seed": n_seed, "spec_keep": int(keep.sum()),
           "tau_px": TAU, "views": list(map(int, view_split.TEST)),
           "theta_nan": theta_nan,
           "null_covered_rate": float(sum(null_cov) / sum(null_n)),
           "bands": {}}
    tot = {k: int(acc[k].sum()) for k in acc}
    res["global"] = {k: tot[k] for k in tot}
    res["global"]["uncovered"] = tot["unc"] / tot["n"]
    res["global"]["culled"] = tot["cull"] / tot["n"]
    res["global"]["ranked"] = tot["rank"] / tot["n"]
    res["global"]["realised"] = tot["hit"] / tot["n"]
    res["global"]["conversion"] = tot["hit"] / max(tot["rank"], 1)

    for bi, (nm, lo, hi) in enumerate(BANDS):
        n = int(acc["n"][bi])
        if n == 0:
            continue
        mi = max(int(acc["miss"][bi]), 1)
        res["bands"][nm] = {
            "theta_lo": lo, "theta_hi": hi, "n": n, "share_of_all": n / tot["n"],
            "UNCOVERED": int(acc["unc"][bi]) / n,
            "COVERED_ranked": int(acc["rank"][bi]) / n,
            "COVERED_culled": int(acc["cull"][bi]) / n,
            "realised_R": int(acc["hit"][bi]) / n,
            "conversion": int(acc["hit"][bi]) / max(int(acc["rank"][bi]), 1),
            "n_missed": int(acc["miss"][bi]),
            "share_of_missset": int(acc["miss"][bi]) / max(tot["miss"], 1),
            "capA": int(acc["A"][bi]) / mi, "capB0": int(acc["B0"][bi]) / mi,
            "capB1": int(acc["B1"][bi]) / mi, "capB2": int(acc["B2"][bi]) / mi,
            "rho_B2": int(acc["B2"][bi]) / max(int(acc["B1"][bi]) + int(acc["B2"][bi]), 1),
        }

    # free banked read: carrier-persistence ablation
    try:
        ab = json.load(open(os.path.join(OUT, "m1b_stroke_temporal_table_abl_carrier_persistence.json")))
        k = "scenes" if "scenes" in ab else "headline"
        res["carrier_persistence_ablation"] = {
            s: {"variant": r.get("variant"), "chain": r.get("chain"),
                "f240": r["by_frames"].get("240")} for s, r in ab[k].items()}
    except Exception as e:
        res["carrier_persistence_ablation"] = f"unavailable: {e}"

    with open(os.path.join(OUT, "e_band_lego.json"), "w") as fh:
        json.dump(res, fh, indent=2)
    print("\nwrote out/e_band_lego.json", flush=True)

    print(f"\nGLOBAL n={tot['n']} unc={res['global']['uncovered']:.4f} "
          f"cull={res['global']['culled']:.4f} rank={res['global']['ranked']:.4f} "
          f"realised={res['global']['realised']:.4f} conv={res['global']['conversion']:.4f}")
    print(f"NULL covered rate = {res['null_covered_rate']:.4f}\n")
    print(f"{'band':16s} {'n':>9s} {'share':>6s} | {'UNCOV':>7s} {'CULL':>7s} {'RANK':>7s} "
          f"{'realR':>7s} {'conv':>6s} | {'A':>6s} {'B0':>6s} {'B1':>6s} {'B2':>6s} {'rhoB2':>6s}")
    for nm, d in res["bands"].items():
        print(f"{nm:16s} {d['n']:9d} {d['share_of_all']:6.3f} | {d['UNCOVERED']:7.4f} "
              f"{d['COVERED_culled']:7.4f} {d['COVERED_ranked']:7.4f} {d['realised_R']:7.4f} "
              f"{d['conversion']:6.3f} | {d['capA']:6.3f} {d['capB0']:6.3f} {d['capB1']:6.3f} "
              f"{d['capB2']:6.3f} {d['rho_B2']:6.3f}")


if __name__ == "__main__":
    main()
