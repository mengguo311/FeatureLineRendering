"""Round 5: denoised-normal C_N features + honest blocked-CV ceiling Pareto."""
import os
import sys
import time
import numpy as np

sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tune_lib import Harness, structure_tensor, nms_along_e1
from explore_geom import auc, labels, sweep, SCRATCH
from _geom_feats3 import compute_denoised

Zo = np.load(os.path.join(SCRATCH, "geom_all.npz"))
META = {"sel", "near", "visa", "ncnt", "vcnt"}


def zr(x):
    return (np.argsort(np.argsort(x)) + 0.5) / len(x)


def main():
    t0 = time.time()
    h = Harness("chair")
    st = structure_tensor(h.X, h.N, 8)
    cand = np.where(st["s_crease"] > 0.05)[0]
    sel = nms_along_e1(h.X, cand, st["s_crease"], st["e1"], st["knn"])
    P = h.X[sel]
    near, visa = Zo["near"], Zo["visa"]
    assert np.array_equal(sel, Zo["sel"])

    F3 = compute_denoised(h, st)
    print(f"denoised feats {len(F3)}  ({time.time()-t0:.1f}s)")
    rows = [(n, auc(v[sel], near), auc(v[sel][visa], near[visa])) for n, v in F3.items()]
    rows.sort(key=lambda r: -max(r[2], 1 - r[2]))
    print("\n=== denoised-normal features, AUC ===")
    for n, a, av in rows:
        print(f"{n:22s} all={a:6.3f} vis={av:6.3f}")

    print("\n=== Pareto of the top 6 ===")
    for n, a, av in rows[:6]:
        s = F3[n][sel] if av >= 0.5 else -F3[n][sel]
        res = sweep(h, P, s)
        print(f"{('' if av>=0.5 else '-')+n:24s} " +
              " ".join(f"{f:.1f}:{p:.3f}/{r:.3f}" for f, p, r, _ in res))

    np.savez(os.path.join(SCRATCH, "geom_denoise.npz"),
             **{k: np.asarray(v, float)[sel] for k, v in F3.items()})
    print(f"total {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
