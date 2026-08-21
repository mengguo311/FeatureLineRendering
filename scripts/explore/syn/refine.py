"""Refined search on the winning 'all de-floatered gaussians' pool: richer evidence
terms, weight search, local-rank recall protection, and oracle upper bounds."""
import os, sys, time, itertools, numpy as np, cv2
from scipy.stats import rankdata
from scipy.spatial import cKDTree
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts/explore"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts/explore/syn"))
from tune_lib import Harness, structure_tensor, nms_along_e1
from fastgate import FastGate
from src import visibility

OUT = os.path.expanduser("~/3dgs_line/tier1/scripts/explore/syn")
scene = sys.argv[1] if len(sys.argv) > 1 else "chair"
h = Harness(scene)
X, N, opa = h.X, h.N, h.opa
M = len(X)
E = np.load(os.path.join(OUT, f"evid_all_{scene}.npz"))
vis = E["vis"]; nv = np.maximum(vis.sum(0), 1)
Rk = lambda v: rankdata(v) / len(v)

T = {}
for k in ("sparse", "ridge45"):
    A = np.where(vis, E[k], np.nan)
    with np.errstate(all="ignore"):
        T[f"{k}_mean"] = -np.nan_to_num(np.nanmean(A, 0), nan=1e9)
        T[f"{k}_q75"] = -np.nan_to_num(np.nanpercentile(A, 75, axis=0), nan=1e9)
        T[f"{k}_q90"] = -np.nan_to_num(np.nanpercentile(A, 90, axis=0), nan=1e9)
    for s in (8.0, 16.0):
        T[f"{k}_soft{int(s)}"] = np.where(vis, np.exp(-E[k] / s), 0).sum(0) / nv
    T[f"{k}_fr8"] = (vis & (E[k] <= 8)).sum(0) / nv
never = vis.sum(0) == 0
for k in T: T[k] = np.where(never, np.min(T[k]) - 1, T[k])

tree = cKDTree(X)
dist, knn = tree.query(X, k=33, workers=-1); knn = knn[:, 1:]
nbp = X[knn[:, :32]]; dd = nbp - nbp.mean(1, keepdims=True)
C = np.einsum("nkc,nkd->ncd", dd, dd) / 32
npca = np.linalg.eigh(C)[1][:, :, 0]
npca /= np.linalg.norm(npca, axis=1, keepdims=True) + 1e-12


def st_on(nrm, k):
    nb = knn[:, :k]; nj = nrm[nb]
    sg = np.sign(np.einsum("nkc,nc->nk", nj, nrm)); sg[sg == 0] = 1.0
    nj = nj * sg[..., None]; dn = nj - nj.mean(1, keepdims=True)
    w, V = np.linalg.eigh(np.einsum("nkc,nkd->ncd", dn, dn) / k)
    return w[:, 2], w[:, 2] - w[:, 1]


T["l1_pca16"], T["scr_pca16"] = st_on(npca, 16)
T["l1_pca8"], _ = st_on(npca, 8)
T["opa"] = opa.astype(float)
T["dens"] = -dist[:, 1:33].mean(1)
# robust dihedral (geom's transferable finding): 10th-pct cos to PCA-normal neighbours
nj = npca[knn[:, :20]]
cs = np.abs(np.einsum("nkc,nc->nk", nj, npca))
T["dih20"] = np.degrees(np.arccos(np.clip(np.percentile(cs, 10, axis=1), -1, 1)))

names = list(T)
R = {k: Rk(T[k]) for k in names}
fg = FastGate(h, np.arange(M))
print(f"[{scene}] all={M}, base %.3f/%.3f/%d" % fg(np.ones(M, bool)))

FGRID = np.arange(0.08, 0.75, 0.01)


def best(s, rmin=0.72, grid=FGRID):
    o = np.argsort(-s, kind="stable"); b = None
    for f in grid:
        k = np.zeros(M, bool); k[o[:int(round(f * M))]] = True
        p, r, n = fg(k)
        if r >= rmin and (b is None or p > b[0]): b = (p, r, f, n)
    return b


