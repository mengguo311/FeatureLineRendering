"""tier1/scripts/tgap_pull.py — TGAP stage 1: run the METHOD PATH once per f and dump
everything the three arms need, so a whole alpha/beta/global-r grid can be swept without
re-running the DT pull.

*** METHOD PATH ONLY.  Mesh-free.  No mesh_oracle import anywhere in this file. ***

The arms of tgap_spec.md differ ONLY in the post-pull prune/length thresholds, and the pull
is identical for all of them at a given f.  Running it once and dumping (p, t, l, resid3,
vis, E) therefore costs nothing in fidelity and turns a grid search from hours into seconds.
The flags below are the PUBLISHED lego baseline's, byte for byte
(scripts/teedgen_L_m1b.sh: --gate, edge=sharp, pull_split=train, steps=100, lr=0.35,
delta_max=5, and the canny OVERALL score, which is bit-identical to the default score).

--pull_gamma > 0 ADDITIONALLY TESTS THE SPEC'S PROSE CLAUSE "stronger DT-pull".
tgap_spec.md's method paragraph says high-TEED regions should get "relaxed pruning + stronger
DT-pull", but attaches an equation, a knob name and a gate to the pruning half only, and its
tuned set is exactly {alpha, beta, global-r}.  Rather than drop the clause on that technicality
it is implemented here as an UNTUNED AUXILIARY: the DT pull's trust region, which is the only
thing that limits how far a linelet may travel to reach a feature, is widened where the prior
agrees,

    delta_max(x) = 5.0 px * (1 + gamma * E0(x)),   E0 = the TEED response at the SEED p0

using E at the PRE-pull position, because that is what a pull-time gate can actually see.  No
method-path file changes: dt_pull._trust_clamp already compares and rescales elementwise, so a
per-linelet tensor passes straight through, and gamma=0 (the default) reproduces the committed
scalar exactly.  Results are reported as an auxiliary in out/TGAP_RESULTS.md and no frozen gate
is decided on them.

REPRODUCTION CONTROL, asserted in-process: the tuned prune recomputed from the dumped
resid3/vis by src/tgap_gate.tuned_stats must be BIT-IDENTICAL to
linelet_prune.consensus_prune(..., tau_in=1.0, use_resid3=True), and arm A's masks must be
bit-identical to run_m1b's keep_tuned / l_mod_tuned.  If that fails the sweep is measuring
something other than the committed headline stage and the script aborts.
"""
import argparse
import json
import os
import sys
import time

import numpy as np
import torch

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
sys.path.insert(0, os.path.join(TIER1, "scripts/explore/syn"))

from src import (common, render, linelet, dt_pull, linelet_prune, view_split,
                 tgap_gate)

