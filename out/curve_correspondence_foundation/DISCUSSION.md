# Scientific interpretation

**STOP_CORRESPONDENCE for Lego and Chair.** The explicit correspondence formulation produces some persistent 3D curves, unlike the corrected local-pixel baseline, but does not establish the registered foundation hypothesis. Both primary arms fail G1–G4 in both scenes, and neither scene meets stable GS benefit. These machine failures determine STOP without independent manual review.

The one formulation is unique calibrated epipolar-intersection matching of ordered Canny segments, fixed bilateral RGB evidence, mutual ambiguity margins, closed three-view identities, monotone arc maps, robust triangulation and bounded shared-polyline bundle adjustment. Identity is frozen before fitting. The GS arm only vetoes unsupported spans; it never invents an identity.

The preregistration and literature memo were committed and pushed before execution. The targeted classical literature establishes that curve identity, confirmation views, ordering and bundle adjustment are not novel inventions. This experiment contributes a controlled feasibility/abstention result under fixed images and qualified GS priors. See LITERATURE.md for verified sources and reading limits.

## Yield and prediction

Supported F length is averaged over all eight F views, counting a track only in its matched observation views and counting zero in the others. C/DEV prediction lengths are means over all held-out views. Joint support requires distance <=2px and unoriented tangent error <=20 degrees; unknown directions count against it. Detector proximity is not ground-truth correspondence accuracy.

| Scene / arm | Tracks | Separated | F supported length (px/view) | Four-view fraction | C joint | DEV joint | C independent overlap (forward/backward) |
|---|---:|---:|---:|---:|---:|---:|---|
| lego / image_only | 3 | 3 | 31.559 | 0.000 | 0.403 | 0.537 | 0.000/0.000 |
| lego / gs | 1 | 1 | 5.890 | 0.000 | 0.475 | 0.685 | 0.000/0.000 |
| chair / image_only | 2 | 2 | 17.137 | 0.000 | 0.287 | 0.712 | 0.000/0.000 |
| chair / gs | 1 | 1 | 10.795 | 0.000 | 0.301 | 0.861 | 0.000/0.000 |

Every primary track has three views; none reaches four views. The gates require at least 12 spatially separated tracks, 300 supported F pixels/view, six occupied cells in four views and at least 25% four-view tracks. F residual/tangent fits pass for the few accepted curves, but fitting the generating images does not establish prediction.

| Scene / arm / split | Distance median/P90 (px) | Tangent median/P90 (deg) | Track coverage | Good/bad length (px/view) |
|---|---|---|---:|---|
| lego / image_only / C | 1.000/8.602 | 20.221/90.000 | 0.667 | 29.331/39.663 |
| lego / image_only / DEV | 1.000/3.000 | 7.871/90.000 | 0.667 | 39.542/31.700 |
| lego / gs / C | 0.000/1.000 | 21.297/90.000 | 1.000 | 6.592/6.144 |
| lego / gs / DEV | 1.000/1.000 | 11.284/90.000 | 1.000 | 10.788/5.023 |
| chair / image_only / C | 3.606/6.708 | 8.464/79.768 | 0.500 | 12.271/36.290 |
| chair / image_only / DEV | 0.000/2.000 | 8.565/50.526 | 0.500 | 30.115/12.173 |
| chair / gs / C | 4.472/6.708 | 5.918/41.462 | 1.000 | 7.848/24.100 |
| chair / gs / DEV | 0.000/2.000 | 6.025/17.446 | 1.000 | 21.871/2.655 |

Chair GS passes the DEV prediction sub-gate, but fails C prediction and the other necessary gates. No average or favorable view rescues either scene. The all-in-frame gate conservatively includes occluded spans. Visibility-stratified sample counts and projected lengths are in visibility/SCENE; they cannot change this gate.

## Correspondence controls

| Scene / arm | F curves | C joint | DEV joint | C good length | DEV good length |
|---|---:|---:|---:|---:|---:|
| lego / shifted | 0 | 0.000 | 0.000 | 0.000 | 0.000 |
| lego / shifted_gs | 0 | 0.000 | 0.000 | 0.000 | 0.000 |
| lego / random_graph | 0 | 0.000 | 0.000 | 0.000 | 0.000 |
| lego / random_graph_gs | 0 | 0.000 | 0.000 | 0.000 | 0.000 |
| lego / pairwise | 175 | 0.295 | 0.445 | 1289.409 | 1942.925 |
| lego / pairwise_gs | 27 | 0.386 | 0.664 | 392.448 | 695.601 |
| lego / no_order | 5 | 0.369 | 0.557 | 52.672 | 72.858 |
| lego / no_order_gs | 3 | 0.453 | 0.648 | 24.399 | 32.324 |
| chair / shifted | 0 | 0.000 | 0.000 | 0.000 | 0.000 |
| chair / shifted_gs | 0 | 0.000 | 0.000 | 0.000 | 0.000 |
| chair / random_graph | 0 | 0.000 | 0.000 | 0.000 | 0.000 |
| chair / random_graph_gs | 0 | 0.000 | 0.000 | 0.000 | 0.000 |
| chair / pairwise | 169 | 0.287 | 0.364 | 915.367 | 1156.816 |
| chair / pairwise_gs | 18 | 0.369 | 0.614 | 113.980 | 184.946 |
| chair / no_order | 2 | 0.288 | 0.714 | 12.396 | 30.530 |
| chair / no_order_gs | 1 | 0.301 | 0.861 | 7.848 | 21.871 |

