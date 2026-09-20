# Density-ridge feasibility experiment

**Preregistered global result: limited GO for a later 3D feasibility experiment, on opacity and flattening only.** The broad bands are useful on Lego, Chair and Drums. Ficus is a partial result: opacity preserves pot/stem bands but almost no leaves; geometric channels produce crowded short canopy arcs. Other channels remain PIVOT under the combined criteria. This does not mean the current experiment produced persistent strokes.

**This is a 2D orthographic PCA-projection diagnostic. It cannot establish multi-view or 3D persistence.** All depths are superposed without visibility filtering. No source RGB image, mesh, 2DGS, SDF, learned detector, or retraining was used. The displayed color is SH-DC decoded from the frozen PLY, not a rendered source photograph.

## Evidence to inspect

- [Cross-scene final overlays](all_scenes_ridge_summary.png), fixed seven-channel order.
- Atlases: [Lego](lego_ridge_atlas.png), [Chair](chair_ridge_atlas.png), [Drums](drums_ridge_atlas.png), [Ficus](ficus_ridge_atlas.png).
- Raw-mask audits: [Lego](lego_raw_audit.png), [Chair](chair_raw_audit.png), [Drums](drums_raw_audit.png), [Ficus](ficus_raw_audit.png).
- [Frozen protocol](PROTOCOL.md), [parameters and metrics](metrics.json), [visual review and decisions](visual_review.json), [verification](verification.json).

Each atlas has five rows: normalized source field, density-coupled detector input, Hessian ridge response, cleaned/matched ridge overlay, and gradient baseline overlay. Each source scalar has the same 0–1 range; ridge display maxima are pooled by channel and printed. Black areas are outside the common support map. Arrays retain the unmasked fields. The background in each overlay is the same dim PLY-color/density image, so recognizable background alone is not evidence that a mask captured the object. Cyan/amber pixels are the actual selected masks.

## Frozen method

All 1,212,012 Gaussian centers from the four seed_1729/iteration_30000 vanilla checkpoints contribute. The exact old atlas frame and 24,000-point crop sample are reused, while KDE and 24-NN attributes use all centers. The cropped grids have 640 pixels on the longer axis. Gaussian attributes enter an adaptive unit-count center KDE, not the covariance-mixture density PDF. Count denominator, confidence, support, attribute numerators, normalized attributes, tensor/coherence, detector inputs, every response, and every mask stage are saved.

