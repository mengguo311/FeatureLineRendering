"""tier1/scripts/tgap_paired.py — TGAP paired per-view comparison (EVAL; mesh via Harness).

The frontier gates aggregate over the 10 held-out TEST views.  This reports the same
comparisons per view and paired, which is how ECO reported its precision claim, so a small
mean difference can be told apart from a small difference that is also unstable across views.
"""
import json
import os
import sys

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))

from src import view_split, tgap_gate                                    # noqa: E402

OUT = os.path.join(TIER1, "out")
ARMS = [(0.50, 0.0, 0.0, "A@f0.50"), (0.50, 0.0, 0.2, "B_frozen@f0.50"),
        (0.55, 0.0, 0.0, "A@f0.55"), (0.50, 0.6, 0.6, "B_spatial@f0.50"),
        (1.00, 0.0, 0.0, "A@f1.00"), (1.00, 0.0, 0.2, "B_frozen@f1.00")]


def main():
    from run_m1b import eval_segments                                    # EVAL harness
    from tune_lib import Harness                                         # mesh_oracle
    h = Harness("lego", views=tuple(view_split.TEST))
    res = {}
    for f, a, b, name in ARMS:
        z = np.load(os.path.join(OUT, f"tgap_pull_lego_f{f:.2f}.npz"))
        st = {"inlier_ratio": z["inlier_ratio"], "median_resid": z["median_resid"],
              "n_vis": z["n_vis"]}
        k, lm = tgap_gate.arm_masks(st, z["l"], z["E"], a, b)
        e = eval_segments(h, z["p"], z["t"], lm, keep=k, per_view=True)
        res[name] = {"P": np.array(e[1.5][0]), "R": np.array(e[1.5][1]),
                     "n": int(k.sum())}
        print(f"{name:18s} n={res[name]['n']:6d}  P={res[name]['P'].mean():.4f}  "
              f"R={res[name]['R'].mean():.4f}")

    def paired(x, y):
        o = {}
        for m in ("P", "R"):
            d = res[x][m] - res[y][m]
            sd = d.std(ddof=1)
            o[m] = {"mean": float(d.mean()),
                    "t": float(d.mean() / (sd / np.sqrt(len(d)))) if sd > 0 else float("inf"),
                    "n_pos": int((d > 0).sum()), "n": int(len(d))}
        return o

    cmp = {}
    for x, y in [("B_frozen@f0.50", "A@f0.50"), ("B_frozen@f0.50", "A@f0.55"),
                 ("B_spatial@f0.50", "A@f0.50"), ("B_frozen@f1.00", "A@f1.00")]:
        cmp[f"{x} vs {y}"] = paired(x, y)
        c = cmp[f"{x} vs {y}"]
        print(f"  {x:18s} vs {y:12s}  dP {c['P']['mean']:+.4f} t={c['P']['t']:+6.2f} "
              f"{c['P']['n_pos']}/{c['P']['n']}   dR {c['R']['mean']:+.4f} "
              f"t={c['R']['t']:+6.2f} {c['R']['n_pos']}/{c['R']['n']}")
    json.dump({"per_view": {k: {"P": v["P"].tolist(), "R": v["R"].tolist(), "n": v["n"]}
                            for k, v in res.items()}, "paired": cmp},
              open(os.path.join(OUT, "tgap_paired_lego.json"), "w"), indent=1)
    print("wrote out/tgap_paired_lego.json")


if __name__ == "__main__":
    main()
