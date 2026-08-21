"""Sweep 3: full combined grid (pca_k x ST k x nms x opacity floor x tau x saliency)."""
import os, sys, time, itertools
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _pool_common import build_knn, pca_normals, make_pool
from tune_lib import Harness, structure_tensor

t0 = time.time()
h = Harness("chair")
X = h.X
knn = build_knn(X)
rows = []

PCAK = [12, 16, 24]
STK = [4, 5, 6, 8]
NMS = ["off", 0.9, 0.7]
OPA = [0.1, 0.3, 0.5, 0.6, 0.7, 0.8]
QS = [0.25, 0.40, 0.55, 0.65, 0.75]
MODE = ["crease", "l1"]

for pk in PCAK:
    n = pca_normals(X, knn, pk)
    for k in STK:
        st = structure_tensor(X, n, k, knn=knn[:, :k])
        for mode in MODE:
            sc = st["s_crease"] if mode == "crease" else st["l1"]
            for opa in OPA:
                elig = h.opa > opa
                for q in QS:
                    tau = float(np.quantile(sc[elig], q))
                    for nm in NMS:
                        sel, _ = make_pool(X, n, knn, k, tau, use_nms=(nm != "off"),
                                           cos_thr=(0.7 if nm == "off" else nm),
                                           st=st, elig=elig, mode=mode)
                        if len(sel) < 300:
                            continue
                        p, r, nv = h.evaluate(X[sel])
                        rows.append((pk, k, mode, opa, q, str(nm), len(sel), p, r, nv))
    print(f"pca{pk} done {time.time()-t0:.0f}s", flush=True)

out = os.path.expanduser("~/3dgs_line/tier1/scripts/explore/res_s3.csv")
with open(out, "w") as f:
    f.write("pcak,k,mode,opa,q,nms,nsel,prec,rec,nvis\n")
    for r_ in rows:
        f.write("%d,%d,%s,%.2f,%.2f,%s,%d,%.4f,%.4f,%d\n" % r_)
print("wrote", out, len(rows), "rows", f"{time.time()-t0:.0f}s")

for thr in (0.75, 0.80, 0.85):
    a = [x for x in rows if x[8] >= thr]
    a.sort(key=lambda z: -z[7])
    print(f"\n== best prec @ rec>={thr} ==")
    print("pcak k  mode    opa   q    nms   nsel   prec    rec")
    for x in a[:12]:
        print("%4d %2d  %-6s %.2f %.2f  %-4s %6d  %.4f  %.4f" %
              (x[0], x[1], x[2], x[3], x[4], x[5], x[6], x[7], x[8]))
