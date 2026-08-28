#!/usr/bin/env python
"""CONDLAW — ADVERSARIAL probe: give lego every chance to beat DRR@80 = 0.55.

The frozen gate NO-GOs if lego's DRR@80 > 0.55.  Reporting a single statistic that
happens to be at chance is weak evidence for a ceiling claim.  This script actively
TRIES to break the ceiling, using strictly more than the headline statistic:

  A. each single GT-mesh statistic, best orientation (upper bound)
  B. a 2-feature and a 4-feature LEARNED combiner (logistic regression on rank-normalised
     features) FIT ON VAL, evaluated on TEST -- multivariate geometry, not one scalar
  C. the stricter TEED-confidence definitions of the distractor class
  D. the flattest-available decal subsets (the chair-like "flat printed" class, if any)

If none of these clears 0.55, the ceiling is not an artefact of statistic choice.
"""
import json
import numpy as np
from condlaw_drr import drr_at_recall, auc_mw

TEST = "out/diag2dgs_lego_test.npz"
VAL = "out/diag2dgs_lego_val_sweep.npz"
MESH = ["mesh3d_rho4_xi0.25_nmin5", "spreadmesh_rho4_xi0.25_nmin5"]
ALL4 = MESH + ["surfel3d_rho4_xi0.25_nmin5", "spread2dgs_rho4_xi0.25_nmin5"]


def sel(z, keys):
    m = z["seen"].astype(bool)
    for k in keys:
        m &= z[f"ok_{k}"].astype(bool) & np.isfinite(z[k])
    return (z["crease"].astype(bool) & m), (z["decal"].astype(bool) & m)


def ranknorm(x, ref):
    """map x into [0,1] by its rank within ref (fit on VAL, applied to TEST)."""
    r = np.searchsorted(np.sort(ref), x, side="left") / max(len(ref), 1)
    return np.clip(r, 0.0, 1.0)


def logistic_fit(X, y, iters=400, lr=0.5):
    X = np.c_[X, np.ones(len(X))]
    w = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1.0 / (1.0 + np.exp(-X @ w))
        g = X.T @ (y.astype(float) - p) / len(X)
        w += lr * g
    return w


def apply_w(X, w):
    return np.c_[X, np.ones(len(X))] @ w


