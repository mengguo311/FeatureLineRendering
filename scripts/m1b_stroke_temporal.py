"""tier1/scripts/m1b_stroke_temporal.py — STEP 06 headline: forward-warped STROKE
temporal residual, OURS (object-space carrier) vs BASELINE (naive image-space Canny).

METHOD PATH ONLY for both pipelines and for the metric (src/{strokes,stroke_metric}).
The GT mesh is touched solely by the optional --ablation block, which scores chair FP
density inside GT-flat regions; it is imported there and nowhere else.

Camera path: interpolated poses between two HELD-OUT TEST views. Neither pipeline has
ever optimised against them (the DT pull consumed TRAIN views only).
"""
import argparse
import json
import os
import sys
import time

import cv2
import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))

from src import common, render, visibility, strokes, stroke_metric, view_split
from src import render2dgs
import temporal_m1b as T

OUT = os.path.join(TIER1, "out")


# ------------------------------------------------------------------ stroke sources
def ours_strokes(chain3d, cam, depth, min_pts=2, fg=None):
    """Project the static 3D stroke graph into one camera; split at occlusion."""
    out = []
    for V in chain3d:
        vis, uv, _ = visibility.visible_mask(V, cam, depth)
        inb = (uv[:, 0] >= 0) & (uv[:, 0] < cam.W) & (uv[:, 1] >= 0) & (uv[:, 1] < cam.H)
        good = vis & inb
        if fg is not None:
            uu = np.clip(np.round(uv[:, 0]).astype(int), 0, cam.W - 1)
            vv = np.clip(np.round(uv[:, 1]).astype(int), 0, cam.H - 1)
            good = good & fg[vv, uu]
        if good.sum() < min_pts:
            continue
        run = []
        for i, g in enumerate(good):
            if g:
                run.append(uv[i])
            elif len(run) >= min_pts:
                out.append(np.array(run))
                run = []
            else:
                run = []
        if len(run) >= min_pts:
            out.append(np.array(run))
    return out


def baseline_strokes(gray, lo, hi, min_len, eps, fg=None):
    """fg (optional): restrict the Canny map to the object interior BEFORE tracing.

    Why this control exists. The baseline's Canny fires hard on the object silhouette
    against the background, where the gaussian z-buffer is empty, so ~20% of its strokes
    cannot be forward-warped at all and would be charged as popping — an artefact of the
    warp operator rather than of the baseline. Restricting both pipelines to lines on the
    object interior removes that at source and compares like with like (our linelets are
    interior crease carriers and cannot draw silhouettes either)."""
    import cv2
    e = cv2.Canny(gray.astype(np.uint8), lo, hi)
    if fg is not None:
        e = e * fg.astype(np.uint8)
    return strokes.trace_polylines(e > 0, min_len=min_len, approx_eps=eps)


def frame_data(g, keep_g, cam, chain3d, args, g2=None):
    """g2 = (gaussians, pipe, bg_white) of a trained 2DGS model, or None.

    When given, ONLY the occlusion test that projects the 3D stroke graph uses the 2DGS
    z-buffer -- because that is the surface those strokes were built on, and culling them
    against a different reconstruction's depth would drop correct strokes. Everything the
    METRIC touches (the warp depth, the baseline's gray image, the foreground mask) stays
    on the vanilla render for BOTH pipelines, so the operator is identical and the numbers
    remain comparable with the published --variant gated/ungated runs.
    """
    gb = render.render_gbuffer(g, keep_g, cam, with_albedo=True)
    depth = gb["depth"].detach().cpu().numpy()
    alb = gb["albedo"].detach().cpu().numpy()
    gray = np.clip(alb.mean(2) * 255.0, 0, 255).astype(np.uint8)
    fg = None
    if args.fg_only:
        import cv2
        a = (gb["alpha"].detach().cpu().numpy() > 0.5).astype(np.uint8)
        fg = cv2.erode(a, np.ones((2 * args.fg_erode + 1,) * 2, np.uint8)) > 0
    if g2 is not None:
        gb2 = render2dgs.render_gbuffer_2dgs(g2[0], g2[1], cam, bg_white=g2[2])
        depth_ours = gb2["depth"]
    else:
        depth_ours = gb["depth"]
    A = ours_strokes(chain3d, cam, depth_ours, fg=fg)
    B = baseline_strokes(gray, args.canny_lo, args.canny_hi, args.min_len,
                         args.approx_eps, fg=fg)
    del gb
    if g2 is not None:
        del gb2
    return {"depth": depth, "gray": gray, "A": A, "B": B, "cam": cam}


