"""tier1/scripts/m1b_headline.py — the M1b HEADLINE TABLE (measurement only).

Builds out/m1b_headline_table.{json,md} + out/m1b_headline.png from linelets that were
ALREADY extracted. It trains nothing, tunes nothing, and builds no renderer.

EVAL PATH (mesh) is confined to tune_lib.Harness / mesh_oracle, used below the banner in
each block. No method module imports either.

BLOCK 0  hard-surface characterisation -> decides whether ficus is in scope
BLOCK 1  held-out TEST precision/recall on the hard-surface scene, gated vs ungated,
         both protocols (points = linelet centres, segments = the drawn p+-l*t)
BLOCK 2  temporal flicker, object-space vs image-space, on a held-out TEST trajectory,
         with the motion-scaling floor fit and a_temp (sub-pixel locus preservation)
BLOCK 3  chair false-positive LINE DENSITY inside GT-verified-FLAT regions
"""
import argparse
import json
import os
import subprocess
import sys

import cv2
import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))

from src import common, render, visibility, linelet, view_split
import run_m1b

OUT = os.path.join(TIER1, "out")


def _ll(scene, variant):
    p = os.path.join(OUT, f"linelets_{scene}_{variant}_test.npz")
    z = np.load(p)
    return {"p": z["p"], "t": z["t"], "l": z["l"], "keep": z["keep"].astype(bool),
            "inlier_ratio": z["inlier_ratio"], "path": os.path.basename(p)}


