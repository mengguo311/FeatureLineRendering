"""TRACK C.3 — the SEED-level go/no-go: does Canny->TEED move the M1a f-frontier OUTWARD?

*** EVAL-ONLY driver (imports tune_lib.Harness -> mesh). The METHOD path it drives
    (final_recipe with EDGE_SOURCE="teed") is mesh-free. ***

WHY THIS AND NOT THE 2D PIXEL NUMBERS
    recall_trackC_detector.py measures the detectors as detectors: threshold the edge map,
    intersect with GT pixels.  The M1a recipe never does that.  It builds a DISTANCE
    TRANSFORM of the edge map, aggregates exp(-dt/16) over 25 spread views, adds the
    G-buffer ridge term and a local-competition rank, and keeps the top f of gaussians.
    View-inconsistent false edges are attenuated by that aggregate; a 2D per-view precision
    number cannot see that happening.  So the honest question for the deliverable is the one
    HYBRID_RESULTS.md established as the bar:

        at MATCHED SEED COUNT / MATCHED RECALL, does the TEED-sourced score beat the point
        the Canny-sourced score reaches on its own by lowering f?

    Only a TEED point strictly OUTSIDE the Canny f-frontier is evidence that the learned
    detector injected recall the existing dial could not buy.  (Note that "seed count < 2.5x
    Canny" is automatically satisfied here and carries no information: the M1a keep-fraction
    f fixes the seed count at round(f*M) regardless of which detector fed the DT.  The
    informative version of that guard -- seeds needed to reach matched precision -- is
    reported instead.)

WHAT IS REUSED, AND THE SELF-CHECK THAT LICENSES IT
    Only the photometric channel DP changes with the edge source; the G-buffer ridge channel
    DR and the visibility VIS do not.  Both are taken from the existing
    scripts/explore/syn/final_evid_<scene>.npz.  To prove that reuse is sound, DP is
    RECOMPUTED for Canny in this run and asserted equal to the cached DP before any TEED
    number is produced.  If that check fails, nothing downstream is trustworthy and the run
    aborts.

CAVEAT, PRE-EXISTING AND SHARED BY BOTH ARMS
    The M1a evidence views are 25 spread views (final_recipe.N_VIEWS), which include 3 VAL
    and 3 TEST views. That is a property of the published recipe, not of this experiment;
    the Canny and TEED arms consume the IDENTICAL view set, so the comparison between them
    is unaffected. It is flagged because the absolute seed P/R inherits it.
"""
import os
import sys
import json
import time
import argparse

import numpy as np
import torch
from scipy.ndimage import map_coordinates

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
SYN = os.path.join(TIER1, "scripts/explore/syn")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
sys.path.insert(0, SYN)

from src import common, render, visibility, view_split
import final_recipe as FR

OUT = os.path.join(TIER1, "out")
FS = (0.50, 0.45, 0.40, 0.35, 0.30, 0.28, 0.26, 0.24, 0.22, 0.20, 0.18,
      0.15, 0.12, 0.10, 0.08, 0.06, 0.04)


