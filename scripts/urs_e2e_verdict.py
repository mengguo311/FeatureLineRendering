#!/usr/bin/env python
"""URS-E2E — FROZEN scorer + thresholds. Committed BEFORE any densified number is read.

QUESTION. URS showed post-hoc TEED-ridge densification lifts lego carrier COVERAGE
0.4338 -> 0.7617 within a 3x budget, but only as an UPPER BOUND: it was never run through
pull+prune to held-out P/R, and the temporal coherence of the new carriers was never measured.
The lego ceiling autopsy attributes 31.5% of the recall gap to "covered-but-culled". Does
spending that coverage end-to-end move the held-out frontier, and does it cost the temporal
win, which is the paper's CORE and is SACRED?

PRIMARY GATE = TEMPORAL, FAIL-FAST. Measured FIRST, before any P/R is scored.
    ratio_f = P_pop(B, per-frame Canny) / P_pop(A, ours) at each frame count.
    The gate reads the MINIMUM ratio over frames — the conservative choice, so a regression
    at any frame count trips it rather than being averaged away by a good one.
    ABORT-NO-GO if min ratio < TEMPORAL_MIN = 6.0x. Do NOT proceed to P/R.
    Frechet ratios are reported alongside but the gate is on P_pop, matching the published
    8.5-13.1x headline.

SECONDARY GATE = HELD-OUT DOWNSTREAM LIFT (only if temporal passes).
    Matched-recall LIFT_P of densified+TEED against the FROZEN-CARRIER+TEED arm — NOT against
    Canny. The point is the MARGINAL value of densification over the existing best pipeline,
    so the frozen-carrier TEED f-frontier is the reference and is passed to
    teedgen_verdict.analyse() in the "canny" slot. The segment metric itself is the frozen
    XMEP/LEGO-GEN one, unchanged: segments / pull+prune[tuned+len], interpolated reference P
    at the same recall, beyond-reach rows excluded.
    GO      mean LIFT_P >= +0.02 across the reachable band AND dP > 0 on >= 70% of TEST views
    NO-GO   LIFT_P <= 0  (or temporal < 6x, which already aborted)
    PARTIAL otherwise, reported straight

BUDGET. densified carrier count must be <= 3x the baseline linelet count (89748), the same
cap URS respected.

Mesh is EVAL-ONLY (tune_lib.Harness -> mesh_oracle). Densification/seeding/pull/prune touch
only TEED ridges and the frozen-3DGS carrier. Held-out TEST views {5,15,...,95} throughout;
nothing is tuned on TEST.
"""
import argparse, glob, json, os, subprocess, sys

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
OUT = os.path.join(TIER1, "out")
sys.path.insert(0, os.path.join(TIER1, "scripts"))
import teedgen_verdict as TV
from xmep_verdict import load_arms

TEMPORAL_MIN = 6.0
LIFT_P_MIN = 0.02
VIEW_CONSISTENCY = 0.70
BUDGET_CAP = 89748
FMIN, FMAX = 0.22, 0.50
KIND, STAGE = "segments", TV.SEG
REF_ARM = "teed_native_0.5"          # frozen-carrier TEED = the reference frontier
FROZEN_TEED_RMAX = 0.48              # current frozen-carrier TEED reachable segR (URS-E2E q4)


def temporal_ratios(table_path):
    d = json.load(open(table_path))
    bf = d["scenes"]["lego"]["by_frames"]
    pop, fre = {}, {}
    for k in sorted(bf, key=int):
        A, B = bf[k]["A"], bf[k]["B"]
        pop[k] = B["P_pop"] / A["P_pop"]
        fre[k] = B["frechet_median"] / A["frechet_median"]
    return {"P_pop_ratio": pop, "frechet_ratio": fre,
            "min_P_pop_ratio": float(min(pop.values())),
            "max_P_pop_ratio": float(max(pop.values())),
            "min_frechet_ratio": float(min(fre.values())),
            "source": table_path}


def manifest_ok():
    r = subprocess.run(["sha256sum", "-c", "out/CMEPI_protected_manifest.sha256"],
                       cwd=TIER1, capture_output=True, text=True)
    ok = sum(1 for l in r.stdout.splitlines() if l.endswith(": OK"))
    bad = [l for l in r.stdout.splitlines() if l.strip() and not l.endswith(": OK")]
    return ok, len(bad)


