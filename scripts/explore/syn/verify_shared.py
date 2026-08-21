import os, sys, numpy as np
from scipy.stats import rankdata
from scipy.spatial import cKDTree
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts/explore/syn"))
from tune_lib import Harness, structure_tensor

OUT = os.path.expanduser("~/3dgs_line/tier1/scripts/explore/syn")
Rk = lambda v: rankdata(v) / len(v)
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
    s = (Rk(ph) + 0.5 * Rk(ri) + 1.0 * Rk(st8["s_corner"]) +
         0.5 * Rk(st8["s_crease"]) + 1.0 * Rk(opa))
    np.save(os.path.join(OUT, f"finalscore_shared_{scene}.npy"), s)
    o = np.argsort(-s, kind="stable")
    print(f"\n##### {scene} SHARED recipe #####")
    for f in (1.0, 0.6, 0.5, 0.46, 0.42, 0.38, 0.3):
        k = np.zeros(M, bool); k[o[:int(round(f * M))]] = True
        p, r, n = h.evaluate(X, extra_mask=k)
        print(f"  f={f:<5} p={p:.4f} r={r:.4f} n={n}" + ("   <== LOCKED" if f == 0.42 else ""))
    k = np.zeros(M, bool); k[o[:int(round(0.42 * M))]] = True
    ps, rs, ns = h.evaluate(X, extra_mask=k, per_view=True)
    print("  PER-VIEW f=0.42: " + "  ".join(f"v{v}: p={a:.4f} r={b:.4f} n={c}"
                                            for v, a, b, c in zip(h.views, ps, rs, ns)))
