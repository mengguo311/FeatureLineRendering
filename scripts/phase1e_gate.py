"""PHASE 1e — CHEAP go/no-go: discriminator-gated Phase-1b cloud precision check.

EXPLORATORY probe BEYOND the locked path-C paper (camera-ready 4856be7). Writes ONLY NEW
files (out/phase1e_*). No banked paper number is altered, recomputed, or unfrozen: the
banked TEST baseline (out/m1b_chair_gated_test.json, segments tuned+len P@1.5 0.6573 /
R@1.5 0.5959) is QUOTED from its result file, never re-run.

MESH-FREE-GATE invariant (SACRED, spec tier1/phase1e_spec.md): no target-scene (chair)
mesh label touches any GATE score:
  (i)  TRANSFER   : DINOv2 probe fit on LEGO mesh labels with the exact banked P1d
                    protocol (fit-halfspace, StandardScaler+LogisticRegression C=1.0,
                    max_fit=60000, rng seed 0), applied zero-shot to chair.
                    NOTE the banked direction numbers: chair->lego 0.8245 (the number the
                    phase1e spec quotes), lego->chair 0.5626 (the direction that is
                    method-legal AT CHAIR and therefore the one used here).
  (ii) GUARDED    : the mesh-free-selected constants frozen in the paper (P1d) —
                    raw crease_vote V (banked chair AUC 0.6329) and the PL-VOTE-trained
                    FAM-C probe (banked mesh-free collapse 0.6371; deployed form fit on
                    ALL pseudo-labeled candidates, mesh-free by construction).
  ORACLE          : in-scene mesh-supervised probe — reported PURELY as a labelled
                    oracle upper bound, NEVER a GO trigger.

Protocol: tau per arm is picked on VAL views ONLY (recall matched to the _p1e_valref
baseline VAL recall), frozen to out/phase1e_val_freeze.json, then TEST is evaluated
exactly once per arm (out/phase1e_test_eval.json). Metric = the EXACT run_m1b macro
segment-raster convention (run_m1b.eval_segments / raster_segments), applied to the point
cloud as l=0 degenerate segments; the fast VAL sweep is verified mask-identical to the
literal rasteriser before use, and every frozen number is produced by the literal code.

Stages:  python scripts/phase1e_gate.py --stage scores
         python scripts/phase1e_gate.py --stage sweep
         python scripts/phase1e_gate.py --stage test
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

from src import edge_semantics as ES
from src import visibility, view_split

TAU_PX = 1.5                       # the headline metric radius (px)
ARMS_MESHFREE = ["transfer", "vote_probe", "raw_vote"]
ARMS_ALL = ARMS_MESHFREE + ["oracle"]
BANKED_BASELINE_JSON = os.path.join(OUT, "m1b_chair_gated_test.json")
VALREF_JSON = os.path.join(OUT, "m1b_chair_p1e_valref.json")
VALREF_NPZ = os.path.join(OUT, "linelets_chair_p1e_valref.npz")
SCORES_NPZ = os.path.join(OUT, "phase1e_scores_chair.npz")
SCORES_META = os.path.join(OUT, "phase1e_scores_meta.json")
FREEZE_JSON = os.path.join(OUT, "phase1e_val_freeze.json")
TEST_JSON = os.path.join(OUT, "phase1e_test_eval.json")

# frozen GO / NO-GO bars (phase1e_spec.md)
BAR_GO_P = 0.71
BAR_STRETCH_P = 0.78
BAR_TOPO = 0.90


def load_feats(scene):
    z = np.load(os.path.join(OUT, f"dexp1d_feats_{scene}.npz"))
    return {k: z[k] for k in z.files}


def fit_probe(X, y, train_mask, seed=0, max_fit=60000):
    """The exact banked P1d probe protocol (dexprimary_p1d.fit_eval, fit side)."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    ok_tr = train_mask & (y >= 0) & np.isfinite(X).all(1)
    sc = StandardScaler().fit(X[ok_tr])
    clf = LogisticRegression(max_iter=2000, C=1.0)
    sub = np.where(ok_tr)[0]
    if len(sub) > max_fit:
        sub = np.random.default_rng(seed).choice(sub, max_fit, replace=False)
    clf.fit(sc.transform(X[sub]), y[sub])
    return sc, clf, int(ok_tr.sum()), int(min(len(sub), max_fit))


