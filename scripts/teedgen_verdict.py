"""TEED-generalisation verdict: the M1b f-frontier on a held-out TEST split, per edge source.

*** ANALYSIS ONLY — reads the jsons run_m1b.py already wrote.  No mesh, no GPU. ***

The bar (HYBRID_RESULTS.md, restated in RECALL_RESULTS.md) is NOT "does arm X beat canny at
one f".  Any seed change that trades precision for recall is dominated by simply lowering f.
So every arm is scored against the CANNY f-FRONTIER interpolated to the same recall (LIFT_P)
and to the same precision (LIFT_R).  Positive LIFT = information the f dial cannot buy.

The verdict rule is the one frozen in tier1/teed_gen_spec.md before any lego number existed:
  GO        LIFT_P > 0 at some f in [0.22, 0.50]
            OR R_max >= canny R_max + 0.12 at P >= 0.75 without precision collapse
  MARGINAL  best LIFT_P in [-0.01, +0.02] but the arm reaches higher-recall points cleanly
  NO-GO     LIFT_P <= -0.04 for all f <= 0.30
"""
import os
import sys
import json
import glob
import argparse

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
OUT = os.path.join(TIER1, "out")
SEG = "AFTER   pull+prune[tuned+len]"      # segments headline stage
PTS = "AFTER   pull+prune[tuned]"          # the points stage carries a different label
SEG_SPEC = "AFTER   pull+prune[spec]"


def row(d, kind, stage):
    for r in d["rows"]:
        if r["kind"] == kind and r["stage"] == stage:
            return r
    return None


def interp_P_at_R(front, R):
    a = sorted(front)
    rs, ps = [x[0] for x in a], [x[1] for x in a]
    return float(np.interp(R, rs, ps)) if rs[0] < R < rs[-1] else float("nan")


def interp_R_at_P(front, P):
    a = sorted(front, key=lambda x: x[1])
    ps, rs = [x[1] for x in a], [x[0] for x in a]
    return float(np.interp(P, ps, rs)) if ps[0] < P < ps[-1] else float("nan")


def env_P_at_R(front, R):
    """Best precision the canny f-dial reaches while ALSO reaching at least recall R.

    np.interp over the raw (R,P) points assumes the frontier is a trade-off curve.  On chair
    it is; on lego it is NOT -- canny's P RISES with R, so the curve's own endpoint dominates
    it and 'the precision canny gets at recall R' is not well defined by interpolation.  The
    Pareto envelope is the question that is always well posed: can the dial buy this recall
    at this precision, at ANY f?  nan iff no swept f reaches recall R at all.
    """
    ps = [p for r, p in front if r >= R - 1e-12]
    return max(ps) if ps else float("nan")


