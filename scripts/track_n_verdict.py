#!/usr/bin/env python
"""TRACK N — cross-model edge-prior invariance, consensus-only. FROZEN scorer + thresholds.

*** ANALYSIS ONLY. Reads jsons run_m1b.py already wrote plus temporal tables. No mesh, no GPU,
    no detector. ***

FREEZE NOTE. track_n_spec.md says "Commit nothing unless the whole track closes", which
prevents the usual freeze-first commit. Tamper-evidence is preserved instead by hashing this
file BEFORE any Track-N number is computed and recording that digest in
out/track_n_freeze.json; the final commit contains both, so the scorer provably predates the
results.

QUESTION. NG-MEC's consensus-only cull bought free precision on chair (+0.0108 points /
+0.0130 segments at matched f, dR ~ 0) and nothing on lego. Is that a property of LEARNED EDGE
PRIORS IN GENERAL, or of TEED specifically? Track N swaps the proposer for PiDiNet and DexiNed,
both frozen zero-shot, and keeps everything else identical.

FROZEN GO / NO-GO (verbatim from track_n_spec.md):
  GO (invariance CONFIRMED) requires ALL of:
      BOTH detectors, on CHAIR:  mean_dP >= +0.006 (points) AND |mean_dR| <= 0.005
      BOTH detectors replicate the dichotomy: lego mean_dP < +0.003
      chair temporal at 240f no worse than -8.5% relative (parity with TEED's -8.41%)
  NO-GO (TEED-specific): either detector gives chair mean_dP < +0.003 on points
  Between: PARTIAL, reported straight.
The +0.006 bar is deliberately below TEED's own +0.011: the claim under test is SIGN-CONSISTENT
transfer plus the same conditional law, not identical magnitude. A +0.010 bar would be circular
against TEED itself.

METRIC. mean_dP / mean_dR are the mean over the frozen f-grid {0.22,0.30,0.40,0.50} of the
per-f difference against the reference arm teed_native_0.5 at MATCHED f, on the primary stage
points/"AFTER   pull+prune[tuned]" (segments reported alongside). This is exactly the
comparison NG-MEC used, so the TEED number it is judged against is commensurable.
"""
import argparse, json, os, subprocess, sys

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, os.path.join(TIER1, "scripts"))
import teedgen_verdict as TV
from ngmec_verdict import rows_for

F_GRID = [0.22, 0.30, 0.40, 0.50]
CHAIR_DP_GO, CHAIR_DP_NOGO = 0.006, 0.003
CHAIR_DR_MAX = 0.005
LEGO_DP_MAX = 0.003
TEMPORAL_240_MAX_REGRESSION = 0.085
REF = {"chair": "teed05", "lego": "teed_native_0.5"}
DETECTORS = ["pidinet", "dexined"]
VIZ_TAG = "track_n"


def manifest():
    r = subprocess.run(["sha256sum", "-c", "out/CMEPI_protected_manifest.sha256"],
                       cwd=TIER1, capture_output=True, text=True)
    ok = sum(1 for l in r.stdout.splitlines() if l.endswith(": OK"))
    bad = [l for l in r.stdout.splitlines() if l.strip() and not l.endswith(": OK")]
    return ok, len(bad)


def arm_vs_reference(scene, det):
    """rows + mean_dP/mean_dR vs teed_native_0.5 at matched f, both stages."""
    out = {}
    for kind, stage, lbl in (("points", TV.PTS, "points"),
                             ("segments", TV.SEG, "segments")):
        ng = rows_for(f"m1b_{scene}_trackn{det}_", det, kind, stage)
        rf = rows_for(f"m1b_{scene}_tc_", REF[scene], kind, stage)
        if ng is None or rf is None:
            out[lbl] = {"status": "MISSING"}
            continue
        ref = {r["f"]: r for r in rf}
        rows, dps, drs = [], [], []
        for r in ng:
            if not any(abs(r["f"] - f) < 1e-9 for f in F_GRID):
                continue
            rr = ref.get(r["f"])
            if not rr:
                continue
            dp, dr = r["P"] - rr["P"], r["R"] - rr["R"]
            dps.append(dp); drs.append(dr)
            rows.append({"f": r["f"], "P": r["P"], "R": r["R"],
                         "P25": r["P25"], "R25": r["R25"], "n": r["n"],
                         "ref_P": rr["P"], "ref_R": rr["R"], "dP": dp, "dR": dr})
        out[lbl] = {"status": "OK", "rows": rows,
                    "mean_dP": float(np.mean(dps)) if dps else float("nan"),
                    "mean_dR": float(np.mean(drs)) if drs else float("nan"),
                    "n_f": len(rows)}
    return out


