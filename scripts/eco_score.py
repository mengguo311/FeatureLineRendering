"""ECO — spend the epipolar-consensus score C into the M1a ranking vector, and sweep on VAL.

*** EVAL-ONLY DRIVER in --sweep mode (imports tune_lib.Harness -> mesh, for VAL/TEST seed P/R).
    The METHOD it drives -- the reweighting itself -- is mesh-free and lives in `spend()`. ***

THE THREE WAYS TO SPEND C, and why the first is primary
    base = the published CMEPI carrier's ranking vector, e.g.
           scripts/explore/syn/finalscore_overall_<scene>__dexined_native_0.7.npy
    _R    = final_recipe's own rank transform, rankdata(v)/len(v) -> (0, 1]

      add   s = base + lambda * _R(C)
            The recipe's OWN idiom: score_from_evidence combines its channels as
            g = _R(soft) + 0.5*_R(rq90).  Consensus enters as one more rank-transformed
            channel.  PRIMARY.
      mul   s = _R(base) * (1 + lambda * C)
            The spec's literal example, made well-posed by rank-normalising the base first
            (the raw base is a sum of ranks plus a local-competition term and is not
            sign-constrained, so multiplying it directly is not monotone).  SENSITIVITY ARM.
      veto  s = base - BIG * (C < c_thr)
            The ABLATION the spec demands: the SAME consensus signal used as a hard cull
            instead of a reweight.  NG-MEC Stage 1 is the precedent -- its veto worked in 2D
            and lost ~7:1 downstream to the learned prior -- so this arm re-tests the
            "additive, not veto" law on new machinery.  It must UNDER-PERFORM `add`.

    All three are monotone in `base` at fixed C, and none of them changes n_seeds: at a given
    keep-fraction f the pipeline still takes round(f*M) gaussians out of the SAME candidate
    pool.  ECO can only re-rank, never enlarge -- which is exactly the property that makes the
    comparison against the published Canny f-frontier fair, and it is also why an absolute
    precision gate is a much harder ask than a LIFT_P gate.

SELECTION DISCIPLINE (identical to CMEPI's)
    Every knob -- lambda, sigma_c, tau, rho, K, c_thr -- is chosen on CHAIR VAL only, then
    transferred to lego UNCHANGED.  TEST numbers are printed in the sweep for audit but are
    never read by the selection, which uses `--select_split val` and chair alone.
"""
import os
import sys
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
_R = lambda v: rankdata(v) / len(v)          # final_recipe's own transform
BIG = 1e6

BASE_ARM = {"dexined": "dexined_native_0.7", "teed": "teed_native_0.5"}


def spend(base, C, mode, lam, c_thr=0.5, q=None):
    """METHOD PATH, mesh-free: combine the base ranking vector with the consensus score."""
    assert base.shape == C.shape, (base.shape, C.shape)
    if mode == "add":
        return base + lam * _R(C)
    if mode == "mul":
        return _R(base) * (1.0 + lam * C)
    if mode == "veto":
        return base - BIG * (C < c_thr).astype(np.float64)
    if mode == "vetoq":
        # QUANTILE-ANCHORED veto.  An ABSOLUTE c_thr is not a transferable operating point:
        # at the frozen band, c=0.9 culls 23.0% of chair's gaussians but 32.8% of lego's, so
        # "the same veto" would mean two different interventions and the chair->lego transfer
        # would be meaningless.  Freezing the QUANTILE q instead culls exactly q of the pool on
        # both scenes, which is what makes the ablation a fair test of veto-vs-additive.
        return base - BIG * (C < np.quantile(C, q)).astype(np.float64)
    raise ValueError(mode)