def analyse(arms, kind, stage, fmin=0.22, fmax=0.50):
    """-> (frontier, {arm: {rows, summary}})"""
    front = []
    for f, d in sorted(arms["canny"].items()):
        r = row(d, kind, stage)
        front.append((r["R1.5"], r["P1.5"]))
    Rmax_c = max(x[0] for x in front)
    Pmax_c = max(x[1] for x in front)
    P_at_Rmax_c = max(p for r, p in front if r >= Rmax_c - 1e-12)
    res = {}
    for name in arms:
        if name == "canny":
            continue
        rows = []
        for f, d in sorted(arms[name].items(), reverse=True):
            r = row(d, kind, stage)
            pf = interp_P_at_R(front, r["R1.5"])          # chair-comparable interpolation
            pe = env_P_at_R(front, r["R1.5"])             # Pareto envelope (always posed)
            rf = interp_R_at_P(front, r["P1.5"])
            beyond = bool(r["R1.5"] > Rmax_c)
            # when canny cannot reach this recall at any swept f, the honest number is a
            # LOWER BOUND: canny's precision at its OWN maximum recall.
            lift_lb = r["P1.5"] - (P_at_Rmax_c if beyond else pe)
            cm = row(arms["canny"][f], kind, stage) if f in arms["canny"] else None
            rows.append({"f": f, "P": r["P1.5"], "R": r["R1.5"],
                         "P25": r["P2.5"], "R25": r["R2.5"], "n": r["n"],
                         "n_seeds": d["n_seeds"], "n_keep": d["n_keep_tuned"],
                         "canny_P_at_R": pf, "LIFT_P": r["P1.5"] - pf,
                         "canny_P_env_at_R": pe, "LIFT_P_env": r["P1.5"] - pe,
                         "LIFT_P_lb": lift_lb,
                         "canny_R_at_P": rf, "LIFT_R": r["R1.5"] - rf,
                         "beyond_canny_Rmax": beyond,
                         "dominates_whole_canny_frontier":
                             bool(r["R1.5"] > Rmax_c and r["P1.5"] >= Pmax_c),
                         "matched_f_canny_P": (cm["P1.5"] if cm else float("nan")),
                         "matched_f_canny_R": (cm["R1.5"] if cm else float("nan")),
                         "matched_f_dP": (r["P1.5"] - cm["P1.5"]) if cm else float("nan"),
                         "matched_f_dR": (r["R1.5"] - cm["R1.5"]) if cm else float("nan")})
        band = [r for r in rows if fmin - 1e-9 <= r["f"] <= fmax + 1e-9]
        # GO-a is read off LIFT_P_lb: it equals LIFT_P_env inside the frontier's range and
        # a conservative lower bound outside it, so an arm is never credited for a recall
        # the dial was merely never swept to.
        fin = [r for r in band if np.isfinite(r["LIFT_P_lb"])]
        best = max(fin, key=lambda r: r["LIFT_P_lb"]) if fin else None
        lo = [r for r in rows if r["f"] <= 0.30 and np.isfinite(r["LIFT_P_lb"])]
        Rmax_a = max(r["R"] for r in rows)
        hi_p = [r for r in rows if r["P"] >= 0.75]
        Rmax_a_p75 = max((r["R"] for r in hi_p), default=float("nan"))
        cq = [x for x in front if x[1] >= 0.75]
        Rmax_c_p75 = max((x[0] for x in cq), default=float("nan"))
        go_a = bool(best is not None and best["LIFT_P_lb"] > 0)
        go_b = bool(np.isfinite(Rmax_a_p75) and np.isfinite(Rmax_c_p75)
                    and Rmax_a_p75 >= Rmax_c_p75 + 0.12)
        nogo = bool(len(lo) > 0 and all(r["LIFT_P_lb"] <= -0.04 for r in lo))
        marg = bool(best is not None and -0.01 <= best["LIFT_P_lb"] <= 0.02
                    and Rmax_a > Rmax_c)
        res[name] = {
            "rows": rows,
            "best_LIFT_P_in_band": (best["LIFT_P_lb"] if best else float("nan")),
            "best_LIFT_P_f": (best["f"] if best else float("nan")),
            "n_above_frontier_in_band": sum(1 for r in band if r["LIFT_P_lb"] > 0),
            "n_in_band": len(band),
            "n_beyond_canny_Rmax": sum(1 for r in rows if r["beyond_canny_Rmax"]),
            "n_dominating_whole_frontier":
                sum(1 for r in rows if r["dominates_whole_canny_frontier"]),
            "R_max": Rmax_a, "R_max_canny": Rmax_c, "dR_max": Rmax_a - Rmax_c,
            "P_max_canny": Pmax_c, "canny_P_at_its_own_Rmax": P_at_Rmax_c,
            "R_max_at_P75": Rmax_a_p75, "R_max_canny_at_P75": Rmax_c_p75,
            "GO_liftP_positive_in_band": go_a,
            "GO_Rmax_plus_0.12_at_P75": go_b,
            "NOGO_liftP_le_-0.04_for_all_f_le_0.30": nogo,
            "MARGINAL": marg,
            "VERDICT": ("NO-GO" if nogo else
                        ("GO" if (go_a or go_b) else
                         ("MARGINAL" if marg else "BELOW-FRONTIER"))),
        }
    return front, res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="m1b_lego_tc_")
    ap.add_argument("--out", default=None)
    ap.add_argument("--fmin", type=float, default=0.22)
    ap.add_argument("--fmax", type=float, default=0.50)
    args = ap.parse_args()

    arms = {}
    for p in sorted(glob.glob(os.path.join(OUT, args.prefix + "*.json"))):
        tag = os.path.basename(p)[len(args.prefix):-len(".json")]
        name, f = tag.rsplit("_f", 1)
        arms.setdefault(name, {})[float(f)] = json.load(open(p))
    if "canny" not in arms:
        sys.exit(f"no canny frontier arm under prefix {args.prefix}")
    print(f"[verdict] {sum(len(v) for v in arms.values())} runs, arms: "
          f"{ {k: sorted(v) for k, v in arms.items()} }\n")

    allres = {}
    for kind, stage, label in (("segments", SEG, "SEGMENTS (headline stage)"),
                               ("points", PTS, "POINTS (same stage)"),
                               ("segments", SEG_SPEC, "SEGMENTS (spec prune rule)")):
        front, res = analyse(arms, kind, stage, args.fmin, args.fmax)
        key = f"{kind}|{stage}"
        allres[key] = {"frontier": front, "arms": res}
        print("=" * 122)
        print(f"M1b HELD-OUT TEST — {label}   |   canny frontier: "
              f"R [{min(x[0] for x in front):.4f}, {max(x[0] for x in front):.4f}]  "
              f"P [{min(x[1] for x in front):.4f}, {max(x[1] for x in front):.4f}]")
        print("=" * 122)
        print(f"{'arm':>18} {'f':>5} {'nseed':>7} {'nkeep':>7} {'P@1.5':>8} {'R@1.5':>8} "
              f"{'P@2.5':>8} {'R@2.5':>8} {'cannyP@R':>9} {'LIFT_P':>8} {'LIFT_R':>8}")
        for f, d in sorted(arms["canny"].items(), reverse=True):
            r = row(d, kind, stage)
            print(f"{'canny':>18} {f:5.2f} {d['n_seeds']:7d} {d['n_keep_tuned']:7d} "
                  f"{r['P1.5']:8.4f} {r['R1.5']:8.4f} {r['P2.5']:8.4f} {r['R2.5']:8.4f}")
        for name in sorted(res):
            print("")
            for r in res[name]["rows"]:
                lp = ("      —" if not np.isfinite(r["LIFT_P_lb"])
                      else f"{r['LIFT_P_lb']:+8.4f}")
                lr = ("      —" if not np.isfinite(r["LIFT_R"]) else f"{r['LIFT_R']:+8.4f}")
                cp = ("      —" if not np.isfinite(r["canny_P_env_at_R"])
                      else f"{r['canny_P_env_at_R']:9.4f}")
                mk = ("  DOM" if r["dominates_whole_canny_frontier"]
                      else ("  bey" if r["beyond_canny_Rmax"] else "     "))
                print(f"{name:>18} {r['f']:5.2f} {r['n_seeds']:7d} {r['n_keep']:7d} "
                      f"{r['P']:8.4f} {r['R']:8.4f} {r['P25']:8.4f} {r['R25']:8.4f} "
                      f"{cp:>9} {lp:>8} {lr:>8}{mk}")
            v = res[name]
            print(f"{'':>18} -> above frontier {v['n_above_frontier_in_band']}"
                  f"/{v['n_in_band']} in f[{args.fmin},{args.fmax}]  "
                  f"(+{v['n_beyond_canny_Rmax']} beyond canny Rmax)  "
                  f"best LIFT_P {v['best_LIFT_P_in_band']:+.4f} (f={v['best_LIFT_P_f']})  "
                  f"Rmax {v['R_max']:.4f} vs canny {v['R_max_canny']:.4f} "
                  f"({v['dR_max']:+.4f})   => {v['VERDICT']}")

    print("\n" + "=" * 122)
    print("MATCHED-f (identical seed count; no interpolation involved) — segments headline")
    print("=" * 122)
    _, resm = analyse(arms, "segments", SEG, args.fmin, args.fmax)
    print(f"{'arm':>18} {'f':>5} {'nseed':>7} {'arm P/R':>17} {'canny P/R':>17} "
          f"{'dP':>8} {'dR':>8}")
    for name in sorted(resm):
        for r in resm[name]["rows"]:
            if not np.isfinite(r["matched_f_dP"]):
                continue
            print(f"{name:>18} {r['f']:5.2f} {r['n_seeds']:7d} "
                  f"{r['P']:8.4f}/{r['R']:8.4f} "
                  f"{r['matched_f_canny_P']:8.4f}/{r['matched_f_canny_R']:8.4f} "
                  f"{r['matched_f_dP']:+8.4f} {r['matched_f_dR']:+8.4f}")

    print("\n" + "=" * 122)
    print("VERDICT (spec rule, frozen before any number was produced) — segments headline stage")
    print("=" * 122)
    _, res = analyse(arms, "segments", SEG, args.fmin, args.fmax)
    for name in sorted(res):
        v = res[name]
        print(f"  {name:>18}: {v['VERDICT']:<15} "
              f"GO-a LIFT_P>0 in f[{args.fmin},{args.fmax}]: "
              f"{'YES' if v['GO_liftP_positive_in_band'] else 'no '} "
              f"(best {v['best_LIFT_P_in_band']:+.4f} @f={v['best_LIFT_P_f']}"
              f", {v['n_dominating_whole_frontier']} pts dominate the WHOLE canny frontier)  | "
              f"GO-b Rmax@P>=.75 >= canny+0.12: "
              f"{'YES' if v['GO_Rmax_plus_0.12_at_P75'] else 'no '} "
              f"({v['R_max_at_P75']:.4f} vs {v['R_max_canny_at_P75']:.4f})  | "
              f"NO-GO all f<=0.30 LIFT_P<=-0.04: "
              f"{'TRIPPED' if v['NOGO_liftP_le_-0.04_for_all_f_le_0.30'] else 'no'}")

    jp = args.out or os.path.join(OUT, f"teedgen_verdict_{args.prefix.strip('_')}.json")
    json.dump({"prefix": args.prefix, "fband": [args.fmin, args.fmax],
               "results": {k: {"frontier": v["frontier"],
                               "arms": v["arms"]} for k, v in allres.items()}},
              open(jp, "w"), indent=2)
    print(f"\nwrote {jp}")


if __name__ == "__main__":
    main()
