"""EVAL-SIDE screen 5: oracle Pareto sanity-check + LOCALLY-COMPETITIVE scores
(rank / max-ratio within a spatial neighbourhood), which is what recall needs."""
import os
import sys
import numpy as np
from scipy.stats import rankdata
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
from tune_lib import Harness, structure_tensor

SCRATCH = "/tmp/claude-1026/-home-u00134-3dgs-line/4ee6144a-2815-4286-bec9-0a63623a57f6/scratchpad"
Z = np.load(os.path.join(SCRATCH, "neigh_cache.npz"))
sel, lab, vis, dmin = Z["sel"], Z["label"], Z["vis_any"], Z["dmin"]
EPS = 1e-12
FS = [1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2]


def auc(s, y):
    r = rankdata(np.asarray(s, float))
    n1 = int(y.sum()); n0 = len(y) - n1
    return float((r[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


h = Harness("chair")
X, Nrm = h.X, h.N
P = X[sel]
M = len(sel)
treeX = cKDTree(X)
treeP = cKDTree(P)
dk, knnB = treeX.query(X, k=193, workers=8)
dk, knnB = dk[:, 1:], knnB[:, 1:]
sp = 0.00625


def pareto(name, score):
    order = np.argsort(-score)
    print(f"\n--- {name} (AUC_all={auc(score, lab):.4f}) ---")
    out = []
    for f in FS:
        keep = np.zeros(M, bool)
        keep[order[:int(round(f * M))]] = True
        p, r, n = h.evaluate(P, extra_mask=keep)
        flag = "  <== GATE PASS" if (p >= 0.80 and r >= 0.70) else ""
        print(f"  f={f:.1f}  prec={p:.4f}  rec={r:.4f}  nvis={n}{flag}")
        out.append((f, p, r))
    return out


# ---- sanity: oracle ranking reproduces the stated upper bound? ----
oracle = -np.where(np.isfinite(dmin), dmin, 1e6)
pareto("ORACLE (-true crease dist)  [sanity check]", oracle)


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
dih48 = two_plane(48)
DENS = -dk[:, 95]

# ---- locally-competitive transforms over the SEED pool ----
_, knnP = treeP.query(P, k=65, workers=8)
knnP = knnP[:, 1:]


def local_rank(v, kk):
    """fraction of the kk nearest SEEDS with a strictly lower value"""
    nb = knnP[:, :kk]
    return (v[nb] < v[:, None]).mean(1)


def local_ratio(v, kk):
    nb = knnP[:, :kk]
    return v / (v[nb].max(1) + EPS)


BASE = {"dih192": dih192[sel], "dih48": dih48[sel], "sc8": Z["sc8"][sel],
        "sc32": Z["sc32"][sel], "dens": DENS[sel]}
print("\n=== locally-competitive AUC ===")
for bn, bv in BASE.items():
    for kk in [8, 16, 32, 64]:
        lr = local_rank(bv, kk)
        print(f"lrank[{bn}]_k{kk:<3d} AUC_all={auc(lr, lab):.4f}  "
              f"AUC_vis={auc(lr[vis], lab[vis]):.4f}")

print("\n=== spatial-cluster-stratified AUC (200 kmeans-ish spatial bins) ===")
rng = np.random.default_rng(0)
cent = P[rng.choice(M, 200, replace=False)]
_, cl = cKDTree(cent).query(P, k=1)
for bn, bv in BASE.items():
    aa, ww = [], []
    for c in range(200):
        m = cl == c
        if lab[m].sum() < 10 or (~lab[m]).sum() < 10:
            continue
        aa.append(auc(bv[m], lab[m])); ww.append(m.sum())
    print(f"{bn:8s} within-cluster AUC = {np.average(aa, weights=ww):.4f} "
          f"({len(aa)} clusters used)")

print("\n\n############ PARETO of locally-competitive scores ############")
for bn in ["dih192", "sc8"]:
    for kk in [16, 32]:
        pareto(f"lrank[{bn}]_k{kk}", local_rank(BASE[bn], kk))


def rk(v):
    return rankdata(v) / len(v)


print("\n############ hybrid: global density x local competition ############")
hy = {
    "0.5*rk(dens)+0.5*lrank[dih192]_32":
        0.5 * rk(BASE["dens"]) + 0.5 * local_rank(BASE["dih192"], 32),
    "rk(dens)+lrank[dih192]_32+rk(dih192)":
        rk(BASE["dens"]) + local_rank(BASE["dih192"], 32) + rk(BASE["dih192"]),
}
for nm, s in hy.items():
    pareto(nm, s)
