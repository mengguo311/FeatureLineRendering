"""EVAL-SIDE screen 3: push scale on chain support + dihedral, add regional smoothing,
and honest DENSITY CONTROLS (is chain-support just measuring local density?)."""
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
from tune_lib import Harness, structure_tensor

SCRATCH = "/tmp/claude-1026/-home-u00134-3dgs-line/4ee6144a-2815-4286-bec9-0a63623a57f6/scratchpad"
Z = np.load(os.path.join(SCRATCH, "neigh_cache.npz"))
sel, lab, vis = Z["sel"], Z["label"], Z["vis_any"]
EPS = 1e-12


def auc(s, y):
    r = rankdata(np.asarray(s, float))
    n1 = int(y.sum()); n0 = len(y) - n1
    return float((r[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def rep(name, s):
    a = auc(s, lab)
    print(f"{name:40s} AUC_all={a:.4f}  AUC_vis={auc(s[vis], lab[vis]):.4f}")
    return a


h = Harness("chair")
X, Nrm = h.X, h.N
P = X[sel]
treeX = cKDTree(X)
treeP = cKDTree(P)
sp = 0.00625  # median 1-NN gaussian spacing (measured)

# ------------- big kNN for larger scales / regional smoothing -------------
t = time.time()
KBIG = 192
dk, knnB = treeX.query(X, k=KBIG + 1, workers=8)
dk, knnB = dk[:, 1:], knnB[:, 1:]
print(f"knn{KBIG} {time.time()-t:.1f}s")

print("\n=== DENSITY CONTROLS (mesh-free but NOT crease-specific) ===")
for k in [8, 32, 96, 192]:
    rep(f"-radius_k{k} (density up)", -dk[:, k - 1][sel])
for rm in [5, 10, 20, 40]:
    cnt = np.asarray(treeX.query_ball_point(P, rm * sp, return_length=True), float)
    rep(f"gauss_count_r{rm}sp", cnt)
    cntS = np.asarray(treeP.query_ball_point(P, rm * sp, return_length=True), float)
    rep(f"seed_count_r{rm}sp", cntS)
    rep(f"seed_frac_r{rm}sp", cntS / np.clip(cnt, 1, None))

# ------------- dihedral / s_crease at bigger k -------------
print("\n=== larger-scale structure tensor / dihedral ===")


def two_plane(k):
    nb = knnB[:, :k]
    nj = Nrm[nb]
    sgn = np.sign(np.einsum("nkc,nc->nk", nj, Nrm)); sgn[sgn == 0] = 1.0
    nj = nj * sgn[..., None]
    nbar = nj.mean(1, keepdims=True)
    st = structure_tensor(X, Nrm, k, knn=nb)
    e1 = st["e1"]
    a = np.einsum("nkc,nc->nk", nj - nbar, e1)
    A = a > 0
    cA, cB = A.sum(1), (~A).sum(1)
    ok = (cA >= 2) & (cB >= 2)

    def gm(mask, arr):
        w = mask[..., None].astype(np.float64)
        return (arr * w).sum(1) / np.clip(w.sum(1), 1, None)
    xj = X[nb]
    nA = gm(A, nj); nB_ = gm(~A, nj)
    nA /= np.linalg.norm(nA, axis=1, keepdims=True) + EPS
    nB_ /= np.linalg.norm(nB_, axis=1, keepdims=True) + EPS
    pA, pB = gm(A, xj), gm(~A, xj)
    g = np.clip(np.einsum("nc,nc->n", nA, nB_), -0.9999, 0.9999)
    dih = np.degrees(np.arccos(np.abs(g)))
    rad = dk[:, k - 1] + EPS
    resA = np.abs(np.einsum("nkc,nc->nk", xj - pA[:, None], nA))
    resB = np.abs(np.einsum("nkc,nc->nk", xj - pB[:, None], nB_))
    res = np.where(A, resA, resB)
    rms = np.sqrt((res ** 2).mean(1))
    dih[~ok] = 0.0
    bal = np.minimum(cA, cB) / k
    return dih, rms / rad, rms, bal, st["s_crease"]


DIH, RMSn, RMS, BAL, SC = {}, {}, {}, {}, {}
for k in [32, 64, 96, 128, 192]:
    t = time.time()
    DIH[k], RMSn[k], RMS[k], BAL[k], SC[k] = two_plane(k)
    rep(f"dihedral_k{k}", DIH[k][sel])
    rep(f"+planeRMSn_k{k}", RMSn[k][sel])
    rep(f"+planeRMS_k{k}(raw)", RMS[k][sel])
    rep(f"balance_k{k}", BAL[k][sel])
    rep(f"s_crease_k{k}", SC[k][sel])
    print(f"    ({time.time()-t:.1f}s)")

# ------------- regional smoothing of weak per-point scores -------------
print("\n=== regional smoothing (mean of a weak score over kNN) ===")
base = {"sc8": Z["sc8"], "sc48": Z["sc48"], "dih48": None}
d48, r48, _, _, _ = two_plane(48)
base["dih48"] = d48
base["dih192"] = DIH[192]
for bname, bv in base.items():
    for ks in [16, 48, 96, 192]:
        sm = bv[knnB[:, :ks]].mean(1)
        rep(f"smooth[{bname}]_k{ks}", sm[sel])

# ------------- chain support at bigger radius -------------
print("\n=== chain support, large radius ===")
e3 = Z["e3_8"][sel]
E3 = np.stack([Z[f"e3_{k}"][sel] for k in [8, 12, 16, 24]])
Tm = np.einsum("smi,smj->mij", E3, E3) / 4.0
e3ms = np.linalg.eigh(Tm)[1][:, :, 2]


def chain(tv, rm, ct, ca):
    pairs = treeP.query_pairs(rm * sp, output_type="ndarray")
    i, j = pairs[:, 0], pairs[:, 1]
    d = P[j] - P[i]
    dh = d / (np.linalg.norm(d, axis=1) + EPS)[:, None]
    tt = np.abs(np.einsum("mc,mc->m", tv[i], tv[j]))
    ai = np.abs(np.einsum("mc,mc->m", dh, tv[i]))
    aj = np.abs(np.einsum("mc,mc->m", dh, tv[j]))
    keep = (tt > ct) & (ai > ca) & (aj > ca)
    i, j = i[keep], j[keep]
    M = len(P)
    deg = np.bincount(i, minlength=M) + np.bincount(j, minlength=M)
    W = coo_matrix((np.ones(len(i)), (i, j)), shape=(M, M))
    _, ccl = connected_components(W, directed=False)
    csz = np.bincount(ccl)[ccl]
    return deg, csz, len(i)


for rm in [5, 8, 12, 20]:
    for ct in [0.6, 0.8]:
        for ca in [0.5, 0.7]:
            deg, csz, ne = chain(e3ms, rm, ct, ca)
            print(f"-- r={rm}sp cos_t={ct} cos_a={ca} edges={ne}")
            rep("   chain_deg", deg.astype(float))
            rep("   chain_logcc", np.log1p(csz))
            # density-normalised: fraction of nearby seeds that are chain-compatible
            cntS = np.asarray(treeP.query_ball_point(P, rm * sp, return_length=True), float)
            rep("   chain_deg/localseeds", deg / np.clip(cntS, 1, None))
