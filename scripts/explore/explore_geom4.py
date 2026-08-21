"""Round 4: supervised CEILING of the geom family (analysis only; oracle-fit models are
NOT proposable scores) + per-feature pos/neg separation table.

Two CV schemes:
  * random 5-fold  (optimistic; density/opacity features leak spatially)
  * spatially-blocked 5-fold (honest: contiguous 3D blocks held out)
"""
import os
import sys
import numpy as np
import torch

sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tune_lib import Harness, structure_tensor, nms_along_e1
from explore_geom import auc, sweep, SCRATCH

Z = np.load(os.path.join(SCRATCH, "geom_all.npz"))
META = {"sel", "near", "visa", "ncnt", "vcnt"}
NAMES = [k for k in Z.files if k not in META]
near, visa, sel = Z["near"], Z["visa"], Z["sel"]
dev = "cuda" if torch.cuda.is_available() else "cpu"


def zr(x):
    return (np.argsort(np.argsort(x)) + 0.5) / len(x)


def fit_predict(Xtr, ytr, Xte, hidden=0, epochs=400, wd=1e-3, lr=0.05, seed=0):
    torch.manual_seed(seed)
    xt = torch.tensor(Xtr, dtype=torch.float32, device=dev)
    yt = torch.tensor(ytr, dtype=torch.float32, device=dev)
    xe = torch.tensor(Xte, dtype=torch.float32, device=dev)
    d = xt.shape[1]
    if hidden:
        m = torch.nn.Sequential(torch.nn.Linear(d, hidden), torch.nn.ReLU(),
                                torch.nn.Linear(hidden, hidden), torch.nn.ReLU(),
                                torch.nn.Linear(hidden, 1)).to(dev)
    else:
        m = torch.nn.Linear(d, 1).to(dev)
    opt = torch.optim.Adam(m.parameters(), lr=lr, weight_decay=wd)
    lo = torch.nn.BCEWithLogitsLoss()
    for _ in range(epochs):
        opt.zero_grad()
        l = lo(m(xt).squeeze(1), yt)
        l.backward()
        opt.step()
    with torch.no_grad():
        p = m(xe).squeeze(1).cpu().numpy()
    w = None if hidden else m[0].weight.detach().cpu().numpy()[0] if isinstance(
        m, torch.nn.Sequential) else m.weight.detach().cpu().numpy()[0]
    return p, w


def cv_auc(X, y, folds, hidden=0):
    pred = np.zeros(len(y))
    for f in np.unique(folds):
        te = folds == f
        p, _ = fit_predict(X[~te], y[~te], X[te], hidden=hidden)
        pred[te] = p
    return auc(pred, y), pred


def main():
    h = Harness("chair")
    st = structure_tensor(h.X, h.N, 8)
    P = h.X[sel]
    Pv = P[visa]

    M = np.stack([zr(Z[n]) for n in NAMES], 1)
    M = (M - 0.5) * 3.464
    Mv, yv = M[visa], near[visa].astype(float)

    rng = np.random.default_rng(0)
    rand_folds = rng.integers(0, 5, len(yv))
    # spatially blocked folds: 5x5x5 grid cells assigned round-robin to 5 folds
    q = np.floor((Pv - Pv.min(0)) / (Pv.ptp(0) + 1e-9) * 5).astype(int).clip(0, 4)
    cell = q[:, 0] * 25 + q[:, 1] * 5 + q[:, 2]
    perm = rng.permutation(125)
    blk_folds = perm[cell] % 5

    print(f"vis seeds={len(yv)} pos rate={yv.mean():.3f} nfeat={len(NAMES)}")
    for hid, tag in [(0, "logreg"), (64, "MLP-64x2")]:
        a1, _ = cv_auc(Mv, yv, rand_folds, hidden=hid)
        a2, p2 = cv_auc(Mv, yv, blk_folds, hidden=hid)
        print(f"  {tag:10s} randomCV AUC={a1:.3f}   spatial-blockCV AUC={a2:.3f}")
        if hid == 0:
            _, w = fit_predict(Mv, yv, Mv[:1], hidden=0)
            o = np.argsort(-np.abs(w))[:12]
            print("     top |coef|:", ", ".join(f"{NAMES[i]}({w[i]:+.2f})" for i in o))

    # Pareto of the in-sample oracle-fit MLP = optimistic family ceiling
    p_all, _ = fit_predict(Mv, yv, M, hidden=64)
    res = sweep(h, P, p_all)
    print("\nORACLE-FIT MLP (in-sample, upper bound, NOT usable): " +
          " ".join(f"{f:.1f}:{p:.3f}/{r:.3f}" for f, p, r, _ in res))

    # per-feature pos/neg medians for the top separators
    print("\n=== pos/neg medians (visible seeds) ===")
    rows = [(n, auc(Z[n][visa], near[visa])) for n in NAMES]
    rows.sort(key=lambda r: -abs(r[1] - 0.5))
    for n, a in rows[:12]:
        x = Z[n][visa]
        print(f"{n:22s} AUC={a:.3f}  pos_med={np.median(x[yv>0]):+.4g} "
              f"neg_med={np.median(x[yv==0]):+.4g}")

    # anisotropy hypothesis, explicitly
    print("\n=== ANISOTROPY HYPOTHESIS check ===")
    for n in ["flat_mid_min", "flat_max_min", "iso", "discness", "log_flat",
              "nb_flat_mean", "n_pca_agree", "scale_min"]:
        x = Z[n][visa]
        print(f"{n:16s} AUC={auc(x, yv>0):.3f}  pos_med={np.median(x[yv>0]):+.4g} "
              f"neg_med={np.median(x[yv==0]):+.4g}")


if __name__ == "__main__":
    main()
