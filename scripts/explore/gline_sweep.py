"""Sweep of the `gline` family: rank candidate mesh-free scores by AUC, then run the
real gate (h.evaluate) on the best ones.  EVAL-SIDE script -> may use h.crease for
ANALYSIS only; nothing here feeds back into the score definitions.
"""
import os
import sys
import time
import numpy as np

sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
from tune_lib import Harness, structure_tensor, nms_along_e1  # noqa: E402
from src import visibility  # noqa: E402

CACHE = os.path.expanduser("~/3dgs_line/tier1/cache/gline")
NQ = 101
FS = [1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2]


def auc(score, label):
    s = np.asarray(score, float)
    y = np.asarray(label, bool)
    if y.all() or (~y).any() == 0:
        return float("nan")
    r = np.empty(len(s))
    order = np.argsort(s, kind="mergesort")
    sr = s[order]
    # average ranks for ties
    r_sorted = np.arange(1, len(s) + 1, dtype=float)
    i = 0
    while i < len(sr):
        j = i
        while j + 1 < len(sr) and sr[j + 1] == sr[i]:
            j += 1
        r_sorted[i:j + 1] = 0.5 * (i + 1 + j + 1)
        i = j + 1
    r[order] = r_sorted
    n1 = y.sum()
    n0 = len(y) - n1
    return float((r[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def rank_norm(vals, qq):
    """per-view empirical CDF of the foreground distribution."""
    q = np.maximum.accumulate(qq.astype(np.float64)) + np.arange(len(qq)) * 1e-9
    return np.interp(vals, q, np.linspace(0.0, 1.0, len(qq)))


def robust_z(vals, qq):
    med = qq[NQ // 2]
    iqr = max(float(qq[75] - qq[25]), 1e-6)
    return (vals - med) / iqr


class Agg:
    """aggregate a [V,M] value array over views where the seed is visible."""

    def __init__(self, vis):
        self.vis = vis
        self.nv = vis.sum(0)

    def _masked(self, A, fill):
        return np.where(self.vis, A, fill)

    def mean(self, A):
        s = np.where(self.vis, A, 0.0).sum(0)
        return s / np.maximum(self.nv, 1)

    def quant(self, A, q):
        B = self._masked(A, np.nan)
        with np.errstate(all="ignore"):
            out = np.nanquantile(B, q, axis=0)
        return np.nan_to_num(out, nan=0.0)

    def trimmed(self, A, lo=0.2, hi=0.8):
        B = self._masked(A, np.nan)
        with np.errstate(all="ignore"):
            a = np.nanquantile(B, lo, axis=0)
            b = np.nanquantile(B, hi, axis=0)
        C = np.where((B >= a[None]) & (B <= b[None]), B, np.nan)
        with np.errstate(all="ignore"):
            out = np.nanmean(C, axis=0)
        return np.nan_to_num(out, nan=0.0)

    def frac_above(self, A, t):
        s = np.where(self.vis & (A > t), 1.0, 0.0).sum(0)
        return s / np.maximum(self.nv, 1)


def main():
    t0 = time.time()
    z = np.load(os.path.join(CACHE, "feat_chair_s8.npz"))
    views = z["views"]
    sel = z["sel"]
    vis = z["vis"] & z["inb"]
    M = len(sel)
    V = len(views)

    h = Harness("chair")
    st = structure_tensor(h.X, h.N, 8)
    cand = np.where(st["s_crease"] > 0.05)[0]
    sel2 = nms_along_e1(h.X, cand, st["s_crease"], st["e1"], st["knn"])
    assert np.array_equal(sel, sel2)
    P = h.X[sel]
    print(f"[{time.time()-t0:.1f}s] baseline:", h.evaluate(P))

    # ---------- EVAL-ONLY label for AUC analysis ----------
    near = np.zeros(M, bool)
    vis_eval = np.zeros(M, bool)
    for v in h.views:
        vv, uv, _ = visibility.visible_mask(P, h.cams[v], h.gbufs[v]["depth"])
        u = np.clip(np.round(uv[:, 0]).astype(int), 0, 799)
        w = np.clip(np.round(uv[:, 1]).astype(int), 0, 799)
        cdt = h.crease[v][2]
        near |= vv & (cdt[w, u] <= 2.5)
        vis_eval |= vv
    print(f"label: {near.sum()} near-crease / {vis_eval.sum()} visible in >=1 eval view "
          f"(of {M}); base rate among visible = {near[vis_eval].mean():.3f}")

    A = Agg(vis)
    nv = vis.sum(0)
    print("seeds visible in 0 views:", int((nv == 0).sum()),
          " median #views visible:", float(np.median(nv)))

    # ---------- build candidate scores ----------
    scores = {}
    names = ["gmag", "kappa", "nang", "nang_sd"]
    modes = ["p0", "p3", "p5"]
    for n in names:
        qg = z[f"q_{n}"]
        for m in modes:
            R = z[f"raw_{n}_{m}"]                       # [V,M]
            Rn = np.stack([rank_norm(R[i], qg[i]) for i in range(V)])
            Rz = np.stack([robust_z(R[i], qg[i]) for i in range(V)])
            for tag, X in (("raw", R), ("rk", Rn), ("rz", Rz)):
                b = f"{n}_{m}_{tag}"
                scores[b + "_mean"] = A.mean(X)
                scores[b + "_med"] = A.quant(X, 0.5)
                scores[b + "_trim"] = A.trimmed(X)
                scores[b + "_q25"] = A.quant(X, 0.25)
                scores[b + "_q10"] = A.quant(X, 0.10)
                scores[b + "_min"] = A.quant(X, 0.0)
            scores[f"{n}_{m}_fracrk50"] = A.frac_above(Rn, 0.50)
            scores[f"{n}_{m}_fracrk80"] = A.frac_above(Rn, 0.80)
            scores[f"{n}_{m}_fracrk90"] = A.frac_above(Rn, 0.90)
            scores[f"{n}_{m}_fracrk95"] = A.frac_above(Rn, 0.95)

    # thresholded-line-mask agreement: frac of visible views with linedt <= d
    ldt = z["linedt"]
    td, tn = z["tau_d"], z["tau_n"]
    j = 0
    for a in td:
        for b in tn:
            for d in (0.0, 1.0, 2.0, 3.0):
                scores[f"line_td{a}_tn{b}_d{int(d)}"] = A.frac_above(-ldt[j], -d - 1e-9)
            scores[f"linedt_td{a}_tn{b}_negmean"] = -A.mean(ldt[j])
            scores[f"linedt_td{a}_tn{b}_negq75"] = -A.quant(ldt[j], 0.75)
            j += 1

    # a few structural references (not gline, for calibration of "is 0.5 the norm?")
    scores["_ref_s_crease"] = st["s_crease"][sel]
    scores["_ref_nviews"] = nv.astype(float)
    scores["_ref_random"] = np.random.RandomState(0).rand(M)

    res = [(k, auc(v[vis_eval], near[vis_eval]), auc(v, near)) for k, v in scores.items()]
    res.sort(key=lambda r: -r[1])
    print(f"\n[{time.time()-t0:.1f}s] === AUC (restricted to seeds visible in an eval view) ===")
    for k, a1, a2 in res[:40]:
        print(f"  {a1:.4f}  (all {a2:.4f})  {k}")
    print("  ...")
    for k, a1, a2 in res[-8:]:
        print(f"  {a1:.4f}  (all {a2:.4f})  {k}")

    np.save(os.path.join(CACHE, "auc_table.npy"),
            np.array([(k, a1, a2) for k, a1, a2 in res], dtype=object), allow_pickle=True)

    # ---------- gate Pareto for the top scores ----------
    print(f"\n[{time.time()-t0:.1f}s] === GATE PARETO ===")
    top = [k for k, _, _ in res[:8]] + ["_ref_s_crease", "_ref_random"]
    for k in top:
        s = scores[k]
        line = []
        for f in FS:
            keep = np.zeros(M, bool)
            keep[np.argsort(-s, kind="mergesort")[:int(f * M)]] = True
            p, r, n = h.evaluate(P, extra_mask=keep)
            line.append(f"f={f:.1f}:{p:.3f}/{r:.3f}")
        print(f"  {k:44s} " + "  ".join(line))
    print(f"[{time.time()-t0:.1f}s] done")


if __name__ == "__main__":
    main()
