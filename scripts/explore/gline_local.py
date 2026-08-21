"""gline round 3: v3 ridge features + the local-vs-global decomposition test.
EVAL-SIDE."""
import os
import sys
import time
import itertools
import numpy as np
from scipy.stats import rankdata
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
from tune_lib import Harness, structure_tensor, nms_along_e1  # noqa: E402
from src import visibility  # noqa: E402
from gline_fuse import fast_agg, gnorm, auc, gate, fmt  # noqa: E402

CACHE = os.path.expanduser("~/3dgs_line/tier1/cache/gline")


def strat_auc(s, y, cell):
    """AUC pooled within cells (Mann-Whitney within each cell, n1*n0 weighted)."""
    num = den = 0.0
    for c in np.unique(cell):
        m = cell == c
        yy = y[m]
        n1 = int(yy.sum())
        n0 = int(len(yy) - n1)
        if n1 == 0 or n0 == 0:
            continue
        r = rankdata(s[m])
        a = (r[yy].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0)
        num += a * n1 * n0
        den += n1 * n0
    return num / den, den


def local_rank(P, s, k=48, tree=None):
    tree = tree or cKDTree(P)
    _, nb = tree.query(P, k=k + 1)
    nb = nb[:, 1:]
    return (s[:, None] > s[nb]).mean(1)


