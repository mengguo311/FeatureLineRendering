"""CMEPI — the cross-model edge-prior invariance table and the FROZEN GO/NO-GO verdict.

*** ANALYSIS ONLY — reads the jsons run_m1b.py already wrote.  No mesh, no GPU. ***

Every number here is produced by `teedgen_verdict.analyse`, the SAME function that produced
the published TEED chair and lego LIFT_P numbers, called on the SAME `m1b_<scene>_tc_` arm
glob, so the Canny f-frontier each arm is scored against is literally the published one
(chair 14 swept f out to 1.00, lego 16 out to 1.00).  Nothing about the estimator is new;
only the detector that fed the M1a photometric DT is.

THE RULE, frozen in tier1/cmepi_spec.md before any non-TEED number existed:

  GO (invariance CONFIRMED)  at least ONE non-TEED learned detector reproduces LIFT_P > 0
                             for f in [0.30, 0.50] on chair AND non-negative best-LIFT_P on
                             lego.  => the lift is a property of learned priors, not TEED.
  NO-GO (TEED-specific)      all non-TEED learned detectors give LIFT_P <= 0 across
                             f in [0.30, 0.50] on chair.
  CONDITIONAL                lift holds on chair but reverses on lego for all detectors
                             => confirms the hard-surface headroom limit already seen.

TWO READINGS OF "LIFT_P > 0 for f in [0.30,0.50]", AND BOTH ARE REPORTED
    The verdict script's own frozen GO-a leg is "LIFT_P > 0 at SOME f in the band"; the
    English of the CMEPI rule can also be read as "at EVERY f in the band".  These can
    disagree, so the table prints n_pos/n_band for every arm and the verdict is stated under
    both readings.  A result that is positive at all 5 band points satisfies them jointly and
    needs no adjudication.

TWO ESTIMATORS, ALSO BOTH REPORTED
    LIFT_P     precision minus the CANNY frontier INTERPOLATED to the same recall.  Smooth,
               and what the published chair report headlines.
    LIFT_P_lb  precision minus the Pareto ENVELOPE (best precision the Canny f-dial reaches
               while ALSO reaching at least that recall), with a conservative lower bound
               when the arm is beyond Canny's swept R_max.  Well-posed even on lego, whose
               frontier is not a trade-off curve (its P RISES with R).  This is what the
               verdict script's GO-a actually reads.
    The published TEED figures are quoted in the same pair, so the comparison is symmetric.

WHAT THE TWO ESTIMATORS ACTUALLY DO ON THESE TWO SCENES -- measured, not assumed
    "LIFT_P_lb" is NOT the conservative estimator here, and its name is inoperative:
    * The `beyond_canny_Rmax` lower-bound branch of teedgen_verdict.lift_lb NEVER FIRES in
      this experiment -- no arm at any f on either scene reaches the Canny dial's own R_max
      (chair closest is 0.0348 short, lego 0.0290 short).  So LIFT_P_lb == LIFT_P_env
      everywhere below, and no denominator is ever switched.
    * ON CHAIR the Canny frontier is strictly P-decreasing in R, so env_P_at_R <= interp_P_at_R
      at every row and LIFT_P_lb >= LIFT_P ALWAYS.  The envelope there is the GENEROUS
      estimator, inflated purely by the coarseness of the Canny f-grid: scoring the Canny arm
      against ITSELF at off-grid recalls gives a null envelope-lift of +0.0009..+0.0290.  An
      arm whose envelope lift is below its own off-grid null has not cleared the frontier.
      (This is exactly what separates pidinet_native_0.9 -- whose two sign-flipped cells sit
      BELOW that null -- from every DexiNed / TEED / pidinet@0.5 band cell, which sit above
      it, equivalently which are positive on the INTERPOLATED estimator too.)
    * ON LEGO the Canny frontier's P RISES with R, so env_P_at_R returns the global maximum
      precision for every arm at every f: lego's envelope lift degenerates to "arm precision
      minus Canny's single best precision" and does no recall matching at all.  The same
      self-scoring null is NEGATIVE there (-0.0104..-0.0164 in band), i.e. lego envelope
      numbers are conservative.
    CONSEQUENCE FOR READING THE TABLE: treat the INTERPOLATED column as primary on chair, and
    require an arm to be positive on BOTH columns before calling it above the frontier.
"""
import os
import sys
import json
import glob
import argparse

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from teedgen_verdict import analyse, SEG                       # noqa: E402

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
OUT = os.path.join(TIER1, "out")

