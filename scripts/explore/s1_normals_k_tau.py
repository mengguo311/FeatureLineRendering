"""Sweep 1: normal definition x structure-tensor k x tau (NMS fixed cos=0.7).
Writes a CSV of gate numbers.
"""
import os, sys, time, itertools
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _pool_common import build_knn, pca_normals, smooth_normals, make_pool
from tune_lib import Harness, structure_tensor

OUT = os.path.expanduser("~/3dgs_line/tier1/scripts/explore/res_s1.csv")

t0 = time.time()
h = Harness("chair")
X, Ncov = h.X, h.N
knn = build_knn(X)
print(f"knn {time.time()-t0:.1f}s", flush=True)

normals = {"cov": Ncov}
for k in (6, 8, 12, 16):
    normals[f"pca{k}"] = pca_normals(X, knn, k)
for k in (6, 8, 12, 16):
    normals[f"sm{k}"] = smooth_normals(Ncov, knn, k)
print(f"normals {time.time()-t0:.1f}s", flush=True)

QS = [0.0, 0.10, 0.25, 0.40, 0.55, 0.65, 0.75, 0.85, 0.92]
KS = [6, 8, 12, 16, 24]

rows = []
for nname, n in normals.items():
    for k in KS:
        st = structure_tensor(X, n, k, knn=knn[:, :k])
        s = st["s_crease"]
        for q in QS:
            tau = float(np.quantile(s, q)) if q > 0 else -1.0
            sel, _ = make_pool(X, n, knn, k, tau, use_nms=True, cos_thr=0.7, st=st)
            if len(sel) < 200:
                continue
            p, r, nv = h.evaluate(X[sel])
            rows.append((nname, k, q, tau, len(sel), p, r, nv))
        print(f"{nname} k={k} done {time.time()-t0:.0f}s", flush=True)

with open(OUT, "w") as f:
    f.write("normal,k,q,tau,nsel,prec,rec,nvis\n")
    for r_ in rows:
        f.write("%s,%d,%.2f,%.5f,%d,%.4f,%.4f,%d\n" % r_)
print("wrote", OUT, len(rows), "rows", time.time() - t0)

# quick top table: best precision with recall>=0.75
arr = [r_ for r_ in rows if r_[6] >= 0.75]
arr.sort(key=lambda z: -z[5])
print("\n== best prec @ rec>=0.75 ==")
print("normal   k   q     tau      nsel   prec    rec")
for r_ in arr[:20]:
    print("%-7s %2d  %.2f  %.5f  %6d  %.4f  %.4f" % (r_[0], r_[1], r_[2], r_[3], r_[4], r_[5], r_[6]))
