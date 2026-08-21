"""EVAL-SIDE screen 8: RANDOM-KEEP control (how much recall does an uninformative score
cost?), saliency-contrast features, wider smoothing, and a wide gate-objective search."""
import os
import sys
import time
import itertools
import numpy as np
from scipy.stats import rankdata
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts/explore"))
from tune_lib import structure_tensor
from _neigh_lite import LiteHarness

SCRATCH = "/tmp/claude-1026/-home-u00134-3dgs-line/4ee6144a-2815-4286-bec9-0a63623a57f6/scratchpad"
Z = np.load(os.path.join(SCRATCH, "neigh_cache.npz"))
sel, lab, vis, dmin = Z["sel"], Z["label"], Z["vis_any"], Z["dmin"]
EPS = 1e-12
FS = [1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2]


def auc(s, y):
    r = rankdata(np.asarray(s, float))
    n1 = int(y.sum()); n0 = len(y) - n1
    return float((r[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


h = LiteHarness("chair")
X, Nrm = h.X, h.N
P = X[sel]
M = len(sel)
treeX = cKDTree(X)
dk, knnB = treeX.query(X, k=385, workers=8)
dk, knnB = dk[:, 1:], knnB[:, 1:]


def rk(v):
    return rankdata(v) / len(v)


def pareto(name, score, show=True):
    order = np.argsort(-score)
    rows = []
    for f in FS:
        keep = np.zeros(M, bool)
        keep[order[:int(round(f * M))]] = True
        p, r, n = h.evaluate(P, extra_mask=keep)
        rows.append((f, p, r, n))
    if show:
        print(f"\n--- {name} (AUC_all={auc(score, lab):.4f}) ---")
        for f, p, r, n in rows:
            fl = "  <== GATE PASS" if (p >= 0.80 and r >= 0.70) else ""
            print(f"  f={f:.2f}  prec={p:.4f}  rec={r:.4f}  nvis={n}{fl}")
    return rows

print("=== RANDOM-KEEP CONTROL (mean of 5 seeds): the recall cost of NO information ===")
rng = np.random.default_rng(0)
acc = {f: [] for f in FS}
for s in range(5):
    rr = rng.random(M)
    for f, p, r, n in pareto("rand", rr, show=False):
        acc[f].append((p, r))
for f in FS:
    a = np.array(acc[f])
    print(f"  f={f:.2f}  prec={a[:,0].mean():.4f}  rec={a[:,1].mean():.4f}")

print("\n=== ORACLE upper bound (sanity) ===")
pareto("ORACLE -dmin", -np.where(np.isfinite(dmin), dmin, 1e6))


def two_plane(k):
    nb = knnB[:, :k]
    nj = Nrm[nb]
    sg = np.sign(np.einsum("nkc,nc->nk", nj, Nrm)); sg[sg == 0] = 1.0
    nj = nj * sg[..., None]
    st = structure_tensor(X, Nrm, k, knn=nb)
    a = np.einsum("nkc,nc->nk", nj - nj.mean(1, keepdims=True), st["e1"])
    A = a > 0
    ok = (A.sum(1) >= 2) & ((~A).sum(1) >= 2)

    def gm(m, arr):
        w = m[..., None].astype(np.float64)
        return (arr * w).sum(1) / np.clip(w.sum(1), 1, None)
    nA, nB_ = gm(A, nj), gm(~A, nj)
    nA /= np.linalg.norm(nA, axis=1, keepdims=True) + EPS
    nB_ /= np.linalg.norm(nB_, axis=1, keepdims=True) + EPS
    g = np.clip(np.einsum("nc,nc->n", nA, nB_), -0.9999, 0.9999)
    d = np.degrees(np.arccos(np.abs(g))); d[~ok] = 0.0
    return d


dih192 = two_plane(192)
print("\n=== saliency CONTRAST (point value minus regional mean) ===")
for base, bn in [(Z["sc8"], "sc8"), (dih192, "dih192")]:
    for ks in [32, 96, 192, 384]:
        sm = base[knnB[:, :ks]].mean(1)
        print(f"contrast[{bn}]_k{ks:<4d} AUC={auc((base - sm)[sel], lab):.4f}   "
              f"smooth AUC={auc(sm[sel], lab):.4f}")

print("\n=== density at wider k ===")
for k in [96, 192, 288, 384]:
    print(f"-radius_k{k:<4d} AUC={auc(-dk[:, k-1][sel], lab):.4f}")

# ---------- feature bank + wide search ----------
dens = rk(-dk[:, 95][sel])
dens192 = rk(-dk[:, 191][sel])
dih = rk(dih192[sel])
smdih = rk(dih192[knnB[:, :192]].mean(1)[sel])
smdih384 = rk(dih192[knnB[:, :384]].mean(1)[sel])
k = 192
dd = X[knnB[:, :k]] - X[:, None]
wv = np.linalg.eigvalsh(np.einsum("nkc,nkd->ncd", dd, dd) / k)
scat = rk((wv[:, 0] / (wv[:, 2] + EPS))[sel])
sc8 = rk(Z["sc8"][sel])
minr = rk(np.stack([rankdata(Z[f"sc{kk}"])[sel] for kk in [6, 8, 12, 16, 24, 32, 48]]).min(0))
FEAT = {"dens96": dens, "dens192": dens192, "dih192": dih, "smdih192": smdih,
        "smdih384": smdih384, "scat192": scat, "sc8": sc8, "minrank": minr}
print("\nfeature bank:")
for n, v in FEAT.items():
    print(f"  {n:10s} AUC_all={auc(v, lab):.4f} AUC_vis={auc(v[vis], lab[vis]):.4f}")

FSW = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2]


def gate_obj(score):
    order = np.argsort(-score)
    best = (0.0, None)
    for f in FSW:
        keep = np.zeros(M, bool)
        keep[order[:int(round(f * M))]] = True
        p, r, _ = h.evaluate(P, extra_mask=keep)
        if r >= 0.70 and p > best[0]:
            best = (p, (f, p, r))
    return best


names = list(FEAT)
grid = [0.0, 0.5, 1.0]
res = []
t0 = time.time()
for ws in itertools.product(grid, repeat=len(names)):
    if sum(ws) == 0 or sum(ws) > 2.5:
        continue
    s = np.zeros(M)
    for n, w in zip(names, ws):
        if w:
            s = s + w * FEAT[n]
    o, det = gate_obj(s)
    res.append((o, ws, det))
res.sort(key=lambda x: -x[0])
print(f"\n=== wide search: {len(res)} combos in {time.time()-t0:.0f}s ===")
for o, ws, det in res[:6]:
    print(f"prec@rec>=0.70 = {o:.4f}  at f={det[0]} rec={det[2]:.4f}  "
          f"w={ {n: w for n, w in zip(names, ws) if w} }")
BEST = res[0][1]
sbest = np.zeros(M)
for n, w in zip(names, BEST):
    if w:
        sbest = sbest + w * FEAT[n]
pareto("BEST COMBO", sbest)
np.save(os.path.join(SCRATCH, "best_weights.npy"),
        np.array([[names.index(n), w] for n, w in zip(names, BEST) if w]))
print("BEST weights:", {n: w for n, w in zip(names, BEST) if w})
pareto("dens96 alone", FEAT["dens96"])
