# M1b — object-space feature lines from a frozen 3DGS: temporal coherence

All numbers below are on **held-out TEST views** (10 of 100; the DT pull consumed the 80 TRAIN views only). The GT mesh is used **exclusively** for evaluation and for labelling diagnostic pixels; no method module imports it.

Camera path: the 240-frame arc between TEST views 5 and 15, on the **look-at-corrected orbit**. An earlier version of this table used an interpolator that slerped camera rotation and centre independently; both endpoints look at the origin but the intermediate poses did not, which drove the object off-frame (chair: visible area 130664 px at frame 0 -> 27012 px at frame 120, clipped against the border from frame ~40 to ~200). Those numbers are superseded by the ones here.

## 1. Headline — forward-warped stroke temporal residual

Every stroke of frame *t* is forward-warped into *t+1* by the scene's own motion (each vertex un-projected with the frame-*t* gaussian z-buffer and re-projected), then matched to the strokes actually produced at *t+1*. `Frechet` is the discrete Frechet distance to the best match; `P_pop` is the fraction of strokes with no match in either direction plus the topological split/merge rate.

- **OURS** — DT-pulled linelets chained into static 3D polylines, projected per frame.
- **BASELINE** — naive image-space Canny, re-traced independently every frame.
- The **identical** depth-based warp is applied to both, which is deliberately conservative for OURS: it charges our strokes for resampling error they would not really suffer, since their inter-frame motion is known exactly.

| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** | unmatched | cuts | strokes/frame |
|---|---|---|---|---|---|---|---|---|---|
| lego | 30 | OURS | 0.619 | 1.681 | 0.321 | **0.234** | 0.212 | 0.022 | 1121 |
| lego | 30 | BASE | 1.503 | 2.688 | 0.521 | **0.803** | 0.801 | 0.002 | 617 |
| lego | 60 | OURS | 0.330 | 1.320 | 0.188 | **0.144** | 0.120 | 0.024 | 1121 |
| lego | 60 | BASE | 1.399 | 2.633 | 0.483 | **0.764** | 0.762 | 0.002 | 616 |
| lego | 120 | OURS | 0.170 | 0.882 | 0.102 | **0.091** | 0.065 | 0.025 | 1121 |
| lego | 120 | BASE | 1.272 | 2.584 | 0.442 | **0.734** | 0.732 | 0.002 | 617 |
| lego | 240 | OURS | 0.086 | 0.514 | 0.052 | **0.063** | 0.037 | 0.026 | 1122 |
| lego | 240 | BASE | 1.202 | 2.556 | 0.421 | **0.719** | 0.717 | 0.002 | 615 |
| chair | 30 | OURS | 0.330 | 0.708 | 0.181 | **0.093** | 0.050 | 0.043 | 756 |
| chair | 30 | BASE | 1.380 | 2.639 | 0.470 | **0.788** | 0.786 | 0.003 | 577 |
| chair | 60 | OURS | 0.164 | 0.350 | 0.095 | **0.076** | 0.032 | 0.044 | 754 |
| chair | 60 | BASE | 1.293 | 2.617 | 0.434 | **0.770** | 0.768 | 0.003 | 577 |
| chair | 120 | OURS | 0.082 | 0.174 | 0.049 | **0.068** | 0.025 | 0.043 | 752 |
| chair | 120 | BASE | 1.252 | 2.611 | 0.421 | **0.756** | 0.753 | 0.003 | 575 |
| chair | 240 | OURS | 0.041 | 0.086 | 0.024 | **0.067** | 0.023 | 0.043 | 751 |
| chair | 240 | BASE | 1.225 | 2.616 | 0.414 | **0.755** | 0.752 | 0.003 | 578 |

**Ratios (BASELINE / OURS — higher means our strokes are steadier):**

| scene | frames | Frechet ratio | P_pop ratio |
|---|---|---|---|
| lego | 30 | **2.43x** | **3.44x** |
| lego | 60 | **4.24x** | **5.30x** |
| lego | 120 | **7.49x** | **8.10x** |
| lego | 240 | **14.03x** | **11.49x** |
| chair | 30 | **4.19x** | **8.52x** |
| chair | 60 | **7.87x** | **10.17x** |
| chair | 120 | **15.22x** | **11.11x** |
| chair | 240 | **29.92x** | **11.35x** |

