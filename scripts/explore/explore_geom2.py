"""Round 2: seed-level features + combination analysis. EVAL-SIDE (oracle for analysis only)."""
import os
import sys
import time
import numpy as np

sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tune_lib import Harness, structure_tensor, nms_along_e1
from _geom_feats import compute_all
from _geom_feats2 import compute_seedlevel
from explore_geom import auc, labels, sweep, FS, SCRATCH


def main():
    t0 = time.time()
    h = Harness("chair")
    st = structure_tensor(h.X, h.N, 8)
    cand = np.where(st["s_crease"] > 0.05)[0]
    sel = nms_along_e1(h.X, cand, st["s_crease"], st["e1"], st["knn"])
    P = h.X[sel]
    F1 = compute_all(h, st)
    F2 = compute_seedlevel(h, sel, st)
    F = {k: np.asarray(v, float)[sel] for k, v in F1.items()}
    F.update({k: np.asarray(v, float) for k, v in F2.items()})
    near, visa, ncnt, vcnt = labels(h, P)
    print(f"pool={len(sel)} vis={visa.sum()} near={near.sum()} feats={len(F)} "
          f"({time.time()-t0:.1f}s)")

    rows = []
    for name, s in F.items():
        rows.append((name, auc(s, near), auc(s[visa], near[visa])))
    rows.sort(key=lambda r: -max(r[2], 1 - r[2]))
    print("\n=== single-feature AUC (round 2, sorted by |AUC_vis-0.5|) ===")
    for name, a, av in rows[:30]:
        print(f"{name:22s} all={a:6.3f} vis={av:6.3f}")

    np.savez(os.path.join(SCRATCH, "geom_all.npz"), sel=sel, near=near, visa=visa,
             ncnt=ncnt, vcnt=vcnt, **F)

    print("\n=== Pareto of top 10 singles ===")
    for name, a, av in rows[:10]:
        s = F[name] if av >= 0.5 else -F[name]
        nm = name if av >= 0.5 else "-" + name
        res = sweep(h, P, s)
        print(f"{nm:22s} " + " ".join(f"{f:.1f}:{p:.3f}/{r:.3f}" for f, p, r, _ in res))
    print(f"total {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
