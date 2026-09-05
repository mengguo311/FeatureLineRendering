# B3 — per-scene table (held-out TEST; mesh EVAL-ONLY)

TEST views [5,15,...,95]; DT pull on TRAIN views only. Definitions: pixel precision/recall at 1.5 px vs GT-mesh crease pixels (mesh EVAL-ONLY), mean over the 10 TEST views; points = linelet centres, segments = rasterised linelets. Temporal: forward-warped stroke residual on the 240-frame look-at orbit between TEST views 5 and 15; P_pop = popped-stroke fraction, ratio = Canny/OURS (higher = OURS steadier).

## Shipped lines (M1b gated variant): precision / recall / F1 vs GT-mesh creases

| scene | n lines | points P@1.5 | R@1.5 | F1 | segments P@1.5 | R@1.5 | F1 | segments P@2.5 | R@2.5 | ungated seg P/R@1.5 |
|---|---|---|---|---|---|---|---|---|---|---|
| chair | 15,091 | 0.735 | 0.503 | 0.598 | 0.657 | 0.596 | 0.625 | 0.778 | 0.672 | 0.646 / 0.644 |
| lego | 20,142 | 0.644 | 0.228 | 0.336 | 0.620 | 0.286 | 0.391 | 0.762 | 0.369 | 0.592 / 0.295 |
| ficus | 5,305 | 0.219 | 0.134 | 0.166 | 0.222 | 0.170 | 0.192 | 0.296 | 0.243 | 0.197 / 0.226 |

## Temporal coherence: object-space lines vs per-frame Canny (P_pop ratio = Canny/OURS; the 7-13x crown jewel = 120-240 f band)

| scene | 30 f P_pop OURS / Canny (ratio) | 60 f | 120 f | 240 f | Frechet ratio 240 f | strokes/frame OURS / Canny |
|---|---|---|---|---|---|---|
| chair | 0.093 / 0.788 (**8.52x**) | 0.076 / 0.770 (**10.17x**) | 0.068 / 0.756 (**11.11x**) | 0.067 / 0.755 (**11.35x**) | 29.92x | 751 / 578 |
| lego | 0.234 / 0.803 (**3.44x**) | 0.144 / 0.764 (**5.30x**) | 0.091 / 0.734 (**8.10x**) | 0.063 / 0.719 (**11.49x**) | 14.03x | 1122 / 615 |
| ficus | 0.417 / 0.876 (**2.10x**) | 0.275 / 0.854 (**3.11x**) | 0.164 / 0.820 (**5.01x**) | 0.103 / 0.786 (**7.64x**) | 11.36x | 421 / 571 |

## Coverage-ceiling breaker and discriminator (context rows)

| scene | DexiNed triangulation 3D recall @1.5px-equiv | single-view depth lift | miss-set recovery | triangulation precision | DINOv2 crease-vs-texture AUC (held-out) |
|---|---|---|---|---|---|
| chair | 0.6753 | 0.6583 | 0.6914 | 0.1636 | 0.8401 (RESULTS_MASTER.md (DINOv2 semantic family, held-out, P1c/P1d)) |
| lego | 0.2112 | — | — | — | 0.9044 (RESULTS_MASTER.md (DINOv2 semantic family, held-out, P1c/P1d)) |
| ficus | 0.6489 | 0.5483 | 0.6117 | 0.1280 | — (not run (P1c is scoped to chair/lego)) |

## Caveats

- ficus: the banked headline table (out/m1b_headline_table.md) EXCLUDES ficus by design ('thin/foliage: only 33% of object pixels are >4px from a silhouette, so crease vs flat surface is not well posed'); it is run here for completeness with the identical frozen recipe and reported straight. Its GT crease set (mesh_oracle, split-vertex face adjacency) covers only ~31% of the geometric >=30deg edges and none of the 31,390 open-boundary leaf-rim edges, so P/R vs 'GT creases' understates what the lines capture on a plant.
- train-fit vs test-eval: the DT pull (the only fitted step) consumed the 80 TRAIN views; every P/R and temporal number is on the 10 held-out TEST views / the TEST-to-TEST orbit. The prune/length thresholds ('tuned') were selected on VAL views per the M1b protocol; no number here is in-sample.
- line-buffer pivot NO-GO (motivation for shipping the frozen design): pre-registered EPIPOLAR ACCUMULATION TEST, corrected labels (out/EPIPOLAR_ACCUM_RESULTS.md): lego S_bar AUC 0.698 / Recall@85%P 0.000 (NO-GO, structural), chair 0.859 / 0.000 (NO-GO, knife-edge). Multi-view accumulation of raw DexiNed does not separate missed creases from flat surface at 85% precision; the mechanism is DexiNed's ~5 px spatial response tail on edge-dense surfaces, not dead zeros. (The B3 spec's 0.572/0.733 figures are from the superseded first run with a label bug.)
- GT crease topology (inherited, all scenes): src/mesh_oracle.py builds GT creases from split-vertex face adjacency; the banked crease set covers 37% (lego) / 43% (chair) / ~31% (ficus) of the geometric >=30deg edges. All P/R here are against that banked definition, as in every prior result.

Sources per cell are in `out/ship/tab_ship_perscene.json` (`source` fields).