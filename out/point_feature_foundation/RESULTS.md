# Foundation prerequisite result

**Verdict: UNDETERMINED. Hypothesis B was not scientifically tested.**

The stock renderer calibrated, but neither preregistered intervention qualified as RGB-near-equivalent. G0 therefore prevents a valid invariance experiment. The run stopped before local edge-band inference, all image controls, glyphs, DEV, and Chair. This is neither a scientific rejection of B nor evidence for a pivot.

| Gate | State | Evidence / limitation |
|---|---|---|
| G0 | INVALID | no qualifying nontrivial RGB-near-equivalent intervention |
| G1 | NOT_EVALUATED | local image evidence stage not reached |
| G2 | UNCERTIFIED | no frozen local output or independent DEV span annotations; C support not evaluated |
| G3 | NOT_EVALUATED | no eligible local outputs for repeatability |
| G4 | NOT_EVALUATED | local controls and independent visible-region comparison not reached |
| G5 | UNCERTIFIED | three independent evaluators unavailable; glyph stage not reached |

Chair: G0–G5 **NOT_RUN**; Lego did not permit transfer. No FOUNDATION-GO claim.

## Renderer and intervention evidence

Original Gaussians: 166,044; selected parents: 83,022; each perturbed asset: 249,066. Original PLY bytes were preserved. No defloat or center pruning was used.

| Check | Measurement | Required |
|---|---|---|
| White RGB max absolute error | 8.96751881e-05 | ≤1/255 = 0.00392156863 |
| Black RGB max absolute error | 0.000364154577 | ≤1/255 = 0.00392156863 |
| Alpha max absolute error | 0.000283837318 | ≤1/255 = 0.00392156863 |
| Selected-parent contribution, per-view range | 49.461323%–50.483222% | ≥20% in every view |
| Maximum outside-box contribution | 0.000000% | ≤1% |

| Intervention | Qualifying view/background pairs | PSNR range (dB) | SSIM range | P99 error range |
|---|---:|---:|---:|---:|
| clone | 0/32 | 38.34145–41.82743 | 0.9915701–0.9962918 | 0.0391951–0.0607494 |
| split | 0/32 | 38.44386–41.42265 | 0.9915466–0.9960904 | 0.0400663–0.0599458 |

All three limits must pass in every TRAIN view on both backgrounds: PSNR ≥40 dB, SSIM ≥0.995, P99 ≤8/255. The P99 criterion alone fails every measured pair for both interventions. No amplitude, parent, threshold, view, ROI, or detector was changed.

Baseline delta = 0.006785303354, from 796,671 conditional-median foreground depths. It is a pixel-scale unit, not certified surface accuracy. Full native conics, ordering, weights-derived maps, ROIs and depth quantiles are retained in lego/native/.

## Access and review boundaries

Forbidden successful input reads: 0; unresolved accesses: 0. No TRAIN/C/DEV/TEST photograph, mesh, mesh-derived cache, or historical experiment array entered this prerequisite run. All 16 TRAIN camera matrices were allowed. Landlock was installed before opening the GS; strace covers process startup and native IO. See access_audit.json for bootstrap directory/runtime-code exceptions and the raw strace location. The original GS training split is unverified; this is only a postprocessing access claim.

No independent annotators or reviewers were available. No target spans, challenge regions, or DEV labels were invented. G2 manual precision and G5 remain UNCERTIFIED. No local method result exists to review anonymously. The fixed 120-frame video and foundation glyph comparisons were not reached, so no substitute video or schematic output is supplied.

## Timing and completed implementation

Setup/input preparation: 10.056 s; native calibration: 44.764 s; scientific perturbation qualification: 11.995 s; local scientific probe: 0 s. Even charging all setup to science gives 22.051 s, below 1800 s. Software development/testing and the reused stock renderer build are separate from these run timers.

Implemented and observed RED→GREEN: protocol hashing, kernel input restrictions, full-K camera Jacobian, native stock projection/state replay, unfiltered SH3 asset loading, fixed interventions, numerical qualification, prerequisite verdict states, IO audit, deterministic sheets, end-to-end runner, and reporting. The additional native shuffle/rotation test is a regression check of existing behavior, not a fabricated RED. See TDD_LEDGER.md and tests/ for exact commands and evidence.

