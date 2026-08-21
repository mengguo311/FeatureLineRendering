"""Test the only two signals that are positive on BOTH scenes, and print the final
per-view table for every candidate recipe."""
import os, sys, numpy as np
from scipy.stats import rankdata
from scipy.spatial import cKDTree
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts/explore/syn"))
from tune_lib import Harness, structure_tensor, nms_along_e1

OUT = os.path.expanduser("~/3dgs_line/tier1/scripts/explore/syn")
Rk = lambda v: rankdata(v) / len(v)
for scene in ("chair", "lego"):
    h = Harness(scene); X, N = h.X, h.N; M = len(X)
    tree = cKDTree(X)
    dist, _ = tree.query(X, k=33, workers=-1)
    dens = -dist[:, 1:33].mean(1)
    st8 = structure_tensor(X, N, 8)
    print(f"\n########## {scene}  (M={M}) ##########")
    print("  all-gaussian f=1        %.4f/%.4f/%d" % h.evaluate(X))
    cand = np.where(st8["s_crease"] > 0.05)[0]
    sel = nms_along_e1(X, cand, st8["s_crease"], st8["e1"], st8["knn"])
    print("  canonical K=8 pool      %.4f/%.4f/%d" % h.evaluate(X[sel]))

    for nm, s in (("density_k32", Rk(dens)),
                  ("dens+corner", Rk(dens) + Rk(st8["s_corner"])),
                  ("s_corner_k8", Rk(st8["s_corner"]))):
        o = np.argsort(-s, kind="stable")
        row = []
        for f in (0.8, 0.6, 0.5, 0.4, 0.3):
            k = np.zeros(M, bool); k[o[:int(round(f * M))]] = True
            p, r, _ = h.evaluate(X, extra_mask=k)
            row.append(f"f{f}:{p:.3f}/{r:.3f}")
        print(f"  {nm:16s} " + "  ".join(row), flush=True)

    for mode, f in (("overall", 0.22), ("overall", 0.20), ("puregeom", 0.28)):
        s = np.load(os.path.join(OUT, f"finalscore_{mode}_{scene}.npy"))
        o = np.argsort(-s, kind="stable")
        k = np.zeros(M, bool); k[o[:int(round(f * M))]] = True
        p, r, n = h.evaluate(X, extra_mask=k)
        ps, rs, ns = h.evaluate(X, extra_mask=k, per_view=True)
        print(f"  RECIPE {mode} f={f}: {p:.4f}/{r:.4f}  per-view " +
              "  ".join(f"v{v}: p={a:.4f} r={b:.4f} n={c}"
                        for v, a, b, c in zip(h.views, ps, rs, ns)), flush=True)
    ps, rs, ns = h.evaluate(X[sel], per_view=True)
    print("  canonical pool per-view: " +
          "  ".join(f"v{v}: p={a:.4f} r={b:.4f} n={c}"
                    for v, a, b, c in zip(h.views, ps, rs, ns)))
