"""tier1/scripts/geoline_step6.py — STEP 6: the threshold-family CEILING sweep.

*** EVAL-ONLY for the metric; no method change, no new pull, no training.  Inputs are the
    f=1.00 pooled linelets already on disk for all four solids.  The GT mesh is read only by
    tune_lib.Harness to score rendered segments. ***

WHY A CEILING AND NOT A RULE
    Step 5 returned THRESHOLD-LIMITED: the consensus statistic ORDERS oracle-good above
    oracle-bad on every solid (AUC 0.82-0.94) but the frozen 0.50 cut lands at the 72.6th
    percentile on the cube and the 87.7th on the icosahedron, so no constant transports.
    The tempting next move is to build an adaptive cut (Otsu, keep-fraction, null bar).
    That is premature for a reason this project already MEASURED: Step 2 banked a verifier
    at AUC 0.9294 on the same gapped 1.5-vs-3.0 px label boundary and Step 3 converted it
    into the deliverable metric, where it LOST to the shipped prune everywhere above P 0.65.
    A high AUC on a gapped boundary did not forecast ranking at 1.5 px then and cannot be
    assumed to now.  So: measure whether ANY threshold on the existing statistic moves the
    DELIVERABLE metric, before building any rule that picks one.

WHAT IS SWEPT
    keep = (n_vis >= 3) AND (inlier_ratio >= tau)  [AND (median_resid <= 1.5) if ACTIVE]
    tau is indexed by the per-solid QUANTILE of that solid's own inlier-ratio distribution,
    which is exactly what "one global keep-fraction applied to each scene's own
    distribution" means.  The median-residual clause is run BOTH active and disabled so the
    redundancy I reported in Step 5 is measured rather than assumed -- that observation was
    made at ONE operating point and does not license a structural claim.
    Every point is scored with run_m1b.eval_segments at tau=1.5 px on held-out TEST, the
    same evaluator that produced every P/R number in this campaign, at the published raw
    half-length (no length modulation), so the tau=0.50 ACTIVE point must reproduce the
    Step-4 zero-knob row exactly.  That reproduction is checked and reported.

FROZEN GO/NO-GO (pre-registered before any number was looked at)
    PRIMARY   a frozen threshold redesign is viable only if ONE global keep-fraction puts
              ALL FOUR solids at R@1.5 >= 0.35 AND P@1.5 >= 0.70 simultaneously.
    NECESSARY per-solid ceiling: if the icosahedron's own best point over all thresholds
              misses R 0.35 at P 0.70, the whole threshold family is dead, adaptive or
              frozen, and Step 5's THRESHOLD-LIMITED verdict is practically void.
    REPORTED  (not gated) the gap between each solid's ceiling and the global-constant point.
    INFO ONLY where a global keep-fraction, an Otsu split and a null-calibrated bar land.
              NO rule is adopted from this run.
"""
import argparse
import json
import os
import sys

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
sys.path.insert(0, os.path.join(TIER1, "scripts/explore/syn"))

from src import view_split                                              # noqa: E402
import run_m1b                                                          # noqa: E402

OUT = os.path.join(TIER1, "out")
POOLS = {"gcube": "_step4", "cadpartA": "_step3pool", "gstep": "_step4",
         "gprism": "_step4", "gicosa": "_step4"}
MAX_MED, MIN_VIEWS = 1.5, 3           # the SHIPPED constants, untouched
KF = [1.0, 0.9, 0.8, 0.7, 0.6, 0.55, 0.5, 0.45, 0.4, 0.35, 0.32, 0.30, 0.28,
      0.26, 0.24, 0.22, 0.20, 0.18, 0.16, 0.14, 0.12, 0.10, 0.08, 0.06, 0.04]
BAR_R, BAR_P = 0.35, 0.70


