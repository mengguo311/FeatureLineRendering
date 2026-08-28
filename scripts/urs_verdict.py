#!/usr/bin/env python
"""URS — FROZEN coverage scorer + GO/NO-GO. Committed BEFORE any coverage number exists.

*** EVAL-ONLY. The GT mesh is read here and ONLY here (via src/mesh_oracle), exactly as
    scripts/lego_ceiling_autopsy.py does. The URS carrier builder imports no mesh. ***

FROZEN THRESHOLD (verbatim from tier1/urs_spec.md), not to be moved after the numbers land:

  GO    : lego raw geometric coverage >= 0.75  AND  linelet count <= 3x the OVERALL-recipe
          baseline count.
  NO-GO : coverage < 0.75  =>  empirical proof of a splat-carrier resolution limit.

FROZEN COVERAGE METRIC (fixed here so it cannot be redefined once the answer is known):

  population   every VISIBLE GT crease point on the held-out TEST views. Visibility is the
               mesh-depth z-peel of MeshOracle.visible_crease_uv (3x3 min |dz|, eps 0.015),
               the same control the lego ceiling autopsy used, so occluded stud/cavity
               creases are never counted as ground truth.
  carrier      an arbitrary set of 3D points. A segment carrier (p, t, l) is expanded to
               N_SEG samples along p +- l*t before projection, matching how the harness
               rasterises linelets. A point carrier is used as-is. Carrier points are
               projected per view and kept only where the 3DGS depth z-buffer says they are
               the front surface (src/visibility.visible_mask), so occluded carrier does not
               get credit.
  covered      a GT crease point is COVERED iff a visible projected carrier point lies within
               TAU_PX = 1.5 px of it -- the same tolerance and the same 2D space as the
               R@1.5 metric this probe is explaining.
  coverage     covered / population, pooled over all TEST views.

This is a PURE COVERAGE CEILING: no ranking, no culling, no precision term. Precision is
deliberately not measured and must not be traded against.
"""
import argparse, json, os, sys

import numpy as np
from scipy.spatial import cKDTree

TAU_PX = 1.5
GO_COVERAGE = 0.75
BUDGET_MULT = 3.0
N_SEG = 5

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
for p in (TIER1, os.path.join(TIER1, "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)


def segments_to_points(p, t, l, n=N_SEG):
    """Expand linelets to N samples along p +- l*t (harness rasterises the same span)."""
    s = np.linspace(-1.0, 1.0, n)
    return (p[:, None, :] + (l[:, None] * s)[:, :, None] * t[:, None, :]).reshape(-1, 3)


def coverage(scene, carrier_pts, tau_px=TAU_PX, verbose=True):
    """Frozen metric. carrier_pts [K,3] world points. -> dict."""
    from src import common, render, visibility, view_split
    from src.mesh_oracle import MeshOracle                       # EVAL ONLY

    cams, _ = common.load_cameras(scene)
    oracle = MeshOracle(scene)
    g = common.load_gaussians(scene)
    keep = render.defloat_mask(g["mu"], g["opacity"])

    tot_n = tot_cov = 0
    per_view = []
    for v in view_split.TEST:
        cam = cams[v]
        uvq = oracle.visible_crease_uv(cam, view_key=("urs", v))   # z-peeled GT
        if not len(uvq):
            continue
        gb = render.render_gbuffer(g, keep, cam)
        vis, uv, _ = visibility.visible_mask(carrier_pts, cam, gb["depth"])
        del gb
        try:
            import torch; torch.cuda.empty_cache()
        except Exception:
            pass
        cp = uv[vis]
        if len(cp):
            d = cKDTree(cp).query(uvq, workers=-1)[0]
        else:
            d = np.full(len(uvq), 1e9)
        cov = d <= tau_px
        per_view.append({"view": int(v), "n_gt": int(len(uvq)),
                         "n_carrier_visible": int(vis.sum()),
                         "coverage": float(cov.mean())})
        tot_n += len(uvq); tot_cov += int(cov.sum())
        if verbose:
            print(f"    [cov:{scene}] view {v:3d}  n_gt={len(uvq):7d}  "
                  f"carrier_vis={int(vis.sum()):7d}  coverage={cov.mean():.4f}", flush=True)
    del oracle
    return {"scene": scene, "tau_px": tau_px, "n_gt_crease_pts": tot_n,
            "n_carrier_pts": int(len(carrier_pts)),
            "coverage": tot_cov / max(tot_n, 1), "per_view": per_view}


def verdict(urs_cov, urs_count, baseline_count, baseline_cov, chair_cov=None):
    budget_cap = BUDGET_MULT * baseline_count
    within = urs_count <= budget_cap
    go = bool(urs_cov >= GO_COVERAGE and within)
    return {"thresholds": {"GO_coverage": GO_COVERAGE, "tau_px": TAU_PX,
                           "budget_mult": BUDGET_MULT, "n_seg_samples": N_SEG},
            "baseline": {"coverage": baseline_cov, "n_linelets": baseline_count},
            "urs": {"coverage": urs_cov, "n_carrier": urs_count},
            "budget_cap": budget_cap, "within_budget": bool(within),
            "chair_control_coverage": chair_cov,
            "coverage_gate": bool(urs_cov >= GO_COVERAGE),
            "GO": go,
            "reading": ("GO: post-hoc densification can cover lego creases"
                        if go else
                        "NO-GO: splat-carrier resolution limit is empirical, not asserted")}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scored", default="out/urs_coverage.json",
                    help="json written by scripts/urs_build.py holding the scored coverages")
    ap.add_argument("--out", default="out/urs_verdict.json")
    a = ap.parse_args()
    s = json.load(open(a.scored))
    v = verdict(s["urs"]["coverage"], s["urs"]["n_carrier_pts"],
                s["baseline"]["n_linelets"], s["baseline"]["coverage"],
                (s.get("chair_control") or {}).get("coverage"))
    print("=" * 72)
    print("URS — FROZEN GO/NO-GO   (threshold committed before any coverage was scored)")
    print("=" * 72)
    print(f"  baseline  coverage {v['baseline']['coverage']:.4f}   "
          f"n_linelets {v['baseline']['n_linelets']}")
    print(f"  URS       coverage {v['urs']['coverage']:.4f}   "
          f"n_carrier  {v['urs']['n_carrier']}")
    print(f"  budget    cap {v['budget_cap']:.0f}  -> within budget: {v['within_budget']}")
    if v["chair_control_coverage"] is not None:
        print(f"  chair control coverage {v['chair_control_coverage']:.4f}")
    print(f"\n  coverage >= {GO_COVERAGE}  -> {'PASS' if v['coverage_gate'] else 'FAIL'}")
    print(f"  VERDICT: {'GO' if v['GO'] else 'NO-GO'}")
    print(f"  {v['reading']}")
    json.dump(v, open(a.out, "w"), indent=1, default=float)
    print(f"\nwrote {a.out}")
