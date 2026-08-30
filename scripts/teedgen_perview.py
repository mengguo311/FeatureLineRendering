"""Per-view paired significance for the headline arm comparisons.

*** EVAL ONLY (tune_lib.Harness -> mesh_oracle). ***

Every M1b P/R in this experiment is a MEAN over the 10 held-out TEST views, and
RECALL_RESULTS.md already recorded that the per-view spread on chair is 0.05-0.12 -- wide
enough that a difference of 0.02-0.03 between arms could in principle be one or two views.
So the headline orderings are re-read as PAIRED per-view differences: same view, same
protocol, only the edge source differs.  Reported: mean d, sd, sem, t, and the sign count.
The linelets are the ones run_m1b.py already saved; nothing is re-optimised.
"""
import os
import sys
import json
import argparse

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
OUT = os.path.join(TIER1, "out")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", required=True)
    ap.add_argument("--pairs", nargs="+", required=True,
                    help="A:B tag pairs, e.g. tc_teed_native_0.5_f0.30:tc_canny_f0.30")
    ap.add_argument("--tau", type=float, default=1.5)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    from run_m1b import eval_segments, eval_points          # EVAL ONLY
    from tune_lib import Harness
    from src import view_split
    h = Harness(args.scene, views=tuple(view_split.TEST))

    cache = {}

    def measure(tag):
        if tag in cache:
            return cache[tag]
        z = np.load(os.path.join(OUT, f"linelets_{args.scene}_{tag}.npz"))
        # reproduce run_m1b's headline "tuned" arm is not possible from the npz alone
        # (it stores the SPEC keep mask), so the paired test is run on the SPEC stage,
        # which the same npz defines exactly and which every arm shares.
        seg = eval_segments(h, z["p"], z["t"], z["l"], keep=z["keep"],
                            taus=(args.tau,), per_view=True)
        pts = eval_points(h, z["p"], keep=z["keep"], taus=(args.tau,))
        cache[tag] = {"segP": np.array(seg[args.tau][0]),
                      "segR": np.array(seg[args.tau][1]),
                      "pts": pts, "n_keep": int(z["keep"].sum())}
        return cache[tag]

    res = {"scene": args.scene, "tau": args.tau, "views": list(h.views), "pairs": {}}
    print(f"[perview] {args.scene}, TEST views {h.views}, tau={args.tau}, "
          f"stage = pull+prune[spec] (the stage the saved keep-mask defines)\n")
    hdr = (f"{'A vs B':>52} {'metric':>5} {'meanA':>8} {'meanB':>8} {'mean d':>8} "
           f"{'sd':>7} {'sem':>7} {'t':>7} {'A>B views':>10}")
    print(hdr)
    print("-" * len(hdr))
    for pair in args.pairs:
        A, B = pair.split(":")
        a, b = measure(A), measure(B)
        row = {}
        for m in ("segP", "segR"):
            d = a[m] - b[m]
            sd = float(d.std(ddof=1))
            sem = sd / np.sqrt(len(d))
            t = float(d.mean() / sem) if sem > 0 else float("inf")
            row[m] = {"meanA": float(a[m].mean()), "meanB": float(b[m].mean()),
                      "mean_d": float(d.mean()), "sd": sd, "sem": float(sem), "t": t,
                      "n_A_gt_B": int((d > 0).sum()), "n": int(len(d)),
                      "per_view_d": d.tolist()}
            print(f"{A + ' vs ' + B:>52} {m:>5} {a[m].mean():8.4f} {b[m].mean():8.4f} "
                  f"{d.mean():+8.4f} {sd:7.4f} {sem:7.4f} {t:+7.2f} "
                  f"{int((d > 0).sum()):5d}/{len(d):<4d}")
        row["n_keep"] = {"A": a["n_keep"], "B": b["n_keep"]}
        res["pairs"][pair] = row
    jp = args.out or os.path.join(OUT, f"teedgen_perview_{args.scene}.json")
    json.dump(res, open(jp, "w"), indent=2)
    print(f"\nwrote {jp}")


if __name__ == "__main__":
    main()