The Canny/image-profile/H_img, surface-sample audit, PCA/shifted/random/no-GS controls, geometric matching, and scientific G1–G5 implementations were deliberately not reached after the necessary validity prerequisite failed. They are not claimed complete or tested. No field, network, tracer, curve, selector, or chainer was built.

## Artifacts and permitted next action

[Qualification plot](qualification_metrics.png), [fixed white-background comparisons](fixed_white.png), [fixed black-background comparisons](fixed_black.png), [fixed calibration](fixed_calibration.png). contact_white_00–03.png and contact_black_00–03.png cover all 16 views; contact_calibration_00–03.png covers every calibration view. Per-view full-resolution sheets and immutable prerequisite JSON are in lego/. Native arrays, binary, and strace remain on the server; MANIFEST.json inventories their exact paths, sizes and SHA256 hashes. Reproduction: REPRODUCE.md.

**Next permitted action:** retain this invalid-intervention result and pause investment in B. Only complete the original execution prerequisites; any changed perturbation recipe, threshold, algorithm meaning or evidence needs a new preregistration. Do not reduce the split amplitude, loosen RGB limits, run Chair, train a UDF, or develop a curve extractor under this run.

## All recorded qualification pairs

| Intervention | View | Background | PSNR dB | SSIM | P99 | Qualified |
|---|---:|---|---:|---:|---:|---|
| clone | 1 | white | 40.727881 | 0.99479100 | 0.04401186 | False |
| clone | 1 | black | 41.573143 | 0.99484633 | 0.04052198 | False |
| clone | 7 | white | 40.129031 | 0.99584989 | 0.05166544 | False |
| clone | 7 | black | 40.257127 | 0.99591635 | 0.05094698 | False |
| clone | 14 | white | 41.364040 | 0.99605763 | 0.04243677 | False |
| clone | 14 | black | 41.529678 | 0.99609846 | 0.04093383 | False |
| clone | 21 | white | 40.173057 | 0.99422406 | 0.05444378 | False |
| clone | 21 | black | 40.002928 | 0.99420214 | 0.05493448 | False |
| clone | 27 | white | 41.449032 | 0.99621101 | 0.04130857 | False |
| clone | 27 | black | 41.827429 | 0.99607748 | 0.03919512 | False |
| clone | 33 | white | 39.531155 | 0.99157008 | 0.05874497 | False |
| clone | 33 | black | 39.274729 | 0.99169110 | 0.05933163 | False |
| clone | 41 | white | 41.070467 | 0.99445602 | 0.04271152 | False |
| clone | 41 | black | 41.614398 | 0.99445569 | 0.04103582 | False |
| clone | 47 | white | 40.631636 | 0.99604181 | 0.04719573 | False |
| clone | 47 | black | 40.586164 | 0.99613690 | 0.04695051 | False |
| clone | 53 | white | 38.341450 | 0.99458990 | 0.06074939 | False |
| clone | 53 | black | 39.553884 | 0.99412502 | 0.05044039 | False |
| clone | 59 | white | 38.831966 | 0.99523553 | 0.05926796 | False |
| clone | 59 | black | 39.144500 | 0.99541728 | 0.05716133 | False |
| clone | 67 | white | 41.208735 | 0.99535244 | 0.04248516 | False |
| clone | 67 | black | 41.588934 | 0.99536530 | 0.04081288 | False |
| clone | 73 | white | 39.654656 | 0.99380817 | 0.05673174 | False |
| clone | 73 | black | 39.531967 | 0.99404391 | 0.05757682 | False |
| clone | 79 | white | 40.701344 | 0.99628893 | 0.04629972 | False |
| clone | 79 | black | 40.954192 | 0.99629177 | 0.04383716 | False |
| clone | 86 | white | 39.467055 | 0.99193855 | 0.05917172 | False |
| clone | 86 | black | 39.235515 | 0.99201842 | 0.05946066 | False |
| clone | 93 | white | 40.691607 | 0.99563191 | 0.04758164 | False |
| clone | 93 | black | 40.734776 | 0.99562164 | 0.04724189 | False |
| clone | 99 | white | 39.281487 | 0.99437509 | 0.05771815 | False |
| clone | 99 | black | 39.322179 | 0.99458232 | 0.05699243 | False |
| split | 1 | white | 40.650317 | 0.99443734 | 0.04383959 | False |
| split | 1 | black | 41.422654 | 0.99444525 | 0.04067674 | False |
| split | 7 | white | 40.276208 | 0.99587932 | 0.05064731 | False |
| split | 7 | black | 40.389871 | 0.99587514 | 0.04996408 | False |
| split | 14 | white | 41.185509 | 0.99603537 | 0.04254332 | False |
| split | 14 | black | 41.352712 | 0.99599324 | 0.04114000 | False |
| split | 21 | white | 40.111913 | 0.99420336 | 0.05359069 | False |
| split | 21 | black | 39.974134 | 0.99419783 | 0.05390088 | False |
| split | 27 | white | 40.982595 | 0.99576624 | 0.04217816 | False |
| split | 27 | black | 41.328851 | 0.99558205 | 0.04006635 | False |
| split | 33 | white | 39.585924 | 0.99154664 | 0.05776485 | False |
| split | 33 | black | 39.363156 | 0.99168949 | 0.05772644 | False |
| split | 41 | white | 40.911422 | 0.99399354 | 0.04263414 | False |
| split | 41 | black | 41.383081 | 0.99392764 | 0.04095890 | False |
| split | 47 | white | 40.617662 | 0.99595573 | 0.04721848 | False |
| split | 47 | black | 40.497511 | 0.99601536 | 0.04812686 | False |
| split | 53 | white | 38.443859 | 0.99462067 | 0.05895338 | False |
| split | 53 | black | 39.612523 | 0.99414697 | 0.04986920 | False |
| split | 59 | white | 38.769365 | 0.99483543 | 0.05994581 | False |
| split | 59 | black | 39.056181 | 0.99509140 | 0.05733598 | False |
| split | 67 | white | 41.016841 | 0.99501521 | 0.04267830 | False |
| split | 67 | black | 41.369224 | 0.99496869 | 0.04107440 | False |
| split | 73 | white | 39.495469 | 0.99358519 | 0.05660892 | False |
| split | 73 | black | 39.405029 | 0.99384564 | 0.05714447 | False |
| split | 79 | white | 40.670823 | 0.99609043 | 0.04547216 | False |
| split | 79 | black | 40.897898 | 0.99608322 | 0.04375672 | False |
| split | 86 | white | 39.575502 | 0.99204698 | 0.05861530 | False |
| split | 86 | black | 39.373826 | 0.99212282 | 0.05882098 | False |
| split | 93 | white | 40.491032 | 0.99546241 | 0.04797903 | False |
| split | 93 | black | 40.565638 | 0.99544973 | 0.04753084 | False |
| split | 99 | white | 39.353116 | 0.99428549 | 0.05708566 | False |
| split | 99 | black | 39.403326 | 0.99449270 | 0.05604088 | False |

## Final verification and internal visual inspection

The final repository suite passed **61 tests**, including **16 foundation tests**; see `setup/full_suite_final.txt`. All reported RED failures precede their corresponding implementations. No tests were rewritten to accept measured scene output. The replay binary was rebuilt with measured timing and remained byte-identical to the one used in the run; see `setup/build_timing.json`. The existing stock CUDA build was reused (zero new stock build time).

Internal inspection covered all 16 TRAIN comparisons on both backgrounds through the eight complete contact pages, the fixed calibration views, and the measurement plot. Overall RGB appearance is similar; amplified errors span baseplate details, bucket, cabin and mechanical parts. This cannot certify RGB near-equivalence against the frozen numeric thresholds. The inspection is by the implementing assistant, not independent review. Details: `VISUAL_REVIEW.md`.

The 48 full-resolution per-view PNGs (20,382,070 bytes), 84 native NPZs (382,394,067 bytes), copied PLY (41,180,443 bytes), binary and strace are intentionally excluded from Git. Their exact absolute server paths and individual hashes/sizes are in `MANIFEST.json`. Sixteen aggregate/fixed diagnostic PNGs (10,509,037 bytes) are committed, including complete contacts for every measured view.
