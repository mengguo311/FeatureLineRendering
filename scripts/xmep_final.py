#!/usr/bin/env python
"""XMEP — final verdict under BOTH metric variants, with the primary chosen by the spec.

The frozen scorer (scripts/xmep_verdict.py, committed 2dd8d8c before any lift existed) chose
points / pull+prune[tuned] with the Pareto-envelope lower bound LIFT_P_lb over the FULL canny
frontier (f up to 1.00). That was a MIS-SPECIFICATION: xmep_spec.md mandates "the SAME
frontier-outward lift used for TEED on chair ... (+0.0607)", and +0.0607 is reproduced only by

    segments / pull+prune[tuned+len],
    INTERPOLATED canny P at the same recall (not the envelope),
    rows beyond canny's reach EXCLUDED,
    canny frontier restricted to f in {0.15,0.22,0.30,0.35,0.40,0.45,0.50}

which returns teed05 = +0.0607 at f=0.40 (segP 0.6148, segR 0.7207), byte-matching
RECALL_RESULTS.md:198. Comparing a lift measured one way against a threshold derived from a
lift measured another way is apples-to-oranges, and here it is GENEROUS: the frozen variant
scores teed05 at +0.0800, ~32% above the reference it is normalised by.

So the PRIMARY reported number is the spec-compliant one. The frozen-variant number is
reported beside it, unchanged, so the discrepancy is auditable rather than buried.
"""
import json, os, sys

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, os.path.join(TIER1, "scripts"))
import teedgen_verdict as TV
from xmep_verdict import load_arms, TEED_LIFT_P_REF, GO_FRAC, NOGO_FRAC, GO_ABS, NOGO_ABS

PUB_CANNY_F = [0.15, 0.22, 0.30, 0.35, 0.40, 0.45, 0.50]
ARMS = ["teed05", "teed09", "pidinet_native_0.5", "pidinet_native_0.9",
        "dexined_native_0.5", "dexined_native_0.7"]
PRIMARY = "pidinet_native_0.5"


def best(res, arm, use_lb, drop_beyond):
    if arm not in res:
        return None
    key = "LIFT_P_lb" if use_lb else "LIFT_P"
    rr = [r for r in res[arm]["rows"] if 0.22 - 1e-9 <= r["f"] <= 0.50 + 1e-9
          and np.isfinite(r[key]) and not (drop_beyond and r["beyond_canny_Rmax"])]
    if not rr:
        return None
    b = max(rr, key=lambda r: r[key])
    return {"LIFT_P": b[key], "f": b["f"], "P": b["P"], "R": b["R"],
            "matched_f_dP": b["matched_f_dP"], "matched_f_dR": b["matched_f_dR"]}


def call_of(lift):
    return "GO" if lift >= GO_ABS else ("NO-GO" if lift < NOGO_ABS else "PARTIAL")


if __name__ == "__main__":
    full = load_arms("m1b_chair_tc_")
    pub = dict(full)
    pub["canny"] = {f: d for f, d in full["canny"].items() if f in PUB_CANNY_F}

    _, res_pub = TV.analyse(pub, "segments", TV.SEG, 0.22, 0.50)
    _, res_frz = TV.analyse(full, "points", TV.PTS, 0.22, 0.50)

    out = {"thresholds": {"TEED_LIFT_P_REF": TEED_LIFT_P_REF, "GO_abs": GO_ABS,
                          "NOGO_abs": NOGO_ABS, "GO_frac": GO_FRAC,
                          "NOGO_frac": NOGO_FRAC},
           "primary_metric": "segments/pull+prune[tuned+len], interpolated canny P@R, "
                             "beyond-reach excluded, canny frontier f<=0.50 "
                             "(reproduces the published +0.0607 exactly)",
           "frozen_script_metric": "points/pull+prune[tuned], Pareto-envelope LIFT_P_lb, "
                                   "full canny frontier f<=1.00 (MIS-SPECIFIED vs the spec)",
           "arms": {}}
    hdr = (f"{'arm':22s} | {'PRIMARY (spec)':>16s} {'frac':>6s} {'call':>8s} | "
           f"{'frozen variant':>15s} {'frac':>6s} {'call':>8s}")
    print(hdr); print("-" * len(hdr))
    for a in ARMS:
        bp = best(res_pub, a, use_lb=False, drop_beyond=True)
        bf = best(res_frz, a, use_lb=True, drop_beyond=False)
        row = {"primary": bp, "frozen_variant": bf}
        if bp:
            row["primary_frac"] = bp["LIFT_P"] / TEED_LIFT_P_REF
            row["primary_call"] = call_of(bp["LIFT_P"])
        if bf:
            row["frozen_frac"] = bf["LIFT_P"] / TEED_LIFT_P_REF
            row["frozen_call"] = call_of(bf["LIFT_P"])
        out["arms"][a] = row
        print(f"{a:22s} | {bp['LIFT_P']:+16.4f} {row['primary_frac']:6.3f} "
              f"{row['primary_call']:>8s} | {bf['LIFT_P']:+15.4f} "
              f"{row['frozen_frac']:6.3f} {row['frozen_call']:>8s}")

    p = out["arms"][PRIMARY]
    out["primary_arm"] = PRIMARY
    out["headline"] = {"arm": PRIMARY, "LIFT_P": p["primary"]["LIFT_P"],
                       "fraction_of_TEED": p["primary_frac"], "call": p["primary_call"]}
    print(f"\nHEADLINE  {PRIMARY}:  LIFT_P {p['primary']['LIFT_P']:+.4f}  "
          f"= {p['primary_frac']:.3f} of TEED's +0.0607  ->  {p['primary_call']}")
    print(f"  (frozen-variant number, mis-specified: {p['frozen']['LIFT_P']:+.4f} "
          f"= {p['frozen_frac']:.3f} -> {p['frozen_call']})"
          if False else
          f"  (frozen-variant number, mis-specified: {p['frozen_variant']['LIFT_P']:+.4f} "
          f"= {p['frozen_frac']:.3f} -> {p['frozen_call']})")
    json.dump(out, open(os.path.join(TIER1, "out/xmep_final.json"), "w"),
              indent=1, default=float)
    print("\nwrote out/xmep_final.json")