def arm_name(det, mode, lam, ctag, c_thr=None):
    lamtag = f"{lam:g}".replace(".", "p")
    if mode == "veto":
        return f"eco_{det}_veto_c{c_thr:g}".replace(".", "p") + f"_{ctag}"
    return f"eco_{det}_{mode}_l{lamtag}_{ctag}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="chair")
    ap.add_argument("--det", default="dexined", choices=["dexined", "teed"])
    ap.add_argument("--ctag", required=True,
                    help="consensus tag, i.e. the stem of out/eco_C_<scene>__<ctag>.npy")
    ap.add_argument("--mode", default="add", choices=["add", "mul", "veto"])
    ap.add_argument("--lams", type=float, nargs="*",
                    default=[0.25, 0.5, 1.0, 2.0, 4.0])
    ap.add_argument("--c_thrs", type=float, nargs="*", default=[0.5, 0.7, 0.9],
                    help="veto-mode cull thresholds")
    ap.add_argument("--sweep", action="store_true",
                    help="evaluate the grid at the SEED level on VAL (+TEST for audit) "
                         "and write out/eco_sweep_<scene>_<tag>.json")
    ap.add_argument("--emit", action="store_true",
                    help="write scripts/explore/syn/finalscore_overall_<scene>__<arm>.npy "
                         "for every (mode, lambda) in the grid")
    ap.add_argument("--tag", default="", help="suffix for the sweep json")
    args = ap.parse_args()

    base_arm = BASE_ARM[args.det]
    bp = os.path.join(SYN, f"finalscore_overall_{args.scene}__{base_arm}.npy")
    cp = os.path.join(OUT, f"eco_C_{args.scene}__{args.ctag}.npy")
    assert os.path.exists(bp), f"missing base score {bp}"
    assert os.path.exists(cp), f"missing consensus {cp}"
    base = np.load(bp)
    C = np.load(cp)
    assert base.shape == C.shape, (base.shape, C.shape)
    print(f"[eco-score] scene={args.scene} base={base_arm} ctag={args.ctag} "
          f"M={len(base)}  C mean {C.mean():.4f} sd {C.std():.4f}", flush=True)

    grid = ([("veto", None, t) for t in args.c_thrs] if args.mode == "veto"
            else [(args.mode, l, None) for l in args.lams])

    emitted = {}
    if args.emit:
        for mode, lam, ct in grid:
            s = spend(base, C, mode, lam if lam is not None else 0.0,
                      c_thr=ct if ct is not None else 0.5)
            nm = arm_name(args.det, mode, lam if lam is not None else 0.0, args.ctag, ct)
            sp = os.path.join(SYN, f"finalscore_overall_{args.scene}__{nm}.npy")
            np.save(sp, s)
            emitted[nm] = sp
            print(f"  [emit] {nm} -> {os.path.relpath(sp, TIER1)}", flush=True)

    if not args.sweep:
        json.dump({"emitted": emitted}, open(
            os.path.join(OUT, f"eco_emit_{args.scene}_{args.det}_{args.mode}{args.tag}.json"),
            "w"), indent=2)
        return

    # ---------------------------------------------------------------- SEED-LEVEL SWEEP
    from src import common, render, view_split                       # noqa: E402
    from tune_lib import Harness                                     # EVAL ONLY
    g = common.load_gaussians(args.scene)
    keep = render.defloat_mask(g["mu"], g["opacity"])
    X = g["mu"][keep]
    assert len(X) == len(base)
    H = {sp: Harness(args.scene, views=tuple(getattr(view_split, sp.upper())))
         for sp in ("val", "test")}
    FS = (0.50, 0.45, 0.40, 0.35, 0.30, 0.22, 0.15)

    def frontier(s):
        o = np.argsort(-s, kind="stable")
        rows = {}
        for sp in ("val", "test"):
            rr = []
            for f in FS:
                k = np.zeros(len(X), bool)
                k[o[:int(round(f * len(X)))]] = True
                p, r, n = H[sp].evaluate(X, extra_mask=k)
                rr.append({"f": f, "P": float(p), "R": float(r), "n": int(n)})
            rows[sp] = rr
        return rows

    res = {"scene": args.scene, "det": args.det, "base_arm": base_arm, "ctag": args.ctag,
           "mode": args.mode, "C_mean": float(C.mean()), "C_std": float(C.std()),
           "arms": {}}
    res["arms"]["BASE"] = frontier(base)
    for mode, lam, ct in grid:
        s = spend(base, C, mode, lam if lam is not None else 0.0,
                  c_thr=ct if ct is not None else 0.5)
        nm = arm_name(args.det, mode, lam if lam is not None else 0.0, args.ctag, ct)
        res["arms"][nm] = frontier(s)

    jp = os.path.join(OUT, f"eco_sweep_{args.scene}_{args.det}_{args.mode}{args.tag}.json")
    json.dump(res, open(jp, "w"), indent=2)

    print(f"\n{'arm':>42} " + "".join(f"{'f=%.2f' % f:>16}" for f in FS))
    print(f"{'(VAL P/R — selection split)':>42}")
    for nm, rows in res["arms"].items():
        cells = "".join(f"{r['P']:7.4f}/{r['R']:<8.4f}" for r in rows["val"])
        print(f"{nm:>42} {cells}")
    print(f"\n{'(TEST P/R — audit only, NOT used for selection)':>42}")
    for nm, rows in res["arms"].items():
        cells = "".join(f"{r['P']:7.4f}/{r['R']:<8.4f}" for r in rows["test"])
        print(f"{nm:>42} {cells}")
    print(f"\nwrote {jp}")


if __name__ == "__main__":
    main()
