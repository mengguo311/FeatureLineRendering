#!/usr/bin/env python
"""NG-MEC — FROZEN scorer + thresholds. Committed BEFORE any NG-MEC number exists.

*** ANALYSIS ONLY. Reads jsons run_m1b.py already wrote plus a temporal table. No mesh, no
    GPU, no detector. The NG-MEC gate/consensus/seed path is a separate, mesh-free module. ***

METHOD BEING SCORED. Normal-gated multi-view epipolar consensus culling of TEED proposals on
the EXISTING frozen carrier. The carrier is NOT grown — NG-MEC only removes proposals, which
is the whole point after URS-E2E showed that growing it costs the temporal win.

FROZEN GATE (verbatim from tier1/ngmec_spec.md). GO requires ALL of:
    P@1.5 >= 0.85  on BOTH chair AND lego
    R     >= 0.65  on BOTH chair AND lego
    temporal regression <= 5% relative at EVERY frame count (30/60/120/240) vs the
    teed_native_0.5 baseline, on lego
Otherwise NO-GO.

RECALL FLOOR IS MANDATORY AND IS THE POINT. NG-MEC is a culling operator: it can trivially
buy precision by keeping almost nothing. A precision pass with collapsed recall is NO-GO, so
R is checked with equal force and is never traded away.

STAGE CHOICE, FIXED NOW. The historical end-to-end gate in this repo is quoted on the POINTS
stage — PLAN1_RESULTS.md states 'End-to-end gate P@1.5>=0.85 AND R@1.5>=0.75: FAIL for Plan #1
(0.597/0.521) and for the baseline (0.727/0.533)', which are points numbers. So:
    PRIMARY   points   / "AFTER   pull+prune[tuned]"
    SECONDARY segments / "AFTER   pull+prune[tuned+len]"   (reported, not gated)
Both are computed and printed; the call is made on the primary. LIFT_P vs teed_native_0.5 is
reported for context on both, using teedgen_verdict.analyse() with the reference arm in the
"canny" slot, so no formula is copied.

UNLIKE URS-E2E, P/R IS REPORTED EVEN ON A TEMPORAL FAIL, so the precision mechanism can be
judged independently of its temporal cost. The spec asks for this explicitly.
"""
import argparse, json, os, subprocess, sys

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, os.path.join(TIER1, "scripts"))
import teedgen_verdict as TV
from xmep_verdict import load_arms

P_MIN, R_MIN = 0.85, 0.65
TEMPORAL_MAX_REGRESSION = 0.05          # <=5% relative, at EVERY frame count
FMIN, FMAX = 0.22, 0.50
PRIMARY = ("points", TV.PTS)
SECONDARY = ("segments", TV.SEG)
REF_ARM = "teed_native_0.5"
VIZ_TAG = "ngmec_v1"                    # NEVER empty: an empty tag overwrites protected figures


def manifest():
    r = subprocess.run(["sha256sum", "-c", "out/CMEPI_protected_manifest.sha256"],
                       cwd=TIER1, capture_output=True, text=True)
    ok = sum(1 for l in r.stdout.splitlines() if l.endswith(": OK"))
    bad = [l for l in r.stdout.splitlines() if l.strip() and not l.endswith(": OK")]
    return ok, len(bad)


def rows_for(prefix, arm, kind, stage):
    """Every (f, P, R) for one arm at one stage."""
    arms = load_arms(prefix)
    if arm not in arms:
        return None
    out = []
    for f, d in sorted(arms[arm].items()):
        r = TV.row(d, kind, stage)
        if r:
            out.append({"f": f, "P": r["P1.5"], "R": r["R1.5"],
                        "P25": r["P2.5"], "R25": r["R2.5"], "n": r["n"]})
    return out


def best_gate_point(rows):
    """The frontier point that maximises P subject to R >= R_MIN; None if unreachable."""
    ok = [r for r in rows if r["R"] >= R_MIN]
    if not ok:
        return None
    return max(ok, key=lambda r: r["P"])


def lift_vs_ref(prefix, arm, ref_prefix, kind, stage):
    base = load_arms(ref_prefix)
    dens = load_arms(prefix)
    if REF_ARM not in base or arm not in dens:
        return None
    arms = {"canny": base[REF_ARM], arm: dens[arm]}
    _, res = TV.analyse(arms, kind, stage, FMIN, FMAX)
    rr = [r for r in res[arm]["rows"] if FMIN - 1e-9 <= r["f"] <= FMAX + 1e-9
          and np.isfinite(r["LIFT_P"]) and not r["beyond_canny_Rmax"]]
    if not rr:
        return {"mean": float("nan"), "best": None, "n_rows": 0}
    b = max(rr, key=lambda r: r["LIFT_P"])
    return {"mean": float(np.mean([r["LIFT_P"] for r in rr])),
            "best": {"LIFT_P": b["LIFT_P"], "f": b["f"], "P": b["P"], "R": b["R"]},
            "n_rows": len(rr)}


