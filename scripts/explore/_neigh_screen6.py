"""EVAL-SIDE screen 6: POSITIONAL neighbourhood structure — local PCA (linearity /
planarity), local intrinsic dimension, surface density, and tangent-filament alignment."""
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
sel, lab, vis = Z["sel"], Z["label"], Z["vis_any"]
EPS = 1e-12
FS = [1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2]


def auc(s, y):
    r = rankdata(np.asarray(s, float))
    n1 = int(y.sum()); n0 = len(y) - n1
    return float((r[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def rep(n, s):
    print(f"{n:34s} AUC_all={auc(s, lab):.4f}  AUC_vis={auc(s[vis], lab[vis]):.4f}")


h = Harness("chair")
X, Nrm = h.X, h.N
P = X[sel]
M = len(sel)
treeX = cKDTree(X)
dk, knnB = treeX.query(X, k=193, workers=8)
dk, knnB = dk[:, 1:], knnB[:, 1:]
sp = 0.00625

print("=== positional local PCA ===")
PCA = {}
for k in [8, 16, 32, 64, 128, 192]:
    nb = knnB[:, :k]
    d = X[nb] - X[:, None]
    C = np.einsum("nkc,nkd->ncd", d, d) / k
    w, V = np.linalg.eigh(C)
    l1, l2, l3 = w[:, 2], w[:, 1], w[:, 0]
    s1 = np.sqrt(np.clip(l1, 0, None)) + EPS
    lin = (l1 - l2) / (l1 + EPS)
    pla = (l2 - l3) / (l1 + EPS)
    sca = l3 / (l1 + EPS)
    PCA[k] = (V[:, :, 2], lin, pla, sca, s1)
    rep(f"pos_linearity_k{k}", lin[sel])
    rep(f"pos_planarity_k{k}", pla[sel])
    rep(f"-pos_scatter_k{k}", -sca[sel])
    rep(f"+pos_scatter_k{k}", sca[sel])
    rep(f"-pos_extent_k{k}", -s1[sel])
    rep(f"-thickness_k{k}(sqrt l3)", -np.sqrt(np.clip(l3, 0, None))[sel])

print("\n=== filament / tangent alignment ===")
for k in [8, 16, 32, 64, 128]:
    v1 = PCA[k][0]
    for ke in [8, 16, 32, 48]:
        al = np.abs(np.einsum("nc,nc->n", v1, Z[f"e3_{ke}"]))
        rep(f"|v1_k{k} . e3_k{ke}|", al[sel])
        break

print("\n=== local intrinsic dimension (count ratio) ===")
for r0 in [3, 5, 8]:
    c1 = np.asarray(treeX.query_ball_point(X, r0 * sp, return_length=True), float)
    c2 = np.asarray(treeX.query_ball_point(X, 2 * r0 * sp, return_length=True), float)
    dimd = np.log(np.clip(c2, 1, None) / np.clip(c1, 1, None)) / np.log(2.0)
    rep(f"-locdim_r{r0}->{2*r0}", -dimd[sel])
    rep(f"+locdim_r{r0}->{2*r0}", dimd[sel])
    rep(f"surfdens_r{r0} (c1/r^2)", c1)

print("\n=== best density variants (recap / refine) ===")
DENS = {}
for k in [32, 96, 192]:
    DENS[k] = -dk[:, k - 1]
    rep(f"-radius_k{k}", DENS[k][sel])
for k in [32, 96]:
    # density normalised by the LOCAL SURFACE extent (scale-free-ish)
    rep(f"knnrad_ratio_k{k}/k192", -(dk[:, k - 1] / (dk[:, 191] + EPS))[sel])


def pareto(name, score):
    order = np.argsort(-score)
    print(f"\n--- {name} (AUC_all={auc(score, lab):.4f}) ---")
    for f in FS:
        keep = np.zeros(M, bool)
        keep[order[:int(round(f * M))]] = True
        p, r, n = h.evaluate(P, extra_mask=keep)
        flag = "  <== GATE PASS" if (p >= 0.80 and r >= 0.70) else ""
        print(f"  f={f:.1f}  prec={p:.4f}  rec={r:.4f}  nvis={n}{flag}")


def rk(v):
    return rankdata(v) / len(v)


# pick the two strongest positional features for a Pareto
cands = {}
for k in [32, 128]:
    cands[f"-thickness_k{k}"] = -np.sqrt(np.clip(
        np.linalg.eigvalsh(np.einsum("nkc,nkd->ncd", X[knnB[:, :k]] - X[:, None],
                                     X[knnB[:, :k]] - X[:, None]) / k)[:, 0], 0, None))[sel]
cands["dens_k96"] = DENS[96][sel]
for nm, s in cands.items():
    pareto(nm, s)

print("\n############ combos of positional + density + dihedral ############")
