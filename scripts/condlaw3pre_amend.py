#!/usr/bin/env python
"""CONDLAW-3-PRE Stage-1.5 — amend the calibration onto a SAME-STATISTIC lego anchor.

The Stage-1 freeze calibrated on anchors measured with DIFFERENT statistics:
  chair 0.986  = chair-lineage (2DGS rendered-normal ribbon theta_normal, mesh-refined classes)
  lego  0.512  = lego-lineage  (mesh dihedral on TEED-defined decals)
Stage 2 scores ship with the CHAIR lineage, so the lower anchor was cross-lineage and
confounded flat-mass with statistic-change.  lego has a trained 2DGS on disk, so the
same-statistic anchor was measured directly:

  scripts/condlaw_chair_test.py --scene lego --views test --no_vanilla \
      --model2dgs out/2dgs_lego      ->  out/condlaw_lego_test.json

lego' = the 2DGS[default]|theta_normal|refined DRR@80 there, i.e. IDENTICAL statistic,
identical class construction and identical held-out TEST split to chair's 0.986.

The amendment is UNCONDITIONAL (spec Stage-1.5 task 3): the old lego=0.512 band is
superseded, not kept alongside as an alternative to choose from later.
Ship is NOT touched and NOT unblinded here - only the anchors move.
"""
import json

CHAIR = 0.985772                      # out/condlaw_chair_test.json
CHAIR_CI = (0.9848, 0.9866)           # out/condlaw_chair_null.json
LEGO_OLD = 0.512323                   # out/condlaw_lego_drr.json (lego-lineage)
LEGO_OLD_CI_HI = 0.5281               # out/condlaw_lego_null.json


