"""tier1/scripts/tgap_diag.py — TGAP diagnostics: WHY the gates land where they land.

*** EVAL / ANALYSIS.  Reads the GT mesh via tune_lib.Harness -> mesh_oracle, like every other
    scorer in this repo.  Defines no method and modifies no method-path file. ***

A frontier gate is a single scalar and it cannot say WHERE a mechanism failed.  Three
measurements are made instead, each of which can independently kill or rescue the mechanism:

  1. IS E INFORMATIVE AT ALL?  AUC of the TEED response E as a predictor of "this linelet is
     actually on a GT crease", against the AUC of the statistic the prune already uses
     (multi-view inlier ratio).  If E is at chance, no functional form of E can help and the
     NO-GO is a property of the signal, not of the equations.  If E is informative, the
     equations are the thing that failed.

  2. WHAT IS THE PRECISION OF THE RESCUED SET?  Relaxing a prune can only ADD linelets.  The
     arm's precision therefore rises above arm A's only if the ADDED linelets are more precise
     than arm A's kept set.  This draws ONLY the added set and scores it.  It is a much
     sharper instrument than the frontier: a mechanism can be genuinely selective and still be
     unable to move a frontier whose reference point is "keep everything".

  3. IS THE TEED GATE SELECTIVE AGAINST A COUNT-MATCHED GLOBAL RELAXATION?  Arm C is re-tuned
     to rescue the SAME NUMBER of linelets as arm B, and the two rescued sets are scored
     against each other, per view and paired.  This is gate 2's question asked at the level of
     the decision the gate actually makes.
"""
import argparse
import json
import os
import sys

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))

from src import view_split, tgap_gate, common, visibility                # noqa: E402

OUT = os.path.join(TIER1, "out")


