#!/usr/bin/env python
"""
CONDLAW — DRR@80 (Distractor Rejection Rate at >=80% TrueCrease recall).

ANALYSIS / DIAGNOSTIC ONLY.  Reads existing artifacts; writes nothing outside a
condlaw_ / CONDLAW_ prefix.  No method-path change, no retraining, mesh used only
as eval/label oracle (mesh_oracle), held-out TEST.

Definition (frozen by tier1/condlaw_spec.md):
  Sweep the operating point to the threshold t where TrueCrease recall
  (fraction of TrueCrease loci scored ABOVE t) >= 0.80; report the fraction of
  DecalDistractor loci scored BELOW t.
  0.50 == chance;  high == geometry cleanly separates distractors from creases.

Exact convention used here:
  recall(t)    = mean(s_crease >= t)          (non-increasing step function in t)
  rejection(t) = mean(s_decal  <  t)          (non-decreasing step function in t)
  t*           = max{ t in candidates : recall(t) >= 0.80 }   -> maximises rejection
                 subject to the recall constraint.  Candidates = all observed scores
                 plus +inf sentinel, so t* is exact (no interpolation, no ties fudge).
  DRR@80       = rejection(t*)

ORIENTATION.  diag2dgs.auc() is Mann-Whitney with positive class = TrueCrease, so
AUC > 0.5 means "higher statistic == more crease-like".  Several lego statistics are
ANTI-predictive (AUC < 0.5).  We therefore report three orientation policies, all
labelled, and never silently pick the flattering one:
   frozen : sign=+1, the literal spec reading ("scored ABOVE threshold" == crease).
   val    : sign AND threshold both chosen on VAL, evaluated on TEST (held-out; the
            invariant "any threshold-selection on VAL, report TEST beside it").
   oracle : sign chosen on TEST by whichever gives the larger TEST AUC, threshold on
            TEST.  This is an UPPER BOUND, not a held-out number.  Labelled as such.
"""
import argparse
import json

import numpy as np


