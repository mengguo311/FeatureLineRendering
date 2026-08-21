"""gline sweep v2: fast AUC over v1+v2 features and their fusions, then the real gate.
EVAL-SIDE (uses h.crease for ANALYSIS of score power only)."""
import os
import sys
import time
import numpy as np
from scipy.stats import rankdata

sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
from tune_lib import Harness, structure_tensor, nms_along_e1  # noqa: E402
from src import visibility  # noqa: E402

CACHE = os.path.expanduser("~/3dgs_line/tier1/cache/gline")
FS = [1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2]


def auc(s, y):
    r = rankdata(s)
    n1 = int(y.sum())
    n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return float("nan")
    return float((r[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def agg(A, vis, how):
    B = np.where(vis, A.astype(np.float64), np.nan)
    with np.errstate(all="ignore"):
        if how == "mean":
            o = np.nanmean(B, 0)
        elif how == "med":
            o = np.nanmedian(B, 0)
        elif how.startswith("q"):
            o = np.nanquantile(B, float(how[1:]) / 100.0, 0)
        elif how == "trim":
            a = np.nanquantile(B, 0.2, 0)
            b = np.nanquantile(B, 0.8, 0)
            o = np.nanmean(np.where((B >= a) & (B <= b), B, np.nan), 0)
        else:
            raise ValueError(how)
    return np.nan_to_num(o, nan=0.0)


def pv_rank(A, vis):
    """per-view rank-normalise each field within the VISIBLE seeds of that view."""
    O = np.zeros_like(A, dtype=np.float64)
    for i in range(A.shape[0]):
        m = vis[i]
        if m.sum() > 1:
            O[i, m] = (rankdata(A[i, m]) - 0.5) / m.sum()
    return O


def gate(h, P, s, M, fs=FS):
    out = []
    order = np.argsort(-s, kind="mergesort")
    for f in fs:
        keep = np.zeros(M, bool)
        keep[order[:int(f * M)]] = True
        p, r, n = h.evaluate(P, extra_mask=keep)
        out.append((f, p, r, n))
    return out


def fmt(rows):
    return "  ".join(f"f={f:.1f}:{p:.3f}/{r:.3f}" for f, p, r, _ in rows)


def main():
    t0 = time.time()
    z1 = np.load(os.path.join(CACHE, "feat_chair_s8.npz"))
    z2 = np.load(os.path.join(CACHE, "feat2_chair_s8.npz"))
    sel = z2["sel"]
    vis = z2["vis"]
    M = len(sel)

    h = Harness("chair")
    st = structure_tensor(h.X, h.N, 8)
    cand = np.where(st["s_crease"] > 0.05)[0]
    assert np.array_equal(sel, nms_along_e1(h.X, cand, st["s_crease"], st["e1"], st["knn"]))
    P = h.X[sel]
    base = h.evaluate(P)
    print(f"[{time.time()-t0:.1f}s] baseline {base}")

    # ---- EVAL-ONLY label ----
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
    print(f"label: near={near.sum()} vis_eval={vis_eval.sum()} rate={ye.mean():.3f}")

    # oracle upper bound reference
    orc = -dmin
    print("ORACLE  ", fmt(gate(h, P, orc, M)))

    # ---- assemble raw per-view fields ----
    fields = {}
    for k in ["talign", "coh", "ngrad0", "ngrad3", "carea", "gmag0", "kappa3", "fgfrac",
              "dihed2", "dihed3", "dihed5", "dstep2", "dstep3", "dstep5"]:
        fields[k] = z2[k]
    for k in ["nang_sd_p3", "nang_sd_p5", "nang_p5", "kappa_p5", "gmag_p3"]:
        fields[k] = z1[f"raw_{k}"]
    fields["carea_log"] = np.log1p(fields["carea"])

    # per-view rank normalised versions
    rk = {k: pv_rank(v, vis) for k, v in fields.items()}

    scores = {}
    for k, A in fields.items():
        for how in ["mean", "med", "q10", "q25", "trim"]:
            scores[f"{k}|raw|{how}"] = agg(A, vis, how)
            scores[f"{k}|rk|{how}"] = agg(rk[k], vis, how)
    print(f"[{time.time()-t0:.1f}s] {len(scores)} single scores built")

    res = sorted(((k, auc(v[vis_eval], ye)) for k, v in scores.items()), key=lambda r: -r[1])
    print("\n=== TOP single-field AUC (visible-in-eval subset) ===")
    for k, a in res[:25]:
        print(f"  {a:.4f}  {k}")
    print("=== BOTTOM (inverted signals) ===")
    for k, a in res[-10:]:
        print(f"  {a:.4f}  {k}")

    np.savez(os.path.join(CACHE, "sweep2_scores.npz"),
             **{k.replace("|", "__"): v for k, v in scores.items()},
             near=near, vis_eval=vis_eval, dmin=dmin)
    print(f"[{time.time()-t0:.1f}s] saved")


if __name__ == "__main__":
    main()
