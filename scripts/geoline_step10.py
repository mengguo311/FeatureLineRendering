"""tier1/scripts/geoline_step10.py — STEP 10: comparability transforms, deliverable metric.

Executes out/GEOLINE_STEP10_SPEC.md exactly.  *** MESH EVAL-ONLY: the GT mesh supplies the
oracle labels and scores rendered segments.  BOTH transforms are mesh-free. ***

Stage 1 (label space) is a DIAGNOSTIC ONLY and gates nothing -- amendment accepted before
execution, because a label-space screen could false-kill a transform whose deliverable
intervals do intersect (the Step-2-to-Step-3 precedent).
"""
import argparse
import json
import os
import sys

import numpy as np
from scipy.spatial import cKDTree

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
sys.path.insert(0, os.path.join(TIER1, "scripts/explore/syn"))

from src import common, visibility, view_split                          # noqa: E402
import diag2dgs                                                         # noqa: E402
import run_m1b                                                          # noqa: E402

OUT = os.path.join(TIER1, "out")
POOLS = {"gcube": "_step4", "cadpartA": "_step3pool", "gprism": "_step4",
         "gicosa": "_step4", "gstep": "_step4"}
SOLIDS = ["gcube", "cadpartA", "gprism", "gicosa", "gstep"]
Z_WILSON = 1.2816          # frozen, 90% one-sided
DELTA_MAX_PX = 5.0         # the pull's capture radius
N_DECILE = 10              # frozen
MIN_VIEWS = 3
BAR_R, BAR_P = 0.35, 0.70
KF = [0.98, 0.94, 0.9, 0.85, 0.8, 0.7, 0.6, 0.55, 0.5, 0.45, 0.4, 0.35, 0.32,
      0.30, 0.28, 0.26, 0.24, 0.22, 0.20, 0.18, 0.15, 0.12, 0.10, 0.07, 0.04]
RAW_AUC = {"gcube": 0.9404, "cadpartA": 0.9019, "gprism": 0.8948, "gicosa": 0.8219}


def wilson_lb(k, n, z=Z_WILSON):
    n = np.maximum(n, 1).astype(np.float64)
    p = np.clip(k / n, 0.0, 1.0)
    den = 1.0 + z * z / n
    ctr = (p + z * z / (2 * n)) / den
    hw = (z / den) * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return np.maximum(0.0, ctr - hw)


def crowding(P, scene):
    """Mesh-free, pixel-anchored: count of OTHER candidates within 5 px worth of world
    radius at the candidate's median TRAIN-camera depth.  Pure projection, no rendering."""
    cams, _ = common.load_cameras(scene)
    tv = list(view_split.TRAIN)
    zs = []
    for v in tv:
        c = cams[v]
        zc = (c.w2c[:3, :3] @ P.T).T[:, 2] + c.w2c[2, 3]
        zs.append(np.where(zc > 1e-6, zc, np.nan))
    zmed = np.nanmedian(np.stack(zs, 1), axis=1)
    zmed = np.where(np.isfinite(zmed), zmed, np.nanmedian(zmed))
    f = cams[0].K[0, 0]
    r = DELTA_MAX_PX * zmed / f
    tree = cKDTree(P)
    return np.array([len(b) - 1 for b in tree.query_ball_point(P, r, workers=-1)],
                    np.float64), float(np.median(r))


def decile_centre(x, c):
    """x minus the mean of x within the candidate's own crowding decile."""
    out = np.array(x, np.float64, copy=True)
    q = np.quantile(c, np.linspace(0, 1, N_DECILE + 1))
    q[0] -= 1e-9; q[-1] += 1e-9
    b = np.clip(np.digitize(c, q[1:-1]), 0, N_DECILE - 1)
    for d in range(N_DECILE):
        m = b == d
        if m.sum() >= 2:
            out[m] = x[m] - x[m].mean()
    return out


