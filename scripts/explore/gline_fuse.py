"""gline fusion + failure diagnostics.  EVAL-SIDE."""
import os
import sys
import time
import itertools
import numpy as np
import cv2
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
    return float((r[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def fast_agg(A, vis, how):
    """A[V,M] -> [M]; aggregate over views where vis. Sort-based, no apply_along_axis."""
    B = np.where(vis, A.astype(np.float32), np.inf)
    S = np.sort(B, axis=0)                       # valid values first, inf padding after
    n = vis.sum(0)
    V, M = A.shape
    idx = np.arange(M)
    out = np.zeros(M, np.float64)
    ok = n > 0
    if how == "mean":
        out[ok] = (np.where(vis, A, 0.0).sum(0)[ok] / n[ok])
        return out
    if how.startswith("q"):
        q = float(how[1:]) / 100.0
        pos = np.clip((np.ceil(q * (n - 1))).astype(int), 0, V - 1)
        out[ok] = S[pos[ok], idx[ok]]
        return out
    if how == "trim":
        lo = np.clip((np.ceil(0.2 * (n - 1))).astype(int), 0, V - 1)
        hi = np.clip((np.floor(0.8 * (n - 1))).astype(int), 0, V - 1)
        ar = np.arange(V)[:, None]
        m = (ar >= lo[None]) & (ar <= hi[None]) & np.isfinite(S)
        cnt = m.sum(0)
        out[cnt > 0] = (np.where(m, S, 0.0).sum(0)[cnt > 0] / cnt[cnt > 0])
        return out
    raise ValueError(how)


def gnorm(s):
    return (rankdata(s) - 0.5) / len(s)


def gate(h, P, s, M, fs=FS):
    order = np.argsort(-s, kind="mergesort")
    out = []
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
    sel, vis = z2["sel"], z2["vis"]
    M = len(sel)

    h = Harness("chair")
    st = structure_tensor(h.X, h.N, 8)
    cand = np.where(st["s_crease"] > 0.05)[0]
    assert np.array_equal(sel, nms_along_e1(h.X, cand, st["s_crease"], st["e1"], st["knn"]))
    P = h.X[sel]
    print(f"[{time.time()-t0:.1f}s] baseline {h.evaluate(P)}")

    near = np.zeros(M, bool)
    vis_eval = np.zeros(M, bool)
    dmin = np.full(M, 1e9)
    uvs = {}
    for v in h.views:
        vv, uv, _ = visibility.visible_mask(P, h.cams[v], h.gbufs[v]["depth"])
        u = np.clip(np.round(uv[:, 0]).astype(int), 0, 799)
        w = np.clip(np.round(uv[:, 1]).astype(int), 0, 799)
        cdt = h.crease[v][2]
        near |= vv & (cdt[w, u] <= 2.5)
        dmin = np.where(vv, np.minimum(dmin, cdt[w, u]), dmin)
        vis_eval |= vv
        uvs[v] = (vv, u, w)
    ye = near[vis_eval]

    fields = {k: z2[k] for k in ["talign", "coh", "ngrad0", "ngrad3", "carea", "gmag0",
                                 "kappa3", "fgfrac", "dihed2", "dihed3", "dihed5",
                                 "dstep2", "dstep3", "dstep5"]}
    fields["carea_log"] = np.log1p(fields["carea"])
    for k in ["nang_sd_p3", "nang_sd_p5", "nang_p5", "kappa_p5", "gmag_p3", "nang_sd_p0"]:
        fields[k] = z1[f"raw_{k}"]
    ldt = z1["linedt"]
    td, tn = z1["tau_d"], z1["tau_n"]
    j = 0
    for a in td:
        for b in tn:
            fields[f"nlinedt_{a}_{b}"] = -ldt[j]
            j += 1

    print(f"\n=== ALL single-field AUC (agg over visible views) ===")
    singles = {}
    rows = []
    for k, A in fields.items():
        for how in ["mean", "q10", "q25", "trim"]:
            s = fast_agg(A, vis, how)
            singles[f"{k}|{how}"] = s
            rows.append((f"{k}|{how}", auc(s[vis_eval], ye)))
    rows.sort(key=lambda r: -r[1])
    for k, a in rows:
        print(f"  {a:.4f}  {k}")

    # ---------------- fusion ----------------
    base_terms = {
        "crease": gnorm(fast_agg(fields["nang_sd_p5"], vis, "q10")),
        "dihed": gnorm(fast_agg(fields["dihed2"], vis, "trim")),
        "nogmag": gnorm(-fast_agg(fields["gmag_p3"], vis, "trim")),
        "nodstep": gnorm(-fast_agg(fields["dstep3"], vis, "trim")),
        "coh": gnorm(fast_agg(fields["coh"], vis, "trim")),
        "talign": gnorm(fast_agg(fields["talign"], vis, "trim")),
        "carea": gnorm(fast_agg(fields["carea_log"], vis, "trim")),
        "line": gnorm(fast_agg(fields["nlinedt_0.1_1.0"], vis, "trim")),
        "s_crease": gnorm(st["s_crease"][sel]),
    }
    print(f"\n=== fusion term AUCs ===")
    for k, v in base_terms.items():
        print(f"  {auc(v[vis_eval], ye):.4f}  {k}")

    print(f"\n=== pair / triple fusions (equal weight rank-sum) ===")
    keys = list(base_terms)
    fus = {}
    for r in (2, 3):
        for combo in itertools.combinations(keys, r):
            s = sum(base_terms[c] for c in combo) / r
            fus["+".join(combo)] = s
    fr = sorted(((k, auc(v[vis_eval], ye)) for k, v in fus.items()), key=lambda x: -x[1])
    for k, a in fr[:15]:
        print(f"  {a:.4f}  {k}")

    # weight grid on the best triple
    best_triple = fr[0][0].split("+")
    print(f"\n=== weight grid on {best_triple} ===")
    bw, ba, bs = None, -1, None
    grid = [0, 0.25, 0.5, 0.75, 1.0, 1.5]
    for w in itertools.product(grid, repeat=len(best_triple)):
        if sum(w) == 0:
            continue
        s = sum(wi * base_terms[c] for wi, c in zip(w, best_triple))
        a = auc(s[vis_eval], ye)
        if a > ba:
            bw, ba, bs = w, a, s
    print(f"  best weights {bw} AUC {ba:.4f}")

    # full-term weight search (coarse, greedy forward selection)
    print(f"\n=== greedy forward selection over all terms ===")
    cur = np.zeros(M)
    chosen = []
    for step in range(5):
        bk, bva, bvs = None, -1, None
        for k in keys:
            if k in chosen:
                continue
            for w in (0.5, 1.0):
                s = cur + w * base_terms[k]
                a = auc(s[vis_eval], ye)
                if a > bva:
                    bk, bva, bvs, bw2 = k, a, s, w
        if bva <= auc(cur[vis_eval], ye) + 1e-4 and step > 0:
            break
        chosen.append(bk)
        cur = bvs
        print(f"  + {bk} (w={bw2}) -> AUC {bva:.4f}")
    greedy = cur

    # ---------------- gate ----------------
    print(f"\n=== GATE ===")
    orc = -dmin
    cands = {"ORACLE(-dmin)": orc,
             "s_crease": base_terms["s_crease"],
             "random": np.random.RandomState(0).rand(M),
             "crease(nang_sd q10)": base_terms["crease"],
             "best_pair": fus[fr[0][0]] if "+" in fr[0][0] else None,
             "best_weighted": bs,
             "greedy": greedy}
    for k in [x[0] for x in fr[:3]]:
        cands[f"fus:{k}"] = fus[k]
    for k, s in cands.items():
        if s is None:
            continue
        print(f"  {k:34s} AUC={auc(s[vis_eval], ye):.4f}  " + fmt(gate(h, P, s, M)))

    # ---------------- diagnostics: why does recall collapse? ----------------
    print(f"\n=== DIAGNOSTIC: recall decomposition at f=0.3 ===")
    s = greedy
    order = np.argsort(-s, kind="mergesort")
    keep = np.zeros(M, bool)
    keep[order[:int(0.3 * M)]] = True
    rng = np.random.RandomState(1)
    n_true_kept = int((keep & near).sum())
    rand_true = np.zeros(M, bool)
    ti = np.where(near)[0]
    rand_true[rng.choice(ti, n_true_kept, replace=False)] = True
    for tag, m in (("all seeds", None), ("all TRUE seeds", near),
                   ("score-top30% ∩ TRUE", keep & near),
                   (f"random {n_true_kept} TRUE", rand_true),
                   ("score-top30% (as gated)", keep)):
        p, r, n = h.evaluate(P, extra_mask=m)
        cnt = M if m is None else int(m.sum())
        print(f"  {tag:28s} n={cnt:6d}  prec={p:.3f} rec={r:.3f}")

    # spatial clustering of the lost crease pixels
    print("\n  lost-crease-pixel contiguity (view, frac of lost px with >=4/8 lost nbrs):")
    for v in h.views:
        cu, cv_, _ = h.crease[v]
        vv, u, w = uvs[v]
        m_full = np.zeros((800, 800), bool)
        sel_f = vv
        m_full[w[sel_f], u[sel_f]] = True
        dt_full = cv2.distanceTransform((~m_full).astype(np.uint8), cv2.DIST_L2, 5)
        m_k = np.zeros((800, 800), bool)
        sel_k = vv & keep
        m_k[w[sel_k], u[sel_k]] = True
        dt_k = cv2.distanceTransform((~m_k).astype(np.uint8), cv2.DIST_L2, 5)
        cov_full = dt_full[cv_, cu] <= 3.0
        cov_k = dt_k[cv_, cu] <= 3.0
        lost = cov_full & ~cov_k
        cm = np.zeros((800, 800), np.uint8)
        cm[cv_[lost], cu[lost]] = 1
        allc = np.zeros((800, 800), np.uint8)
        allc[cv_, cu] = 1
        kern = np.ones((3, 3), np.uint8)
        kern[1, 1] = 0
        nb_lost = cv2.filter2D(cm, cv2.CV_32F, kern)
        contig = float((nb_lost[cv_[lost], cu[lost]] >= 4).mean()) if lost.any() else 0.0
        print(f"    v{v}: crease px={len(cu)} covered_full={cov_full.mean():.3f} "
              f"covered_top30={cov_k.mean():.3f} lost={lost.sum()} contiguity={contig:.3f}")

    np.savez(os.path.join(CACHE, "fuse_out.npz"), greedy=greedy, near=near,
             vis_eval=vis_eval, dmin=dmin, **{f"t_{k}": v for k, v in base_terms.items()})
    print(f"[{time.time()-t0:.1f}s] done")


if __name__ == "__main__":
    main()