The mechanism is in the scaling, not only the ratio. OURS falls roughly in proportion to the per-frame motion (halving on each frame-doubling), i.e. its residual is warp resampling and nothing else; BASELINE is nearly flat across the same range, saturating at a motion-independent floor. That floor is the popping: its strokes are re-derived every frame, so most of them have no counterpart in the next one.

## 2. Confound controls

### 2a. Sparsity

A method could fake a low `P_pop` by drawing fewer, easier strokes. The opposite holds here — OURS is the DENSER stroke set:

| scene | frames | OURS strokes/frame | BASE strokes/frame | OURS unmatched | BASE unmatched |
|---|---|---|---|---|---|
| lego | 120 | 1121 | 617 | 0.065 | 0.732 |
| lego | 240 | 1122 | 615 | 0.037 | 0.717 |
| chair | 120 | 752 | 575 | 0.025 | 0.753 |
| chair | 240 | 751 | 578 | 0.023 | 0.752 |

### 2b. Silhouette warp-drop

The baseline's Canny fires on the object silhouette, where the gaussian z-buffer is empty; those strokes cannot be forward-warped at all and would be charged as popping through the warp operator rather than through any real instability. Measured drop rate: **BASELINE 19.8% (lego) / 18.2% (chair) vs OURS 0.2% / 0.0%**. The control removes it at source by restricting BOTH pipelines to the object interior (OURS draws interior crease carriers and cannot draw silhouettes either).

| scene | frames | pipeline | Frechet med | **P_pop** | strokes/frame |
|---|---|---|---|---|---|
| lego | 120 | OURS | 0.175 | **0.132** | 1048 |
| lego | 120 | BASE | 1.253 | **0.699** | 413 |
| lego | 240 | OURS | 0.088 | **0.105** | 1048 |
| lego | 240 | BASE | 1.189 | **0.680** | 411 |
| chair | 120 | OURS | 0.082 | **0.103** | 712 |
| chair | 120 | BASE | 1.213 | **0.708** | 282 |
| chair | 240 | OURS | 0.041 | **0.100** | 711 |
| chair | 240 | BASE | 1.176 | **0.704** | 283 |

| scene | frames | Frechet ratio (controlled) | P_pop ratio (controlled) |
|---|---|---|---|
| lego | 120 | 7.15x | 5.29x |
| lego | 240 | 13.44x | 6.49x |
| chair | 120 | 14.83x | 6.85x |
| chair | 240 | 28.79x | 7.01x |

The advantage survives both controls.

## 3. Limitation — texture false positives on a frozen 3DGS

The temporal result above is about the **stability** of the extracted lines. It says nothing about whether every extracted line *should* exist, and on a texture-rich object many should not.

### 3.1 Quantified false-positive line density

On chair, we measure line density inside **GT-verified-flat regions**: pixels on the GT mesh that are more than *c* px from any visible GT crease and more than 4 px from the silhouette, so that occluding contours — which are legitimately line-worthy — cannot be miscounted. Every line drawn there is a false positive.

| flat-region definition | FP line px per kilopixel | with carrier-persistence prune |
|---|---|---|
| >5 px from any GT crease | **22.1** | 13.0 |
| >8 px from any GT crease | **12.1** | 7.4 |

That is 22.1 px/kpx of ink laid down on surfaces that are provably flat, reducible to 13.0 px/kpx by a persistence filter that keeps only carriers with stable multi-view support (16208 -> 13124 linelets). **These are false positives and are reported as such.** They are not stylistic hatching, and the persistence filter does not identify texture — it removes weakly supported carriers, some of which happen to lie on flat regions.

### 3.2 Why post-hoc extraction cannot fix this