# =============================================================== BLOCK 0 =========
def block0_hard_surface(scenes=("chair", "lego", "ficus"), n_views=3):
    """Objective scene-scoping indicators, measured from the GT mesh (EVAL ONLY).

    TWO SEPARATE AXES — they were conflated in a first pass and the conflation gave a
    wrong answer, so they are kept apart here:

      (a) SOLID vs THIN/FOLIAGE  -> interior fraction (object pixels >4px from any
          silhouette boundary). Foliage is almost all silhouette. This is what decides
          whether a scene is a surface at all, and it is what excludes ficus.
      (b) TEXTURE CONTAMINATION  -> purity of the RGB-Canny edge field, i.e. the
          fraction of on-object Canny pixels within 1.5px of a GT crease. This is what
          separates the PRIMARY hard-surface scene from the texture STRESS scene.

    Crease DENSITY is deliberately NOT a hard-surface criterion: lego has the highest
    crease density of the three precisely because it is CAD-like plastic brickwork, so
    thresholding on it inverts the intended meaning."""
    from src.mesh_oracle import MeshOracle                        # EVAL ONLY
    out = {}
    for scene in scenes:
        try:
            o = MeshOracle(scene)
            cams, _ = common.load_cameras(scene)
        except Exception as e:                                     # missing assets
            out[scene] = {"error": str(e)}
            continue
        from src import dt_pull
        g = common.load_gaussians(scene)
        keep_g = render.defloat_mask(g["mu"], g["opacity"])
        _, rgb_paths = common.load_cameras(scene)
        views = list(view_split.TEST)[:n_views]
        inter, cd, obj, pur = [], [], [], []
        for v in views:
            md = o.render_depth(cams[v], view_key=int(v)).cpu().numpy()
            fg = md < 1e8
            if not fg.any():
                continue
            sil = fg ^ (cv2.erode(fg.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)
            sdt = cv2.distanceTransform((~sil).astype(np.uint8), cv2.DIST_L2, 5)
            uvq = o.visible_crease_uv(cams[v], view_key=int(v))
            cm = np.zeros(fg.shape, bool)
            cm[np.clip(np.round(uvq[:, 1]).astype(int), 0, fg.shape[0] - 1),
               np.clip(np.round(uvq[:, 0]).astype(int), 0, fg.shape[1] - 1)] = True
            npx = int(fg.sum())
            obj.append(npx)
            inter.append(float((fg & (sdt > 4)).sum()) / max(npx, 1))
            cd.append(1000.0 * int((cm & fg).sum()) / max(npx, 1))
            cdt_ = cv2.distanceTransform((~cm).astype(np.uint8), cv2.DIST_L2, 5)
            gbuf = render.render_gbuffer(g, keep_g, cams[v])
            afg = (gbuf["alpha"].cpu().numpy() > 0.5)
            del gbuf
            e = dt_pull.edge_map(rgb_paths[v], dt_pull.EDGE_SHARP) & afg
            ys, xs = np.nonzero(e)
            pur.append(float((cdt_[ys, xs] <= 1.5).mean()) if len(ys) else float("nan"))
        out[scene] = {"views": views, "object_px_mean": float(np.mean(obj)),
                      "interior_frac": float(np.mean(inter)),
                      "crease_px_per_kpx_object": float(np.mean(cd)),
                      "canny_edge_purity@1.5": float(np.nanmean(pur))}
        del o, g
        import torch
        torch.cuda.empty_cache()
    # decision: (a) solid-surface gate, then (b) role by edge purity
    for scene, r in out.items():
        if "error" in r:
            r["solid_surface"] = None
            r["role"] = "excluded (assets unavailable)"
            continue
        r["solid_surface"] = bool(r["interior_frac"] >= 0.55)
        if not r["solid_surface"]:
            r["role"] = ("excluded — thin/foliage: only "
                         f"{r['interior_frac']:.0%} of object pixels are >4px from a "
                         "silhouette, so 'crease vs flat surface' is not well posed")
        elif r["canny_edge_purity@1.5"] >= 0.50:
            r["role"] = "PRIMARY hard-surface scene (edge field is mostly real geometry)"
        else:
            r["role"] = ("texture false-positive STRESS scene (most Canny edges are not "
                         "creases)")
    return out


# =============================================================== BLOCK 1 =========
def block1_test_pr(scene):
    from tune_lib import Harness                                   # EVAL ONLY
    h = Harness(scene, views=tuple(view_split.TEST))
    rows = {}
    for variant in ("ungated", "gated"):
        L = _ll(scene, variant)
        pts = run_m1b.eval_points(h, L["p"], keep=L["keep"])
        seg = run_m1b.eval_segments(h, L["p"], L["t"], L["l"], keep=L["keep"])
        rows[variant] = {
            "n_linelets_kept": int(L["keep"].sum()), "n_total": int(len(L["p"])),
            "source": L["path"],
            "points": {"P@1.5": pts[1.5][0], "R@1.5": pts[1.5][1],
                       "P@2.5": pts[2.5][0], "R@2.5": pts[2.5][1]},
            "segments": {"P@1.5": seg[1.5][0], "R@1.5": seg[1.5][1],
                         "P@2.5": seg[2.5][0], "R@2.5": seg[2.5][1]},
        }
    rows["delta_gated_minus_ungated"] = {
        proto: {k: rows["gated"][proto][k] - rows["ungated"][proto][k]
                for k in rows["ungated"][proto]} for proto in ("points", "segments")}
    rows["eval_views"] = list(view_split.TEST)
    del h
    import gc, torch
    gc.collect()
    torch.cuda.empty_cache()
    return rows


# =============================================================== BLOCK 2 =========
def block2_temporal(scene, frames=(30, 60, 120, 240), va=5, vb=15, rerun=True):
    """Reuses scripts/temporal_m1b.py verbatim (the harness that produced the chair
    f240 numbers), on a held-out TEST-view trajectory."""
    res = {"trajectory": f"TEST views {va}->{vb}", "frames": list(frames), "variants": {}}
    for variant in ("ungated", "gated"):
        per = []
        for f in frames:
            tag = f"_{variant}_test"
            otag = f"_head_{variant}_f{f}"
            jp = os.path.join(OUT, f"m1b_temporal_{scene}{otag}.json")
            if rerun or not os.path.exists(jp):
                cmd = [sys.executable, os.path.join(TIER1, "scripts", "temporal_m1b.py"),
                       "--scene", scene, "--tag", tag, "--out_tag", otag,
                       "--view_a", str(va), "--view_b", str(vb), "--frames", str(f)]
                env = dict(os.environ, CUDA_VISIBLE_DEVICES="1")
                # the GPU is ~3.7GB; the child needs ~1.5GB for lego, so the parent must
                # not be holding a Harness worth of G-buffers while it runs.
                r = subprocess.run(cmd, env=env, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)
                if r.returncode != 0:
                    import time
                    time.sleep(20)
                    r = subprocess.run(cmd, env=env, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT)
                if r.returncode != 0:
                    raise RuntimeError(
                        f"temporal_m1b failed for {scene} {variant} f{f}:\n"
                        + r.stdout.decode()[-2000:])
            d = json.load(open(jp))
            per.append({"frames": f, "obj_strict": d["obj_strict"],
                        "img_strict": d["img_strict"], "obj_tol": d["obj_tol"],
                        "img_tol": d["img_tol"],
                        "reduction_strict": d["reduction_strict"],
                        "reduction_tol": d["reduction_tol"],
                        "a_temp_px": d["a_temp_px"],
                        "obj_on_px": d["obj_on_px"], "img_on_px": d["img_on_px"],
                        "n_linelets": d["n_linelets"]})
        # flicker = floor + k * motion, motion ~ 1/frames. The intercept is the
        # IRREDUCIBLE flicker. Report it with its standard error: for a static 3D
        # primitive the true floor is 0, so a fit can legitimately land at or below
        # zero, and a naive ratio then explodes. Guard against reporting that.
        x = np.array([1.0 / r["frames"] for r in per])
        A = np.stack([np.ones_like(x), x], 1)

        def _fit(y):
            coef, *_ = np.linalg.lstsq(A, y, rcond=None)
            resid = y - A @ coef
            dof = max(len(y) - 2, 1)
            s2 = float(resid @ resid) / dof
            cov = s2 * np.linalg.inv(A.T @ A)
            return float(coef[0]), float(np.sqrt(max(cov[0, 0], 0.0))), float(coef[1])

        ao, seo, ko = _fit(np.array([r["obj_tol"] for r in per]))
        ai, sei, ki = _fit(np.array([r["img_tol"] for r in per]))
        obj_zero = (ao - 2 * seo) <= 0.0            # floor indistinguishable from zero
        img_zero = (ai - 2 * sei) <= 0.0
        obj_hi = max(ao + 2 * seo, 1e-9)            # conservative upper bound on the floor
        res["variants"][variant] = {
            "per_frame_density": per,
            "obj_floor_pct": float(100 * ao), "obj_floor_se_pct": float(100 * seo),
            "img_floor_pct": float(100 * ai), "img_floor_se_pct": float(100 * sei),
            "obj_floor_consistent_with_zero": bool(obj_zero),
            "img_floor_consistent_with_zero": bool(img_zero),
            # a point ratio is only meaningful when the object floor is resolvably >0;
            # otherwise quote a LOWER BOUND using the +2se upper limit on that floor.
            "floor_ratio_img_over_obj": (None if obj_zero
                                         else float(ai / max(ao, 1e-12))),
            "floor_ratio_lower_bound": float(ai / obj_hi),
            "motion_coeff_obj": ko, "motion_coeff_img": ki,
            "reduction_tol_finest": per[-1]["reduction_tol"],
            "finest_frames": per[-1]["frames"],
            "obj_tol_finest_pct": float(100 * per[-1]["obj_tol"]),
            "img_tol_finest_pct": float(100 * per[-1]["img_tol"]),
        }
    g, u = res["variants"]["gated"], res["variants"]["ungated"]
    res["guard"] = {
        "obj_floor_change_pp": g["obj_floor_pct"] - u["obj_floor_pct"],
        "obj_tol_finest_change_pp": g["obj_tol_finest_pct"] - u["obj_tol_finest_pct"],
        "allowed_pp": 0.02,
        "pass": bool((g["obj_floor_pct"] - u["obj_floor_pct"]) <= 0.02 and
                     (g["obj_tol_finest_pct"] - u["obj_tol_finest_pct"]) <= 0.02),
        "note": "measured on the gated-vs-ungated pair; both the fitted floor and the "
                "directly-measured finest-motion value must not regress",
    }
    return res


# =============================================================== BLOCK 3 =========
def block3_flat_fp(scene="chair", crease_clear=(5.0, 8.0), sil_clear=4.0):
    """FP line density INSIDE GT-verified-FLAT regions.

    flat = on the GT mesh AND >crease_clear px from any visible GT crease AND
           >sil_clear px from the silhouette (so occluding contours, which are not
           creases but are legitimately line-worthy, cannot be counted as FPs).
    Mesh is EVAL-ONLY: it builds the mask, nothing else."""
    from src.mesh_oracle import MeshOracle                          # EVAL ONLY
    cams, _ = common.load_cameras(scene)
    g = common.load_gaussians(scene)
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    o = MeshOracle(scene)
    views = list(view_split.TEST)
    L = {v: _ll(scene, v) for v in ("ungated", "gated")}
    acc = {v: {c: {"px": 0, "cent": 0, "area": 0} for c in crease_clear} for v in L}

    for v in views:
        cam = cams[v]
        md = o.render_depth(cam, view_key=int(v)).cpu().numpy()
        mfg = md < 1e8
        sil = mfg ^ (cv2.erode(mfg.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)
        sdt = cv2.distanceTransform((~sil).astype(np.uint8), cv2.DIST_L2, 5)
        uvq = o.visible_crease_uv(cam, view_key=int(v))
        cm = np.zeros(mfg.shape, bool)
        cm[np.clip(np.round(uvq[:, 1]).astype(int), 0, cam.H - 1),
           np.clip(np.round(uvq[:, 0]).astype(int), 0, cam.W - 1)] = True
        cdt = cv2.distanceTransform((~cm).astype(np.uint8), cv2.DIST_L2, 5)
        gb = render.render_gbuffer(g, keep_g, cam)
        for variant, Lv in L.items():
            mask, _ = _raster(Lv, cam, gb["depth"])
            vis, uv, _ = visibility.visible_mask(Lv["p"], cam, gb["depth"])
            sel = vis & Lv["keep"]
            cu = np.clip(np.round(uv[sel, 0]).astype(int), 0, cam.W - 1)
            cv_ = np.clip(np.round(uv[sel, 1]).astype(int), 0, cam.H - 1)
            for c in crease_clear:
                flat = mfg & (cdt > c) & (sdt > sil_clear)
                acc[variant][c]["area"] += int(flat.sum())
                acc[variant][c]["px"] += int((mask & flat).sum())
                acc[variant][c]["cent"] += int(flat[cv_, cu].sum())
        del gb
    out = {"scene": scene, "views": views, "sil_clear_px": sil_clear, "by_threshold": {}}
    for c in crease_clear:
        rec = {}
        for variant in L:
            a = acc[variant][c]
            kpx = max(a["area"], 1) / 1000.0
            rec[variant] = {"flat_area_px": a["area"],
                            "fp_line_px": a["px"],
                            "fp_line_px_per_kpx": a["px"] / kpx,
                            "fp_linelet_centres": a["cent"],
                            "fp_linelets_per_kpx": a["cent"] / kpx}
        rec["delta_pct"] = 100.0 * (rec["gated"]["fp_line_px_per_kpx"] /
                                    max(rec["ungated"]["fp_line_px_per_kpx"], 1e-12) - 1.0)
        out["by_threshold"][f"crease_clear_{c:g}px"] = rec
    return out


class _Shim:
    """Minimal stand-in for tune_lib.Harness so run_m1b.raster_segments can be reused
    verbatim on one camera without rebuilding the whole eval harness."""

    def __init__(self, cam, depth):
        self.cams = {0: cam}
        self.gbufs = {0: {"depth": depth}}


def _raster(Lv, cam, depth):
    return run_m1b.raster_segments(_Shim(cam, depth), 0, Lv["p"], Lv["t"], Lv["l"],
                                   keep=Lv["keep"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--primary", default="lego")
    ap.add_argument("--stress", default="chair")
    ap.add_argument("--no_temporal_rerun", action="store_true")
    args = ap.parse_args()

    table = {"note": "M1b headline table — measurement only over existing linelets; "
                     "no renderer, no training, no tuning.",
             "view_split": {"train": len(view_split.TRAIN), "val": len(view_split.VAL),
                            "test": view_split.TEST}}

    print("BLOCK 0 — hard-surface characterisation ...", flush=True)
    table["block0_scene_scoping"] = block0_hard_surface()
    for s, r in table["block0_scene_scoping"].items():
        if "error" in r:
            print(f"  {s:6s} EXCLUDED (assets): {r['error'][:60]}")
        else:
            print(f"  {s:6s} interior_frac {r['interior_frac']:.3f}  "
                  f"edge_purity {r['canny_edge_purity@1.5']:.3f}  "
                  f"crease_px/kpx {r['crease_px_per_kpx_object']:6.1f}  -> {r['role']}")

    print(f"BLOCK 1 — held-out TEST P/R on {args.primary} ...", flush=True)
    table["block1_heldout_test_pr"] = {args.primary: block1_test_pr(args.primary)}

    import gc, torch
    gc.collect()
    torch.cuda.empty_cache()
    print(f"BLOCK 2 — temporal flicker on {args.primary} TEST trajectory ...", flush=True)
    table["block2_temporal"] = {args.primary: block2_temporal(
        args.primary, rerun=not args.no_temporal_rerun)}

    gc.collect()
    torch.cuda.empty_cache()
    print(f"BLOCK 3 — {args.stress} FP line density in GT-flat regions ...", flush=True)
    table["block3_flat_fp_density"] = block3_flat_fp(args.stress)

    p = os.path.join(OUT, "m1b_headline_table.json")
    json.dump(table, open(p, "w"), indent=2)
    print(f"\nwrote {p}")
    _report(table, args)


def _report(t, args):
    P = args.primary
    b1 = t["block1_heldout_test_pr"][P]
    b2 = t["block2_temporal"][P]
    b3 = t["block3_flat_fp_density"]
    lines = []
    A = lines.append
    A("# M1b headline table (measurement only)\n")
    A(f"Held-out split: {len(view_split.TRAIN)} train / {len(view_split.VAL)} val / "
      f"{len(view_split.TEST)} test. All P/R on TEST views {view_split.TEST}.\n")
    A("## Scene scoping\n")
    A("| scene | interior frac (solid?) | Canny edge purity@1.5 | GT crease px/kpx | role |")
    A("|---|---|---|---|---|")
    for s, r in t["block0_scene_scoping"].items():
        if "error" in r:
            A(f"| {s} | — | — | — | excluded (assets) |")
        else:
            A(f"| {s} | {r['interior_frac']:.3f} | {r['canny_edge_purity@1.5']:.3f} | "
              f"{r['crease_px_per_kpx_object']:.1f} | {r['role']} |")
    A(f"\n## 1. Held-out TEST P/R — {P} (primary, hard-surface)\n")
    A("| protocol | variant | P@1.5 | R@1.5 | P@2.5 | R@2.5 | n |")
    A("|---|---|---|---|---|---|---|")
    for proto in ("points", "segments"):
        for var in ("ungated", "gated"):
            r = b1[var][proto]
            A(f"| {proto} | {var} | {r['P@1.5']:.4f} | {r['R@1.5']:.4f} | "
              f"{r['P@2.5']:.4f} | {r['R@2.5']:.4f} | {b1[var]['n_linelets_kept']} |")
        d = b1["delta_gated_minus_ungated"][proto]
        A(f"| {proto} | **delta** | {d['P@1.5']:+.4f} | {d['R@1.5']:+.4f} | "
          f"{d['P@2.5']:+.4f} | {d['R@2.5']:+.4f} | |")
    A(f"\n## 2. Temporal flicker — {P}, held-out {b2['trajectory']}\n")
    A("| variant | frames | obj tol % | img tol % | reduction (tol) | a_temp px/f^2 |")
    A("|---|---|---|---|---|---|")
    for var in ("ungated", "gated"):
        for r in b2["variants"][var]["per_frame_density"]:
            A(f"| {var} | {r['frames']} | {100*r['obj_tol']:.2f} | {100*r['img_tol']:.2f} | "
              f"{r['reduction_tol']:.2f}x | {r['a_temp_px']:.5f} |")
    for var in ("ungated", "gated"):
        v = b2["variants"][var]
        o = (f"{v['obj_floor_pct']:.2f}% +- {v['obj_floor_se_pct']:.2f}"
             + (" (consistent with ZERO)" if v["obj_floor_consistent_with_zero"] else ""))
        rat = ("> %.1fx (lower bound; object floor is not resolvably above 0)"
               % v["floor_ratio_lower_bound"]) if v["obj_floor_consistent_with_zero"] \
            else "%.1fx" % v["floor_ratio_img_over_obj"]
        A(f"\n- **{var}** fitted floors: object-space **{o}** vs image-space "
          f"**{v['img_floor_pct']:.2f}% +- {v['img_floor_se_pct']:.2f}** -> **{rat}**")
        A(f"  - directly measured at the finest motion ({v['finest_frames']} frames): "
          f"object {v['obj_tol_finest_pct']:.2f}% vs image "
          f"{v['img_tol_finest_pct']:.2f}% = **{v['reduction_tol_finest']:.2f}x** "
          f"(no model, no extrapolation)")
    A(f"\n- temporal guard (gated vs ungated): fitted-floor change "
      f"{b2['guard']['obj_floor_change_pp']:+.3f} pp, finest-motion change "
      f"{b2['guard']['obj_tol_finest_change_pp']:+.3f} pp "
      f"(allowed +{b2['guard']['allowed_pp']}) -> "
      f"**{'PASS' if b2['guard']['pass'] else 'FAIL'}**")
    A(f"\n## 3. {args.stress} FP line density inside GT-verified-FLAT regions\n")
    A("| crease clearance | variant | flat area px | FP line px / kpx | FP linelets / kpx |")
    A("|---|---|---|---|---|")
    for k, rec in b3["by_threshold"].items():
        for var in ("ungated", "gated"):
            r = rec[var]
            A(f"| {k} | {var} | {r['flat_area_px']} | {r['fp_line_px_per_kpx']:.2f} | "
              f"{r['fp_linelets_per_kpx']:.2f} |")
        A(f"| {k} | **gated vs ungated** | | **{rec['delta_pct']:+.1f}%** | |")
    md = "\n".join(lines)
    p = os.path.join(OUT, "m1b_headline_table.md")
    open(p, "w").write(md + "\n")
    print(md)
    print(f"\nwrote {p}")
    _png(t, args)


def _png(t, args):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    P = args.primary
    b1 = t["block1_heldout_test_pr"][P]
    b2 = t["block2_temporal"][P]
    b3 = t["block3_flat_fp_density"]
    fig, ax = plt.subplots(1, 3, figsize=(18, 5))
    lbl = ["P@1.5", "R@1.5", "P@2.5", "R@2.5"]
    x = np.arange(4)
    for i, var in enumerate(("ungated", "gated")):
        ax[0].bar(x + i * 0.35 - 0.17, [b1[var]["segments"][k] for k in lbl], 0.35,
                  label=f"{var} (segments)")
    ax[0].set_xticks(x); ax[0].set_xticklabels(lbl)
    ax[0].axhline(0.85, color="k", ls=":", lw=1)
    ax[0].set_title(f"1. {P} held-out TEST — segments\n(dotted = 0.85 gate)")
    ax[0].legend(fontsize=8); ax[0].set_ylim(0, 1)

    for var, c in (("ungated", "tab:blue"), ("gated", "tab:orange")):
        pf = b2["variants"][var]["per_frame_density"]
        fr = [r["frames"] for r in pf]
        ax[1].plot(fr, [100 * r["obj_tol"] for r in pf], "o-", color=c,
                   label=f"object-space {var}")
        ax[1].plot(fr, [100 * r["img_tol"] for r in pf], "s--", color=c, alpha=0.5,
                   label=f"image-space {var}")
    ax[1].set_xscale("log"); ax[1].set_xlabel("frames on the arc (finer = less motion)")
    ax[1].set_ylabel("flicker (1px tol) %")
    ax[1].set_title(f"2. {P} temporal, held-out TEST trajectory")
    ax[1].legend(fontsize=7)

    ks = list(b3["by_threshold"])
    xx = np.arange(len(ks))
    for i, var in enumerate(("ungated", "gated")):
        ax[2].bar(xx + i * 0.35 - 0.17,
                  [b3["by_threshold"][k][var]["fp_line_px_per_kpx"] for k in ks], 0.35,
                  label=var)
    ax[2].set_xticks(xx); ax[2].set_xticklabels(ks, fontsize=8)
    ax[2].set_ylabel("FP line px per kilopixel of flat region")
    ax[2].set_title(f"3. {args.stress} FP density inside GT-FLAT regions")
    ax[2].legend(fontsize=8)
    plt.tight_layout()
    p = os.path.join(OUT, "m1b_headline.png")
    plt.savefig(p, dpi=110)
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
