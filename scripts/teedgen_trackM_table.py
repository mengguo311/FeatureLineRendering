"""TRACK M — which property of TEED's edge map does M1b actually consume?

*** ANALYSIS ONLY — reads jsons run_m1b.py already wrote.  No mesh, no GPU. ***

Every arm is scored the same way TRACK C scored TEED: LIFT_P against the CANNY f-frontier
interpolated to the same recall.  The reference lift is the published TEED arm.  Then:

  M1  continuous confidence     d = LIFT_P(teed_soft)  - LIFT_P(teed_binarised)
      -> if ~0, a hard step at 0.5 throws away nothing the pipeline was using.
  M2  connected-component len   d = LIFT_P(teed_cc_L)  - LIFT_P(teed_no_filter)
      -> if ~0 (or negative for large L), stroke continuity is not the operative factor.
  M3  selectivity as a MASK     ratio = LIFT_P(canny_masked_by_TEED) / LIFT_P(teed)
      -> TEED contributes ONLY a binary spatial support; every edge pixel that survives was
         placed by Canny.  A high ratio means the win is WHERE TEED SAYS THERE IS A CONTOUR,
         not TEED's own sub-pixel edge placement, not its calibrated confidence.
      The base for the permissive-Canny variant is that SAME Canny unmasked, which scores
      -0.17..-0.23 -- so the mask's effect is measured as a swing, not just a level.
  M3-CTL shifted mask           the identical mask rolled 15/40 px: same area, same shape
      statistics, MORE pixels removed, only the registration destroyed.
"""
import os
import sys
import json
import glob
import argparse

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from teedgen_verdict import analyse, SEG, PTS          # noqa: E402

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
OUT = os.path.join(TIER1, "out")


def load(prefix):
    arms = {}
    for p in sorted(glob.glob(os.path.join(OUT, prefix + "*.json"))):
        tag = os.path.basename(p)[len(prefix):-len(".json")]
        name, f = tag.rsplit("_f", 1)
        arms.setdefault(name, {})[float(f)] = json.load(open(p))
    return arms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="m1b_chair_tm_")
    ap.add_argument("--ref", default="teed05", help="the published TEED arm = reference lift")
    ap.add_argument("--extra_prefix", default="m1b_chair_tc_",
                    help="where the un-masked permissive-Canny CONTROL arms live")
    ap.add_argument("--extra", nargs="*", default=["cannysharplow", "cannysharp"])
    ap.add_argument("--kind", default="segments", choices=["segments", "points"])
    ap.add_argument("--metric", default="LIFT_P_lb", choices=["LIFT_P_lb", "LIFT_P"],
                    help="LIFT_P_lb = Pareto envelope (conservative, well posed on a "
                         "non-monotone frontier); LIFT_P = interpolated (smooth, and what "
                         "the published chair report used).")
    args = ap.parse_args()

    arms = load(args.prefix)
    stage = SEG if args.kind == "segments" else PTS
    # pull the unmasked permissive-Canny controls in under the same canny frontier
    if args.extra_prefix:
        ex = load(args.extra_prefix)
        for nm in args.extra:
            if nm in ex:
                arms[nm] = ex[nm]
    front, res = analyse(arms, args.kind, stage)
    if args.ref not in res:
        sys.exit(f"reference arm {args.ref} not present ({sorted(res)})")

    lift = {n: {r["f"]: r[args.metric] for r in v["rows"]} for n, v in res.items()}
    PR = {n: {r["f"]: (r["P"], r["R"]) for r in v["rows"]} for n, v in res.items()}
    FS = sorted({f for v in lift.values() for f in v}, reverse=True)

    print("=" * 118)
    print(f"TRACK M — LIFT_P vs the canny f-frontier ({args.kind}, held-out TEST, "
          f"metric={args.metric}). reference arm = {args.ref}")
    print("=" * 118)
    print(f"{'arm':>20} " + "".join(f"{'f=%.2f' % f:>10}" for f in FS) + f"{'best':>10}")
    order = [args.ref] + [n for n in sorted(res) if n != args.ref]
    for n in order:
        cells = "".join(
            (f"{lift[n][f]:+10.4f}" if f in lift[n] and np.isfinite(lift[n][f]) else f"{'':>10}")
            for f in FS)
        fin = [v for v in lift[n].values() if np.isfinite(v)]
        print(f"{n:>20} {cells}{(max(fin) if fin else float('nan')):+10.4f}")

    print("\n" + "=" * 118)
    print("FACTOR DECOMPOSITION — at MATCHED f, against the reference TEED arm")
    print("=" * 118)
    print(f"{'factor':>8}  {'arm':>20} {'base':>20} " +
          "".join(f"{'f=%.2f' % f:>10}" for f in FS) + f"{'mean d':>10}")

    def line(tag, arm, base):
        if arm not in lift:
            return None
        ds = []
        cells = ""
        for f in FS:
            a = lift.get(arm, {}).get(f, np.nan)
            b = (lift.get(base, {}).get(f, np.nan) if base else 0.0)
            d = a - b
            cells += (f"{d:+10.4f}" if np.isfinite(d) else f"{'':>10}")
            if np.isfinite(d):
                ds.append(d)
        m = float(np.mean(ds)) if ds else float("nan")
        print(f"{tag:>8}  {arm:>20} {(base or 'canny frontier'):>20} {cells}{m:+10.4f}")
        return m

    out = {"kind": args.kind, "metric": args.metric, "reference": args.ref,
           "lift": lift, "PR": PR, "delta": {}}
    for tag, arm, base in (
            ("M1", "m1_soft_g1.0", args.ref),
            ("M2", "m2_cc10", args.ref),
            ("M2", "m2_cc25", args.ref),
            ("M2", "m2_cc50", args.ref),
            ("M3", "m3_maskM1a_d2", None),
            ("M3", "m3_masksharplow_d2", None),
            ("M3-sw", "m3_masksharplow_d2", "cannysharplow"),
            ("M3-CTL", "m3_shift15_d2", None),
            ("M3-CTL", "m3_shift40_d2", None),
            ("CTL", "cannysharplow", None),
            ("CTL", "cannysharp", None)):
        m = line(tag, arm, base)
        if m is not None:
            out["delta"][f"{tag}:{arm}|{base or 'frontier'}"] = m

    print("\n" + "=" * 118)
    print("CARRIED FRACTION of the TEED lift  (LIFT_P(arm) / LIFT_P(teed)) at matched f")
    print("=" * 118)
    print(f"{'arm':>20} " + "".join(f"{'f=%.2f' % f:>10}" for f in FS) + f"{'mean':>10}")
    for n in order:
        if n == args.ref:
            continue
        rs, cells = [], ""
        for f in FS:
            a, b = lift.get(n, {}).get(f, np.nan), lift[args.ref].get(f, np.nan)
            r = a / b if (np.isfinite(a) and np.isfinite(b) and abs(b) > 1e-9) else np.nan
            cells += (f"{r:10.2f}" if np.isfinite(r) else f"{'':>10}")
            if np.isfinite(r):
                rs.append(r)
        print(f"{n:>20} {cells}{(np.mean(rs) if rs else np.nan):10.2f}")
        out.setdefault("carried_fraction", {})[n] = (float(np.mean(rs)) if rs else None)

    jp = os.path.join(OUT,
                      f"teedgen_trackM_{args.prefix.strip('_')}_{args.kind}_{args.metric}.json")
    json.dump(out, open(jp, "w"), indent=2, default=float)
    print(f"\nwrote {jp}")


if __name__ == "__main__":
    main()
