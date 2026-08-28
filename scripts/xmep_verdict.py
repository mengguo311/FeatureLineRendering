#!/usr/bin/env python
"""XMEP — Cross-Model Edge-Prior Invariance. FROZEN GO/NO-GO, committed BEFORE any lift.

*** ANALYSIS ONLY. Reads jsons run_m1b.py already wrote. No mesh, no GPU, no detector. ***

QUESTION. The paper's mechanism claim is that a frozen zero-shot LEARNED edge prior buys
RANKABLE seeds that push the precision/recall frontier OUTWARD. That currently rests entirely
on TEED (BIPED weights). Is the lift a property of learned edge priors in general, or a
TEED-specific artifact? This scores a second frozen zero-shot learned detector on the
identical pipeline and asks what fraction of TEED's lift it reproduces.

METRIC (CORRECTED 2026-08-29 — see the note below).
PRIMARY = the SPEC metric, i.e. exactly the lift that produced the published TEED chair
reference +0.0607:
    segments / pull+prune[tuned+len]
    INTERPOLATED canny P at the same recall (not the Pareto envelope)
    rows beyond canny's reach EXCLUDED
    canny frontier restricted to f in {0.15,0.22,0.30,0.35,0.40,0.45,0.50}
Verified: this returns teed05 = +0.0607 at f=0.40 (segP 0.6148, segR 0.7207), byte-matching
RECALL_RESULTS.md:198.

SECONDARY (labelled, retained for the audit trail) = the variant this script originally froze:
points / pull+prune[tuned], Pareto-envelope lower bound LIFT_P_lb, FULL canny frontier
(f <= 1.00). That variant is MIS-SPECIFIED against the spec's own reference: it scores TEED
itself at +0.0800, ~32% above the +0.0607 the thresholds are normalised by, so comparing it
to those thresholds is apples-to-oranges and generous. It is reported, never used for the call.

teedgen_verdict.analyse() is called directly for both, so no formula is copied and the
numbers cannot drift from the published ones.

FROZEN THRESHOLDS (verbatim from tier1/xmep_spec.md; TEED chair reference LIFT_P = +0.0607):
    GO       LIFT_P >= 0.70 * 0.0607 = +0.04249   mechanism generalises
             AND temporal manifest no-regress
             AND gate directions consistent with TEED (recall up, precision drop modest,
                 frontier outward not inward)
    NO-GO    LIFT_P <  0.30 * 0.0607 = +0.01821   TEED-specific alignment
    PARTIAL  fraction in [0.30, 0.70)             reported straight, no spin

Nothing here may be adjusted after a number is seen.
"""
import argparse, glob, json, os, subprocess, sys

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
OUT = os.path.join(TIER1, "out")
sys.path.insert(0, os.path.join(TIER1, "scripts"))
import teedgen_verdict as TV                                      # identical LIFT_P math

TEED_LIFT_P_REF = 0.0607
GO_FRAC, NOGO_FRAC = 0.70, 0.30
GO_ABS = GO_FRAC * TEED_LIFT_P_REF
NOGO_ABS = NOGO_FRAC * TEED_LIFT_P_REF
FMIN, FMAX = 0.22, 0.50
# PRIMARY = spec metric; SECONDARY = the originally-frozen mis-specified variant.
KIND, STAGE = "segments", TV.SEG                  # primary
KIND2, STAGE2 = "points", TV.PTS                  # secondary, labelled
PUB_CANNY_F = [0.15, 0.22, 0.30, 0.35, 0.40, 0.45, 0.50]


def load_arms(prefix):
    arms = {}
    for p in sorted(glob.glob(os.path.join(OUT, prefix + "*.json"))):
        tag = os.path.basename(p)[len(prefix):-len(".json")]
        if "_f" not in tag:
            continue
        name, fs = tag.rsplit("_f", 1)
        try:
            f = float(fs)
        except ValueError:
            continue
        arms.setdefault(name, {})[f] = json.load(open(p))
    return arms