OUT = os.path.join(TIER1, "out")
SYN = os.path.join(TIER1, "scripts/explore/syn")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="lego")
    ap.add_argument("--f", type=float, required=True)
    ap.add_argument("--score", default=None,
                    help="default = the published canny OVERALL score for the scene")
    ap.add_argument("--edge", default="sharp")
    ap.add_argument("--steps", type=int, default=100)
    ap.add_argument("--lr", type=float, default=0.35)
    ap.add_argument("--delta_max", type=float, default=5.0)
    ap.add_argument("--huber", type=float, default=2.0)
    ap.add_argument("--lam_s", type=float, default=0.02)
    ap.add_argument("--lam_t", type=float, default=0.02)
    ap.add_argument("--rel_tol", type=float, default=0.02)
    ap.add_argument("--view_chunk", type=int, default=25)
    ap.add_argument("--vis_every", type=int, default=25)
    ap.add_argument("--gate_theta", type=float, default=20.0)
    ap.add_argument("--gate_tau", type=float, default=0.015)
    ap.add_argument("--gate_dilate", type=int, default=2)
    ap.add_argument("--pull_gamma", type=float, default=0.0,
                    help="AUXILIARY, untuned: widen the DT-pull trust region where the TEED "
                         "prior agrees, delta_max(x) = delta_max*(1 + gamma*E0(x)). "
                         "0 = the committed scalar trust region (default).")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    gtag = "" if args.pull_gamma == 0.0 else f"_g{args.pull_gamma:g}"
    dst = os.path.join(OUT, f"tgap_pull_{args.scene}_f{args.f:.2f}{gtag}.npz")
    if os.path.exists(dst) and not args.force:
        print(f"HAVE {dst} — skipped")
        return

    t_all = time.time()
    cams, rgb_paths = common.load_cameras(args.scene)
    g = common.load_gaussians(args.scene)
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    X = g["mu"][keep_g]
    scale_g = g["scale"][keep_g]

    sp = args.score or os.path.join(SYN, f"finalscore_overall_{args.scene}__canny.npy")
    s = np.load(sp)
    if len(s) != len(X):
        raise RuntimeError(f"score/gaussian mismatch {len(s)} vs {len(X)}")
    o = np.argsort(-s, kind="stable")
    idx = np.sort(o[:int(round(args.f * len(X)))])
    seeds_pos = X[idx]
    print(f"[{args.scene}] f={args.f} -> {len(idx)} seeds of {len(X)} gaussians", flush=True)

    L = linelet.init_linelets(seeds_pos, X, scale_g)
    views = list(view_split.TRAIN)
    gate = dict(theta=args.gate_theta, tau_depth=args.gate_tau,
                dilate_px=args.gate_dilate, soft=False)
    field = dt_pull.build_field(args.scene, g, keep_g, cams, rgb_paths, views,
                                cfg_name=args.edge, device=args.device, gate=gate)
    dmax = args.delta_max
    if args.pull_gamma != 0.0:
        vis0 = field.visibility(torch.as_tensor(L["p0"].astype(np.float32),
                                                device=field.device),
                                rel_tol=args.rel_tol, two_sided=True)
        E0 = tgap_gate.teed_response(field, L["p0"].astype(np.float32), args.scene,
                                     vis=vis0.cpu().numpy(), chunk=args.view_chunk)
        dmax = torch.as_tensor(args.delta_max * (1.0 + args.pull_gamma * E0),
                               dtype=torch.float32, device=field.device)
        print(f"  [pull_gamma={args.pull_gamma}] trust region {float(dmax.min()):.2f}"
              f"-{float(dmax.max()):.2f} px, median {float(dmax.median()):.2f}", flush=True)
    t0 = time.time()
    res = dt_pull.pull(field, L, steps=args.steps, lr=args.lr,
                       delta_max=dmax, huber_delta=args.huber,
                       lam_s=args.lam_s, lam_t=args.lam_t, opt_tangent=True,
                       opt_length=False, rel_tol=args.rel_tol, two_sided=True,
                       require_fg=False, dir_weight=False,
                       view_chunk=args.view_chunk, vis_every=args.vis_every, lam_a=0.0)
    print(f"  [pull] {time.time()-t0:.1f}s over {field.V} TRAIN views", flush=True)

    # ---- E: the frozen TEED gate, over the SAME views and the SAME visibility the
    #      residual statistic used, so nothing but the edge prior is new.
    t0 = time.time()
    E = tgap_gate.teed_response(field, res["p"].astype(np.float32), args.scene,
                                vis=res["vis"].astype(np.float32),
                                chunk=args.view_chunk)
    print(f"  [E] TEED response {time.time()-t0:.1f}s  mean {E.mean():.4f}  "
          f"frac>0 {(E > 0).mean():.4f}  q90 {np.quantile(E, 0.9):.4f}  "
          f"q99 {np.quantile(E, 0.99):.4f}", flush=True)

    # ---- REPRODUCTION CONTROL -------------------------------------------------------
    keep_t, st_t = linelet_prune.consensus_prune(
        res["resid"], res["vis"], tau_in=1.0, min_ratio=0.50, max_med=1.5,
        resid3=res["resid3"], use_resid3=True)
    l_mod_t = linelet.modulate_length(res["l"], st_t["inlier_ratio"], thr=0.9,
                                      lo=0.25, hi=1.5)
    st = tgap_gate.tuned_stats(res["resid3"], res["vis"], tau_in=1.0)
    for k in ("inlier_ratio", "median_resid", "n_vis"):
        assert np.array_equal(st[k], st_t[k]), f"tuned_stats mismatch on {k}"
    kA, lA = tgap_gate.arm_masks(st, res["l"], np.zeros(len(res["l"])), 0.0, 0.0)
    assert np.array_equal(kA, keep_t), "arm A keep != run_m1b keep_tuned"
    assert np.array_equal(lA, l_mod_t), "arm A l_mod != run_m1b l_mod_tuned"
    print(f"  [control] arm A masks reproduce the tuned+len stage bit-identically "
          f"({int(keep_t.sum())}/{len(keep_t)} kept)"
          + ("  [gamma != 0: this is the committed RULE on a MODIFIED pull, "
             "not the committed arm]" if args.pull_gamma else ""), flush=True)

    np.savez(dst, p=res["p"], t=res["t"], l=res["l"],
             resid3=res["resid3"].astype(np.float32), vis=res["vis"],
             E=E, seed_idx=idx, f=np.float64(args.f),
             inlier_ratio=st["inlier_ratio"], median_resid=st["median_resid"],
             n_vis=st["n_vis"])
    meta = {"scene": args.scene, "f": args.f, "pull_gamma": args.pull_gamma,
            "n_seeds": int(len(idx)),
            "n_keep_armA": int(keep_t.sum()), "score": sp,
            "pull_views": [int(v) for v in views], "args": vars(args),
            "E_mean": float(E.mean()), "E_frac_pos": float((E > 0).mean()),
            "total_s": time.time() - t_all}
    json.dump(meta, open(dst.replace(".npz", ".json"), "w"), indent=2)
    print(f"  wrote {dst}  ({time.time()-t_all:.0f}s total)", flush=True)


if __name__ == "__main__":
    main()