# ----------------------------------------------------------------------- the metric
def sequence_metrics(frames, args):
    """Forward-warp every stroke of frame t into t+1 and match. Identical operator for
    both pipelines."""
    acc = {p: {"fre": [], "cha": [], "pop": [], "unm": [], "cut": [],
               "n": [], "len": [], "drop": []} for p in ("A", "B")}
    for i in range(len(frames) - 1):
        f0, f1 = frames[i], frames[i + 1]
        for p in ("A", "B"):
            src, dst = f0[p], f1[p]
            acc[p]["n"].append(len(src))
            acc[p]["len"].append(float(np.mean([len(q) for q in src])) if src else 0.0)
            w, surv = stroke_metric.warp_strokes(src, f0["depth"], f0["cam"], f1["cam"])
            dropped = int((~surv).sum()) if len(surv) else 0
            m = stroke_metric.match_strokes(
                w, dst, n_resample=args.n_resample, max_cand=args.max_cand,
                cand_radius=args.cand_radius, match_thresh=args.match_thresh)
            pp = stroke_metric.pop_penalty(m, n_dropped_by_warp=dropped)
            if len(m["frechet"]):
                acc[p]["fre"].append(m["frechet"])
                acc[p]["cha"].append(m["chamfer"])
            acc[p]["pop"].append(pp["P_pop"])
            acc[p]["unm"].append(pp["unmatched_frac"])
            acc[p]["cut"].append(pp["cut_frac"])
            acc[p]["drop"].append(dropped / max(len(src), 1))
    out = {}
    for p in ("A", "B"):
        fre = np.concatenate(acc[p]["fre"]) if acc[p]["fre"] else np.zeros(0)
        cha = np.concatenate(acc[p]["cha"]) if acc[p]["cha"] else np.zeros(0)
        out[p] = {
            "frechet_median": float(np.median(fre)) if len(fre) else float("nan"),
            "frechet_mean": float(fre.mean()) if len(fre) else float("nan"),
            "frechet_p90": float(np.percentile(fre, 90)) if len(fre) else float("nan"),
            "chamfer_median": float(np.median(cha)) if len(cha) else float("nan"),
            "P_pop": float(np.mean(acc[p]["pop"])),
            "unmatched_frac": float(np.mean(acc[p]["unm"])),
            "cut_frac": float(np.mean(acc[p]["cut"])),
            "n_strokes_per_frame": float(np.mean(acc[p]["n"])),
            "mean_vertices_per_stroke": float(np.mean(acc[p]["len"])),
            "n_matched_total": int(len(fre)),
            "warp_dropped_frac": float(np.mean(acc[p]["drop"])),
        }
    return out


def build_chains(scene, variant, args, verbose=True):
    z = np.load(os.path.join(OUT, f"linelets_{scene}_{variant}_test.npz"))
    keep = z["keep"].astype(bool)
    if args.carrier_persistence:
        keep = keep & (z["inlier_ratio"] >= args.cp_ratio) & (z["n_vis"] >= args.cp_views)
    p, t, l = z["p"][keep], z["t"][keep], z["l"][keep]
    conf = z["inlier_ratio"][keep]
    t0 = time.time()
    ch, kept = strokes.chain_linelets_3d(
        p, t, l, conf=conf, nms_radius_mult=args.nms_mult, k=args.knn,
        cos_tan=args.cos_tan, cos_col=args.cos_col, gap_mult=args.gap_mult,
        min_nodes=args.min_nodes)
    P = p[kept]
    chain3d = [P[c] for c in ch]
    if verbose:
        ln = [len(c) for c in ch]
        print(f"  [chain] {scene}/{variant}: {keep.sum()} linelets -> NMS {kept.sum()} "
              f"-> {len(ch)} strokes, vertices/stroke med {np.median(ln) if ln else 0:.0f} "
              f"max {max(ln) if ln else 0} ({time.time()-t0:.1f}s)", flush=True)
    return chain3d, {"n_linelets": int(keep.sum()), "n_nms": int(kept.sum()),
                     "n_strokes": len(ch),
                     "median_vertices": float(np.median([len(c) for c in ch])) if ch else 0.0}


