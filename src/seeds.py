"""tier1/src/seeds.py — object-space crease/corner seeds via normal-structure-tensor C_N.
METHOD PATH: consumes only gaussian centers + per-gaussian normals. NO mesh.

C_N^(i) = mean over kNN of (n_j - nbar_i)(n_j - nbar_i)^T with neighbor normals
sign-aligned to n_i (gaussian normals have arbitrary sign). Eigen l1>=l2>=l3 with
eigenvectors e1,e2,e3: s_crease = l1-l2 (tangent = e3), s_corner = l2-l3.
NMS: seed i is suppressed if a kNN neighbor whose offset lies mostly along e1_i
(across the crease) has strictly higher saliency.
"""
import numpy as np
from scipy.spatial import cKDTree


def compute_seeds(X, n, k=16, tau_seed=0.05, corner_ratio=0.7, nms_cos=0.7,
                  use_cn=True, score=None, keep_frac=None):
    """X[N,3] centers, n[N,3] unit normals (sign arbitrary).
    Returns dict: pos[M,3], tangent[M,3], saliency[M], type[M] (0=crease,1=corner),
    plus 'index' back into X.

    use_cn=False keeps every input gaussian as a candidate instead of thresholding
    s_crease. On vanilla 3DGS the C_N threshold is close to chance (measured on
    chair: AUC 0.54, and it costs recall — 0.883 vs 0.963 for keeping everything),
    so the honest pipeline is to skip it and rank by evidence.py instead.
    score[N] (optional, mesh-free, higher=better) + keep_frac then select the top
    fraction of the surviving candidates.
    """
    N = len(X)
    tree = cKDTree(X)
    _, knn = tree.query(X, k=k + 1)
    knn = knn[:, 1:]  # drop self  [N,k]

    nj = n[knn]                                   # [N,k,3]
    sign = np.sign(np.einsum("nkc,nc->nk", nj, n))
    sign[sign == 0] = 1.0
    nj = nj * sign[..., None]                     # align neighbor normals to n_i
    nbar = nj.mean(1, keepdims=True)              # [N,1,3]
    dnj = nj - nbar
    C = np.einsum("nkc,nkd->ncd", dnj, dnj) / k   # [N,3,3]

    w, V = np.linalg.eigh(C)                      # ascending: w[:,2]>=w[:,1]>=w[:,0]
    l1, l2, l3 = w[:, 2], w[:, 1], w[:, 0]
    e1 = V[:, :, 2]                               # normal-variation direction (across crease)
    e3 = V[:, :, 0]                               # crease tangent
    s_crease = l1 - l2
    s_corner = l2 - l3

    if use_cn:
        cand = np.where(s_crease > tau_seed)[0]
        if len(cand) == 0:
            return {"pos": np.zeros((0, 3)), "tangent": np.zeros((0, 3)),
                    "saliency": np.zeros(0), "type": np.zeros(0, np.uint8),
                    "index": np.zeros(0, np.int64)}
        # NMS along e1 within local kNN (vectorized over candidates)
        is_cand = np.zeros(N, bool)
        is_cand[cand] = True
        nb = knn[cand]                                        # [M,k]
        d = X[nb] - X[cand][:, None]                          # [M,k,3]
        dn = np.linalg.norm(d, axis=2) + 1e-12
        along_e1 = np.abs(np.einsum("mkc,mc->mk", d, e1[cand])) / dn > nms_cos
        rival = is_cand[nb] & along_e1 & (s_crease[nb] > s_crease[cand][:, None])
        sel = cand[~rival.any(1)]
    else:
        sel = np.arange(N)

    if score is not None and keep_frac is not None and 0 < keep_frac < 1:
        order = sel[np.argsort(-np.asarray(score)[sel])]
        sel = np.sort(order[:max(1, int(keep_frac * len(sel)))])

    typ = (s_corner[sel] > corner_ratio * s_crease[sel]).astype(np.uint8)  # 1=corner
    out = {"pos": X[sel], "tangent": e3[sel], "saliency": s_crease[sel],
           "type": typ, "index": sel}
    if score is not None:
        out["score"] = np.asarray(score)[sel]
    return out


def save_seeds(path, seeds):
    np.savez(path, **seeds)


def load_seeds(path):
    z = np.load(path)
    return {k: z[k] for k in z.files}
