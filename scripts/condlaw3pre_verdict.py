#!/usr/bin/env python
"""CONDLAW-3-PRE Stage 2 — apply the FROZEN GO/NO-GO to the ship measurement.

Written BEFORE the ship number existed (the 2DGS was still training), so the gate cannot
have been fitted to the result. The thresholds below are read from out/condlaw3pre_amend.json,
which was committed (92ce75f) before ship had any trained model or scored artifact.

FROZEN GATE (verbatim from the approving instruction):
  PRIMARY falsifier  : DRR@80(ship) in the affine band [0.692, 0.852]
  SECONDARY sanity   : monotonic lego' 0.4334 < ship < chair 0.9858
                       AND ship in [0.4477, 0.9848]
Both are reported; neither is moved.
"""
import json

SHIP_JSON = "out/condlaw_ship_test.json"
SHIP_NULL = "out/condlaw3pre_ship_null.json"
KEY = "2DGS[default]|theta_normal|refined"


def band_str(lo, hi):
    return f"[{lo:.4f}, {hi:.4f}]"


if __name__ == "__main__":
    am = json.load(open("out/condlaw3pre_amend.json"))
    lo, hi = am["ship"]["band_new"]
    lego_p = am["lego_prime"]["drr80"]
    lego_hi = am["lego_prime"]["ci"][1]
    chair = am["chair"]["drr80"]
    chair_lo = am["chair"]["ci"][0]
    d_hat = am["ship"]["D_hat_new"]

    sj = json.load(open(SHIP_JSON))
    row = sj["rows"][KEY]
    d = row["drr"]
    try:
        nl = json.load(open(SHIP_NULL))["rows"][KEY]
        ci = (nl["boot_lo"], nl["boot_hi"])
        null_mean = nl["null_mean"]
    except Exception:
        ci, null_mean = (float("nan"), float("nan")), float("nan")

    primary = bool(lo <= d <= hi)
    mono = bool(lego_p < d < chair)
    interval = bool(am["amended_prereg"]["HARD_GO_FLOOR"] < d < chair_lo)
    secondary = bool(mono and interval)

    print("=" * 78)
    print("CONDLAW-3-PRE STAGE 2 — SHIP UNBLINDED")
    print("=" * 78)
    print(f"  statistic : {KEY}  (2DGS rendered-normal ribbon, mesh-refined classes)")
    print(f"  model     : {sj['model2dgs']}")
    print(f"  views     : {sj['views']}   (frozen held-out TEST)")
    print(f"  n_crease  : {row['n_cre']}    n_distractor : {row['n_dec']}")
    print(f"  AUC       : {row['auc']:.6f}   achieved recall {row['recall']:.6f}")
    print()
    print(f"  DRR@80(ship) = {d:.6f}   95% CI {band_str(*ci)}")
    print(f"  measured chance floor (label permutation) = {null_mean:.4f}")
    print()
    print("-" * 78)
    print("FROZEN GATE (committed 92ce75f, before ship had a model)")
    print("-" * 78)
    print(f"  PRIMARY   affine band {band_str(lo, hi)}   (D_hat {d_hat:.4f})")
    print(f"            ship {d:.4f}  ->  {'PASS' if primary else 'FAIL'}"
          f"{'' if primary else f'   (misses by {min(abs(d-lo), abs(d-hi)):.4f})'}")
    print(f"  SECONDARY monotonic {lego_p:.4f} < ship < {chair:.4f}"
          f"  ->  {'PASS' if mono else 'FAIL'}")
    print(f"            and ship in {band_str(am['amended_prereg']['HARD_GO_FLOOR'], chair_lo)}"
          f"  ->  {'PASS' if interval else 'FAIL'}")
    print(f"            SECONDARY overall  ->  {'PASS' if secondary else 'FAIL'}")
    print()
    verdict = ("PASS (both)" if primary and secondary else
               "PARTIAL — SECONDARY passes, PRIMARY affine band missed"
               if secondary else
               "FAIL (monotonicity broken)" if primary else "FAIL (both)")
    print(f"  VERDICT: {verdict}")

    out = {"ship_drr80": d, "ci": list(ci), "auc": row["auc"], "n_cre": row["n_cre"],
           "n_dist": row["n_dec"], "null_mean": null_mean,
           "recall": row["recall"], "thr": row["thr"],
           "model2dgs": sj["model2dgs"], "views": sj["views"], "statistic": KEY,
           "frozen_band": [lo, hi], "D_hat": d_hat,
           "anchors": {"lego_prime": lego_p, "lego_prime_ci_hi": lego_hi,
                       "chair": chair, "chair_ci_lo": chair_lo},
           "PRIMARY_affine_pass": primary,
           "SECONDARY_monotonic_pass": mono,
           "SECONDARY_interval_pass": interval,
           "SECONDARY_pass": secondary,
           "verdict": verdict,
           "gate_source": "out/condlaw3pre_amend.json @ commit 92ce75f (pre-unblind)"}
    json.dump(out, open("out/condlaw3pre_stage2_verdict.json", "w"), indent=1, default=float)
    print("\nwrote out/condlaw3pre_stage2_verdict.json")
