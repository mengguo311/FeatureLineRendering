"""Oracle-supervised ceiling over the UNION of all six families' features, with
spatially-blocked CV so smooth regional features cannot leak.  EVAL-SIDE ONLY:
this tells us what the best possible mesh-free ranker from these signals can do.
"""
import os, sys, numpy as np
from scipy.stats import rankdata
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts/explore/syn"))
from cache_scores import build
from fastgate import FastGate
import torch

OUT = os.path.expanduser("~/3dgs_line/tier1/scripts/explore/syn")
h, st, sel = build("chair")
fg = FastGate(h, sel); M = len(sel)
z = dict(np.load(os.path.join(OUT, "scores_chair.npz")))
sa = dict(np.load(os.path.join(OUT, "sharpaggs_chair.npz")))
pos, visany = z["lab_pos"], z["lab_vis"]

feats, names = [], []
for src in (z, sa):
    for k, v in src.items():
        if k.startswith(("lab_", "sel")): continue
        v = np.asarray(v, np.float64)
        if v.shape != (M,) or not np.isfinite(v).any(): continue
        feats.append(rankdata(np.nan_to_num(v, nan=-1e9, posinf=1e9, neginf=-1e9)) / M)
        names.append(k)
F = np.stack(feats, 1)
print("features", F.shape)

X = h.X[sel]
# spatial blocks: 8x8x8 grid of contiguous 3D cells -> 5 folds by block id
q = np.floor((X - X.min(0)) / (X.max(0) - X.min(0) + 1e-9) * 8).clip(0, 7).astype(int)
blk = q[:, 0] * 64 + q[:, 1] * 8 + q[:, 2]
ub = np.unique(blk)
rng = np.random.RandomState(0); rng.shuffle(ub)
fold = np.zeros(M, int)
for i, b in enumerate(ub): fold[blk == b] = i % 5

y = pos.astype(np.float32)
dev = "cuda" if torch.cuda.is_available() else "cpu"
Ft = torch.tensor((F - F.mean(0)) / (F.std(0) + 1e-9), dtype=torch.float32, device=dev)
yt = torch.tensor(y, device=dev)


def fit(tr, te, epochs=800, hid=0):
    torch.manual_seed(0)
    if hid:
        m = torch.nn.Sequential(torch.nn.Linear(F.shape[1], hid), torch.nn.ReLU(),
                                torch.nn.Linear(hid, hid), torch.nn.ReLU(),
                                torch.nn.Linear(hid, 1)).to(dev)
    else:
        m = torch.nn.Linear(F.shape[1], 1).to(dev)
    opt = torch.optim.Adam(m.parameters(), lr=0.05 if not hid else 0.01, weight_decay=1e-4)
    lf = torch.nn.BCEWithLogitsLoss()
    tri = torch.tensor(tr, device=dev)
    for _ in range(epochs):
        opt.zero_grad(); l = lf(m(Ft[tri])[:, 0], yt[tri]); l.backward(); opt.step()
    with torch.no_grad():
        return m(Ft)[:, 0].cpu().numpy()


def auc(s, m=None):
    yy = pos if m is None else pos[m]
    ss = s if m is None else s[m]
    r = rankdata(ss); n1 = yy.sum(); n0 = len(yy) - n1
    return (r[yy].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


for hid in (0, 64):
    oof = np.zeros(M)
    for k in range(5):
        tr = np.where(fold != k)[0]; te = np.where(fold == k)[0]
        p = fit(tr, te, hid=hid)
        oof[te] = rankdata(p[te]) / len(te)      # per-fold rank -> comparable
    tag = "logreg" if not hid else "mlp64"
    print(f"\n{tag}: blocked-CV AUC(vis) = {auc(oof, visany):.3f}")
    o = np.argsort(-oof, kind="stable"); best = None
    for f in np.arange(0.15, 0.85, 0.01):
        kk = np.zeros(M, bool); kk[o[:int(round(f * M))]] = True
        p_, r_, n_ = fg(kk)
        if r_ >= 0.72 and (best is None or p_ > best[0]): best = (p_, r_, f)
    print(f"  best @rec>=0.72: p={best[0]:.3f} r={best[1]:.3f} f={best[2]:.2f}")
    for f in (0.6, 0.5, 0.4, 0.3, 0.2):
        kk = np.zeros(M, bool); kk[o[:int(round(f * M))]] = True
        print(f"    f={f}: %.3f/%.3f" % fg(kk)[:2])

# in-sample (memorisation) reference
p = fit(np.arange(M), None, hid=64)
o = np.argsort(-p, kind="stable")
print("\nIN-SAMPLE mlp64 (memorisation, NOT achievable):", "AUC %.3f" % auc(p, visany))
for f in (0.5, 0.4, 0.3, 0.2):
    kk = np.zeros(M, bool); kk[o[:int(round(f * M))]] = True
    print(f"    f={f}: %.3f/%.3f" % fg(kk)[:2])
