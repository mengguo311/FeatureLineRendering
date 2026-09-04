"""EXPERIMENT Y — temporal CONTROL: does Condition B really worsen coherence, or was the
apparent worsening an artefact of B projecting through a DENSER z-buffer?

*** EVAL ONLY. ***

WHY
    In the main Y run each condition's 3D chains were projected through THAT CONDITION'S OWN
    gaussian z-buffer.  m1b_stroke_temporal.ours_strokes splits a chain at every occlusion
    break, so a denser reconstruction fragments the same curve into more, shorter strokes.
    B (192,068 gaussians, 60,773 after defloat) produced 436 strokes/frame against A's 408
    (75,539 / 32,476).  P_pop counts unmatched strokes, and stroke_metric.match_strokes
    retrieves only the top-6 candidate centroids within 40 px, so a denser stroke population
    is charged more popping for the same underlying motion.  The raw A->B gap (+0.021) may
    therefore be measuring z-buffer density, not line stability.

THE CONTROL
    Re-run the identical metric with ONE shared reference z-buffer (Condition A's gaussians)
    used for the occlusion split and for the warp, for every condition.  Then the only thing
    that differs between conditions is the 3D line geometry itself, which is what the frozen
    rule is about.  Both readings are reported.
"""
import argparse
import json
import os
import sys

import numpy as np
import torch
from scipy.spatial import cKDTree

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
OUT = os.path.join(TIER1, "out", "xy")
CONDS = [("cadpartA", "A_vanilla"), ("cadpartB", "B_ORACLE"), ("cadpartH", "Bp_honest")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref_scene", default="cadpartA", help="scene whose z-buffer is shared")
    ap.add_argument("--n_orbit", type=int, default=60)
    ap.add_argument("--budget", type=int, default=20000)
    ap.add_argument("--min_nodes", type=int, default=8)
    ap.add_argument("--n_resample", type=int, default=16)
    ap.add_argument("--max_cand", type=int, default=6)
    ap.add_argument("--cand_radius", type=float, default=40.0)
    ap.add_argument("--match_thresh", type=float, default=3.0)
    ap.add_argument("--match_frac", default="",
                    help="comma list label=frac: randomly keep that fraction of a condition's "
                         "chains, 3 seeds, to equalise strokes/frame against A")
    args = ap.parse_args()
    from src import common, render, stroke_metric, strokes
    from m1b_stroke_temporal import ours_strokes
    from dexprimary_p0 import voxel_budget
    from xy_expY import load_traj, tangents_pca

    cams = load_traj(args.ref_scene, "orbit")[:args.n_orbit]
    gref = common.load_gaussians(args.ref_scene)
    kref = render.defloat_mask(gref["mu"], gref["opacity"])
    print(f"[ctrl] shared z-buffer from {args.ref_scene}: {len(gref['mu'])} gaussians, "
          f"{int(kref.sum())} after defloat; {len(cams)} orbit frames", flush=True)
    depths = []
    for c in cams:
        gb = render.render_gbuffer(gref, kref, c)
        depths.append(gb["depth"])
        del gb
    res = {}
    for scene, lab in CONDS:
        z = np.load(os.path.join(TIER1, "out", f"dexprimary_p1b_cloud_{scene}_ref40.npz"))
        keep = (z["support"] >= 2) & z["surface_keep"] & (z["resid"] <= 1.0)
        P = z["P"][keep]
        Pb = P[voxel_budget(P, args.budget)]
        t, sp = tangents_pca(Pb)
        ch, kept = strokes.chain_linelets_3d(Pb, t, np.full(len(Pb), sp), nms_radius_mult=1.0,
                                             k=10, cos_tan=0.60, cos_col=0.50, gap_mult=4.0,
                                             min_nodes=args.min_nodes)
        Pk = Pb[kept]
        chain3d_full = [Pk[c] for c in ch]
        mf = dict(x.split("=") for x in args.match_frac.split(",") if x)
        seeds = [0, 1, 2] if lab in mf else [0]
        runs = []
        for sd in seeds:
          chain3d = chain3d_full
          if lab in mf:
            r = np.random.default_rng(sd)
            k2 = r.choice(len(chain3d_full), int(round(float(mf[lab]) * len(chain3d_full))),
                          replace=False)
            chain3d = [chain3d_full[i] for i in sorted(k2)]
          frames = [{"A": ours_strokes(chain3d, c, depths[i]),
                     "depth": depths[i].detach().cpu().numpy(), "cam": c}
                    for i, c in enumerate(cams)]
          fre, pop, unm, nst, drop = [], [], [], [], []
          for i in range(len(frames) - 1):
              f0, f1 = frames[i], frames[i + 1]
              nst.append(len(f0["A"]))
              w, surv = stroke_metric.warp_strokes(f0["A"], f0["depth"], f0["cam"], f1["cam"])
              dr = int((~surv).sum()) if len(surv) else 0
              m = stroke_metric.match_strokes(w, f1["A"], n_resample=args.n_resample,
                                              max_cand=args.max_cand,
                                              cand_radius=args.cand_radius,
                                              match_thresh=args.match_thresh)
              pp = stroke_metric.pop_penalty(m, n_dropped_by_warp=dr)
              if len(m["frechet"]):
                  fre.append(m["frechet"])
              pop.append(pp["P_pop"])
              unm.append(pp["unmatched_frac"])
              drop.append(dr / max(len(f0["A"]), 1))
          f = np.concatenate(fre) if fre else np.zeros(0)
          runs.append({"seed": sd, "n_chains": len(chain3d),
                       "n_strokes_per_frame": round(float(np.mean(nst)), 2),
                       "P_pop": round(float(np.mean(pop)), 5),
                       "frechet_median": round(float(np.median(f)), 5) if len(f) else None,
                       "frechet_p90": round(float(np.percentile(f, 90)), 5) if len(f) else None,
                       "unmatched_frac": round(float(np.mean(unm)), 5),
                       "warp_dropped_frac": round(float(np.mean(drop)), 5)})
        res[lab] = runs[0] if len(runs) == 1 else {
            "runs": runs,
            "n_strokes_per_frame": round(float(np.mean([r["n_strokes_per_frame"] for r in runs])), 2),
            "P_pop": round(float(np.mean([r["P_pop"] for r in runs])), 5),
            "P_pop_sd": round(float(np.std([r["P_pop"] for r in runs])), 5),
            "frechet_median": round(float(np.mean([r["frechet_median"] for r in runs])), 5)}
        print(f"[ctrl] {lab}: {json.dumps(res[lab])}", flush=True)
    out = {"control": "shared reference z-buffer for the occlusion split and the warp",
           "ref_scene": args.ref_scene, "n_orbit": args.n_orbit, "budget": args.budget,
           "conditions": res,
           "delta_P_pop_B_minus_A": round(res["B_ORACLE"]["P_pop"] - res["A_vanilla"]["P_pop"], 5),
           "delta_strokes_B_minus_A": round(res["B_ORACLE"]["n_strokes_per_frame"] -
                                            res["A_vanilla"]["n_strokes_per_frame"], 2)}
    json.dump(out, open(os.path.join(OUT, "xy_temporal_ctrl.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