if __name__ == "__main__":
    zt = np.load(TEST, allow_pickle=True)
    zv = np.load(VAL, allow_pickle=True)
    res, T = {}, 0.80
    print("\nLEGO adversarial probe — every attempt to exceed DRR@80 = 0.55 (TEST split)")
    print(f"{'attempt':<58} {'AUC':>7} {'DRR@80':>8} {'n_cre':>7} {'n_dec':>7}")
    print("-" * 92)

    # ---- A. single statistics, best (TEST-oracle) orientation -----------------------
    for k in ALL4:
        c, d = sel(zt, [k])
        sc, sd = zt[k][c], zt[k][d]
        A = auc_mw(np.r_[sc, sd], np.r_[np.ones(len(sc), bool), np.zeros(len(sd), bool)])
        s = 1 if A >= 0.5 else -1
        r = drr_at_recall(s * sc, s * sd, T)
        res[f"A|{k}"] = dict(auc=A, sign=s, drr=r["drr"], n_cre=r["n_cre"], n_dec=r["n_dec"])
        print(f"{'A single (best sign): ' + k:<58} {A:7.4f} {r['drr']:8.4f} "
              f"{r['n_cre']:7d} {r['n_dec']:7d}")

    # ---- B. learned multivariate combiner, FIT ON VAL, evaluated on TEST ------------
    for name, keys in (("mesh 2-feature", MESH), ("all 4-feature", ALL4)):
        kk = [k for k in keys if k in zv.files and k in zt.files]
        if len(kk) < len(keys):
            print(f"{'B combiner ' + name:<58} {'SKIP (feature absent in VAL)':>7}")
            continue
        cv, dv = sel(zv, kk)
        ct, dt = sel(zt, kk)
        refs = [np.r_[zv[k][cv], zv[k][dv]] for k in kk]
        Xv = np.column_stack([ranknorm(np.r_[zv[k][cv], zv[k][dv]], refs[i])
                              for i, k in enumerate(kk)])
        yv = np.r_[np.ones(int(cv.sum()), bool), np.zeros(int(dv.sum()), bool)]
        w = logistic_fit(Xv, yv)
        Xt = np.column_stack([ranknorm(np.r_[zt[k][ct], zt[k][dt]], refs[i])
                              for i, k in enumerate(kk)])
        st = apply_w(Xt, w)
        n1 = int(ct.sum())
        sc, sd = st[:n1], st[n1:]
        A = auc_mw(np.r_[sc, sd], np.r_[np.ones(len(sc), bool), np.zeros(len(sd), bool)])
        s = 1 if A >= 0.5 else -1
        r = drr_at_recall(s * sc, s * sd, T)
        res[f"B|{name}"] = dict(auc=A, sign=s, drr=r["drr"], w=w.tolist(),
                                n_cre=r["n_cre"], n_dec=r["n_dec"])
        print(f"{'B combiner (VAL-fit -> TEST): ' + name:<58} {A:7.4f} {r['drr']:8.4f} "
              f"{r['n_cre']:7d} {r['n_dec']:7d}")

    # ---- C. stricter TEED-confidence distractor definitions --------------------------
    dmed, teed = zt["dmed"], zt["teed_hi"].astype(bool)
    seen = zt["seen"].astype(bool)
    for lbl, dd in (("TEED frozen >=0.5", seen & (dmed > 3.0) & teed),):
        for k in MESH:
            ok = zt[f"ok_{k}"].astype(bool)
            c = zt["crease"].astype(bool) & seen & ok
            d = dd & ok
            sc, sd = zt[k][c], zt[k][d]
            A = auc_mw(np.r_[sc, sd], np.r_[np.ones(len(sc), bool), np.zeros(len(sd), bool)])
            s = 1 if A >= 0.5 else -1
            r = drr_at_recall(s * sc, s * sd, T)
            res[f"C|{lbl}|{k}"] = dict(auc=A, sign=s, drr=r["drr"],
                                       n_cre=r["n_cre"], n_dec=r["n_dec"])
            print(f"{'C ' + lbl + ' : ' + k.split('_rho')[0]:<58} {A:7.4f} {r['drr']:8.4f} "
                  f"{r['n_cre']:7d} {r['n_dec']:7d}")

    # ---- D. flattest-available decals (the chair-like 'flat printed' class) ----------
    ks = "spreadmesh_rho4_xi0.25_nmin5"
    okm = zt[f"ok_{ks}"].astype(bool)
    c0 = zt["crease"].astype(bool) & seen & okm
    d0 = zt["decal"].astype(bool) & seen & okm
    v = zt[ks]
    for q in (0.10, 0.25, 0.50):
        thr = np.quantile(v[d0], q)
        d = d0 & (v <= thr)
        for k in MESH:
            ok2 = zt[f"ok_{k}"].astype(bool)
            cc, ddm = c0 & ok2, d & ok2
            if ddm.sum() < 20:
                continue
            sc, sd = zt[k][cc], zt[k][ddm]
            A = auc_mw(np.r_[sc, sd], np.r_[np.ones(len(sc), bool), np.zeros(len(sd), bool)])
            s = 1 if A >= 0.5 else -1
            r = drr_at_recall(s * sc, s * sd, T)
            circ = (k == ks)      # selected BY this feature and scored WITH it
            res[f"D|q{q}|{k}"] = dict(auc=A, sign=s, drr=r["drr"], spread_thr=float(thr),
                                      circular=circ, n_cre=r["n_cre"], n_dec=r["n_dec"])
            note = "  <-- CIRCULAR (subset defined by this same feature); excluded" if circ else ""
            print(f"{f'D flattest {int(q*100)}% decals (spread<={thr:.1f}deg): ' + k.split('_rho')[0]:<58} "
                  f"{A:7.4f} {r['drr']:8.4f} {r['n_cre']:7d} {r['n_dec']:7d}{note}")

    valid = {k: r for k, r in res.items()
             if np.isfinite(r["drr"]) and not r.get("circular", False)}
    best = max((r["drr"] for r in valid.values()), default=float("nan"))
    bk = [k for k, r in valid.items() if r["drr"] == best]
    print("-" * 92)
    ncirc = sum(1 for r in res.values() if r.get("circular", False))
    print(f"BEST lego DRR@80 over {len(valid)} NON-CIRCULAR attempts "
          f"({ncirc} circular rows excluded): {best:.4f}   ({bk[0]})")
    print(f"frozen NO-GO bar is 0.55  ->  {'EXCEEDED (NO-GO)' if best > 0.55 else 'NOT exceeded (lego stays at/below the bar)'}")
    json.dump(dict(best_noncircular=best, best_key=bk, bar=0.55,
                   n_circular_excluded=ncirc, rows=res),
              open("out/condlaw_lego_probe.json", "w"), indent=1, default=float)
    print("\nwrote out/condlaw_lego_probe.json")
