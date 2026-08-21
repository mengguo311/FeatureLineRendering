"""LOCAL COMPETITION: the global evidence score is regional (cannot resolve 2.5px),
but COMPARING gaussians inside one local cluster can -- the cluster straddles the
crease and the member closest to it wins.  Sweep local-rank / local-NMS variants."""
import os, sys, numpy as np
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
E = np.load(os.path.join(OUT, f"evid_all_{scene}.npz"))
vis = E["vis"]; nv = np.maximum(vis.sum(0), 1)
Rk = lambda v: rankdata(v) / len(v)
never = vis.sum(0) == 0

soft16 = np.where(vis, np.exp(-E["sparse"] / 16.0), 0).sum(0) / nv
with np.errstate(all="ignore"):
    rq90 = -np.nan_to_num(np.nanpercentile(np.where(vis, E["ridge45"], np.nan), 90, axis=0), nan=1e9)
rfr8 = (vis & (E["ridge45"] <= 8)).sum(0) / nv
for a in (soft16, rq90, rfr8): a[never] = a.min() - 1

S_ALL = Rk(soft16) + 0.5 * Rk(rq90)                 # overall (photos + G-buffer)
S_GEO = Rk(rq90) + 0.5 * Rk(opa) + 0.25 * Rk(rfr8)  # pure geometry (G-buffer only)

fg = FastGate(h, np.arange(M))
print(f"[{scene}] all={M} base %.3f/%.3f/%d" % fg(np.ones(M, bool)))
tree = cKDTree(X)
sp = np.median(tree.query(X, k=2)[0][:, 1])
print("median 1NN spacing %.5f" % sp)

FG = np.arange(0.05, 0.75, 0.01)


def best(s, rmin=0.72):
    o = np.argsort(-s, kind="stable"); b = None
    for f in FG:
        k = np.zeros(M, bool); k[o[:int(round(f * M))]] = True
        p, r, n = fg(k)
        if r >= rmin and (b is None or p > b[0]): b = (p, r, f, n)
    return b


def show(s, tag):
    b = best(s)
    print(f"  {tag:34s} " + (f"p={b[0]:.3f} r={b[1]:.3f} f={b[2]:.2f} n={b[3]}" if b else "-"),
          flush=True)
    return b


for label, S in (("OVERALL", S_ALL), ("PUREGEOM", S_GEO)):
    print(f"\n########## {label} ##########")
    show(S, "global only")
    print("  -- kNN local rank --")
    for k in (6, 8, 12, 16, 24, 48):
        _, nb = tree.query(X, k=k, workers=-1)
        lr = (S[nb] < S[:, None]).sum(1) / k
        for lam in (0.5, 1.0, 2.0, 4.0):
            show(S + lam * lr, f"knn{k} lam{lam}")
        show(lr + 1e-6 * S, f"knn{k} PURE local rank")
    print("  -- radius local rank --")
    for rm in (2, 3, 5, 8):
        L = tree.query_ball_point(X, r=rm * sp, workers=-1)
        lr = np.array([np.mean(S[np.asarray(l)] < S[i]) if len(l) > 1 else 1.0
                       for i, l in enumerate(L)])
        cnt = np.array([len(l) for l in L], float)
        for lam in (0.5, 1.0, 2.0):
            show(S + lam * lr, f"rad{rm}sp lam{lam}")
        show(lr + 1e-6 * S, f"rad{rm}sp PURE local rank")
        show(S + 1.0 * lr + 0.25 * Rk(cnt), f"rad{rm}sp lam1 +dens")

print("\n########## ORACLE upper bound on this pool ##########")
from src import visibility
dmin = np.full(M, np.inf)
for v in h.views:
    vm, uv, _ = visibility.visible_mask(X, h.cams[v], h.gbufs[v]["depth"])
    u = np.clip(np.round(uv[:, 0]).astype(int), 0, 799)
    w = np.clip(np.round(uv[:, 1]).astype(int), 0, 799)
    _, _, cdt = h.crease[v]
    dmin = np.where(vm, np.minimum(dmin, cdt[w, u]), dmin)
orc = -np.nan_to_num(dmin, posinf=1e6)
b = best(orc)
print(f"  oracle best @rec>=0.72: p={b[0]:.3f} r={b[1]:.3f} f={b[2]:.2f}")
o = np.argsort(-orc, kind="stable")
for f in (0.4, 0.3, 0.25, 0.2, 0.15, 0.1):
    k = np.zeros(M, bool); k[o[:int(round(f * M))]] = True
    print(f"    f={f}: %.3f/%.3f" % fg(k)[:2])
