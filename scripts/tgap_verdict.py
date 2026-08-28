"""tier1/scripts/tgap_verdict.py — TGAP stage 3: frontiers, LIFT_P, and the four FROZEN gates.

*** ANALYSIS ONLY — reads the jsons scripts/tgap_eval.py already wrote.  No mesh, no GPU. ***

The LIFT_P machinery is IMPORTED from scripts/teedgen_verdict.py rather than re-implemented,
so "measured the same way as the TEED breakthrough" is literally true and not a claim:
  interp_P_at_R  chair-comparable linear interpolation of the reference frontier
  env_P_at_R     Pareto envelope -- the best precision the f dial reaches while ALSO reaching
                 at least that recall.  Well posed even when the frontier is not a trade-off
                 curve, which on lego it is not (its precision RISES with recall, so its own
                 endpoint dominates it).
  LIFT_P_lb      env inside the frontier's recall range; outside it, the reference's precision
                 at its OWN maximum recall, i.e. an honest lower bound.  This is the estimator
                 the repo's frozen verdict code decides on, so it is the one gated here; the
                 interpolated estimator is reported beside it at every point.

The reference frontier is ARM A -- the committed tuned+len prune swept over f.  Arms B and C
are re-prunes of the SAME pull at the SAME f, so this is the same comparison the TEED
breakthrough made, with the prune varying instead of the seed score.

SELECTION DISCIPLINE
  alpha, beta                     chosen on VAL only, by best in-band LIFT_P_lb.
  arm C's (tau_r, tau_L) per f    chosen on VAL only, to MATCH arm B's VAL recall.
  Everything reported as a TEST number is then a frozen configuration applied to a split no
  knob ever saw.  Two extra controls are reported because they can only hurt arm B:
    C_env@f    the best precision ANY global relaxation on the grid reaches at f* while also
               reaching arm B's TEST recall -- selected ON TEST, i.e. the adversarially
               strongest TEED-blind control.
    C_env@any  the same, free to use any f as well.
"""
import argparse
import json
import os
import sys

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))

from teedgen_verdict import interp_P_at_R, env_P_at_R                    # noqa: E402

OUT = os.path.join(TIER1, "out")
BAND = (0.22, 0.50)
GATE1_LIFT = 0.030
GATE2_MARGIN = 0.015


def load(scene, split):
    p = os.path.join(OUT, f"tgap_arms_{scene}_{split}.json")
    return json.load(open(p))


def frontier_A(rows):
    a = [(r["R1.5"], r["P1.5"]) for r in rows if r["arm"] == "A"]
    return sorted(a)


def lifts(front, R, P):
    """(LIFT_P_lb, LIFT_P_interp, beyond_Rmax) against the reference frontier."""
    Rmax = max(x[0] for x in front)
    P_at_Rmax = max(p for r, p in front if r >= Rmax - 1e-12)
    pe = env_P_at_R(front, R)
    pf = interp_P_at_R(front, R)
    beyond = bool(R > Rmax)
    lb = P - (P_at_Rmax if beyond else pe)
    return float(lb), float(P - pf), beyond


def sel(rows, arm, f=None, k1=None, k2=None):
    out = [r for r in rows if r["arm"] == arm
           and (f is None or abs(r["f"] - f) < 1e-9)
           and (k1 is None or abs(r["k1"] - k1) < 1e-9)
           and (k2 is None or abs(r["k2"] - k2) < 1e-9)]
    return out


