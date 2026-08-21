"""Sweep 2: NMS variants, extreme k, opacity floor / de-floater, corner split.
All on top of the winning PCA-normal family from sweep 1.
"""
import os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _pool_common import build_knn, pca_normals, make_pool
from tune_lib import Harness, structure_tensor

t0 = time.time()
h = Harness("chair")
X, knn = h.X, None
knn = build_knn(X)
rows = []


def rec(tag, sel, extra=""):
    if len(sel) < 200:
        return
    p, r, nv = h.evaluate(X[sel])
    rows.append((tag, len(sel), p, r, nv, extra))
    print("%-34s nsel=%6d prec=%.4f rec=%.4f nvis=%6d %s" % (tag, len(sel), p, r, nv, extra), flush=True)


print("=== A. NMS variants (pca16 normals) ===", flush=True)
QS = [0.25, 0.40, 0.55, 0.65]
for pk in (16,):
    n = pca_normals(X, knn, pk)
    for k in (6, 8):
        st = structure_tensor(X, n, k, knn=knn[:, :k])
        s = st["s_crease"]
        for q in QS:
            tau = float(np.quantile(s, q))
            for nmsmode in ("off", 0.5, 0.7, 0.9):
                sel, _ = make_pool(X, n, knn, k, tau, use_nms=(nmsmode != "off"),
                                   cos_thr=(0.7 if nmsmode == "off" else nmsmode), st=st)
                rec(f"pca{pk}/k{k}/q{q}/nms{nmsmode}", sel)

print("\n=== B. extreme ST k and PCA k (nms 0.7) ===", flush=True)
for pk in (8, 16, 24, 32):
    n = pca_normals(X, knn, pk)
    for k in (4, 5, 6, 8):
        st = structure_tensor(X, n, k, knn=knn[:, :k])
        s = st["s_crease"]
        for q in (0.40, 0.55, 0.65):
            tau = float(np.quantile(s, q))
            sel, _ = make_pool(X, n, knn, k, tau, use_nms=True, cos_thr=0.7, st=st)
            rec(f"pca{pk}/k{k}/q{q}/nms0.7", sel)

print("\n=== C. opacity floor as seed eligibility (pca16/k6) ===", flush=True)
n16 = pca_normals(X, knn, 16)
st6 = structure_tensor(X, n16, 6, knn=knn[:, :6])
s6 = st6["s_crease"]
for floor in (0.1, 0.3, 0.5, 0.7):
    elig = h.opa > floor
    for q in (0.40, 0.55):
        tau = float(np.quantile(s6, q))
        sel, _ = make_pool(X, n16, knn, 6, tau, use_nms=True, cos_thr=0.7, st=st6, elig=elig)
        rec(f"opa>{floor}/q{q}", sel, extra=f"elig={elig.sum()}")

print("\n=== D. corner split (pca16/k6) ===", flush=True)
sc = st6["s_corner"]
for q in (0.40, 0.55):
    tau = float(np.quantile(s6, q))
    for cr in (0.3, 0.5, 0.7, 1.0):
        sel, _ = make_pool(X, n16, knn, 6, tau, use_nms=True, cos_thr=0.7, st=st6, corner_ratio=cr)
        rec(f"creaseonly cr<{cr}/q{q}", sel)
    # corner-ONLY pool
    cand = np.where((s6 > tau) & (sc > 0.7 * s6))[0]
    rec(f"corneronly/q{q}", cand)

print("\n=== E. l1 (total normal variation) instead of s_crease ===", flush=True)
for q in (0.40, 0.55, 0.65, 0.75):
    tau = float(np.quantile(st6["l1"], q))
    sel, _ = make_pool(X, n16, knn, 6, tau, use_nms=True, cos_thr=0.7, st=st6, mode="l1")
    rec(f"l1/q{q}", sel)

with open(os.path.expanduser("~/3dgs_line/tier1/scripts/explore/res_s2.csv"), "w") as f:
    f.write("tag,nsel,prec,rec,nvis,extra\n")
    for r_ in rows:
        f.write("%s,%d,%.4f,%.4f,%d,%s\n" % r_)
print("\ntotal", time.time() - t0)
