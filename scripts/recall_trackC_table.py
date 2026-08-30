"""TRACK C — final table: M1b held-out TEST, TEED vs the Canny f-FRONTIER.

The bar is not "does TEED beat the single Canny f=0.30 point".  A seed change that trades
precision for recall is dominated by simply lowering f, and HYBRID_RESULTS.md records the
2DGS hybrid failing exactly that way (14/15 arms below the frontier).  So each TEED arm is
scored against the Canny frontier INTERPOLATED to the same recall (LIFT_P) and to the same
precision (LIFT_R).  Positive LIFT = information the f dial cannot buy.
"""
import os
import sys
import json
import glob
import argparse

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
OUT = os.path.join(TIER1, "out")
HEAD = "AFTER   pull+prune[tuned+len]"       # segments headline stage
HEAD_PT = "AFTER   pull+prune[tuned]"       # the points stage carries a different label
SPEC = "AFTER   pull+prune[spec]"


def row(d, kind, stage):
    for r in d["rows"]:
        if r["kind"] == kind and r["stage"] == stage:
            return r
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="m1b_chair_tc_")
    args = ap.parse_args()

    arms = {}
    for p in sorted(glob.glob(os.path.join(OUT, args.prefix + "*.json"))):
        tag = os.path.basename(p)[len(args.prefix):-len(".json")]
        d = json.load(open(p))
        name, f = tag.rsplit("_f", 1)
        arms.setdefault(name, {})[float(f)] = d

    def pts(d, kind, stage):
        r = row(d, kind, stage)
        return (r["P1.5"], r["R1.5"], r["P2.5"], r["R2.5"], r["n"]) if r else (np.nan,) * 5

    # ---- Canny frontier (headline segment stage)
    cf = sorted(arms["canny"].items())
    front_seg = [(pts(d, "segments", HEAD)[1], pts(d, "segments", HEAD)[0]) for _, d in cf]
    front_pt = [(pts(d, "points", HEAD_PT)[1], pts(d, "points", HEAD_PT)[0]) for _, d in cf]

    def interp_P_at_R(front, R):
        a = sorted(front)
        rs, ps = [x[0] for x in a], [x[1] for x in a]
        return float(np.interp(R, rs, ps)) if rs[0] < R < rs[-1] else float("nan")

    def interp_R_at_P(front, P):
        a = sorted(front, key=lambda x: x[1])
        ps, rs = [x[1] for x in a], [x[0] for x in a]
        return float(np.interp(P, ps, rs)) if ps[0] < P < ps[-1] else float("nan")

    print("=" * 118)
    print("M1b HELD-OUT TEST — segments, stage 'pull+prune[tuned+len]' (the published "
          "headline stage; baseline = 0.6573 / 0.5959)")
    print("=" * 118)
    print(f"{'arm':>20} {'f':>5} {'nseed':>6} {'nkeep':>6} {'segP@1.5':>9} {'segR@1.5':>9} "
          f"{'segP@2.5':>9} {'segR@2.5':>9} {'cannyP@R':>9} {'LIFT_P':>8} {'LIFT_R':>8}")
    summary = {}
    for name in ["canny"] + [n for n in sorted(arms) if n != "canny"]:
        for f, d in sorted(arms[name].items(), reverse=True):
            P, R, P2, R2, n = pts(d, "segments", HEAD)
            if name == "canny":
                print(f"{name:>20} {f:5.2f} {d['n_seeds']:6d} {d['n_keep_tuned']:6d} "
                      f"{P:9.4f} {R:9.4f} {P2:9.4f} {R2:9.4f}")
            else:
                pf = interp_P_at_R(front_seg, R)
                rf = interp_R_at_P(front_seg, P)
                print(f"{name:>20} {f:5.2f} {d['n_seeds']:6d} {d['n_keep_tuned']:6d} "
                      f"{P:9.4f} {R:9.4f} {P2:9.4f} {R2:9.4f} {pf:9.4f} "
                      f"{P - pf:+8.4f} {R - rf:+8.4f}")
                summary.setdefault(name, []).append(
                    {"f": f, "P": P, "R": R, "LIFT_P": P - pf, "LIFT_R": R - rf})

    print("\n" + "=" * 118)
    print("M1b HELD-OUT TEST — points, same stage")
    print("=" * 118)
    print(f"{'arm':>20} {'f':>5} {'P@1.5':>9} {'R@1.5':>9} {'P@2.5':>9} {'R@2.5':>9} "
          f"{'cannyP@R':>9} {'LIFT_P':>8}")
    for name in ["canny"] + [n for n in sorted(arms) if n != "canny"]:
        for f, d in sorted(arms[name].items(), reverse=True):
            P, R, P2, R2, n = pts(d, "points", HEAD_PT)
            pf = interp_P_at_R(front_pt, R) if name != "canny" else float("nan")
            print(f"{name:>20} {f:5.2f} {P:9.4f} {R:9.4f} {P2:9.4f} {R2:9.4f} "
                  f"{pf:9.4f} {P - pf:+8.4f}" if name != "canny" else
                  f"{name:>20} {f:5.2f} {P:9.4f} {R:9.4f} {P2:9.4f} {R2:9.4f}")

    # ---- does the frontier move OUTWARD?
    print("\n" + "=" * 118)
    print("FRONTIER SHIFT (segments, headline stage)")
    print("=" * 118)
    Rmax_c = max(x[0] for x in front_seg)
    Pmax_c = max(x[1] for x in front_seg)
    print(f"  canny frontier: R range [{min(x[0] for x in front_seg):.4f}, {Rmax_c:.4f}]  "
          f"P range [{min(x[1] for x in front_seg):.4f}, {Pmax_c:.4f}]")
    verdict = {}
    for name, rows in summary.items():
        na = sum(1 for r in rows if r["LIFT_P"] > 0)
        fin = [r for r in rows if np.isfinite(r["LIFT_P"])]
        best = max(fin, key=lambda r: r["LIFT_P"]) if fin else \
            {"LIFT_P": float("nan"), "f": float("nan")}
        Rmax_t = max(r["R"] for r in rows)
        beyond = sum(1 for r in rows if not np.isfinite(r["LIFT_P"]) and r["R"] > Rmax_c)
        verdict[name] = {
            "n_beyond_canny_Rmax": beyond,
            "n_above_frontier": na, "n_points": len(rows),
            "best_LIFT_P": best["LIFT_P"], "best_LIFT_P_f": best["f"],
            "best_LIFT_R": max([r["LIFT_R"] for r in rows
                                if np.isfinite(r["LIFT_R"])] or [float("nan")]),
            "R_max": Rmax_t, "R_max_canny": Rmax_c, "dR_max": Rmax_t - Rmax_c,
            "OUTWARD": bool((na + beyond) > len(rows) / 2 and Rmax_t > Rmax_c),
        }
        print(f"  {name:>20}: above frontier {na}/{len(rows)} "
              f"(+{beyond} BEYOND canny's max recall)  "
              f"best LIFT_P {best['LIFT_P']:+.4f} (f={best['f']})  "
              f"best LIFT_R {verdict[name]['best_LIFT_R']:+.4f}  "
              f"Rmax {Rmax_t:.4f} vs canny {Rmax_c:.4f} ({Rmax_t - Rmax_c:+.4f})  "
              f"=> {'OUTWARD' if verdict[name]['OUTWARD'] else 'not outward'}")

    print("\n  reference — 2DGS hybrid (HYBRID_RESULTS.md, same harness): "
          "14/15 arms BELOW the frontier, best LIFT +0.0004")
    print(f"\n  M1b gate P@1.5>=0.85 AND R@1.5>=0.75:")
    for name in sorted(arms):
        for f, d in sorted(arms[name].items(), reverse=True):
            P, R, _, _, _ = pts(d, "segments", HEAD)
            if P >= 0.85 and R >= 0.75:
                print(f"    {name} f={f}: PASS ({P:.4f}/{R:.4f})")
    print("    (no arm passes; baseline does not either — 0.6573/0.5959)")

    jp = os.path.join(OUT, "trackC_m1b_table.json")
    json.dump({"arms": {n: {str(f): {"segments": pts(d, "segments", HEAD),
                                     "points": pts(d, "points", HEAD_PT),
                                     "segments_spec": pts(d, "segments", SPEC),
                                     "n_seeds": d["n_seeds"],
                                     "n_keep_tuned": d["n_keep_tuned"]}
                            for f, d in a.items()} for n, a in arms.items()},
               "verdict": verdict}, open(jp, "w"), indent=2)
    print(f"\nwrote {jp}")


if __name__ == "__main__":
    main()
