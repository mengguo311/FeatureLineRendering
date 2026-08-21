"""Round 7: edge-model fit with denoised normals, threshold cascades, dense f grid."""
import os
import sys
import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tune_lib import Harness, structure_tensor, nms_along_e1
from explore_geom import auc, sweep, SCRATCH

Z1 = np.load(os.path.join(SCRATCH, "geom_all.npz"))
Z2 = np.load(os.path.join(SCRATCH, "geom_denoise.npz"))
META = {"sel", "near", "visa", "ncnt", "vcnt"}
near, visa, sel = Z1["near"], Z1["visa"], Z1["sel"]
F = {k: Z1[k] for k in Z1.files if k not in META}
F.update({k: Z2[k] for k in Z2.files})


def zr(x):
    return (np.argsort(np.argsort(x)) + 0.5) / len(x)


def edge_fit(h, sel, kp=20, kc=24):
    """2-plane (edge) model fit residual gain using position-PCA normals. MESH-FREE."""
    X = h.X
    tree = cKDTree(X)
    d, knn = tree.query(X, k=max(kp, kc) + 1)
    d, knn = d[:, 1:], knn[:, 1:]
    nb = knn[:, :kp]
    Q = X[nb] - X[nb].mean(1, keepdims=True)
    C = np.einsum("nkc,nkd->ncd", Q, Q) / kp
    w, V = np.linalg.eigh(C)
    npca = V[:, :, 0]
    s = np.sign((npca * h.N).sum(1))
    s[s == 0] = 1
    npca = npca * s[:, None]

    nbc = knn[:, :kc]
    nj = npca[nbc]
    sg = np.sign(np.einsum("nkc,nc->nk", nj, npca))
    sg[sg == 0] = 1
    nj = nj * sg[..., None]
    nbar = nj.mean(1, keepdims=True)
    Cn = np.einsum("nkc,nkd->ncd", nj - nbar, nj - nbar) / kc
    wn, Vn = np.linalg.eigh(Cn)
    e1 = Vn[:, :, 2]
    proj = np.einsum("nkc,nc->nk", nj - nbar, e1)
    side = proj > 0
    Pn = X[nbc] - X[:, None, :]
    # 1-plane residual
    r1 = np.einsum("nkc,nc->nk", Pn - Pn.mean(1, keepdims=True), npca)
    rms1 = np.sqrt((r1 ** 2).mean(1))
    res2 = np.zeros(len(X))
    cnt = np.zeros(len(X))
    for sflag in (True, False):
        m = (side == sflag)
        c = m.sum(1).astype(float)
        mean = (Pn * m[..., None]).sum(1) / np.maximum(c, 1)[:, None]
        D = (Pn - mean[:, None, :]) * m[..., None]
        Cm = np.einsum("nkc,nkd->ncd", D, D) / np.maximum(c, 1)[:, None, None]
        wm, Vm = np.linalg.eigh(Cm)
        rr = np.einsum("nkc,nc->nk", Pn - mean[:, None, :], Vm[:, :, 0]) * m
        res2 += (rr ** 2).sum(1)
        cnt += c
    rms2 = np.sqrt(res2 / np.maximum(cnt, 1))
    sp = d[:, :kc].mean(1) + 1e-12
    return {"edge_gain": np.log((rms1 + 1e-9) / (rms2 + 1e-9)),
            "edge_thick": rms1 / sp,
            "edge_res2": -(rms2 / sp)}


def main():
    h = Harness("chair")
    st = structure_tensor(h.X, h.N, 8)
    P = h.X[sel]
    E = edge_fit(h, sel)
    print("=== edge-model fit (PCA-normal 2-plane) ===")
    for n, v in E.items():
        vv = v[sel]
        print(f"{n:14s} AUC_vis={auc(vv[visa], near[visa]):.3f}")
        F[n] = vv

    G = ["seed_dens_k24", "nb_opa_mean", "p90ang_pca_k20", "dens", "curv_k20",
         "nb_flat_mean", "opa"]
    SG = {n: (1.0 if auc(F[n][visa], near[visa]) >= 0.5 else -1.0) for n in F}
    combo = sum(zr(SG[n] * F[n]) for n in G)

    print("\n=== dense f grid, greedy-7 combo ===")
    fs = [1.0, 0.9, 0.8, 0.7, 0.65, 0.6, 0.55, 0.5, 0.45, 0.4, 0.35, 0.3, 0.25, 0.2, 0.15, 0.1]
    res = sweep(h, P, combo, fs)
    for f, p, r, nv in res:
        flag = "  <-- recall>=0.70" if r >= 0.70 else ""
        print(f"  f={f:.2f}  prec={p:.3f} rec={r:.3f} nvis={nv}{flag}")

    # with the edge features added
    for extra in [["edge_gain"], ["edge_thick"], ["edge_gain", "edge_thick"]]:
        c2 = combo + sum(zr(SG[n] * F[n]) for n in extra)
        print(f"\n+{extra} AUCvis={auc(c2[visa], near[visa]):.3f}  " +
              " ".join(f"{f:.1f}:{p:.3f}/{r:.3f}"
                       for f, p, r, _ in sweep(h, P, c2, [0.6, 0.5, 0.4, 0.3])))

    # ---------------- threshold cascades ----------------
    print("\n=== threshold cascades (hard AND gates, then rank inside by combo) ===")
    dih = F["p90ang_pca_k20"]
    for ang in [20, 30, 40, 50]:
        for opq in [0.0, 0.3, 0.5]:
            g = (dih > ang) & (F["nb_opa_mean"] > opq)
            if g.sum() < 500:
                continue
            s = combo + 1e6 * g
            r6 = sweep(h, P, s, [g.mean()])
            f, p, r, nv = r6[0]
            print(f"  dih>{ang:3d} nb_opa>{opq:.1f}: f={g.mean():.3f} "
                  f"prec={p:.3f} rec={r:.3f}")

    np.save(os.path.join(SCRATCH, "combo7.npy"), combo)


if __name__ == "__main__":
    main()
