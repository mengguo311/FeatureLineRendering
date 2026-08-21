"""Sweep 4: CONTROLS. How much does the structure tensor actually contribute
once an opacity floor is applied? Plus other mesh-free eligibility features.
"""
import os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _pool_common import build_knn, pca_normals, make_pool
from tune_lib import Harness, structure_tensor
from src import visibility

t0 = time.time()
h = Harness("chair")
X = h.X
knn = build_knn(X)
n16 = pca_normals(X, knn, 16)
st6 = structure_tensor(X, n16, 6, knn=knn[:, :6])
rows = []


def rec(tag, sel):
    if len(sel) < 300:
        print("%-40s SKIP n=%d" % (tag, len(sel)))
        return
    p, r, nv = h.evaluate(X[sel])
    rows.append((tag, len(sel), p, r, nv))
    print("%-40s nsel=%6d prec=%.4f rec=%.4f nvis=%6d" % (tag, len(sel), p, r, nv), flush=True)


print("=== CONTROL 1: NO structure tensor, opacity floor only ===")
for opa in (0.0, 0.1, 0.3, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95):
    sel = np.where(h.opa > opa)[0]
    rec(f"ALL gaussians opa>{opa}", sel)

print("\n=== CONTROL 2: random subset of opa>0.6 (size-matched to the grid winner) ===")
rng = np.random.default_rng(0)
e = np.where(h.opa > 0.6)[0]
for frac in (0.75, 0.5):
    sel = rng.choice(e, int(frac * len(e)), replace=False)
    rec(f"RANDOM {frac} of opa>0.6", sel)

print("\n=== CONTROL 3: s_crease on top of opa>0.6 (does ST add anything?) ===")
s = st6["s_crease"]
for opa in (0.1, 0.6):
    el = h.opa > opa
    for q in (0.0, 0.25, 0.5, 0.75, 0.9):
        tau = float(np.quantile(s[el], q)) if q > 0 else -1
        sel = np.where(el & (s > tau))[0]
        rec(f"opa>{opa} & s_crease>q{q}", sel)

print("\n=== CONTROL 4: other mesh-free eligibility features (no ST) ===")
smax = h.scale.max(1)
smin = h.scale.min(1)
smid = np.sort(h.scale, 1)[:, 1]
feats = {
    "scale_max_SMALL": -smax,
    "scale_max_BIG": smax,
    "flat_ratio_small(smin/smid)": -(smin / (smid + 1e-12)),
    "aniso_smid/smax_small": -(smid / (smax + 1e-12)),
    "opacity": h.opa,
}
d6 = np.linalg.norm(X[knn[:, :6]] - X[:, None], axis=2).mean(1)
feats["dense(-knn6dist)"] = -d6
for name, f in feats.items():
    for q in (0.5, 0.7):
        thr = np.quantile(f, q)
        sel = np.where(f > thr)[0]
        rec(f"{name} top{1-q:.2f}", sel)

print("\n=== CONTROL 5: combine opacity floor with scale/density ===")
for opa in (0.6, 0.7):
    el = h.opa > opa
    for name, f in [("smax_small", -smax), ("dense", -d6)]:
        for q in (0.3, 0.5):
            thr = np.quantile(f[el], q)
            sel = np.where(el & (f > thr))[0]
            rec(f"opa>{opa} & {name} top{1-q:.1f}", sel)

with open(os.path.expanduser("~/3dgs_line/tier1/scripts/explore/res_s4.csv"), "w") as fo:
    fo.write("tag,nsel,prec,rec,nvis\n")
    for r_ in rows:
        fo.write("%s,%d,%.4f,%.4f,%d\n" % r_)
print("\ntotal", time.time() - t0)
