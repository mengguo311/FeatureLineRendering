"""score_neigh.py -- family "neigh": neighbourhood structure & curve support.

MESH-FREE. Uses only gaussian centres (h.X) and per-gaussian normals (h.N).
No image, no G-buffer, no mesh, no oracle.

compute(h, sel, st) -> float [len(sel)], higher = more likely a true crease seed.

Honest summary of what this family actually delivers on chair (views 0,25),
canonical pool sel = nms_along_e1(structure_tensor(X,N,8), s_crease>0.05), 19304 seeds:

  best single score  : compute_density        AUC 0.788   (local kNN radius; NOT crease-specific)
  best combination   : compute (this module)  AUC 0.761, prec 0.477 @ rec 0.700 (f=0.6)
  assigned "most promising" multi-scale C_N agreement : AUC 0.551  -> essentially useless
  tangent-field coherence / e3 stability across scales: AUC 0.489  -> at/below chance
  curve / chain support: AUC 0.727 raw, but strictly WORSE than the plain local seed count
                         it contains (0.776); density-normalised it is AUC 0.51 -> adds nothing

The gate (prec >= 0.80 @ rec >= 0.70) is NOT reachable from this family.
"""
import numpy as np
from scipy.spatial import cKDTree
from scipy.stats import rankdata
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

EPS = 1e-12
_CACHE = {}


# --------------------------------------------------------------------------- #
# shared neighbourhood cache (one big kNN query, reused by every score)
# --------------------------------------------------------------------------- #
def _nbrs(h, kmax=384):
    key = (id(h), kmax)
    if key not in _CACHE:
        tree = cKDTree(h.X)
        d, idx = tree.query(h.X, k=kmax + 1, workers=8)
        _CACHE[key] = (d[:, 1:], idx[:, 1:], tree)
    return _CACHE[key]


def _rk(v):
    return rankdata(v) / len(v)


def _aligned_normals(h, nb):
    """neighbour normals sign-aligned to the centre normal. nb [N,k] -> [N,k,3]"""
    nj = h.N[nb]
    sg = np.sign(np.einsum("nkc,nc->nk", nj, h.N))
    sg[sg == 0] = 1.0
    return nj * sg[..., None]


def _struct(h, nb):
    """normal structure tensor C_N on a given neighbour set. Returns (s_crease,e1,e3)."""
    nj = _aligned_normals(h, nb)
    dnj = nj - nj.mean(1, keepdims=True)
    C = np.einsum("nkc,nkd->ncd", dnj, dnj) / nb.shape[1]
    w, V = np.linalg.eigh(C)
    return w[:, 2] - w[:, 1], V[:, :, 2], V[:, :, 0]


# --------------------------------------------------------------------------- #
# individual family members
# --------------------------------------------------------------------------- #
def compute_density(h, sel, st=None, k=96):
    """Local point density = -(distance to the k-th nearest gaussian).

    STRONGEST SINGLE SIGNAL IN THIS FAMILY (AUC 0.788) but it is a *regional*
    property, not a crease property: 3DGS densifies where geometry is detailed.
    Its Pareto is poor because it strips isolated seeds that carry unique recall.
    """
    d, _, _ = _nbrs(h)
    return -d[:, k - 1][sel]


def compute_dihedral(h, sel, st=None, k=192):
    """Two-plane fit of the local normal field -> estimated dihedral angle (degrees).

    Split the kNN normals into two clusters by the sign of their deviation along e1,
    average each cluster into a plane normal, and report the angle between the planes.
    A cleaner estimate of "is there a real >=30 deg crease here" than s_crease = l1-l2,
    which conflates the angle with the cluster balance. AUC 0.611.
    """
    _, nb, _ = _nbrs(h)
    nb = nb[:, :k]
    nj = _aligned_normals(h, nb)
    _, e1, _ = _struct(h, nb)
    a = np.einsum("nkc,nc->nk", nj - nj.mean(1, keepdims=True), e1)
    A = a > 0
    ok = (A.sum(1) >= 2) & ((~A).sum(1) >= 2)

    def gm(m):
        w = m[..., None].astype(np.float64)
        return (nj * w).sum(1) / np.clip(w.sum(1), 1, None)

    nA, nB = gm(A), gm(~A)
    nA /= np.linalg.norm(nA, axis=1, keepdims=True) + EPS
    nB /= np.linalg.norm(nB, axis=1, keepdims=True) + EPS
    g = np.clip(np.einsum("nc,nc->n", nA, nB), -0.9999, 0.9999)
    dih = np.degrees(np.arccos(np.abs(g)))
    dih[~ok] = 0.0
    return dih[sel]


