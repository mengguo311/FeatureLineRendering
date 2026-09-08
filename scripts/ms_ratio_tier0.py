#!/usr/bin/env python
"""MS-RATIO TIER-0 — is a multi-scale coarse/fine TEED ratio a BAND-SELECTIVE rank?

Mechanism under test: the 'ms' map is TEED at 0.64 scale (512px), i.e. COARSER than 'native'
(800px). At coarse scale a stud barrel's 12 longitudinal facet stripes blur into one smooth
cylinder, while a brick edge stays sharp. So ms/native should be HIGH on real brick geometry
and LOW on the tessellation family -- the same mechanism that makes tessellation invisible.

Harness is deliberately IDENTICAL to scripts/a_reframed_tier0.py so the AUCs are directly
comparable to that run's junction 0.7053 and TEED-seedscore 0.7271.

Two questions:
  (Q1) band discrimination           band90 vs band30, all near-crease carriers
  (Q2) RECOVERY-relevant version     same, restricted to NON-SEEDED (culled) carriers, plus
                                     the broader all-non-tessellation (theta>=30.05) contrast
Q2 is what "lifts non-tessellation-band culled recall" requires.

FROZEN GATE (orchestrator): GO iff the ms-ratio rank beats TEED seedscore AUC 0.7271 AND
lifts non-tessellation culled discrimination. NO-GO otherwise -> rank lever is 0-for-4.

VAL views only, so TEST stays untouched. Mesh EVAL-ONLY via banked caches. No pull.
"""
import json, os, sys

import numpy as np
from scipy.spatial import cKDTree

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
for p in (TIER1, os.path.join(TIER1, "scripts"), os.path.join(TIER1, "scripts/explore"),
          os.path.join(TIER1, "scripts/explore/syn")):
    if p not in sys.path:
        sys.path.insert(0, p)

from src import view_split, visibility            # noqa: E402
from tune_lib import Harness                      # noqa: E402

OUT = os.path.join(TIER1, "out")
SEED_AUC_REF = 0.7271           # banked A-reframed control
JUNCTION_REF = 0.7053           # banked A-reframed primary
EPS = 1e-6


