#!/usr/bin/env python
"""NG-MEC-v2 CUE 1 — per-gaussian CONTINUOUS 2DGS-normal creaseness score. METHOD-SAFE.

Emits S_normal[M], one value per carrier gaussian: the MEDIAN over the views in which the
gaussian is visible of the 2DGS rendered-normal ribbon dihedral at its projected centre.

WHY THIS SIGNAL.  src/gate2dgs.py records the measurement: on chair FLAT-printed vs
SHARP-crease pixels the ribbon dihedral reads AUC 0.696 on vanilla-3DGS normals but
0.967 on 2DGS normals (0.958 on the m1a seed subset).  Vanilla normals bake printed
texture into geometry; 2DGS normals do not.  So the cue is built on the 2DGS rendered
normal map, never on vanilla.

CONTINUOUS, NOT A GATE.  gate2dgs.geom_support_2dgs() thresholds this quantity at
tau_geom to make a binary mask; that path is deliberately NOT used here.  NG-MEC-v2's
finding is that orthogonal evidence must be spent ADDITIVELY - the two prior hard-veto
attempts (ECO veto, TGAP prior-as-gate) are on record as NO-GO / anti-predictive.  We emit
degrees and let the log-odds sum decide.

MESH-FREE.  Imports only common / render2dgs / gate2dgs / visibility / view_split.  It never
imports mesh_oracle and never reads the GT mesh, so it is legal in the method path.

HELD-OUT DISCIPLINE.  The published M1a recipe accumulates evidence over
np.linspace(0, 99, 25), which contains TEST views 25/45/95 and VAL views 0/50/70.  This cue
deliberately uses only the TRAIN members of that spread (19 views), so it introduces no new
test-set contact.  Cached visibility rows are selected to match.
"""
import argparse
import os
import sys
import time

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
for p in (TIER1, os.path.join(TIER1, "scripts"), os.path.join(TIER1, "scripts/explore")):
    if p not in sys.path:
        sys.path.insert(0, p)

from src import common, render, render2dgs, view_split, gate2dgs      # noqa: E402

SYN = os.path.join(TIER1, "scripts/explore/syn")


def evidence_views(cams):
    """The 25 spread views the published M1a recipe accumulates over (eco_consensus:69)."""
    return np.unique(np.round(np.linspace(0, len(cams) - 1, 25)).astype(int))


def project(X, cam):
    """uv[M,2], z[M] — identical math to src/visibility.visible_mask:15-18."""
    c = (cam.w2c[:3, :3] @ X.T).T + cam.w2c[:3, 3]
    z = c[:, 2]
    uv = (cam.K @ c.T).T
    return uv[:, :2] / np.clip(uv[:, 2:3], 1e-9, None), z


def cue_2dgs_normal(scene, model2dgs, verbose=True):
    cams, rgb_paths = common.load_cameras(scene)
    ev = evidence_views(cams)
    TR = set(view_split.TRAIN)
    sel = [i for i, v in enumerate(ev) if int(v) in TR]      # rows of the cached VIS
    views = [int(ev[i]) for i in sel]

    g = common.load_gaussians(scene)
    keep = render.defloat_mask(g["mu"], g["opacity"])
    X = g["mu"][keep]
    M = len(X)

    z = np.load(os.path.join(SYN, f"final_evid_{scene}.npz"))
    VIS = z["vis"]
    assert VIS.shape == (len(ev), M), (VIS.shape, (len(ev), M))
    VIS = VIS[sel]                                            # TRAIN rows only

    if verbose:
        print(f"[cue2dgs] {scene}: {M} carrier gaussians, {len(views)} TRAIN-spread views "
              f"{views}", flush=True)
        print(f"[cue2dgs] 2DGS model {model2dgs}", flush=True)

    g2, pipe, meta = render2dgs.load_2dgs(model2dgs)
    acc = np.full((len(views), M), np.nan, np.float32)
    t0 = time.time()
    for i, v in enumerate(views):
        cam = cams[v]
        gb2 = render2dgs.render_gbuffer_2dgs(g2, pipe, cam,
                                             bg_white=meta.get("white_background", True),
                                             half_pixel=True)
        nrm = gb2["normal"].cpu().numpy()
        fg = gb2["alpha"].cpu().numpy() > 0.5
        del gb2
        try:
            import torch
            torch.cuda.empty_cache()
        except Exception:
            pass

        dirx, diry = gate2dgs.edge_normals_dir(rgb_paths[v])
        uv, zc = project(X, cam)
        uu = np.clip(uv[:, 0], 0, cam.W - 1)
        ww = np.clip(uv[:, 1], 0, cam.H - 1)
        ui = np.clip(np.round(uu).astype(np.int64), 0, cam.W - 1)
        wi = np.clip(np.round(ww).astype(np.int64), 0, cam.H - 1)

        th, ok = gate2dgs.ribbon_normal_theta(uu.astype(np.float64), ww.astype(np.float64),
                                              dirx[wi, ui], diry[wi, ui], nrm, fg)
        good = VIS[i] & ok & np.isfinite(th)
        acc[i][good] = th[good].astype(np.float32)
        if verbose:
            print(f"    [cue2dgs] view {i+1}/{len(views)} (v{v})  "
                  f"measurable {good.mean():.3f}   {time.time()-t0:.0f}s", flush=True)

    with np.errstate(all="ignore"):
        S = np.nanmedian(acc, axis=0)
    n_seen = np.sum(np.isfinite(acc), axis=0)
    never = n_seen == 0
    # Recipe convention (score_from_evidence / eco_consensus:165-170): gaussians visible in
    # NO evidence view are pushed BELOW every real value rather than tying at 0.
    if never.any():
        S[never] = np.nanmin(S[~never]) - 1.0 if (~never).any() else 0.0
    diag = {"scene": scene, "model2dgs": model2dgs, "views": views, "M": int(M),
            "n_never_visible": int(never.sum()),
            "median_theta": float(np.nanmedian(S[~never])) if (~never).any() else float("nan"),
            "p05": float(np.nanpercentile(S[~never], 5)) if (~never).any() else float("nan"),
            "p95": float(np.nanpercentile(S[~never], 95)) if (~never).any() else float("nan"),
            "mean_views_seen": float(n_seen.mean())}
    return S.astype(np.float64), diag


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="chair")
    ap.add_argument("--model2dgs", default=None,
                    help="default out/2dgs_<scene>")
    ap.add_argument("--out", default=None,
                    help="default out/ngmec_v2_cue2dgs_<scene>.npy")
    a = ap.parse_args()
    m2 = a.model2dgs or os.path.join(TIER1, f"out/2dgs_{a.scene}")
    S, diag = cue_2dgs_normal(a.scene, m2)
    outp = a.out or os.path.join(TIER1, f"out/ngmec_v2_cue2dgs_{a.scene}.npy")
    np.save(outp, S)
    import json
    json.dump(diag, open(outp.replace(".npy", ".json"), "w"), indent=1, default=float)
    print(f"\n[cue2dgs] {a.scene}: median {diag['median_theta']:.3f} deg  "
          f"p05 {diag['p05']:.3f}  p95 {diag['p95']:.3f}  "
          f"never-visible {diag['n_never_visible']}")
    print(f"wrote {outp}")