def apply_probe(sc, clf, X):
    s = np.full(len(X), np.nan)
    ok = np.isfinite(X).all(1)
    s[ok] = clf.predict_proba(sc.transform(X[ok]))[:, 1]
    return s


def auc_of(y, s, mask):
    from sklearn.metrics import roc_auc_score
    m = mask & (y >= 0) & np.isfinite(s)
    return float(roc_auc_score(y[m], s[m])), int(m.sum())


# --------------------------------------------------------------- stage: scores ----
def stage_scores():
    ch, lg = load_feats("chair"), load_feats("lego")
    DDc = ch["DD"].astype(np.float32)
    DDl = lg["DD"].astype(np.float32)
    meta = {"n_chair": int(len(DDc)), "banked_refs": {
        "transfer_lego_to_chair": 0.5626, "transfer_chair_to_lego": 0.8245,
        "raw_vote_chair_evalhalf": 0.6329, "plvote_probe_xsplit": 0.6371,
        "mesh_ceiling_xsplit": 0.8395}}

    # (i) TRANSFER (PRIMARY): fit on lego mesh labels, fit-halfspace (banked protocol).
    fit_l = ~lg["x_eval_half"].astype(bool)
    sc, clf, n_tr, n_fit = fit_probe(DDl, lg["y"], fit_l)
    s_transfer = apply_probe(sc, clf, DDc)
    a, n = auc_of(ch["y"], s_transfer, np.ones(len(DDc), bool))
    meta["transfer"] = {"fit_scene": "lego", "fit_rows": n_tr, "fit_used": n_fit,
                        "auc_chair_labeled": a, "n_eval": n,
                        "sanity_vs_banked_0.5626": abs(a - 0.5626) < 0.005}
    print(f"[scores] transfer (lego->chair)  AUC on chair labeled = {a:.4f} "
          f"(banked 0.5626)")

    # (ii) GUARDED: raw vote V (a-priori constants, no fitting at all) ...
    V = ES.crease_vote(ch["FA"], ch["FB"])
    ev_c = ch["x_eval_half"].astype(bool)
    a_all, _ = auc_of(ch["y"], V, np.ones(len(DDc), bool))
    a_ev, _ = auc_of(ch["y"], V, ev_c)
    meta["raw_vote"] = {"auc_chair_labeled_all": a_all, "auc_chair_evalhalf": a_ev,
                        "sanity_vs_banked_0.6329": abs(a_ev - 0.6329) < 0.005}
    print(f"[scores] raw vote V             AUC all {a_all:.4f} / eval-half {a_ev:.4f} "
          f"(banked eval-half 0.6329)")

    # ... and the PL-VOTE-trained FAM-C probe (mesh-free; deployed = fit on ALL PLs).
    pl, _V2 = ES.pseudo_labels_votes(ch["FA"], ch["FB"])
    sc_v, clf_v, n_trv, n_fitv = fit_probe(DDc, pl, np.ones(len(DDc), bool))
    s_vote = apply_probe(sc_v, clf_v, DDc)
    a_vp, _ = auc_of(ch["y"], s_vote, np.ones(len(DDc), bool))
    a_vp_ev, _ = auc_of(ch["y"], s_vote, ev_c)
    meta["vote_probe"] = {"fit_rows": n_trv, "fit_used": n_fitv,
                          "auc_chair_labeled_all": a_vp, "auc_chair_evalhalf": a_vp_ev,
                          "banked_xsplit_ref": 0.6371}
    print(f"[scores] PL-VOTE probe          AUC all {a_vp:.4f} / eval-half {a_vp_ev:.4f} "
          f"(banked xsplit 0.6371)")

    # ORACLE (labelled upper bound ONLY): in-scene mesh-supervised, fit on ALL labels.
    sc_o, clf_o, n_tro, n_fito = fit_probe(DDc, ch["y"], np.ones(len(DDc), bool))
    s_oracle = apply_probe(sc_o, clf_o, DDc)
    a_o, _ = auc_of(ch["y"], s_oracle, np.ones(len(DDc), bool))
    a_o_ev, _ = auc_of(ch["y"], s_oracle, ev_c)
    meta["oracle"] = {"fit_rows": n_tro, "fit_used": n_fito,
                      "auc_in_sample_all": a_o, "auc_evalhalf_in_sample": a_o_ev,
                      "note": "IN-SCENE MESH-SUPERVISED, fit on ALL labels incl. eval "
                              "rows -> in-sample; ORACLE UPPER BOUND ONLY, never a GO "
                              "trigger. Banked honest xsplit ceiling 0.8395."}
    print(f"[scores] ORACLE (mesh, in-scene) AUC in-sample {a_o:.4f} "
          f"(banked xsplit ceiling 0.8395)")

    np.savez(SCORES_NPZ, P=ch["P"], transfer=s_transfer, vote_probe=s_vote,
             raw_vote=V, oracle=s_oracle, y=ch["y"])
    json.dump(meta, open(SCORES_META, "w"), indent=2)
    print(f"[scores] wrote {SCORES_NPZ}\n[scores] wrote {SCORES_META}")


