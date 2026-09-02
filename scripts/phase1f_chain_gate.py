"""PHASE 1f — chain-level gating diagnostic on the CACHED Phase-1e oracle scores.

APPENDIX-HARDENING DIAGNOSTIC ONLY (spec tier1/phase1f_spec.md). Path B is a PERMANENT
NO-GO (Phase 1e); neither branch of this fork reopens it. CHEAP + CPU-ONLY: gaussian
g-buffers are rendered on CPU (render_gbuffer device='cpu' — deterministic, no GPU
touched), no pipeline restart, NO new scoring, NO refitting: the oracle per-point
probabilities are loaded verbatim from out/phase1e_scores_chair.npz, the chain topology
verbatim from out/dexp1d_feats_chair.npz (key 'chain' — the P1c/P1d 3D
proximity+direction connected components over the SAME 272,366-pt cloud; row order
verified bit-identical via the P arrays). Writes ONLY NEW files (out/phase1f_*).

Question: is the Phase-1e point-oracle topology collapse (guard 0.6372) STRUCTURAL
(post-hoc thresholding cannot preserve 1D continuity) or an artifact of POINT-level
thresholding that chain pooling fixes?

Protocol (same as Phase 1e): pooled chain score (mean oracle prob; median as robustness
arm) -> keep whole chains with pool >= tau; tau on VAL {0,10,..,90} ONLY (argmax VAL
P@1.5 s.t. VAL R@1.5 >= baseline VAL 0.6307), frozen, TEST {5,15,..,95} evaluated once.
Metric = the LITERAL run_m1b macro segment-raster path; topology_guard = same definition
and same baseline strokes (linelets_chair_p1e_valref.npz) as Phase 1e. The Phase-1e
point-oracle comparison row is QUOTED from out/phase1e_test_eval.json, not re-run.

Frozen fork (chain_mean arm): topology_guard < 0.90 => STRUCTURAL impossibility;
>= 0.90 => REPRESENTATION bottleneck (mesh-free supervision gap is the only barrier).

Stages:  python scripts/phase1f_chain_gate.py --stage sweep
         python scripts/phase1f_chain_gate.py --stage test
"""
import argparse
import json
import os
import sys

import cv2
import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
OUT = os.path.join(TIER1, "out")

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")   # CPU-only: never touch a GPU

from src import render, view_split

# CPU patch BEFORE any Harness construction: render g-buffers on CPU (deterministic).
_orig_render_gbuffer = render.render_gbuffer
def _cpu_render_gbuffer(*a, **k):
    k["device"] = "cpu"
    return _orig_render_gbuffer(*a, **k)
render.render_gbuffer = _cpu_render_gbuffer

from phase1e_gate import (literal_eval, literal_mask, sweep_curves,
                          verify_raster_equivalence, script_md5, refuse_overwrite,
                          VALREF_JSON, VALREF_NPZ, SCORES_NPZ, TAU_PX)

P1E_TEST_JSON = os.path.join(OUT, "phase1e_test_eval.json")
FEATS_NPZ = os.path.join(OUT, "dexp1d_feats_chair.npz")
FREEZE_JSON = os.path.join(OUT, "phase1f_val_freeze.json")
TEST_JSON = os.path.join(OUT, "phase1f_test_eval.json")
BAR_TOPO = 0.90
ARMS = ["chain_mean", "chain_median"]               # chain_mean = PRIMARY (spec)


def build_chain_scores():
    """Pool the CACHED oracle probs over the CACHED chain components. No refitting."""
    z = np.load(SCORES_NPZ)
    zf = np.load(FEATS_NPZ)
    P, s, ch = z["P"], z["oracle"].astype(np.float64), zf["chain"]
    assert np.array_equal(P, zf["P"]), "row-order mismatch between cached npz files"
    m = ch >= 0
    assert np.isfinite(s[m]).all(), "NaN oracle score inside a chain"
    ids, inv, cnt = np.unique(ch[m], return_inverse=True, return_counts=True)
    pool_mean = np.zeros(len(ids))
    np.add.at(pool_mean, inv, s[m])
    pool_mean /= cnt
    pool_med = np.array([np.median(g) for g in
                         np.split(s[m][np.argsort(inv, kind="stable")],
                                  np.cumsum(cnt)[:-1])])
    s_mean = np.full(len(P), np.nan)
    s_med = np.full(len(P), np.nan)
    s_mean[m] = pool_mean[inv]
    s_med[m] = pool_med[inv]
    stats = {"n_points": int(len(P)), "n_chained": int(m.sum()),
             "chain_cover": float(m.mean()), "n_chains": int(len(ids)),
             "size_min": int(cnt.min()), "size_median": float(np.median(cnt)),
             "size_max": int(cnt.max())}
    return P, {"chain_mean": s_mean, "chain_median": s_med}, \
        {"chain_mean": pool_mean, "chain_median": pool_med}, stats