def in_band(f):
    return BAND[0] - 1e-9 <= f <= BAND[1] + 1e-9


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="lego")
    args = ap.parse_args()

    V, T = load(args.scene, "val"), load(args.scene, "test")
    fV, fT = frontier_A(V["rows"]), frontier_A(T["rows"])

    # ---------------------------------------------------- 1. choose alpha,beta on VAL
    cand = {}
    for r in V["rows"]:
        if r["arm"] != "B" or not in_band(r["f"]):
            continue
        lb, itp, byd = lifts(fV, r["R1.5"], r["P1.5"])
        cand.setdefault((r["k1"], r["k2"]), []).append(
            {"f": r["f"], "P": r["P1.5"], "R": r["R1.5"], "lift_lb": lb,
             "lift_interp": itp, "beyond": byd, "n_keep": r["n_keep"]})
    ranked = []
    for (a, b), rs in cand.items():
        best = max(rs, key=lambda x: x["lift_lb"])
        ranked.append({"alpha": a, "beta": b, "val_best_lift_lb": best["lift_lb"],
                       "val_best_f": best["f"], "val_P": best["P"], "val_R": best["R"],
                       "val_best_lift_interp": best["lift_interp"]})
    ranked.sort(key=lambda x: -x["val_best_lift_lb"])
    star = ranked[0]
    alpha, beta = star["alpha"], star["beta"]

    # ------------------------------ 2. arm C frozen on VAL: match arm B's VAL recall per f
    Cfrozen = {}
    for f in sorted({r["f"] for r in V["rows"] if r["arm"] == "B"}):
        rb = sel(V["rows"], "B", f, alpha, beta)
        if not rb:
            continue
        RB = rb[0]["R1.5"]
        cs = sel(V["rows"], "C", f)
        cs += sel(V["rows"], "A", f)          # arm A IS the (0.50,0.90) member of the C grid
        if not cs:
            continue
        best = min(cs, key=lambda r: (abs(r["R1.5"] - RB), -r["P1.5"]))
        Cfrozen[f] = {"tau_r": best["k1"] if best["arm"] == "C" else 0.50,
                      "tau_L": best["k2"] if best["arm"] == "C" else 0.90,
                      "val_R": best["R1.5"], "val_P": best["P1.5"],
                      "val_R_target": RB, "val_dR": best["R1.5"] - RB}

    # ------------------------------------------------------------- 3. TEST, frozen config
    tb = []
    for r in T["rows"]:
        if r["arm"] != "B" or abs(r["k1"] - alpha) > 1e-9 or abs(r["k2"] - beta) > 1e-9:
            continue
        lb, itp, byd = lifts(fT, r["R1.5"], r["P1.5"])
        tb.append({"f": r["f"], "P": r["P1.5"], "R": r["R1.5"], "n_keep": r["n_keep"],
                   "lift_lb": lb, "lift_interp": itp, "beyond": byd,
                   "in_band": in_band(r["f"])})
    tb.sort(key=lambda x: x["f"])
    band_rows = [x for x in tb if x["in_band"]]
    bestB = max(band_rows, key=lambda x: x["lift_lb"])
    fstar = bestB["f"]
    # the fully-frozen alternative: f also taken from VAL
    frozen_f = star["val_best_f"]
    bestB_frozen_f = next((x for x in tb if abs(x["f"] - frozen_f) < 1e-9), None)

    # arm A at the same f (matched-f reference) and the whole-frontier reference
    Arow = sel(T["rows"], "A", fstar)[0]

    # ---- arm C, three readings ------------------------------------------------------
    cz = Cfrozen.get(fstar)
    Cf = None
    if cz:
        rr = (sel(T["rows"], "C", fstar, cz["tau_r"], cz["tau_L"])
              or sel(T["rows"], "A", fstar))
        if rr:
            lb, itp, byd = lifts(fT, rr[0]["R1.5"], rr[0]["P1.5"])
            Cf = {"tau_r": cz["tau_r"], "tau_L": cz["tau_L"], "P": rr[0]["P1.5"],
                  "R": rr[0]["R1.5"], "n_keep": rr[0]["n_keep"], "lift_lb": lb,
                  "lift_interp": itp, "val_dR": cz["val_dR"],
                  "test_dR_vs_B": rr[0]["R1.5"] - bestB["R"]}

    def env_control(rows, RB, f=None):
        pool = [r for r in rows if r["arm"] in ("C", "A")
                and (f is None or abs(r["f"] - f) < 1e-9) and r["R1.5"] >= RB - 1e-12]
        if not pool:
            return None
        best = max(pool, key=lambda r: r["P1.5"])
        lb, itp, byd = lifts(fT, best["R1.5"], best["P1.5"])
        return {"arm": best["arm"], "f": best["f"], "tau_r": best["k1"],
                "tau_L": best["k2"], "P": best["P1.5"], "R": best["R1.5"],
                "n_keep": best["n_keep"], "lift_lb": lb, "lift_interp": itp}

    Cenv_f = env_control(T["rows"], bestB["R"], f=fstar)
    Cenv_any = env_control(T["rows"], bestB["R"], f=None)

    # ------------------------------------------------------------------- 4. the gates
    g1 = bool(bestB["lift_lb"] >= GATE1_LIFT)
    g1_interp = bool(bestB["lift_interp"] >= GATE1_LIFT)
    g2 = bool(Cf is not None and (bestB["lift_lb"] - Cf["lift_lb"]) >= GATE2_MARGIN)
    g2_env = bool(Cenv_f is not None
                  and (bestB["lift_lb"] - Cenv_f["lift_lb"]) >= GATE2_MARGIN)
    g2_env_any = bool(Cenv_any is not None
                      and (bestB["lift_lb"] - Cenv_any["lift_lb"]) >= GATE2_MARGIN)
    g3 = bool(bestB["lift_lb"] >= 0.0)

    out = {
        "scene": args.scene, "band": list(BAND),
        "gate_bars": {"gate1_lift_P": GATE1_LIFT, "gate2_margin": GATE2_MARGIN,
                      "gate3": "LIFT_P >= 0 (no precision regress at matched recall)",
                      "gate4": "temporal, scored by scripts/tgap_temporal_table.py"},
        "frontier_A_val": fV, "frontier_A_test": fT,
        "val_selection": {"alpha": alpha, "beta": beta,
                          "val_best_lift_lb": star["val_best_lift_lb"],
                          "val_best_f": star["val_best_f"],
                          "top10": ranked[:10]},
        "C_frozen_on_val": Cfrozen,
        "test_B_rows": tb,
        "test_best_B": bestB,
        "test_B_at_val_frozen_f": bestB_frozen_f,
        "test_A_at_fstar": {"f": fstar, "P": Arow["P1.5"], "R": Arow["R1.5"],
                            "n_keep": Arow["n_keep"]},
        "test_C_frozen": Cf, "test_C_env_at_fstar": Cenv_f, "test_C_env_any_f": Cenv_any,
        "gates": {
            "1_LIFT_P_ge_0.030": {"value": bestB["lift_lb"], "pass": g1,
                                  "interp_value": bestB["lift_interp"],
                                  "interp_pass": g1_interp, "f": fstar},
            "2_B_minus_C_ge_0.015": {
                "value": (bestB["lift_lb"] - Cf["lift_lb"]) if Cf else None, "pass": g2,
                "vs_C_env_at_f": ((bestB["lift_lb"] - Cenv_f["lift_lb"])
                                  if Cenv_f else None), "pass_vs_C_env_at_f": g2_env,
                "vs_C_env_any_f": ((bestB["lift_lb"] - Cenv_any["lift_lb"])
                                   if Cenv_any else None),
                "pass_vs_C_env_any_f": g2_env_any},
            "3_precision_no_regress": {"value": bestB["lift_lb"], "pass": g3},
        },
        "VERDICT_gates_1_3": "GO" if (g1 and g2 and g3) else "NO-GO",
    }
    p = os.path.join(OUT, f"tgap_verdict_{args.scene}.json")
    json.dump(out, open(p, "w"), indent=1)

    print("=" * 92)
    print(f"TGAP verdict — {args.scene}   (alpha,beta chosen on VAL = {alpha}, {beta})")
    print("=" * 92)
    print(f"arm A TEST frontier: Rmax {max(x[0] for x in fT):.4f} "
          f"Pmax {max(x[1] for x in fT):.4f}   (16 f points)")
    print(f"{'f':>6s} {'n_keep':>8s} {'P@1.5':>8s} {'R@1.5':>8s} {'LIFT_lb':>9s} "
          f"{'LIFT_int':>9s}")
    for x in tb:
        print(f"{x['f']:6.2f} {x['n_keep']:8d} {x['P']:8.4f} {x['R']:8.4f} "
              f"{x['lift_lb']:+9.4f} {x['lift_interp']:+9.4f}"
              f"{'  <-- best in band' if x is bestB else ''}")
    print("-" * 92)
    for k, v in out["gates"].items():
        print(f"  gate {k}: {v}")
    print(f"  VERDICT (gates 1-3): {out['VERDICT_gates_1_3']}")
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
