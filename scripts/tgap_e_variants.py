"""tier1/scripts/tgap_e_variants.py — TGAP robustness: alternative definitions of E.

*** METHOD PATH.  Mesh-free. ***

E had exactly one degree of freedom that tgap_spec.md does not pin down: a linelet is an
OBJECT-SPACE primitive seen from many views, so "the TEED edge response at the candidate's
projected uv" has to be aggregated over views, and the raw sigmoid has to be mapped into
[0,1].  The frozen choice is (threshold 0.5 = TEED's published operating point in this repo,
aggregator = mean over the visible TRAIN views).  If the verdict flips under a different
choice it is a verdict about that choice and not about the mechanism, so three alternatives
are computed and swept as well:

    mean@0.5   FROZEN.  graded response, averaged over the views the pull used.
    max@0.5    the strongest single-view agreement, i.e. "TEED fires here in SOME view".
    mean@0.8   only strong TEED response counts at all -> a much sparser, higher-contrast
               gate, which is the setting most favourable to selectivity.
    frac@0.5   fraction of visible views in which TEED fires above its published threshold,
               i.e. the multi-view-consensus form of the same prior.
"""
import argparse
import os
import sys

import numpy as np
import torch

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))

from src import common, render, dt_pull, view_split, tgap_gate           # noqa: E402

OUT = os.path.join(TIER1, "out")
VARIANTS = ["max@0.5", "mean@0.8", "frac@0.5"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="lego")
    ap.add_argument("--f", type=float, nargs="+", required=True)
    ap.add_argument("--device", default="cuda")
    args = ap.parse_args()

    cams, rgb_paths = common.load_cameras(args.scene)
    g = common.load_gaussians(args.scene)
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    views = list(view_split.TRAIN)
    field = dt_pull.build_field(args.scene, g, keep_g, cams, rgb_paths, views,
                                cfg_name="sharp", device=args.device,
                                gate=dict(theta=20.0, tau_depth=0.015, dilate_px=2,
                                          soft=False))
    for f in args.f:
        src = os.path.join(OUT, f"tgap_pull_{args.scene}_f{f:.2f}.npz")
        z = dict(np.load(src))
        P = torch.as_tensor(z["p"].astype(np.float32), device=field.device)
        W = torch.as_tensor(z["vis"].astype(np.float32), device=field.device)
        out = {}
        for name in VARIANTS:
            kind, thr = name.split("@")
            thr = float(thr)
            E = tgap_gate.teed_edge_maps(args.scene, field.views, thr=thr)
            if kind == "frac":
                E = (E > 0).astype(np.float16)
            Et = torch.tensor(np.ascontiguousarray(E), device=field.device)
            acc = (torch.full((len(P),), -1.0, device=field.device) if kind == "max"
                   else torch.zeros(len(P), device=field.device))
            den = torch.zeros(len(P), device=field.device)
            with torch.no_grad():
                for k0 in range(0, field.V, 25):
                    k1 = min(k0 + 25, field.V)
                    uv, _ = field.project(P, k0, k1)
                    e = field.sample(Et, uv, k0, k1)
                    w = W[k0:k1]
                    if kind == "max":
                        acc = torch.maximum(acc, (e * w + (-1.0) * (1 - w)).max(0).values)
                    else:
                        acc += (e * w).sum(0)
                    den += w.sum(0)
            v = (acc.clamp(min=0.0) if kind == "max" else acc / den.clamp(min=1.0))
            v = torch.where(den > 0, v, torch.zeros_like(v)).clamp(0.0, 1.0)
            out[name] = v.cpu().numpy().astype(np.float64)
            print(f"  f={f:.2f} {name:9s} mean {out[name].mean():.4f} "
                  f"frac>0 {(out[name] > 0).mean():.4f} q90 {np.quantile(out[name], .9):.4f}",
                  flush=True)
        for k, v in out.items():
            z["E_" + k.replace("@", "_").replace(".", "p")] = v
        np.savez(src, **z)
        print(f"  updated {src}", flush=True)


if __name__ == "__main__":
    main()
