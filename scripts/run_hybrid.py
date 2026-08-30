"""STEP 2 — the HYBRID: VANILLA M1a seeds gated by the 2DGS geometric-edge signal.

METHOD PATH (mesh-free): src/{common,render,visibility,linelet,dt_pull,linelet_prune,
                              render2dgs,hybrid_gate,gate2dgs}
EVAL PATH  (mesh, ONLY below the banner): scripts/tune_lib.Harness -> mesh_oracle

WHAT IS AND IS NOT CHANGED vs the vanilla M1b baseline (out/m1b_chair_gated_test.json,
seg P@1.5 = 0.6573 / R = 0.5959):
    CHANGED   the seed set. The vanilla M1a OVERALL seeds (f=0.30) are FILTERED by
              src/hybrid_gate.build_seed_gate: a seed survives if it has 2DGS geometric
              support at its reprojection in >= vote_frac of the TRAIN views where the
              VANILLA z-buffer says it is visible.
    UNCHANGED everything else -- linelets initialised on the vanilla gaussians, the same
              DT target, visibility from the vanilla depth, delta_max=5px, 3-point
              sampling, Huber, the multi-view consensus prune, the same TEST views.
    So any delta is attributable to the seed gate alone.

    --dt selects the DT target so the two streams can be separated:
        vanilla_gated  the baseline's own src/geom_gate field (BASELINE PARITY -- use this
                       to isolate the SEED gate's contribution)
        raw            ungated RGB-Canny
        2dgs           the Plan #1 2DGS-gated edge field (both streams gated)

    --no_seed_gate + --f <matched>  is the control that matters: the gate necessarily
    trades recall for precision, and the M1a score already offers that trade for free by
    lowering f. A hybrid only earns its keep if it beats the SAME SEED COUNT reached by
    lowering f. That control is run explicitly, never assumed.
"""
import argparse
import json
import os
import sys
import time

import cv2
import numpy as np
import torch

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
sys.path.insert(0, os.path.join(TIER1, "scripts/explore/syn"))

from src import (common, render, visibility, linelet, dt_pull, linelet_prune,
                 view_split, hybrid_gate, gate2dgs)
import run_m1b as M                                  # eval/viz helpers, reused verbatim

