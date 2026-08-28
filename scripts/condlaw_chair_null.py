#!/usr/bin/env python
"""CONDLAW — permutation null + bootstrap CI for the CHAIR DRR@80, from the dumped arrays."""
import argparse, json
import numpy as np
from condlaw_drr import drr_at_recall, auc_mw
from condlaw_null import perm_null, boot_ci

KEYS = [
    ("2DGS[default]|theta_normal", "refined"),
    ("2DGS[default]|theta_normal", "headline"),
    ("GT-mesh_(ceiling_control)|theta_depth", "headline"),
    ("GT-mesh_(ceiling_control)|theta_depth", "refined"),
    ("vanilla-3DGS|theta_normal", "refined"),
    ("2DGS[default]|theta_depth", "refined"),
]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz", default="out/condlaw_chair_test.npz")
    ap.add_argument("--target", type=float, default=0.80)
    ap.add_argument("--n_perm", type=int, default=200)
    ap.add_argument("--n_boot", type=int, default=400)
    ap.add_argument("--seed", type=int, default=20260828)
    ap.add_argument("--out", default="out/condlaw_chair_null.json")
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    z = np.load(a.npz, allow_pickle=True)
    flat_fab, sharp_cre = z["flat_fab"], z["sharp_cre"]

    rows = {}
    T = round(a.target * 100)
    hdr = (f"{'arm|statistic':<40} {'scope':<9} {'AUC':>7} {'DRR@'+str(T):>7} "
           f"{'boot95':>18} {'null_mean':>9} {'null95':>18}")
    print(f"\nCHAIR bootstrap + permutation null  ({a.npz}, n_perm={a.n_perm}, "
          f"n_boot={a.n_boot}, seed={a.seed})")
    print(hdr); print("-" * len(hdr))
    for key, scope in KEYS:
        if f"{key}|cre_val" not in z.files:
            continue
        vf, of = z[f"{key}|fab_val"], z[f"{key}|fab_ok"]
        vc, oc = z[f"{key}|cre_val"], z[f"{key}|cre_ok"]
        mf = of if scope == "headline" else (of & flat_fab)
        mc = oc if scope == "headline" else (oc & sharp_cre)
        sf, sc_ = vf[mf], vc[mc]
        sf, sc_ = sf[np.isfinite(sf)], sc_[np.isfinite(sc_)]
        if len(sf) < 20 or len(sc_) < 20:
            continue
        A = auc_mw(np.r_[sc_, sf], np.r_[np.ones(len(sc_), bool), np.zeros(len(sf), bool)])
        obs = drr_at_recall(sc_, sf, a.target)
        bv = boot_ci(sc_, sf, a.target, a.n_boot, rng)
        nv = perm_null(sc_, sf, a.target, a.n_perm, rng)
        r = dict(scope=scope, auc=A, drr=obs["drr"], thr=obs["thr"], recall=obs["recall"],
                 n_cre=obs["n_cre"], n_fab=obs["n_dec"],
                 boot_lo=float(np.percentile(bv, 2.5)), boot_hi=float(np.percentile(bv, 97.5)),
                 boot_frac_ge_080=float((bv >= 0.80).mean()),
                 null_mean=float(nv.mean()),
                 null_lo=float(np.percentile(nv, 2.5)), null_hi=float(np.percentile(nv, 97.5)))
        rows[f"{key}|{scope}"] = r
        print(f"{key:<40} {scope:<9} {A:7.4f} {r['drr']:7.4f} "
              f"[{r['boot_lo']:.4f},{r['boot_hi']:.4f}] {r['null_mean']:9.4f} "
              f"[{r['null_lo']:.4f},{r['null_hi']:.4f}]")
    json.dump(dict(meta=dict(npz=a.npz, target=a.target, n_perm=a.n_perm,
                             n_boot=a.n_boot, seed=a.seed), rows=rows),
              open(a.out, "w"), indent=1, default=float)
    print(f"\nwrote {a.out}")
