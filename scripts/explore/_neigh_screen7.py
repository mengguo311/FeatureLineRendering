"""EVAL-SIDE screen 7: normal-BIMODALITY SNR (crease sharpness) + gate-objective
weight search over the surviving family features."""
import os
import sys
import time
import itertools
import numpy as np
from scipy.stats import rankdata
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
from tune_lib import structure_tensor
from _neigh_lite import LiteHarness

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


sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts/explore"))
h = LiteHarness("chair")
X, Nrm = h.X, h.N
P = X[sel]
M = len(sel)
treeX = cKDTree(X)
dk, knnB = treeX.query(X, k=193, workers=8)
dk, knnB = dk[:, 1:], knnB[:, 1:]
sp = 0.00625


def bimodal(k):
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
    # within-group angular dispersion (deg)
    cA = np.clip(np.einsum("nkc,nc->nk", nj, nA), -1, 1)
    cB = np.clip(np.einsum("nkc,nc->nk", nj, nB_), -1, 1)
    ang = np.degrees(np.arccos(np.where(A, cA, cB)))
    w = A.astype(float)
    wsA = np.clip(w.sum(1), 1, None); wsB = np.clip((1 - w).sum(1), 1, None)
    sdA = np.sqrt((w * ang ** 2).sum(1) / wsA)
    sdB = np.sqrt(((1 - w) * ang ** 2).sum(1) / wsB)
    disp = 0.5 * (sdA + sdB)
    snr = dih / (disp + 1.0)
    dih[~ok] = 0.0; snr[~ok] = 0.0; disp[~ok] = 1e3
    return dih, snr, disp


print("=== normal bimodality (crease sharpness SNR) ===")
DIH, SNR, DSP = {}, {}, {}
for k in [16, 32, 64, 128, 192]:
    DIH[k], SNR[k], DSP[k] = bimodal(k)
    rep(f"bimodal_SNR_k{k}", SNR[k][sel])
    rep(f"-within_disp_k{k}", -DSP[k][sel])
    rep(f"dihedral_k{k}", DIH[k][sel])

# ---- surviving feature bank ----
def rk(v):
    return rankdata(v) / len(v)


dens = rk(-dk[:, 95][sel])
d128 = rk(DIH[128][sel])
snr128 = rk(SNR[128][sel])
smdih = rk(DIH[192][knnB[:, :192]].mean(1)[sel])
k = 192
dd = X[knnB[:, :k]] - X[:, None]
wv = np.linalg.eigvalsh(np.einsum("nkc,nkd->ncd", dd, dd) / k)
scat = rk((wv[:, 0] / (wv[:, 2] + EPS))[sel])
sc8 = rk(Z["sc8"][sel])
FEAT = {"dens": dens, "dih128": d128, "snr128": snr128, "smdih": smdih,
        "scat": scat, "sc8": sc8}
print("\nfeature bank AUCs:")
for n, v in FEAT.items():
    rep(n, v)


def gate(score, fs=(0.6, 0.5, 0.4, 0.3, 0.2)):
    order = np.argsort(-score)
    rows = []
    for f in fs:
        keep = np.zeros(M, bool)
        keep[order[:int(round(f * M))]] = True
        p, r, _ = h.evaluate(P, extra_mask=keep)
        rows.append((f, p, r))
    return rows


t = time.time()
gate(dens, (0.5,))
print(f"\none evaluate ~{time.time()-t:.2f}s")

print("\n=== weight search (objective: best precision with recall >= 0.70) ===")
names = ["dih128", "snr128", "smdih", "scat", "sc8"]
grid = [0.0, 0.5, 1.0]
best = []
t0 = time.time()
for ws in itertools.product(grid, repeat=len(names)):
    if sum(ws) > 2.0:
        continue
    s = dens.copy()
    for n, w in zip(names, ws):
        if w:
            s = s + w * FEAT[n]
    rows = gate(s, (0.6, 0.5, 0.4))
    ok = [(p, r, f) for f, p, r in rows if r >= 0.70]
    obj = max([p for p, r, f in ok], default=0.0)
    best.append((obj, ws, rows))
best.sort(key=lambda x: -x[0])
print(f"searched {len(best)} combos in {time.time()-t0:.0f}s")
for obj, ws, rows in best[:8]:
    print(f"obj={obj:.4f} w={dict(zip(names, ws))}")
    for f, p, r in rows:
        print(f"    f={f:.1f} prec={p:.4f} rec={r:.4f}")
