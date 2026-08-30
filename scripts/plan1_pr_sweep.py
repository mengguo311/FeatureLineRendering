"""Plan #1 STEP B — precision/recall sweep: does the 2DGS GATE actually help?

*** EVAL-ONLY DRIVER (imports tune_lib.Harness -> mesh_oracle). The method modules it
calls are mesh-free. ***

WHY THIS EXISTS
    The single-operating-point run (scripts/run_plan1.py) is not a fair comparison against
    the M1b baseline: it produced 28890 linelets against the baseline's 16039, and linelet
    count trades precision against recall directly. A single (P,R) pair from each pipeline
    therefore cannot say which is better. This sweeps the seed fraction f -- the operating
    point dial -- and reports the whole curve, so the baseline's operating point can be read
    off Plan #1's curve at MATCHED recall (and matched count).

THE ABLATION THAT ISOLATES THE GATE
    Both arms run on IDENTICAL 2DGS geometry, identical seeds-from-evidence machinery,
    identical pull/prune/eval. The only difference is whether the DT target is the gated
    edge field E_v = A_v AND dilate(G_v > tau_geom) or the raw Canny field A_v. Any gap
    between the two curves is the gate's contribution and nothing else -- unlike the
    comparison against M1b, which also changes the reconstruction, the seed recipe and the
    splat scale at the same time.

    NOTE the seed evidence is read from the SAME field the pull uses, so `gated` and
    `ungated` also differ in which surfels get selected. That is deliberate: it is how the
    gate would actually be deployed. The `--fixed_seeds` flag freezes the seed set to the
    ungated one so the DT-target effect can be separated from the seed-selection effect.
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

from src import (common, gate2dgs, render2dgs, linelet, dt_pull, linelet_prune,
                 view_split)
import run_m1b as RM

OUT = os.path.join(TIER1, "out")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="chair")
    ap.add_argument("--model", default=os.path.join(OUT, "2dgs_chair"))
    ap.add_argument("--tau_geom", type=float, default=12.0)
    ap.add_argument("--gate_mode", default="patch", choices=["patch", "ribbon"])
    ap.add_argument("--gate_dilate", type=int, default=2)
    ap.add_argument("--edge", default="sharp")
    ap.add_argument("--fracs", type=float, nargs="*",
                    default=[0.03, 0.06, 0.10, 0.15, 0.22, 0.30, 0.45])
    ap.add_argument("--arms", nargs="*", default=["gated", "ungated"])
    ap.add_argument("--fixed_seeds", action="store_true")
    ap.add_argument("--sigma", type=float, default=2.0)
    ap.add_argument("--min_vis", type=int, default=3)
    ap.add_argument("--steps", type=int, default=100)
    ap.add_argument("--recipe", default="overall", choices=["mean", "overall"],
                    help="mean = first-cut soft evidence (saturates); overall = the "
                         "M1a OVERALL recipe structure ported to 2DGS surfels")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    cams, rgb_paths = common.load_cameras(args.scene)
    S = gate2dgs.load_surfels(args.model)
    X, scale_g = S["mu"][S["keep"]], S["scale"][S["keep"]]
    views = list(view_split.TRAIN)
    print(f"[pr sweep] {args.scene}: {len(X)} surfels, {len(views)} TRAIN views", flush=True)

    # ---- both fields, built once
    fields, gstats = {}, {}
    dt_g, dm, fg, gst = gate2dgs.build_2dgs_caches(
        args.scene, args.model, rgb_paths, cams, views, cfg_name=args.edge,
        tau_geom=args.tau_geom, dilate_px=args.gate_dilate, mode=args.gate_mode)
    fields["gated"] = dt_g
    gstats["gated"] = gst
    dt_u = np.stack([dt_pull._dt(dt_pull.edge_map(rgb_paths[v],
                                                  dt_pull.EDGE_SETS[args.edge])
                                 ).astype(np.float16) for v in views])
    fields["ungated"] = dt_u
    gstats["ungated"] = {"n_before": gst["n_before"], "n_after": gst["n_before"]}
    print(f"  [gate] {gst['n_before']} -> {gst['n_after']} edge px "
          f"({100.0*gst['n_after']/max(gst['n_before'],1):.1f}% survive) "
          f"tau_geom={args.tau_geom} mode={args.gate_mode}", flush=True)

    # ---- evidence per arm, once
    ev_score, ev_nvis = {}, {}
    for arm in args.arms:
        t0 = time.time()
        if args.recipe == "overall":
            D, VIS = gate2dgs.surfel_evidence_matrix(X, cams, views, fields[arm], dm)
            ev_score[arm], ev_nvis[arm] = gate2dgs.surfel_score_overall(X, D, VIS)
            del D, VIS
        else:
            ev_score[arm], ev_nvis[arm] = gate2dgs.surfel_edge_evidence(
                X, cams, views, fields[arm], dm, sigma=args.sigma)
        print(f"  [seeds/{arm}] recipe={args.recipe} in {time.time()-t0:.1f}s", flush=True)

    # =========================================================== EVAL ONLY ====
    from tune_lib import Harness
    ev = view_split.TEST
    h = Harness(args.scene, views=tuple(ev))
    g2, pipe, meta2 = render2dgs.load_2dgs(args.model)
    for v in ev:
        gb2 = render2dgs.render_gbuffer_2dgs(g2, pipe, h.cams[v],
                                             bg_white=meta2.get("white_background", True))
        h.gbufs[v] = {"depth": gb2["depth"], "alpha": gb2["alpha"]}
        h.depth_np[v] = gb2["depth"].cpu().numpy()
    del g2
    torch.cuda.empty_cache()
    print(f"  [eval] harness on TEST views {list(ev)}, 2DGS occlusion z-buffer", flush=True)

    rows = []
    for arm in args.arms:
        field = dt_pull.PullField(cams, views, fields[arm], dm, fg, device="cuda")
        sc = ev_score["ungated" if args.fixed_seeds else arm]
        nv = ev_nvis["ungated" if args.fixed_seeds else arm]
        ok = nv >= args.min_vis
        s = np.where(ok, sc, -1.0)
        order = np.argsort(-s, kind="stable")
        for f in args.fracs:
            t0 = time.time()
            n_keep = max(int(round(f * int(ok.sum()))), 16)
            idx = np.sort(order[:n_keep])
            L = linelet.init_linelets(X[idx], X, scale_g)
            res = dt_pull.pull(field, L, steps=args.steps, lr=0.35, delta_max=5.0,
                               huber_delta=2.0, lam_s=0.02, lam_t=0.02,
                               opt_tangent=True, opt_length=False, rel_tol=0.02,
                               two_sided=True, require_fg=False, dir_weight=False,
                               view_chunk=25, vis_every=25, lam_a=0.0, verbose=False)
            stat = linelet_prune.consensus_statistic(res["resid3"], res["vis"],
                                                     knn=L["knn"])
            keep, st = linelet_prune.consensus_prune(
                res["resid"], res["vis"], tau_in=1.5, min_ratio=0.50, max_med=1.5,
                resid3=res["resid3"], use_resid3=False, keep_frac=None, stat=stat)
            pts = RM.eval_points(h, res["p"], keep=keep)
            seg = RM.eval_segments(h, res["p"], res["t"], res["l"], keep=keep)
            r = {"arm": arm, "f": f, "n_seeds": int(len(idx)), "n_keep": int(keep.sum()),
                 "pts_P1.5": pts[1.5][0], "pts_R1.5": pts[1.5][1],
                 "pts_P2.5": pts[2.5][0], "pts_R2.5": pts[2.5][1],
                 "seg_P1.5": seg[1.5][0], "seg_R1.5": seg[1.5][1],
                 "seg_P2.5": seg[2.5][0], "seg_R2.5": seg[2.5][1]}
            rows.append(r)
            print(f"  [{arm:>7} f={f:<5}] n={r['n_keep']:>6}  "
                  f"points P {r['pts_P1.5']:.4f} R {r['pts_R1.5']:.4f} | "
                  f"segments P {r['seg_P1.5']:.4f} R {r['seg_R1.5']:.4f}  "
                  f"({time.time()-t0:.0f}s)", flush=True)
        del field
        torch.cuda.empty_cache()

    # ---- baseline points
    base = {}
    for variant in ("gated", "ungated"):
        bp = os.path.join(OUT, f"m1b_{args.scene}_{variant}_test.json")
        if os.path.exists(bp):
            b = json.load(open(bp))
            got = {}
            for br in b["rows"]:
                if br["stage"].startswith("AFTER   pull+prune[spec]"):
                    got[br["kind"]] = br
            base[variant] = {"n": b["n_keep"], **{f"{k}": v for k, v in got.items()}}

    print("\n" + "=" * 104)
    print(f"PLAN #1 PR SWEEP — {args.scene}, TEST views, 2DGS geometry both arms")
    print(f"{'arm':>8} {'f':>6} {'n':>7} | {'pts P@1.5':>10} {'pts R@1.5':>10} | "
          f"{'seg P@1.5':>10} {'seg R@1.5':>10} {'seg P@2.5':>10} {'seg R@2.5':>10}")
    print("-" * 104)
    for r in rows:
        print(f"{r['arm']:>8} {r['f']:>6} {r['n_keep']:>7} | {r['pts_P1.5']:>10.4f} "
              f"{r['pts_R1.5']:>10.4f} | {r['seg_P1.5']:>10.4f} {r['seg_R1.5']:>10.4f} "
              f"{r['seg_P2.5']:>10.4f} {r['seg_R2.5']:>10.4f}")
    print("-" * 104)
    for variant, b in base.items():
        for kind in ("points", "segments"):
            if kind in b:
                br = b[kind]
                pre = "pts" if kind == "points" else "seg"
                print(f"{'M1b/' + variant:>8} {'--':>6} {b['n']:>7} | "
                      + (f"{br['P1.5']:>10.4f} {br['R1.5']:>10.4f} | "
                         f"{'':>10} {'':>10} {'':>10} {'':>10}" if kind == "points"
                         else f"{'':>10} {'':>10} | {br['P1.5']:>10.4f} "
                              f"{br['R1.5']:>10.4f} {br['P2.5']:>10.4f} "
                              f"{br['R2.5']:>10.4f}"))
    print("=" * 104, flush=True)

    tag = f"_{args.tag}" if args.tag else ""
    pj = os.path.join(OUT, f"plan1_pr_sweep_{args.scene}{tag}.json")
    json.dump({"scene": args.scene, "args": vars(args), "gate_stats": gstats,
               "rows": rows, "baseline": base}, open(pj, "w"), indent=1, default=float)
    print(f"wrote {pj}")

    # ---- PR plot
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    for ax, pre, name in ((axes[0], "pts", "points"), (axes[1], "seg", "segments")):
        for arm, col in (("gated", "tab:blue"), ("ungated", "tab:red")):
            rr = [r for r in rows if r["arm"] == arm]
            if not rr:
                continue
            ax.plot([r[f"{pre}_R1.5"] for r in rr], [r[f"{pre}_P1.5"] for r in rr],
                    "o-", color=col, label=f"2DGS {arm} (tau={args.tau_geom})")
            for r in rr:
                ax.annotate(f"{r['n_keep']//1000}k", (r[f"{pre}_R1.5"], r[f"{pre}_P1.5"]),
                            fontsize=6, xytext=(3, 3), textcoords="offset points")
        for variant, mk in (("gated", "*"), ("ungated", "s")):
            if variant in base and name in base[variant]:
                br = base[variant][name]
                ax.plot([br["R1.5"]], [br["P1.5"]], mk, color="k", markersize=12,
                        label=f"vanilla-3DGS M1b [{variant}]")
        ax.axhline(0.85, color="g", ls=":", lw=1)
        ax.axvline(0.75, color="g", ls=":", lw=1)
        ax.set_xlabel("recall @1.5px")
        ax.set_ylabel("precision @1.5px")
        ax.set_title(f"{args.scene} — {name} (TEST views); green = end-to-end gate")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=7)
    plt.tight_layout()
    pp = os.path.join(OUT, f"plan1_pr_sweep_{args.scene}{tag}.png")
    plt.savefig(pp, dpi=120)
    print(f"wrote {pp}")


if __name__ == "__main__":
    main()
