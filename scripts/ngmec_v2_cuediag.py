#!/usr/bin/env python
"""NG-MEC-v2 — why did each cue help or not? EVAL-ONLY (mesh_oracle for labels).

The weight sweep drove w_2dgs to ZERO even though the SAME 2DGS-normal ribbon dihedral is a
near-perfect PIXEL classifier (AUC 0.967 flat-print vs sharp-crease, gate2dgs.py). This asks
the obvious question directly: at the CARRIER-GAUSSIAN level, does each cue rank
near-crease gaussians above far-from-crease ones?

Labels (EVAL ONLY): a carrier gaussian is CREASE if its 3D centre lies within tau of a GT
mesh crease point (mesh edges with dihedral >= 30 deg, the mesh_oracle definition), and
NON-CREASE if it lies beyond 3*tau. The band between is discarded, mirroring the 1.5/3.0 px
band the image-space labels use.
"""
import argparse, json, os, sys

import numpy as np
from scipy.spatial import cKDTree

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
for p in (TIER1, os.path.join(TIER1, "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)
from src import common, render                                   # noqa: E402
from src.mesh_oracle import MeshOracle                            # EVAL ONLY  # noqa: E402
from ngmec_v2_combine import load_cues, R                         # noqa: E402


def auc(score, pos):
    s = np.asarray(score, float); y = np.asarray(pos, bool)
    n1, n0 = int(y.sum()), int((~y).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    r = np.empty(len(s)); r[np.argsort(s, kind="stable")] = np.arange(len(s))
    return float((r[y].sum() - n1 * (n1 - 1) / 2) / (n1 * n0))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", nargs="+", default=["chair", "lego"])
    ap.add_argument("--tau_mult", type=float, default=1.0,
                    help="tau = tau_mult * median nearest-neighbour spacing of the carrier")
    ap.add_argument("--out", default="out/ngmec_v2_cuediag.json")
    a = ap.parse_args()

    res = {}
    for scene in a.scenes:
        g = common.load_gaussians(scene)
        keep = render.defloat_mask(g["mu"], g["opacity"])
        X = g["mu"][keep]
        o = MeshOracle(scene)                                     # EVAL ONLY
        d = cKDTree(o.crease_pts).query(X, workers=-1)[0]
        spacing = float(np.median(cKDTree(X).query(X, k=2, workers=-1)[0][:, 1]))
        tau = a.tau_mult * spacing
        pos, neg = d <= tau, d > 3 * tau
        m = pos | neg
        base, cue2, ecoC = load_cues(scene)
        cues = {"teed_base": base, "cue_2dgs_normal": cue2, "cue_epi_consensus": ecoC,
                "additive_g0_e0.25": R(base) + 0.25 * R(ecoC),
                "additive_g0.5_e0.25": R(base) + 0.5 * R(cue2) + 0.25 * R(ecoC)}
        row = {"n_gauss": int(len(X)), "spacing": spacing, "tau": tau,
               "n_pos": int(pos.sum()), "n_neg": int(neg.sum()),
               "auc": {k: auc(v[m], pos[m]) for k, v in cues.items()},
               "corr_base_vs_2dgs": float(np.corrcoef(R(base), R(cue2))[0, 1]),
               "corr_base_vs_epi": float(np.corrcoef(R(base), R(ecoC))[0, 1]),
               "corr_2dgs_vs_epi": float(np.corrcoef(R(cue2), R(ecoC))[0, 1])}
        res[scene] = row
        print(f"\n=== {scene} ===  n={row['n_gauss']}  spacing={spacing:.5f} tau={tau:.5f}"
              f"  pos={row['n_pos']} neg={row['n_neg']}")
        for k, v in row["auc"].items():
            print(f"    AUC  {k:24s} {v:.4f}")
        print(f"    corr base~2dgs {row['corr_base_vs_2dgs']:+.4f}   "
              f"base~epi {row['corr_base_vs_epi']:+.4f}   "
              f"2dgs~epi {row['corr_2dgs_vs_epi']:+.4f}")
        del o
    json.dump(res, open(a.out, "w"), indent=1, default=float)
    print(f"\nwrote {a.out}")
