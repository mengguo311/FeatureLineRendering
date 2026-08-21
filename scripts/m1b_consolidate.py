"""tier1/scripts/m1b_consolidate.py — paper-ready consolidation of the M1b results.

Reads the corrected-orbit STEP-06 JSONs and emits out/m1b_stroke_temporal_table.{md,json}:
headline temporal result, both confound controls, the quantified LIMITATION subsection,
and the carrier-persistence ablation. Measurement is done elsewhere; this only formats.
"""
import json
import os
import sys

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
OUT = os.path.join(TIER1, "out")
FRAMES = ("30", "60", "120", "240")


def _r(m, p, k):
    return m[p][k]


def main():
    head = json.load(open(f"{OUT}/m1b_stroke_temporal_table_orbit.json"))
    ctrl = json.load(open(f"{OUT}/m1b_stroke_temporal_table_orbit_fgonly.json"))
    abl = json.load(open(f"{OUT}/m1b_ablation_carrier_chair.json"))
    L = []
    A = L.append

    A("# M1b — object-space feature lines from a frozen 3DGS: temporal coherence\n")
    A("All numbers below are on **held-out TEST views** (10 of 100; the DT pull consumed "
      "the 80 TRAIN views only). The GT mesh is used **exclusively** for evaluation and "
      "for labelling diagnostic pixels; no method module imports it.\n")
    A("Camera path: the 240-frame arc between TEST views 5 and 15, on the "
      "**look-at-corrected orbit**. An earlier version of this table used an "
      "interpolator that slerped camera rotation and centre independently; both "
      "endpoints look at the origin but the intermediate poses did not, which drove the "
      "object off-frame (chair: visible area 130664 px at frame 0 -> 27012 px at frame "
      "120, clipped against the border from frame ~40 to ~200). Those numbers are "
      "superseded by the ones here.\n")

    A("## 1. Headline — forward-warped stroke temporal residual\n")
    A("Every stroke of frame *t* is forward-warped into *t+1* by the scene's own motion "
      "(each vertex un-projected with the frame-*t* gaussian z-buffer and re-projected), "
      "then matched to the strokes actually produced at *t+1*. `Frechet` is the discrete "
      "Frechet distance to the best match; `P_pop` is the fraction of strokes with no "
      "match in either direction plus the topological split/merge rate.\n")
    A("- **OURS** — DT-pulled linelets chained into static 3D polylines, projected per frame.")
    A("- **BASELINE** — naive image-space Canny, re-traced independently every frame.")
    A("- The **identical** depth-based warp is applied to both, which is deliberately "
      "conservative for OURS: it charges our strokes for resampling error they would not "
      "really suffer, since their inter-frame motion is known exactly.\n")
    A("| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** "
      "| unmatched | cuts | strokes/frame |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for sc in head["scenes"]:
        for nf in FRAMES:
            m = head["scenes"][sc]["by_frames"][nf]
            for p, nm in (("A", "OURS"), ("B", "BASE")):
                d = m[p]
                A(f"| {sc} | {nf} | {nm} | {d['frechet_median']:.3f} | "
                  f"{d['frechet_p90']:.3f} | {d['chamfer_median']:.3f} | "
                  f"**{d['P_pop']:.3f}** | {d['unmatched_frac']:.3f} | "
                  f"{d['cut_frac']:.3f} | {d['n_strokes_per_frame']:.0f} |")
    A("\n**Ratios (BASELINE / OURS — higher means our strokes are steadier):**\n")
    A("| scene | frames | Frechet ratio | P_pop ratio |")
    A("|---|---|---|---|")
    for sc in head["scenes"]:
        for nf in FRAMES:
            m = head["scenes"][sc]["by_frames"][nf]
            A(f"| {sc} | {nf} | **{m['B']['frechet_median']/m['A']['frechet_median']:.2f}x** "
              f"| **{m['B']['P_pop']/m['A']['P_pop']:.2f}x** |")
    A("\nThe mechanism is in the scaling, not only the ratio. OURS falls roughly in "
      "proportion to the per-frame motion (halving on each frame-doubling), i.e. its "
      "residual is warp resampling and nothing else; BASELINE is nearly flat across the "
      "same range, saturating at a motion-independent floor. That floor is the popping: "
      "its strokes are re-derived every frame, so most of them have no counterpart in "
      "the next one.\n")

    A("## 2. Confound controls\n")
    A("### 2a. Sparsity\n")
    A("A method could fake a low `P_pop` by drawing fewer, easier strokes. The opposite "
      "holds here — OURS is the DENSER stroke set:\n")
    A("| scene | frames | OURS strokes/frame | BASE strokes/frame | OURS unmatched | BASE unmatched |")
    A("|---|---|---|---|---|---|")
    for sc in head["scenes"]:
        for nf in ("120", "240"):
            m = head["scenes"][sc]["by_frames"][nf]
            A(f"| {sc} | {nf} | {m['A']['n_strokes_per_frame']:.0f} | "
              f"{m['B']['n_strokes_per_frame']:.0f} | {m['A']['unmatched_frac']:.3f} | "
              f"{m['B']['unmatched_frac']:.3f} |")
    A("\n### 2b. Silhouette warp-drop\n")
    A("The baseline's Canny fires on the object silhouette, where the gaussian z-buffer "
      "is empty; those strokes cannot be forward-warped at all and would be charged as "
      "popping through the warp operator rather than through any real instability. "
      "Measured drop rate: **BASELINE 19.8% (lego) / 18.2% (chair) vs OURS 0.2% / 0.0%**. "
      "The control removes it at source by restricting BOTH pipelines to the object "
      "interior (OURS draws interior crease carriers and cannot draw silhouettes either).\n")
    A("| scene | frames | pipeline | Frechet med | **P_pop** | strokes/frame |")
    A("|---|---|---|---|---|---|")
    for sc in ctrl["scenes"]:
        for nf in ("120", "240"):
            m = ctrl["scenes"][sc]["by_frames"][nf]
            for p, nm in (("A", "OURS"), ("B", "BASE")):
                d = m[p]
                A(f"| {sc} | {nf} | {nm} | {d['frechet_median']:.3f} | "
                  f"**{d['P_pop']:.3f}** | {d['n_strokes_per_frame']:.0f} |")
    A("\n| scene | frames | Frechet ratio (controlled) | P_pop ratio (controlled) |")
    A("|---|---|---|---|")
    for sc in ctrl["scenes"]:
        for nf in ("120", "240"):
            m = ctrl["scenes"][sc]["by_frames"][nf]
            A(f"| {sc} | {nf} | {m['B']['frechet_median']/m['A']['frechet_median']:.2f}x | "
              f"{m['B']['P_pop']/m['A']['P_pop']:.2f}x |")
    A("\nThe advantage survives both controls.\n")

    # ------------------------------------------------------------------ LIMITATION
    f5 = abl["flat_fp"]["crease_clear_5px"]
    f8 = abl["flat_fp"]["crease_clear_8px"]
    A("## 3. Limitation — texture false positives on a frozen 3DGS\n")
    A("The temporal result above is about the **stability** of the extracted lines. It "
      "says nothing about whether every extracted line *should* exist, and on a "
      "texture-rich object many should not.\n")
    A("### 3.1 Quantified false-positive line density\n")
    A("On chair, we measure line density inside **GT-verified-flat regions**: pixels on "
      "the GT mesh that are more than *c* px from any visible GT crease and more than "
      "4 px from the silhouette, so that occluding contours — which are legitimately "
      "line-worthy — cannot be miscounted. Every line drawn there is a false positive.\n")
    A("| flat-region definition | FP line px per kilopixel | with carrier-persistence prune |")
    A("|---|---|---|")
    A(f"| >5 px from any GT crease | **{f5['base']['fp_line_px_per_kpx']:.1f}** | "
      f"{f5['carrier_persistence']['fp_line_px_per_kpx']:.1f} |")
    A(f"| >8 px from any GT crease | **{f8['base']['fp_line_px_per_kpx']:.1f}** | "
      f"{f8['carrier_persistence']['fp_line_px_per_kpx']:.1f} |")
    A(f"\nThat is {f5['base']['fp_line_px_per_kpx']:.1f} px/kpx of ink laid down on "
      f"surfaces that are provably flat, reducible to "
      f"{f5['carrier_persistence']['fp_line_px_per_kpx']:.1f} px/kpx by a persistence "
      "filter that keeps only carriers with stable multi-view support "
      f"({abl['n_keep_base']} -> {abl['n_keep_cp']} linelets). **These are false "
      "positives and are reported as such.** They are not stylistic hatching, and the "
      "persistence filter does not identify texture — it removes weakly supported "
      "carriers, some of which happen to lie on flat regions.\n")
    A("### 3.2 Why post-hoc extraction cannot fix this\n")
    A("The failure is structural, not a matter of a better filter. On a frozen vanilla "
      "3DGS the printed pattern is **baked into the geometry**: the reconstruction places "
      "real, tilted splats wherever the colour varies, because that is where the "
      "photometric evidence is. Labelling Canny pixels by the GT mesh and measuring the "
      "bilateral-ribbon dihedral from the rendered G-buffer gives\n")
    A("| population | dihedral theta |")
    A("|---|---|")
    A("| fabric print | p50 28.8 deg, **p95 79.3 deg** |")
    A("| true crease | **p05 4.9 deg**, p50 23.4 deg |")
    A("\ni.e. the print is *more* dihedral than the crease and the two distributions "
      "overlap almost completely (separation -74.4 deg against the +6 deg a usable gate "
      "would need). The estimator is sound: the identical ribbon code run on GT-mesh "
      "depth separates the two classes at AUC 0.72-0.77, while on gaussian depth it is "
      "at chance (AUC 0.42-0.51). So the geometry channel is poisoned by albedo.\n")
    A("Inverting the test does not help, because the albedo channel is poisoned by "
      "geometry. The SH degree-0 term is not a material property — it is mean radiance, "
      "so a crease bakes its own shading step into it. The bilateral SH-DC albedo step "
      "gives AUC(fabric>crease) = **0.31 on chair** (the hypothesis is backwards: creases "
      "carry the *larger* albedo step, p50 0.175 vs 0.092) and **0.500 on lego** (exactly "
      "chance).\n")
    A("Consistently, a geometry-gated DT built on that signal buys almost nothing "
      "end-to-end on held-out TEST. Segment precision / recall @1.5 px, gated vs "
      "ungated:\n")
    A("| scene | ungated | geometry-gated | change |")
    A("|---|---|---|---|")
    A("| chair (texture stress) | 0.6024 / 0.7206 | 0.6067 / 0.7077 | +0.4 pp P, -1.3 pp R |")
    A("| lego (hard surface) | 0.5628 / 0.4193 | 0.5826 / 0.4168 | +2.0 pp P, -0.25 pp R |")
    A("\nOn chair that lands on the ungated precision/recall frontier, i.e. no real gain; "
      "on lego it is a small genuine gain, consistent with lego's edges already being "
      "mostly real geometry. Multi-view rescues fare no better either: across-view "
      "dihedral variance AUC 0.577, world-normal consensus 0.596, and the best candidate "
      "of any kind — shading-vs-albedo view-contrast variance — only 0.638, itself "
      "largely explained by edge contrast alone (control AUC 0.619).\n")
    A("**Conclusion.** Print and crease are not separable *after* the fact from a frozen "
      "vanilla 3DGS, because that representation does not factor material from geometry "
      "in either direction. The contamination has to be attacked upstream — a "
      "reconstruction whose geometry is not albedo-driven (normal- or "
      "smoothness-regularised training), or a seeding stage that never proposes on "
      "flat-but-patterned surface — not by filtering the edge field downstream. Scenes "
      "should be scoped accordingly: lego-like hard surfaces are the primary regime "
      "(Canny edge purity 0.663), chair is a texture false-positive stress case "
      "(purity 0.284).\n")

    A("## 4. Ablation — carrier-persistence prune (not part of the headline)\n")
    A(f"chair, {abl['n_keep_base']} -> {abl['n_keep_cp']} linelets "
      f"(multi-view inlier ratio >= {abl['cp_ratio']}, seen in >= {abl['cp_views']} "
      "views), applied before chaining.\n")
    A("| variant | FP px/kpx (>5px) | FP px/kpx (>8px) | OURS Frechet med | OURS P_pop | strokes/frame |")
    A("|---|---|---|---|---|---|")
    b = abl["stroke_temporal"]["base"]["OURS"]
    c = abl["stroke_temporal"]["carrier_persistence"]["OURS"]
    A(f"| base | {f5['base']['fp_line_px_per_kpx']:.1f} | {f8['base']['fp_line_px_per_kpx']:.1f} | "
      f"{b['frechet_median']:.3f} | {b['P_pop']:.3f} | {b['n_strokes_per_frame']:.0f} |")
    A(f"| carrier-persistence | {f5['carrier_persistence']['fp_line_px_per_kpx']:.1f} | "
      f"{f8['carrier_persistence']['fp_line_px_per_kpx']:.1f} | {c['frechet_median']:.3f} | "
      f"{c['P_pop']:.3f} | {c['n_strokes_per_frame']:.0f} |")
    A("\nIt cuts flat-region FP density by ~40% at essentially no temporal cost, but see "
      "3.1: it is a support filter, not a texture detector.\n")

    A("## 5. Stroke graphs and reproduction\n")
    A("| scene | linelets | after 3D NMS | strokes | median vertices/stroke |")
    A("|---|---|---|---|---|")
    for sc in head["scenes"]:
        ch = head["scenes"][sc]["chain"]
        A(f"| {sc} | {ch['n_linelets']} | {ch['n_nms']} | {ch['n_strokes']} | "
          f"{ch['median_vertices']:.0f} |")
    A("\n```\npython scripts/m1b_stroke_temporal.py --scenes lego chair "
      "--frames 30 60 120 240 --tag _orbit\npython scripts/m1b_stroke_temporal.py "
      "--scenes lego chair --frames 120 240 --fg_only --tag _orbit_fgonly\n"
      "python scripts/m1b_ablation_carrier.py --scene chair --frames 120\n"
      "python scripts/m1b_consolidate.py\n```\n")
    A("Side-by-side videos: `out/m1b_temporal_sidebyside_{chair,lego}.mp4` "
      "(240 frames, same orbit).")

    md = "\n".join(L)
    open(f"{OUT}/m1b_stroke_temporal_table.md", "w").write(md + "\n")
    merged = {"trajectory": "look-at-corrected orbit, TEST views 5->15",
              "supersedes": "earlier interp_cameras path clipped the object out of frame",
              "headline": head["scenes"], "control_fg_only": ctrl["scenes"],
              "confound_warp_dropped_frac": {"BASE_lego": 0.198, "BASE_chair": 0.182,
                                             "OURS_lego": 0.002, "OURS_chair": 0.000},
              "ablation_carrier_persistence": abl,
              "args_headline": head["args"], "args_control": ctrl["args"]}
    json.dump(merged, open(f"{OUT}/m1b_stroke_temporal_table.json", "w"), indent=2)
    print(f"wrote {OUT}/m1b_stroke_temporal_table.md (+ .json)")
    return md


if __name__ == "__main__":
    main()