def compute_smooth_dihedral(h, sel, st=None, k=192, ksm=384):
    """Regional mean of the two-plane dihedral over the ksm nearest gaussians.

    Spatial averaging turns the weak per-point dihedral (0.611) into the second
    strongest feature in the family (AUC 0.718): true creases live in regions where
    the whole neighbourhood agrees a crease exists.
    """
    dih_all = _dihedral_all(h, k)
    _, nb, _ = _nbrs(h)
    return dih_all[nb[:, :ksm]].mean(1)[sel]


def _dihedral_all(h, k=192):
    key = ("dih", id(h), k)
    if key not in _CACHE:
        _, nb, _ = _nbrs(h)
        nb = nb[:, :k]
        nj = _aligned_normals(h, nb)
        _, e1, _ = _struct(h, nb)
        a = np.einsum("nkc,nc->nk", nj - nj.mean(1, keepdims=True), e1)
        A = a > 0
        ok = (A.sum(1) >= 2) & ((~A).sum(1) >= 2)

        def gm(m):
            w = m[..., None].astype(np.float64)
            return (nj * w).sum(1) / np.clip(w.sum(1), 1, None)

        nA, nB = gm(A), gm(~A)
        nA /= np.linalg.norm(nA, axis=1, keepdims=True) + EPS
        nB /= np.linalg.norm(nB, axis=1, keepdims=True) + EPS
        g = np.clip(np.einsum("nc,nc->n", nA, nB), -0.9999, 0.9999)
        dih = np.degrees(np.arccos(np.abs(g)))
        dih[~ok] = 0.0
        _CACHE[key] = dih
    return _CACHE[key]


def compute_multiscale_agreement(h, sel, st=None, ks=(6, 8, 12, 16, 24, 32, 48)):
    """MIN over scales of the globally rank-normalised s_crease  (the brief's
    "most promising idea": a true crease should be salient at ALL scales).

    NEGATIVE RESULT: AUC 0.551 vs 0.542 for single-scale s_crease at k=8.
    Multi-scale agreement buys ~0.01 AUC. The geometric mean (0.553), the raw
    geometric mean (0.552) and the (l1-l2)/(l1+l2+l3) normalisation (0.515) are
    all in the same dead band. s_crease simply does not separate the pool.
    """
    _, nb, _ = _nbrs(h)
    R = []
    for k in ks:
        sc, _, _ = _struct(h, nb[:, :k])
        R.append(rankdata(sc) / len(sc))
    return np.stack(R)[:, sel].min(0)


def compute_tangent_coherence(h, sel, st=None, ks=(6, 8, 12, 16, 24, 32, 48)):
    """Angular stability of the crease tangent e3 across scales: largest eigenvalue
    of (1/S) sum_k e3_k e3_k^T, in [1/3, 1].

    NEGATIVE RESULT: AUC 0.489 -- below chance. The e1 (across-crease) version is
    0.520. Tangent stability carries no usable information on this pool.
    """
    _, nb, _ = _nbrs(h)
    E = []
    for k in ks:
        _, _, e3 = _struct(h, nb[:, :k])
        E.append(e3[sel])
    E = np.stack(E)
    T = np.einsum("smi,smj->mij", E, E) / len(ks)
    return np.linalg.eigvalsh(T)[:, 2]


