"""Final weight re-optimisation at the TRUE gate floor (recall >= 0.70), using the
cached 25-view evidence, plus a check of whether more views help."""
import os, sys, itertools, numpy as np
from scipy.stats import rankdata
from scipy.spatial import cKDTree
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts/explore/syn"))
from tune_lib import Harness
from fastgate import FastGate

OUT = os.path.expanduser("~/3dgs_line/tier1/scripts/explore/syn")
scene = sys.argv[1] if len(sys.argv) > 1 else "chair"
h = Harness(scene); X, opa = h.X, h.opa; M = len(X)
Z = np.load(os.path.join(OUT, f"final_evid_{scene}.npz"))
DP_, DR, VIS = Z["dp"], Z["dr"], Z["vis"]
nv = np.maximum(VIS.sum(0), 1); never = VIS.sum(0) == 0
Rk = lambda v: rankdata(v) / len(v)
fg = FastGate(h, np.arange(M))


def fix(a):
    a = np.asarray(a, float)
    a[never] = np.nanmin(a[~never]) - 1
    return np.nan_to_num(a, nan=-1e9)


T = {}
with np.errstate(all="ignore"):
    for nm, D in (("p", DP_), ("r", DR)):
        A = np.where(VIS, D, np.nan)
        T[nm + "_mean"] = fix(-np.nanmean(A, 0))
        for q in (75, 90):
            T[f"{nm}_q{q}"] = fix(-np.nanpercentile(A, q, axis=0))
        for s in (4, 8, 16, 32):
            T[f"{nm}_soft{s}"] = fix(np.where(VIS, np.exp(-D / s), 0).sum(0) / nv)
        for tau in (4, 8, 16):
            T[f"{nm}_fr{tau}"] = fix((VIS & (D <= tau)).sum(0) / nv)
T["opa"] = opa.astype(float)
R = {k: Rk(v) for k, v in T.items()}

tree = cKDTree(X)
sp = np.median(tree.query(X, k=2)[0][:, 1])
BALL = {rm: tree.query_ball_point(X, r=rm * sp, workers=-1) for rm in (1.5, 2.0, 2.5, 3.0)}


def lrank(s, rm):
    return np.array([np.mean(s[np.asarray(b)] < s[i]) if len(b) > 1 else 1.0
                     for i, b in enumerate(BALL[rm])])


FG = np.arange(0.05, 0.7, 0.01)


def best(s, rmin):
    o = np.argsort(-s, kind="stable"); b = None
    for f in FG:
        k = np.zeros(M, bool); k[o[:int(round(f * M))]] = True
        p, r, n = fg(k)
        if r >= rmin and (b is None or p > b[0]): b = (p, r, f, n)
    return b


PH = [k for k in R if k.startswith("p_")]
RI = [k for k in R if k.startswith("r_")]
print("searching photo x ridge x opa weights ...", flush=True)
res = []
for a in PH:
    for b_ in RI:
        for wb in (0.25, 0.5, 0.75, 1.0):
            for wo in (0.0, 0.25, 0.5):
                g = R[a] + wb * R[b_] + wo * R["opa"]
                bb = best(g, 0.70)
                if bb: res.append((bb[0], bb[1], bb[2], (a, b_, wb, wo), g))
res.sort(key=lambda t: -t[0])
print("\n=== top global combos @rec>=0.70 (before local rank) ===")
for t in res[:10]:
    print(f"  p={t[0]:.4f} r={t[1]:.4f} f={t[2]:.2f}  {t[3][0]} + {t[3][2]}*{t[3][1]} + {t[3][3]}*opa")

print("\n=== + local rank, on the top-6 global combos ===")
fin = []
for t in res[:6]:
    g = t[4]
    for rm in (1.5, 2.0, 2.5, 3.0):
        lr = lrank(g, rm)
        for lam in (0.25, 0.5, 0.75, 1.0):
            for rmin in (0.70, 0.72):
                bb = best(g + lam * lr, rmin)
                if bb: fin.append((bb[0], bb[1], bb[2], t[3], rm, lam, rmin))
fin.sort(key=lambda x: -x[0])
seen = set()
for x in fin:
    key = (x[6],)
    print(f"  [rec>={x[6]}] p={x[0]:.4f} r={x[1]:.4f} f={x[2]:.2f}  "
          f"{x[3][0]}+{x[3][2]}*{x[3][1]}+{x[3][3]}*opa  rad{x[4]}sp lam{x[5]}")
    seen.add(key)
    if len([1 for y in fin[:fin.index(x) + 1]]) > 24: break

print("\n=== PURE GEOMETRY (ridge + opa only) @rec>=0.70 / 0.72 ===")
resg = []
for b_ in RI:
    for b2 in RI:
        for wb in (0.0, 0.25, 0.5):
            for wo in (0.0, 0.25, 0.5, 0.75):
                g = R[b_] + wb * R[b2] + wo * R["opa"]
                for rmin in (0.70, 0.72):
                    bb = best(g, rmin)
                    if bb: resg.append((bb[0], bb[1], bb[2], (b_, b2, wb, wo), rmin, g))
resg.sort(key=lambda t: -t[0])
shown = {0.70: 0, 0.72: 0}
for t in resg:
    if shown[t[4]] >= 5: continue
    shown[t[4]] += 1
    print(f"  [rec>={t[4]}] p={t[0]:.4f} r={t[1]:.4f} f={t[2]:.2f}  "
          f"{t[3][0]}+{t[3][2]}*{t[3][1]}+{t[3][3]}*opa")
gbest = resg[0][5]
for rm in (1.5, 2.0, 3.0):
    lr = lrank(gbest, rm)
    for lam in (0.25, 0.5):
        for rmin in (0.70, 0.72):
            bb = best(gbest + lam * lr, rmin)
            if bb: print(f"  GEOM+lrank rad{rm} lam{lam} [rec>={rmin}]: "
                         f"p={bb[0]:.4f} r={bb[1]:.4f} f={bb[2]:.2f}")