def temporal_240(table, baseline):
    if not (table and os.path.exists(table) and os.path.exists(baseline)):
        return None
    d = json.load(open(table)); b = json.load(open(baseline))
    sc = "chair"
    D, B = d["scenes"][sc]["by_frames"], b["scenes"][sc]["by_frames"]
    per = {}
    for k in sorted(D, key=int):
        rd = B[k]["B"]["P_pop"] / D[k]["A"]["P_pop"]
        rb = B[k]["B"]["P_pop"] / B[k]["A"]["P_pop"]
        per[k] = {"ratio": rd, "baseline_ratio": rb, "relative": rd / rb - 1.0}
    return {"per_frame": per, "rel_240": per.get("240", {}).get("relative"),
            "pass": bool(per.get("240", {}).get("relative", -1) >= -TEMPORAL_240_MAX_REGRESSION)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--temporal", nargs="*", default=[],
                    help="det=path pairs for the chair temporal tables")
    ap.add_argument("--baseline_temporal",
                    default="out/m1b_stroke_temporal_table_tc_tcteed.json")
    ap.add_argument("--out", default="out/track_n_invariance.json")
    a = ap.parse_args()

    ok0, bad0 = manifest()
    temp_paths = dict(x.split("=", 1) for x in a.temporal) if a.temporal else {}
    res = {"thresholds": {"chair_dP_GO": CHAIR_DP_GO, "chair_dP_NOGO": CHAIR_DP_NOGO,
                          "chair_dR_max": CHAIR_DR_MAX, "lego_dP_max": LEGO_DP_MAX,
                          "temporal_240_max_regression": TEMPORAL_240_MAX_REGRESSION,
                          "f_grid": F_GRID, "reference_arm": REF, "viz_tag": VIZ_TAG},
           "manifest_before": {"ok": ok0, "failures": bad0},
           "teed_reference_lift": {"chair_points": 0.0108, "chair_segments": 0.0130,
                                   "lego_points": 0.0004, "lego_segments": 0.0022,
                                   "source": "out/ngmec_mechanism.json"},
           "detectors": {}}

    print("=" * 80)
    print("TRACK N — FROZEN GO/NO-GO (scorer hash-stamped before any Track-N number)")
    print("=" * 80)
    print(f"  manifest before: {ok0}/332 OK, {bad0} failures\n")

    chair_go, chair_nogo, dicho, temporal_ok = {}, {}, {}, {}
    for det in DETECTORS:
        entry = {"chair": arm_vs_reference("chair", det),
                 "lego": arm_vs_reference("lego", det)}
        T = temporal_240(temp_paths.get(det), a.baseline_temporal)
        entry["temporal_chair"] = T
        res["detectors"][det] = entry

        cp = entry["chair"].get("points", {})
        lp = entry["lego"].get("points", {})
        if cp.get("status") != "OK":
            print(f"  --- {det}: chair points MISSING/BLOCKED ---")
            chair_go[det] = False; chair_nogo[det] = True; dicho[det] = False
            temporal_ok[det] = bool(T and T["pass"]); continue
        print(f"  --- {det} ---")
        print(f"    chair  points mean_dP {cp['mean_dP']:+.4f}  mean_dR {cp['mean_dR']:+.4f}"
              f"  (GO >= {CHAIR_DP_GO:+.3f}, |dR| <= {CHAIR_DR_MAX})")
        cs = entry["chair"].get("segments", {})
        if cs.get("status") == "OK":
            print(f"    chair  segs   mean_dP {cs['mean_dP']:+.4f}  mean_dR {cs['mean_dR']:+.4f}")
        if lp.get("status") == "OK":
            print(f"    lego   points mean_dP {lp['mean_dP']:+.4f}  "
                  f"(dichotomy needs < {LEGO_DP_MAX:+.3f})")
        if T:
            print(f"    chair temporal 240f relative {T['rel_240']:+.2%}  "
                  f"(allowed >= {-TEMPORAL_240_MAX_REGRESSION:+.1%})  "
                  f"-> {'PASS' if T['pass'] else 'FAIL'}")
        chair_go[det] = bool(cp["mean_dP"] >= CHAIR_DP_GO
                             and abs(cp["mean_dR"]) <= CHAIR_DR_MAX)
        chair_nogo[det] = bool(cp["mean_dP"] < CHAIR_DP_NOGO)
        dicho[det] = bool(lp.get("status") == "OK" and lp["mean_dP"] < LEGO_DP_MAX)
        temporal_ok[det] = bool(T and T["pass"])

    GO = bool(all(chair_go.values()) and all(dicho.values())
              and all(temporal_ok.values()) and len(chair_go) == len(DETECTORS))
    NOGO = bool(any(chair_nogo.values()))
    call = "GO" if GO else ("NO-GO" if NOGO else "PARTIAL")
    ok1, bad1 = manifest()
    res.update({"chair_go_per_detector": chair_go, "chair_nogo_per_detector": chair_nogo,
                "dichotomy_per_detector": dicho, "temporal_per_detector": temporal_ok,
                "manifest_after": {"ok": ok1, "failures": bad1},
                "GO": GO, "call": call})
    print(f"\n  manifest after: {ok1}/332 OK, {bad1} failures")
    print(f"\n  CALL: {call}")
    json.dump(res, open(a.out, "w"), indent=1, default=float)
    print(f"\nwrote {a.out}")
