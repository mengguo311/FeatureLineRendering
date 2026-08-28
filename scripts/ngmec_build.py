#!/usr/bin/env python
"""NG-MEC — normal-gated multi-view epipolar consensus CULL of TEED proposals. MESH-FREE.

*** METHOD PATH. Imports common/render/visibility/view_split only. It never imports
    mesh_oracle and never reads the GT mesh. Evaluation happens downstream in run_m1b's
    harness and in the frozen scorer scripts/ngmec_verdict.py. ***

THE CARRIER IS NOT GROWN. NG-MEC only REMOVES proposals from the existing frozen
teed_native_0.5 set. A culled proposal is pushed below every real score, so run_m1b's
top-f selection can never seed it; at a given f the seeds are the top-f TEED-ranked
SURVIVORS. run_m1b itself is used unmodified.

STAGE 1 - NORMAL GATE (frozen 3DGS geometry only).
An occluding contour is where the surface normal turns perpendicular to the viewing ray, so
it moves as the camera moves and is not a stable object-space crease. For each carrier
gaussian we take |n . v| (v = unit vector from the camera to the gaussian) over the TRAIN
views in which it is the front surface, and keep the MEDIAN. Occluding-contour-like loci sit
near 0; stable creases sit higher. Proposals below tau_n are culled.
Nothing here uses the mesh or any retraining - only g["normal"] from the frozen gaussians.

STAGE 2 - MULTI-VIEW EPIPOLAR CONSENSUS.
Reuses the repo's own per-gaussian consensus C in [0,1] from scripts/eco_consensus.py
(out/eco_C_<scene>__teed0.5_K3_t2.5_r0_s16.npy), which is exactly "is this position
corroborated by TEED ridges in other TRAIN views along the epipolar geometry", accumulated
softly over views rather than as a hard K count. Sweeping the threshold on C sweeps the
effective K. Proposals below c_thr are culled.

SELECTION DISCIPLINE. tau_n and c_thr are swept on CHAIR VAL only and transferred to lego
UNCHANGED, the discipline eco_score.py and CMEPI use. TEST is never used to choose them.
"""
import argparse, json, os, sys

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
for p in (TIER1, os.path.join(TIER1, "scripts"), os.path.join(TIER1, "scripts/explore"),
          os.path.join(TIER1, "scripts/explore/syn")):
    if p not in sys.path:
        sys.path.insert(0, p)

from src import common, render, visibility, view_split          # noqa: E402

SYN = os.path.join(TIER1, "scripts/explore/syn")
OUT = os.path.join(TIER1, "out")
BASE_SCORE = "teed_native_0.5"
ECO_TAG = "teed0.5_K3_t2.5_r0_s16"


def normal_gate_signal(scene, stride=4, verbose=True):
    """Median over visible TRAIN views of |n . v|. Low => occluding-contour-like. MESH-FREE."""
    cache = os.path.join(OUT, f"ngmec_normalgate_{scene}.npy")
    if os.path.exists(cache):
        return np.load(cache)
    cams, _ = common.load_cameras(scene)
    g = common.load_gaussians(scene)
    keep = render.defloat_mask(g["mu"], g["opacity"])
    X, Nrm = g["mu"][keep], g["normal"][keep]
    Nrm = Nrm / np.maximum(np.linalg.norm(Nrm, axis=1, keepdims=True), 1e-12)
    views = list(view_split.TRAIN)[::stride]
    acc = np.full((len(views), len(X)), np.nan, np.float32)
    for i, v in enumerate(views):
        cam = cams[v]
        gb = render.render_gbuffer(g, keep, cam)
        vis, _, _ = visibility.visible_mask(X, cam, gb["depth"])
        del gb
        try:
            import torch; torch.cuda.empty_cache()
        except Exception:
            pass
        d = X - cam.center
        d /= np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-12)
        c = np.abs(np.einsum("ij,ij->i", Nrm, d))
        acc[i][vis] = c[vis].astype(np.float32)
        if verbose:
            print(f"    [ngate] view {v:3d} ({i+1}/{len(views)}) vis {vis.mean():.3f}",
                  flush=True)
    with np.errstate(all="ignore"):
        S = np.nanmedian(acc, axis=0)
    S[~np.isfinite(S)] = 0.0                 # never visible -> treated as unsupported
    np.save(cache, S)
    return S


def build_score(scene, tau_n, c_thr):
    """TEED score with culled proposals pushed below every real value. Returns (S, diag)."""
    base = np.load(os.path.join(SYN, f"finalscore_overall_{scene}__{BASE_SCORE}.npy"))
    ng = normal_gate_signal(scene)
    C = np.load(os.path.join(OUT, f"eco_C_{scene}__{ECO_TAG}.npy"))
    assert len(base) == len(ng) == len(C), (len(base), len(ng), len(C))
    pass_n = ng >= tau_n
    pass_c = C >= c_thr
    surv = pass_n & pass_c
    S = base.astype(np.float64).copy()
    S[~surv] = base.min() - 1e6              # can never enter any top-f
    return S, {"n": int(len(base)), "n_survivors": int(surv.sum()),
               "surv_frac": float(surv.mean()),
               "culled_by_normal": int((~pass_n).sum()),
               "culled_by_consensus": int((~pass_c).sum()),
               "culled_by_both": int((~pass_n & ~pass_c).sum()),
               "tau_n": float(tau_n), "c_thr": float(c_thr),
               "max_f_supported": float(surv.mean())}


def tag_of(tau_n, c_thr):
    return f"n{tau_n:g}_c{c_thr:g}".replace(".", "p")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="chair")
    ap.add_argument("--tau_n", type=float, required=True)
    ap.add_argument("--c_thr", type=float, required=True)
    ap.add_argument("--name", default=None, help="score file stem override")
    a = ap.parse_args()
    S, diag = build_score(a.scene, a.tau_n, a.c_thr)
    nm = a.name or f"ngmec_{tag_of(a.tau_n, a.c_thr)}"
    p = os.path.join(SYN, f"finalscore_overall_{a.scene}__{nm}.npy")
    np.save(p, S)
    print(f"[ngmec] {a.scene} tau_n={a.tau_n:g} c_thr={a.c_thr:g}  "
          f"survivors {diag['n_survivors']}/{diag['n']} ({diag['surv_frac']:.3f})  "
          f"culled: normal {diag['culled_by_normal']}, consensus {diag['culled_by_consensus']}"
          f"  -> max supported f = {diag['max_f_supported']:.3f}")
    print(f"wrote {os.path.basename(p)}")
    json.dump(diag, open(os.path.join(OUT, f"ngmec_build_{a.scene}_{nm}.json"), "w"),
              indent=1, default=float)
