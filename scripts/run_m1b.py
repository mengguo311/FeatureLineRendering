"""tier1/scripts/run_m1b.py — M1b end-to-end driver: seeds -> linelets -> DT pull ->
consensus prune -> BEFORE/AFTER evaluation + 3-panel visualisation.

METHOD PATH (mesh-free)  : src/{common,render,visibility,linelet,dt_pull,linelet_prune}
EVAL PATH (mesh, ONLY here, below the banner): scripts/tune_lib.Harness -> mesh_oracle

END-TO-END GATE (chair): precision@1.5px >= 85%  AND  recall@1.5px >= 75%.

Two evaluation protocols are reported, because a linelet is a SEGMENT and M1a scored
POINTS:
  [points]   the literal M1a harness on the linelet centres — apples-to-apples with the
             M1a numbers, and the protocol the gate is quoted in.
  [segments] the projected p+-l*t segment rasterised at 1/16-px precision — this is what
             the NPR line rendering actually draws, so it is the honest number for the
             deliverable. Precision is over drawn pixels, recall over GT crease pixels.
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
                 view_split)

OUT = os.path.join(TIER1, "out")
SYN = os.path.join(TIER1, "scripts/explore/syn")


# ===================================================================== METHOD PATH
SCORE_OVERRIDE = None   # set by --score: use an alternative M1a OVERALL score .npy
                        # (e.g. the same recipe with EDGE_SOURCE="teed"). None = published.


def get_seeds(scene, f, X, verbose=True):
    """M1a seeds = top-f of the OVERALL recipe score (reused, NOT rebuilt).

    Uses the cached per-gaussian score written by scripts/explore/syn/run_final.py;
    if it is absent, runs the same recipe through m1a_seeds.extract_seeds.
    SCORE_OVERRIDE swaps in a score computed from a different photometric edge source;
    everything downstream of the score is untouched, so any delta is the detector's."""
    p = SCORE_OVERRIDE or os.path.join(SYN, f"finalscore_overall_{scene}.npy")
    if os.path.exists(p):
        s = np.load(p)
        if len(s) != len(X):
            raise RuntimeError(f"score/gaussian mismatch {len(s)} vs {len(X)}")
        if verbose:
            print(f"  [seeds] reusing OVERALL score {os.path.relpath(p, TIER1)}")
    else:
        if verbose:
            print("  [seeds] no cached score -> running the OVERALL recipe")
        import m1a_seeds
        _, s, _, _ = m1a_seeds.extract_seeds(scene, "overall", keep_f=f)
    o = np.argsort(-s, kind="stable")
    idx = np.sort(o[:int(round(f * len(X)))])
    return idx, s


# ================================================================== EVAL ONLY ====
# Everything below this banner may touch the GT mesh (via tune_lib.Harness ->
# mesh_oracle). Nothing above it does, and no method module imports anything here.
def raster_segments(h, v, p, t, l, keep=None, shift=4, max_seg_px=64.0):
    """Rasterise the visible linelet segments of view v. Returns (mask[H,W], n_drawn)."""
    cam = h.cams[v]
    vis, uv, _ = visibility.visible_mask(p, cam, h.gbufs[v]["depth"])
    if keep is not None:
        vis = vis & keep
    a, b = linelet.endpoints(p, t, l)
    uva, _ = common.project(a, cam)
    uvb, _ = common.project(b, cam)
    S = 1 << shift
    m = np.zeros((cam.H, cam.W), np.uint8)
    # an endpoint behind the camera projects to garbage; a linelet whose 2D extent is
    # absurd is degenerate, not a line. Drop both rather than streak across the frame.
    za = (cam.w2c[:3, :3] @ a.T).T[:, 2] + cam.w2c[2, 3]
    zb = (cam.w2c[:3, :3] @ b.T).T[:, 2] + cam.w2c[2, 3]
    seg = np.linalg.norm(uvb - uva, axis=1)
    vis = vis & (za > 1e-6) & (zb > 1e-6) & (seg < max_seg_px)
    idx = np.where(vis)[0]
    A = np.clip(uva[idx], -1e4, 1e4) * S
    B = np.clip(uvb[idx], -1e4, 1e4) * S
    for i in range(len(idx)):
        cv2.line(m, (int(A[i, 0]), int(A[i, 1])), (int(B[i, 0]), int(B[i, 1])),
                 1, 1, cv2.LINE_8, shift)
    return m > 0, len(idx)