OUT = os.path.join(TIER1, "out")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="chair")
    ap.add_argument("--f", type=float, default=0.30)
    # ---- the 2DGS seed gate (operating point picked on VAL in STEP 1) ----
    ap.add_argument("--model", default=os.path.join(OUT, "2dgs_chair"))
    ap.add_argument("--signal", default="gradn", choices=["gradn", "dihedral"])
    ap.add_argument("--tau", type=float, default=None)
    ap.add_argument("--tau_q", type=float, default=90.0)
    ap.add_argument("--r", type=int, default=0)
    ap.add_argument("--vote", type=float, default=0.75)
    ap.add_argument("--no_half_pixel", action="store_true")
    ap.add_argument("--no_seed_gate", action="store_true",
                    help="control arm: skip the gate (matched-count f baseline)")
    # ---- DT target ----
    ap.add_argument("--dt", default="vanilla_gated",
                    choices=["vanilla_gated", "raw", "2dgs"])
    ap.add_argument("--edge", default="sharp", choices=sorted(dt_pull.EDGE_SETS))
    ap.add_argument("--gate_theta", type=float, default=20.0)
    ap.add_argument("--gate_tau", type=float, default=0.015)
    ap.add_argument("--gate_dilate", type=int, default=2)
    ap.add_argument("--tau_geom2dgs", type=float, default=6.0,
                    help="ribbon tau for --dt 2dgs (VAL-picked, plan1_tau_sweep ribbon)")
    # ---- pull / prune (identical defaults to the baseline run) ----
    ap.add_argument("--steps", type=int, default=100)
    ap.add_argument("--lr", type=float, default=0.35)
    ap.add_argument("--delta_max", type=float, default=5.0)
    ap.add_argument("--huber", type=float, default=2.0)
    ap.add_argument("--lam_s", type=float, default=0.02)
    ap.add_argument("--lam_t", type=float, default=0.02)
    ap.add_argument("--rel_tol", type=float, default=0.02)
    ap.add_argument("--tau_in", type=float, default=1.5)
    ap.add_argument("--min_ratio", type=float, default=0.50)
    ap.add_argument("--max_med", type=float, default=1.5)
    ap.add_argument("--len_thr", type=float, default=0.9)
    ap.add_argument("--len_lo", type=float, default=0.25)
    ap.add_argument("--len_hi", type=float, default=1.5)
    ap.add_argument("--view_chunk", type=int, default=25)
    ap.add_argument("--vis_every", type=int, default=25)
    ap.add_argument("--eval_split", default="test", choices=["test", "val", "legacy"])
    ap.add_argument("--viz_views", type=int, nargs="*", default=[])
    ap.add_argument("--viz_ref", default=None,
                    help="out/linelets_*.npz of the vanilla-only run, for the middle panel")
    ap.add_argument("--tag", default="_hybrid_test")
    ap.add_argument("--device", default="cuda")
    args = ap.parse_args()
    t_all = time.time()
    torch.cuda.reset_peak_memory_stats()

    # ------------------------------------------------------------ METHOD PATH
    cams, rgb_paths = common.load_cameras(args.scene)
    g = common.load_gaussians(args.scene)
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    X = g["mu"][keep_g]
    scale_g = g["scale"][keep_g]
    print(f"[{args.scene}] {len(X)} de-floatered gaussians", flush=True)

    idx, score = M.get_seeds(args.scene, args.f, X)
    print(f"  [seeds] M1a OVERALL f={args.f} -> {len(idx)} seeds", flush=True)

    views = list(view_split.TRAIN)
    depthmin, fgv = dt_pull.build_geom_cache(args.scene, g, keep_g, cams, views,
                                             device=args.device)

    gate_info = None
    if not args.no_seed_gate:
        t0 = time.time()
        keep_s, gate_info = hybrid_gate.build_seed_gate(
            args.scene, args.model, X[idx], cams, views, depthmin,
            signal=args.signal, tau=args.tau, tau_q=args.tau_q, r=args.r,
            vote_frac=args.vote, rel_tol=args.rel_tol,
            half_pixel=not args.no_half_pixel)
        gate_info["t_s"] = time.time() - t0
        idx = idx[keep_s]
    seeds_pos = X[idx]
    print(f"  [seeds] after 2DGS gate: {len(idx)}", flush=True)

    t0 = time.time()
    L = linelet.init_linelets(seeds_pos, X, scale_g)
    t_init = time.time() - t0
    print(f"  [linelet] init {len(L['p0'])} in {t_init:.1f}s  tangent valid "
          f"{L['t_valid'].mean():.3f}", flush=True)

    t0 = time.time()
    if args.dt == "2dgs":
        DT, _, _, gst = gate2dgs.build_2dgs_caches(
            args.scene, args.model, rgb_paths, cams, views, cfg_name=args.edge,
            tau_geom=args.tau_geom2dgs, mode="ribbon")
        field = dt_pull.PullField(cams, views, DT, depthmin, fgv, device=args.device)
        field.gate_stats = gst
    else:
        gate = (dict(theta=args.gate_theta, tau_depth=args.gate_tau,
                     dilate_px=args.gate_dilate, soft=False)
                if args.dt == "vanilla_gated" else None)
        field = dt_pull.build_field(args.scene, g, keep_g, cams, rgb_paths, views,
                                    cfg_name=args.edge, device=args.device, gate=gate)
    t_cache = time.time() - t0
    gs = getattr(field, "gate_stats", None)
    print(f"  [field] {field.V} train views, edge='{args.edge}', dt='{args.dt}', "
          f"build {t_cache:.1f}s", flush=True)
    if gs:
        print(f"  [dt gate] edge px {gs['n_before']} -> {gs['n_after']} "
              f"({100.0 * gs['n_after'] / max(gs['n_before'], 1):.1f}% survive)", flush=True)

    t0 = time.time()
    res = dt_pull.pull(field, L, steps=args.steps, lr=args.lr,
                       delta_max=args.delta_max, huber_delta=args.huber,
                       lam_s=args.lam_s, lam_t=args.lam_t, opt_tangent=True,
                       opt_length=False, rel_tol=args.rel_tol, two_sided=True,
                       require_fg=False, dir_weight=False,
                       view_chunk=args.view_chunk, vis_every=args.vis_every)
    t_pull = time.time() - t0

    stat = linelet_prune.consensus_statistic(res["resid3"], res["vis"], knn=L["knn"])
    keep, st = linelet_prune.consensus_prune(
        res["resid"], res["vis"], tau_in=args.tau_in, min_ratio=args.min_ratio,
        max_med=args.max_med, resid3=res["resid3"], use_resid3=False, stat=stat)
    keep_t, st_t = linelet_prune.consensus_prune(
        res["resid"], res["vis"], tau_in=1.0, min_ratio=args.min_ratio,
        max_med=args.max_med, resid3=res["resid3"], use_resid3=True)
    vram = torch.cuda.max_memory_allocated() / 2 ** 30
    print(f"  [pull] {t_pull:.1f}s | [prune] spec keep {keep.sum()}/{len(keep)}, "
          f"tuned keep {keep_t.sum()}/{len(keep_t)}", flush=True)

    # ---------------------------------------------------------- EVAL ONLY ----
    from tune_lib import Harness
    ev = {"test": view_split.TEST, "val": view_split.VAL, "legacy": [0, 25]}[args.eval_split]
    h = Harness(args.scene, views=tuple(ev))
    assert len(h.X) == len(X), "harness/method gaussian pool mismatch"

    P0, P1, t1, l1 = L["p0"], res["p"], res["t"], res["l"]
    l_mod_t = linelet.modulate_length(res["l"], st_t["inlier_ratio"], thr=args.len_thr,
                                      lo=args.len_lo, hi=args.len_hi)
    rows = []

    def row(name, e, n, kind):
        rows.append({"stage": name, "kind": kind, "P1.5": e[1.5][0], "R1.5": e[1.5][1],
                     "P2.5": e[2.5][0], "R2.5": e[2.5][1], "n": n})

    pts_before = M.eval_points(h, P0)
    pts_pp = M.eval_points(h, P1, keep=keep)
    pts_tuned = M.eval_points(h, P1, keep=keep_t)
    seg_before = M.eval_segments(h, P0, L["t"], L["l"])
    seg_pp = M.eval_segments(h, P1, t1, l1, keep=keep)
    seg_tuned = M.eval_segments(h, P1, t1, l_mod_t, keep=keep_t)
    row("BEFORE  seeds (gated M1a)", pts_before, int(len(P0)), "points")
    row("AFTER   pull+prune[spec]", pts_pp, int(keep.sum()), "points")
    row("AFTER   pull+prune[tuned]", pts_tuned, int(keep_t.sum()), "points")
    row("BEFORE  linelets init", seg_before, int(len(P0)), "segments")
    row("AFTER   pull+prune[spec]", seg_pp, int(keep.sum()), "segments")
    row("AFTER   pull+prune[tuned+len]", seg_tuned, int(keep_t.sum()), "segments")

    if args.no_seed_gate:
        glab = "OFF"
    else:
        tlab = ("t%g" % args.tau) if args.tau is not None else ("q%g" % args.tau_q)
        glab = (f"{os.path.basename(os.path.normpath(args.model))}/{args.signal}"
                f"/{tlab}/r{args.r}/vote{args.vote}")
    print("\n" + "=" * 96)
    print(f"HYBRID {args.scene}{args.tag}  seed_gate={glab}  dt={args.dt}  "
          f"f={args.f}   TEST views {h.views}")
    print("=" * 96)
    print(f"{'stage':28s} {'kind':9s} {'P@1.5':>7s} {'R@1.5':>7s} {'P@2.5':>7s} "
          f"{'R@2.5':>7s} {'n':>8s}")
    for r_ in rows:
        print(f"{r_['stage']:28s} {r_['kind']:9s} {r_['P1.5']:7.4f} {r_['R1.5']:7.4f} "
              f"{r_['P2.5']:7.4f} {r_['R2.5']:7.4f} {r_['n']:8d}")
    gate_pts = (pts_pp[1.5][0] >= 0.85) and (pts_pp[1.5][1] >= 0.75)
    gate_seg = (seg_pp[1.5][0] >= 0.85) and (seg_pp[1.5][1] >= 0.75)
    print("-" * 96)
    print(f"END-TO-END GATE P@1.5>=0.85 AND R@1.5>=0.75: "
          f"points {'PASS' if gate_pts else 'FAIL'} | "
          f"segments {'PASS' if gate_seg else 'FAIL'}")
    print(f"TUNED rule + length policy: segments P={seg_tuned[1.5][0]:.4f} "
          f"R={seg_tuned[1.5][1]:.4f} (n={int(keep_t.sum())})   "
          f"[vanilla baseline: 0.6573 / 0.5959, n=15091]")

    pngs = []
    if args.viz_views:
        ref = np.load(args.viz_ref) if args.viz_ref else None
        for v in args.viz_views:
            pth = os.path.join(OUT, f"hybrid_{args.scene}_v{v}.png")
            rgb = M.load_rgb_white(h.rgb_paths[v])
            cam = h.cams[v]

            def draw(pp, tt, ll, kk, col=None):
                im = rgb.copy()
                vv, _, _ = visibility.visible_mask(pp, cam, h.gbufs[v]["depth"])
                sel = np.where(vv & kk)[0]
                a, b = linelet.endpoints(pp, tt, ll)
                uva, _ = common.project(a, cam)
                uvb, _ = common.project(b, cam)
                for i in sel:
                    cv2.line(im, (int(np.clip(uva[i, 0], -1e4, 1e4) * 16),
                                  int(np.clip(uva[i, 1], -1e4, 1e4) * 16)),
                             (int(np.clip(uvb[i, 0], -1e4, 1e4) * 16),
                              int(np.clip(uvb[i, 1], -1e4, 1e4) * 16)),
                             col or (0, 0, 255), 1, cv2.LINE_8, 4)
                return im, len(sel)

            panels = [M.panel(rgb, f"RGB  v{v}")]
            if ref is not None:
                im, n = draw(ref["p"], ref["t"], ref["l"], ref["keep"], (0, 0, 255))
                panels.append(M.panel(im, f"VANILLA-ONLY linelets  n={n}"))
            im, n = draw(P1, t1, l1, keep, (0, 160, 0))
            panels.append(M.panel(im, f"VANILLA-SEED + 2DGS-GATE  n={n}"))
            cv2.imwrite(pth, cv2.hconcat(panels))
            pngs.append(pth)
            print(f"  wrote {pth}", flush=True)

    js = {"scene": args.scene, "args": vars(args), "views_pull": field.V,
          "eval_views": list(ev), "dt_gate_stats": gs, "seed_gate": gate_info,
          "n_seeds": int(len(P0)), "n_keep": int(keep.sum()),
          "n_keep_tuned": int(keep_t.sum()), "rows": rows,
          "gate_points": bool(gate_pts), "gate_segments": bool(gate_seg),
          "peak_vram_gb": vram, "pngs": pngs, "t_pull_s": t_pull,
          "total_s": time.time() - t_all}
    jp = os.path.join(OUT, f"hybrid_{args.scene}{args.tag}.json")
    json.dump(js, open(jp, "w"), indent=2, default=float)
    np.savez(os.path.join(OUT, f"linelets_{args.scene}{args.tag}.npz"),
             p0=P0, p=P1, t=t1, l=l1, keep=keep, inlier_ratio=st["inlier_ratio"],
             median_resid=st["median_resid"], n_vis=st["n_vis"], seed_idx=idx)
    print(f"  wrote {jp}  ({time.time() - t_all:.0f}s total)")


if __name__ == "__main__":
    main()
