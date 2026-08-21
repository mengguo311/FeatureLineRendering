"""Honest diagnosis of the lego transfer failure: random-keep control + per-component AUC."""
import os, sys, numpy as np
from scipy.stats import rankdata
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts/explore/syn"))
from tune_lib import Harness, structure_tensor, nms_along_e1
from fastgate import FastGate
from src import visibility

OUT = os.path.expanduser("~/3dgs_line/tier1/scripts/explore/syn")
scene = sys.argv[1] if len(sys.argv) > 1 else "lego"
h = Harness(scene); X, opa = h.X, h.opa; M = len(X)
Z = np.load(os.path.join(OUT, f"final_evid_{scene}.npz"))
DP_, DR, VIS = Z["dp"], Z["dr"], Z["vis"]
nv = np.maximum(VIS.sum(0), 1); never = VIS.sum(0) == 0
Rk = lambda v: rankdata(v) / len(v)
fg = FastGate(h, np.arange(M))

# labels (EVAL ONLY)
pos = np.zeros(M, bool); visany = np.zeros(M, bool)
for v in h.views:
    vm, uv, _ = visibility.visible_mask(X, h.cams[v], h.gbufs[v]["depth"])
    u = np.clip(np.round(uv[:, 0]).astype(int), 0, h.cams[v].W - 1)
    w = np.clip(np.round(uv[:, 1]).astype(int), 0, h.cams[v].H - 1)
    _, _, cdt = h.crease[v]
    visany |= vm; pos |= vm & (cdt[w, u] <= 2.5)
print(f"[{scene}] M={M} vis>=1 {visany.sum()} pos {pos.sum()} "
      f"base rate(vis) {pos[visany].mean():.3f}")


def auc(s):
    r = rankdata(s[visany]); y = pos[visany]
    n1 = y.sum(); n0 = len(y) - n1
    return (r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def fix(a):
    a = np.asarray(a, float); a[never] = np.nanmin(a[~never]) - 1
    return np.nan_to_num(a, nan=-1e9)


with np.errstate(all="ignore"):
    p_soft16 = fix(np.where(VIS, np.exp(-DP_ / 16.0), 0).sum(0) / nv)
    r_q90 = fix(-np.nanpercentile(np.where(VIS, DR, np.nan), 90, axis=0))
    r_fr8 = fix((VIS & (DR <= 8)).sum(0) / nv)
S_ov = np.load(os.path.join(OUT, f"finalscore_overall_{scene}.npy"))
S_pg = np.load(os.path.join(OUT, f"finalscore_puregeom_{scene}.npy"))
st = structure_tensor(X, h.N, 8)

print("\ncomponent AUCs (over gaussians visible in >=1 eval view):")
for nm, s in (("photo DT soft16", p_soft16), ("ridge q90", r_q90), ("ridge fr8", r_fr8),
              ("opacity", opa.astype(float)), ("s_crease K=8", st["s_crease"]),
              ("FINAL overall", S_ov), ("FINAL puregeom", S_pg)):
    print(f"  {nm:18s} AUC={auc(s):.3f}")

print("\nrandom-keep control (mean of 5 seeds) vs the final score:")
rng = np.random.RandomState(0)
for f in (0.8, 0.6, 0.4, 0.3, 0.22, 0.2):
    ps, rs = [], []
    for t in range(5):
        k = rng.rand(M) < f
        p, r, _ = fg(k); ps.append(p); rs.append(r)
    o = np.argsort(-S_ov, kind="stable")
    k = np.zeros(M, bool); k[o[:int(round(f * M))]] = True
    p2, r2, _ = fg(k)
    o = np.argsort(-S_pg, kind="stable")
    k = np.zeros(M, bool); k[o[:int(round(f * M))]] = True
    p3, r3, _ = fg(k)
    print(f"  f={f:<5} random {np.mean(ps):.4f}/{np.mean(rs):.4f}   "
          f"overall {p2:.4f}/{r2:.4f}   puregeom {p3:.4f}/{r3:.4f}")

print("\nreference operating points on lego:")
print("  all de-floatered gaussians (f=1)      %.4f/%.4f/%d" % h.evaluate(X))
cand = np.where(st["s_crease"] > 0.05)[0]
sel = nms_along_e1(X, cand, st["s_crease"], st["e1"], st["knn"])
print("  canonical K=8 pool                    %.4f/%.4f/%d" % h.evaluate(X[sel]))
ps, rs, ns = h.evaluate(X[sel], per_view=True)
print("    per-view: " + "  ".join(f"v{v}: p={p:.4f} r={r:.4f} n={n}"
                                   for v, p, r, n in zip(h.views, ps, rs, ns)))
ps, rs, ns = h.evaluate(X, per_view=True)
print("    all f=1 per-view: " + "  ".join(f"v{v}: p={p:.4f} r={r:.4f} n={n}"
                                           for v, p, r, n in zip(h.views, ps, rs, ns)))
# oracle bound on lego
dmin = np.full(M, np.inf)
for v in h.views:
    vm, uv, _ = visibility.visible_mask(X, h.cams[v], h.gbufs[v]["depth"])
    u = np.clip(np.round(uv[:, 0]).astype(int), 0, h.cams[v].W - 1)
    w = np.clip(np.round(uv[:, 1]).astype(int), 0, h.cams[v].H - 1)
    _, _, cdt = h.crease[v]
    dmin = np.where(vm, np.minimum(dmin, cdt[w, u]), dmin)
o = np.argsort(np.nan_to_num(dmin, posinf=1e6), kind="stable")
print("\n  ORACLE upper bound on lego (all gaussians):")
for f in (0.6, 0.5, 0.4, 0.3, 0.2):
    k = np.zeros(M, bool); k[o[:int(round(f * M))]] = True
    print(f"    f={f}: %.4f/%.4f" % fg(k)[:2])
