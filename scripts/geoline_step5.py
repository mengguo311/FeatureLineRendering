"""tier1/scripts/geoline_step5.py — STEP 5: rejected-candidate mechanism analysis.

*** EVAL / DIAGNOSTIC.  The GT mesh (tune_lib.Harness -> mesh_oracle) supplies the ORACLE
    LABELS and the crease-ambiguity geometry.  It defines no method and changes nothing in
    the pipeline.  Existing artifacts only: the f=1.00 pooled linelets already on disk plus
    the ten held-out gbuffers per solid that the oracle labels require. ***

THE QUESTION STEP 4 LEFT OPEN
    Step 4 is NOT-GENERAL: the icosahedron reaches R@1.5 0.2598 at the zero-knob point
    against a 0.35 bar, while its ORACLE ceiling is R 0.7106 at P 0.8414.  So the ranker is
    at fault, not the pool.  But "the ranker is at fault" has two readings with OPPOSITE
    fixes, and nothing so far has separated them:

      RANKER-LIMITED     the consensus statistic does not ORDER oracle-good above
                         oracle-bad on this solid.  Fix = a different statistic.
      THRESHOLD-LIMITED  it orders fine, but the FROZEN cut (inlier ratio >= 0.50 AND
                         median residual <= 1.5 px AND n_vis >= 3) falls in the wrong place
                         in this solid's distribution.  That is a further NOT-GENERAL
                         finding about the thresholds and explicitly NOT a licence to
                         retune them per scene.

WHY THE OBVIOUS SIGNATURE IS BACKWARDS (design-argue correction, recorded here)
    "Residuals landing on a symmetry-equivalent wrong edge" cannot happen as stated: a
    linelet has ONE 3-D position, optimised against all views jointly, so it cannot sit on
    edge E in one view and on E' in another.  If views disagree about which edge it belongs
    to, the pull lands it at a COMPROMISE position on neither, and the residual is then
    LARGE and roughly UNIFORM across views.  The compromise signature is therefore
    high median_resid together with low inlier_ratio, not a small residual to a wrong
    target.  Both aggregates are already saved, so this is testable without re-running the
    pull.

FROZEN GO/NO-GO (pre-registered by the user before any number was looked at)
    RANKER-LIMITED    iff gicosa inlier-ratio AUC < 0.70 AND at least 0.10 below the mean
                      of the other three solids.
    THRESHOLD-LIMITED iff gicosa AUC >= 0.70 and within 0.10 of the others, while the
                      frozen cut sits at a materially different quantile of its own
                      distribution.  Reported NOT-GENERAL with ZERO retuning.
    NEITHER           reported straight.
    Mechanism leg runs ONLY under RANKER-LIMITED.
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

OUT = os.path.join(TIER1, "out")
POOLS = {"cadpartA": "_step3pool", "gcube": "_step4",
         "gicosa": "_step4", "gprism": "_step4"}
MIN_RATIO, MAX_MED, MIN_VIEWS = 0.50, 1.5, 3          # the SHIPPED spec rule, untouched
DELTA_MAX = 5.0                                        # the pull's capture radius, px


def oracle_dmed(P, h):
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
    return dm, np.array([len(a) > 0 for a in acc])


def ambiguity(P, h, scene):
    """Median over held-out views of the 3-D SPREAD of GT crease samples whose projection
    falls within the pull's capture radius of the linelet's projection.  Large spread = two
    or more genuinely different creases compete for the same pixels, which is the crowding /
    symmetry-aliasing signature.  World units; every solid is built to the same max vertex
    radius so the scenes are directly comparable."""
    from src.mesh_oracle import MeshOracle                              # EVAL ONLY
    o = MeshOracle(scene, angle_deg=30.0)
    C = np.asarray(o.crease_pts, np.float64)
    acc = [[] for _ in range(len(P))]
    for v in view_split.TEST:
        cam = h.cams[v]
        vis, uv, _ = visibility.visible_mask(P, cam, h.gbufs[v]["depth"])
        cuv, cz = common.project(C, cam)
        okc = cz > 1e-6
        tree = cKDTree(cuv[okc])
        Cok = C[okc]
        idx = np.where(vis)[0]
        for i, nb in zip(idx, tree.query_ball_point(uv[idx], DELTA_MAX, workers=-1)):
            if len(nb) >= 2:
                q = Cok[np.asarray(nb)]
                acc[i].append(float(np.linalg.norm(q.std(0))))
            elif len(nb) == 1:
                acc[i].append(0.0)
    return np.array([np.median(a) if a else np.nan for a in acc])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", nargs="+", default=["cadpartA", "gcube", "gicosa", "gprism"])
    args = ap.parse_args()
    from tune_lib import Harness                                        # EVAL ONLY (mesh)

    res = {"frozen_rule": {"min_ratio": MIN_RATIO, "max_med": MAX_MED,
                           "min_views": MIN_VIEWS, "delta_max_px": DELTA_MAX},
           "labels": "oracle-good: median TEST-view GT-crease distance <= 1.5 px; "
                     "oracle-bad: > 3.0 px (the Step-1/2 convention)",
           "mesh_eval_only": "labels + ambiguity geometry only; no method-path change",
           "solids": {}}
    cache = {}

    for s in args.scenes:
        z = np.load(os.path.join(OUT, f"linelets_{s}{POOLS[s]}.npz"))
        P, ir, mr, nv, keep = (z["p"], z["inlier_ratio"], z["median_resid"],
                               z["n_vis"], z["keep"])
        h = Harness(s, views=tuple(view_split.TEST))
        dm, seen = oracle_dmed(P, h)
        good = seen & (dm <= 1.5)
        bad = seen & (dm > 3.0)
        lab = np.concatenate([np.ones(int(good.sum()), bool),
                              np.zeros(int(bad.sum()), bool)])
        a_ir = diag2dgs.auc(np.concatenate([ir[good], ir[bad]]), lab)
        a_mr = diag2dgs.auc(np.concatenate([-mr[good], -mr[bad]]), lab)
        # where the FROZEN cut lands in THIS solid's own distribution
        q_ir = float((ir < MIN_RATIO).mean())
        q_mr = float((mr > MAX_MED).mean())
        q_nv = float((nv < MIN_VIEWS).mean())
        row = {"n_pool": int(len(P)), "n_seen": int(seen.sum()),
               "n_good": int(good.sum()), "n_bad": int(bad.sum()),
               "AUC_inlier_ratio": float(a_ir), "AUC_neg_median_resid": float(a_mr),
               "retention": float(keep.mean()), "n_keep": int(keep.sum()),
               "frac_cut_by_ratio": q_ir, "frac_cut_by_median_resid": q_mr,
               "frac_cut_by_n_vis": q_nv,
               "median_inlier_ratio": float(np.median(ir)),
               "median_median_resid": float(np.median(mr)),
               "median_inlier_ratio_good": float(np.median(ir[good])),
               "median_median_resid_good": float(np.median(mr[good])),
               # THE interpretable number: what fraction of genuinely-good candidates does
               # the FROZEN rule keep, and what fraction of them does each clause remove?
               "frac_good_kept_by_frozen_rule": float(keep[good].mean()),
               "frac_good_cut_by_ratio": float((ir[good] < MIN_RATIO).mean()),
               "frac_good_cut_by_median_resid": float((mr[good] > MAX_MED).mean()),
               "frac_bad_kept_by_frozen_rule": float(keep[bad].mean())}
        res["solids"][s] = row
        cache[s] = (P, ir, mr, keep, good, bad, h)
        print(f"[{s}] AUC(inlier_ratio) {a_ir:.4f}  AUC(-median_resid) {a_mr:.4f}  "
              f"retention {keep.mean():.3f}  good/bad {int(good.sum())}/{int(bad.sum())}",
              flush=True)
        print(f"        frozen rule KEEPS {keep[good].mean():.3f} of oracle-GOOD and "
              f"{keep[bad].mean():.3f} of oracle-BAD", flush=True)
        print(f"        frozen cut removes: ratio<0.50 {q_ir:.3f} | med_resid>1.5 {q_mr:.3f}"
              f" | n_vis<3 {q_nv:.3f}   median ratio {np.median(ir):.3f} "
              f"(good {np.median(ir[good]):.3f})", flush=True)

    # ---- the frozen verdict ------------------------------------------------------------
    ai = res["solids"]["gicosa"]["AUC_inlier_ratio"]
    others = [res["solids"][s]["AUC_inlier_ratio"] for s in args.scenes if s != "gicosa"]
    mo = float(np.mean(others))
    ranker = bool(ai < 0.70 and ai <= mo - 0.10)
    thresh = bool(ai >= 0.70 and abs(ai - mo) <= 0.10)
    res["verdict"] = {"gicosa_AUC": ai, "mean_other_AUC": mo, "delta": ai - mo,
                      "RANKER_LIMITED": ranker, "THRESHOLD_LIMITED": thresh,
                      "outcome": ("RANKER-LIMITED" if ranker else
                                  "THRESHOLD-LIMITED" if thresh else "NEITHER")}
    print(f"\n  gicosa AUC {ai:.4f} vs mean(others) {mo:.4f}  (delta {ai - mo:+.4f})")
    print(f"  === STEP 5 OUTCOME: {res['verdict']['outcome']} ===", flush=True)

    # ---- mechanism leg: ONLY under RANKER-LIMITED --------------------------------------
    if ranker:
        print("\n  RANKER-LIMITED fired -> running the mechanism leg", flush=True)
        res["mechanism"] = {}
        for s in args.scenes:
            P, ir, mr, keep, good, bad, h = cache[s]
            rg = good & ~keep                      # rejected but oracle-good
            kg = good & keep                       # kept and oracle-good
            amb = ambiguity(P, h, s)
            fin = np.isfinite(amb)
            m = {"n_rejected_good": int(rg.sum()), "n_kept_good": int(kg.sum()),
                 "frac_good_rejected": float(rg.sum() / max(good.sum(), 1)),
                 # compromise signature: uniformly bad residual, not bimodal
                 "rejgood_median_resid_med": float(np.median(mr[rg])) if rg.any() else None,
                 "rejgood_inlier_ratio_med": float(np.median(ir[rg])) if rg.any() else None,
                 "keptgood_median_resid_med": float(np.median(mr[kg])) if kg.any() else None,
                 "keptgood_inlier_ratio_med": float(np.median(ir[kg])) if kg.any() else None,
                 "ambiguity_median_all": float(np.nanmedian(amb)),
                 "ambiguity_median_rejgood": (float(np.nanmedian(amb[rg]))
                                              if (rg & fin).any() else None),
                 "ambiguity_median_keptgood": (float(np.nanmedian(amb[kg]))
                                               if (kg & fin).any() else None)}
            a, b = rg & fin, kg & fin
            if a.sum() >= 10 and b.sum() >= 10:
                lab = np.concatenate([np.ones(int(a.sum()), bool),
                                      np.zeros(int(b.sum()), bool)])
                m["AUC_ambiguity_rejgood_vs_keptgood"] = float(
                    diag2dgs.auc(np.concatenate([amb[a], amb[b]]), lab))
            res["mechanism"][s] = m
            print(f"  [{s}] rejected-good {int(rg.sum())}/{int(good.sum())} "
                  f"({rg.sum()/max(good.sum(),1):.3f}) | med_resid rej {m['rejgood_median_resid_med']} "
                  f"vs kept {m['keptgood_median_resid_med']} | ratio rej "
                  f"{m['rejgood_inlier_ratio_med']} vs kept {m['keptgood_inlier_ratio_med']}",
                  flush=True)
            print(f"        ambiguity med all {m['ambiguity_median_all']:.5f} | rejgood "
                  f"{m['ambiguity_median_rejgood']} | keptgood {m['ambiguity_median_keptgood']}"
                  f" | AUC {m.get('AUC_ambiguity_rejgood_vs_keptgood')}", flush=True)

    p = os.path.join(OUT, "geoline_step5.json")
    json.dump(res, open(p, "w"), indent=1)
    print(f"\n  -> {p}", flush=True)


if __name__ == "__main__":
    main()
