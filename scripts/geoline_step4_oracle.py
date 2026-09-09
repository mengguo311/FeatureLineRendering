"""tier1/scripts/geoline_step4_oracle.py — STEP 4 dissociation arm.

*** EVAL-ONLY.  The oracle score is -median TEST-view distance to the nearest GT crease
    pixel.  It is a CEILING and never a method claim: it says what the best possible ranker
    could achieve on this scene's f=1.00 pulled pool, so a solid that misses the frozen bar
    can be attributed to the RANKER (oracle clears R 0.60) or to the POOL (oracle does not).
    Same construction and the same sweep grid as scripts/geoline_step3.py arm C. ***

It also re-prints the ZERO-KNOB operating point (the shipped spec consensus prune, no keep
fraction) so the gated number and its ceiling appear side by side for each solid.
"""
import argparse
import json
import os
import sys

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
sys.path.insert(0, os.path.join(TIER1, "scripts/explore/syn"))

from src import visibility, view_split                                  # noqa: E402
import run_m1b                                                          # noqa: E402

OUT = os.path.join(TIER1, "out")
KF_GRID = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.35, 0.3, 0.25, 0.2, 0.15,
           0.12, 0.1, 0.08, 0.06, 0.05, 0.04, 0.03, 0.02, 0.015, 0.01]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", required=True)
    ap.add_argument("--tag", default="_step4")
    args = ap.parse_args()

    z = np.load(os.path.join(OUT, f"linelets_{args.scene}{args.tag}.npz"))
    P1, T1, L1, KEEP = z["p"], z["t"], z["l"], z["keep"]
    from tune_lib import Harness                                       # EVAL ONLY (mesh)
    h = Harness(args.scene, views=tuple(view_split.TEST))

    zk = run_m1b.eval_segments(h, P1, T1, L1, keep=KEEP, taus=(1.5,))
    print(f"[{args.scene}] ZERO-KNOB (spec prune, no keep-frac): "
          f"P {zk[1.5][0]:.4f}  R {zk[1.5][1]:.4f}  n {int(KEEP.sum())}", flush=True)

    # ---- oracle score (EVAL-ONLY ceiling) ---------------------------------------------
    acc = [[] for _ in range(len(P1))]
    for v in view_split.TEST:
        vis, uv, _ = visibility.visible_mask(P1, h.cams[v], h.gbufs[v]["depth"])
        _, _, cdt = h.crease[v]
        u = np.clip(np.round(uv[:, 0]).astype(int), 0, cdt.shape[1] - 1)
        w = np.clip(np.round(uv[:, 1]).astype(int), 0, cdt.shape[0] - 1)
        d = cdt[w, u]
        for i in np.where(vis)[0]:
            acc[i].append(d[i])
    dm = np.array([np.median(a) if a else np.inf for a in acc])
    s = -dm

    front = []
    fin = np.isfinite(s)
    ss = np.where(fin, s, -np.inf)
    for kf in KF_GRID:
        k = (ss >= np.quantile(ss[fin], 1.0 - kf)) & fin if kf < 1.0 else fin
        if k.sum() < 10:
            continue
        e = run_m1b.eval_segments(h, P1, T1, L1, keep=k, taus=(1.5,))
        front.append({"keep_frac": kf, "n": int(k.sum()),
                      "P1.5": e[1.5][0], "R1.5": e[1.5][1]})
        print(f"    oracle kf {kf:5.3f}  n {int(k.sum()):6d}  P {e[1.5][0]:.4f}  "
              f"R {e[1.5][1]:.4f}", flush=True)

    ok = [r for r in front if r["P1.5"] >= 0.70]
    best = max(ok, key=lambda r: r["R1.5"]) if ok else None
    res = {"scene": args.scene, "n_pool": int(len(P1)),
           "zero_knob": {"P1.5": zk[1.5][0], "R1.5": zk[1.5][1], "n": int(KEEP.sum())},
           "oracle_frontier": front, "oracle_best_at_P0.70": best,
           "dissociation": (None if best is None else
                            ("RANKER failure if the solid misses its bar (oracle clears "
                             "R 0.60)" if best["R1.5"] >= 0.60 else
                             "POOL failure (oracle itself misses R 0.60)")),
           "mesh_eval_only": "oracle is a ceiling, never a method claim"}
    p = os.path.join(OUT, f"geoline_step4_oracle_{args.scene}.json")
    json.dump(res, open(p, "w"), indent=1)
    print(f"  ORACLE best at P>=0.70: " +
          (f"R {best['R1.5']:.4f} P {best['P1.5']:.4f}" if best else "none reaches P>=0.70"))
    print(f"  -> {p}", flush=True)


if __name__ == "__main__":
    main()