def temporal_check(ngmec_table, baseline_table):
    d = json.load(open(ngmec_table)); b = json.load(open(baseline_table))
    D, B = d["scenes"]["lego"]["by_frames"], b["scenes"]["lego"]["by_frames"]
    per = {}
    for k in sorted(D, key=int):
        rd = B[k]["B"]["P_pop"] / D[k]["A"]["P_pop"]      # ngmec ratio
        rb = B[k]["B"]["P_pop"] / B[k]["A"]["P_pop"]      # baseline ratio
        per[k] = {"ngmec_ratio": rd, "baseline_ratio": rb, "relative": rd / rb - 1.0,
                  "ngmec_frechet": B[k]["B"]["frechet_median"] / D[k]["A"]["frechet_median"],
                  "baseline_frechet": B[k]["B"]["frechet_median"] / B[k]["A"]["frechet_median"]}
    worst = min(v["relative"] for v in per.values())
    return {"per_frame": per, "worst_relative": worst,
            "pass": bool(worst >= -TEMPORAL_MAX_REGRESSION)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--chair_prefix", default="m1b_chair_ngmec_")
    ap.add_argument("--lego_prefix", default="m1b_lego_ngmec_")
    ap.add_argument("--arm", default="ngmec")
    ap.add_argument("--temporal", default=None)
    ap.add_argument("--baseline_temporal",
                    default="out/m1b_stroke_temporal_table_tcL_tcteed040.json")
    ap.add_argument("--out", default="out/ngmec_verdict.json")
    a = ap.parse_args()

    ok0, bad0 = manifest()
    res = {"thresholds": {"P_MIN": P_MIN, "R_MIN": R_MIN,
                          "temporal_max_regression": TEMPORAL_MAX_REGRESSION,
                          "primary_stage": PRIMARY[1], "secondary_stage": SECONDARY[1],
                          "reference_arm": REF_ARM, "viz_tag": VIZ_TAG},
           "manifest_before": {"ok": ok0, "failures": bad0}, "scenes": {}}

    print("=" * 78)
    print("NG-MEC — FROZEN GO/NO-GO (scorer committed before any NG-MEC number)")
    print("=" * 78)
    print(f"  manifest before: {ok0}/332 OK, {bad0} failures")

    gate_ok = {}
    for scene, prefix, refpre in (("chair", a.chair_prefix, "m1b_chair_tc_"),
                                  ("lego", a.lego_prefix, "m1b_lego_tc_")):
        entry = {}
        for label, (kind, stage) in (("primary", PRIMARY), ("secondary", SECONDARY)):
            rows = rows_for(prefix, a.arm, kind, stage)
            ref = rows_for(refpre, REF_ARM, kind, stage)
            if rows is None:
                entry[label] = {"status": "ARM_MISSING"}
                continue
            gp = best_gate_point(rows)
            entry[label] = {
                "rows": rows, "reference_rows": ref,
                "gate_point": gp,
                "R_max": max(r["R"] for r in rows),
                "P_max": max(r["P"] for r in rows),
                "recall_floor_reachable": gp is not None,
                "P_at_gate": (gp["P"] if gp else None),
                "gate_pass": bool(gp is not None and gp["P"] >= P_MIN),
                "lift": lift_vs_ref(prefix, a.arm, refpre, kind, stage)}
        res["scenes"][scene] = entry
        p = entry.get("primary", {})
        gate_ok[scene] = bool(p.get("gate_pass"))
        print(f"\n  --- {scene} (primary = {PRIMARY[0]}) ---")
        if p.get("status") == "ARM_MISSING":
            print("    ARM MISSING"); continue
        print(f"    R_max {p['R_max']:.4f}  P_max {p['P_max']:.4f}  "
              f"recall floor R>={R_MIN} reachable: {p['recall_floor_reachable']}")
        if p["gate_point"]:
            g = p["gate_point"]
            print(f"    at R>={R_MIN}: best P = {g['P']:.4f} (f={g['f']:.2f}, R={g['R']:.4f}) "
                  f"-> P>={P_MIN}: {'PASS' if g['P'] >= P_MIN else 'FAIL'}")
        else:
            print(f"    no operating point reaches R >= {R_MIN}  -> gate FAIL")

    T = temporal_check(a.temporal, a.baseline_temporal) if a.temporal else None
    if T:
        print(f"\n  --- temporal (lego, vs {REF_ARM}) ---")
        for k, v in T["per_frame"].items():
            print(f"    {k:>4s} frames  ngmec {v['ngmec_ratio']:6.2f}x  "
                  f"baseline {v['baseline_ratio']:6.2f}x  relative {v['relative']:+7.2%}")
        print(f"    worst relative {T['worst_relative']:+.2%}  "
              f"(allowed >= {-TEMPORAL_MAX_REGRESSION:+.0%})  -> "
              f"{'PASS' if T['pass'] else 'FAIL'}")
    res["temporal"] = T

    ok1, bad1 = manifest()
    res["manifest_after"] = {"ok": ok1, "failures": bad1}
    GO = bool(all(gate_ok.values()) and gate_ok and T is not None and T["pass"])
    res["gate_pass_per_scene"] = gate_ok
    res["GO"] = GO
    res["call"] = "GO" if GO else "NO-GO"
    print(f"\n  manifest after: {ok1}/332 OK, {bad1} failures")
    print(f"\n  CALL: {res['call']}")
    json.dump(res, open(a.out, "w"), indent=1, default=float)
    print(f"\nwrote {a.out}")
