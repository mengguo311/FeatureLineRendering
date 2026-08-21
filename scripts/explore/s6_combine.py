"""Sweep 6: combine the strong mesh-free features; AUC + gate Pareto on the CANONICAL pool,
and the best POOL (base precision at recall>=75%)."""
import os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _pool_common import build_knn, pca_normals, crease_label, auc
from tune_lib import Harness, structure_tensor, nms_along_e1
from scipy.stats import rankdata

t0 = time.time()
h = Harness("chair")
X = h.X
N = len(X)
knn = build_knn(X)

# canonical pool
st_base = structure_tensor(X, h.N, 8)
cand = np.where(st_base["s_crease"] > 0.05)[0]
sel = nms_along_e1(X, cand, st_base["s_crease"], st_base["e1"], st_base["knn"])
P = X[sel]
print("canonical pool", len(sel), h.evaluate(P))

lab_sel, seen_sel = crease_label(h, X, sel)
print(f"canonical pool label: {lab_sel.mean():.3f} positive")

# --- features over ALL gaussians ---
n32 = pca_normals(X, knn, 32)
st16 = structure_tensor(X, n32, 16, knn=knn[:, :16])
dens32 = -np.linalg.norm(X[knn[:, :32]] - X[:, None], axis=2).mean(1)
dens16 = -np.linalg.norm(X[knn[:, :16]] - X[:, None], axis=2).mean(1)
feat = {
    "dens32": dens32,
    "dens16": dens16,
    "l1n": st16["l1"],
    "screase": st16["s_crease"],
    "opa": h.opa,
}
R = {k: rankdata(v) / N for k, v in feat.items()}

combos = {
    "dens32": R["dens32"],
    "l1n": R["l1n"],
    "dens32+l1n": R["dens32"] + R["l1n"],
    "dens32+l1n+opa": R["dens32"] + R["l1n"] + R["opa"],
    "dens32+opa": R["dens32"] + R["opa"],
    "l1n+opa": R["l1n"] + R["opa"],
    "2dens32+l1n": 2 * R["dens32"] + R["l1n"],
    "dens32+2l1n": R["dens32"] + 2 * R["l1n"],
    "dens32*l1n(min)": np.minimum(R["dens32"], R["l1n"]),
    "dens32+l1n+0.5opa": R["dens32"] + R["l1n"] + 0.5 * R["opa"],
    "min(d,l1,opa)": np.minimum(np.minimum(R["dens32"], R["l1n"]), R["opa"]),
}

print("\n=== AUC on ALL gaussians / on CANONICAL POOL seeds ===")
lab_all = np.load(os.path.expanduser("~/3dgs_line/tier1/scripts/explore/lab_all.npy"))
rows = []
for name, c in combos.items():
    a_all = auc(c, lab_all)
    a_sel = auc(c[sel], lab_sel)
    rows.append((name, a_all, a_sel))
    print("  %-20s AUC_all=%.4f  AUC_pool=%.4f" % (name, a_all, a_sel))

# --- Pareto on canonical pool for the best few ---
FS = [1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2]
print("\n=== Pareto on CANONICAL pool (extra_mask = top-f by score) ===")
best = sorted(rows, key=lambda z: -z[2])[:5]
for name, _, _ in best:
    s = combos[name][sel]
    order = np.argsort(-s)
    line = []
    for f in FS:
        keep = np.zeros(len(sel), bool)
        keep[order[:int(f * len(sel))]] = True
        p, r, nv = h.evaluate(P, extra_mask=keep)
        line.append((f, p, r))
    print("  %-20s " % name + "  ".join(f"f={f:.1f}:{p:.3f}/{r:.3f}" for f, p, r in line))

# --- best POOL: threshold combos directly over all gaussians ---
print("\n=== POOL search: threshold combined score over ALL gaussians ===")
pool_rows = []
for name, c in combos.items():
    for q in np.arange(0.30, 0.90, 0.05):
        thr = np.quantile(c, q)
        s2 = np.where(c > thr)[0]
        if len(s2) < 300:
            continue
        p, r, nv = h.evaluate(X[s2])
        pool_rows.append((name, round(q, 2), len(s2), p, r, nv))
a = [x for x in pool_rows if x[4] >= 0.75]
a.sort(key=lambda z: -z[3])
print("  best prec @ rec>=0.75:")
for x in a[:15]:
    print("    %-20s q=%.2f nsel=%6d prec=%.4f rec=%.4f nvis=%6d" % x)
np.savez(os.path.expanduser("~/3dgs_line/tier1/scripts/explore/combos.npz"),
         **{k: v for k, v in combos.items()}, sel=sel)
print("\ntotal", time.time() - t0)
