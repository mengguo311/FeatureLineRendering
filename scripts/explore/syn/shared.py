"""Is there ANY single shared parameter set that beats the baseline on BOTH scenes?
Objective: maximise min-over-scenes precision subject to recall >= 0.70 in both."""
import os, sys, itertools, numpy as np
from scipy.stats import rankdata
from scipy.spatial import cKDTree
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts/explore/syn"))
from tune_lib import Harness, structure_tensor
from fastgate import FastGate

OUT = os.path.expanduser("~/3dgs_line/tier1/scripts/explore/syn")
Rk = lambda v: rankdata(v) / len(v)
S = {}
for scene in ("chair", "lego"):
    h = Harness(scene); X, N, opa = h.X, h.N, h.opa; M = len(X)
    Z = np.load(os.path.join(OUT, f"final_evid_{scene}.npz"))
    DP_, DR, VIS = Z["dp"], Z["dr"], Z["vis"]
    nv = np.maximum(VIS.sum(0), 1); never = VIS.sum(0) == 0

    def fix(a):
        a = np.asarray(a, float); a[never] = np.nanmin(a[~never]) - 1
        return np.nan_to_num(a, nan=-1e9)

    with np.errstate(all="ignore"):
        ph = fix(np.where(VIS, np.exp(-DP_ / 16.0), 0).sum(0) / nv)
        ri = fix(-np.nanpercentile(np.where(VIS, DR, np.nan), 90, axis=0))
    st8 = structure_tensor(X, N, 8)
    tree = cKDTree(X); dist, _ = tree.query(X, k=33, workers=-1)
    F = {"photo": Rk(ph), "ridge": Rk(ri), "corner": Rk(st8["s_corner"]),
         "crease": Rk(st8["s_crease"]), "dens": Rk(-dist[:, 1:33].mean(1)),
         "opa": Rk(opa)}
    S[scene] = dict(F=F, fg=FastGate(h, np.arange(M)), M=M, h=h, X=X)
    print(f"{scene} ready M={M}", flush=True)

FGRID = np.arange(0.1, 1.01, 0.02)
keys = ["photo", "ridge", "corner", "crease", "dens", "opa"]
W = [0.0, 0.5, 1.0]
best = []
for wv in itertools.product(W, repeat=len(keys)):
    if sum(wv) == 0: continue
    per = {}
    for sc in S:
        s = sum(w * S[sc]["F"][k] for w, k in zip(wv, keys) if w)
        o = np.argsort(-s, kind="stable"); M = S[sc]["M"]; fgg = S[sc]["fg"]
        per[sc] = []
        for f in FGRID:
            kk = np.zeros(M, bool); kk[o[:int(round(f * M))]] = True
            p, r, _ = fgg(kk)
            per[sc].append((f, p, r))
    # shared f: require recall>=0.70 in BOTH, maximise min precision
    bb = None
    for i, f in enumerate(FGRID):
        _, pc, rc = per["chair"][i]; _, pl, rl = per["lego"][i]
        if rc >= 0.70 and rl >= 0.70:
            m = min(pc, pl)
            if bb is None or m > bb[0]: bb = (m, f, pc, rc, pl, rl)
    if bb: best.append((bb, wv))
best.sort(key=lambda t: -t[0][0])
print(f"\n{'min-prec':>8s} {'f':>5s}  chair p/r        lego p/r         weights")
for (m, f, pc, rc, pl, rl), wv in best[:20]:
    ws = " ".join(f"{k}={w}" for k, w in zip(keys, wv) if w)
    print(f"{m:8.4f} {f:5.2f}  {pc:.4f}/{rc:.4f}   {pl:.4f}/{rl:.4f}   {ws}")

print("\nreference (no ranking at all):")
for sc in S:
    print(f"  {sc} all-gaussians   %.4f/%.4f/%d" % S[sc]["h"].evaluate(S[sc]["X"]))
