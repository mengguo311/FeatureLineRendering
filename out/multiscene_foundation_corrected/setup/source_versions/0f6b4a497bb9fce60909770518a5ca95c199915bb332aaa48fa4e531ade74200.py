"""tier1/src/tgap_gate.py — TGAP: TEED-GATED ADAPTIVE PULL+PRUNE (METHOD PATH, mesh-free).

HARD INVARIANT: this file sees gaussians, training RGBs, cameras and the FROZEN zero-shot
TEED edge cache only.  It never imports mesh_oracle and nothing above the EVAL banner of any
driver may hand it a mesh-derived quantity.

WHY (from CAP, out/CAP_RESULTS.md)
    CAP proved lego's recall miss is NOT a representational void: rho_B2 = 0.0799 against a
    0.30 gate and |B2| = 1.31% of the miss-set, which is BELOW chance (the same true-void test
    fires on 8.0% of random foreground pixels).  The topology is in the 3D carrier -> keep it.
    BUT CAP also showed the Class-A "a candidate was nearby" test is near-VACUOUS on lego:
    72.9% of missed crease loci vs 72.5% of arbitrary foreground pixels, a 0.4-point margin.
    So a GLOBAL prune relaxation spends near-uniform noise and merely retraces the mapped P/R
    frontier.  The binding quantity is SELECTIVITY AT HIGH RECALL, so the prune is relaxed
    ONLY where the frozen learned edge prior agrees.

WHAT "r" AND "L_min" ARE IN THIS PIPELINE, AND WHY (this is an interpretation the spec's
wording forced, so it is stated in full rather than buried)
    tgap_spec.md writes the mechanism as an NMS suppression radius r and a min-length L_min.
    Neither exists under those names in the P/R path.  The headline stage
    `AFTER pull+prune[tuned+len]` (run_m1b.py) suppresses candidates with exactly two
    thresholds, and both are "clear this or be suppressed", i.e. both have the sign the
    spec's equations assume:

      r      -> linelet_prune.consensus_prune(min_ratio=0.50): keep a linelet only if its
                multi-view 3-point inlier ratio reaches 0.50.  MEASURED to be THE binding
                suppression at lego f=1.00: it alone accounts for 54.0% of all prune
                failures exclusively (23,465 of 43,452), and the fraction passing it
                (0.56457) is the kept fraction (0.56426) to 3 decimals.
      L_min  -> linelet.modulate_length(thr=0.90): a linelet whose inlier ratio does not
                reach 0.90 is SHORTENED to lo=0.25x its half-length (a near-dot) instead of
                being extended to hi=1.5x.  MEASURED to be aggressive: only 7.8% of lego
                linelets (13.9% of the kept ones) clear it, so 86% of the drawn set is
                length-suppressed.  Shrinking a segment towards a dot IS the length prune of
                a drawn line, and the threshold that triggers it is the operative L_min.

    The one condition that IS literally a suppression radius in pixels -- max_med = 1.5 px on
    the post-pull median residual -- is NOT binding and is therefore NOT modulated: relaxing
    it to infinity at lego f=1.00 admits THREE more linelets out of 99,721 (0.003%).
    Modulating it would have been the literal reading and a measured no-op.  That is reported,
    not hidden.

THE TWO EQUATIONS, APPLIED EXACTLY AS THE SPEC WRITES THEM
    r(x)     = r_base     * (1 - alpha * E(x))      ->  min_ratio(x) = 0.50 * (1 - alpha*E)
    L_min(x) = L_base     * (1 - beta  * E(x))      ->  len_thr(x)   = 0.90 * (1 - beta *E)
    High E  -> both thresholds fall -> the prune is relaxed and the linelet is drawn long.
    E = 0   -> both thresholds are the committed baseline values EXACTLY, so arm A is the
               alpha=beta=0 member of this family and the arms are strictly nested.

E(x) -- THE FROZEN DEFINITION, fixed before any TEST number was read
    E_px = clip((p_teed - 0.5) / 0.5, 0, 1) on the RAW (un-thinned) TEED `native` probability
    map.  0.5 is TEED's PUBLISHED binarisation threshold in this repo (the teed_native_0.5
    arm, epipolar_consensus.teed_binary), so nothing is tuned here: below the published
    operating point E is exactly 0 and the prune stays exactly as committed, which is the
    spec's "texture/background keeps strict prune".  Un-thinned rather than NMS-thinned
    because projecting a 3D point onto a 1-px thinned ridge is a coin flip on sub-pixel
    registration, whereas the graded probability is what "edge response in [0,1]" means.
    On lego 89.3% of pixels give E = 0 exactly and ~6% exceed 0.6, so the field has real
    spatial contrast rather than being a disguised global constant -- which is precisely
    what arm C exists to falsify.

    A linelet is an OBJECT-SPACE primitive, so its E is the mean of E_px over the views in
    which it is visible.  Those views are the TRAIN views the DT pull already consumed and
    nothing else: VAL and TEST never enter the method path.
"""
import os

import numpy as np
import torch

TEED_THR = 0.5          # TEED's published binarisation threshold in this repo
R_BASE = 0.50           # linelet_prune.consensus_prune min_ratio (the binding suppression)
L_BASE = 0.90           # linelet.modulate_length thr (the length suppression)
MAX_MED = 1.5           # px; measured non-binding, deliberately NOT modulated
MIN_VIEWS = 3
LEN_LO, LEN_HI = 0.25, 1.5


