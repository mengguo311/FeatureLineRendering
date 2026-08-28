#!/usr/bin/env python
"""CONDLAW — chair DRR@80 CERTIFIED BOUND from the stored percentiles.

scripts/explore/gate_falsify_2dgs.py dumps only summary percentiles + AUC (json.dump at
line 509); it never writes per-locus arrays.  So the exact chair ROC is not on disk.
But DRR@80 is a pure quantile composition, and the stored percentiles pin it inside a
CERTIFIED interval with NO interpolation and NO fabrication:

  threshold  t* = Q_cre(1 - 0.80) = Q_cre(0.20)          (higher theta_normal = crease,
                                                          since AUC 0.967 > 0.5)
  monotonicity of the quantile function:  cre_p10 <= t* <= cre_p25
  DRR@80 = F_fab(t*), and F_fab is non-decreasing, so
           F_fab(cre_p10) <= DRR@80 <= F_fab(cre_p25)
  each F_fab(.) is itself bracketed by the two stored fab percentiles straddling it.

The result is a hard interval [lo, hi] that the true DRR@80 provably lies in.
"""
import json
import sys

FAB_PCTS = [50, 90, 95, 99]      # keys fab_p50 / fab_p90 / fab_p95 / fab_p99
CRE_PCTS = [5, 10, 25, 50]       # keys cre_p05 / cre_p10 / cre_p25 / cre_p50


def _fab_key(p): return f"fab_p{p:02d}"
def _cre_key(p): return f"cre_p{p:02d}"


def bracket_Ffab(t, row):
    """Return (lo, hi) bracketing F_fab(t) using only the stored fab percentiles."""
    lo, hi = 0.0, 1.0
    for p in FAB_PCTS:                       # F_fab(fab_pP) = P/100
        v = row[_fab_key(p)]
        if v <= t:
            lo = max(lo, p / 100.0)          # at least P% of fab are <= v <= t
        if v >= t:
            hi = min(hi, p / 100.0)          # at most P% of fab are < v, and t <= v
    return lo, hi


def bound(row, target=0.80):
    q = 1.0 - target                          # crease quantile of the threshold
    below = [p for p in CRE_PCTS if p / 100.0 <= q]
    above = [p for p in CRE_PCTS if p / 100.0 >= q]
    if not below or not above:
        return None
    t_lo = row[_cre_key(max(below))]          # cre_p10 when target = 0.80
    t_hi = row[_cre_key(min(above))]          # cre_p25 when target = 0.80
    lo = bracket_Ffab(t_lo, row)[0]
    hi = bracket_Ffab(t_hi, row)[1]
    return dict(target=target, thr_lo=t_lo, thr_hi=t_hi,
                thr_from=f"cre_p{max(below):02d}", thr_to=f"cre_p{min(above):02d}",
                drr_lo=lo, drr_hi=hi, auc=row["auc"],
                n_fab=row["n_fab"], n_cre=row["n_cre"])


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "out/2dgs_falsify_chair_full.json"
    d = json.load(open(src))
    out = {"source": src, "views": d["views"], "flat_deg": d["flat_deg"],
           "sharp_deg": d["sharp_deg"], "rows": {}}
    print(f"\nCHAIR DRR@80 certified bounds from stored percentiles — {src}")
    print(f"  refined classes: fab = edge px, interior, >3px from GT crease, "
          f"MESH theta_depth < {d['flat_deg']} deg (flat printed fabric)")
    print(f"                   cre = edge px, interior, <=2px from GT crease, "
          f"MESH theta_depth > {d['sharp_deg']} deg (genuinely sharp)")
    print(f"  views {d['views']}  <-- NOT the frozen TEST split")
    hdr = (f"{'arm':<28} {'statistic':<13} {'AUC':>7} {'thr in':>16} "
           f"{'DRR@80 in':>16} {'n_fab':>7} {'n_cre':>7}")
    print("\n" + hdr); print("-" * len(hdr))
    for arm in d["refined"]:
        for st in ("theta_normal", "theta_depth"):
            row = d["refined"][arm]["sharp"].get(st)
            if row is None:
                print(f"{arm:<28} {st:<13} {'N/A (no normal buffer for this arm)':>7}")
                out["rows"][f"{arm}|{st}"] = None
                continue
            b = bound(row)
            out["rows"][f"{arm}|{st}"] = b
            print(f"{arm:<28} {st:<13} {b['auc']:7.4f} "
                  f"[{b['thr_lo']:6.2f},{b['thr_hi']:6.2f}] "
                  f"[{b['drr_lo']:6.3f},{b['drr_hi']:6.3f}] "
                  f"{b['n_fab']:7d} {b['n_cre']:7d}")
    json.dump(out, open("out/condlaw_chair_bound.json", "w"), indent=1, default=float)
    print("\nwrote out/condlaw_chair_bound.json")
