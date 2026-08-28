"""tier1/scripts/tgap_temporal.py — TGAP gate 4 stage 1: materialise arm A / arm B / arm C
linelet sets at the chosen operating f in the layout m1b_stroke_temporal.py addresses.

*** METHOD-SIDE artefact writer.  Mesh-free: it only re-applies src/tgap_gate.arm_masks to a
    dumped pull.  The temporal metric itself is scripts/m1b_stroke_temporal.py, which is
    METHOD PATH for both pipelines. ***

m1b_stroke_temporal.build_chains reads out/linelets_<scene>_<variant>_test.npz and chains
z["keep"] with lengths z["l"] and confidence z["inlier_ratio"].

WHICH HALF-LENGTH GOES INTO THE CHAINER, AND WHY IT IS THE RAW ONE (--stroke_lengths raw,
the default)
    strokes.chain_linelets_3d sets its spatial NMS radius to nms_radius_mult * median(l).
    linelet.modulate_length shrinks 86% of lego's linelets to 0.25x, and by different amounts
    per arm: at f=0.50 the median drawn half-length is 0.00241 for arm A, 0.00337 for arm B at
    the frozen (0, 0.2) and 0.00613 for a spatial (0.6, 0.6).  Feeding the MODULATED length in
    would therefore hand every arm a DIFFERENT chaining operator -- a 2.5x spread in the NMS
    radius -- which is exactly what tgap_spec.md forbids with "linelet/polyline definitions
    unchanged", and it would also break comparability with every published temporal run, all
    of which chain the raw l.

    So the default feeds the RAW half-length for every arm and the arms differ ONLY in the
    prune mask, which is the object-space carrier gate 4 vetoes on.  modulate_length is a
    RASTERISATION-time precision dial (it is applied inside run_m1b.eval_segments); it is not
    part of the 3-D carrier.  --stroke_lengths tuned reproduces the other convention and is
    reported as a secondary reading in out/TGAP_RESULTS.md.
"""
import argparse
import os
import sys

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))

from src import tgap_gate                                                # noqa: E402

OUT = os.path.join(TIER1, "out")


def write_variant(scene, f, variant, alpha, beta, E_mode="teed", stroke_lengths="raw"):
    z = np.load(os.path.join(OUT, f"tgap_pull_{scene}_f{f:.2f}.npz"))
    st = {"inlier_ratio": z["inlier_ratio"], "median_resid": z["median_resid"],
          "n_vis": z["n_vis"]}
    E = z["E"] if E_mode == "teed" else np.ones(len(z["l"]))
    keep, l_mod = tgap_gate.arm_masks(st, z["l"], E, alpha, beta)
    l_out = z["l"] if stroke_lengths == "raw" else l_mod
    p = os.path.join(OUT, f"linelets_{scene}_{variant}_test.npz")
    np.savez(p, p0=z["p"], p=z["p"], t=z["t"], l=l_out, keep=keep, l_mod=l_mod,
             inlier_ratio=st["inlier_ratio"], median_resid=st["median_resid"],
             n_vis=st["n_vis"], seed_idx=z["seed_idx"], E=E)
    print(f"  wrote {p}  keep {int(keep.sum())}/{len(keep)}  "
          f"frac drawn long {float((l_mod > z['l']).mean()):.4f}  "
          f"stroke lengths={stroke_lengths} (median {float(np.median(l_out[keep])):.5f})")
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="lego")
    ap.add_argument("--f", type=float, required=True)
    ap.add_argument("--alpha", type=float, required=True)
    ap.add_argument("--beta", type=float, required=True)
    ap.add_argument("--c_tau_r", type=float, default=None)
    ap.add_argument("--c_tau_L", type=float, default=None)
    ap.add_argument("--prefix", default="tgap")
    ap.add_argument("--stroke_lengths", default="raw", choices=["raw", "tuned"])
    args = ap.parse_args()
    sl = args.stroke_lengths

    write_variant(args.scene, args.f, f"{args.prefix}A", 0.0, 0.0, stroke_lengths=sl)
    write_variant(args.scene, args.f, f"{args.prefix}B", args.alpha, args.beta,
                  stroke_lengths=sl)
    if args.c_tau_r is not None:
        write_variant(args.scene, args.f, f"{args.prefix}C",
                      1.0 - args.c_tau_r / 0.50, 1.0 - args.c_tau_L / 0.90,
                      E_mode="ones", stroke_lengths=sl)


if __name__ == "__main__":
    main()
