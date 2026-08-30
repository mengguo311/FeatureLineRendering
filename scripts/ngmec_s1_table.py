"""NG-MEC Stage 1 — the gate table: (TEED + epipolar consensus) vs RAW TEED at matched f.

*** ANALYSIS ONLY — reads the jsons run_m1b.py already wrote. ***

Unlike TRACK L/M this is NOT a frontier question: the spec fixes the comparison as arm-vs-arm
at matched f against raw TEED, with a precision bar AND a recall-drop ceiling, because a
filter can only remove and would otherwise be rewarded for culling true creases.
"""
import os
import sys
import json
import glob
import argparse

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
OUT = os.path.join(TIER1, "out")
STAGES = [("segments", "AFTER   pull+prune[tuned+len]", "segments headline"),
          ("segments", "AFTER   pull+prune[spec]", "segments spec-prune"),
          ("points", "AFTER   pull+prune[tuned]", "points")]


def row(d, kind, stage):
    for r in d["rows"]:
        if r["kind"] == kind and r["stage"] == stage:
            return r
    return None


def load(prefix):
    arms = {}
    for p in sorted(glob.glob(os.path.join(OUT, prefix + "*.json"))):
        tag = os.path.basename(p)[len(prefix):-len(".json")]
        name, f = tag.rsplit("_f", 1)
        arms.setdefault(name, {})[float(f)] = json.load(open(p))
    return arms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", required=True)
    ap.add_argument("--base", default="teedbase")
    ap.add_argument("--fmin", type=float, default=0.22)
    ap.add_argument("--fmax", type=float, default=0.50)
    args = ap.parse_args()
    arms = load(f"m1b_{args.scene}_ng_")
    if args.base not in arms:
        sys.exit(f"missing baseline arm {args.base}; have {sorted(arms)}")

    res = {"scene": args.scene, "base": args.base, "stages": {}}
    for kind, stage, label in STAGES:
        base = {f: row(d, kind, stage) for f, d in arms[args.base].items()}
        print("=" * 108)
        print(f"{args.scene.upper()} — M1b held-out TEST, {label}: "
              f"(TEED + epipolar consensus) vs RAW TEED at MATCHED f")
        print("=" * 108)
        print(f"{'arm':>20} {'f':>5} {'P@1.5':>8} {'R@1.5':>8} {'dP@1.5':>9} {'dR@1.5':>9} "
              f"{'P@2.5':>8} {'R@2.5':>8} {'dP@2.5':>9} {'nkeep':>7}")
        for f in sorted(base, reverse=True):
            b = base[f]
            print(f"{args.base:>20} {f:5.2f} {b['P1.5']:8.4f} {b['R1.5']:8.4f} "
                  f"{'—':>9} {'—':>9} {b['P2.5']:8.4f} {b['R2.5']:8.4f} {'—':>9} "
                  f"{arms[args.base][f]['n_keep_tuned']:7d}")
        st = {}
        for name in sorted(a for a in arms if a not in (args.base, "canny")):
            print("")
            rows = []
            for f, d in sorted(arms[name].items(), reverse=True):
                r = row(d, kind, stage)
                b = base.get(f)
                if b is None:
                    continue
                dP, dR = r["P1.5"] - b["P1.5"], r["R1.5"] - b["R1.5"]
                rows.append({"f": f, "P": r["P1.5"], "R": r["R1.5"], "dP": dP, "dR": dR,
                             "P25": r["P2.5"], "R25": r["R2.5"],
                             "dP25": r["P2.5"] - b["P2.5"],
                             "n_keep": d["n_keep_tuned"], "n_seeds": d["n_seeds"]})
                print(f"{name:>20} {f:5.2f} {r['P1.5']:8.4f} {r['R1.5']:8.4f} "
                      f"{dP:+9.4f} {dR:+9.4f} {r['P2.5']:8.4f} {r['R2.5']:8.4f} "
                      f"{r['P2.5'] - b['P2.5']:+9.4f} {d['n_keep_tuned']:7d}")
            band = [r for r in rows if args.fmin - 1e-9 <= r["f"] <= args.fmax + 1e-9]
            if not band:
                continue
            best = max(band, key=lambda r: r["dP"])
            st[name] = {
                "rows": rows,
                "best_dP": best["dP"], "best_dP_f": best["f"],
                "dR_at_best_dP": best["dR"],
                "worst_dR": min(r["dR"] for r in band),
                "mean_dP": float(np.mean([r["dP"] for r in band])),
                "mean_dR": float(np.mean([r["dR"] for r in band])),
                "GO_dP_ge_0.05": bool(best["dP"] >= 0.05),
                "GO_recall_cost_ok": bool(best["dR"] >= -0.05),
                "NOGO_dP_lt_0.02": bool(best["dP"] < 0.02),
                "NOGO_recall_drop_gt_0.05": bool(min(r["dR"] for r in band) < -0.05),
            }
            print(f"{'':>20} -> best dP {best['dP']:+.4f} at f={best['f']} "
                  f"(dR {best['dR']:+.4f})   mean dP {st[name]['mean_dP']:+.4f}   "
                  f"worst dR {st[name]['worst_dR']:+.4f}")
        res["stages"][label] = st

    print("\n" + "=" * 108)
    print("FROZEN GO / NO-GO (Stage 1) — evaluated on the segments headline stage")
    print("  GO    : dP@1.5 >= +0.05 AND recall drop <= 0.05 AND flicker-win >= 12.0x @240f")
    print("  NO-GO : dP@1.5 < +0.02  OR  recall drop > 0.05  OR  flicker-win < 11.0x @240f")
    print("=" * 108)
    st = res["stages"]["segments headline"]
    for name, v in sorted(st.items()):
        verdict = ("NO-GO" if (v["NOGO_dP_lt_0.02"] or v["NOGO_recall_drop_gt_0.05"])
                   else ("GO(pending temporal)" if (v["GO_dP_ge_0.05"]
                                                    and v["GO_recall_cost_ok"])
                         else "INCONCLUSIVE"))
        print(f"  {name:>20}: best dP {v['best_dP']:+.4f} (bar +0.05, no-go < +0.02)   "
              f"dR at that f {v['dR_at_best_dP']:+.4f}   worst dR {v['worst_dR']:+.4f} "
              f"(ceiling -0.05)   => {verdict}")
    jp = os.path.join(OUT, f"ngmec_s1_table_{args.scene}.json")
    json.dump(res, open(jp, "w"), indent=2)
    print(f"\nwrote {jp}")


if __name__ == "__main__":
    main()