The failure is structural, not a matter of a better filter. On a frozen vanilla 3DGS the printed pattern is **baked into the geometry**: the reconstruction places real, tilted splats wherever the colour varies, because that is where the photometric evidence is. Labelling Canny pixels by the GT mesh and measuring the bilateral-ribbon dihedral from the rendered G-buffer gives

| population | dihedral theta |
|---|---|
| fabric print | p50 28.8 deg, **p95 79.3 deg** |
| true crease | **p05 4.9 deg**, p50 23.4 deg |

i.e. the print is *more* dihedral than the crease and the two distributions overlap almost completely (separation -74.4 deg against the +6 deg a usable gate would need). The estimator is sound: the identical ribbon code run on GT-mesh depth separates the two classes at AUC 0.72-0.77, while on gaussian depth it is at chance (AUC 0.42-0.51). So the geometry channel is poisoned by albedo.

Inverting the test does not help, because the albedo channel is poisoned by geometry. The SH degree-0 term is not a material property — it is mean radiance, so a crease bakes its own shading step into it. The bilateral SH-DC albedo step gives AUC(fabric>crease) = **0.31 on chair** (the hypothesis is backwards: creases carry the *larger* albedo step, p50 0.175 vs 0.092) and **0.500 on lego** (exactly chance).

Consistently, a geometry-gated DT built on that signal buys almost nothing end-to-end on held-out TEST. Segment precision / recall @1.5 px, gated vs ungated:

| scene | ungated | geometry-gated | change |
|---|---|---|---|
| chair (texture stress) | 0.6024 / 0.7206 | 0.6067 / 0.7077 | +0.4 pp P, -1.3 pp R |
| lego (hard surface) | 0.5628 / 0.4193 | 0.5826 / 0.4168 | +2.0 pp P, -0.25 pp R |

On chair that lands on the ungated precision/recall frontier, i.e. no real gain; on lego it is a small genuine gain, consistent with lego's edges already being mostly real geometry. Multi-view rescues fare no better either: across-view dihedral variance AUC 0.577, world-normal consensus 0.596, and the best candidate of any kind — shading-vs-albedo view-contrast variance — only 0.638, itself largely explained by edge contrast alone (control AUC 0.619).

**Conclusion.** Print and crease are not separable *after* the fact from a frozen vanilla 3DGS, because that representation does not factor material from geometry in either direction. The contamination has to be attacked upstream — a reconstruction whose geometry is not albedo-driven (normal- or smoothness-regularised training), or a seeding stage that never proposes on flat-but-patterned surface — not by filtering the edge field downstream. Scenes should be scoped accordingly: lego-like hard surfaces are the primary regime (Canny edge purity 0.663), chair is a texture false-positive stress case (purity 0.284).

## 4. Ablation — carrier-persistence prune (not part of the headline)

chair, 16208 -> 13124 linelets (multi-view inlier ratio >= 0.8, seen in >= 20 views), applied before chaining.

| variant | FP px/kpx (>5px) | FP px/kpx (>8px) | OURS Frechet med | OURS P_pop | strokes/frame |
|---|---|---|---|---|---|
| base | 22.1 | 12.1 | 0.082 | 0.068 | 752 |
| carrier-persistence | 13.0 | 7.4 | 0.072 | 0.076 | 661 |

It cuts flat-region FP density by ~40% at essentially no temporal cost, but see 3.1: it is a support filter, not a texture detector.

## 5. Stroke graphs and reproduction

| scene | linelets | after 3D NMS | strokes | median vertices/stroke |
|---|---|---|---|---|
| lego | 25870 | 14302 | 1897 | 4 |
| chair | 16208 | 8679 | 1184 | 4 |

```
python scripts/m1b_stroke_temporal.py --scenes lego chair --frames 30 60 120 240 --tag _orbit
python scripts/m1b_stroke_temporal.py --scenes lego chair --frames 120 240 --fg_only --tag _orbit_fgonly
python scripts/m1b_ablation_carrier.py --scene chair --frames 120
python scripts/m1b_consolidate.py
```

Side-by-side videos: `out/m1b_temporal_sidebyside_{chair,lego}.mp4` (240 frames, same orbit).