print("\n=== singles ===")
for k in names:
    b = best(R[k])
    print(f"  {k:16s} " + (f"p={b[0]:.3f} r={b[1]:.3f} f={b[2]:.2f}" if b else "-"))

print("\n=== 2/3-term weighted rank sums (anchor = sparse_mean) ===")
res = []
POOL = ["ridge45_soft16", "ridge45_mean", "ridge45_q90", "sparse_q75", "sparse_soft16",
        "l1_pca16", "scr_pca16", "opa", "dens", "dih20", "l1_pca8", "sparse_fr8",
        "ridge45_fr8", "sparse_q90"]
for a in ["sparse_mean", "sparse_soft16", "sparse_q75"]:
    for b_ in POOL:
        if b_ == a: continue
        for wb in (0.25, 0.5, 0.75, 1.0, 1.5):
            s2 = R[a] + wb * R[b_]
            bb = best(s2)
            if bb: res.append((bb[0], bb[1], bb[2], (a, b_), (1.0, wb)))
            for c in POOL:
                if c in (a, b_): continue
                for wc in (0.25, 0.5):
                    s3 = s2 + wc * R[c]
                    b3 = best(s3, grid=np.arange(0.1, 0.6, 0.02))
                    if b3: res.append((b3[0], b3[1], b3[2], (a, b_, c), (1.0, wb, wc)))
res.sort(key=lambda t: -t[0])
seen = set(); n = 0
for t in res:
    key = tuple(sorted(t[3]))
    if key in seen: continue
    seen.add(key)
    print(f"  p={t[0]:.3f} r={t[1]:.3f} f={t[2]:.2f}  {t[3]} w={t[4]}")
    n += 1
    if n >= 15: break

print("\n=== PURE GEOMETRY (no photographs: ridge45 = rendered G-buffer only) ===")
n = 0
for t in res:
    if any("sparse" in x for x in t[3]): continue
    print(f"  p={t[0]:.3f} r={t[1]:.3f} f={t[2]:.2f}  {t[3]} w={t[4]}")
    n += 1
    if n >= 8: break
resg = []
for a in ["ridge45_soft16", "ridge45_mean", "ridge45_q90"]:
    for b_ in POOL:
        if "sparse" in b_ or b_ == a: continue
        for wb in (0.25, 0.5, 0.75, 1.0, 1.5):
            s2 = R[a] + wb * R[b_]
            bb = best(s2)
            if bb: resg.append((bb[0], bb[1], bb[2], (a, b_), (1.0, wb)))
            for c in POOL:
                if "sparse" in c or c in (a, b_): continue
                for wc in (0.25, 0.5):
                    b3 = best(s2 + wc * R[c], grid=np.arange(0.1, 0.6, 0.02))
                    if b3: resg.append((b3[0], b3[1], b3[2], (a, b_, c), (1.0, wb, wc)))
resg.sort(key=lambda t: -t[0])
seen = set(); n = 0
for t in resg:
    key = tuple(sorted(t[3]))
    if key in seen: continue
    seen.add(key); n += 1
    print(f"  GEOM p={t[0]:.3f} r={t[1]:.3f} f={t[2]:.2f}  {t[3]} w={t[4]}")
    if n >= 10: break

print("\n=== local-rank recall protection on the best combo ===")
sb = R[res[0][3][0]] + res[0][4][1] * R[res[0][3][1]] + (res[0][4][2] * R[res[0][3][2]] if len(res[0][3]) > 2 else 0)
for kk in (8, 16, 32):
    _, nb = tree.query(X, k=kk, workers=-1)
    for lam in (0.25, 0.5, 1.0):
        lr = (sb[nb] < sb[:, None]).sum(1) / kk
        b = best(sb + lam * lr)
        if b: print(f"  knn{kk} lam{lam}: p={b[0]:.3f} r={b[1]:.3f} f={b[2]:.2f} n={b[3]}")