def auc(score, label):
    """Mann-Whitney AUC, ties averaged."""
    s = np.asarray(score, np.float64)
    y = np.asarray(label, bool)
    n1, n0 = int(y.sum()), int((~y).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    r = np.empty(len(s))
    order = np.argsort(s, kind="stable")
    sv = s[order]
    i = 0
    rank = np.empty(len(s))
    while i < len(sv):
        j = i
        while j + 1 < len(sv) and sv[j + 1] == sv[i]:
            j += 1
        rank[order[i:j + 1]] = 0.5 * (i + j) + 1.0
        i = j + 1
    r = rank
    return float((r[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="lego")
    ap.add_argument("--f", type=float, required=True)
    ap.add_argument("--alpha", type=float, required=True)
    ap.add_argument("--beta", type=float, required=True)
    ap.add_argument("--split", default="test", choices=["test", "val"])
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    from run_m1b import eval_segments                                    # EVAL harness
    from tune_lib import Harness                                         # mesh_oracle
    views = {"val": view_split.VAL, "test": view_split.TEST}[args.split]
    h = Harness(args.scene, views=tuple(views))

    z = np.load(os.path.join(OUT, f"tgap_pull_{args.scene}_f{args.f:.2f}.npz"))
    st = {"inlier_ratio": z["inlier_ratio"], "median_resid": z["median_resid"],
          "n_vis": z["n_vis"]}
    P, T, L, E = z["p"], z["t"], z["l"], z["E"]
    out = {"scene": args.scene, "f": args.f, "alpha": args.alpha, "beta": args.beta,
           "split": args.split, "views": list(views)}

    # ---- 1. is E informative about linelet correctness? ------------------------------
    hit = np.zeros(len(P))
    nvis = np.zeros(len(P))
    for v in views:
        vis, uv, _ = visibility.visible_mask(P, h.cams[v], h.gbufs[v]["depth"])
        cu, cv_, cdt = h.crease[v]
        u = np.clip(np.round(uv[:, 0]).astype(int), 0, cdt.shape[1] - 1)
        w = np.clip(np.round(uv[:, 1]).astype(int), 0, cdt.shape[0] - 1)
        d = cdt[w, u]
        hit += vis * (d <= 1.5)
        nvis += vis
    frac_on = np.where(nvis > 0, hit / np.maximum(nvis, 1), 0.0)
    ok = nvis > 0
    lab = frac_on[ok] >= 0.5
    out["informativeness"] = {
        "n_scored": int(ok.sum()), "pos_rate": float(lab.mean()),
        "AUC_E": auc(E[ok], lab),
        "AUC_inlier_ratio": auc(st["inlier_ratio"][ok], lab),
        "AUC_neg_median_resid": auc(-st["median_resid"][ok], lab),
        "spearman_E_vs_inlier": float(np.corrcoef(
            np.argsort(np.argsort(E[ok])), np.argsort(np.argsort(st["inlier_ratio"][ok])))[0, 1]),
        "definition": "label = linelet centre within 1.5 px of a GT crease pixel in >=50% "
                      "of the split views in which it is visible",
    }

    # Does E add anything BEYOND the statistic the prune already uses?  Stratify by
    # inlier_ratio decile and re-score E inside each stratum: if E is only a restatement of
    # inlier_ratio, its within-stratum AUC collapses to chance.
    strat = []
    q = np.quantile(st["inlier_ratio"][ok], np.linspace(0, 1, 11))
    ir_ok, E_ok = st["inlier_ratio"][ok], E[ok]
    for i in range(10):
        lo_, hi_ = q[i], q[i + 1]
        m = (ir_ok >= lo_) & (ir_ok <= hi_ if i == 9 else ir_ok < hi_)
        if m.sum() < 200 or len(np.unique(lab[m])) < 2:
            continue
        strat.append({"decile": i + 1, "inlier_lo": float(lo_), "inlier_hi": float(hi_),
                      "n": int(m.sum()), "pos_rate": float(lab[m].mean()),
                      "AUC_E_within": auc(E_ok[m], lab[m])})
    out["informativeness"]["within_inlier_decile"] = strat
    out["informativeness"]["mean_AUC_E_within_decile"] = (
        float(np.mean([x["AUC_E_within"] for x in strat])) if strat else float("nan"))
    np.savez(os.path.join(OUT, f"tgap_labels_{args.scene}_f{args.f:.2f}{args.tag}.npz"),
             frac_on=frac_on, nvis=nvis, E=E, inlier_ratio=st["inlier_ratio"],
             median_resid=st["median_resid"], n_vis=st["n_vis"])

    # ---- 2/3. precision of the rescued set, TEED-gated vs count-matched global --------
    kA, lA = tgap_gate.arm_masks(st, L, E, 0.0, 0.0)
    kB, lB = tgap_gate.arm_masks(st, L, E, args.alpha, args.beta)
    addB = kB & ~kA
    ones = np.ones(len(L))

    # global tau_r that rescues the same COUNT (the prune lever only; beta=0 on both sides)
    kBr, _ = tgap_gate.arm_masks(st, L, E, args.alpha, 0.0)
    addBr = kBr & ~kA
    target = int(addBr.sum())
    inl = st["inlier_ratio"]
    pool = (~kA) & (st["n_vis"] >= tgap_gate.MIN_VIEWS) & (st["median_resid"] <= tgap_gate.MAX_MED)
    cand = np.sort(inl[pool])[::-1]
    tau_r = float(cand[min(target, len(cand)) - 1]) if target > 0 and len(cand) else 0.50
    kC, _ = tgap_gate.arm_masks(st, L, ones, 1.0 - tau_r / 0.50, 0.0)
    addC = kC & ~kA

    def sc(mask, lens):
        if mask.sum() == 0:
            return None
        e = eval_segments(h, P, T, lens, keep=mask, per_view=True)
        return {"n": int(mask.sum()), "P1.5": float(np.mean(e[1.5][0])),
                "R1.5": float(np.mean(e[1.5][1])), "P1.5_per_view": e[1.5][0]}

    _, lBr = tgap_gate.arm_masks(st, L, E, args.alpha, 0.0)
    out["rescued_sets"] = {
        "armA_kept": sc(kA, lA),
        "armB_rescued_prune_only": sc(addBr, lBr),
        "armC_rescued_count_matched": sc(addC, lBr),
        "armB_rescued_full": sc(addB, lB),
        "tau_r_count_matched": tau_r,
        "n_target": target,
    }
    a = out["rescued_sets"]["armB_rescued_prune_only"]
    c = out["rescued_sets"]["armC_rescued_count_matched"]
    if a and c:
        d = np.array(a["P1.5_per_view"]) - np.array(c["P1.5_per_view"])
        out["rescued_sets"]["paired_dP_B_minus_C"] = {
            "mean": float(d.mean()), "t": float(d.mean() / (d.std(ddof=1) / np.sqrt(len(d)))
                                                if d.std(ddof=1) > 0 else np.inf),
            "n_views_positive": int((d > 0).sum()), "n_views": len(d)}

    # ---- length lever: which linelets get drawn long, and are they right? -------------
    longA = inl >= tgap_gate.L_BASE
    longB = inl >= tgap_gate.L_BASE * (1.0 - args.beta * E)
    addL = longB & ~longA & kA
    tgtL = int(addL.sum())
    poolL = (~longA) & kA
    candL = np.sort(inl[poolL])[::-1]
    tau_L = float(candL[min(tgtL, len(candL)) - 1]) if tgtL > 0 and len(candL) else 0.90
    addLC = (inl >= tau_L) & (~longA) & kA
    out["length_lever"] = {
        "n_long_A": int(longA.sum()), "n_long_B": int(longB.sum()),
        "n_newly_long_B": tgtL, "tau_L_count_matched": tau_L,
        "newly_long_B_frac_on_crease": float(frac_on[addL].mean()) if tgtL else None,
        "newly_long_C_frac_on_crease": float(frac_on[addLC].mean()) if addLC.sum() else None,
        "armA_kept_frac_on_crease": float(frac_on[kA].mean()),
    }

    p = os.path.join(OUT, f"tgap_diag_{args.scene}_f{args.f:.2f}{args.tag}.json")
    json.dump(out, open(p, "w"), indent=1, default=float)
    print(json.dumps({k: v for k, v in out.items() if k != "rescued_sets"},
                     indent=1, default=float))
    rs = out["rescued_sets"]
    for k in ("armA_kept", "armB_rescued_prune_only", "armC_rescued_count_matched",
              "armB_rescued_full"):
        if rs.get(k):
            print(f"  {k:32s} n={rs[k]['n']:7d}  P@1.5={rs[k]['P1.5']:.4f}  "
                  f"R@1.5={rs[k]['R1.5']:.4f}")
    print("  paired dP(B-C):", rs.get("paired_dP_B_minus_C"))
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