def stage_sweep(force=False):
    from tune_lib import Harness
    if os.path.exists(TEST_JSON):
        raise RuntimeError("phase1f TEST already evaluated — tau may not be re-frozen")
    refuse_overwrite(FREEZE_JSON, force)
    P, S, pools, stats = build_chain_scores()
    base_val = json.load(open(VALREF_JSON))
    row = [r for r in base_val["rows"]
           if r["kind"] == "segments" and "tuned+len" in r["stage"]][0]
    Pb, Rb = row["P1.5"], row["R1.5"]
    print(f"[sweep] baseline VAL reference: P@1.5 {Pb:.4f} R@1.5 {Rb:.4f}")
    print(f"[sweep] chains: {stats['n_chains']} over {stats['n_chained']} pts "
          f"(cover {stats['chain_cover']:.4f})")

    h = Harness("chair", views=tuple(view_split.VAL))
    frz = {"baseline_val": {"P1.5": Pb, "R1.5": Rb, "n": row["n"],
                            "src": os.path.basename(VALREF_JSON)},
           "chain_stats": stats, "val_views": list(view_split.VAL),
           "script_md5": script_md5(), "cpu_only": True, "arms": {}}

    for arm in ARMS:
        s = S[arm]
        fin = np.isfinite(s)
        # EXACT grid: every distinct pooled chain score is a threshold (1,692 chains)
        taus = np.unique(pools[arm])
        verify_raster_equivalence(h, P, s, taus[len(taus) // 2])
        Pc, Rc = sweep_curves(h, P, s, taus)
        for tq in (taus[0], taus[len(taus) // 2], taus[-2]):
            e = literal_eval(h, P, keep=np.where(fin, s, -np.inf) >= tq)
            i = int(np.where(taus == tq)[0][0])
            if abs(e[1.5][0] - Pc[i]) > 1e-9 or abs(e[1.5][1] - Rc[i]) > 1e-9:
                raise RuntimeError(f"{arm}: sweep/literal mismatch at tau={tq}")
        feas = Rc >= Rb
        starved = not feas.any()
        ti = 0 if starved else int(np.where(feas)[0][np.argmax(Pc[feas])])
        tau_star = float(taus[ti])
        keep = np.where(fin, s, -np.inf) >= tau_star
        e = literal_eval(h, P, keep=keep)
        n_ch_kept = int((pools[arm] >= tau_star).sum())
        frz["arms"][arm] = {
            "tau": tau_star, "starved_on_val": bool(starved),
            "n_kept": int(keep.sum()), "n_chains_kept": n_ch_kept,
            "val_P1.5": e[1.5][0], "val_R1.5": e[1.5][1],
            "val_P2.5": e[2.5][0], "val_R2.5": e[2.5][1],
            "curve": {"tau": [float(x) for x in taus],
                      "P1.5": Pc.tolist(), "R1.5": Rc.tolist()}}
        print(f"[sweep] {arm:12s} tau*={tau_star:.6f} chains {n_ch_kept:4d} "
              f"pts {int(keep.sum()):6d}  VAL P@1.5 {e[1.5][0]:.4f} "
              f"R@1.5 {e[1.5][1]:.4f} {'(STARVED)' if starved else ''}")

    # keep-ALL-chains reference (max-recall chain-gated config; NEW number)
    s = S["chain_mean"]
    keep_all = np.isfinite(s)
    e = literal_eval(h, P, keep=keep_all)
    frz["all_chains_val"] = {"n_kept": int(keep_all.sum()),
                             "P1.5": e[1.5][0], "R1.5": e[1.5][1]}
    print(f"[sweep] all-chains ref VAL: P@1.5 {e[1.5][0]:.4f} R@1.5 {e[1.5][1]:.4f} "
          f"(n={int(keep_all.sum())})")
    frz["note"] = ("chain-level gating: every point inherits its chain's pooled oracle "
                   "score; unchained points (42.4%) are NaN -> dropped by any tau. tau "
                   "grid = ALL distinct pooled chain scores (exact). Same VAL-only "
                   "freeze protocol as Phase 1e; sweep verified vs the literal "
                   "run_m1b rasteriser (mask-identity all VAL views + 3 spot taus).")
    json.dump(frz, open(FREEZE_JSON, "w"), indent=2)
    print(f"[sweep] wrote {FREEZE_JSON}")


def stage_test(force=False):
    from tune_lib import Harness
    import run_m1b
    refuse_overwrite(TEST_JSON, force)
    P, S, pools, stats = build_chain_scores()
    frz = json.load(open(FREEZE_JSON))
    if frz.get("script_md5") != script_md5():
        print(f"[test] WARNING: script md5 changed since freeze (recorded, proceeding)")
    p1e = json.load(open(P1E_TEST_JSON))
    banked = p1e["banked_baseline_test"]
    p1e_oracle = p1e["arms"]["oracle"]
    p1e_topo = p1e["topology_guard"]["arms"]["oracle"]["coverage_of_baseline_covered"]
    Rb = banked["R1.5"]
    print(f"[test] banked TEST baseline (QUOTED): P@1.5 {banked['P1.5']:.4f} "
          f"R@1.5 {Rb:.4f}")
    print(f"[test] Phase-1e point-oracle (QUOTED, cached): P@1.5 "
          f"{p1e_oracle['P1.5']:.4f} R@1.5 {p1e_oracle['R1.5']:.4f} "
          f"topo {p1e_topo:.4f}")

    h = Harness("chair", views=tuple(view_split.TEST))
    res = {"banked_baseline_test": banked,
           "phase1e_point_oracle_quoted": {"P1.5": p1e_oracle["P1.5"],
                                           "R1.5": p1e_oracle["R1.5"],
                                           "n_kept": p1e_oracle["n_kept"],
                                           "topology_guard": p1e_topo,
                                           "src": os.path.basename(P1E_TEST_JSON)},
           "test_views": list(view_split.TEST), "chain_stats": stats,
           "script_md5": script_md5(), "cpu_only": True, "arms": {}}

    keeps = {}
    for arm in ARMS:
        s = S[arm]
        tau = frz["arms"][arm]["tau"]
        keep = np.where(np.isfinite(s), s, -np.inf) >= tau
        keeps[arm] = keep
        e = literal_eval(h, P, keep=keep)
        res["arms"][arm] = {
            "tau_frozen": tau, "n_kept": int(keep.sum()),
            "n_chains_kept": int((pools[arm] >= tau).sum()),
            "P1.5": e[1.5][0], "R1.5": e[1.5][1],
            "P2.5": e[2.5][0], "R2.5": e[2.5][1],
            "recall_matched_to_banked": bool(e[1.5][1] >= Rb),
            "starved_on_val": frz["arms"][arm]["starved_on_val"]}
        print(f"[test] {arm:12s} tau={tau:.6f} chains "
              f"{res['arms'][arm]['n_chains_kept']:4d} pts {int(keep.sum()):6d}  "
              f"P@1.5 {e[1.5][0]:.4f} R@1.5 {e[1.5][1]:.4f} "
              f"(recall {'>=' if e[1.5][1] >= Rb else '<'} banked {Rb:.4f})")
    # all-chains reference on TEST (max-recall chain-gated config)
    keep_all = np.isfinite(S["chain_mean"])
    e = literal_eval(h, P, keep=keep_all)
    res["all_chains_test"] = {"n_kept": int(keep_all.sum()),
                              "P1.5": e[1.5][0], "R1.5": e[1.5][1]}
    keeps["all_chains"] = keep_all

    # -------- topology guard: SAME definition + SAME baseline strokes as Phase 1e ----
    lin = np.load(VALREF_NPZ)
    pB, tB, lB, keepB = lin["p"], lin["t"], lin["l_mod_tuned"], lin["keep_tuned"]
    guard_arms = ARMS + ["all_chains"]
    segs = {a: {"base_cov": 0, "both": 0, "all_cov": 0} for a in guard_arms}
    tot_all, cov_all = 0, 0
    for v in h.views:
        cu, cv_, cdt = h.crease[v]
        H, W = cdt.shape
        m = np.zeros((H, W), np.uint8)
        m[cv_, cu] = 1
        nlab, lab = cv2.connectedComponents(m, connectivity=8)
        mB, _ = run_m1b.raster_segments(h, v, pB, tB, lB, keep=keepB)
        dB = (cv2.distanceTransform((~mB).astype(np.uint8), cv2.DIST_L2, 5)
              if mB.any() else np.full((H, W), 1e9, np.float32))
        lab_f = lab.reshape(-1)
        sel = lab_f > 0
        ids = lab_f[sel]
        bmin = np.full(nlab, 1e9)
        np.minimum.at(bmin, ids, dB.reshape(-1)[sel])
        covB = bmin[1:] <= TAU_PX
        tot_all += nlab - 1
        cov_all += int(covB.sum())
        for a in guard_arms:
            mg = literal_mask(h, v, P, keeps[a])
            dg = (cv2.distanceTransform((~mg).astype(np.uint8), cv2.DIST_L2, 5)
                  if mg.any() else np.full((H, W), 1e9, np.float32))
            gmin = np.full(nlab, 1e9)
            np.minimum.at(gmin, ids, dg.reshape(-1)[sel])
            covG = gmin[1:] <= TAU_PX
            segs[a]["base_cov"] += int(covB.sum())
            segs[a]["both"] += int((covB & covG).sum())
            segs[a]["all_cov"] += int(covG.sum())
    res["topology_guard"] = {
        "convention": "identical to Phase 1e: GT crease 8-conn segments per TEST view "
                      "(pooled); covered iff min chamfer-DT over segment px <= 1.5; "
                      "PRIMARY = frac of baseline-stroke-covered segments retaining "
                      ">=1 surviving gated point",
        "n_gt_segments_total": tot_all, "n_baseline_covered": cov_all,
        "baseline_strokes_src": os.path.basename(VALREF_NPZ),
        "arms": {a: {"coverage_of_baseline_covered":
                     segs[a]["both"] / max(segs[a]["base_cov"], 1),
                     "coverage_of_all_gt_segments":
                     segs[a]["all_cov"] / max(tot_all, 1)}
                 for a in guard_arms}}
    for a in guard_arms:
        c = res["topology_guard"]["arms"][a]
        print(f"[topo] {a:12s} covers {c['coverage_of_baseline_covered']:.4f} of "
              f"baseline-covered GT segments ({c['coverage_of_all_gt_segments']:.4f} "
              f"of all)")

    # ------------------------- frozen DIAGNOSTIC fork (spec) -------------------------
    topo = res["topology_guard"]["arms"]["chain_mean"]["coverage_of_baseline_covered"]
    if topo >= BAR_TOPO:
        verdict = ("REPRESENTATION bottleneck: chain pooling preserves topology "
                   f"(guard {topo:.4f} >= 0.90 vs point-oracle {p1e_topo:.4f}); the "
                   "barrier is purely the mesh-free supervision gap (transfer AUC "
                   "0.5626). Future work = mesh-free edge self-supervision + "
                   "chain-level deployment.")
    else:
        verdict = ("STRUCTURAL impossibility: post-hoc thresholding cannot preserve "
                   f"1D crease continuity even with chain pooling (guard {topo:.4f} "
                   f"< 0.90; point-oracle was {p1e_topo:.4f}). Full builds need "
                   "topology-aware construction, not thresholding.")
    res["verdict_fork"] = {"primary_arm": "chain_mean",
                           "topology_guard": topo,
                           "phase1e_point_oracle_topo": p1e_topo,
                           "verdict": verdict}
    json.dump(res, open(TEST_JSON, "w"), indent=2)
    print(f"[test] FORK VERDICT: {verdict}")
    print(f"[test] wrote {TEST_JSON}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["sweep", "test"])
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    (stage_sweep if a.stage == "sweep" else stage_test)(force=a.force)