def eval_segments(h, p, t, l, keep=None, taus=(1.5, 2.5), per_view=False):
    res = {tau: {"p": [], "r": []} for tau in taus}
    npix = []
    for v in h.views:
        mask, _ = raster_segments(h, v, p, t, l, keep=keep)
        cu, cv_, cdt = h.crease[v]
        ys, xs = np.nonzero(mask)
        npix.append(len(ys))
        sdt = (cv2.distanceTransform((~mask).astype(np.uint8), cv2.DIST_L2, 5)
               if mask.any() else np.full(mask.shape, 1e9, np.float32))
        for tau in taus:
            res[tau]["p"].append(float((cdt[ys, xs] <= tau).mean()) if len(ys) else 0.0)
            res[tau]["r"].append(float((sdt[cv_, cu] <= tau).mean()))
    out = {}
    for tau in taus:
        out[tau] = (res[tau]["p"] if per_view else float(np.mean(res[tau]["p"])),
                    res[tau]["r"] if per_view else float(np.mean(res[tau]["r"])))
    out["n_px"] = npix if per_view else int(np.mean(npix))
    return out


def eval_points(h, pos, keep=None, taus=(1.5, 2.5)):
    out = {}
    for tau in taus:
        p, r, n = h.evaluate(pos, extra_mask=keep, tau_p=tau, tau_r=tau)
        out[tau] = (p, r)
        out["n"] = n
    return out


def load_rgb_white(path):
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if im.ndim == 3 and im.shape[2] == 4:
        a = im[:, :, 3:4].astype(np.float32) / 255.0
        return (im[:, :, :3].astype(np.float32) * a + 255.0 * (1 - a)).astype(np.uint8)
    return im[:, :, :3]