# ----------------------------------------------------------------------------------
def auc_mw(score, is_pos):
    """Mann-Whitney AUC, ties averaged.  Identical to scripts/diag2dgs.py:auc()."""
    s = np.asarray(score, np.float64)
    y = np.asarray(is_pos, bool)
    n1, n0 = int(y.sum()), int((~y).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    order = np.argsort(s, kind="stable")
    sv = s[order]
    rank = np.empty(len(s))
    i = 0
    while i < len(sv):
        j = i
        while j + 1 < len(sv) and sv[j + 1] == sv[i]:
            j += 1
        rank[order[i:j + 1]] = 0.5 * (i + j) + 1.0
        i = j + 1
    return float((rank[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def drr_at_recall(s_cre, s_dec, target=0.80):
    """Exact DRR@<target>.  Returns dict; nan-safe; no interpolation."""
    s_cre = np.asarray(s_cre, np.float64)
    s_dec = np.asarray(s_dec, np.float64)
    s_cre = s_cre[np.isfinite(s_cre)]
    s_dec = s_dec[np.isfinite(s_dec)]
    if len(s_cre) < 10 or len(s_dec) < 10:
        return dict(drr=float("nan"), thr=float("nan"), recall=float("nan"),
                    n_cre=len(s_cre), n_dec=len(s_dec))
    # candidate thresholds: every observed crease score (recall only steps there)
    cand = np.unique(s_cre)
    cs = np.sort(s_cre)
    # recall(t) = mean(s_cre >= t) = 1 - searchsorted(cs, t, 'left')/n
    rec = 1.0 - np.searchsorted(cs, cand, side="left") / float(len(cs))
    okm = rec >= target - 1e-12
    if not okm.any():                       # cannot reach the recall target at all
        return dict(drr=float("nan"), thr=float("nan"), recall=float("nan"),
                    n_cre=len(s_cre), n_dec=len(s_dec))
    t = float(cand[okm][-1])                # largest t meeting the constraint
    ds = np.sort(s_dec)
    return dict(drr=float(np.searchsorted(ds, t, side="left") / float(len(ds))),
                thr=t,
                recall=float((s_cre >= t).mean()),
                n_cre=int(len(s_cre)), n_dec=int(len(s_dec)))


def apply_threshold(s_cre, s_dec, t):
    """Evaluate a FIXED threshold (e.g. picked on VAL) on another split."""
    s_cre = np.asarray(s_cre, np.float64); s_cre = s_cre[np.isfinite(s_cre)]
    s_dec = np.asarray(s_dec, np.float64); s_dec = s_dec[np.isfinite(s_dec)]
    if len(s_cre) < 10 or len(s_dec) < 10 or not np.isfinite(t):
        return dict(drr=float("nan"), thr=float(t), recall=float("nan"),
                    n_cre=len(s_cre), n_dec=len(s_dec))
    return dict(drr=float((s_dec < t).mean()), thr=float(t),
                recall=float((s_cre >= t).mean()),
                n_cre=int(len(s_cre)), n_dec=int(len(s_dec)))


# ----------------------------------------------------------------------------------
# LEGO arm — reuse out/diag2dgs_lego_{test,val_sweep}.npz verbatim.
# ----------------------------------------------------------------------------------
LEGO_TEST = "out/diag2dgs_lego_test.npz"
LEGO_VAL = "out/diag2dgs_lego_val_sweep.npz"

# (signal key, arm, human name).  "GT-mesh" arm reads the ORACLE MESH (eval/labels only);
# "2DGS" arm reads the reconstructed surfel cloud.  Both share the same labels.
LEGO_SIGNALS = [
    ("mesh3d_rho4_xi0.25_nmin5",      "GT-mesh", "mesh dihedral (theta_max)"),
    ("spreadmesh_rho4_xi0.25_nmin5",  "GT-mesh", "mesh normal-dispersion (split-free)"),
    ("surfel3d_rho4_xi0.25_nmin5",    "2DGS",    "surfel dihedral (theta_max)"),
    ("spread2dgs_rho4_xi0.25_nmin5",  "2DGS",    "surfel normal-dispersion (split-free)"),
    ("surfel3d_perlinelet",           "2DGS",    "surfel dihedral, per-linelet radius"),
    ("ribbon2dgs",                    "2DGS",    "rendered-normal ribbon (2DGS)"),
    ("ribbon3dgs_vanilla",            "2DGS",    "rendered-normal ribbon (vanilla 3DGS)"),
]


def _masks(z, key, scope):
    crease = z["crease"].astype(bool)
    decal = z["decal"].astype(bool)
    seen = z["seen"].astype(bool)
    okm = z[f"ok_{key}"].astype(bool) if f"ok_{key}" in z.files else np.isfinite(z[key])
    m = okm if scope == "own" else (okm & z["common_ok"].astype(bool))
    return (crease & seen & m), (decal & seen & m)


def lego(target=0.80, scope="own"):
    zt = np.load(LEGO_TEST, allow_pickle=True)
    zv = np.load(LEGO_VAL, allow_pickle=True)
    out = []
    for key, arm, nice in LEGO_SIGNALS:
        if key not in zt.files:
            out.append(dict(signal=key, arm=arm, name=nice, status="ABSENT_IN_TEST"))
            continue
        ct, dt = _masks(zt, key, scope)
        st_c, st_d = zt[key][ct], zt[key][dt]
        rec = dict(signal=key, arm=arm, name=nice, status="OK", scope=scope,
                   n_cre_test=int(np.isfinite(st_c).sum()),
                   n_dec_test=int(np.isfinite(st_d).sum()))
        # --- AUC (crease = positive), both orientations -----------------------------
        fin_c, fin_d = st_c[np.isfinite(st_c)], st_d[np.isfinite(st_d)]
        lab = np.r_[np.ones(len(fin_c), bool), np.zeros(len(fin_d), bool)]
        rec["auc_test"] = auc_mw(np.r_[fin_c, fin_d], lab)

        # --- policy 1: FROZEN literal orientation (sign=+1), threshold on TEST -------
        rec["frozen"] = drr_at_recall(st_c, st_d, target)
        # --- policy 3: TEST-oracle orientation (upper bound) -------------------------
        pos = drr_at_recall(st_c, st_d, target)
        neg = drr_at_recall(-st_c, -st_d, target)
        sgn = 1 if rec["auc_test"] >= 0.5 else -1
        rec["oracle_sign"] = sgn
        rec["oracle"] = pos if sgn == 1 else neg
        # --- policy 2: VAL-selected sign AND threshold, evaluated on TEST ------------
        if key in zv.files:
            cv, dv = _masks(zv, key, scope)
            sv_c, sv_d = zv[key][cv], zv[key][dv]
            fv_c, fv_d = sv_c[np.isfinite(sv_c)], sv_d[np.isfinite(sv_d)]
            auc_v = auc_mw(np.r_[fv_c, fv_d],
                           np.r_[np.ones(len(fv_c), bool), np.zeros(len(fv_d), bool)])
            s = 1 if auc_v >= 0.5 else -1
            v = drr_at_recall(s * sv_c, s * sv_d, target)     # threshold picked on VAL
            rec["val"] = dict(auc_val=auc_v, sign=s, n_cre_val=v["n_cre"],
                              n_dec_val=v["n_dec"], thr_val=v["thr"],
                              drr_val=v["drr"], recall_val=v["recall"])
            rec["val_on_test"] = apply_threshold(s * st_c, s * st_d, v["thr"])
            rec["val_on_test"]["sign"] = s
        else:
            rec["val"] = None
            rec["val_on_test"] = None
        out.append(rec)
    return out


# ----------------------------------------------------------------------------------
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=float, default=0.80)
    ap.add_argument("--scope", default="own", choices=["own", "common"])
    ap.add_argument("--out", default="out/condlaw_lego_drr.json")
    a = ap.parse_args()

    res = lego(a.target, a.scope)
    meta = dict(target_recall=a.target, scope=a.scope,
                test_npz=LEGO_TEST, val_npz=LEGO_VAL,
                definition="DRR@%d = frac(decal < t*) at t* = max{t: frac(crease>=t) >= %.2f}"
                           % (round(a.target * 100), a.target))
    json.dump(dict(meta=meta, rows=res), open(a.out, "w"), indent=1, default=float)

    T = round(a.target * 100)
    print(f"\nLEGO  scope={a.scope}  target recall >= {a.target:.2f}   (TEST split, "
          f"{LEGO_TEST})")
    hdr = (f"{'signal':32s} {'arm':8s} {'AUC':>6s} | {'DRR@'+str(T):>7s} {'thr':>7s} "
           f"{'rec':>5s} | {'sgn':>3s} {'DRR_or':>7s} | {'sgnV':>4s} {'DRRv->T':>8s} "
           f"{'recV->T':>8s} | {'n_cre':>6s} {'n_dec':>6s}")
    print(hdr); print("-" * len(hdr))
    for r in res:
        if r["status"] != "OK":
            print(f"{r['signal']:32s} {r['arm']:8s}  {r['status']}"); continue
        f_, o_ = r["frozen"], r["oracle"]
        vt = r["val_on_test"]
        vs = f"{vt['sign']:+d}" if vt else "  na"
        vd = f"{vt['drr']:8.4f}" if vt else "      na"
        vr = f"{vt['recall']:8.4f}" if vt else "      na"
        print(f"{r['signal']:32s} {r['arm']:8s} {r['auc_test']:6.4f} | "
              f"{f_['drr']:7.4f} {f_['thr']:7.2f} {f_['recall']:5.3f} | "
              f"{r['oracle_sign']:+3d} {o_['drr']:7.4f} | {vs:>4s} {vd} {vr} | "
              f"{r['n_cre_test']:6d} {r['n_dec_test']:6d}")
    print(f"\nwrote {a.out}")
