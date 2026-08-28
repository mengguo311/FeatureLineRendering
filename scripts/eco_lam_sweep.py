"""ECO — sweep (consensus band) x lambda at the SEED level and rank by PRECISION AT MATCHED RECALL.

*** EVAL-ONLY DRIVER (tune_lib.Harness -> mesh). The method it drives is mesh-free. ***

WHY THIS METRIC AND NOT RAW P
    Any reweight that demotes gaussians also moves recall, so comparing an ECO arm's P against
    the base arm's P AT THE SAME f is confounded -- it is the same "a change that trades
    precision for recall is dominated by simply lowering f" objection the whole arc is built
    around.  So each ECO arm is scored against the BASE arm's OWN seed f-frontier interpolated
    to the arm's recall:

        dP(f) = P_eco(f) - interp( BASE frontier, R_eco(f) )

    dP > 0 means the consensus reweight bought precision that the base detector's own
    keep-fraction dial could not buy at that recall.  This is the seed-level shape of the
    spec's PARTIAL criterion ("ECO strictly increases P@1.5 at matched R"), and it is what the
    chair VAL selection is made on.  TEST is computed too but ONLY printed for audit.

SELECTION IS CHAIR-VAL-ONLY, exactly as CMEPI selected its detector threshold.
"""
import os
import sys
import glob
import json
import argparse

import numpy as np
from scipy.stats import rankdata

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
SYN = os.path.join(TIER1, "scripts/explore/syn")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
sys.path.insert(0, SYN)
OUT = os.path.join(TIER1, "out")
_R = lambda v: rankdata(v) / len(v)

sys.path.insert(0, os.path.join(TIER1, "scripts"))
from eco_score import spend, BASE_ARM                                   # noqa: E402


def interp_P_at_R(front, R):
    a = sorted(front, key=lambda x: x[0])
    rs, ps = [x[0] for x in a], [x[1] for x in a]
    if R <= rs[0] or R >= rs[-1]:
        return float("nan")
    return float(np.interp(R, rs, ps))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="chair")
    ap.add_argument("--det", default="dexined", choices=["dexined", "teed"])
    ap.add_argument("--glob", default=None,
                    help="which consensus fields to sweep; default all rho=0 ones for --det")
    ap.add_argument("--mode", default="add", choices=["add", "mul", "veto"])
    ap.add_argument("--lams", type=float, nargs="*", default=[0.1, 0.25, 0.5, 1.0, 2.0])
    ap.add_argument("--c_thrs", type=float, nargs="*", default=[0.3, 0.5, 0.7, 0.9])
    ap.add_argument("--fs", type=float, nargs="*",
                    default=[0.50, 0.45, 0.40, 0.35, 0.30, 0.22, 0.15])
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    base_arm = BASE_ARM[args.det]
    base = np.load(os.path.join(SYN, f"finalscore_overall_{args.scene}__{base_arm}.npy"))
    thr = "0.7" if args.det == "dexined" else "0.5"
    pat = args.glob or f"eco_C_{args.scene}__{args.det}{thr}_*_r0_*.npy"
    paths = sorted(glob.glob(os.path.join(OUT, pat)))
    assert paths, f"no consensus fields match {pat}"
    print(f"[lam] {len(paths)} consensus fields, mode={args.mode}, "
          f"base={base_arm}, M={len(base)}", flush=True)

    from src import common, render, view_split                          # noqa: E402
    from tune_lib import Harness                                        # EVAL ONLY
    g = common.load_gaussians(args.scene)
    keep = render.defloat_mask(g["mu"], g["opacity"])
    X = g["mu"][keep]
    H = {sp: Harness(args.scene, views=tuple(getattr(view_split, sp.upper())))
         for sp in ("val", "test")}

    def frontier(s):
        o = np.argsort(-s, kind="stable")
        out = {}
        for sp in ("val", "test"):
            rows = []
            for f in args.fs:
                k = np.zeros(len(X), bool)
                k[o[:int(round(f * len(X)))]] = True
                p, r, n = H[sp].evaluate(X, extra_mask=k)
                rows.append((float(r), float(p), f))
            out[sp] = rows
        return out

    BASEF = frontier(base)
    print(f"[lam] BASE val: " + " ".join(f"f{f:.2f} P{p:.4f} R{r:.4f}"
                                         for r, p, f in BASEF["val"]), flush=True)

    grid = ([(None, t) for t in args.c_thrs] if args.mode == "veto"
            else [(l, None) for l in args.lams])
    rows = []
    for cp in paths:
        ctag = os.path.basename(cp)[len(f"eco_C_{args.scene}__"):-4]
        C = np.load(cp)
        for lam, ct in grid:
            s = spend(base, C, args.mode, lam if lam is not None else 0.0,
                      c_thr=ct if ct is not None else 0.5)
            fr = frontier(s)
            rec = {"ctag": ctag, "mode": args.mode, "lam": lam, "c_thr": ct}
            for sp in ("val", "test"):
                dps = [(p - interp_P_at_R([(r0, p0) for r0, p0, _ in BASEF[sp]], r), f)
                       for r, p, f in fr[sp]]
                fin = [(d, f) for d, f in dps if np.isfinite(d)]
                rec[f"{sp}_dP_by_f"] = {f"{f:.2f}": (None if not np.isfinite(d) else d)
                                        for d, f in dps}
                rec[f"{sp}_best_dP"] = (max(d for d, _ in fin) if fin else float("nan"))
                rec[f"{sp}_best_f"] = (max(fin)[1] if fin else float("nan"))
                rec[f"{sp}_n_pos"] = sum(1 for d, _ in fin if d > 0)
                rec[f"{sp}_n_fin"] = len(fin)
                rec[f"{sp}_PR"] = [(r, p, f) for r, p, f in fr[sp]]
            rows.append(rec)
            print(f"  {ctag:>34} {args.mode}"
                  f"{('_l%g' % lam) if lam is not None else ('_c%g' % ct):>8}  "
                  f"VAL best dP {rec['val_best_dP']:+.4f} @f{rec['val_best_f']} "
                  f"({rec['val_n_pos']}/{rec['val_n_fin']})   "
                  f"| TEST {rec['test_best_dP']:+.4f} ({rec['test_n_pos']}/{rec['test_n_fin']})",
                  flush=True)

    rows.sort(key=lambda r: -(r["val_best_dP"] if np.isfinite(r["val_best_dP"]) else -9))
    print("\n" + "=" * 116)
    print(f"TOP BY **VAL** (the selection split) — seed-level precision gain at matched recall")
    print("=" * 116)
    for r in rows[:12]:
        k = ("l%g" % r["lam"]) if r["lam"] is not None else ("c%g" % r["c_thr"])
        print(f"  {r['ctag']:>34} {r['mode']}_{k:<6} "
              f"VAL {r['val_best_dP']:+.4f} @f{r['val_best_f']} "
              f"({r['val_n_pos']}/{r['val_n_fin']} f positive)   "
              f"TEST {r['test_best_dP']:+.4f} ({r['test_n_pos']}/{r['test_n_fin']})")
    jp = args.out or os.path.join(
        OUT, f"eco_lam_sweep_{args.scene}_{args.det}_{args.mode}.json")
    json.dump({"scene": args.scene, "det": args.det, "base_arm": base_arm,
               "mode": args.mode, "fs": args.fs,
               "base_frontier": {k: v for k, v in BASEF.items()},
               "rows": rows}, open(jp, "w"), indent=2, default=float)
    print(f"\nwrote {jp}")


if __name__ == "__main__":
    main()