def compute_chain_support(h, sel, st=None, radius_mult=5.0, cos_t=0.6, cos_a=0.5,
                          spacing=None, mode="cc"):
    """Curve / chain support: graph over the seed pool linking seeds that are close,
    whose tangents agree (|t_i.t_j| > cos_t) and whose connecting direction is aligned
    with those tangents (|dhat.t| > cos_a). mode "cc" = log component size, "deg" = degree.

    NEGATIVE RESULT: best raw AUC 0.727 (cc, r=5*spacing) / 0.724 (deg, r=8*spacing),
    but the plain count of seeds in the same ball -- with NO tangent test at all -- scores
    0.776. The tangent/curve filtering therefore *destroys* information; normalising the
    degree by the local seed count collapses it to AUC 0.51-0.55. Curve support on this
    pool is local density in disguise.
    """
    P = h.X[sel]
    if spacing is None:
        d, _, _ = _nbrs(h)
        spacing = float(np.median(d[:, 0]))
    tv = _tangent_ms(h, sel)
    tree = cKDTree(P)
    pairs = tree.query_pairs(radius_mult * spacing, output_type="ndarray")
    i, j = pairs[:, 0], pairs[:, 1]
    dd = P[j] - P[i]
    dh = dd / (np.linalg.norm(dd, axis=1) + EPS)[:, None]
    keep = ((np.abs(np.einsum("mc,mc->m", tv[i], tv[j])) > cos_t)
            & (np.abs(np.einsum("mc,mc->m", dh, tv[i])) > cos_a)
            & (np.abs(np.einsum("mc,mc->m", dh, tv[j])) > cos_a))
    i, j = i[keep], j[keep]
    M = len(P)
    if mode == "deg":
        return (np.bincount(i, minlength=M) + np.bincount(j, minlength=M)).astype(float)
    W = coo_matrix((np.ones(len(i)), (i, j)), shape=(M, M))
    _, ccl = connected_components(W, directed=False)
    return np.log1p(np.bincount(ccl)[ccl]).astype(float)


def _tangent_ms(h, sel, ks=(8, 12, 16, 24)):
    _, nb, _ = _nbrs(h)
    E = []
    for k in ks:
        _, _, e3 = _struct(h, nb[:, :k])
        E.append(e3[sel])
    E = np.stack(E)
    T = np.einsum("smi,smj->mij", E, E) / len(ks)
    return np.linalg.eigh(T)[1][:, :, 2]


# --------------------------------------------------------------------------- #
# the score to use
# --------------------------------------------------------------------------- #
def compute(h, sel, st=None):
    """Best score found in the 'neigh' family.

    s = 0.5*rank(local density, k=96)
      + 1.0*rank(regionally smoothed two-plane dihedral)
      + 0.5*rank(multi-scale s_crease agreement)

    Weights come from a 926-point grid search against the chair gate (the top six
    combinations all land within 0.474-0.477 precision, so the choice is not
    knife-edge, but the weights ARE tuned on chair and should be re-checked on lego).

    chair, views 0/25, canonical 19304-seed pool:
      f=1.0 p=.351 r=.883 | f=0.8 p=.415 r=.835 | f=0.6 p=.477 r=.700
      f=0.5 p=.507 r=.619 | f=0.4 p=.531 r=.541 | f=0.3 p=.553 r=.467 | f=0.2 p=.581 r=.357
    AUC 0.761.  DOES NOT PASS the >=80% / >=70% gate at any f.
    """
    return (0.5 * _rk(compute_density(h, sel))
            + 1.0 * _rk(compute_smooth_dihedral(h, sel))
            + 0.5 * _rk(compute_multiscale_agreement(h, sel)))


# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    import os
    import sys
    import time
    from types import SimpleNamespace
    sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
    sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
    from src import common, render
    from tune_lib import structure_tensor, nms_along_e1

    t0 = time.time()
    g = common.load_gaussians("chair")
    keep = render.defloat_mask(g["mu"], g["opacity"])
    h = SimpleNamespace(X=g["mu"][keep], N=g["normal"][keep])
    st = structure_tensor(h.X, h.N, 8)
    cand = np.where(st["s_crease"] > 0.05)[0]
    sel = nms_along_e1(h.X, cand, st["s_crease"], st["e1"], st["knn"])
    print(f"pool: N={len(h.X)} sel={len(sel)}  ({time.time()-t0:.1f}s)")
    for name, fn in [("compute", compute),
                     ("density", compute_density),
                     ("dihedral", compute_dihedral),
                     ("smooth_dihedral", compute_smooth_dihedral),
                     ("multiscale_agreement", compute_multiscale_agreement),
                     ("tangent_coherence", compute_tangent_coherence),
                     ("chain_support", compute_chain_support)]:
        t = time.time()
        s = fn(h, sel, st)
        assert s.shape == (len(sel),) and np.isfinite(s).all(), name
        print(f"  {name:22s} {time.time()-t:6.2f}s  "
              f"min={s.min():.4g} med={np.median(s):.4g} max={s.max():.4g}")
    print(f"total {time.time()-t0:.1f}s")