def otsu(x, nbins=256):
    """Standard 1-D Otsu on [0,1]: the split maximising between-class variance.
    Deterministic, no free parameter beyond the bin count."""
    h, edges = np.histogram(np.clip(x, 0.0, 1.0), bins=nbins, range=(0.0, 1.0))
    h = h.astype(np.float64)
    w = np.cumsum(h)
    m = np.cumsum(h * ((edges[:-1] + edges[1:]) / 2.0))
    tot, mt = w[-1], m[-1]
    with np.errstate(all="ignore"):
        wb, wf = w, tot - w
        mb, mf = m / np.maximum(wb, 1e-12), (mt - m) / np.maximum(wf, 1e-12)
        var = wb * wf * (mb - mf) ** 2
    var[~np.isfinite(var)] = -1.0
    return float(edges[1:][int(np.argmax(var))])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--solids", nargs="+",
                    default=["gcube", "cadpartA", "gprism", "gicosa"])
    args = ap.parse_args()
    from tune_lib import Harness                                        # EVAL ONLY (mesh)

    res = {"frozen": {"max_med": MAX_MED, "min_views": MIN_VIEWS,
                      "eval": "run_m1b.eval_segments, tau=1.5 px, held-out TEST, "
                              "published raw half-length (no length modulation)"},
           "bars": {"R": BAR_R, "P": BAR_P},
           "mesh_eval_only": "mesh scores rendered segments only; no method-path change",
           "solids": {}}

    for s in args.solids:
        z = np.load(os.path.join(OUT, f"linelets_{s}{POOLS[s]}.npz"))
        P, T, L = z["p"], z["t"], z["l"]
        ir, mr, nv, spec_keep = (z["inlier_ratio"], z["median_resid"],
                                 z["n_vis"], z["keep"])
        h = Harness(s, views=tuple(view_split.TEST))
        base = nv >= MIN_VIEWS
        row = {"n_pool": int(len(P)),
               "inlier_ratio_quantile_of_0.50": float((ir < 0.50).mean()),
               "otsu_tau": otsu(ir), "modes": {}}
        print(f"\n[{s}] pool {len(P)}  Otsu tau {row['otsu_tau']:.4f}  "
              f"(0.50 sits at pctile {100*(ir<0.50).mean():.1f})", flush=True)

        for mode in ("active", "disabled"):
            gate = base & (mr <= MAX_MED) if mode == "active" else base
            front = []
            for kf in KF:
                tau = float(np.quantile(ir, 1.0 - kf)) if kf < 1.0 else float(ir.min())
                k = gate & (ir >= tau)
                if k.sum() < 10:
                    continue
                e = run_m1b.eval_segments(h, P, T, L, keep=k, taus=(1.5,))
                front.append({"kf": kf, "tau": tau, "n": int(k.sum()),
                              "retention": float(k.mean()),
                              "P1.5": e[1.5][0], "R1.5": e[1.5][1]})
                print(f"    {mode:8s} kf {kf:5.3f} tau {tau:.4f} n {int(k.sum()):6d}  "
                      f"P {e[1.5][0]:.4f}  R {e[1.5][1]:.4f}", flush=True)
            # explicit extras: the SHIPPED tau=0.50 (reproduction check) and the Otsu split
            extras = {}
            for nm, tau in (("frozen_tau_0.50", 0.50), ("otsu", row["otsu_tau"])):
                k = gate & (ir >= tau)
                if k.sum() >= 10:
                    e = run_m1b.eval_segments(h, P, T, L, keep=k, taus=(1.5,))
                    extras[nm] = {"tau": tau, "n": int(k.sum()),
                                  "retention": float(k.mean()),
                                  "P1.5": e[1.5][0], "R1.5": e[1.5][1]}
                    print(f"    {mode:8s} {nm:16s} tau {tau:.4f} n {int(k.sum()):6d}  "
                          f"P {e[1.5][0]:.4f}  R {e[1.5][1]:.4f}", flush=True)
            ok = [r for r in front if r["P1.5"] >= BAR_P]
            ceil = max(ok, key=lambda r: r["R1.5"]) if ok else None
            row["modes"][mode] = {"frontier": front, "extras": extras,
                                  "ceiling_at_P0.70": ceil,
                                  "ceiling_clears_bar": bool(ceil and ceil["R1.5"] >= BAR_R)}
        res["solids"][s] = row
        # reproduction of the Step-4 zero-knob row (spec rule == active, tau 0.50)
        e0 = run_m1b.eval_segments(h, P, T, L, keep=spec_keep, taus=(1.5,))
        row["step4_zero_knob_reproduction"] = {"n": int(spec_keep.sum()),
                                               "P1.5": e0[1.5][0], "R1.5": e0[1.5][1]}
        print(f"  [{s}] Step-4 zero-knob reproduction: P {e0[1.5][0]:.4f} "
              f"R {e0[1.5][1]:.4f} n {int(spec_keep.sum())}", flush=True)

    # ---- PRIMARY: does ONE global keep-fraction clear the bar on all four? --------------
    prim = {}
    for mode in ("active", "disabled"):
        rows = {}
        for kf in KF:
            cells = {}
            allok = True
            for s in args.solids:
                m = [r for r in res["solids"][s]["modes"][mode]["frontier"]
                     if r["kf"] == kf]
                if not m:
                    allok = False
                    break
                r = m[0]
                cells[s] = {"P1.5": r["P1.5"], "R1.5": r["R1.5"], "n": r["n"]}
                if not (r["R1.5"] >= BAR_R and r["P1.5"] >= BAR_P):
                    allok = False
            rows[str(kf)] = {"cells": cells, "all_clear": bool(allok and cells)}
        winners = [k for k, v in rows.items() if v["all_clear"]]
        prim[mode] = {"by_kf": rows, "global_kf_that_clears_all": winners,
                      "PRIMARY": "GO" if winners else "NO-GO"}
    res["primary"] = prim

    nec = {s: res["solids"][s]["modes"]["disabled"]["ceiling_clears_bar"] or
              res["solids"][s]["modes"]["active"]["ceiling_clears_bar"]
           for s in args.solids}
    res["necessary_condition"] = {"per_solid_ceiling_clears_bar": nec,
                                  "icosa_ceiling_clears": bool(nec.get("gicosa", False)),
                                  "threshold_family_dead": not bool(nec.get("gicosa", False))}
    res["null_calibrated_bar"] = (
        "NOT COMPUTABLE from existing artifacts. A null bar needs the per-view Canny/DT edge "
        "maps of the pull field to say what inlier ratio a random position would reach at the "
        "same n_vis; those maps are not saved and regenerating them requires re-running the "
        "field build, which this run explicitly excludes. Reported as not computed rather "
        "than estimated.")

    p = os.path.join(OUT, "geoline_step6.json")
    json.dump(res, open(p, "w"), indent=1)
    print("\n  ===== VERDICT =====")
    for mode in ("active", "disabled"):
        print(f"  PRIMARY ({mode}): {prim[mode]['PRIMARY']}  "
              f"global kf clearing all four: {prim[mode]['global_kf_that_clears_all']}")
    for s in args.solids:
        for mode in ("active", "disabled"):
            c = res["solids"][s]["modes"][mode]["ceiling_at_P0.70"]
            print(f"  ceiling {s:9s} {mode:8s} " +
                  (f"R {c['R1.5']:.4f} P {c['P1.5']:.4f} kf {c['kf']}" if c
                   else "no point reaches P>=0.70"))
    print(f"  NECESSARY: icosa ceiling clears bar = {res['necessary_condition']['icosa_ceiling_clears']}")
    print(f"  -> {p}", flush=True)


if __name__ == "__main__":
    main()