if __name__ == "__main__":
    lp = json.load(open("out/condlaw_lego_test.json"))
    row = lp["rows"]["2DGS[default]|theta_normal|refined"]
    LEGO_NEW = row["drr"]
    ln = json.load(open("out/condlaw3pre_legoprime_null.json"))["rows"][
        "2DGS[default]|theta_normal|refined"]
    LN_LO, LN_HI = ln["boot_lo"], ln["boot_hi"]

    S = json.load(open("out/condlaw3pre_rhoflat2.json"))["scenes"]
    pre = json.load(open("out/condlaw3pre_prereg.json"))
    R = "0.04"
    rl, rc = S["lego"]["by_R"][R]["rho_flat"], S["chair"]["by_R"][R]["rho_flat"]
    t_ship = (S["ship"]["by_R"][R]["rho_flat"] - rl) / (rc - rl)

    d_old = LEGO_OLD + t_ship * (CHAIR - LEGO_OLD)
    d_new = LEGO_NEW + t_ship * (CHAIR - LEGO_NEW)

    # same amendment applied to every scalar variant, for the disclosure Stage 1 made
    allv = {}
    for vn, r in pre["variants"].items():
        t = r["cands"]["ship"]["t"]
        allv[vn] = LEGO_NEW + t * (CHAIR - LEGO_NEW)

    print(f"SAME-STATISTIC LEGO RE-ANCHOR  (out/condlaw_lego_test.json)")
    print(f"  statistic : 2DGS[default] theta_normal, refined (mesh FLAT<5 / SHARP>20)")
    print(f"  model     : {lp['model2dgs']}")
    print(f"  views     : {lp['views']}  (frozen TEST)")
    print(f"  lego' DRR@80 = {LEGO_NEW:.6f}   95% CI [{LN_LO:.4f}, {LN_HI:.4f}]"
          f"   AUC {row['auc']:.4f}   n_cre {row['n_cre']}  n_fab {row['n_dec']}")
    print(f"  chance floor (measured null) = {ln['null_mean']:.4f}")
    print(f"\n  shift vs the old lego-lineage anchor: "
          f"{LEGO_NEW:.4f} - {LEGO_OLD:.4f} = {LEGO_NEW - LEGO_OLD:+.4f}")

    gate = "GO" if 0.40 <= LEGO_NEW <= 0.62 else ("NO-GO(>=0.723)" if LEGO_NEW >= 0.723
                                                  else "OUTSIDE sanity band")
    print(f"  frozen sanity gate [0.40, 0.62] -> {gate}")

    print(f"\nSHIP CALIBRATION  (t = {t_ship:.4f}, unchanged - rho_flat is untouched)")
    print(f"{'anchors':38s} {'D_hat':>8s}  {'band':>18s}  {'PRIMARY interval':>22s}")
    print(f"{'OLD  (lego 0.512 lego-lineage)':38s} {d_old:8.4f}  "
          f"[{d_old-0.08:.3f}, {d_old+0.08:.3f}]  "
          f"({LEGO_OLD_CI_HI:.4f}, {CHAIR_CI[0]:.4f})")
    print(f"{'NEW  (lego 0.433 SAME-statistic)':38s} {d_new:8.4f}  "
          f"[{d_new-0.08:.3f}, {d_new+0.08:.3f}]  "
          f"({LN_HI:.4f}, {CHAIR_CI[0]:.4f})")
    print(f"\n  D_hat(ship) across all 7 scalar variants, amended: "
          f"[{min(allv.values()):.3f}, {max(allv.values()):.3f}]")

    out = {
        "amendment": "Stage-1.5 same-statistic lego re-anchor; supersedes the Stage-1 band",
        "lego_prime": {"drr80": LEGO_NEW, "ci": [LN_LO, LN_HI], "auc": row["auc"],
                       "thr": row["thr"], "recall": row["recall"],
                       "n_crease": row["n_cre"], "n_distractor": row["n_dec"],
                       "null_mean": ln["null_mean"],
                       "statistic": "2DGS[default] theta_normal, refined",
                       "source": "out/condlaw_lego_test.json",
                       "ci_source": "out/condlaw3pre_legoprime_null.json",
                       "model2dgs": lp["model2dgs"], "views": lp["views"]},
        "lego_old": {"drr80": LEGO_OLD, "ci_hi": LEGO_OLD_CI_HI,
                     "statistic": "mesh dihedral on TEED decals (lego-lineage)",
                     "source": "out/condlaw_lego_drr.json"},
        "chair": {"drr80": CHAIR, "ci": list(CHAIR_CI),
                  "source": "out/condlaw_chair_test.json"},
        "shift_lego": LEGO_NEW - LEGO_OLD,
        "sanity_gate": {"band": [0.40, 0.62], "nogo_at": 0.723, "verdict": gate},
        "ship": {"t": t_ship, "rho_flat_R0.04": S["ship"]["by_R"][R]["rho_flat"],
                 "D_hat_old": d_old, "band_old": [d_old - 0.08, d_old + 0.08],
                 "D_hat_new": d_new, "band_new": [d_new - 0.08, d_new + 0.08],
                 "D_hat_new_all_variants": allv,
                 "D_hat_new_range": [min(allv.values()), max(allv.values())]},
        "amended_prereg": {
            "PRIMARY_monotonicity": f"{LN_HI:.4f} < DRR@80(ship) < {CHAIR_CI[0]:.4f}, "
                                    f"ordered lego' < ship < chair, ALL SAME-STATISTIC",
            "SECONDARY_affine_band": [d_new - 0.08, d_new + 0.08],
            "HARD_GO_FLOOR": LN_HI,
            "falsified_if": f"DRR@80(ship) <= {LN_HI:.4f} or >= {CHAIR_CI[0]:.4f}",
            "pipeline": "scripts/condlaw_chair_test.py --scene ship --views test "
                        "--no_vanilla --model2dgs out/2dgs_ship, statistic "
                        "2DGS[default] theta_normal refined"},
    }
    json.dump(out, open("out/condlaw3pre_amend.json", "w"), indent=1, default=float)
    print("\nwrote out/condlaw3pre_amend.json")