def teed_edge_maps(scene, views, cache_dir=None, key="native", thr=TEED_THR):
    """E_px[V,H,W] float16 in [0,1] for the given views, in the given order."""
    cache_dir = cache_dir or os.path.join(os.path.expanduser("~/3dgs_line/tier1"),
                                          "out", f"teed_edges_{scene}")
    out = []
    for v in views:
        p = os.path.join(cache_dir, f"v{int(v):03d}.npz")
        z = np.load(p)[key].astype(np.float32)
        out.append(np.clip((z - thr) / (1.0 - thr), 0.0, 1.0).astype(np.float16))
    return np.stack(out)


def teed_response(field, P, scene, cache_dir=None, key="native", thr=TEED_THR,
                  rel_tol=0.02, two_sided=True, chunk=25, vis=None):
    """E[S] in [0,1] = mean over the visible field views of the TEED response at the
    linelet's projected uv.  `field` is a dt_pull.PullField built on the TRAIN views.

    vis (optional) : reuse the pull's own [V,S] visibility instead of recomputing it, so the
                     aggregate is over EXACTLY the views the residual statistic used."""
    Emaps = teed_edge_maps(scene, field.views, cache_dir=cache_dir, key=key, thr=thr)
    Et = torch.tensor(np.ascontiguousarray(Emaps), device=field.device)      # [V,H,W] f16
    Pt = torch.as_tensor(np.asarray(P, np.float32), device=field.device)
    if vis is None:
        W = field.visibility(Pt, rel_tol=rel_tol, two_sided=two_sided, chunk=chunk)
    else:
        W = torch.as_tensor(np.asarray(vis, np.float32), device=field.device)
    num = torch.zeros(len(Pt), device=field.device)
    den = torch.zeros(len(Pt), device=field.device)
    with torch.no_grad():
        for k0 in range(0, field.V, chunk):
            k1 = min(k0 + chunk, field.V)
            uv, _ = field.project(Pt, k0, k1)
            e = field.sample(Et, uv, k0, k1)                                 # [Vc,S]
            w = W[k0:k1]
            num += (e * w).sum(0)
            den += w.sum(0)
    E = (num / den.clamp(min=1.0)).clamp(0.0, 1.0)
    E = torch.where(den > 0, E, torch.zeros_like(E))     # never visible -> no relaxation
    return E.cpu().numpy().astype(np.float64)


def tuned_stats(resid3, vis, tau_in=1.0):
    """The committed TUNED prune statistic, unchanged: multi-view 3-point inlier ratio at
    tau_in=1.0 and the median 3-point residual.  Identical to
    linelet_prune.consensus_prune(..., use_resid3=True, tau_in=1.0)'s internals; it is
    recomputed here only so a whole alpha/beta grid can be swept without re-running the
    pull.  A bit-exactness check against linelet_prune is asserted by scripts/tgap_pull.py."""
    import warnings
    vis = np.asarray(vis, bool)
    r = np.asarray(resid3, np.float32)
    nv = vis.sum(0)
    inl = ((r <= tau_in) & vis).sum(0) / np.maximum(nv, 1)
    rr = np.where(vis, r, np.nan)
    with np.errstate(all="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        med = np.nanmedian(rr, axis=0)
    med = np.nan_to_num(med, nan=1e9)
    return {"inlier_ratio": inl.astype(np.float64),
            "median_resid": med.astype(np.float64), "n_vis": nv.astype(np.int64)}


def arm_masks(st, l, E, alpha=0.0, beta=0.0, r_base=R_BASE, l_base=L_BASE,
              max_med=MAX_MED, min_views=MIN_VIEWS, lo=LEN_LO, hi=LEN_HI):
    """The spec's two equations.  Returns (keep[S] bool, l_mod[S]).

    alpha = beta = 0            -> arm A, bit-identical to the committed tuned+len stage.
    E = the TEED field          -> arm B (TGAP).
    E = 1 everywhere            -> arm C, i.e. a GLOBAL relaxation of exactly the same two
                                  thresholds by exactly the same functional form.  Arm C is
                                  therefore arm B with the spatial information deleted and
                                  nothing else changed, which is what makes gate 2 a test of
                                  SELECTIVITY rather than of two unrelated implementations."""
    E = np.asarray(E, np.float64)
    inl = st["inlier_ratio"]
    r_x = r_base * (1.0 - alpha * E)
    L_x = l_base * (1.0 - beta * E)
    keep = ((st["n_vis"] >= min_views) & (inl >= r_x) & (st["median_resid"] <= max_med))
    l_mod = np.asarray(l, np.float64) * np.where(inl >= L_x, hi, lo)
    return keep, l_mod


# ---------------------------------------------------------------------------- outcome
# MEASURED OUTCOME — NO-GO on lego.  Recorded here so this file cannot be reused without it.
# Held-out TEST, out/TGAP_RESULTS.md:
#   gate 1  best in-band LIFT_P  -0.0107  (bar +0.030)          FAIL
#   gate 2  B - C                -0.0008 / -0.0113 against the
#           correctly recall-matched TEED-blind controls        FAIL, and the sign says
#                                                               the gate is anti-selective
#   gate 3  precision at matched recall            -0.0107      FAIL
#   gate 4  temporal veto: the VAL-frozen arm has alpha=0 so it does not move the carrier and
#           passes vacuously; at a spatial (0.6,0.6) P_pop degrades +2.42% (bar <2.0%)  FAIL
# CAUSE, measured: within deciles of the inlier ratio this prune already uses, E's AUC against
# "linelet is on a GT crease" is 0.42-0.47, i.e. BELOW chance.  On a texture-rich object the
# strongest multi-view-consistent image edges are decals and stud fillets, so relaxing where
# TEED agrees relaxes preferentially onto the candidates most likely to be wrong.  This puts E
# in the same family as the non-signals linelet_prune.py's docstring already warns about.
# Every (alpha, beta) in a 6x6 grid is negative on BOTH splits, under four definitions of E,
# and at two settings of the auxiliary "stronger DT-pull" trust-region widening.
