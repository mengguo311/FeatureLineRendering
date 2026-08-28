"""tier1/scripts/tgap_eval.py — TGAP stage 2: score arms A / B / C off the dumped pulls.

*** EVAL.  Below the banner in run_m1b.py this is where the GT mesh is allowed, and this
    script is on that side: it imports run_m1b.eval_segments -> tune_lib.Harness ->
    mesh_oracle.  The METHOD is src/tgap_gate.py, which imports none of that. ***

Every arm is scored by the SAME rasteriser, the SAME GT crease pixels and the SAME tau as the
committed headline (`run_m1b.eval_segments`, stage `AFTER pull+prune[tuned+len]`,
tau = 1.5 px, segment protocol).  Nothing about the measurement differs between arms; only
the two thresholds of src/tgap_gate.arm_masks do.

  A  alpha = beta = 0                      the committed tuned+len prune
  B  TGAP, spatial: thresholds scaled by (1 - alpha*E) / (1 - beta*E)
  C  TEED-BLIND control: the SAME two thresholds relaxed GLOBALLY to the constants
     (tau_r, tau_L), i.e. arm B with the spatial information deleted.  A grid is swept so
     that C can be matched to B's recall, and so that C's own Pareto envelope -- the best any
     global relaxation can do at a given recall -- can be used as the adversarial control.

--split val  : the ONLY split alpha/beta/global-r may be chosen on.
--split test : held-out, reported.
"""
import argparse
import json
import os
import sys
import time

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))

from src import view_split, tgap_gate                                    # noqa: E402

OUT = os.path.join(TIER1, "out")

F_ALL = [0.15, 0.22, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65,
         0.70, 0.80, 0.85, 0.90, 0.95, 1.00]
F_ARMS = [0.15, 0.22, 0.30, 0.35, 0.40, 0.45, 0.50, 0.70, 1.00]
ALPHAS = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
BETAS = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
TAU_R = [0.50, 0.45, 0.40, 0.35, 0.30, 0.25, 0.20, 0.15, 0.10, 0.05, 0.00]
TAU_L = [0.90, 0.75, 0.60, 0.45, 0.30, 0.15, 0.00]


def load_dump(scene, f, e_key="E", pull_tag=""):
    p = os.path.join(OUT, f"tgap_pull_{scene}_f{f:.2f}{pull_tag}.npz")
    if not os.path.exists(p):
        raise FileNotFoundError(p)
    z = np.load(p)
    st = {"inlier_ratio": z["inlier_ratio"], "median_resid": z["median_resid"],
          "n_vis": z["n_vis"]}
    if e_key not in z.files:
        raise KeyError(f"{e_key} not in {p} (run scripts/tgap_e_variants.py first)")
    return {"p": z["p"], "t": z["t"], "l": z["l"], "E": z[e_key], "st": st}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="lego")
    ap.add_argument("--split", default="val", choices=["val", "test"])
    ap.add_argument("--arms", default="A,B,C")
    ap.add_argument("--e_key", default="E",
                    help="which E field to gate on; alternatives are written into the same "
                         "dump by scripts/tgap_e_variants.py (E_max_0p5, E_mean_0p8, ...)")
    ap.add_argument("--f_only", type=float, nargs="*", default=None,
                    help="restrict the sweep to these f (robustness runs)")
    ap.add_argument("--pull_tag", default="",
                    help="score a DIFFERENT pull dump, e.g. _g1 for the untuned "
                         "trust-region auxiliary written by tgap_pull.py --pull_gamma")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    from run_m1b import eval_segments                                    # EVAL harness
    from tune_lib import Harness                                         # imports mesh_oracle
    views = {"val": view_split.VAL, "test": view_split.TEST}[args.split]
    h = Harness(args.scene, views=tuple(views))
    want = set(args.arms.split(","))

    dst = os.path.join(OUT, f"tgap_arms_{args.scene}_{args.split}{args.tag}.json")
    res = json.load(open(dst)) if os.path.exists(dst) else {
        "scene": args.scene, "split": args.split, "views": list(views),
        "stage": "AFTER pull+prune[tuned+len]", "protocol": "segments, tau=1.5",
        "rows": []}
    have = {(r["arm"], r["f"], r["k1"], r["k2"]) for r in res["rows"]}

    def score(arm, f, k1, k2, keep, l_mod, D):
        key = (arm, f, k1, k2)
        if key in have:
            return
        e = eval_segments(h, D["p"], D["t"], l_mod, keep=keep)
        res["rows"].append({"arm": arm, "f": f, "k1": k1, "k2": k2,
                            "n_keep": int(keep.sum()),
                            "P1.5": e[1.5][0], "R1.5": e[1.5][1],
                            "P2.5": e[2.5][0], "R2.5": e[2.5][1],
                            "n_px": e["n_px"]})
        have.add(key)

    t_all = time.time()
    f_list = args.f_only if args.f_only else F_ALL
    for f in f_list:
        try:
            D = load_dump(args.scene, f, args.e_key, args.pull_tag)
        except FileNotFoundError as ex:
            print(f"  MISSING {ex} — skipped", flush=True)
            continue
        t0 = time.time()
        n0 = len(res["rows"])
        if "A" in want:
            k, lm = tgap_gate.arm_masks(D["st"], D["l"], D["E"], 0.0, 0.0)
            score("A", f, 0.0, 0.0, k, lm, D)
        if f in F_ARMS and "B" in want:
            for a in ALPHAS:
                for b in BETAS:
                    if a == 0.0 and b == 0.0:
                        continue                       # that is arm A, already scored
                    k, lm = tgap_gate.arm_masks(D["st"], D["l"], D["E"], a, b)
                    score("B", f, a, b, k, lm, D)
        if f in F_ARMS and "C" in want:
            ones = np.ones(len(D["l"]))
            for tr in TAU_R:
                for tl in TAU_L:
                    if tr == 0.50 and tl == 0.90:
                        continue                       # that is arm A, already scored
                    # E == 1 everywhere: (1-a_g) = tau_r/0.50, (1-b_g) = tau_L/0.90
                    k, lm = tgap_gate.arm_masks(D["st"], D["l"], ones,
                                                1.0 - tr / 0.50, 1.0 - tl / 0.90)
                    score("C", f, tr, tl, k, lm, D)
        json.dump(res, open(dst, "w"), indent=1)
        print(f"  f={f:.2f}  +{len(res['rows'])-n0} rows in {time.time()-t0:.0f}s "
              f"(total {len(res['rows'])})", flush=True)
    print(f"wrote {dst}  ({time.time()-t_all:.0f}s)")


if __name__ == "__main__":
    main()