# ------------------------------------------------------- raster helpers (sweep) ----
def degenerate_lt(n):
    """Zero-length 'segments' so the LITERAL run_m1b rasteriser draws each point as the
    degenerate case of the baseline convention (cv2.line a->a at shift=4)."""
    t = np.zeros((n, 3)); t[:, 0] = 1.0
    return t, np.zeros(n)


def view_pack(h, v, P):
    """Per-view precompute replicating raster_segments' pixel mapping exactly:
    fixed-point trunc int(u*16) then cv2's (fx+8)>>4 rounding."""
    cam = h.cams[v]
    vis, uv, _ = visibility.visible_mask(P, cam, h.gbufs[v]["depth"])
    fx = np.trunc(np.clip(uv[:, 0], -1e4, 1e4) * 16).astype(np.int64)
    fy = np.trunc(np.clip(uv[:, 1], -1e4, 1e4) * 16).astype(np.int64)
    px = np.right_shift(fx + 8, 4)
    py = np.right_shift(fy + 8, 4)
    # cv2's fixed-point rasteriser draws nothing for fx/fy in [-8,-1] (u in [-0.5,0)),
    # so require the fixed-point coordinate itself to be non-negative (audit finding).
    ok = (vis & (fx >= 0) & (fy >= 0)
          & (px >= 0) & (px < cam.W) & (py >= 0) & (py < cam.H))
    return ok, px, py


def sweep_curves(h, P, score, taus):
    """Exact macro segment-raster P/R@1.5 curves over a monotone score-threshold family.
    Per view: pixel maxscore image -> precision via sorted cumsum; recall via 3x3
    max-dilated maxscore sampled at crease pixels (chamfer-5 DT<=1.5 == 8-neighbourhood,
    verified against the literal evaluator before freezing anything)."""
    s = np.where(np.isfinite(score), score, -np.inf)
    Pv = np.zeros((len(h.views), len(taus)))
    Rv = np.zeros((len(h.views), len(taus)))
    for vi, v in enumerate(h.views):
        ok, px, py = view_pack(h, v, P)
        cu, cv_, cdt = h.crease[v]
        H, W = cdt.shape
        img = np.full(H * W, -np.inf)
        flat = py[ok] * W + px[ok]
        np.maximum.at(img, flat, s[ok])
        drawn = np.where(img > -np.inf)[0]
        good = (cdt.reshape(-1)[drawn] <= TAU_PX)
        o = np.argsort(-img[drawn], kind="stable")
        ds, dg = img[drawn][o], good[o].astype(np.float64)
        cg = np.concatenate([[0.0], np.cumsum(dg)])
        # precision(tau) = mean(good) over drawn pixels with maxscore >= tau
        # ds is sorted descending; count(ds >= tau) = searchsorted(-ds, -tau, 'right')
        k = np.searchsorted(-ds, -np.asarray(taus), side="right")
        with np.errstate(invalid="ignore"):
            Pv[vi] = np.where(k > 0, cg[k] / np.maximum(k, 1), 0.0)
        # recall(tau) = mean over crease px of (3x3-dilated maxscore >= tau)
        dil = cv2.dilate(img.reshape(H, W), np.ones((3, 3), np.uint8))
        cov = dil[cv_, cu]
        cs = np.sort(cov)
        Rv[vi] = 1.0 - np.searchsorted(cs, np.asarray(taus), side="left") / len(cs)
    return Pv.mean(0), Rv.mean(0)