def youden(x, good, bad):
    s = np.concatenate([x[good], x[bad]])
    lab = np.concatenate([np.ones(int(good.sum()), bool), np.zeros(int(bad.sum()), bool)])
    ts = np.quantile(s, np.linspace(0.01, 0.99, 199))
    best, bt = -2.0, float("nan")
    for t in ts:
        tpr = (s[lab] >= t).mean(); fpr = (s[~lab] >= t).mean()
        if tpr - fpr > best:
            best, bt = tpr - fpr, float(t)
    return bt, float(best)


def interval(front, br=BAR_R, bp=BAR_P):
    f = sorted(front, key=lambda r: r["tau"])
    t = np.array([r["tau"] for r in f])
    if len(t) < 2:
        return None
    g = np.linspace(t.min(), t.max(), 4001)
    P = np.interp(g, t, [r["P1.5"] for r in f])
    R = np.interp(g, t, [r["R1.5"] for r in f])
    m = (P >= bp) & (R >= br)
    return (float(g[m].min()), float(g[m].max())) if m.any() else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--solids", nargs="+", default=SOLIDS)
    args = ap.parse_args()
    from tune_lib import Harness                                        # EVAL ONLY (mesh)

    res = {"spec": "out/GEOLINE_STEP10_SPEC.md", "z_wilson": Z_WILSON,
           "bars": {"R": BAR_R, "P": BAR_P, "auc_guard": 0.02},
           "mesh_eval_only": "labels + segment scoring only; both transforms are mesh-free",
           "solids": {}}

    for s in args.solids:
        z = np.load(os.path.join(OUT, f"linelets_{s}{POOLS[s]}.npz"))
        P, T, L, ir, nv = z["p"], z["t"], z["l"], z["inlier_ratio"], z["n_vis"]
        h = Harness(s, views=tuple(view_split.TEST))

        # oracle labels (mesh, eval-only), the Step-1/2/5 convention
        acc = [[] for _ in range(len(P))]
        for v in view_split.TEST:
            vis, uv, _ = visibility.visible_mask(P, h.cams[v], h.gbufs[v]["depth"])
            _, _, cdt = h.crease[v]
            u = np.clip(np.round(uv[:, 0]).astype(int), 0, cdt.shape[1] - 1)
            w = np.clip(np.round(uv[:, 1]).astype(int), 0, cdt.shape[0] - 1)
            d = cdt[w, u]
            for i in np.where(vis)[0]:
                acc[i].append(d[i])
        dm = np.array([np.median(a) if a else np.inf for a in acc])
        seen = np.array([len(a) > 0 for a in acc])
        good, bad = seen & (dm <= 1.5), seen & (dm > 3.0)

        k = np.round(ir * nv)
        cr, rmed = crowding(P, s)
        X = {"raw": np.asarray(ir, np.float64),
             "D_wilson": wilson_lb(k, nv),
             "A_crowd": decile_centre(np.asarray(ir, np.float64), cr)}
        base = nv >= MIN_VIEWS

        row = {"n_pool": int(len(P)), "n_good": int(good.sum()), "n_bad": int(bad.sum()),
               "median_n_vis": float(np.median(nv)), "median_crowd": float(np.median(cr)),
               "median_capture_radius_world": rmed, "transforms": {}}
        print(f"\n[{s}] pool {len(P)}  good/bad {int(good.sum())}/{int(bad.sum())}  "
              f"median n_vis {np.median(nv):.0f}  median crowding {np.median(cr):.1f}  "
              f"r_med {rmed:.5f}", flush=True)

        for nm, x in X.items():
            lab = np.concatenate([np.ones(int(good.sum()), bool),
                                  np.zeros(int(bad.sum()), bool)])
            auc = diag2dgs.auc(np.concatenate([x[good], x[bad]]), lab)
            yt, yj = youden(x, good, bad)
            front = []
            for kf in KF:
                tau = float(np.quantile(x, 1.0 - kf))
                kk = base & (x >= tau)
                if kk.sum() < 10:
                    continue
                e = run_m1b.eval_segments(h, P, T, L, keep=kk, taus=(1.5,))
                front.append({"kf": kf, "tau": tau, "n": int(kk.sum()),
                              "P1.5": e[1.5][0], "R1.5": e[1.5][1]})
            iv = interval(front)
            row["transforms"][nm] = {"AUC": float(auc), "youden_tau": yt, "youden_J": yj,
                                     "frontier": front, "admissible_interval": iv}
            print(f"  {nm:9s} AUC {auc:.4f}  youden_tau {yt:+.4f}  "
                  f"interval " + (f"[{iv[0]:.4f}, {iv[1]:.4f}]" if iv else "EMPTY"),
                  flush=True)
        res["solids"][s] = row
        del h

    # ---- verdict per transform ---------------------------------------------------------
    res["verdict"] = {}
    for nm in ("raw", "D_wilson", "A_crowd"):
        ivs = {s: res["solids"][s]["transforms"][nm]["admissible_interval"]
               for s in args.solids}
        if any(v is None for v in ivs.values()):
            res["verdict"][nm] = {"GO": False, "reason": "a solid has an EMPTY interval",
                                  "intervals": ivs}
            print(f"\n  {nm}: NO-GO (empty interval on "
                  f"{[s for s, v in ivs.items() if v is None]})")
            continue
        lo = max(v[0] for v in ivs.values()); hi = min(v[1] for v in ivs.values())
        gap = float(lo - hi)
        aucs = {s: res["solids"][s]["transforms"][nm]["AUC"] for s in args.solids}
        raw_auc = {s: res["solids"][s]["transforms"]["raw"]["AUC"] for s in args.solids}
        guard = {s: float(aucs[s] - raw_auc[s]) for s in args.solids}
        guard_ok = all(v >= -0.02 for v in guard.values())
        v = {"intervals": ivs, "intersection": [lo, hi], "non_empty": bool(lo <= hi),
             "gap": gap, "AUC": aucs, "AUC_delta_vs_raw": guard,
             "AUC_guard_pass": bool(guard_ok)}
        if lo <= hi:
            mid = 0.5 * (lo + hi)
            cells = {}
            allok = True
            for s in args.solids:
                zz = np.load(os.path.join(OUT, f"linelets_{s}{POOLS[s]}.npz"))
                hh = Harness(s, views=tuple(view_split.TEST))
                Pp, Tt, Ll, irr, nvv = (zz["p"], zz["t"], zz["l"],
                                        zz["inlier_ratio"], zz["n_vis"])
                xx = {"raw": np.asarray(irr, np.float64),
                      "D_wilson": wilson_lb(np.round(irr * nvv), nvv),
                      "A_crowd": decile_centre(np.asarray(irr, np.float64),
                                               crowding(Pp, s)[0])}[nm]
                kk = (nvv >= MIN_VIEWS) & (xx >= mid)
                e = run_m1b.eval_segments(hh, Pp, Tt, Ll, keep=kk, taus=(1.5,))
                cells[s] = {"P1.5": e[1.5][0], "R1.5": e[1.5][1], "n": int(kk.sum())}
                if not (e[1.5][1] >= BAR_R and e[1.5][0] >= BAR_P):
                    allok = False
                del hh
            v["midpoint"] = mid
            v["midpoint_cells"] = cells
            v["midpoint_all_clear"] = bool(allok)
            v["GO"] = bool(allok and guard_ok)
        else:
            v["GO"] = False
        res["verdict"][nm] = v
        print(f"\n  {nm}: intersection [{lo:.4f}, {hi:.4f}] "
              f"{'NON-EMPTY' if lo <= hi else 'EMPTY'}  gap {gap:+.4f}  "
              f"AUC guard {'PASS' if guard_ok else 'FAIL'}  -> "
              f"{'GO' if v.get('GO') else 'NO-GO'}", flush=True)

    p = os.path.join(OUT, "geoline_step10.json")
    json.dump(res, open(p, "w"), indent=1)
    print(f"\n  -> {p}", flush=True)


if __name__ == "__main__":
    main()
