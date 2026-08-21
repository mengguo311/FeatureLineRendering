"""EVAL-SIDE screen 4: (a) does ANY crease-structure feature add beyond local density?
(density-stratified AUC + rank-residualised AUC)  (b) real Pareto on the gate."""
import os
import sys
import time
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
    if n1 == 0 or n0 == 0:
        return np.nan
    return float((r[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


h = Harness("chair")
X, Nrm = h.X, h.N
P = X[sel]
treeX = cKDTree(X)
dk, knnB = treeX.query(X, k=193, workers=8)
dk, knnB = dk[:, 1:], knnB[:, 1:]


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
    dih = np.degrees(np.arccos(np.abs(g)))
    dih[~ok] = 0.0
    return dih


DENS = -dk[:, 95]                       # -radius_k96
DENS192 = -dk[:, 191]
dih192 = two_plane(192)
dih48 = two_plane(48)
sm_dih192 = dih192[knnB[:, :192]].mean(1)
sm_sc8 = Z["sc8"][knnB[:, :192]].mean(1)

CAND = {
    "dens_k96": DENS[sel],
    "dens_k192": DENS192[sel],
    "dih192": dih192[sel],
    "dih48": dih48[sel],
    "sm_dih192_k192": sm_dih192[sel],
    "sm_sc8_k192": sm_sc8[sel],
    "sc8": Z["sc8"][sel],
    "minrank_sc_all7": np.stack(
        [rankdata(Z[f"sc{k}"]) / len(sel) for k in [6, 8, 12, 16, 24, 32, 48]])[:, sel].min(0),
}

print("=== density-STRATIFIED AUC (10 equal-count bins of dens_k96) ===")
dq = rankdata(CAND["dens_k96"]) / len(sel)
bins = np.clip((dq * 10).astype(int), 0, 9)
for name, s in CAND.items():
    aa, ww = [], []
    for b in range(10):
        m = bins == b
        if lab[m].sum() < 20 or (~lab[m]).sum() < 20:
            continue
        aa.append(auc(s[m], lab[m])); ww.append(m.sum())
    strat = float(np.average(aa, weights=ww))
    print(f"{name:20s} raw={auc(s, lab):.4f}   density-stratified={strat:.4f}  "
          f"(pos-rate spread over bins ok)")

print("\n=== positive rate per density bin (why density works) ===")
print("  bin:", " ".join(f"{b}" for b in range(10)))
print("  rate:", " ".join(f"{lab[bins==b].mean():.2f}" for b in range(10)))


def pareto(name, score, quiet=False):
    order = np.argsort(-score)
    rows = []
    for f in FS:
        keep = np.zeros(len(sel), bool)
        keep[order[:int(round(f * len(sel)))]] = True
        p, r, n = h.evaluate(P, extra_mask=keep)
        rows.append((f, p, r, n))
    if not quiet:
        print(f"\n--- {name} (AUC_all={auc(score, lab):.4f}) ---")
        for f, p, r, n in rows:
            flag = "  <== GATE PASS" if (p >= 0.80 and r >= 0.70) else ""
            print(f"  f={f:.1f}  prec={p:.4f}  rec={r:.4f}  nvis={n}{flag}")
    return rows


print("\n\n############ PARETO ############")
for nm in ["sc8", "minrank_sc_all7", "dih192", "sm_dih192_k192", "dens_k96", "dens_k192"]:
    pareto(nm, CAND[nm])

# ---- combinations (rank-space) ----
def rk(v):
    return rankdata(v) / len(v)


print("\n\n############ COMBINATIONS ############")
combos = {
    "dens96 + 0.5*dih192": rk(CAND["dens_k96"]) + 0.5 * rk(CAND["dih192"]),
    "dens96 + 1.0*dih192": rk(CAND["dens_k96"]) + 1.0 * rk(CAND["dih192"]),
    "dens96 + 0.5*smdih": rk(CAND["dens_k96"]) + 0.5 * rk(CAND["sm_dih192_k192"]),
    "dens96 + 0.5*sc8": rk(CAND["dens_k96"]) + 0.5 * rk(CAND["sc8"]),
    "dens96*dih192 (gm)": np.sqrt(rk(CAND["dens_k96"]) * rk(CAND["dih192"])),
    "min(dens96,dih192)": np.minimum(rk(CAND["dens_k96"]), rk(CAND["dih192"])),
}
for nm, s in combos.items():
    print(f"{nm:26s} AUC_all={auc(s, lab):.4f} AUC_vis={auc(s[vis], lab[vis]):.4f}")
for nm in ["dens96 + 0.5*dih192", "dens96 + 1.0*dih192", "min(dens96,dih192)"]:
    pareto(nm, combos[nm])