# the published frozen-zero-shot control, per scene (the arm names differ by scene for
# historical reasons: chair's TRACK C predates lego's TRACK L naming)
TEED_ARM = {"chair": "teed05", "lego": "teed_native_0.5"}
# every arm that is a FROZEN ZERO-SHOT LEARNED detector -- the population the CMEPI rule
# quantifies over.  Canny variants are re-tuned classical baselines, not learned priors.
def is_learned(name):
    return name.startswith(("teed", "union", "pidinet", "dexined"))


def is_cmepi(name):
    return name.startswith(("pidinet", "dexined"))


def load(prefix):
    arms = {}
    for p in sorted(glob.glob(os.path.join(OUT, prefix + "*.json"))):
        tag = os.path.basename(p)[len(prefix):-len(".json")]
        if "_f" not in tag:
            sys.exit(f"malformed arm file (no _f<value>): {p}")
        name, f = tag.rsplit("_f", 1)
        arms.setdefault(name, {})[float(f)] = json.load(open(p))
    return arms


def band_stats(rows, metric, fmin, fmax):
    band = [r for r in rows if fmin - 1e-9 <= r["f"] <= fmax + 1e-9]
    fin = [r for r in band if np.isfinite(r[metric])]
    pos = [r for r in fin if r[metric] > 0]
    best = max(fin, key=lambda r: r[metric]) if fin else None
    return {
        "n_band": len(band), "n_finite": len(fin), "n_pos": len(pos),
        "best": (best[metric] if best else float("nan")),
        "best_f": (best["f"] if best else float("nan")),
        "f_pos": sorted(r["f"] for r in pos),
        "min_in_band": (min(r[metric] for r in fin) if fin else float("nan")),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", nargs="+", default=["chair", "lego"])
    ap.add_argument("--fmin", type=float, default=0.30)
    ap.add_argument("--fmax", type=float, default=0.50)
    ap.add_argument("--out", default=os.path.join(OUT, "cmepi_table.json"))
    args = ap.parse_args()

    doc = {"fband": [args.fmin, args.fmax], "scenes": {}}

    for scene in args.scenes:
        arms = load(f"m1b_{scene}_tc_")
        if "canny" not in arms:
            sys.exit(f"no canny frontier arm for {scene}")
        front, res = analyse(arms, "segments", SEG, args.fmin, args.fmax)
        Rmax_c = max(x[0] for x in front)
        Pmax_c = max(x[1] for x in front)

        print("=" * 126)
        print(f"CMEPI — {scene.upper()}, held-out TEST, segments headline stage "
              f"'{SEG.strip()}'.  Canny f-frontier: {len(front)} swept f, "
              f"R [{min(x[0] for x in front):.4f},{Rmax_c:.4f}] "
              f"P [{min(x[1] for x in front):.4f},{Pmax_c:.4f}]")
        print("=" * 126)

        FS = sorted({r["f"] for v in res.values() for r in v["rows"]}, reverse=True)
        for metric, label in (("LIFT_P", "INTERPOLATED"), ("LIFT_P_lb", "PARETO-ENVELOPE")):
            print(f"\n--- LIFT_P per f, {label} estimator "
                  f"(>0 = above the Canny frontier the f-dial cannot buy) ---")
            print(f"{'arm':>22} " + "".join(f"{'f=%.2f' % f:>9}" for f in FS)
                  + f"{'best@band':>11}{'n>0/band':>10}")
            order = ([TEED_ARM[scene]]
                     + sorted(n for n in res if is_cmepi(n))
                     + sorted(n for n in res if is_learned(n) and n != TEED_ARM[scene]
                              and not is_cmepi(n))
                     + sorted(n for n in res if not is_learned(n)))
            for n in order:
                if n not in res:
                    continue
                m = {r["f"]: r[metric] for r in res[n]["rows"]}
                cells = "".join((f"{m[f]:+9.4f}" if f in m and np.isfinite(m[f])
                                 else f"{'':>9}") for f in FS)
                b = band_stats(res[n]["rows"], metric, args.fmin, args.fmax)
                mark = " *CMEPI" if is_cmepi(n) else (" *CTRL" if n == TEED_ARM[scene] else "")
                print(f"{n:>22} {cells}{b['best']:+11.4f}"
                      f"{b['n_pos']:>6d}/{b['n_finite']:<3d}{mark}")

        # ---- the reach question: does the arm get to recalls the Canny dial never reaches?
        print(f"\n--- reach: R_max and precision there, vs the Canny dial swept to f=1.00 ---")
        print(f"{'arm':>22} {'R_max':>8} {'dR vs canny':>12} {'P at R_max':>11} "
              f"{'#pts beyond':>12} {'#dominate':>10}")
        for n in order:
            if n not in res:
                continue
            v = res[n]
            pr = max((r for r in v["rows"]), key=lambda r: r["R"])
            print(f"{n:>22} {v['R_max']:8.4f} {v['dR_max']:+12.4f} {pr['P']:11.4f} "
                  f"{v['n_beyond_canny_Rmax']:12d} {v['n_dominating_whole_frontier']:10d}")

        doc["scenes"][scene] = {
            "frontier": front, "canny_R_max": Rmax_c, "canny_P_max": Pmax_c,
            "teed_control_arm": TEED_ARM[scene],
            "arms": {n: {
                "rows": res[n]["rows"],
                "is_cmepi": is_cmepi(n), "is_learned": is_learned(n),
                "R_max": res[n]["R_max"], "dR_max": res[n]["dR_max"],
                "n_beyond_canny_Rmax": res[n]["n_beyond_canny_Rmax"],
                "n_dominating_whole_frontier": res[n]["n_dominating_whole_frontier"],
                "band_LIFT_P": band_stats(res[n]["rows"], "LIFT_P", args.fmin, args.fmax),
                "band_LIFT_P_lb": band_stats(res[n]["rows"], "LIFT_P_lb",
                                             args.fmin, args.fmax),
            } for n in res},
        }

    # ---------------------------------------------- how much of the TEED lift is reproduced
    # "Carried fraction" = LIFT_P(non-TEED learned detector) / LIFT_P(TEED), best-in-band.
    # This is the quantitative form of the invariance question: 1.0 would mean the swap costs
    # nothing, 0.0 that the lift was TEED's alone.  It is only meaningful where the TEED
    # reference lift is itself positive, so the denominator is printed alongside it.
    print("\n" + "=" * 126)
    print(f"CARRIED FRACTION of the TEED lift, best-in-band f in "
          f"[{args.fmin}, {args.fmax}]   (LIFT_P(arm) / LIFT_P(TEED control))")
    print("=" * 126)
    print("{:>22} {:>10} {:>12} {:>10} {:>12} {:>10}".format(
        "scene / arm", "interp", "TEED interp", "carried", "TEED env", "carried"))
    for scene in doc["scenes"]:
        sc = doc["scenes"][scene]
        ref = sc["arms"].get(sc["teed_control_arm"])
        if ref is None:
            continue
        ri, re_ = ref["band_LIFT_P"]["best"], ref["band_LIFT_P_lb"]["best"]
        print(f"  --- {scene} (TEED control = {sc['teed_control_arm']}) ---")
        for n in sorted(k for k in sc["arms"] if sc["arms"][k]["is_cmepi"]):
            a = sc["arms"][n]
            ai, ae = a["band_LIFT_P"]["best"], a["band_LIFT_P_lb"]["best"]
            ci = ai / ri if abs(ri) > 1e-9 else float("nan")
            ce = ae / re_ if abs(re_) > 1e-9 else float("nan")
            print("{:>22} {:>+10.4f} {:>+12.4f} {:>10.2f} {:>+12.4f} {:>10.2f}".format(
                n, ai, ri, ci, re_, ce))
            sc["arms"][n]["carried_fraction_interp"] = ci
            sc["arms"][n]["carried_fraction_env"] = ce

    # ------------------------------------------------------------------ THE FROZEN VERDICT
    print("\n" + "=" * 126)
    print(f"CMEPI FROZEN GO/NO-GO  (band f in [{args.fmin}, {args.fmax}], "
          f"held-out TEST, segments headline stage)")
    print("=" * 126)

    cm = sorted({n for s in doc["scenes"].values() for n in s["arms"] if s["arms"][n]["is_cmepi"]})
    verdict = {"per_detector": {}}
    for n in cm:
        row = {}
        for scene in doc["scenes"]:
            a = doc["scenes"][scene]["arms"].get(n)
            if a is None:
                continue
            row[scene] = {
                "best_LIFT_P": a["band_LIFT_P"]["best"],
                "best_LIFT_P_lb": a["band_LIFT_P_lb"]["best"],
                "n_pos_LIFT_P": a["band_LIFT_P"]["n_pos"],
                "n_pos_LIFT_P_lb": a["band_LIFT_P_lb"]["n_pos"],
                "n_band": a["band_LIFT_P"]["n_finite"],
                "n_band_interp": a["band_LIFT_P"]["n_finite"],
                "n_band_env": a["band_LIFT_P_lb"]["n_finite"],
                "f_pos_LIFT_P": a["band_LIFT_P"]["f_pos"],
                "f_pos_LIFT_P_lb": a["band_LIFT_P_lb"]["f_pos"],
            }
        if "chair" in row:
            c = row["chair"]
            # "at SOME f" (the verdict script's own frozen GO-a leg) and "at EVERY f" (the
            # other reading of the CMEPI rule's English), each stated PER ESTIMATOR.  Mixing
            # them -- n_pos from the envelope against n_band from the interpolant -- would
            # report an arm as unanimously positive on the strength of the estimator that is
            # GENEROUS on chair.  See the estimator caveat in the module docstring.
            row["chair_GO_some_f_interp"] = bool(c["best_LIFT_P"] > 0)
            row["chair_GO_some_f_env"] = bool(c["best_LIFT_P_lb"] > 0)
            row["chair_GO_some_f"] = bool(c["best_LIFT_P"] > 0 or c["best_LIFT_P_lb"] > 0)
            row["chair_GO_every_f_interp"] = bool(c["n_band_interp"] > 0
                                                  and c["n_pos_LIFT_P"] == c["n_band_interp"])
            row["chair_GO_every_f_env"] = bool(c["n_band_env"] > 0
                                               and c["n_pos_LIFT_P_lb"] == c["n_band_env"])
            row["chair_GO_every_f_BOTH"] = bool(row["chair_GO_every_f_interp"]
                                                and row["chair_GO_every_f_env"])
        if "lego" in row:
            g = row["lego"]
            row["lego_nonneg_interp"] = bool(g["best_LIFT_P"] >= 0)
            row["lego_nonneg_env"] = bool(g["best_LIFT_P_lb"] >= 0)
            row["lego_nonneg"] = bool(g["best_LIFT_P"] >= 0 or g["best_LIFT_P_lb"] >= 0)
            row["lego_nonneg_BOTH"] = bool(row["lego_nonneg_interp"]
                                           and row["lego_nonneg_env"])
        verdict["per_detector"][n] = row

    hdr = ("{:>22} | {:>17} {:>9} {:>7} | {:>16} {:>9} {:>7} | {:>8} {:>8}".format(
        "detector arm", "chair interp", "chair env", "n>0 env", "lego interp", "lego env", "n>0 env",
        "chair>0", "lego>=0"))
    print(hdr)
    print("-" * len(hdr))

    def cell(d, key, fmt):
        return format(d[key], fmt) if d else "-"

    def frac(d):
        return "{}/{}".format(d["n_pos_LIFT_P_lb"], d["n_band"]) if d else "-"

    for n, row in verdict["per_detector"].items():
        c, g = row.get("chair"), row.get("lego")
        print("{:>22} | {:>17} {:>9} {:>7} | {:>16} {:>9} {:>7} | {:>8} {:>8}".format(
            n,
            cell(c, "best_LIFT_P", "+.4f"), cell(c, "best_LIFT_P_lb", "+.4f"), frac(c),
            cell(g, "best_LIFT_P", "+.4f"), cell(g, "best_LIFT_P_lb", "+.4f"), frac(g),
            str(row.get("chair_GO_some_f")), str(row.get("lego_nonneg"))))

    # The NO-GO leg quantifies over non-TEED learned detectors THAT WERE RUN ON CHAIR.  An
    # arm with no chair run (lego-only sensitivity arm) must not silently vote "chair failure".
    ran_chair = [n for n, r in verdict["per_detector"].items() if "chair" in r]
    any_chair = [n for n in ran_chair if verdict["per_detector"][n].get("chair_GO_some_f")]
    both = [n for n in any_chair if verdict["per_detector"][n].get("lego_nonneg")]
    # the strict reading: positive at EVERY band f under BOTH estimators on chair, and
    # non-negative under BOTH estimators on lego
    both_strict = [n for n in ran_chair
                   if verdict["per_detector"][n].get("chair_GO_every_f_BOTH")
                   and verdict["per_detector"][n].get("lego_nonneg_BOTH")]
    all_chair_fail = len(any_chair) == 0 and len(ran_chair) > 0
    # the CONDITIONAL leg, evaluated PER DETECTOR as well as globally: an arm that is positive
    # on chair and reverses on lego is exactly the spec's CONDITIONAL case, even when some
    # OTHER detector rescues the global GO.
    conditional_arms = [n for n in any_chair
                        if not verdict["per_detector"][n].get("lego_nonneg")]
    if both:
        v = "GO — INVARIANCE CONFIRMED"
    elif all_chair_fail:
        v = "NO-GO — TEED-SPECIFIC"
    elif any_chair:
        v = "CONDITIONAL — holds on chair, reverses on lego for all detectors"
    else:
        v = "INDETERMINATE"
    verdict["chair_positive_detectors"] = any_chair
    verdict["chair_and_lego_detectors"] = both
    verdict["chair_and_lego_detectors_STRICT"] = both_strict
    verdict["conditional_arms_chair_yes_lego_no"] = conditional_arms
    verdict["arms_with_chair_run"] = ran_chair
    verdict["VERDICT"] = v
    print(f"\n  arms with a chair run            : {ran_chair}")
    print(f"  chair LIFT_P>0 somewhere in band : {any_chair or 'none'}")
    print(f"  ...and lego best-LIFT_P >= 0     : {both or 'none'}")
    print(f"  STRICT (every band f, BOTH estimators, both scenes): {both_strict or 'none'}")
    print(f"  CONDITIONAL per-arm (chair yes, lego reverses)    : "
          f"{conditional_arms or 'none'}")
    print(f"\n  ==> {v}")

    doc["verdict"] = verdict
    json.dump(doc, open(args.out, "w"), indent=2, default=float)
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