def manifest_ok():
    r = subprocess.run(["sha256sum", "-c", "out/CMEPI_protected_manifest.sha256"],
                       cwd=TIER1, capture_output=True, text=True)
    ok = sum(1 for l in r.stdout.splitlines() if l.endswith(": OK"))
    bad = [l for l in r.stdout.splitlines() if l.strip() and not l.endswith(": OK")]
    return ok, len(bad)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="m1b_chair_tc_")
    ap.add_argument("--arm", required=True, help="the cross-model arm, e.g. pidinet_native_0.5")
    ap.add_argument("--teed_arm", default="teed05", help="TEED arm, for the in-run reference")
    ap.add_argument("--out", default="out/xmep_verdict.json")
    a = ap.parse_args()

    full = load_arms(a.prefix)
    if "canny" not in full:
        sys.exit(f"no canny frontier under prefix {a.prefix}")
    if a.arm not in full:
        sys.exit(f"arm {a.arm} not found; have {sorted(full)}")
    pub = dict(full)
    pub["canny"] = {f: d for f, d in full["canny"].items() if f in PUB_CANNY_F}
    front, res = TV.analyse(pub, KIND, STAGE, FMIN, FMAX)            # PRIMARY, spec metric
    _, res2 = TV.analyse(full, KIND2, STAGE2, FMIN, FMAX)            # SECONDARY, mis-specified

    def summarise(name, R=None, key="LIFT_P", drop_beyond=True):
        R = res if R is None else R
        rows = [r for r in R[name]["rows"] if FMIN - 1e-9 <= r["f"] <= FMAX + 1e-9
                and np.isfinite(r[key]) and not (drop_beyond and r["beyond_canny_Rmax"])]
        if not rows:
            return None
        b = max(rows, key=lambda r: r[key])
        return {"best_LIFT_P": b[key], "at_f": b["f"], "P": b["P"], "R": b["R"],
                "canny_P_env_at_R": b["canny_P_env_at_R"],
                "beyond_canny_Rmax": b["beyond_canny_Rmax"],
                "matched_f_dP": b["matched_f_dP"], "matched_f_dR": b["matched_f_dR"],
                "n_above_frontier_in_band": sum(1 for r in rows if r["LIFT_P_lb"] > 0),
                "n_in_band": len(rows), "rows": rows}

    X = summarise(a.arm)
    T = summarise(a.teed_arm) if a.teed_arm in res else None
    X2 = summarise(a.arm, res2, "LIFT_P_lb", False)
    T2 = summarise(a.teed_arm, res2, "LIFT_P_lb", False) if a.teed_arm in res2 else None
    lift = X["best_LIFT_P"]
    frac = lift / TEED_LIFT_P_REF

    # gate-direction consistency with TEED at the matched f (recall up, precision drop modest,
    # frontier outward not inward)
    dirs = {"dRecall_up": bool(X["matched_f_dR"] > 0),
            "precision_drop_modest": bool(X["matched_f_dP"] > -0.10),
            "frontier_outward": bool(lift > 0)}
    dir_ok = all(dirs.values())
    ok, bad = manifest_ok()
    temporal_ok = bool(ok == 332 and bad == 0)

    if lift >= GO_ABS:
        call = "GO"
    elif lift < NOGO_ABS:
        call = "NO-GO"
    else:
        call = "PARTIAL"
    GO = bool(call == "GO" and temporal_ok and dir_ok)

    print("=" * 74)
    print("XMEP — FROZEN GO/NO-GO (thresholds committed before any lift was computed)")
    print("=" * 74)
    print(f"  prefix {a.prefix}   PRIMARY metric {KIND}/{STAGE} (spec)   "
          f"f-band [{FMIN}, {FMAX}]")
    print(f"  cross-model arm : {a.arm}")
    print(f"    best LIFT_P   = {lift:+.4f}  at f={X['at_f']:.2f}  "
          f"(P={X['P']:.4f} R={X['R']:.4f})")
    if T:
        print(f"  in-run TEED arm : {a.teed_arm}")
        print(f"    best LIFT_P   = {T['best_LIFT_P']:+.4f}  at f={T['at_f']:.2f}")
    print(f"  spec TEED reference LIFT_P = {TEED_LIFT_P_REF:+.4f}")
    if X2:
        print(f"  [secondary, MIS-SPECIFIED variant — not used for the call] "
              f"{a.arm} LIFT_P_lb = {X2['best_LIFT_P']:+.4f}"
              + (f", {a.teed_arm} = {T2['best_LIFT_P']:+.4f}" if T2 else ""))
    print(f"\n  FRACTION of TEED lift    = {frac:.3f}")
    print(f"    GO      >= {GO_FRAC:.2f} ({GO_ABS:+.5f})")
    print(f"    NO-GO   <  {NOGO_FRAC:.2f} ({NOGO_ABS:+.5f})")
    print(f"  gate directions {dirs}  -> {'OK' if dir_ok else 'INCONSISTENT'}")
    print(f"  temporal manifest {ok}/332 OK, {bad} failures -> "
          f"{'no regression' if temporal_ok else 'REGRESSION'}")
    print(f"\n  CALL: {call}    (overall GO={GO})")

    json.dump({"thresholds": {"TEED_LIFT_P_REF": TEED_LIFT_P_REF, "GO_frac": GO_FRAC,
                              "NOGO_frac": NOGO_FRAC, "GO_abs": GO_ABS,
                              "NOGO_abs": NOGO_ABS, "fband": [FMIN, FMAX],
                              "kind": KIND, "stage": STAGE},
               "prefix": a.prefix, "arm": a.arm, "teed_arm": a.teed_arm,
               "primary_metric": f"{KIND}/{STAGE}, interpolated canny P@R, beyond-reach "
                                 f"excluded, canny frontier f<={max(PUB_CANNY_F)}",
               "secondary_metric_mis_specified":
                   f"{KIND2}/{STAGE2}, Pareto-envelope LIFT_P_lb, full canny frontier",
               "cross_model": X, "teed_in_run": T,
               "cross_model_secondary": X2, "teed_in_run_secondary": T2,
               "best_LIFT_P": lift, "fraction_of_TEED": frac,
               "gate_directions": dirs, "gate_directions_ok": dir_ok,
               "manifest_ok_count": ok, "manifest_failures": bad,
               "temporal_no_regress": temporal_ok,
               "call": call, "GO": GO},
              open(a.out, "w"), indent=1, default=float)
    print(f"\nwrote {a.out}")
