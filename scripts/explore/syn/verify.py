import os, sys, numpy as np
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts/explore/syn"))
from cache_scores import build
OUT = os.path.expanduser("~/3dgs_line/tier1/scripts/explore/syn")

scene = sys.argv[1] if len(sys.argv) > 1 else "chair"
z = dict(np.load(os.path.join(OUT, f"scores_{scene}.npz")))
h, st, sel = build(scene)
P = h.X[sel]
pos, visany, dmin = z["lab_pos"], z["lab_vis"], z["lab_dmin"]
print("pool", len(sel), "vis>=1", visany.sum(), "pos", pos.sum(),
      "base rate(vis) %.3f" % pos[visany].mean())


def auc(s, y, m=None):
    if m is not None:
        s, y = s[m], y[m]
    o = np.argsort(s); r = np.empty(len(s)); r[o] = np.arange(len(s))
    # average ranks for ties
    from scipy.stats import rankdata
    r = rankdata(s)
    n1 = y.sum(); n0 = len(y) - n1
    return (r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


FS = [1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2]
names = [k for k in z if not k.startswith(("lab_", "sel"))]
print(f"{'name':16s} {'AUCvis':>7s} {'AUCall':>7s}  " + "  ".join(f"f={f}" for f in FS))
for k in names:
    s = z[k]
    a1, a0 = auc(s, pos, visany), auc(s, pos)
    row = []
    for f in FS:
        keep = np.zeros(len(sel), bool)
        keep[np.argsort(-s, kind="stable")[:int(f * len(sel))]] = True
        p, r, n = h.evaluate(P, extra_mask=keep)
        row.append(f"{p*100:4.1f}/{r*100:4.1f}")
    print(f"{k:16s} {a1:7.3f} {a0:7.3f}  " + "  ".join(row), flush=True)