def literal_eval(h, P, keep):
    """The authoritative number: run_m1b.eval_segments on l=0 degenerate segments."""
    import run_m1b
    t, l = degenerate_lt(len(P))
    return run_m1b.eval_segments(h, P, t, l, keep=keep)


def literal_mask(h, v, P, keep):
    import run_m1b
    t, l = degenerate_lt(len(P))
    m, _ = run_m1b.raster_segments(h, v, P, t, l, keep=keep)
    return m


def verify_raster_equivalence(h, P, score, tau):
    """Mask-identity between the fast pixel mapping and the literal cv2 rasteriser,
    over ALL harness views (audit finding: 3 views was too thin)."""
    keep = np.where(np.isfinite(score), score, -np.inf) >= tau
    for v in h.views:
        m_lit = literal_mask(h, v, P, keep)
        ok, px, py = view_pack(h, v, P)
        m_fast = np.zeros_like(m_lit)
        sel = ok & keep
        m_fast[py[sel], px[sel]] = True
        if not np.array_equal(m_lit, m_fast):
            d = int(np.count_nonzero(m_lit ^ m_fast))
            raise RuntimeError(f"raster mismatch view {v}: {d} px differ")
    return True


# ---------------------------------------------------------------- stage: sweep ----
def script_md5():
    import hashlib
    return hashlib.md5(open(os.path.abspath(__file__), "rb").read()).hexdigest()


def refuse_overwrite(path, force):
    if os.path.exists(path) and not force:
        raise RuntimeError(f"{path} already exists — refusing to overwrite the frozen "
                           f"file (pass --force only for a pre-TEST re-freeze)")


