"""tier1/scripts/fgonly_dd3_carrier.py — HYGIENE item 5: re-score the persisted dd3 carrier of
record (out/carrier_dd3_cadpartA.npz, byte-identical strokes to dd3.json) under the
silhouette control (--fg_only, fg_erode 2) that the published lego/chair cells used and that
was never run on any solid.

*** MESH EVAL-ONLY: reads no mesh at all. ***  Nothing in the pipeline is touched: this only
calls the frozen m1b_stroke_temporal.frame_data / sequence_metrics with fg_only=True on the
exact same 240-frame orbit dd3.py used (cams 5->15, look-at centre = median de-floatered
gaussian). The uncontrolled numbers stay in dd3.json; this writes out/dd3_fgonly.json.
"""
import json, os, sys
import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1); sys.path.insert(0, os.path.join(TIER1, "scripts"))
from src import common, render                                              # noqa: E402
import temporal_m1b as T                                                    # noqa: E402
import m1b_stroke_temporal as M                                             # noqa: E402
from strokeviz import chain_args, N_ORBIT, SCENE                            # noqa: E402

OUT = os.path.join(TIER1, "out")


def main():
    z = np.load(os.path.join(OUT, f"carrier_dd3_{SCENE}.npz"))
    pts, offs = z["pts"], z["offs"]
    merged = [pts[offs[i]:offs[i + 1]] for i in range(len(offs) - 1)]
    cams, _ = common.load_cameras(SCENE)
    g = common.load_gaussians(SCENE)
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    ctr = np.median(g["mu"][keep_g], axis=0)
    path = T.orbit_cameras(cams[5], cams[15], N_ORBIT, ctr)
    ca = chain_args()
    ca.n_resample, ca.max_cand, ca.cand_radius, ca.match_thresh = 16, 6, 40.0, 3.0
    rep = {"scene": SCENE, "carrier": f"carrier_dd3_{SCENE}.npz ({len(merged)} strokes)",
           "orbit": "look-at-corrected cam5->cam15, 240 frames (identical to dd3.json)",
           "mesh_eval_only": "reads no mesh"}
    for fg in (False, True):
        ca.fg_only, ca.fg_erode = fg, 2
        frames = [M.frame_data(g, keep_g, c, merged, ca) for c in path]
        m = M.sequence_metrics(frames, ca)
        key = "temporal_240_fg_only" if fg else "temporal_240_uncontrolled_rerun"
        rep[key] = m
        a, b = m["A"], m["B"]
        print(f"  fg_only={fg}: OURS P_pop {a['P_pop']:.4f} (unm {a['unmatched_frac']:.4f} "
              f"cut {a['cut_frac']:.4f} drop {a['warp_dropped_frac']:.4f}) | BASE P_pop "
              f"{b['P_pop']:.4f} (unm {b['unmatched_frac']:.4f} cut {b['cut_frac']:.4f} "
              f"drop {b['warp_dropped_frac']:.4f}) | ratio {b['P_pop']/a['P_pop']:.2f}x",
              flush=True)
    p = os.path.join(OUT, "dd3_fgonly.json")
    json.dump(rep, open(p, "w"), indent=1)
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