Color uses the gradient energy of normalized KDE RGB. Axis orientation uses gradients of the sign-invariant tensor n n^T and its coherence. The other five channels use normalized attribute times confidence and square-root log-density strength. Positive multiscale Hessian ridges are selected at sigma 1.5, 2.5 and 4 pixels, with anisotropy gating, transverse nonmaximum suppression and nominal 3-pixel broadening. The eigenvalue anisotropy design is inspired by [Frangi et al. (1998)](https://doi.org/10.1007/BFb0056195); this is an explicitly specified variant, not a replication of full Frangi/Steger.

The baseline is Gaussian-gradient energy of the same scalar input, or the same color/tensor discontinuity energy before Hessian filtering. A stable pooled ranking selects 6% of supported pixels per channel. Both methods remove components smaller than 12 pixels, then the larger pooled cleaned mask is trimmed to exactly match the smaller. There is no joining, closing, hole filling, or post-trim repair. Nominal band width is 3 pixels; crossings and ranking can widen or truncate it. Actual width statistics are recorded.

**Ink is exactly matched across the four scenes per channel, not within each scene.** The baseline spends much more geometric-channel ink on Ficus, while ridge selection reallocates it to Chair and Drums. Consequently, per-scene visual or connectivity improvements are partly confounded by ink allocation. This protocol tests the pooled recipe, not superiority at equal per-scene recall or ink.

## Machine and visual decisions

| Channel | Machine scene passes | Median long-fraction gain | Machine | Visual | Final |
|---|---:|---:|---|---|---|
| SH-DC color | 2/4 | +0.044 | PIVOT | PIVOT | **PIVOT** |
| Axial orientation | 0/4 | +0.068 | STOP | PIVOT | **PIVOT** |
| Opacity | 4/4 | +0.110 | GO | GO | **GO** |
| Flattening | 3/4 | +0.116 | GO | GO | **GO** |
| 24-NN planarity | 2/4 | +0.116 | PIVOT | PIVOT | **PIVOT** |
| Axis/PCA agreement | 3/4 | +0.061 | GO | PIVOT | **PIVOT** |
| Surface proxy | 4/4 | +0.105 | GO | PIVOT | **PIVOT** |

A machine pass checks coverage budget, supported ink, long-component fraction, fragment density, raw retention and baseline-relative connectivity. A channel GO needs at least three scene passes and a median connectivity gain of at least 0.05. Visual GO separately needs at least three PASS and no FAIL. Final GO requires both; two final channel GOs give the global limited GO. Exact rules were frozen before results. Machine topology scores are not precision or recall. Support overlap is 100% by construction and is only a validity check. Long connected components can still be wrong, doubled or branched.

| Scene | Color | Axis | Opacity | Flattening | Planarity | Agreement | Surface |
|---|---|---|---|---|---|---|---|
| lego | PASS | PARTIAL | PASS | PASS | PARTIAL | PARTIAL | PARTIAL |
| chair | PARTIAL | FAIL | PASS | PASS | PASS | PARTIAL | PASS |
| drums | PARTIAL | PARTIAL | PASS | PASS | PASS | PASS | PASS |
| ficus | FAIL | PARTIAL | PARTIAL | PARTIAL | PARTIAL | PARTIAL | PARTIAL |

## Per-scene observations and earliest limitations

### Lego

| Channel | Visual | Earliest limitation | Observation |
|---|---|---|---|
| SH-DC color | PASS | field construction | Cab, bucket, tread and base yield recognizable bands with less chunky texture than the gradient baseline. Repeated base strips remain; projected color/material changes are not necessarily geometry. |
| Axial orientation | PARTIAL | field construction | Cab and bucket carry useful axis boundaries, but patchy covariance orientation gives short segments and loses the tread. Tensor averaging is sign-safe but does not remove mixed-depth orientations. |
| Opacity | PASS | ridge response | Cab, arm/bucket and upper tread arcs form several clear bands, more coherent than the gradient patches. Some doubled tread arcs and internal holes survive; these may be density ridges rather than separate structures. |
| Flattening | PASS | field construction | A clean cab, bucket edge and long upper tread arc give a useful simplified drawing. The nearly saturated flattening attribute makes the detector largely a density tracer; several joins and base details are absent. |
| 24-NN planarity | PARTIAL | selection | The response contains object curves, but pooled selection leaves mostly cab/bucket pieces and isolated tread fragments. Only 42% of retained ink belongs to long components. |
| Axis/PCA agreement | PARTIAL | selection | Cab and bucket boundaries survive, but the tread arc is materially more interrupted than in flattening; sparse interior dashes remain. The normalized field is strongly density-correlated after coupling. |
| Surface proxy | PARTIAL | selection | Cab and bucket fragments are meaningful, but much of the tread and body is missing. The conservative selection has not produced a comparably complete simplification to opacity or flattening. |

### Chair

| Channel | Visual | Earliest limitation | Observation |
|---|---|---|---|
| SH-DC color | PARTIAL | field construction | The outer seat curve is clear, but upholstery/color texture produces interior wiggles and a busy lower border. Baseline advantage is modest and the left/back structure remains incomplete. |
| Axial orientation | FAIL | field construction | Interior tensor/coherence variation yields many little curls and flecks with only partial outer structure. Most ink is in short components; the axis field is not a useful broad-line drawing under this recipe. |
| Opacity | PASS | selection | Long seat outline, lower rail and central gap bands simplify the texture substantially. Some left/back frame is missing and the interior gap is not fully connected; the scene receives more ink than its baseline. |
| Flattening | PASS | field construction | Clean seat rim, upper/lower frame pieces and central separator remain with little stipple. Strong density domination and low pooled allocation leave the left structure incomplete; this is a partial drawing, not a full contour recovery. |
| 24-NN planarity | PASS | selection | Seat and central-gap bands are coherent with few fragments and less speckling than the baseline. Remaining frame portions are omitted by pooled selection; no surface correctness can be inferred. |
| Axis/PCA agreement | PARTIAL | selection | The seat arc is useful, but central-gap and back regions are broken into isolated dashes. Improvement over the baseline is too limited for a visual GO in this scene. |
| Surface proxy | PASS | selection | Seat rim and central separator are clean and relatively connected. The left structure and most interior organization are absent, and the per-scene baseline has less ink despite exact pooled matching. |

### Drums

| Channel | Visual | Earliest limitation | Observation |
|---|---|---|---|
| SH-DC color | PARTIAL | field construction | Red drum rims and several stands are recognizable, but textured central drums and the pedal produce busy loops. Broad uniform cymbals contribute little color discontinuity; baseline long-component fraction is better. |
| Axial orientation | PARTIAL | field construction | Some drum rings and supports appear, but uniform cymbal orientation supplies little discontinuity while mixed central axes create fragments. The large clean cymbal rims seen in scalar channels are mostly missing. |
| Opacity | PASS | ridge response | Several round drum/cymbal rims and stand segments form a readable set of bands. Some incomplete/doubled rings and interior spots remain; flattening is visually cleaner on the largest cymbals. |
| Flattening | PASS | field construction | The clearest collection of cymbal/drum ellipses and stand branches, with much less stipple than gradient selection. Overlapping drums remain ambiguous and high flattening makes density the dominant driver. |
| 24-NN planarity | PASS | field construction | Large rims and long support segments are coherent; the gradient baseline breaks many of these into pieces. Overlap mixes different depths, and the strong similarity to other scalar channels limits attribute-specific interpretation. |
| Axis/PCA agreement | PASS | field construction | Cymbal ellipses, drum rings and several stands are clearly organized and cleaner than the baseline. Some inner rings and thin junctions are missing; the field remains strongly correlated with density. |
| Surface proxy | PASS | field construction | Major cymbal/drum rims and supporting rods are recognizable broad bands. Central overlapping instruments and short rim gaps remain unresolved, and the method cannot assign a depth to any crossing. |

### Ficus

| Channel | Visual | Earliest limitation | Observation |
|---|---|---|---|
| SH-DC color | FAIL | field construction | Mostly isolated leaf flecks with a few tiny pot/stem segments. Similar projected leaf colors and depth averaging give weak discontinuity energy; neither detector produces a meaningful plant drawing. |
| Axial orientation | PARTIAL | field construction | Numerous leaf-related arcs and some stem segments appear, but the canopy is crowded with short disconnected curves. Mixed projected axes and coherence changes dominate; baseline connectivity is actually higher. |
| Opacity | PARTIAL | field construction | Two pot-side bands and several stem branches are meaningful and cleaner than baseline specks, but almost all foliage disappears because its actual opacity is low. A machine pass therefore does not mean plant-wide coverage. |
| Flattening | PARTIAL | field construction | Some stems and leaf arcs are recognizable, but nearly saturated flattening reduces this to a density-driven canopy of short lobes. The baseline has a higher long-component fraction and receives substantially more scene ink. |
| 24-NN planarity | PARTIAL | field construction | Stems and many short leaf arcs survive, but superposed foliage forms a fragmented web with no reliable long leaf organization. Pooled allocation reaches 12.2% support ink, above the fixed machine gate. |
| Axis/PCA agreement | PARTIAL | field construction | Stem fragments and leaf-shaped curves are visible, yet the canopy remains cluttered and disconnected despite high source agreement. Density and projected layer mixing appear before ridge selection. |
| Surface proxy | PARTIAL | field construction | Several stem bands and many leaf arcs are meaningful, but the dense canopy remains fragmented and the pot boundary is incomplete. The baseline is at least as connected; the geometric mean does not resolve projected overlap. |

## Actual ink, connectivity and cleanup

Values below are final support ink percentages and long-component ink percentages for ridge/baseline. A long component has at least 24 skeleton pixels. The JSON also contains canvas ink, components, fragment counts, widths, raw masks and pre-matching cleanup metrics for every result.

| Scene / channel | Ink % R / B | Long % R / B | Fragments R / B | Ridge raw ink retained |
|---|---:|---:|---:|---:|
| lego / SH-DC color | 8.48 / 9.76 | 78.7 / 72.5 | 60 / 67 | 98.6% |
| lego / Axial orientation | 3.92 / 3.53 | 57.9 / 45.3 | 61 / 56 | 96.7% |
| lego / Opacity | 8.20 / 9.32 | 72.9 / 66.9 | 73 / 89 | 96.8% |
| lego / Flattening | 4.28 / 3.28 | 71.2 / 62.0 | 34 / 37 | 97.6% |
| lego / 24-NN planarity | 2.64 / 1.65 | 42.4 / 54.8 | 41 / 32 | 95.8% |
| lego / Axis/PCA agreement | 3.62 / 2.36 | 64.0 / 57.2 | 39 / 41 | 98.4% |
| lego / Surface proxy | 3.34 / 2.10 | 64.1 / 59.4 | 33 / 35 | 98.2% |
| chair / SH-DC color | 4.59 / 4.28 | 61.4 / 58.7 | 84 / 82 | 97.0% |
| chair / Axial orientation | 2.46 / 2.04 | 40.5 / 39.4 | 72 / 69 | 93.5% |
| chair / Opacity | 3.54 / 2.69 | 85.3 / 69.3 | 25 / 42 | 97.6% |
| chair / Flattening | 1.88 / 1.22 | 75.3 / 61.3 | 23 / 28 | 96.6% |
| chair / 24-NN planarity | 1.98 / 1.04 | 83.6 / 62.3 | 15 / 25 | 98.3% |
| chair / Axis/PCA agreement | 1.86 / 1.01 | 64.0 / 58.5 | 28 / 27 | 97.1% |
| chair / Surface proxy | 1.81 / 0.93 | 79.8 / 63.7 | 16 / 19 | 97.9% |
| drums / SH-DC color | 7.88 / 8.17 | 62.5 / 70.3 | 126 / 102 | 97.7% |
| drums / Axial orientation | 6.20 / 5.26 | 59.8 / 44.2 | 100 / 99 | 96.2% |
| drums / Opacity | 9.69 / 10.21 | 72.3 / 66.5 | 122 / 116 | 97.6% |
| drums / Flattening | 8.31 / 5.89 | 75.7 / 51.1 | 78 / 126 | 97.8% |
| drums / 24-NN planarity | 8.14 / 5.03 | 78.1 / 42.1 | 73 / 128 | 98.4% |
| drums / Axis/PCA agreement | 8.40 / 6.07 | 76.3 / 53.0 | 75 / 112 | 98.6% |
| drums / Surface proxy | 8.12 / 5.14 | 72.9 / 50.7 | 83 / 104 | 98.8% |
| ficus / SH-DC color | 2.25 / 0.99 | 10.8 / 0.0 | 72 / 37 | 92.6% |
| ficus / Axial orientation | 12.53 / 14.88 | 62.1 / 70.3 | 122 / 96 | 98.5% |
| ficus / Opacity | 1.69 / 1.12 | 70.9 / 29.4 | 16 / 26 | 96.2% |
| ficus / Flattening | 10.38 / 15.77 | 56.3 / 65.8 | 127 / 127 | 97.7% |
| ficus / 24-NN planarity | 12.16 / 18.91 | 67.3 / 65.5 | 115 / 150 | 97.0% |
| ficus / Axis/PCA agreement | 11.09 / 16.93 | 53.4 / 67.2 | 140 / 133 | 97.3% |
| ficus / Surface proxy | 11.89 / 18.64 | 63.6 / 68.4 | 122 / 142 | 97.5% |

Cleanup does not explain away the difficult scenes: the raw audit sheets show the same structural shortcomings. More than 92% of raw ridge ink survives in every scene/channel. Small-component removal still boosts some topology fractions, so raw, cleaned-unmatched, and final matched masks and metrics are all retained. Final pooled trimming can reintroduce short fragments; those fragments are counted without another cleanup pass.

## Interpretation and next experiment

The earliest general limitation is **field construction under depth-collapsing projection**. KDE averages unrelated front/back or overlapping structures, and the explicit density multiplier can dominate the scalar attribute. After coupling, flattening correlates with the density factor at roughly 0.93–0.97 in all four scenes; planarity/agreement/surface are also strongly density-correlated. These correlations are descriptive, not a density-only ablation. We cannot say that the attributes add value beyond center density. Uniform orientation/color regions also need not have a strong discontinuity at a geometric rim, explaining some missed cymbals.

Opacity and flattening justify a bounded next feasibility experiment: trace candidate 3D density ridges and test whether these 2D bands correspond to the same 3D neighborhoods under changed projections. The follow-up should preregister a density-only control, a per-scene-ink-matched comparison in addition to pooled allocation, independent view/depth consistency, and coverage measures so sparse pot/stem success cannot stand in for foliage recovery. None of those experiments was run here. PIVOT channels do not justify a standalone 3D claim under this protocol. Flattening is especially a candidate **density tracing** signal; its GO is not evidence that flattening itself provides novel geometric information.

Additional limitations: single seed and checkpoint; one PCA projection per scene; grid-scale rather than physical-scale parameters; quantized KDE bandwidth; kernel/binning approximation; proxy geometry without ground truth; synthetic tests cover simple curves/blobs/noise rather than every crossing; visual review is unblinded model inspection. The channel protocol deliberately tests positive scalar ridges, so low-valued valleys and scalar transitions with no density crest can be missed. No scientifically meaningful mask edits or parameter sweeps were made after inspection.

## Reproducibility and files

`src/density_ridge_lines.py` contains numerical kernels; `scripts/render_density_ridge_lines.py` runs the experiment and figures; `scripts/verify_density_ridge_lines.py` verifies it; `scripts/report_density_ridge_lines.py` records this explicit visual review. `tests/test_density_ridge_lines.py` was written before implementation and initially failed because the module was absent. The old tested quaternion, smallest-axis, flattening and local PCA functions were reused unchanged.

Canonical output is `out/density_ridge_lines/`. Curated PNG/JSON/report/protocol is `artifacts/density_ridge_lines/`. Each `*_ridge_grids.npz` stores 17 attribute numerator/normalized channels: RGB (3), row-major tensor (9), opacity/flattening/planarity/agreement/surface (5). Detector/mask arrays have channel-first shape (7,H,W). Coordinates have increasing y; figures display increasing y upward. The NPZ includes exact frame, crop, sample IDs, KDE IDs, bandwidths, pixel pitches, density, confidence and support. Existing `out/**/*.npz` ignore rules cover only these raw large arrays; no new blanket output ignore was added.

Verification passed: 5 new targeted, 5 legacy field, 9 legacy density, and 146 full-suite tests. All 15 generated protocol/metrics/NPZ/PNG files are byte-identical after a complete PLY rerun. All 36 canonical/curated/rerun PNG copies decode; all four NPZs pass semantic checks. All 61 hashed previous field/density files are unchanged. Every one of the nine unique final figures was visually inspected. The protocol and original tests retain their hashes.

The initial execution encountered a NumPy boolean JSON serialization error before any figures were saved; converting those metadata flags to Python bool fixed it without changing science. After viewing the first figures, only panel spacing, color legends and response-scale labels changed. Hashes confirm all four NPZs and metrics stayed unchanged across the layout edit. The final complete rerun uses that final layout. No diagnostic scientific deviation was used and no exploratory rescue appendix is needed.

No commit or push was made. Exact operational commands, output inventory, hashes, verdicts and unresolved limitations are also recorded in `/home/u00134/codex_astra_density_ridge_report.md`.
