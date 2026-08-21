"""Which mesh-free signals have POSITIVE ranking power on BOTH chair and lego?
Computed over all de-floatered gaussians of each scene."""
import os, sys, numpy as np
from scipy.stats import rankdata
from scipy.spatial import cKDTree
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts/explore/syn"))
from tune_lib import Harness, structure_tensor
from fastgate import FastGate
from src import visibility

OUT = os.path.expanduser("~/3dgs_line/tier1/scripts/explore/syn")
res = {}
for scene in ("chair", "lego"):
    h = Harness(scene); X, opa, N = h.X, h.opa, h.N; M = len(X)
    Z = np.load(os.path.join(OUT, f"final_evid_{scene}.npz"))
    DP_, DR, VIS = Z["dp"], Z["dr"], Z["vis"]
    nv = np.maximum(VIS.sum(0), 1); never = VIS.sum(0) == 0
    pos = np.zeros(M, bool); visany = np.zeros(M, bool)
    for v in h.views:
        vm, uv, _ = visibility.visible_mask(X, h.cams[v], h.gbufs[v]["depth"])
        u = np.clip(np.round(uv[:, 0]).astype(int), 0, h.cams[v].W - 1)
        w = np.clip(np.round(uv[:, 1]).astype(int), 0, h.cams[v].H - 1)
        _, _, cdt = h.crease[v]
        visany |= vm; pos |= vm & (cdt[w, u] <= 2.5)

    def fix(a):
        a = np.asarray(a, float); a[never] = np.nanmin(a[~never]) - 1
        return np.nan_to_num(a, nan=-1e9)

    F = {}
    with np.errstate(all="ignore"):
        F["photo_soft16"] = fix(np.where(VIS, np.exp(-DP_ / 16.0), 0).sum(0) / nv)
        F["photo_mean"] = fix(-np.nanmean(np.where(VIS, DP_, np.nan), 0))
        F["photo_fr4"] = fix((VIS & (DP_ <= 4)).sum(0) / nv)
        F["ridge_q90"] = fix(-np.nanpercentile(np.where(VIS, DR, np.nan), 90, axis=0))
        F["ridge_mean"] = fix(-np.nanmean(np.where(VIS, DR, np.nan), 0))
        F["ridge_fr4"] = fix((VIS & (DR <= 4)).sum(0) / nv)
    F["opacity"] = opa.astype(float)
    F["n_views_visible"] = VIS.sum(0).astype(float)
    st8 = structure_tensor(X, N, 8)
    F["s_crease_k8"] = st8["s_crease"]; F["s_corner_k8"] = st8["s_corner"]
    st24 = structure_tensor(X, N, 24)
    F["s_crease_k24"] = st24["s_crease"]
    tree = cKDTree(X)
    dist, knn = tree.query(X, k=33, workers=-1); knn = knn[:, 1:]
    F["density_k32"] = -dist[:, 1:33].mean(1)
    F["scale_max"] = -h.scale.max(1); F["scale_min"] = -h.scale.min(1)
    nbp = X[knn[:, :32]]; dd = nbp - nbp.mean(1, keepdims=True)
    C = np.einsum("nkc,nkd->ncd", dd, dd) / 32
    w_, V_ = np.linalg.eigh(C)
    npca = V_[:, :, 0]; npca /= np.linalg.norm(npca, axis=1, keepdims=True) + 1e-12
    F["pos_linearity"] = (w_[:, 2] - w_[:, 1]) / (w_[:, 2] + 1e-12)
    F["pos_scatter"] = w_[:, 0] / (w_[:, 2] + 1e-12)
    for k in (8, 16):
        nb = knn[:, :k]; nj = npca[nb]
        sg = np.sign(np.einsum("nkc,nc->nk", nj, npca)); sg[sg == 0] = 1.0
        nj = nj * sg[..., None]; dn = nj - nj.mean(1, keepdims=True)
        ww = np.linalg.eigvalsh(np.einsum("nkc,nkd->ncd", dn, dn) / k)
        F[f"l1_pca{k}"] = ww[:, 2]
        F[f"scr_pca{k}"] = ww[:, 2] - ww[:, 1]
    cs = np.abs(np.einsum("nkc,nc->nk", npca[knn[:, :20]], npca))
    F["dihedral_pca20"] = np.degrees(np.arccos(np.clip(np.percentile(cs, 10, axis=1), -1, 1)))

    def auc(s):
        r = rankdata(s[visany]); y = pos[visany]
        n1 = y.sum(); n0 = len(y) - n1
        return (r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)

    res[scene] = {k: auc(v) for k, v in F.items()}
    res[scene]["_base"] = pos[visany].mean()
    print(f"{scene} done (base rate {pos[visany].mean():.3f})", flush=True)

ks = [k for k in res["chair"] if k != "_base"]
ks.sort(key=lambda k: -min(res["chair"][k], res["lego"][k]))
print(f"\n{'feature':20s} {'chair':>7s} {'lego':>7s}   (sorted by worst-case)")
for k in ks:
    c, l = res["chair"][k], res["lego"][k]
    flag = "  <-- positive on BOTH" if min(c, l) > 0.52 else ""
    print(f"  {k:20s} {c:7.3f} {l:7.3f}{flag}")
