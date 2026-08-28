#!/usr/bin/env python
"""CONDLAW — empirical chance floor + bootstrap CI for DRR@80.

condlaw_spec.md asserts "DRR@80 = 0.50 means chance".  That is the AUC convention,
not this metric's.  For a statistic with NO class information the ROC is the
diagonal, so at TPR = 0.80 the FPR is also 0.80 and specificity = 1 - 0.80 = 0.20.
This script MEASURES the null instead of asserting it: it permutes the
TrueCrease/DecalDistractor labels within the pooled scored population and
recomputes DRR@80, giving the empirical chance floor and its spread.
Also reports a stratified bootstrap CI on the observed DRR@80.
"""
import argparse, json
import numpy as np
from condlaw_drr import drr_at_recall, auc_mw, LEGO_TEST, LEGO_SIGNALS, _masks


def perm_null(s_cre, s_dec, target, n_perm, rng):
    s_cre = s_cre[np.isfinite(s_cre)]; s_dec = s_dec[np.isfinite(s_dec)]
    pool = np.r_[s_cre, s_dec]; n1 = len(s_cre)
    vals = np.empty(n_perm)
    for i in range(n_perm):
        p = rng.permutation(len(pool))
        vals[i] = drr_at_recall(pool[p[:n1]], pool[p[n1:]], target)["drr"]
    return vals


def boot_ci(s_cre, s_dec, target, n_boot, rng):
    s_cre = s_cre[np.isfinite(s_cre)]; s_dec = s_dec[np.isfinite(s_dec)]
    vals = np.empty(n_boot)
    for i in range(n_boot):
        c = s_cre[rng.integers(0, len(s_cre), len(s_cre))]
        d = s_dec[rng.integers(0, len(s_dec), len(s_dec))]
        vals[i] = drr_at_recall(c, d, target)["drr"]
    return vals


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=float, default=0.80)
    ap.add_argument("--scope", default="own")
    ap.add_argument("--n_perm", type=int, default=200)
    ap.add_argument("--n_boot", type=int, default=400)
    ap.add_argument("--seed", type=int, default=20260828)
    ap.add_argument("--out", default="out/condlaw_lego_null.json")
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    z = np.load(LEGO_TEST, allow_pickle=True)

    rows = {}
    T = round(a.target * 100)
    hdr = (f"{'signal':32s} {'sgn':>3s} {'DRR@'+str(T):>7s} {'boot95':>16s} | "
           f"{'null_mean':>9s} {'null95':>16s}")
    print(f"\nLEGO permutation null + bootstrap  (TEST, scope={a.scope}, "
          f"n_perm={a.n_perm}, n_boot={a.n_boot}, seed={a.seed})")
    print(hdr); print("-" * len(hdr))
    for key, arm, nice in LEGO_SIGNALS:
        if key not in z.files:
            continue
        c, d = _masks(z, key, a.scope)
        sc, sd = z[key][c], z[key][d]
        A = auc_mw(np.r_[sc[np.isfinite(sc)], sd[np.isfinite(sd)]],
                   np.r_[np.ones(int(np.isfinite(sc).sum()), bool),
                         np.zeros(int(np.isfinite(sd).sum()), bool)])
        s = 1 if A >= 0.5 else -1                     # best-orientation (upper bound)
        obs = drr_at_recall(s * sc, s * sd, a.target)
        nv = perm_null(s * sc, s * sd, a.target, a.n_perm, rng)
        bv = boot_ci(s * sc, s * sd, a.target, a.n_boot, rng)
        rows[key] = dict(arm=arm, name=nice, sign=s, auc=A, drr=obs["drr"],
                         thr=obs["thr"], recall=obs["recall"],
                         boot_lo=float(np.percentile(bv, 2.5)),
                         boot_hi=float(np.percentile(bv, 97.5)),
                         null_mean=float(nv.mean()), null_sd=float(nv.std()),
                         null_lo=float(np.percentile(nv, 2.5)),
                         null_hi=float(np.percentile(nv, 97.5)),
                         p_greater=float((nv >= obs["drr"]).mean()))
        r = rows[key]
        print(f"{key:32s} {s:+3d} {r['drr']:7.4f} "
              f"[{r['boot_lo']:.4f},{r['boot_hi']:.4f}] | {r['null_mean']:9.4f} "
              f"[{r['null_lo']:.4f},{r['null_hi']:.4f}]")
    json.dump(dict(meta=dict(target=a.target, scope=a.scope, n_perm=a.n_perm,
                             n_boot=a.n_boot, seed=a.seed, src=LEGO_TEST),
                   rows=rows), open(a.out, "w"), indent=1, default=float)
    print(f"\nwrote {a.out}")
