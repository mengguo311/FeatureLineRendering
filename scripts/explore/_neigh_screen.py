"""EVAL-SIDE screen: AUC of many neighbourhood/multi-scale features vs the mesh label."""
import os
import sys
import time
import numpy as np
from scipy.stats import rankdata
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))

SCRATCH = "/tmp/claude-1026/-home-u00134-3dgs-line/4ee6144a-2815-4286-bec9-0a63623a57f6/scratchpad"
KS = [6, 8, 12, 16, 24, 32, 48]
Z = np.load(os.path.join(SCRATCH, "neigh_cache.npz"))
sel = Z["sel"]
lab = Z["label"]
vis = Z["vis_any"]
EPS = 1e-12


def auc(s, y):
    s = np.asarray(s, float)
    r = rankdata(s)
    n1 = int(y.sum())
    n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return np.nan
    return float((r[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def rep(name, s):
    a_all = auc(s, lab)
    a_vis = auc(s[vis], lab[vis])
    print(f"{name:34s} AUC_all={a_all:.4f}  AUC_vis={a_vis:.4f}")
    return a_all


# ---------------- per-scale raw features (restricted to sel) ----------------
F = {}
for k in KS:
    l1, l2, l3 = Z[f"l1_{k}"], Z[f"l2_{k}"], Z[f"l3_{k}"]
    tr = l1 + l2 + l3 + EPS
    F[f"sc{k}"] = Z[f"sc{k}"]
    F[f"aniso{k}"] = (l1 - l2) / tr
    F[f"lin{k}"] = (l1 - l2) / (l1 + EPS)
    F[f"l1_{k}"] = l1
    F[f"l2_{k}"] = l2
    F[f"cor{k}"] = Z[f"sn{k}"]

print("=== per-scale raw (higher=crease) ===")
for k in KS:
    for tag in ["sc", "aniso", "lin", "l1_", "l2_", "cor"]:
        key = f"{tag}{k}" if tag != "l1_" and tag != "l2_" else f"{tag}{k}"
        rep(key, F[key][sel])

# global-rank normalisation per scale (mesh-free: rank over all gaussians)
R = {k: rankdata(F[f"sc{k}"]) / len(F[f"sc{k}"]) for k in KS}
RA = {k: rankdata(F[f"aniso{k}"]) / len(F[f"aniso{k}"]) for k in KS}

print("\n=== multi-scale agreement (s_crease) ===")
SETS = {
    "all7": KS,
    "6-32": [6, 8, 12, 16, 24, 32],
    "8-32": [8, 12, 16, 24, 32],
    "8-48": [8, 12, 16, 24, 32, 48],
    "12-48": [12, 16, 24, 32, 48],
    "16-48": [16, 24, 32, 48],
    "24-48": [24, 32, 48],
    "6-16": [6, 8, 12, 16],
}
for name, S in SETS.items():
    M = np.stack([R[k][sel] for k in S])
    rep(f"minrank_sc[{name}]", M.min(0))
    rep(f"gmrank_sc[{name}]", np.exp(np.log(M + EPS).mean(0)))
    MA = np.stack([RA[k][sel] for k in S])
    rep(f"minrank_aniso[{name}]", MA.min(0))
    rep(f"gmrank_aniso[{name}]", np.exp(np.log(MA + EPS).mean(0)))
    Ms = np.stack([F[f"sc{k}"][sel] for k in S])
    rep(f"gm_sc_raw[{name}]", np.exp(np.log(Ms + EPS).mean(0)))
    rep(f"min_aniso_raw[{name}]", np.stack([F[f"aniso{k}"][sel] for k in S]).min(0))

print("\n=== tangent / e1 stability across scales ===")
for name, S in SETS.items():
    E3 = np.stack([Z[f"e3_{k}"][sel] for k in S])   # [S,M,3]
    T = np.einsum("smi,smj->mij", E3, E3) / len(S)
    w = np.linalg.eigvalsh(T)
    rep(f"e3_coh[{name}]", w[:, 2])
    E1 = np.stack([Z[f"e1_{k}"][sel] for k in S])
    T1 = np.einsum("smi,smj->mij", E1, E1) / len(S)
    w1 = np.linalg.eigvalsh(T1)
    rep(f"e1_coh[{name}]", w1[:, 2])