Shifted and randomized associations retain their input counts but yield zero curves. This rejects those nulls. It does not pass G4: disabling order remains comparable by the frozen supported-length/precision criterion. Chair’s GS no-order output is identical to its primary GS output. Pairwise-only fitting produces many more curves and substantial unsupported clutter; its large good-length totals cannot certify correct persistent identities.

All geometrically proposed pairs, ambiguous competitors, triangle/order failures and rejected fits remain in compressed records. Deterministic diagnostic panels show both selected pairs and competing curves. No successful track was hand-selected into the primary output.

## Re-estimation and GS contribution

| Scene / arm | Independent C curves | LOO passes / 8 | Qualified dose passes | Independent seed |
|---|---:|---:|---|---|
| lego / image_only | 2 | 1/8 | not a measured GS test | prior independent by construction |
| lego / gs | 0 | 4/8 | 9/9 | not eligible |
| chair / image_only | 3 | 4/8 | not a measured GS test | prior independent by construction |
| chair / gs | 1 | 4/8 | 9/9 | FAIL |

Independent C reconstructions have zero bidirectional tube overlap with F in both arms and scenes. Most LOO re-estimations lose or replace supported spans. All nine controlled vetoes retain each scene’s single GS curve, but this stability is insufficient: retained coordinates are unchanged by construction. Chair seed2718 retains a shorter span; forward coverage is 0.631 and total length changes by 43.214%, exceeding the frozen 15% limit. Lego is CONTROLLED_ONLY because its second seed failed inherited replay calibration.

The primary GS veto reduces unsupported DEV length but discards too much supported length: approximately 72.7% on Lego and 27.4% on Chair, versus a maximum permitted loss of 10%. It provides no stable net benefit under G5. Image-only also fails, so PIVOT_IMAGE_ONLY is not warranted. Drums and Ficus have no eligible parent and remain INSUFFICIENT_POSTERIOR_QUALITY; no stress test was executed on them.

## Visual and failure evidence

Internal inspection of actual extraction, identity rejection, projection and comparison sheets shows extensive Canny fragmentation and sparse surviving spans. The Chair DEV42 overlay includes a short top-back contour fragment and a short lower-frame fragment; this does not establish six coherent shape spans or two internal structures. Pairwise reconstructions are visibly fragmented and cluttered; dense PCA linelets remain a visual reference, not curve truth. These observations are internal and unblinded, and are not a manual-gate pass.

Explicit failure buckets retain silhouette, shadow, highlight, repeated-texture, junction and multilayer/cross-part diagnostics. Inherited boxes are coarse proxies, shadows/highlights overlap, and absent certified regions are marked unknown. No unsupported semantic error rate is claimed. Wrong depth and cross-part identity remain diagnostic hypotheses rather than mesh-verified truth.

There are 2,030 canonical PNGs, fourteen 120-frame MP4s and 264 randomized review images. All reached primary/control arms have fixed F/C/DEV views; reached LOO and posterior arms have fixed-F sheets. Fixed-cardinality comparison uses one curve per nonempty arm. At the frozen 60%-of-minimum-F-ink budget, every correspondence arm misses the 5% tolerance; attempted ink sheets are retained and marked incomparable. Width and geometry were not modified to obtain a favorable comparison.

Videos project fixed persistent geometry onto white backgrounds along the frozen orbit. They do not have new orbit GS visibility renders or RGB truth. The identity key is outside each blinded directory; there have been zero independent reviews. Independent visual review remains pending, but cannot reverse the failed necessary machine gates.

## Validity and scope

TDD records 13 observed RED runs across 12 behavior slices, successful GREEN resolutions and passing refactor/full checks. The final targeted suite passes 45 tests and the unchanged repository suite passes 127. A contiguous-image drawing fix repaired the first Lego display attempt without changing any numerical metric/sample array. The first complete-suite wrapper failed runtime access/path checks and was corrected; every failed attempt remains. See EXECUTION_NOTES.md for exact boundaries.

Native-open auditing includes pre-confinement byte hashing and the failed display attempt. TEST bytes stay sealed; no mesh enters generation, matching, fitting, parameter selection or evaluation. All eight posterior hashes and prior archives are checked again after the complete suite. Large arrays and traces are preserved server-side with exact inventory.

The negative result is specific: a minimal unique-intersection, local-RGB, strict-segment-identity formulation cannot establish a useful repeatable foundation on both eligible scenes. It is not a proof that explicit cross-view curve correspondence is impossible. The observed bottlenecks include short/fragmented segment identity, ambiguous local appearance, strong order/common-support rejection and insufficient stability across independent view sets. No detector, threshold, dose or DEV-based repair was attempted, and no UDF/stroke system was built.