def panel(img, label):
    out = img.copy()
    cv2.rectangle(out, (0, 0), (out.shape[1] - 1, 26), (0, 0, 0), -1)
    cv2.putText(out, label, (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                (255, 255, 255), 1, cv2.LINE_AA)
    return out


def viz(h, v, seeds_pos, p, t, l, keep, inl, path, tag=""):
    """3-panel {RGB | seeds before | pulled+pruned linelets after}."""
    rgb = load_rgb_white(h.rgb_paths[v])
    cam = h.cams[v]

    vis0, uv0, _ = visibility.visible_mask(seeds_pos, cam, h.gbufs[v]["depth"])
    before = rgb.copy()
    for u, w in uv0[vis0]:
        if 0 <= u < cam.W and 0 <= w < cam.H:
            cv2.circle(before, (int(round(u)), int(round(w))), 1, (0, 0, 255), -1)

    after = rgb.copy()
    visA, _, _ = visibility.visible_mask(p, cam, h.gbufs[v]["depth"])
    sel = np.where(visA & keep)[0]
    a, b = linelet.endpoints(p, t, l)
    uva, _ = common.project(a, cam)
    uvb, _ = common.project(b, cam)
    S = 16
    order = sel[np.argsort(inl[sel])]          # worst first, best drawn on top
    for i in order:
        c = cv2.applyColorMap(np.uint8([[np.clip(inl[i], 0, 1) * 255]]),
                              cv2.COLORMAP_JET)[0, 0]
        cv2.line(after, (int(np.clip(uva[i, 0], -1e4, 1e4) * S),
                         int(np.clip(uva[i, 1], -1e4, 1e4) * S)),
                 (int(np.clip(uvb[i, 0], -1e4, 1e4) * S),
                  int(np.clip(uvb[i, 1], -1e4, 1e4) * S)),
                 (int(c[0]), int(c[1]), int(c[2])), 1, cv2.LINE_8, 4)

    out = cv2.hconcat([panel(rgb, f"RGB  v{v}"),
                       panel(before, f"BEFORE: M1a seeds  n={int(vis0.sum())}"),
                       panel(after, f"AFTER: pulled+pruned linelets  n={len(sel)}"
                                    f"  {tag}")])
    cv2.imwrite(path, out)
    return path


# ===================================================================== driver ====
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="chair")
    ap.add_argument("--score", default=None,
                    help="alternative M1a OVERALL score .npy (e.g. TEED-sourced). "
                         "Default = the published Canny-sourced score.")
    ap.add_argument("--f", type=float, default=0.30, help="M1a seed keep-fraction")
    ap.add_argument("--views", type=int, default=100, help="train views used for the pull")
    ap.add_argument("--edge", default="sharp", choices=sorted(dt_pull.EDGE_SETS))
    ap.add_argument("--steps", type=int, default=100)
    ap.add_argument("--lr", type=float, default=0.35)
    ap.add_argument("--delta_max", type=float, default=5.0)
    ap.add_argument("--huber", type=float, default=2.0)
    ap.add_argument("--lam_s", type=float, default=0.02)
    ap.add_argument("--lam_t", type=float, default=0.02)
    ap.add_argument("--no_tangent", action="store_true")
    ap.add_argument("--opt_length", action="store_true")
    ap.add_argument("--fg_gate", action="store_true")
    ap.add_argument("--dir_weight", action="store_true")
    ap.add_argument("--rel_tol", type=float, default=0.02)
    ap.add_argument("--one_sided_vis", action="store_true")
    ap.add_argument("--tau_in", type=float, default=1.5)
    ap.add_argument("--min_ratio", type=float, default=0.50)
    ap.add_argument("--max_med", type=float, default=1.5)
    ap.add_argument("--prune_resid3", action="store_true")
    ap.add_argument("--keep_frac", type=float, default=None,
                    help="additionally keep only the top fraction of the measured-best "
                         "mesh-free statistic (linelet_prune.consensus_statistic)")
    ap.add_argument("--len_thr", type=float, default=0.9)
    ap.add_argument("--len_lo", type=float, default=0.25)
    ap.add_argument("--len_hi", type=float, default=1.5)
    ap.add_argument("--len_mod", action="store_true",
                    help="confidence-modulated half-length (beyond spec; reported as the "
                         "TUNED segment row regardless of this flag)")
    ap.add_argument("--lam_a", type=float, default=0.0)
    ap.add_argument("--pull_split", default="train", choices=["train", "all"],
                    help="views the DT pull may consume (train = honest held-out setting)")
    ap.add_argument("--eval_split", default="test", choices=["test", "val", "legacy"],
                    help="views the mesh oracle scores on ('legacy' = the old 0,25)")
    ap.add_argument("--gate", action="store_true",
                    help="geometry-gated DT (src/geom_gate.py) instead of raw RGB-Canny")
    ap.add_argument("--gate_theta", type=float, default=20.0)
    ap.add_argument("--gate_tau", type=float, default=0.015)
    ap.add_argument("--gate_dilate", type=int, default=2)
    ap.add_argument("--gate_soft", action="store_true")
    ap.add_argument("--view_chunk", type=int, default=25)
    ap.add_argument("--vis_every", type=int, default=25)
    ap.add_argument("--tag", default="")
    ap.add_argument("--no_viz", action="store_true")
    ap.add_argument("--device", default="cuda")
    args = ap.parse_args()
    global SCORE_OVERRIDE
    SCORE_OVERRIDE = args.score
    os.makedirs(OUT, exist_ok=True)
    tag = args.tag
    torch.cuda.reset_peak_memory_stats()

    # ------------------------------------------------------------ METHOD PATH
    t_all = time.time()
    cams, rgb_paths = common.load_cameras(args.scene)
    g = common.load_gaussians(args.scene)
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    X = g["mu"][keep_g]
    scale_g = g["scale"][keep_g]
    print(f"[{args.scene}] {len(X)} de-floatered gaussians", flush=True)

    idx, score = get_seeds(args.scene, args.f, X)
    seeds_pos = X[idx]
    print(f"  [seeds] f={args.f} -> {len(idx)} seeds", flush=True)

    t0 = time.time()
    L = linelet.init_linelets(seeds_pos, X, scale_g)
    t_init = time.time() - t0
    print(f"  [linelet] init {len(L['p0'])} linelets in {t_init:.1f}s  "
          f"median half-length {np.median(L['l']):.5f} world "
          f"({np.median(L['l']) / (np.median(np.linalg.norm(X - cams[0].center, axis=1)) / cams[0].f):.2f} px @v0)  "
          f"tangent valid {L['t_valid'].mean():.3f}  median aniso {np.median(L['aniso']):.3f}",
          flush=True)

    if args.pull_split == "train":
        views = list(view_split.TRAIN)
    else:
        step = max(1, len(cams) // args.views)
        views = list(range(0, len(cams), step))[:args.views]
    t0 = time.time()
    gate = (dict(theta=args.gate_theta, tau_depth=args.gate_tau,
                 dilate_px=args.gate_dilate, soft=args.gate_soft) if args.gate else None)
    field = dt_pull.build_field(args.scene, g, keep_g, cams, rgb_paths, views,
                                cfg_name=args.edge, device=args.device, gate=gate)
    t_cache = time.time() - t0
    gs = getattr(field, "gate_stats", None)
    print(f"  [field] {field.V} views ({args.pull_split}), edge='{args.edge}', "
          f"gate={'ON' if args.gate else 'off'}, cache/build {t_cache:.1f}s", flush=True)
    if gs:
        print(f"  [gate] edge px {gs['n_before']} -> {gs['n_after']} "
              f"({100.0 * gs['n_after'] / max(gs['n_before'], 1):.1f}% survive) "
              f"theta>={args.gate_theta} or dd/d>={args.gate_tau}", flush=True)

    t0 = time.time()
    res = dt_pull.pull(field, L, steps=args.steps, lr=args.lr,
                       delta_max=args.delta_max, huber_delta=args.huber,
                       lam_s=args.lam_s, lam_t=args.lam_t,
                       opt_tangent=not args.no_tangent, opt_length=args.opt_length,
                       rel_tol=args.rel_tol, two_sided=not args.one_sided_vis,
                       require_fg=args.fg_gate, dir_weight=args.dir_weight,
                       view_chunk=args.view_chunk, vis_every=args.vis_every,
                       lam_a=args.lam_a)
    t_pull = time.time() - t0

    stat = linelet_prune.consensus_statistic(res["resid3"], res["vis"], knn=L["knn"])
    keep, st = linelet_prune.consensus_prune(
        res["resid"], res["vis"], tau_in=args.tau_in, min_ratio=args.min_ratio,
        max_med=args.max_med, resid3=res["resid3"], use_resid3=args.prune_resid3,
        keep_frac=args.keep_frac, stat=stat)
    t_method = t_init + t_pull + (time.time() - t0 - t_pull)
    vram = torch.cuda.max_memory_allocated() / 2 ** 30
    nv = st["n_vis"]
    print(f"  [pull] {t_pull:.1f}s  moved (max-view px): median "
          f"{np.median(res['move_px']):.2f} p90 {np.percentile(res['move_px'], 90):.2f}  "
          f"n_vis median {np.median(nv):.0f}", flush=True)
    print(f"  [prune] keep {keep.sum()}/{len(keep)} ({keep.mean() * 100:.1f}%)  "
          f"inlier_ratio median {np.median(st['inlier_ratio']):.3f}  "
          f"median_resid median {np.median(st['median_resid']):.2f}px", flush=True)

    # ---------------------------------------------------------- EVAL ONLY ----
    from tune_lib import Harness                      # imports mesh_oracle
    ev = {"test": view_split.TEST, "val": view_split.VAL, "legacy": [0, 25]}[args.eval_split]
    h = Harness(args.scene, views=tuple(ev))
    assert len(h.X) == len(X), "harness/method gaussian pool mismatch"

    P0 = L["p0"]
    P1 = res["p"]
    t1 = res["t"]
    l1 = res["l"]
    t0_ = L["t"]
    l0_ = L["l"]
    # confidence-modulated half-length: the drawn length is itself a precision dial
    l_mod = linelet.modulate_length(l1, st["inlier_ratio"], thr=args.len_thr,
                                    lo=args.len_lo, hi=args.len_hi)
    if args.len_mod:
        l1 = l_mod

    # TUNED prune rule (measured better than the spec's; reported alongside, never
    # silently substituted): 3-point residual at tau_in=1.0 instead of the centre at 1.5.
    keep_t, st_t = linelet_prune.consensus_prune(
        res["resid"], res["vis"], tau_in=1.0, min_ratio=args.min_ratio,
        max_med=args.max_med, resid3=res["resid3"], use_resid3=True)
    l_mod_t = linelet.modulate_length(res["l"], st_t["inlier_ratio"], thr=args.len_thr,
                                      lo=args.len_lo, hi=args.len_hi)

    rows = []
    pts_before = eval_points(h, P0)
    pts_pull = eval_points(h, P1)
    pts_pp = eval_points(h, P1, keep=keep)
    seg_before = eval_segments(h, P0, t0_, l0_)
    seg_pull = eval_segments(h, P1, t1, l1)
    seg_pp = eval_segments(h, P1, t1, l1, keep=keep)
    pts_tuned = eval_points(h, P1, keep=keep_t)
    seg_tuned = eval_segments(h, P1, t1, l_mod_t, keep=keep_t)

    def row(name, e, n, kind):
        rows.append({"stage": name, "kind": kind,
                     "P1.5": e[1.5][0], "R1.5": e[1.5][1],
                     "P2.5": e[2.5][0], "R2.5": e[2.5][1], "n": n})

    row("BEFORE  seeds (M1a)", pts_before, int(len(P0)), "points")
    row("AFTER   pull", pts_pull, int(len(P1)), "points")
    row("AFTER   pull+prune[spec]", pts_pp, int(keep.sum()), "points")
    row("AFTER   pull+prune[tuned]", pts_tuned, int(keep_t.sum()), "points")
    row("BEFORE  linelets init", seg_before, int(len(P0)), "segments")
    row("AFTER   pull", seg_pull, int(len(P1)), "segments")
    row("AFTER   pull+prune[spec]", seg_pp, int(keep.sum()), "segments")
    row("AFTER   pull+prune[tuned+len]", seg_tuned, int(keep_t.sum()), "segments")

    print("\n" + "=" * 96)
    print(f"M1b {args.scene}  (f={args.f}, edge={args.edge}, steps={args.steps}, "
          f"delta_max={args.delta_max}, views={field.V})   views scored: {h.views}")
    print("=" * 96)
    print(f"{'stage':26s} {'kind':9s} {'P@1.5':>7s} {'R@1.5':>7s} {'P@2.5':>7s} "
          f"{'R@2.5':>7s} {'n':>8s}")
    for r in rows:
        print(f"{r['stage']:26s} {r['kind']:9s} {r['P1.5']:7.4f} {r['R1.5']:7.4f} "
              f"{r['P2.5']:7.4f} {r['R2.5']:7.4f} {r['n']:8d}")

    gate_pts = (pts_pp[1.5][0] >= 0.85) and (pts_pp[1.5][1] >= 0.75)
    gate_seg = (seg_pp[1.5][0] >= 0.85) and (seg_pp[1.5][1] >= 0.75)
    print("-" * 96)
    print(f"END-TO-END GATE  P@1.5>=0.85 AND R@1.5>=0.75 : "
          f"points {'PASS' if gate_pts else 'FAIL'} "
          f"(P={pts_pp[1.5][0]:.4f} R={pts_pp[1.5][1]:.4f}) | "
          f"segments {'PASS' if gate_seg else 'FAIL'} "
          f"(P={seg_pp[1.5][0]:.4f} R={seg_pp[1.5][1]:.4f})")
    print(f"TUNED rule (resid3, tau_in=1.0) + length policy: "
          f"points P={pts_tuned[1.5][0]:.4f} R={pts_tuned[1.5][1]:.4f} | "
          f"segments P={seg_tuned[1.5][0]:.4f} R={seg_tuned[1.5][1]:.4f} "
          f"(n={int(keep_t.sum())})")
    print(f"n_linelets {len(P0)} -> {int(keep.sum())} after prune | "
          f"method runtime {t_method:.1f}s (+{t_cache:.1f}s one-time cache) | "
          f"peak VRAM {vram:.2f} GB")

    # ---- measured precision/recall frontier of the mesh-free prune statistic --------
    print("-" * 96)
    print("PRUNE FRONTIER (rank by linelet_prune.consensus_statistic; the spec's fixed "
          "0.50 rule is the row above)")
    print(f"{'keep':>6s} {'n':>7s} {'pts P@1.5':>10s} {'pts R@1.5':>10s} "
          f"{'seg P@1.5':>10s} {'seg R@1.5':>10s}")
    frontier = []
    for kf in (1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3):
        k = keep & (stat >= np.quantile(stat, 1.0 - kf)) if kf < 1.0 else keep
        pe = eval_points(h, P1, keep=k)
        se = eval_segments(h, P1, t1, l1, keep=k)
        frontier.append({"keep_frac": kf, "n": int(k.sum()),
                         "P1.5": pe[1.5][0], "R1.5": pe[1.5][1],
                         "sP1.5": se[1.5][0], "sR1.5": se[1.5][1]})
        print(f"{kf:6.2f} {int(k.sum()):7d} {pe[1.5][0]:10.4f} {pe[1.5][1]:10.4f} "
              f"{se[1.5][0]:10.4f} {se[1.5][1]:10.4f}")

    pngs = []
    if not args.no_viz:
        for v in h.views:
            pth = os.path.join(OUT, f"m1b_{args.scene}{tag}_v{v}.png")
            viz(h, v, P0, P1, t1, l1, keep, st["inlier_ratio"], pth,
                tag=f"edge={args.edge}")
            pngs.append(pth)
            print(f"  wrote {pth}")

    js = {"scene": args.scene, "args": vars(args), "views_pull": field.V,
          "eval_views": list(ev), "gate_stats": gs,
          "n_seeds": int(len(P0)), "n_keep": int(keep.sum()),
          "rows": rows, "gate_points": bool(gate_pts), "gate_segments": bool(gate_seg),
          "n_keep_tuned": int(keep_t.sum()),
          "t_method_s": t_method, "t_cache_s": t_cache, "t_pull_s": t_pull,
          "peak_vram_gb": vram, "pngs": pngs,
          "frontier": frontier,
          "move_px_median": float(np.median(res["move_px"])),
          "move_px_p90": float(np.percentile(res["move_px"], 90)),
          "inlier_ratio_median": float(np.median(st["inlier_ratio"])),
          "n_vis_median": float(np.median(nv)),
          "total_s": time.time() - t_all}
    jp = os.path.join(OUT, f"m1b_{args.scene}{tag}.json")
    json.dump(js, open(jp, "w"), indent=2)
    np.savez(os.path.join(OUT, f"linelets_{args.scene}{tag}.npz"),
             p0=P0, p=P1, t=t1, l=l1, keep=keep, inlier_ratio=st["inlier_ratio"],
             median_resid=st["median_resid"], n_vis=nv, seed_idx=idx)
    print(f"  wrote {jp}")


if __name__ == "__main__":
    main()
