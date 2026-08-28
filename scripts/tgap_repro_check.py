"""tier1/scripts/tgap_repro_check.py — TGAP reproduction control.

*** ANALYSIS ONLY. ***  Arm A of TGAP must BE the committed lego headline, or every LIFT_P
below it is measured against something else.  This compares arm A, recomputed from the TGAP
pull dumps by src/tgap_gate.arm_masks, against the committed
out/m1b_lego_tc_canny_f*.json rows (stage `AFTER pull+prune[tuned+len]`, segments, TEST).
"""
import glob
import json
import os
import sys

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
OUT = os.path.join(TIER1, "out")
SEG = "AFTER   pull+prune[tuned+len]"


def main():
    T = json.load(open(os.path.join(OUT, "tgap_arms_lego_test.json")))
    mine = {round(r["f"], 4): r for r in T["rows"] if r["arm"] == "A"}
    rows, worst = [], 0.0
    for p in sorted(glob.glob(os.path.join(OUT, "m1b_lego_tc_canny_f*.json"))):
        d = json.load(open(p))
        f = round(float(d["args"]["f"]), 4)
        pub = next(r for r in d["rows"] if r["kind"] == "segments" and r["stage"] == SEG)
        if f not in mine:
            rows.append({"f": f, "status": "not swept by TGAP"})
            continue
        m = mine[f]
        dP, dR = m["P1.5"] - pub["P1.5"], m["R1.5"] - pub["R1.5"]
        dn = m["n_keep"] - d["n_keep_tuned"]
        worst = max(worst, abs(dP), abs(dR))
        rows.append({"f": f, "pub_P": pub["P1.5"], "tgap_P": m["P1.5"], "dP": dP,
                     "pub_R": pub["R1.5"], "tgap_R": m["R1.5"], "dR": dR,
                     "pub_n_keep": d["n_keep_tuned"], "tgap_n_keep": m["n_keep"],
                     "dn": dn, "exact": bool(dP == 0.0 and dR == 0.0 and dn == 0)})
    n_ex = sum(1 for r in rows if r.get("exact"))
    n_cmp = sum(1 for r in rows if "exact" in r)
    print(f"{'f':>6s} {'pub P':>8s} {'tgap P':>8s} {'dP':>10s} {'pub R':>8s} "
          f"{'tgap R':>8s} {'dR':>10s} {'d n_keep':>9s}")
    for r in rows:
        if "exact" not in r:
            print(f"{r['f']:6.2f}  {r['status']}")
            continue
        print(f"{r['f']:6.2f} {r['pub_P']:8.4f} {r['tgap_P']:8.4f} {r['dP']:+10.2e} "
              f"{r['pub_R']:8.4f} {r['tgap_R']:8.4f} {r['dR']:+10.2e} {r['dn']:9d}")
    print(f"\nEXACT on {n_ex}/{n_cmp} compared f values; worst |delta| = {worst:.3e}")
    json.dump({"rows": rows, "n_exact": n_ex, "n_compared": n_cmp,
               "worst_abs_delta": worst},
              open(os.path.join(OUT, "tgap_repro_check.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