def build_dp(sources, g, keep, cams, rgb_paths, X, views):
    """Per-view photometric DT sampled at each gaussian's projection, for each source.

    Returns {name: DP[V,M]}.  VIS is taken from the cache (identical for all sources) but
    the projections are recomputed, so a mismatch would surface as a broken Canny self-check.
    """
    DPS = {n: np.zeros((len(views), len(X)), np.float32) for n in sources}
    t0 = time.time()
    for vi, v in enumerate(views):
        cam = cams[v]
        gb = render.render_gbuffer(g, keep, cam)
        _, uv, _ = visibility.visible_mask(X, cam, gb["depth"])
        del gb
        torch.cuda.empty_cache()
        uu = np.clip(uv[:, 0], 0, cam.W - 1)
        ww = np.clip(uv[:, 1], 0, cam.H - 1)
        for name, cfg in sources.items():
            FR.set_edge_source(**cfg)
            DPS[name][vi] = map_coordinates(FR.photo_edge_dt(rgb_paths[v]),
                                            [ww, uu], order=1, mode="nearest")
        if vi % 8 == 0:
            print(f"    view {vi}/{len(views)}  {time.time()-t0:.0f}s", flush=True)
    FR.set_edge_source("canny")
    return DPS


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="chair")
    ap.add_argument("--key", default="native", choices=["native", "ms"])
    ap.add_argument("--thrs", type=float, nargs="*",
                    default=[0.5, 0.7, 0.8, 0.9, 0.95])
    ap.add_argument("--sources", nargs="*", default=["teed"],
                    choices=["teed", "union"])
    ap.add_argument("--teed_cache", default=None,
                    help="TEED npz cache dir; default out/teed_edges_<scene>")
    ap.add_argument("--arms_json", default=None,
                    help="JSON {name: set_edge_source kwargs} of EXTRA arms to score "
                         "alongside canny. Used by the TRACK M mechanism ablation, which "
                         "needs edge variants (soft confidence / CC filter / TEED-masked "
                         "Canny) that are not on the source x threshold grid.")
    ap.add_argument("--tag", default="",
                    help="suffix for the output json (keeps TRACK L / TRACK M separate)")
    ap.add_argument("--canny_variants", action="store_true",
                    help="add RE-TUNED Canny arms (sharp / sharp_low). THE control that "
                         "decides whether a LEARNED detector was needed at all, or whether "
                         "un-blurring the existing Canny buys the same recall.")
    args = ap.parse_args()

    g = common.load_gaussians(args.scene)
    keep = render.defloat_mask(g["mu"], g["opacity"])
    X, opa = g["mu"][keep], g["opacity"][keep]
    M = len(X)
    cams, rgb_paths = common.load_cameras(args.scene)
    views = np.unique(np.round(np.linspace(0, len(cams) - 1, FR.N_VIEWS)).astype(int))
    print(f"[seeds] {M} de-floatered gaussians, {len(views)} evidence views", flush=True)

    z = np.load(os.path.join(SYN, f"final_evid_{args.scene}.npz"))
    DP_cached, DR, VIS = z["dp"], z["dr"], z["vis"]
    assert DP_cached.shape == (len(views), M), (DP_cached.shape, (len(views), M))

    teed_cache = args.teed_cache or os.path.join(OUT, f"teed_edges_{args.scene}")
    print(f"[seeds] TEED cache: {teed_cache}", flush=True)
    sources = {"canny": dict(source="canny")}
    if args.canny_variants:
        sources["cannysharp"] = dict(source="canny", cfgs=((0, 50, 150),))
        sources["cannysharplow"] = dict(source="canny", cfgs=((0, 20, 60),))
        sources["cannyunblur"] = dict(source="canny",
                                      cfgs=((0, 100, 200), (0, 75, 150)))
    for src in args.sources:
        for t in args.thrs:
            sources[f"{src}_{args.key}_{t:g}"] = dict(source=src, key=args.key,
                                                      thr=t, nms=True,
                                                      cache=teed_cache)
    if args.arms_json:
        extra = json.load(open(args.arms_json))
        for nm, cfg in extra.items():
            cfg = dict(cfg)
            cfg.setdefault("cache", teed_cache)
            if "cfgs" in cfg:
                cfg["cfgs"] = tuple(tuple(c) for c in cfg["cfgs"])
            sources[nm] = cfg
    print(f"[seeds] building DP for {list(sources)}", flush=True)
    DPS = build_dp(sources, g, keep, cams, rgb_paths, X, views)

    # ---- SELF-CHECK: recomputed Canny DP must reproduce the cached DP
    d = np.abs(DPS["canny"] - DP_cached)
    print(f"[seeds] canny DP self-check: max|d|={d.max():.6f} mean|d|={d.mean():.6g} "
          f"frac>1e-3={float((d > 1e-3).mean()):.6f}", flush=True)
    assert d.max() < 1e-2, "recomputed Canny DP does not reproduce the cache — abort"

    # ---- scores + seed P/R on VAL and TEST
    from tune_lib import Harness                                  # EVAL ONLY
    H = {sp: Harness(args.scene, views=tuple(getattr(view_split, sp.upper())))
         for sp in ("val", "test")}
    assert len(H["val"].X) == M

    res = {"scene": args.scene, "M": int(M), "key": args.key,
           "evidence_views": [int(v) for v in views], "frontiers": {}}
    for name, DP in DPS.items():
        s = FR.score_from_evidence(X, opa, DP, DR, VIS, mode="overall")
        sp_out = os.path.join(SYN, f"finalscore_overall_{args.scene}__{name}.npy")
        np.save(sp_out, s)
        print(f"  [score] {name} -> {os.path.relpath(sp_out, TIER1)}", flush=True)
        order = np.argsort(-s, kind="stable")
        for sp in ("val", "test"):
            rows = []
            for f in FS:
                k = np.zeros(M, bool)
                k[order[:int(round(f * M))]] = True
                p, r, n = H[sp].evaluate(X, extra_mask=k)
                rows.append({"f": f, "P": float(p), "R": float(r), "n": int(n)})
            res["frontiers"].setdefault(sp, {})[name] = rows
            print(f"  [{sp}] {name}: " +
                  "  ".join(f"f{x['f']:.2f} P{x['P']:.3f} R{x['R']:.3f}"
                            for x in rows if x["f"] in (0.30, 0.22, 0.15)), flush=True)

    # ---- does TEED sit OUTSIDE the Canny f-frontier?
    def interp_P_at_R(front, R):
        a = sorted(front, key=lambda x: x["R"])
        rs, ps = [x["R"] for x in a], [x["P"] for x in a]
        if R <= rs[0] or R >= rs[-1]:
            return float("nan")
        return float(np.interp(R, rs, ps))

    def interp_R_at_P(front, P):
        a = sorted(front, key=lambda x: x["P"])
        ps, rs = [x["P"] for x in a], [x["R"] for x in a]
        if P <= ps[0] or P >= ps[-1]:
            return float("nan")
        return float(np.interp(P, ps, rs))

    res["lift"] = {}
    for sp in ("val", "test"):
        base = res["frontiers"][sp]["canny"]
        Rmax_canny = max(x["R"] for x in base)
        for name, front in res["frontiers"][sp].items():
            if name == "canny":
                continue
            rows = []
            for x in front:
                pf = interp_P_at_R(base, x["R"])
                rf = interp_R_at_P(base, x["P"])
                rows.append({"f": x["f"], "P": x["P"], "R": x["R"], "n": x["n"],
                             "canny_P_at_same_R": pf, "LIFT_P": x["P"] - pf,
                             "canny_R_at_same_P": rf, "LIFT_R": x["R"] - rf})
            best_p = max((r for r in rows if np.isfinite(r["LIFT_P"])),
                         key=lambda r: r["LIFT_P"], default=None)
            best_r = max((r for r in rows if np.isfinite(r["LIFT_R"])),
                         key=lambda r: r["LIFT_R"], default=None)
            res["lift"].setdefault(sp, {})[name] = {
                "rows": rows,
                "n_above_frontier": sum(1 for r in rows if r["LIFT_P"] > 0),
                "n_points": len(rows),
                "best_LIFT_P": best_p, "best_LIFT_R": best_r,
                "R_max_teed": max(x["R"] for x in front),
                "R_max_canny": Rmax_canny,
                "dR_max": max(x["R"] for x in front) - Rmax_canny,
            }

    jp = os.path.join(OUT, f"trackC_seeds_{args.scene}{args.tag}.json")
    json.dump(res, open(jp, "w"), indent=2)

    for sp in ("val", "test"):
        print(f"\n===== SEED f-FRONTIER — {sp.upper()} =====", flush=True)
        print(f"{'arm':>20} {'f':>5} {'seedP':>7} {'seedR':>7} {'n':>7} "
              f"{'cannyP@R':>9} {'LIFT_P':>8} {'cannyR@P':>9} {'LIFT_R':>8}", flush=True)
        for x in res["frontiers"][sp]["canny"]:
            print(f"{'canny':>20} {x['f']:5.2f} {x['P']:7.4f} {x['R']:7.4f} "
                  f"{x['n']:7d}", flush=True)
        for name, L in res["lift"][sp].items():
            print("", flush=True)
            for r in L["rows"]:
                print(f"{name:>20} {r['f']:5.2f} {r['P']:7.4f} {r['R']:7.4f} "
                      f"{r['n']:7d} {r['canny_P_at_same_R']:9.4f} "
                      f"{r['LIFT_P']:+8.4f} {r['canny_R_at_same_P']:9.4f} "
                      f"{r['LIFT_R']:+8.4f}", flush=True)
            bp, br = L["best_LIFT_P"], L["best_LIFT_R"]
            sp_ = (f"best LIFT_P {bp['LIFT_P']:+.4f} (f={bp['f']})" if bp
                   else "best LIFT_P n/a")
            sr_ = (f"best LIFT_R {br['LIFT_R']:+.4f} (f={br['f']})" if br
                   else "best LIFT_R n/a")
            print(f"{'':>20} -> above frontier {L['n_above_frontier']}/{L['n_points']}  "
                  f"{sp_}  {sr_}  "
                  f"Rmax {L['R_max_teed']:.4f} vs canny {L['R_max_canny']:.4f} "
                  f"(dR {L['dR_max']:+.4f})", flush=True)
    print(f"\n[seeds] wrote {jp}", flush=True)


if __name__ == "__main__":
    main()