def stage_sweep(force=False):
    from tune_lib import Harness
    if os.path.exists(TEST_JSON):
        raise RuntimeError("TEST has already been evaluated — tau may not be re-frozen")
    refuse_overwrite(FREEZE_JSON, force)
    z = np.load(SCORES_NPZ)
    P = z["P"]
    base_val = json.load(open(VALREF_JSON))
    row = [r for r in base_val["rows"]
           if r["kind"] == "segments" and "tuned+len" in r["stage"]][0]
    Pb, Rb = row["P1.5"], row["R1.5"]
    print(f"[sweep] baseline VAL reference (tuned+len segments): "
          f"P@1.5 {Pb:.4f}  R@1.5 {Rb:.4f}  n={row['n']}")

    h = Harness("chair", views=tuple(view_split.VAL))
    # ONE ungated convention (audit finding): the literal evaluator at keep=None,
    # i.e. the full 272,366-point cloud including NaN-scored rows.
    e_u = literal_eval(h, P, keep=None)
    frz = {"baseline_val": {"P1.5": Pb, "R1.5": Rb, "n": row["n"],
                            "src": os.path.basename(VALREF_JSON)},
           "ungated_cloud_val": {"n": int(len(P)), "P1.5": e_u[1.5][0],
                                 "R1.5": e_u[1.5][1], "P2.5": e_u[2.5][0],
                                 "R2.5": e_u[2.5][1]},
           "val_views": list(view_split.VAL), "script_md5": script_md5(),
           "arms": {}}
    print(f"[sweep] ungated cloud VAL (literal, keep=None): "
          f"P@1.5 {e_u[1.5][0]:.4f} R@1.5 {e_u[1.5][1]:.4f}")

    for arm in ARMS_ALL:
        s = z[arm].astype(np.float64)
        fin = np.isfinite(s)
        # finite-score quantile grid ONLY — no -inf sentinel (audit finding: the -inf
        # grid point hardcoded recall to 1.0 and made the starvation guard dead code)
        taus = np.unique(np.quantile(s[fin], np.linspace(0.0, 0.995, 400)))
        verify_raster_equivalence(h, P, s, taus[len(taus) // 2])
        Pc, Rc = sweep_curves(h, P, s, taus)
        # spot-check the sweep against the literal evaluator, incl. the grid ends
        for tq in (taus[0], taus[len(taus) // 2], taus[-2]):
            e = literal_eval(h, P, keep=np.where(fin, s, -np.inf) >= tq)
            i = int(np.where(taus == tq)[0][0])
            if abs(e[1.5][0] - Pc[i]) > 1e-9 or abs(e[1.5][1] - Rc[i]) > 1e-9:
                raise RuntimeError(
                    f"{arm}: sweep/literal mismatch at tau={tq}: "
                    f"sweep P {Pc[i]:.6f} R {Rc[i]:.6f} vs literal "
                    f"P {e[1.5][0]:.6f} R {e[1.5][1]:.6f}")
        feas = Rc >= Rb
        starved = not feas.any()
        if starved:
            ti = 0                    # keep all finite-scored points; report honestly
        else:
            pi = np.where(feas)[0]
            ti = int(pi[np.argmax(Pc[pi])])
        tau_star = float(taus[ti])
        e = literal_eval(h, P, keep=np.where(fin, s, -np.inf) >= tau_star)
        n_kept = int((np.where(fin, s, -np.inf) >= tau_star).sum())
        frz["arms"][arm] = {
            "tau": tau_star, "starved_on_val": bool(starved), "n_kept": n_kept,
            "val_P1.5": e[1.5][0], "val_R1.5": e[1.5][1],
            "val_P2.5": e[2.5][0], "val_R2.5": e[2.5][1],
            "sweep_P_at_tau": float(Pc[ti]), "sweep_R_at_tau": float(Rc[ti]),
            "curve": {"tau": [float(x) for x in taus],
                      "P1.5": Pc.tolist(), "R1.5": Rc.tolist()}}
        print(f"[sweep] {arm:10s} tau*={tau_star:.6f} kept {n_kept:6d}  "
              f"VAL P@1.5 {e[1.5][0]:.4f} R@1.5 {e[1.5][1]:.4f} "
              f"{'(RECALL-STARVED: keep-all-finite)' if starved else ''}")

    frz["note"] = ("tau per arm = argmax VAL P@1.5 s.t. VAL R@1.5 >= baseline VAL "
                   "R@1.5, over the finite-score quantile grid; picked on VAL views "
                   "ONLY, frozen here BEFORE any TEST contact. Fast sweep verified "
                   "mask-identical (all VAL views) + value-identical (3 taus/arm incl. "
                   "grid ends) to the literal run_m1b rasteriser.")
    json.dump(frz, open(FREEZE_JSON, "w"), indent=2)
    print(f"[sweep] wrote {FREEZE_JSON}")


# ----------------------------------------------------------------- stage: test ----
def stage_test(force=False):
    from tune_lib import Harness
    refuse_overwrite(TEST_JSON, force)
    z = np.load(SCORES_NPZ)
    P = z["P"]
    frz = json.load(open(FREEZE_JSON))
    if frz.get("script_md5") not in (None, script_md5()):
        print(f"[test] WARNING: script md5 {script_md5()} != freeze-time "
              f"{frz['script_md5']} (recorded, proceeding)")
    banked = json.load(open(BANKED_BASELINE_JSON))
    brow = [r for r in banked["rows"]
            if r["kind"] == "segments" and "tuned+len" in r["stage"]][0]
    Pb, Rb = brow["P1.5"], brow["R1.5"]
    print(f"[test] banked TEST baseline (QUOTED, not re-run): "
          f"P@1.5 {Pb:.4f} R@1.5 {Rb:.4f} n={brow['n']}")

    h = Harness("chair", views=tuple(view_split.TEST))
    res = {"banked_baseline_test": {"P1.5": Pb, "R1.5": Rb, "n": brow["n"],
                                    "src": os.path.basename(BANKED_BASELINE_JSON)},
           "test_views": list(view_split.TEST), "arms": {}}

    # ungated cloud reference (NEW number)
    e0 = literal_eval(h, P, keep=None)
    res["ungated_cloud"] = {"n": int(len(P)), "P1.5": e0[1.5][0], "R1.5": e0[1.5][1],
                            "P2.5": e0[2.5][0], "R2.5": e0[2.5][1]}
    print(f"[test] ungated cloud (n={len(P)}): P@1.5 {e0[1.5][0]:.4f} "
          f"R@1.5 {e0[1.5][1]:.4f}")

    keeps = {}
    for arm in ARMS_ALL:
        s = z[arm].astype(np.float64)
        tau = frz["arms"][arm]["tau"]
        keep = np.where(np.isfinite(s), s, -np.inf) >= tau
        keeps[arm] = keep
        e = literal_eval(h, P, keep=keep)
        res["arms"][arm] = {
            "tau_frozen": tau, "n_kept": int(keep.sum()),
            "P1.5": e[1.5][0], "R1.5": e[1.5][1],
            "P2.5": e[2.5][0], "R2.5": e[2.5][1],
            "recall_matched_to_banked": bool(e[1.5][1] >= Rb),
            "starved_on_val": frz["arms"][arm]["starved_on_val"]}
        print(f"[test] {arm:10s} tau={tau:.6f} kept {int(keep.sum()):6d}  "
              f"P@1.5 {e[1.5][0]:.4f} R@1.5 {e[1.5][1]:.4f} "
              f"(recall {'>=' if e[1.5][1] >= Rb else '<'} banked {Rb:.4f})")

    # ---------------- topology guard: GT crease segment coverage ----------------
    lin = np.load(VALREF_NPZ)
    pB, tB = lin["p"], lin["t"]
    lB, keepB = lin["l_mod_tuned"], lin["keep_tuned"]
    import run_m1b
    segs = {a: {"base_cov": 0, "both": 0} for a in ARMS_ALL}
    tot_all, cov_all, cov_ung = 0, 0, {a: 0 for a in ARMS_ALL}
    ung_base_cov = 0
    n_seg_view = []
    for v in h.views:
        cu, cv_, _ = h.crease[v]
        H, W = h.crease[v][2].shape
        m = np.zeros((H, W), np.uint8)
        m[cv_, cu] = 1
        nlab, lab = cv2.connectedComponents(m, connectivity=8)
        n_seg_view.append(int(nlab - 1))
        mB, _ = run_m1b.raster_segments(h, v, pB, tB, lB, keep=keepB)
        dB = (cv2.distanceTransform((~mB).astype(np.uint8), cv2.DIST_L2, 5)
              if mB.any() else np.full((H, W), 1e9, np.float32))
        dts = {}
        for arm in ARMS_ALL:
            mg = literal_mask(h, v, P, keeps[arm])
            dts[arm] = (cv2.distanceTransform((~mg).astype(np.uint8), cv2.DIST_L2, 5)
                        if mg.any() else np.full((H, W), 1e9, np.float32))
        mu = literal_mask(h, v, P, None)
        du = (cv2.distanceTransform((~mu).astype(np.uint8), cv2.DIST_L2, 5)
              if mu.any() else np.full((H, W), 1e9, np.float32))
        lab_f = lab.reshape(-1)
        sel = lab_f > 0
        ids = lab_f[sel]
        bmin = np.full(nlab, 1e9); np.minimum.at(bmin, ids, dB.reshape(-1)[sel])
        umin = np.full(nlab, 1e9); np.minimum.at(umin, ids, du.reshape(-1)[sel])
        covB = bmin[1:] <= TAU_PX
        covU = umin[1:] <= TAU_PX
        tot_all += nlab - 1
        cov_all += int(covB.sum())
        ung_base_cov += int((covB & covU).sum())
        for arm in ARMS_ALL:
            gmin = np.full(nlab, 1e9)
            np.minimum.at(gmin, ids, dts[arm].reshape(-1)[sel])
            covG = gmin[1:] <= TAU_PX
            segs[arm]["base_cov"] += int(covB.sum())
            segs[arm]["both"] += int((covB & covG).sum())
            cov_ung[arm] += int(covG.sum())
    res["topology_guard"] = {
        "convention": "GT crease 8-conn segments per TEST view (pooled); covered iff "
                      "min chamfer-DT over segment px <= 1.5; PRIMARY = frac of "
                      "baseline-stroke-covered segments retaining >=1 gated point",
        "n_gt_segments_total": tot_all, "n_gt_segments_per_view": n_seg_view,
        "n_baseline_covered": cov_all,
        "baseline_frac_of_all": cov_all / max(tot_all, 1),
        "ungated_cloud_of_baseline_covered": ung_base_cov / max(cov_all, 1),
        "baseline_strokes_src": os.path.basename(VALREF_NPZ),
        "arms": {a: {"coverage_of_baseline_covered":
                     segs[a]["both"] / max(segs[a]["base_cov"], 1),
                     "coverage_of_all_gt_segments": cov_ung[a] / max(tot_all, 1)}
                 for a in ARMS_ALL}}
    for a in ARMS_ALL:
        c = res["topology_guard"]["arms"][a]
        print(f"[topo] {a:10s} covers {c['coverage_of_baseline_covered']:.4f} of "
              f"baseline-covered GT segments ({c['coverage_of_all_gt_segments']:.4f} "
              f"of all)")

    # ------------------------------ frozen verdict ------------------------------
    verdicts = {}
    for arm in ARMS_MESHFREE:
        a = res["arms"][arm]
        topo = res["topology_guard"]["arms"][arm]["coverage_of_baseline_covered"]
        matched = a["R1.5"] >= Rb
        if a["starved_on_val"] or not matched:
            v = "NO-GO (recall starvation)" if a["starved_on_val"] else \
                "NO-GO (TEST recall below banked baseline at frozen tau)"
        elif topo < BAR_TOPO:
            v = "NO-GO (topology fragmentation)"
        elif a["P1.5"] >= BAR_STRETCH_P:
            v = "STRETCH / STRONG-GO"
        elif a["P1.5"] >= BAR_GO_P:
            v = "GO"
        else:
            v = "NO-GO (precision below 0.71 at matched recall)"
        verdicts[arm] = v
    overall = "NO-GO"
    if any(v == "STRETCH / STRONG-GO" for v in verdicts.values()):
        overall = "STRETCH / STRONG-GO"
    elif any(v == "GO" for v in verdicts.values()):
        overall = "GO"
    res["verdicts_meshfree_arms"] = verdicts
    res["verdict_overall"] = overall
    res["oracle_note"] = ("oracle arm is a LABELLED UPPER BOUND ONLY and is excluded "
                          "from the verdict by the mesh-never-in-method-path invariant")
    res["script_md5"] = script_md5()
    json.dump(res, open(TEST_JSON, "w"), indent=2)
    print(f"[test] VERDICT (mesh-free arms only): {verdicts}")
    print(f"[test] OVERALL: {overall}")
    print(f"[test] wrote {TEST_JSON}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["scores", "sweep", "test"])
    ap.add_argument("--force", action="store_true",
                    help="allow overwriting an existing freeze file (pre-TEST only)")
    a = ap.parse_args()
    if a.stage == "scores":
        stage_scores()
    elif a.stage == "sweep":
        stage_sweep(force=a.force)
    else:
        stage_test(force=a.force)
