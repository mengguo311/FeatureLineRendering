import os, sys, time, itertools, numpy as np
from scipy.stats import rankdata
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts/explore/syn"))
from cache_scores import build
from fastgate import FastGate

OUT = os.path.expanduser("~/3dgs_line/tier1/scripts/explore/syn")
h, st, sel = build("chair")
fg = FastGate(h, sel)
z = dict(np.load(os.path.join(OUT, "scores_chair.npz")))
pos, visany = z["lab_pos"], z["lab_vis"]
M = len(sel)

CAND = ["dt", "view", "view_negmed", "gline", "gline_crease", "gline_dihed",
        "gline_nogmag", "geom", "geom_aucbest", "geom_dih", "geom_nbopa",
        "geom_seeddens", "pool", "pool_dens", "pool_l1", "neigh", "neigh_smdih"]
PHOTO = {"dt"}
R = {k: rankdata(z[k]) / M for k in CAND}


def auc(s):
    r = rankdata(s[visany]); y = pos[visany]
    n1 = y.sum(); n0 = len(y) - n1
    return (r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


FGRID = np.arange(0.15, 0.85, 0.01)


def best_point(s, rec_min=0.72):
    order = np.argsort(-s, kind="stable")
    best = None
    for f in FGRID:
        keep = np.zeros(M, bool); keep[order[:int(round(f * M))]] = True
        p, r, n = fg(keep)
        if r >= rec_min and (best is None or p > best[0]):
            best = (p, r, f, n)
    return best


def pareto(s, fs=(1.0, .8, .6, .5, .4, .3, .2)):
    order = np.argsort(-s, kind="stable"); out = []
    for f in fs:
        keep = np.zeros(M, bool); keep[order[:int(round(f * M))]] = True
        out.append(fg(keep)[:2])
    return out


W = [0.0, 0.5, 1.0, 1.5, 2.0]
res = []
t0 = time.time()
# singles
for k in CAND:
    b = best_point(R[k])
    if b: res.append((b[0], b[1], b[2], (k,), (1.0,), auc(R[k])))
# pairs
for a, b in itertools.combinations(CAND, 2):
    for wb in [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]:
        s = R[a] + wb * R[b]
        bp = best_point(s)
        if bp: res.append((bp[0], bp[1], bp[2], (a, b), (1.0, wb), auc(s)))
print("pairs done %.1fs, %d combos" % (time.time() - t0, len(res)), flush=True)
res.sort(key=lambda r: -r[0])
print("\n=== TOP 25 pairs/singles (max precision s.t. recall>=0.72) ===")
for r in res[:25]:
    print(f"  p={r[0]:.3f} rec={r[1]:.3f} f={r[2]:.2f} AUC={r[5]:.3f}  {r[3]} w={r[4]}")
print("\n=== TOP 12 PURE-GEOMETRY (no photographs) ===")
n = 0
for r in res:
    if not (set(r[3]) & PHOTO):
        print(f"  p={r[0]:.3f} rec={r[1]:.3f} f={r[2]:.2f} AUC={r[5]:.3f}  {r[3]} w={r[4]}")
        n += 1
        if n >= 12: break

# triples: restrict to top families
TOP = ["dt", "view", "view_negmed", "gline", "gline_dihed", "geom", "geom_aucbest",
       "geom_nbopa", "pool", "neigh_smdih", "gline_crease", "geom_dih"]
res3 = []
t0 = time.time()
for a, b, c in itertools.combinations(TOP, 3):
    for wb in [0.5, 1.0, 1.5]:
        for wc in [0.25, 0.5, 1.0]:
            s = R[a] + wb * R[b] + wc * R[c]
            bp = best_point(s)
            if bp: res3.append((bp[0], bp[1], bp[2], (a, b, c), (1.0, wb, wc), auc(s)))
print("\ntriples done %.1fs, %d combos" % (time.time() - t0, len(res3)), flush=True)
res3.sort(key=lambda r: -r[0])
print("=== TOP 20 triples ===")
for r in res3[:20]:
    print(f"  p={r[0]:.3f} rec={r[1]:.3f} f={r[2]:.2f} AUC={r[5]:.3f}  {r[3]} w={r[4]}")
print("=== TOP 12 PURE-GEOMETRY triples ===")
n = 0
for r in res3:
    if not (set(r[3]) & PHOTO):
        print(f"  p={r[0]:.3f} rec={r[1]:.3f} f={r[2]:.2f} AUC={r[5]:.3f}  {r[3]} w={r[4]}")
        n += 1
        if n >= 12: break
