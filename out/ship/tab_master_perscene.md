# B3 master per-scene table — shipped M1b object-space lines (gated variant), held-out TEST, mesh EVAL-ONLY

Shipped generator: M1b: frozen-3DGS carrier seeds -> linelets -> multi-view DT pull (TRAIN views) -> consensus prune -> 3D NMS + chaining -> per-frame projection through the 3DGS z-buffer.  triangulation recall and DINOv2 AUC are Contribution B DIAGNOSTIC precision-boundary rows; they are NOT stages of the shipped generator.

| scene | shipped lines | points P / R / F1 @1.5 | segments P / R / F1 @1.5 | P_pop 240 f ours / Canny | **P_pop ratio** | Frechet med 240 f ours / Canny (px) | **Frechet ratio** | strokes/frame ours / Canny | ctx: triangulation 3D recall | ctx: DINOv2 AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| chair | 15,091 | 0.735 / 0.503 / 0.598 | 0.657 / 0.596 / 0.625 | 0.067 / 0.755 | **11.35x** | 0.041 / 1.225 | **29.92x** | 751 / 578 | 0.675 | 0.840 |
| lego | 20,142 | 0.644 / 0.228 / 0.336 | 0.620 / 0.286 / 0.391 | 0.063 / 0.719 | **11.49x** | 0.086 / 1.202 | **14.03x** | 1122 / 615 | 0.211 | 0.904 |
| ficus | 5,305 | 0.219 / 0.134 / 0.166 | 0.222 / 0.170 / 0.192 | 0.103 / 0.786 | **7.64x** | 0.101 / 1.148 | **11.36x** | 421 / 571 | 0.649 | — |

forward-warped stroke residual on the 240-frame look-at orbit between TEST views 5 and 15; P_pop = popped-stroke fraction, ratio = Canny/OURS (higher = OURS steadier); ratios at 240 frames (the finest-motion end of the banked 7-13x band).

## Caveats

- ficus: the banked headline table (out/m1b_headline_table.md) EXCLUDES ficus by design ('thin/foliage: only 33% of object pixels are >4px from a silhouette, so crease vs flat surface is not well posed'); it is run here for completeness with the identical frozen recipe and reported straight. Its GT crease set (mesh_oracle, split-vertex face adjacency) covers only ~31% of the geometric >=30deg edges and none of the 31,390 open-boundary leaf-rim edges, so P/R vs 'GT creases' understates what the lines capture on a plant.
- train-fit vs test-eval: the DT pull (the only fitted step) consumed the 80 TRAIN views; every P/R and temporal number is on the 10 held-out TEST views / the TEST-to-TEST orbit. The prune/length thresholds ('tuned') were selected on VAL views per the M1b protocol; no number here is in-sample.
- line-buffer pivot NO-GO (motivation for shipping the frozen design): pre-registered EPIPOLAR ACCUMULATION TEST, corrected labels (out/EPIPOLAR_ACCUM_RESULTS.md): lego S_bar AUC 0.698 / Recall@85%P 0.000 (NO-GO, structural), chair 0.859 / 0.000 (NO-GO, knife-edge). Multi-view accumulation of raw DexiNed does not separate missed creases from flat surface at 85% precision; the mechanism is DexiNed's ~5 px spatial response tail on edge-dense surfaces, not dead zeros. (The B3 spec's 0.572/0.733 figures are from the superseded first run with a label bug.)
- GT crease topology (inherited, all scenes): src/mesh_oracle.py builds GT creases from split-vertex face adjacency; the banked crease set covers 37% (lego) / 43% (chair) / ~31% (ficus) of the geometric >=30deg edges. All P/R here are against that banked definition, as in every prior result.