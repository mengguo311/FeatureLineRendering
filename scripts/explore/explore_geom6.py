"""Round 6: merge all geom features -> honest blocked-CV ceiling (AUC + Pareto) and a
greedy mesh-free equal-weight rank combination."""
import os
import sys
import numpy as np
import torch

sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tune_lib import Harness, structure_tensor, nms_along_e1
from explore_geom import auc, sweep, SCRATCH
from explore_geom4 import fit_predict

Z1 = np.load(os.path.join(SCRATCH, "geom_all.npz"))
Z2 = np.load(os.path.join(SCRATCH, "geom_denoise.npz"))
META = {"sel", "near", "visa", "ncnt", "vcnt"}
near, visa, sel = Z1["near"], Z1["visa"], Z1["sel"]
F = {k: Z1[k] for k in Z1.files if k not in META}
F.update({k: Z2[k] for k in Z2.files})
NAMES = sorted(F)


def zr(x):
    return (np.argsort(np.argsort(x)) + 0.5) / len(x)


def main():
    h = Harness("chair")
    st = structure_tensor(h.X, h.N, 8)
    P = h.X[sel]
    Pv = P[visa]
    print(f"nfeat={len(NAMES)} vis={visa.sum()} pos={near[visa].sum()}")

    # orient every feature so AUC_vis >= 0.5
    sgn = {}
    R = {}
    for n in NAMES:
        a = auc(F[n][visa], near[visa])
        sgn[n] = 1.0 if a >= 0.5 else -1.0
        R[n] = zr(sgn[n] * F[n])

    M = np.stack([(R[n] - 0.5) * 3.464 for n in NAMES], 1)
    Mv, yv = M[visa], near[visa].astype(float)
    rng = np.random.default_rng(0)
    q = np.floor((Pv - Pv.min(0)) / (Pv.ptp(0) + 1e-9) * 5).astype(int).clip(0, 4)
    cell = q[:, 0] * 25 + q[:, 1] * 5 + q[:, 2]
    blk = rng.permutation(125)[cell] % 5

    oof = np.zeros(len(yv))
    for f in range(5):
        te = blk == f
        p, _ = fit_predict(Mv[~te], yv[~te], Mv[te], hidden=0)
        oof[te] = p
    print(f"\nlogreg spatial-blockCV AUC over ALL {len(NAMES)} geom feats = "
          f"{auc(oof, yv):.3f}")
    full = np.zeros(len(sel))
    full[visa] = oof
    full[~visa] = -1e9  # invisible seeds get no CV prediction; park them last
    res = sweep(h, P, full)
    print("  blockCV-logreg Pareto (HONEST ceiling, still oracle-supervised): " +
          " ".join(f"{f:.1f}:{p:.3f}/{r:.3f}" for f, p, r, _ in res))

    # ---------------- greedy equal-weight rank combination ----------------
    print("\n=== greedy forward selection (equal-weight z-rank sum) ===")
    chosen, cur = [], np.zeros(len(sel))
    best_hist = []
    for step in range(8):
        bn, ba = None, -1
        for n in NAMES:
            if n in chosen:
                continue
            a = auc((cur + R[n])[visa], near[visa])
            if a > ba:
                bn, ba = n, a
        chosen.append(bn)
        cur = cur + R[bn]
        res = sweep(h, P, cur)
        best_hist.append((list(chosen), ba, res))
        print(f"  +{bn:22s} AUCvis={ba:.3f}  " +
              " ".join(f"{f:.1f}:{p:.3f}/{r:.3f}" for f, p, r, _ in res))

    np.save(os.path.join(SCRATCH, "greedy_chosen.npy"),
            np.array([(n, sgn[n]) for n in chosen], dtype=object), allow_pickle=True)
    print("\nchosen with signs:", [(n, sgn[n]) for n in chosen])


if __name__ == "__main__":
    main()
