"""EVAL-SIDE screen 2: two-plane crease fit (dihedral + offset) and curve/chain support."""
import os
import sys
import time
import numpy as np
from scipy.stats import rankdata
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
from tune_lib import Harness

SCRATCH = "/tmp/claude-1026/-home-u00134-3dgs-line/4ee6144a-2815-4286-bec9-0a63623a57f6/scratchpad"
KS = [6, 8, 12, 16, 24, 32, 48]
Z = np.load(os.path.join(SCRATCH, "neigh_cache.npz"))
sel = Z["sel"]
lab = Z["label"]
vis = Z["vis_any"]
knn_full = Z["knn_full"]
EPS = 1e-12


def auc(s, y):
    r = rankdata(np.asarray(s, float))
    n1 = int(y.sum()); n0 = len(y) - n1
    return float((r[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def rep(name, s):
    print(f"{name:36s} AUC_all={auc(s, lab):.4f}  AUC_vis={auc(s[vis], lab[vis]):.4f}")


h = Harness("chair")
X, Nrm = h.X, h.N
P = X[sel]

# ---------- diagnostics: are negatives a "halo" around positives? ----------
tp = cKDTree(P[lab])
d_to_pos, _ = tp.query(P, k=1)
tn = cKDTree(P[~lab])
med_spacing = np.median(np.linalg.norm(X[knn_full[:, 0]] - X, axis=1))
print(f"median 1-NN gaussian spacing = {med_spacing:.5f}")
print("dist(seed -> nearest POSITIVE seed) / spacing:")
for q in [10, 25, 50, 75, 90]:
    print(f"  neg p{q}={np.percentile(d_to_pos[~lab], q)/med_spacing:6.2f}   "
          f"pos p{q}={np.percentile(d_to_pos[lab], q)/med_spacing:6.2f}")
print("dmin(px) percentiles for visible seeds:",
      np.round(np.percentile(Z['dmin'][vis], [10, 25, 50, 75, 90]), 2))


# ---------- two-plane crease fit ----------
def two_plane(k):
    nb = knn_full[:, :k]
    nj = Nrm[nb]
    sgn = np.sign(np.einsum("nkc,nc->nk", nj, Nrm)); sgn[sgn == 0] = 1.0
    nj = nj * sgn[..., None]
    nbar = nj.mean(1, keepdims=True)
    dnj = nj - nbar
    # e1 at this scale (across-crease normal-variation direction)
    e1 = Z[f"e1_{k}"]
    a = np.einsum("nkc,nc->nk", dnj, e1)          # [N,k] signed normal deviation
    A = a > 0
    B = ~A
    cntA, cntB = A.sum(1), B.sum(1)
    ok = (cntA >= 2) & (cntB >= 2)

    def grpmean(mask, arr):
        w = mask[..., None].astype(np.float64)
        return (arr * w).sum(1) / np.clip(w.sum(1), 1, None)

    xj = X[nb]
    nA = grpmean(A, nj); nB_ = grpmean(B, nj)
    nA /= np.linalg.norm(nA, axis=1, keepdims=True) + EPS
    nB_ /= np.linalg.norm(nB_, axis=1, keepdims=True) + EPS
    pA = grpmean(A, xj); pB = grpmean(B, xj)

    g = np.clip(np.einsum("nc,nc->n", nA, nB_), -0.9999, 0.9999)
    dihedral = np.degrees(np.arccos(np.abs(g)))    # unoriented dihedral deviation
    rA = np.einsum("nc,nc->n", nA, pA - X)
    rB = np.einsum("nc,nc->n", nB_, pB - X)
    det = 1.0 - g * g
    al = (rA - g * rB) / det
    be = (rB - g * rA) / det
    dist = np.sqrt(np.clip(al * al + be * be + 2 * al * be * g, 0, None))
    rad = np.linalg.norm(xj - X[:, None], axis=2).mean(1) + EPS
    dist_n = dist / rad
    # plane-fit residual (how well do 2 planes explain the patch)
    resA = np.abs(np.einsum("nkc,nc->nk", xj - pA[:, None], nA))
    resB = np.abs(np.einsum("nkc,nc->nk", xj - pB[:, None], nB_))
    res = np.where(A, resA, resB)
    rms = np.sqrt((res ** 2).mean(1)) / rad
    dihedral[~ok] = 0.0
    dist_n[~ok] = 1e3
    return dihedral, dist_n, rms, ok, rad


print("\n=== two-plane crease fit ===")
TP = {}
for k in [8, 12, 16, 24, 32, 48]:
    t = time.time()
    dih, dn, rms, ok, rad = two_plane(k)
    TP[k] = (dih, dn, rms, rad)
    rep(f"dihedral_k{k}", dih[sel])
    rep(f"-lineoffset_k{k}", -dn[sel])
    rep(f"-planeRMS_k{k}", -rms[sel])
    print(f"    ({time.time()-t:.1f}s)")

print("\n=== multi-scale two-plane ===")
for S in [[8, 12, 16], [12, 16, 24], [16, 24, 32], [8, 16, 32], [12, 24, 48], [8, 12, 16, 24, 32, 48]]:
    tag = "-".join(map(str, S))
    D = np.stack([TP[k][0][sel] for k in S])
    O = np.stack([TP[k][1][sel] for k in S])
    rep(f"min_dihedral[{tag}]", D.min(0))
    rep(f"med_dihedral[{tag}]", np.median(D, 0))
    rep(f"-max_offset[{tag}]", -O.max(0))
    rep(f"-med_offset[{tag}]", -np.median(O, 0))


# ---------- curve / chain support ----------
def chain_scores(t_vec, radius_mult, cos_thr, cos_align):
    r = radius_mult * med_spacing
    tree = cKDTree(P)
    pairs = np.array(list(tree.query_pairs(r)), dtype=np.int64)
    if len(pairs) == 0:
        return None
    i, j = pairs[:, 0], pairs[:, 1]
    d = P[j] - P[i]
    dn = np.linalg.norm(d, axis=1) + EPS
    dh = d / dn[:, None]
    tt = np.abs(np.einsum("mc,mc->m", t_vec[i], t_vec[j]))
    ai = np.abs(np.einsum("mc,mc->m", dh, t_vec[i]))
    aj = np.abs(np.einsum("mc,mc->m", dh, t_vec[j]))
    keep = (tt > cos_thr) & (ai > cos_align) & (aj > cos_align)
    i, j, dh = i[keep], j[keep], dh[keep]
    M = len(P)
    deg = np.bincount(i, minlength=M) + np.bincount(j, minlength=M)
    # two-sided support: at least one edge each way along the tangent
    si = np.einsum("mc,mc->m", dh, t_vec[i])
    pos_i = np.bincount(i[si > 0], minlength=M) + np.bincount(j[si < 0], minlength=M)
    neg_i = np.bincount(i[si < 0], minlength=M) + np.bincount(j[si > 0], minlength=M)
    twosided = np.minimum(pos_i, neg_i)
    Wg = coo_matrix((np.ones(len(i)), (i, j)), shape=(M, M))
    ncc, ccl = connected_components(Wg, directed=False)
    csize = np.bincount(ccl)[ccl]
    return deg, twosided, csize, len(i), ncc


print("\n=== curve / chain support ===")
e3_8 = Z["e3_8"][sel]
E3 = np.stack([Z[f"e3_{k}"][sel] for k in [8, 12, 16, 24]])
Tm = np.einsum("smi,smj->mij", E3, E3) / 4.0
wv, Vv = np.linalg.eigh(Tm)
e3_ms = Vv[:, :, 2]
for tname, tv in [("e3k8", e3_8), ("e3ms", e3_ms)]:
    for rm in [2.0, 3.0, 5.0]:
        for ct in [0.8, 0.9]:
            for ca in [0.7, 0.85]:
                out = chain_scores(tv, rm, ct, ca)
                if out is None:
                    continue
                deg, two, csz, ne, ncc = out
                print(f"-- t={tname} r={rm} cos_t={ct} cos_a={ca}  edges={ne} ncc={ncc}")
                rep("   deg", deg)
                rep("   twosided", two)
                rep("   log_csize", np.log1p(csz))