def main():
    t0 = time.time()
    z1 = np.load(os.path.join(CACHE, "feat_chair_s8.npz"))
    z2 = np.load(os.path.join(CACHE, "feat2_chair_s8.npz"))
    z3 = np.load(os.path.join(CACHE, "feat3_chair_s8.npz"))
    sel, vis = z2["sel"], z2["vis"]
    M = len(sel)
    h = Harness("chair")
    st = structure_tensor(h.X, h.N, 8)
    cand = np.where(st["s_crease"] > 0.05)[0]
    assert np.array_equal(sel, nms_along_e1(h.X, cand, st["s_crease"], st["e1"], st["knn"]))
    P = h.X[sel]

    near = np.zeros(M, bool)
    vis_eval = np.zeros(M, bool)
    dmin = np.full(M, 1e9)
    for v in h.views:
        vv, uv, _ = visibility.visible_mask(P, h.cams[v], h.gbufs[v]["depth"])
        u = np.clip(np.round(uv[:, 0]).astype(int), 0, 799)
        w = np.clip(np.round(uv[:, 1]).astype(int), 0, 799)
        cdt = h.crease[v][2]
        near |= vv & (cdt[w, u] <= 2.5)
        dmin = np.where(vv, np.minimum(dmin, cdt[w, u]), dmin)
        vis_eval |= vv
    ye = near[vis_eval]

    # ---- v3 single features ----
    print("=== v3 ridge features ===")
    v3 = {"nridge_off": -z3["ridge_off"], "ridge_val": z3["ridge_val"],
          "nridge_dt": -z3["ridge_dt"], "ngdt": -z3["gdt"], "gdt": z3["gdt"],
          "ngrad_at": z3["ngrad_at"]}
    v3s = {}
    for k, A in v3.items():
        for how in ["mean", "q10", "q25", "trim"]:
            s = fast_agg(A, vis, how)
            v3s[f"{k}|{how}"] = s
            print(f"  {auc(s[vis_eval], ye):.4f}  {k}|{how}")

    terms = {
        "crease": gnorm(fast_agg(z1["raw_nang_sd_p5"], vis, "q10")),
        "dihed": gnorm(fast_agg(z2["dihed2"], vis, "trim")),
        "nogmag": gnorm(-fast_agg(z1["raw_gmag_p3"], vis, "trim")),
        "nridge_off": gnorm(fast_agg(-z3["ridge_off"], vis, "trim")),
        "nridge_dt": gnorm(fast_agg(-z3["ridge_dt"], vis, "trim")),
        "ngdt": gnorm(fast_agg(z3["gdt"], vis, "trim")),
        "ridge_val": gnorm(fast_agg(z3["ridge_val"], vis, "trim")),
    }
    print("\n=== term AUCs ===")
    for k, v in terms.items():
        print(f"  {auc(v[vis_eval], ye):.4f}  {k}")

    print("\n=== fusions incl. v3 ===")
    keys = list(terms)
    fus = {}
    for r in (2, 3, 4):
        for c in itertools.combinations(keys, r):
            fus["+".join(c)] = sum(terms[x] for x in c) / r
    fr = sorted(((k, auc(v[vis_eval], ye)) for k, v in fus.items()), key=lambda x: -x[1])
    for k, a in fr[:12]:
        print(f"  {a:.4f}  {k}")
    best = fus[fr[0][0]]

    # weight search over all 7 terms (coarse random search) -- NOTE: fitted on the
    # eval label, so the resulting AUC is an optimistic in-sample number.
    rng = np.random.RandomState(0)
    T = np.stack([terms[k] for k in keys])
    bw, ba = None, -1
    for _ in range(400):
        w = rng.rand(len(keys))
        w[rng.rand(len(keys)) < 0.4] = 0
        if w.sum() == 0:
            continue
        s = (w[:, None] * T).sum(0)
        a = auc(s[vis_eval], ye)
        if a > ba:
            bw, ba = w, a
    wbest = (bw[:, None] * T).sum(0)
    print(f"\n  random weight search best AUC {ba:.4f}  w=" +
          ", ".join(f"{k}:{v:.2f}" for k, v in zip(keys, bw)))

    # ---------------- local vs global decomposition ----------------
    print("\n=== LOCAL vs GLOBAL decomposition ===")
    lo = P.min(0)
    hi = P.max(0)
    for nb_ in (8, 16, 32):
        cell_ijk = np.clip(((P - lo) / (hi - lo + 1e-12) * nb_).astype(int), 0, nb_ - 1)
        cell = cell_ijk[:, 0] * nb_ * nb_ + cell_ijk[:, 1] * nb_ + cell_ijk[:, 2]
        for name, s in (("crease", terms["crease"]), ("best_fus", best),
                        ("wbest", wbest)):
            g = auc(s[vis_eval], ye)
            a, den = strat_auc(s[vis_eval], ye, cell[vis_eval])
            print(f"  grid{nb_:3d}  {name:9s} global AUC={g:.4f}  within-cell AUC={a:.4f}"
                  f"  (pairs={den:.3g}, ncells={len(np.unique(cell))})")

    # ---------------- local rank normalisation ----------------
    print("\n=== local-rank normalised scores (mesh-free) ===")
    tree = cKDTree(P)
    out = {}
    for name, s in (("crease", terms["crease"]), ("best_fus", best), ("wbest", wbest)):
        for k in (24, 48, 96):
            lr = local_rank(P, s, k=k, tree=tree)
            out[f"{name}_lr{k}"] = lr
            for mix in (0.0, 0.5, 1.0):
                sm = lr + mix * gnorm(s)
                out[f"{name}_lr{k}_mix{mix}"] = sm
    for k, s in sorted(out.items()):
        print(f"  {auc(s[vis_eval], ye):.4f}  {k}")

    print("\n=== GATE (best candidates) ===")
    show = {"ORACLE": -dmin, "wbest": wbest, "best_fus": best}
    top_lr = sorted(out.items(), key=lambda kv: -auc(kv[1][vis_eval], ye))[:4]
    show.update(dict(top_lr))
    for k, s in show.items():
        print(f"  {k:28s} AUC={auc(s[vis_eval], ye):.4f}  " + fmt(gate(h, P, s, M)))
    np.savez(os.path.join(CACHE, "local_out.npz"), wbest=wbest, keys=np.array(keys),
             w=bw, near=near, vis_eval=vis_eval)
    print(f"[{time.time()-t0:.1f}s] done")


if __name__ == "__main__":
    main()
