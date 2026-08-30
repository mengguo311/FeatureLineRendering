"""tier1/scripts/run_plan1.py — Plan #1 STEP B end-to-end:
2DGS-gated multi-view edge fusion -> 3D vector feature lines.

METHOD PATH (mesh-free) : src/{common,render2dgs,gate2dgs,visibility,linelet,dt_pull,
                              linelet_prune,strokes}
EVAL PATH (mesh, ONLY below the banner): scripts/tune_lib.Harness -> mesh_oracle

WHAT IS DIFFERENT FROM M1b (scripts/run_m1b.py), AND WHY
  1. GEOMETRY.  Every geometric quantity comes from a trained 2DGS model instead of the
     vanilla 3DGS ply: the gate signal, the DT target, the pull's occlusion z-buffer, the
     seed cloud, and the local splat scale that sets linelet half-length. STEP A measured
     why: on pixels the GT mesh says are FLAT-and-printed, the bilateral-ribbon dihedral
     reads p50 1.8 deg / p95 7.3 deg on 2DGS normals versus 11.9 / 38.5 on vanilla
     (AUC 0.967 vs 0.696).
  2. THE GATE is the ribbon-on-normals estimator, evaluated at each Canny pixel
     (src/gate2dgs.ribbon_gate_edges) -- the exact estimator STEP A validated. M1b's
     geom_gate used a patch dihedral on vanilla normals, which STEP A shows is the wrong
     signal on the wrong geometry.
  3. SEEDS.  M1b reused the cached M1a per-gaussian OVERALL recipe score, which does not
     exist for a 2DGS surfel cloud. Instead seeds are the surfels with the strongest
     multi-view GATED-edge evidence (gate2dgs.surfel_edge_evidence) -- the spec's
     "backproject the gated 2D edges onto the 2DGS surface". This is only viable BECAUSE
     the gate works: on vanilla 3DGS the raw Canny evidence is dominated by fabric print,
     which is why M1a needed a multi-term ranked recipe in the first place.

Everything else -- the pull optimiser (delta_max=5px trust region, 3-point directional
sampling, Huber), the multi-view consensus prune, the chaining, and BOTH evaluation
protocols -- is imported from the M1b code unchanged, so the comparison is like-for-like.
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

from src import (common, gate2dgs, render2dgs, visibility, linelet, dt_pull,
                 linelet_prune, strokes, view_split)
import run_m1b as RM                      # reuse the M1b evaluation protocol verbatim

OUT = os.path.join(TIER1, "out")


def build_seeds(X, cams, views, dt, dm, f, sigma, min_vis, recipe="overall",
                verbose=True):
    """Top-f surfels by multi-view gated-edge evidence.

    recipe="mean"    : soft evidence only (first cut; saturates, see gate2dgs docstring)
    recipe="overall" : the M1a OVERALL recipe structure -- soft + worst-case q90 +
                       local competition -- ported to the 2DGS surfel cloud.
    """
    t0 = time.time()
    if recipe == "overall":
        D, VIS = gate2dgs.surfel_evidence_matrix(X, cams, views, dt, dm)
        score, nvis = gate2dgs.surfel_score_overall(X, D, VIS)
        del D, VIS
    else:
        score, nvis = gate2dgs.surfel_edge_evidence(X, cams, views, dt, dm, sigma=sigma)
    ok = nvis >= min_vis
    s = np.where(ok, score, -1.0)
    n_keep = int(round(f * int(ok.sum())))
    order = np.argsort(-s, kind="stable")
    idx = np.sort(order[:max(n_keep, 1)])
    if verbose:
        print(f"  [seeds] evidence over {len(views)} views in {time.time()-t0:.1f}s; "
              f"{int(ok.sum())}/{len(X)} surfels seen >={min_vis} views; "
              f"f={f} -> {len(idx)} seeds  "
              f"(score p50 {np.median(score[idx]):.3f}, "
              f"min {score[idx].min():.3f})", flush=True)
    return idx, score, nvis


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="chair")
    ap.add_argument("--model", default=os.path.join(OUT, "2dgs_chair"))
    # --- gate
    ap.add_argument("--tau_geom", type=float, default=None,
                    help="default: read from out/plan1_tau_sweep_<scene>_ribbon.json")
    ap.add_argument("--gate_mode", default="ribbon", choices=["ribbon", "patch"])
    ap.add_argument("--gate_dilate", type=int, default=2)
    ap.add_argument("--no_gate", action="store_true",
                    help="ablation: 2DGS geometry but UNGATED Canny DT")
    ap.add_argument("--edge", default="sharp", choices=sorted(dt_pull.EDGE_SETS))
    # --- seeds
    ap.add_argument("--f", type=float, default=0.30)
    ap.add_argument("--sigma", type=float, default=2.0)
    ap.add_argument("--min_vis", type=int, default=3)
    ap.add_argument("--recipe", default="overall", choices=["mean", "overall"])
    ap.add_argument("--opa_min", type=float, default=0.1)
    # --- pull (M1b defaults, unchanged)
    ap.add_argument("--steps", type=int, default=100)
    ap.add_argument("--lr", type=float, default=0.35)
    ap.add_argument("--delta_max", type=float, default=5.0)
    ap.add_argument("--huber", type=float, default=2.0)
    ap.add_argument("--lam_s", type=float, default=0.02)
    ap.add_argument("--lam_t", type=float, default=0.02)
    ap.add_argument("--rel_tol", type=float, default=0.02)
    ap.add_argument("--view_chunk", type=int, default=25)
    ap.add_argument("--vis_every", type=int, default=25)
    # --- prune (M1b defaults)
    ap.add_argument("--tau_in", type=float, default=1.5)
    ap.add_argument("--min_ratio", type=float, default=0.50)
    ap.add_argument("--max_med", type=float, default=1.5)
    ap.add_argument("--len_thr", type=float, default=0.9)
    ap.add_argument("--len_lo", type=float, default=0.25)
    ap.add_argument("--len_hi", type=float, default=1.5)
    # --- eval / io
    ap.add_argument("--eval_split", default="test", choices=["test", "val", "legacy"])
    ap.add_argument("--viz_views", type=int, nargs="*", default=[0, 25])
    ap.add_argument("--tag", default="plan1")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--no_viz", action="store_true")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    tau = args.tau_geom
    if tau is None:
        p = os.path.join(OUT, f"plan1_tau_sweep_{args.scene}_ribbon.json")
        tau = json.load(open(p))["best_tau"] if os.path.exists(p) else gate2dgs.TAU_GEOM
        print(f"[tau] using tau_geom={tau} (from {'VAL sweep' if os.path.exists(p) else 'default'})")

    # =============================================================== METHOD PATH
    t_all = time.time()
    cams, rgb_paths = common.load_cameras(args.scene)
    S = gate2dgs.load_surfels(args.model, opa_min=args.opa_min)
    X = S["mu"][S["keep"]]
    scale_g = S["scale"][S["keep"]]
    print(f"[{args.scene}] 2DGS model {S['meta']['model_path']} it={S['meta']['iteration']}"
          f"  {len(S['mu'])} surfels -> {len(X)} with opacity>{args.opa_min}", flush=True)

    views = list(view_split.TRAIN)
    t0 = time.time()
    dt, dm, fg, gst = gate2dgs.build_2dgs_caches(
        args.scene, args.model, rgb_paths, cams, views, cfg_name=args.edge,
        tau_geom=(0.0 if args.no_gate else tau), dilate_px=args.gate_dilate,
        mode=("patch" if args.no_gate else args.gate_mode))
    if args.no_gate:
        # rebuild the DT from the raw Canny field (tau=0 would still run the estimator)
        dt = np.stack([dt_pull._dt(dt_pull.edge_map(rgb_paths[v], dt_pull.EDGE_SETS[args.edge])
                                   ).astype(np.float16) for v in views])
        gst = {"n_before": gst["n_before"], "n_after": gst["n_before"]}
    print(f"  [field] {len(views)} TRAIN views, edge='{args.edge}', "
          f"gate={'OFF' if args.no_gate else f'{args.gate_mode} tau={tau}'}, "
          f"{time.time()-t0:.1f}s", flush=True)
    surv = 100.0 * gst["n_after"] / max(gst["n_before"], 1)
    print(f"  [gate] edge px {gst['n_before']} -> {gst['n_after']} ({surv:.1f}% survive)",
          flush=True)

    idx, score, nvis = build_seeds(X, cams, views, dt, dm, args.f, args.sigma,
                                   args.min_vis, recipe=args.recipe)
    seeds_pos = X[idx]

    t0 = time.time()
    L = linelet.init_linelets(seeds_pos, X, scale_g)
    print(f"  [linelet] init {len(L['p0'])} in {time.time()-t0:.1f}s  "
          f"median half-length {np.median(L['l']):.5f} world  "
          f"tangent valid {L['t_valid'].mean():.3f}", flush=True)

    field = dt_pull.PullField(cams, views, dt, dm, fg, device=args.device)
    t0 = time.time()
    res = dt_pull.pull(field, L, steps=args.steps, lr=args.lr,
                       delta_max=args.delta_max, huber_delta=args.huber,
                       lam_s=args.lam_s, lam_t=args.lam_t,
                       opt_tangent=True, opt_length=False, rel_tol=args.rel_tol,
                       two_sided=True, require_fg=False, dir_weight=False,
                       view_chunk=args.view_chunk, vis_every=args.vis_every, lam_a=0.0)
    t_pull = time.time() - t0
    stat = linelet_prune.consensus_statistic(res["resid3"], res["vis"], knn=L["knn"])
    keep, st = linelet_prune.consensus_prune(
        res["resid"], res["vis"], tau_in=args.tau_in, min_ratio=args.min_ratio,
        max_med=args.max_med, resid3=res["resid3"], use_resid3=False,
        keep_frac=None, stat=stat)
    print(f"  [pull] {t_pull:.1f}s  moved px median {np.median(res['move_px']):.2f} "
          f"p90 {np.percentile(res['move_px'], 90):.2f}", flush=True)
    print(f"  [prune] keep {keep.sum()}/{len(keep)} ({keep.mean()*100:.1f}%)  "
          f"inlier_ratio med {np.median(st['inlier_ratio']):.3f}  "
          f"median_resid med {np.median(st['median_resid']):.2f}px", flush=True)
    t_method = time.time() - t_all

    P1 = res["p"]
    T1 = res["t"] if "t" in res else L["t"]
    l1 = res["l"] if "l" in res else L["l"]
    l_tuned = linelet.modulate_length(l1, st["inlier_ratio"], thr=args.len_thr,
                                      lo=args.len_lo, hi=args.len_hi)

    np.savez(os.path.join(OUT, f"linelets_{args.scene}_{args.tag}_test.npz"),
             p0=L["p0"], p=P1, t=T1, l=l1, keep=keep,
             inlier_ratio=st["inlier_ratio"], median_resid=st["median_resid"],
             n_vis=st["n_vis"], seed_idx=idx)

    # ============================================================ EVAL ONLY ====
    from tune_lib import Harness                      # imports mesh_oracle
    ev = {"test": view_split.TEST, "val": view_split.VAL, "legacy": [0, 25]}[args.eval_split]
    h = Harness(args.scene, views=tuple(ev))

    # Visibility during EVAL must come from the geometry the linelets live on, otherwise a
    # correct 2DGS linelet can be culled by the vanilla z-buffer (and vice versa). Replace
    # the harness G-buffers with 2DGS ones; the GT crease labels it scores against are
    # untouched, so the comparison against the M1b baseline stays honest.
    g2, pipe, meta2 = render2dgs.load_2dgs(args.model)
    for v in ev:
        gb2 = render2dgs.render_gbuffer_2dgs(g2, pipe, h.cams[v],
                                             bg_white=meta2.get("white_background", True))
        h.gbufs[v] = {"depth": gb2["depth"], "alpha": gb2["alpha"],
                      "normal": gb2["normal"]}
        h.depth_np[v] = gb2["depth"].cpu().numpy()
    torch.cuda.empty_cache()

    rows = []

    def add(stage, kind, d, n):
        rows.append({"stage": stage, "kind": kind,
                     "P1.5": d[1.5][0], "R1.5": d[1.5][1],
                     "P2.5": d[2.5][0], "R2.5": d[2.5][1], "n": int(n)})

    add("BEFORE  seeds (2DGS evidence)", "points", RM.eval_points(h, seeds_pos), len(idx))
    add("AFTER   pull", "points", RM.eval_points(h, P1), len(P1))
    add("AFTER   pull+prune[spec]", "points", RM.eval_points(h, P1, keep=keep),
        int(keep.sum()))
    add("BEFORE  linelets init", "segments",
        RM.eval_segments(h, L["p0"], L["t"], L["l"]), len(P1))
    add("AFTER   pull", "segments", RM.eval_segments(h, P1, T1, l1), len(P1))
    add("AFTER   pull+prune[spec]", "segments",
        RM.eval_segments(h, P1, T1, l1, keep=keep), int(keep.sum()))
    add("AFTER   pull+prune[tuned+len]", "segments",
        RM.eval_segments(h, P1, T1, l_tuned, keep=keep), int(keep.sum()))

    # ---- chaining into 3D polylines
    ch, kept = strokes.chain_linelets_3d(P1[keep], T1[keep], l1[keep],
                                         conf=st["inlier_ratio"][keep])
    Pk = P1[keep][kept]
    chain3d = [Pk[c] for c in ch]
    nvert = [len(c) for c in ch]
    print(f"  [chain] {int(keep.sum())} linelets -> NMS {int(kept.sum())} -> "
          f"{len(ch)} 3D polylines, vertices/stroke med "
          f"{np.median(nvert) if nvert else 0:.0f} max {max(nvert) if nvert else 0}",
          flush=True)

    print("\n" + "=" * 96)
    print(f"PLAN #1 STEP B — {args.scene}, eval on {args.eval_split.upper()} views {list(ev)}")
    print(f"  gate: {'OFF' if args.no_gate else f'{args.gate_mode}, tau_geom={tau}'}   "
          f"edge px {gst['n_before']} -> {gst['n_after']} ({surv:.1f}% survive)")
    print("=" * 96)
    print(f"{'stage':<32} {'kind':<9} {'P@1.5':>7} {'R@1.5':>7} {'P@2.5':>7} {'R@2.5':>7} "
          f"{'n':>7}")
    for r in rows:
        print(f"{r['stage']:<32} {r['kind']:<9} {r['P1.5']:>7.4f} {r['R1.5']:>7.4f} "
              f"{r['P2.5']:>7.4f} {r['R2.5']:>7.4f} {r['n']:>7}")

    # ---- side-by-side with the vanilla-3DGS M1b baseline
    base = {}
    for variant in ("gated", "ungated"):
        bp = os.path.join(OUT, f"m1b_{args.scene}_{variant}_test.json")
        if os.path.exists(bp):
            base[variant] = json.load(open(bp))
    if base and args.eval_split == "test":
        print("\n" + "-" * 96)
        print("vs vanilla-3DGS M1b baseline (same TEST views, same protocol)")
        print(f"{'pipeline':<34} {'kind':<9} {'P@1.5':>7} {'R@1.5':>7} {'P@2.5':>7} "
              f"{'R@2.5':>7}")
        for variant, b in base.items():
            for br in b["rows"]:
                if br["stage"].startswith("AFTER   pull+prune[spec]"):
                    print(f"{'vanilla-3DGS M1b [' + variant + ']':<34} {br['kind']:<9} "
                          f"{br['P1.5']:>7.4f} {br['R1.5']:>7.4f} {br['P2.5']:>7.4f} "
                          f"{br['R2.5']:>7.4f}")
        for r in rows:
            if r["stage"].startswith("AFTER   pull+prune[spec]"):
                print(f"{'2DGS-gated (Plan #1)':<34} {r['kind']:<9} {r['P1.5']:>7.4f} "
                      f"{r['R1.5']:>7.4f} {r['P2.5']:>7.4f} {r['R2.5']:>7.4f}")
    gate_row = [r for r in rows
                if r["stage"].startswith("AFTER   pull+prune[spec]") and r["kind"] == "points"]
    if gate_row:
        g = gate_row[0]
        ok = (g["P1.5"] >= 0.85) and (g["R1.5"] >= 0.75)
        print(f"\n  END-TO-END GATE (P@1.5>=0.85 AND R@1.5>=0.75, points): "
              f"P {g['P1.5']:.4f}  R {g['R1.5']:.4f}  ==> {'PASS' if ok else 'FAIL'}")
    print("=" * 96, flush=True)

    res_json = {"scene": args.scene, "args": vars(args), "tau_geom": tau,
                "model": S["meta"], "views_pull": len(views),
                "eval_views": [int(x) for x in ev], "gate_stats": gst,
                "n_seeds": int(len(idx)), "n_keep": int(keep.sum()),
                "n_strokes": len(ch), "rows": rows,
                "t_method_s": t_method}
    pj = os.path.join(OUT, f"plan1_{args.scene}_{args.tag}.json")
    json.dump(res_json, open(pj, "w"), indent=1, default=float)
    print(f"wrote {pj}")

    # ---- 3-panel viz: RGB | vanilla-3DGS linelets (old) | 2DGS-gated linelets (new)
    if not args.no_viz:
        vz = np.load(os.path.join(OUT, f"linelets_{args.scene}_gated_test.npz")) \
            if os.path.exists(os.path.join(OUT, f"linelets_{args.scene}_gated_test.npz")) \
            else None
        import run_m1b
        for v in args.viz_views:
            cam = cams[v]
            if v not in h.gbufs:
                gbv = render2dgs.render_gbuffer_2dgs(
                    g2, pipe, cam, bg_white=meta2.get("white_background", True))
                h.gbufs[v] = {"depth": gbv["depth"]}
            rgb = run_m1b.load_rgb_white(rgb_paths[v])
            panels = [run_m1b.panel(rgb, f"RGB  v{v}")]
            for name, (pp, tt, ll, kk, cc) in [
                    ("vanilla-3DGS M1b (old)",
                     (vz["p"], vz["t"], vz["l"], vz["keep"].astype(bool),
                      vz["inlier_ratio"]) if vz is not None else (None,)*5),
                    ("2DGS-gated (new)", (P1, T1, l1, keep, st["inlier_ratio"]))]:
                img = rgb.copy()
                if pp is None:
                    panels.append(run_m1b.panel(img, name + " [missing]"))
                    continue
                vis, _, _ = visibility.visible_mask(pp, cam, h.gbufs[v]["depth"])
                sel = np.where(vis & kk)[0]
                a, b = linelet.endpoints(pp, tt, ll)
                uva, _ = common.project(a, cam)
                uvb, _ = common.project(b, cam)
                for i in sel[np.argsort(cc[sel])]:
                    col = cv2.applyColorMap(
                        np.uint8([[np.clip(cc[i], 0, 1) * 255]]), cv2.COLORMAP_JET)[0, 0]
                    cv2.line(img, (int(np.clip(uva[i, 0], -1e4, 1e4) * 16),
                                   int(np.clip(uva[i, 1], -1e4, 1e4) * 16)),
                             (int(np.clip(uvb[i, 0], -1e4, 1e4) * 16),
                              int(np.clip(uvb[i, 1], -1e4, 1e4) * 16)),
                             (int(col[0]), int(col[1]), int(col[2])), 1, cv2.LINE_8, 4)
                panels.append(run_m1b.panel(img, f"{name}  n={len(sel)}"))
            pth = os.path.join(OUT, f"plan1_{args.scene}_v{v}.png")
            cv2.imwrite(pth, cv2.hconcat(panels))
            print(f"wrote {pth}")


if __name__ == "__main__":
    main()