def auc_mw(score, pos):
    s = np.asarray(score, np.float64); y = np.asarray(pos, bool)
    ok = np.isfinite(s); s, y = s[ok], y[ok]
    n1, n0 = int(y.sum()), int((~y).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    o = np.argsort(s, kind="stable"); r = np.empty(len(s)); r[o] = np.arange(len(s)) + 1.0
    sv = s[o]; i = 0
    while i < len(sv):
        j = i
        while j + 1 < len(sv) and sv[j + 1] == sv[i]:
            j += 1
        if j > i:
            r[o[i:j + 1]] = 0.5 * ((i + 1) + (j + 1))
        i = j + 1
    return float((r[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def main():
    gt = np.load(os.path.join(TIER1, "cache/dexp0_gt_lego_a30.npz"))
    cp = gt["crease_pts"]
    xz = np.load(os.path.join(OUT, "xy/xy_expX_lego_p1c.npz"))
    theta = np.full(len(cp), np.nan, np.float32)
    theta[xz["seen_idx"]] = xz["theta0_pt"]

    h = Harness("lego", views=view_split.VAL)
    X = h.X
    sp = float(np.median(cKDTree(X).query(X, k=2)[0][:, 1]))
    d3, i3 = cKDTree(cp).query(X, workers=-1)
    th = theta[i3]
    near = d3 <= sp
    b90 = near & (th >= 89.95) & (th < 90.05)
    b30 = near & (th >= 30.00) & (th < 30.05)
    nontess = near & (th >= 30.05)

    seed = np.load(os.path.join(TIER1, "scripts/explore/syn",
                                "finalscore_overall_lego__teed_native_0.5.npy"))
    k = int(round(0.40 * len(X)))
    is_seed = np.zeros(len(X), bool); is_seed[np.argsort(-seed, kind="stable")[:k]] = True
    print(f"pool={len(X)} spacing={sp:.6f} seeds={k}")
    print(f"near-crease={int(near.sum())}  band90={int(b90.sum())}  band30={int(b30.sum())}  "
          f"nontess={int(nontess.sum())}")
    print(f"NON-SEEDED: band90={int((b90&~is_seed).sum())} band30={int((b30&~is_seed).sum())} "
          f"nontess={int((nontess&~is_seed).sum())}", flush=True)

    accn = np.zeros(len(X)); accm = np.zeros(len(X)); cnt = np.zeros(len(X))
    for v in view_split.VAL:
        z = np.load(os.path.join(OUT, f"teed_edges_lego/v{v:03d}.npz"))
        nat = z["native"].astype(np.float32); ms = z["ms"].astype(np.float32)
        cam = h.cams[v]
        vis, uv, _ = visibility.visible_mask(X, cam, h.gbufs[v]["depth"])
        uu = np.clip(np.round(uv[:, 0]).astype(int), 0, cam.W - 1)
        vv = np.clip(np.round(uv[:, 1]).astype(int), 0, cam.H - 1)
        accn[vis] += nat[vv[vis], uu[vis]]
        accm[vis] += ms[vv[vis], uu[vis]]
        cnt += vis
        print(f"  view {v:3d}: vis={int(vis.sum())}", flush=True)
    den = np.maximum(cnt, 1)
    nat_a = np.where(cnt > 0, accn / den, np.nan)
    ms_a = np.where(cnt > 0, accm / den, np.nan)

    feats = {
        "ms_over_native": ms_a / (nat_a + EPS),
        "ms_minus_native": ms_a - nat_a,
        "ms_alone": ms_a,
        "native_alone": nat_a,
        "teed_seedscore": seed.astype(np.float64),
    }

    res = {"spacing": sp, "views": "VAL", "ref_seedscore_auc": SEED_AUC_REF,
           "ref_junction_auc": JUNCTION_REF, "n": {}, "auc": {}}
    tests = [
        ("Q1 band90-vs-band30 (all near-crease)", b90, b30),
        ("Q2a band90-vs-band30 (NON-SEEDED only)", b90 & ~is_seed, b30 & ~is_seed),
        ("Q2b nontess-vs-tess (NON-SEEDED only)", nontess & ~is_seed, b30 & ~is_seed),
    ]
    for name, pmask, nmask in tests:
        sel = pmask | nmask
        y = pmask[sel]
        res["n"][name] = {"pos": int(pmask.sum()), "neg": int(nmask.sum())}
        res["auc"][name] = {}
        print(f"\n{name}   pos={int(pmask.sum())} neg={int(nmask.sum())}")
        for fk, fv in feats.items():
            a = auc_mw(fv[sel], y)
            res["auc"][name][fk] = a
            mark = ""
            if fk == "teed_seedscore":
                mark = "   <- CONTROL"
            print(f"  {fk:16s} AUC = {a:.4f}{mark}")

    q1 = res["auc"][tests[0][0]]
    best_ms = max(q1["ms_over_native"], q1["ms_minus_native"], q1["ms_alone"])
    beats_seed = best_ms > SEED_AUC_REF
    q2b = res["auc"][tests[2][0]]
    best_ms_culled = max(q2b["ms_over_native"], q2b["ms_minus_native"], q2b["ms_alone"])
    lifts_culled = best_ms_culled > q2b["teed_seedscore"]
    verdict = "GO" if (beats_seed and lifts_culled) else "NO-GO"
    res.update({"best_ms_Q1": best_ms, "beats_seedscore_ref": bool(beats_seed),
                "best_ms_Q2b_culled": best_ms_culled,
                "seedscore_Q2b_culled": q2b["teed_seedscore"],
                "lifts_nontess_culled": bool(lifts_culled), "verdict": verdict})
    print(f"\nGATE: best ms channel Q1 {best_ms:.4f} vs seedscore ref {SEED_AUC_REF} -> "
          f"{'BEATS' if beats_seed else 'does NOT beat'}")
    print(f"      culled non-tess lift: ms {best_ms_culled:.4f} vs seedscore "
          f"{q2b['teed_seedscore']:.4f} -> {'LIFTS' if lifts_culled else 'does NOT lift'}")
    print(f"VERDICT: {verdict}")
    json.dump(res, open(os.path.join(OUT, "ms_ratio_tier0.json"), "w"), indent=2)
    print("wrote out/ms_ratio_tier0.json")


if __name__ == "__main__":
    main()