def lift_vs_frozen_teed(dens_prefix, dens_arm):
    """LIFT_P of the densified arm against the FROZEN-CARRIER TEED f-frontier."""
    base = load_arms("m1b_lego_tc_")
    dens = load_arms(dens_prefix)
    if REF_ARM not in base:
        sys.exit(f"reference arm {REF_ARM} missing")
    if dens_arm not in dens:
        sys.exit(f"densified arm {dens_arm} missing; have {sorted(dens)}")
    arms = {"canny": base[REF_ARM], dens_arm: dens[dens_arm]}    # ref goes in the "canny" slot
    _, res = TV.analyse(arms, KIND, STAGE, FMIN, FMAX)
    rows = [r for r in res[dens_arm]["rows"]
            if FMIN - 1e-9 <= r["f"] <= FMAX + 1e-9
            and np.isfinite(r["LIFT_P"]) and not r["beyond_canny_Rmax"]]
    allrows = [r for r in res[dens_arm]["rows"] if FMIN - 1e-9 <= r["f"] <= FMAX + 1e-9]
    return rows, allrows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--temporal_table", required=True)
    ap.add_argument("--baseline_temporal",
                    default="out/m1b_stroke_temporal_table_tcL_tcteed040.json")
    ap.add_argument("--dens_prefix", default="m1b_lego_urse2e_")
    ap.add_argument("--dens_arm", default="urs")
    ap.add_argument("--per_view", default="out/urs_e2e_per_view.json")
    ap.add_argument("--n_carrier", type=int, default=None)
    ap.add_argument("--out", default="out/urs_e2e_verdict.json")
    a = ap.parse_args()

    # ---------------- PRIMARY GATE: TEMPORAL, FAIL-FAST -----------------------------
    T = temporal_ratios(a.temporal_table)
    B = temporal_ratios(a.baseline_temporal) if os.path.exists(a.baseline_temporal) else None
    ok, bad = manifest_ok()
    temporal_pass = bool(T["min_P_pop_ratio"] >= TEMPORAL_MIN)

    print("=" * 76)
    print("URS-E2E — PRIMARY GATE (TEMPORAL, FAIL-FAST). Reported FIRST.")
    print("=" * 76)
    print(f"  densified P_pop ratios by frames: "
          + "  ".join(f"{k}:{v:.2f}x" for k, v in T["P_pop_ratio"].items()))
    print(f"  densified Frechet ratios        : "
          + "  ".join(f"{k}:{v:.2f}x" for k, v in T["frechet_ratio"].items()))
    if B:
        print(f"  BASELINE (frozen carrier + TEED): "
              + "  ".join(f"{k}:{v:.2f}x" for k, v in B["P_pop_ratio"].items()))
    print(f"\n  MIN P_pop ratio = {T['min_P_pop_ratio']:.3f}x   "
          f"(gate: >= {TEMPORAL_MIN}x)  -> {'PASS' if temporal_pass else 'ABORT-NO-GO'}")
    print(f"  protected manifest {ok}/332 OK, {bad} failures")

    out = {"thresholds": {"TEMPORAL_MIN": TEMPORAL_MIN, "LIFT_P_MIN": LIFT_P_MIN,
                          "VIEW_CONSISTENCY": VIEW_CONSISTENCY, "BUDGET_CAP": BUDGET_CAP,
                          "fband": [FMIN, FMAX], "kind": KIND, "stage": STAGE,
                          "reference_arm": REF_ARM},
           "temporal": T, "temporal_baseline": B,
           "temporal_pass": temporal_pass,
           "manifest_ok_count": ok, "manifest_failures": bad,
           "n_carrier": a.n_carrier,
           "within_budget": (None if a.n_carrier is None
                             else bool(a.n_carrier <= BUDGET_CAP))}

    if not temporal_pass:
        out["call"] = "ABORT-NO-GO (temporal)"
        out["GO"] = False
        print(f"\n  CALL: {out['call']} — P/R deliberately NOT scored.")
        json.dump(out, open(a.out, "w"), indent=1, default=float)
        print(f"\nwrote {a.out}")
        sys.exit(0)

    # ---------------- SECONDARY GATE: HELD-OUT DOWNSTREAM LIFT ----------------------
    rows, allrows = lift_vs_frozen_teed(a.dens_prefix, a.dens_arm)
    mean_lift = float(np.mean([r["LIFT_P"] for r in rows])) if rows else float("nan")
    best = max(rows, key=lambda r: r["LIFT_P"]) if rows else None
    Rmax_dens = max((r["R"] for r in allrows), default=float("nan"))

    pv = json.load(open(a.per_view)) if os.path.exists(a.per_view) else None
    cons = pv["frac_dP_positive"] if pv else float("nan")

    go = bool(mean_lift >= LIFT_P_MIN and pv is not None and cons >= VIEW_CONSISTENCY)
    nogo = bool((not np.isfinite(mean_lift)) or mean_lift <= 0)
    call = "GO" if go else ("NO-GO" if nogo else "PARTIAL")

    print("\n" + "=" * 76)
    print("URS-E2E — SECONDARY GATE (held-out lift vs FROZEN-CARRIER+TEED)")
    print("=" * 76)
    print(f"  in-reach rows: " + (", ".join(f"f{r['f']:.2f}:{r['LIFT_P']:+.4f}" for r in rows)
                                  or "NONE"))
    print(f"  mean LIFT_P = {mean_lift:+.4f}  (GO >= {LIFT_P_MIN:+.3f})")
    if best:
        print(f"  best        = {best['LIFT_P']:+.4f} at f={best['f']:.2f} "
              f"(segP {best['P']:.4f}, segR {best['R']:.4f})")
    print(f"  densified reachable segR max = {Rmax_dens:.4f}  "
          f"(frozen-carrier TEED R_max ~ {FROZEN_TEED_RMAX})  "
          f"-> extends by {Rmax_dens - FROZEN_TEED_RMAX:+.4f}")
    if pv:
        print(f"  per-view dP>0 = {cons:.3f} (need >= {VIEW_CONSISTENCY})  "
              f"median dP {pv['dP_median']:+.4f}")
    print(f"\n  CALL: {call}")

    out.update({"rows": rows, "all_band_rows": allrows, "mean_LIFT_P": mean_lift,
                "best": best, "R_max_densified": Rmax_dens,
                "frozen_teed_Rmax": FROZEN_TEED_RMAX,
                "R_extension": Rmax_dens - FROZEN_TEED_RMAX,
                "per_view": pv, "view_consistency": cons,
                "call": call, "GO": go})
    json.dump(out, open(a.out, "w"), indent=1, default=float)
    print(f"\nwrote {a.out}")
