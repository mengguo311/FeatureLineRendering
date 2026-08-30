"""STEP 2 summary — every arm's TEST numbers in one table, plus the matched-count control.

EVAL-ONLY reporting: reads the jsons written by run_hybrid.py / run_m1b.py. No new compute.

THE COLUMN THAT DECIDES IT: `LIFT vs f-ctl`. A gate that removes seeds always trades
recall for precision, and the M1a score already offers that trade for free by lowering f.
So every gated arm is compared against the ungated f-control arm interpolated to the SAME
segment recall. Positive lift = the 2DGS gate bought precision the M1a score could not.
"""
import glob
import json
import os
import sys

import numpy as np

OUT = os.path.expanduser("~/3dgs_line/tier1/out")


def seg_tuned(j):
    for r in j["rows"]:
        if r["kind"] == "segments" and "tuned" in r["stage"]:
            return r
    return None


def seg_spec(j):
    for r in j["rows"]:
        if r["kind"] == "segments" and "spec" in r["stage"]:
            return r
    return None


def load(pat):
    out = []
    for p in sorted(glob.glob(os.path.join(OUT, pat))):
        j = json.load(open(p))
        st, sp = seg_tuned(j), seg_spec(j)
        if st is None:
            continue
        out.append({"file": os.path.basename(p), "tag": j["args"].get("tag", ""),
                    "j": j, "tuned": st, "spec": sp,
                    "n_seeds": j["n_seeds"],
                    "gate": j.get("seed_gate")})
    return out


