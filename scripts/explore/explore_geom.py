"""EVAL-SIDE exploration for the `geom` family. Uses the oracle ONLY for analysis
(AUC / Pareto), never inside a proposed score.
"""
import os
import sys
import time
import numpy as np

sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tune_lib import Harness, structure_tensor, nms_along_e1
from src import visibility
from _geom_feats import compute_all

SCRATCH = os.path.expanduser(
    "/tmp/claude-1026/-home-u00134-3dgs-line/4ee6144a-2815-4286-bec9-0a63623a57f6/scratchpad")
os.makedirs(SCRATCH, exist_ok=True)
FS = [1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2]


def auc(score, y):
    """rank AUC, higher score should mean y==1."""
    y = np.asarray(y, bool)
    n1, n0 = int(y.sum()), int((~y).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    order = np.argsort(score, kind="mergesort")
    r = np.empty(len(score))
    s = score[order]
    # average ranks for ties
    ranks = np.arange(1, len(score) + 1, dtype=float)
    i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and s[j + 1] == s[i]:
            j += 1
        ranks[i:j + 1] = ranks[i:j + 1].mean()
        i = j + 1
    r[order] = ranks
    return (r[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0)


def labels(h, P):
    """EVAL ONLY. Returns (near_any, vis_any, near_cnt, vis_cnt) per seed."""
    near = np.zeros(len(P), bool)
    visa = np.zeros(len(P), bool)
    ncnt = np.zeros(len(P), int)
    vcnt = np.zeros(len(P), int)
    for v in h.views:
        vis, uv, _ = visibility.visible_mask(P, h.cams[v], h.gbufs[v]["depth"])
        u = np.round(uv[:, 0]).astype(int)
        w = np.round(uv[:, 1]).astype(int)
        inb = (u >= 0) & (u < 800) & (w >= 0) & (w < 800)
        ok = vis & inb
        cu, cv_, cdt = h.crease[v]
        d = np.full(len(P), np.inf)
        d[ok] = cdt[w[ok], u[ok]]
        visa |= ok
        vcnt += ok
        nn = ok & (d <= 2.5)
        near |= nn
        ncnt += nn
    return near, visa, ncnt, vcnt


def sweep(h, P, score, fs=FS):
    out = []
    order = np.argsort(-score, kind="mergesort")
    for f in fs:
        keep = np.zeros(len(P), bool)
        keep[order[:int(round(f * len(P)))]] = True
        p, r, nvis = h.evaluate(P, extra_mask=keep)
        out.append((f, p, r, nvis))
    return out


def main():
    t0 = time.time()
    h = Harness("chair")
    print(f"harness {time.time()-t0:.1f}s  N={len(h.X)}")
    st = structure_tensor(h.X, h.N, 8)
    cand = np.where(st["s_crease"] > 0.05)[0]
    sel = nms_along_e1(h.X, cand, st["s_crease"], st["e1"], st["knn"])
    P = h.X[sel]
    print("pool", len(sel), "baseline", h.evaluate(P))

    t = time.time()
    F = compute_all(h, st)
    print(f"features {time.time()-t:.1f}s  n={len(F)}")

    near, visa, ncnt, vcnt = labels(h, P)
    print(f"seeds vis_any={visa.sum()}  near_any={near.sum()} "
          f"({near.sum()/max(visa.sum(),1):.3f} of visible)")

    rows = []
    for name, arr in F.items():
        s = np.asarray(arr, float)[sel]
        a_all = auc(s, near)
        a_vis = auc(s[visa], near[visa])
        rows.append((name, a_all, a_vis))
    rows.sort(key=lambda r: -max(r[2], 1 - r[2]))
    print("\n=== single-feature AUC (label = within 2.5px of GT crease in >=1 view) ===")
    print(f"{'feature':22s} {'AUC_all':>8s} {'AUC_vis':>8s}")
    for name, a_all, a_vis in rows:
        print(f"{name:22s} {a_all:8.3f} {a_vis:8.3f}")

    np.savez(os.path.join(SCRATCH, "geom_feats.npz"),
             sel=sel, near=near, visa=visa, ncnt=ncnt, vcnt=vcnt,
             **{k: np.asarray(v, float) for k, v in F.items()})
    print("saved", os.path.join(SCRATCH, "geom_feats.npz"))

    # sweep the top few singles (both polarities)
    print("\n=== Pareto sweep of top singles ===")
    for name, a_all, a_vis in rows[:8]:
        s = np.asarray(F[name], float)[sel]
        if a_vis < 0.5:
            s = -s
            name = "-" + name
        res = sweep(h, P, s)
        print(name, " ".join(f"f{f:.1f}:{p:.3f}/{r:.3f}" for f, p, r, _ in res))
    print(f"total {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
