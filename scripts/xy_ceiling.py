"""EXPERIMENT Y, §Y.7 — the frozen extractor's ABSOLUTE F1 CEILING per condition.

*** EVAL ONLY.  Uses the GT mesh to define a PERFECT cull.  Not a method. ***

WHY THIS EXISTS
    The natural objection to a KILL verdict is "your oracle retrain was implemented too
    weakly".  This closes that objection without building a stronger oracle.  The frozen
    extractor's candidate pool is fixed by the DexiNed edge pixels (227,018 points, identical
    across conditions because the images are identical); retraining the 3DGS can only change
    WHERE along its ray each candidate is placed, plus which candidates the free-space cull
    keeps.  So apply a PERFECT cull -- keep exactly the candidates within the scoring radius
    of a GT crease, precision forced to 1.000 -- and read off the best F1 that condition could
    ever support under ANY selection or scoring rule.  The gap between conditions at that
    ceiling is the entire prize available to retraining, oracle strength included.
"""
import json
import os
import sys

import numpy as np
from scipy.spatial import cKDTree

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
OUT = os.path.join(TIER1, "out", "xy")
VIEWS = [5, 15, 25, 35, 45, 55, 65, 75, 85, 95]
CONDS = [("cadpartA", "A_vanilla"), ("cadpartB", "B_ORACLE"), ("cadpartH", "Bp_honest")]


def main():
    rad = json.load(open(os.path.join(OUT, "xy_expY.json")))["radius_world"]
    gt = np.load(os.path.join(TIER1, "cache", "dexp0_gt_cadpartA_a30.npz"))
    cp = gt["crease_pts"]
    seen = np.zeros(len(cp), bool)
    for v in VIEWS:
        seen[gt[f"idx{v}"]] = True
    si = np.where(seen)[0]
    tg = cKDTree(cp)
    rep = {"radius_world": rad, "n_gt_seen": int(len(si)),
           "note": ("ceiling = perfect cull of the RAW candidate pool (precision forced to "
                    "1.0). It bounds every selection/scoring rule, so it bounds every "
                    "retraining scheme acting through this extractor."),
           "conditions": {}}
    for scene, lab in CONDS:
        z = np.load(os.path.join(TIER1, "out", f"dexprimary_p1b_cloud_{scene}_ref40.npz"))
        Praw = z["P"]
        k = (z["support"] >= 2) & z["surface_keep"] & (z["resid"] <= 1.0)
        P = Praw[k]
        R = float((cKDTree(P).query(cp[si], k=1, workers=-1)[0] <= rad).mean())
        Pr = float((tg.query(P, k=1, workers=-1)[0] <= rad).mean())
        orc = Praw[tg.query(Praw, k=1, workers=-1)[0] <= rad]
        Rc = float((cKDTree(orc).query(cp[si], k=1, workers=-1)[0] <= rad).mean())
        rep["conditions"][lab] = {
            "n_raw_candidates": int(len(Praw)), "n_kept_canonical": int(len(P)),
            "actual_recall": round(R, 4), "actual_precision": round(Pr, 4),
            "actual_F1": round(2 * R * Pr / (R + Pr), 4),
            "n_kept_perfect_cull": int(len(orc)),
            "ceiling_recall": round(Rc, 4), "ceiling_precision": 1.0,
            "ceiling_F1": round(2 * Rc / (Rc + 1.0), 4)}
    c = rep["conditions"]
    rep["delta_ceiling_F1_B_minus_A"] = round(c["B_ORACLE"]["ceiling_F1"] -
                                              c["A_vanilla"]["ceiling_F1"], 4)
    rep["bar_A_plus_0.15"] = round(c["A_vanilla"]["actual_F1"] + 0.15, 4)
    rep["bar_is_below_ceiling"] = bool(rep["bar_A_plus_0.15"] < c["A_vanilla"]["ceiling_F1"])
    json.dump(rep, open(os.path.join(OUT, "xy_ceiling.json"), "w"), indent=1)
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