def main():
    ctl = load("hybrid_chair_ctl_f*.json")
    arms = [x for x in load("hybrid_chair_*.json") if not x["tag"].startswith("_ctl_")]
    base = json.load(open(os.path.join(OUT, "m1b_chair_base_test.json")))
    bt, bs = seg_tuned(base), seg_spec(base)

    ctl = sorted(ctl, key=lambda x: x["tuned"]["R1.5"])
    cR = [x["tuned"]["R1.5"] for x in ctl]
    cP = [x["tuned"]["P1.5"] for x in ctl]
    cRs = [x["spec"]["R1.5"] for x in ctl]
    cPs = [x["spec"]["P1.5"] for x in ctl]

    def lift(P, R, xs, ys):
        if R <= xs[0] or R >= xs[-1]:
            return float("nan")
        return P - float(np.interp(R, xs, ys))

    print("=" * 122)
    print("STEP 2 — chair, held-out TEST views [5,15,...,95].  segments, prune[tuned+len] "
          "(the reported M1b protocol)")
    print("  BASELINE (vanilla M1b, gated DT, f=0.30): seg P@1.5 = "
          f"{bt['P1.5']:.4f}  R@1.5 = {bt['R1.5']:.4f}  n = {bt['n']}")
    print("  LIFT vs f-ctl = arm precision MINUS the ungated f-control's precision at the "
          "SAME recall.  <=0 means the gate bought nothing.")
    print("=" * 122)
    print(f"{'arm':42s} {'n_seed':>7} {'n_kept':>7} {'segP@1.5':>9} {'segR@1.5':>9} "
          f"{'segP@2.5':>9} {'segR@2.5':>9} {'LIFT':>8}")
    print("-" * 122)
    print(f"{'BASELINE vanilla M1b f=0.30 (gated DT)':42s} {base['n_seeds']:>7} "
          f"{bt['n']:>7} {bt['P1.5']:>9.4f} {bt['R1.5']:>9.4f} {bt['P2.5']:>9.4f} "
          f"{bt['R2.5']:>9.4f} {'--':>8}")
    for x in ctl:
        t = x["tuned"]
        print(f"{'f-CONTROL ' + x['tag'].replace('_ctl_', ''):42s} {x['n_seeds']:>7} "
              f"{t['n']:>7} {t['P1.5']:>9.4f} {t['R1.5']:>9.4f} {t['P2.5']:>9.4f} "
              f"{t['R2.5']:>9.4f} {'--':>8}")
    print("-" * 122)
    rows = []
    for x in sorted(arms, key=lambda z: z["tag"]):
        t = x["tuned"]
        lf = lift(t["P1.5"], t["R1.5"], cR, cP)
        rows.append((x, lf))
        print(f"{'HYBRID ' + x['tag'].lstrip('_'):42s} {x['n_seeds']:>7} {t['n']:>7} "
              f"{t['P1.5']:>9.4f} {t['R1.5']:>9.4f} {t['P2.5']:>9.4f} {t['R2.5']:>9.4f} "
              f"{lf:>+8.4f}")
    print("-" * 122)
    good = [(x, l) for x, l in rows if np.isfinite(l) and l > 0]
    print(f"  arms strictly above the ungated f-control frontier: {len(good)}/{len(rows)}")
    if good:
        b = max(good, key=lambda z: z[1])
        print(f"  best: {b[0]['tag']}  segP={b[0]['tuned']['P1.5']:.4f} "
              f"R={b[0]['tuned']['R1.5']:.4f}  LIFT={b[1]:+.4f}")
    print("=" * 122)

    # same table on the SPEC prune rule, in case the tuned length policy confounds it
    print("\n  [cross-check on prune[spec], no length modulation]")
    print(f"{'arm':42s} {'segP@1.5':>9} {'segR@1.5':>9} {'LIFT':>8}")
    print(f"{'BASELINE':42s} {bs['P1.5']:>9.4f} {bs['R1.5']:>9.4f} {'--':>8}")
    for x in sorted(arms, key=lambda z: z["tag"]):
        s = x["spec"]
        lf = lift(s["P1.5"], s["R1.5"], cRs, cPs)
        print(f"{'HYBRID ' + x['tag'].lstrip('_'):42s} {s['P1.5']:>9.4f} "
              f"{s['R1.5']:>9.4f} {lf:>+8.4f}")

    js = {"baseline": {"tuned": bt, "spec": bs, "n_seeds": base["n_seeds"]},
          "f_control": [{"tag": x["tag"], "n_seeds": x["n_seeds"], "tuned": x["tuned"],
                         "spec": x["spec"]} for x in ctl],
          "arms": [{"tag": x["tag"], "n_seeds": x["n_seeds"], "tuned": x["tuned"],
                    "spec": x["spec"], "seed_gate": x["gate"], "lift_tuned": l}
                   for x, l in rows]}
    p = os.path.join(OUT, "hybrid_step2_table.json")
    json.dump(js, open(p, "w"), indent=1, default=float)
    print(f"\nwrote {p}")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.figure(figsize=(8, 6.2))
    plt.plot(cR, cP, "-ok", lw=2, ms=4, label="ungated M1a f-control (TEST)")
    for x in ctl:
        plt.annotate(x["tag"].replace("_ctl_f", "f="), (x["tuned"]["R1.5"],
                     x["tuned"]["P1.5"]), fontsize=6)
    cols = {"_b_": "tab:blue", "_c_": "tab:purple", "_d_": "tab:orange",
            "_h1": "tab:blue", "_e_": "tab:cyan"}
    seen = set()
    for x, l in rows:
        c = next((v for k, v in cols.items() if x["tag"].startswith(k)), "tab:gray")
        lab = {"tab:blue": "2dgs_chair / gradn", "tab:purple": "2dgs_chair / dihedral",
               "tab:orange": "2dgs_chair_dist", "tab:cyan": "DT=2dgs"}.get(c, "other")
        plt.scatter(x["tuned"]["R1.5"], x["tuned"]["P1.5"], s=45, c=c,
                    label=lab if lab not in seen else None)
        seen.add(lab)
    plt.scatter([bt["R1.5"]], [bt["P1.5"]], marker="*", s=260, c="red", zorder=5,
                label="vanilla M1b baseline")
    plt.xlabel("segment recall @1.5px (TEST)")
    plt.ylabel("segment precision @1.5px (TEST)")
    plt.title("STEP 2: does the 2DGS seed gate beat simply lowering f?  (chair, TEST)")
    plt.grid(alpha=0.3); plt.legend(fontsize=8)
    pp = os.path.join(OUT, "hybrid_step2_frontier.png")
    plt.tight_layout(); plt.savefig(pp, dpi=120)
    print(f"wrote {pp}")


if __name__ == "__main__":
    main()