def run_scene(scene, args):
    cams, _ = common.load_cameras(scene)
    g = common.load_gaussians(scene)
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    g2 = None
    if args.geom2dgs:
        _g2, _pipe, _m2 = render2dgs.load_2dgs(os.path.expanduser(args.geom2dgs))
        g2 = (_g2, _pipe, _m2.get("white_background", True))
        print(f"  [{scene}] OURS occlusion z-buffer from 2DGS "
              f"{_m2['model_path']} it={_m2['iteration']}", flush=True)
    chain3d, cinfo = build_chains(scene, args.variant, args)
    target = np.median(g["mu"][keep_g], axis=0)          # mesh-free scene centre
    traj = ("raw interp_cameras (rotation and centre slerped independently; CLIPS the "
            "object out of frame)" if args.raw_path else
            "look-at-corrected orbit (object stays framed)")
    res = {"scene": scene, "chain": cinfo, "variant": args.variant,
           "trajectory": f"TEST views {args.view_a}->{args.view_b}, {traj}",
           "orbit_target": [float(x) for x in target], "by_frames": {}}
    print(f"  [{scene}] trajectory: {traj}", flush=True)
    for nf in args.frames:
        path = (T.interp_cameras(cams[args.view_a], cams[args.view_b], nf)
                if args.raw_path else
                T.orbit_cameras(cams[args.view_a], cams[args.view_b], nf, target))
        t0 = time.time()
        frames = [frame_data(g, keep_g, c, chain3d, args, g2=g2) for c in path]
        m = sequence_metrics(frames, args)
        m["_seconds"] = time.time() - t0
        res["by_frames"][str(nf)] = m
        print(f"  [{scene}] {nf:4d} frames | OURS frechet_med "
              f"{m['A']['frechet_median']:.3f} P_pop {m['A']['P_pop']:.3f} "
              f"| BASE frechet_med {m['B']['frechet_median']:.3f} "
              f"P_pop {m['B']['P_pop']:.3f}  ({m['_seconds']:.0f}s)", flush=True)
        if nf == args.frames[0]:
            _dump_vis(scene, frames[len(frames) // 2], args)
    return res


def _dump_vis(scene, fr, args):
    """Write the vector stroke-path figures.

    `--viz_tag` (default "", i.e. the published file names bit-for-bit) namespaces these
    four files.  Without it EVERY invocation of this script for a scene overwrites the
    PUBLISHED M1b stroke paths out/m1b_vector_<scene>_{A_ours,B_baseline}.{svg,png}, which
    carry no --tag of their own -- an unguarded clobber that has already happened once.
    Any run that is not re-deriving the published figures must pass a non-empty --viz_tag."""
    H, W = fr["depth"].shape
    vt = getattr(args, "viz_tag", "") or ""
    for p, tag in (("A", "A_ours"), ("B", "B_baseline")):
        strokes.write_svg(os.path.join(OUT, f"m1b_vector_{scene}{vt}_{tag}.svg"),
                          fr[p], W, H, width=1.2)
        m = strokes.raster_polylines(fr[p], H, W)
        img = np.full((H, W, 3), 255, np.uint8)
        img[m] = (20, 20, 20)
        cv2.imwrite(os.path.join(OUT, f"m1b_vector_{scene}{vt}_{tag}.png"), img)
    print(f"    wrote out/m1b_vector_{scene}{vt}_{{A_ours,B_baseline}}.{{svg,png}} "
          f"(OURS {len(fr['A'])} strokes, BASELINE {len(fr['B'])})", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", nargs="+", default=["lego", "chair"])
    ap.add_argument("--frames", type=int, nargs="+", default=[30, 60, 120, 240])
    ap.add_argument("--variant", default="ungated")
    ap.add_argument("--viz_tag", default="",
                    help="namespace for the four out/m1b_vector_<scene>*.{svg,png} figures. "
                         "Default \"\" reproduces the PUBLISHED file names exactly; pass a "
                         "non-empty value from any experiment that must not overwrite them.")
    ap.add_argument("--view_a", type=int, default=5)
    ap.add_argument("--view_b", type=int, default=15)
    # chaining
    ap.add_argument("--nms_mult", type=float, default=1.0)
    ap.add_argument("--knn", type=int, default=10)
    ap.add_argument("--cos_tan", type=float, default=0.60)
    ap.add_argument("--cos_col", type=float, default=0.50)
    ap.add_argument("--gap_mult", type=float, default=4.0)
    ap.add_argument("--min_nodes", type=int, default=3)
    # baseline
    ap.add_argument("--canny_lo", type=int, default=50)
    ap.add_argument("--canny_hi", type=int, default=150)
    ap.add_argument("--min_len", type=int, default=4)
    ap.add_argument("--approx_eps", type=float, default=1.0)
    # metric
    ap.add_argument("--n_resample", type=int, default=16)
    ap.add_argument("--max_cand", type=int, default=6)
    ap.add_argument("--cand_radius", type=float, default=40.0)
    ap.add_argument("--match_thresh", type=float, default=3.0)
    # ablation
    ap.add_argument("--carrier_persistence", action="store_true")
    ap.add_argument("--cp_ratio", type=float, default=0.8)
    ap.add_argument("--cp_views", type=int, default=20)
    ap.add_argument("--raw_path", action="store_true",
                    help="use the OLD uncorrected interp_cameras path (clips the object "
                         "out of frame); default is the look-at-corrected orbit")
    ap.add_argument("--fg_only", action="store_true",
                    help="control: restrict BOTH pipelines to the object interior, so "
                         "silhouette strokes with no depth are not charged as popping")
    ap.add_argument("--fg_erode", type=int, default=2)
    ap.add_argument("--geom2dgs", default=None,
                    help="path to a trained 2DGS model; OURS strokes are then occlusion-"
                         "tested against its z-buffer (Plan #1). Metric operator unchanged.")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    table = {"metric": "forward-warped stroke temporal residual (discrete Frechet, px) "
                       "+ popping penalty P_pop",
             "pipelines": {"A": "OURS: object-space carrier (3D-chained DT-pulled "
                                "linelets), projected per frame",
                           "B": "BASELINE: naive image-space Canny on the rendered "
                                "frame, re-traced per frame, no object-space carrier"},
             "warp": "identical depth-based forward warp for both pipelines",
             "held_out": f"TEST views only; trajectory {args.view_a}->{args.view_b}",
             "args": {k: v for k, v in vars(args).items()},
             "scenes": {}}
    for scene in args.scenes:
        print(f"=== {scene} ===", flush=True)
        table["scenes"][scene] = run_scene(scene, args)

    p = os.path.join(OUT, f"m1b_stroke_temporal_table{args.tag}.json")
    json.dump(table, open(p, "w"), indent=2)
    print(f"\nwrote {p}")
    _md(table, args)


def _md(table, args):
    L = []
    A = L.append
    A("# M1b STEP-06 — forward-warped STROKE temporal residual\n")
    A(f"Metric: {table['metric']}.  Warp: {table['warp']}.")
    A(f"Held-out: {table['held_out']}.  Stroke variant: `{args.variant}`.\n")
    A("- **A = OURS**: object-space carrier — DT-pulled linelets chained into static 3D "
      "polylines, projected into each frame.")
    A("- **B = BASELINE**: naive image-space Canny re-traced independently every frame.\n")
    A("| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** "
      "| unmatched | cuts | warp-dropped | strokes/frame | verts/stroke |")
    A("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for scene, r in table["scenes"].items():
        for nf in args.frames:
            m = r["by_frames"].get(str(nf))
            if not m:
                continue
            for p, nm in (("A", "OURS"), ("B", "BASE")):
                d = m[p]
                A(f"| {scene} | {nf} | {nm} | {d['frechet_median']:.3f} | "
                  f"{d['frechet_p90']:.3f} | {d['chamfer_median']:.3f} | "
                  f"**{d['P_pop']:.3f}** | {d['unmatched_frac']:.3f} | "
                  f"{d['cut_frac']:.3f} | {d.get('warp_dropped_frac', float('nan')):.3f} | "
                  f"{d['n_strokes_per_frame']:.0f} | "
                  f"{d['mean_vertices_per_stroke']:.2f} |")
    A("\n## Headline ratios (BASELINE / OURS — higher means our strokes are steadier)\n")
    A("| scene | frames | Frechet med ratio | P_pop ratio |")
    A("|---|---|---|---|")
    for scene, r in table["scenes"].items():
        for nf in args.frames:
            m = r["by_frames"].get(str(nf))
            if not m:
                continue
            fr = m["B"]["frechet_median"] / max(m["A"]["frechet_median"], 1e-9)
            pp = m["B"]["P_pop"] / max(m["A"]["P_pop"], 1e-9)
            A(f"| {scene} | {nf} | {fr:.2f}x | {pp:.2f}x |")
    A("\n## Stroke graphs\n")
    A("| scene | linelets | after 3D NMS | strokes | median vertices/stroke |")
    A("|---|---|---|---|---|")
    for scene, r in table["scenes"].items():
        c = r["chain"]
        A(f"| {scene} | {c['n_linelets']} | {c['n_nms']} | {c['n_strokes']} | "
          f"{c['median_vertices']:.0f} |")
    md = "\n".join(L)
    p = os.path.join(OUT, f"m1b_stroke_temporal_table{args.tag}.md")
    open(p, "w").write(md + "\n")
    print(md)
    print(f"\nwrote {p}")


if __name__ == "__main__":
    main()
