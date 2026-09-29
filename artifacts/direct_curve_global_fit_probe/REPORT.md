# Direct fixed-3D-curve D/I/L probe: NO_GO

All four preregistered scenes, three arms, three starts, full/LOO fits and independent reruns were completed. The scope is the frozen 128-span, 300-step configuration and the declared F/C/interpolation domain. Mesh was not used; TEST/DEV imagery was not opened.

| Scene | Arm | C interior | C outline | C coverage | Unsupported | Evaluable precision | Beyond 4px |
|---|---|---:|---:|---:|---:|---:|---:|
| lego | D | 0.72% | 12.25% | 2.65% | 75.08% | 30.12% | 32.47% |
| lego | I | 2.53% | 10.84% | 3.92% | 70.81% | 37.02% | 20.44% |
| lego | L | 0.10% | 0.47% | 0.16% | 98.37% | 1.71% | 66.73% |
| chair | D | 1.34% | 17.30% | 4.43% | 76.70% | 29.01% | 32.20% |
| chair | I | 8.86% | 14.85% | 10.02% | 61.08% | 52.20% | 17.38% |
| chair | L | 0.48% | 0.99% | 0.58% | 96.11% | 4.56% | 48.99% |
| drums | D | 2.31% | 14.54% | 8.87% | 73.97% | 34.51% | 12.42% |
| drums | I | 4.24% | 10.57% | 7.63% | 69.54% | 42.73% | 12.81% |
| drums | L | 0.37% | 0.81% | 0.60% | 95.81% | 5.67% | 16.81% |
| ficus | D | 0.65% | 2.33% | 2.07% | 88.09% | 18.56% | 14.62% |
| ficus | I | 2.19% | 1.90% | 1.94% | 81.25% | 26.82% | 15.29% |
| ficus | L | 0.21% | 0.30% | 0.28% | 97.95% | 2.67% | 45.75% |

| Scene | Precision | Retain D | Extra RGB | Global coupling | Unambiguous | Budget | Decision |
|---|---|---|---|---|---|---|---|
| lego | FAIL | FAIL | FAIL | PASS | FAIL | PASS | NO_GO |
| chair | FAIL | FAIL | FAIL | PASS | FAIL | PASS | NO_GO |
| drums | FAIL | FAIL | FAIL | PASS | FAIL | PASS | NO_GO |
| ficus | FAIL | FAIL | FAIL | PASS | FAIL | PASS | NO_GO |

| Scene | I−D interior gain (percentage points) | Improved nonempty interior cells | I−L C coverage (percentage points) | Largest eligible I ambiguity disagreement |
|---|---:|---:|---:|---:|
| lego | 1.81 | 44.49% | 3.76 | 47.29% |
| chair | 7.51 | 68.57% | 9.44 | 62.10% |
| drums | 1.92 | 29.06% | 7.03 | 50.31% |
| ficus | 1.54 | 12.90% | 1.65 | 100.00% |

Numerical failures can deny continuation without independent visual approval. Internal implementing-model inspection is not independent validation; no independent visual GO is claimed. Counts retain all 64 cells per F/C view (512 per split/scene/arm), including empty cells. Unknown visibility earns no support. C is held out from curve fitting but belongs to frozen GS TRAIN. Arc imagery is renderer-domain evidence, not unseen real photographs.

## Internal visual review

### lego

A = D, B = depth2d, C = I, D = L. Initial observations and reviewed file hashes are preserved in BLINDED_REVIEW_* records; REVIEW_METHOD.md describes the review limits.

- I (panel C) retains some board, bucket and cabin fragments, but misses much of the coherent vehicle structure and its fine interior features. Nearby parallel board strokes and long contour gaps remain. The 2D depth reference (B) is more legible as a complete vehicle, despite missing studs, track detail and some internal boundaries.
- Across both complete arcs, I fragments broadly follow the camera but remain incomplete and show local gap/visibility changes. The reference retains a more connected base, bucket and cabin, with changing internal lift/track contours.
- D (A) is also sparse; L (D) collapses visually to small point-like marks. Beating L numerically therefore does not establish an adequate global reconstruction.
- I/depth2D mean ink ratio is 0.259383 over all 66 frames, outside the frozen [0.8,1.25] range. Fewer temporal defects at comparable ink is not established; this is a failed continuation requirement, not a claim of universally greater perceptual flicker.

### chair

A = D, B = depth2d, C = I, D = L. Initial observations and reviewed file hashes are preserved in BLINDED_REVIEW_* records; REVIEW_METHOD.md describes the review limits.

- I (C) leaves major gaps in the back, arms, seat and legs, and does not recover coherent upholstery or decorative interior structure. Nearby parallel rim fragments occur. The 2D depth reference (B) retains the recognizable chair, although its seat/back interior can be noisy or merged.
- Across both complete arcs, I has persistent missing contours and some changing local fragments. The reference keeps the connected outer chair while internal back/arm lines can open or disappear. Lower apparent motion in sparse ink does not rescue the missing structure.
- D (A) also leaves extensive gaps; L (D) is predominantly point-like.
- I/depth2D mean ink ratio is 0.369902 over all 66 frames, outside the frozen [0.8,1.25] range. Fewer temporal defects at comparable ink is not established; this is a failed continuation requirement, not a claim of universally greater perceptual flicker.

### drums

A = D, B = depth2d, C = I, D = L. Initial observations and reviewed file hashes are preserved in BLINDED_REVIEW_* records; REVIEW_METHOD.md describes the review limits.

- I (C) recovers useful local drumhead curves, including the central loop in several F/C views and the first arc. The 2D depth reference (B) merges some central drums and loses those separate interior boundaries.
- Whole-frame kit legibility remains worse for I: many cymbal, body and support contours are disconnected or missing. The reference retains substantially more connected cymbal, stool, stand and outer body structure.
- Both complete arcs show changing local gaps and boundary mergers. I preserves some useful head curves but also persistent missing structure; its mean shared motion disagreement exceeds the reference in this domain. D (A) often has longer cymbal/tripod fragments; L (D) remains point-like.
- I/depth2D mean ink ratio is 0.224195 over all 66 frames, outside the frozen [0.8,1.25] range. Fewer temporal defects at comparable ink is not established; this is a failed continuation requirement, not a claim of universally greater perceptual flicker.

### ficus

A = D, B = depth2d, C = I, D = L. Initial observations and reviewed file hashes are preserved in BLINDED_REVIEW_* records; REVIEW_METHOD.md describes the review limits.

- I (C) recovers a useful pot-base ellipse or circle in underside views and both arcs. This feature is not separately drawn by the 2D depth reference (B), which mostly retains the outer pot silhouette.
- I nonetheless omits most foliage, many trunk segments and much of the pot contour. The reference preserves the recognizable whole plant and many leaf boundaries, although leaves merge and their local contours change. Pot ribbing remains absent.
- The pot-base curve persists through both complete arcs with local gaps and adjacent fragments; the underside second arc visibly rotates in the image. I has higher shared motion disagreement than the reference. D (A) has longer partial trunks and scattered canopy curves; L (D) is point-like.
- I/depth2D mean ink ratio is 0.087194 over all 66 frames, outside the frozen [0.8,1.25] range. Fewer temporal defects at comparable ink is not established; this is a failed continuation requirement, not a claim of universally greater perceptual flicker.

| Scene | Method | Mean arc ink | Shared popping components / transitions | Mean motion disagreement | ID pops / ID transitions |
|---|---|---:|---:|---:|---:|
| lego | D | 2482.6 | 588 / 64 | 0.0373 | 95 / 8192 |
| lego | I | 3023.9 | 489 / 64 | 0.0329 | 142 / 8192 |
| lego | L | 234.3 | 3027 / 64 | 0.4192 | 16 / 8192 |
| lego | depth2d | 11658.0 | 2022 / 64 | 0.0633 | not applicable |
| chair | D | 1513.7 | 1494 / 64 | 0.1055 | 82 / 8192 |
| chair | I | 2048.2 | 330 / 64 | 0.0162 | 87 / 8192 |
| chair | L | 169.8 | 2342 / 64 | 0.4191 | 48 / 8192 |
| chair | depth2d | 5537.2 | 540 / 64 | 0.0239 | not applicable |
| drums | D | 5921.8 | 1032 / 64 | 0.0189 | 81 / 8192 |
| drums | I | 4322.7 | 1082 / 64 | 0.0333 | 118 / 8192 |
| drums | L | 269.2 | 1026 / 64 | 0.1027 | 73 / 8192 |
| drums | depth2d | 19280.9 | 1804 / 64 | 0.0181 | not applicable |
| ficus | D | 1581.7 | 990 / 64 | 0.0500 | 174 / 8192 |
| ficus | I | 1282.1 | 868 / 64 | 0.0643 | 171 / 8192 |
| ficus | L | 183.5 | 1967 / 64 | 0.3306 | 81 / 8192 |
| ficus | depth2d | 14704.2 | 642 / 64 | 0.0070 | not applicable |

| Scene | I/depth2D arc ink ratio | Comparable ink |
|---|---:|---|
| lego | 0.2594 | no |
| chair | 0.3699 | no |
| drums | 0.2242 | no |
| ficus | 0.0872 | no |

Mean arc ink includes all 66 frames per scene; motion proxies use the 64 within-arc transitions. Persistent-ID popping has no direct 2D-depth analogue. Shared motion disagreement advects previous ink with frozen GS median depth and inherits its errors; component counts are proxies, not human defect rates. All framewise doubling, detachment, visibility and census data are retained, with aggregate lengths/counts and denominators in SUMMARY_RESUME.json.

## Engineering evidence

The original CPU replay failed Lego arc0_005 because CUDA fused quadratic arithmetic crossed the native alpha cutoff. The replacement independently accumulates RGB/transmittance and contribution-depth quantiles on CUDA using the stock expression. It receives no stock final_T or stock RGB. The literal 1/255 calibration gate, scientific thresholds, objective, capacity, optimizer and camera domain are unchanged. All 82 preregistered views/frames per scene were explicitly calibrated in both runs before resumed evaluation. Detailed arithmetic, regressions, hashes and the preserved failed summary attempt are documented in REPLAY_REPAIR.md.

The traced suite completed 226 tests: 225 passed and one expected nested-strace test was skipped. Its access audit found zero forbidden successful opens and no unparsed calls. The cutoff regression has observed RED/GREEN evidence, and the independent synthetic oracle invokes unchanged upstream FORWARD::render. Scheduler tests cover failure independence, exclusive atomic seals and preserved-fit hash checks. Final verification checks unchanged Lego fit/proposal/native arrays, both optimization runs, fixed world geometry on all 82 frames, all media decoding, native calibration, source provenance, preserved attempts and scene budgets.

Proof: out/direct_curve_global_fit_probe/scheduler/resume_20260929_v2/verification_v2/VERIFICATION.json; COMPARISON.json; GEOMETRY.json; MEDIA.json; ACCESS.json; BUDGETS.json. Exact scene-stage commands, access traces, immutable stage seals, process records and resource samples are under out/direct_curve_global_fit_probe/scheduler/resume_20260929_v2/.

The original sequential launchers were preserved and replaced with a scene-stage scheduler. All missing scene fits run before evaluations; a scene evaluation failure cannot prevent other fitting. Evaluation reruns archive old directories and hash inventories. No existing fit or output is overwritten, and no sealed Lego asset is refitted. An atomic completion seal is published only after a successful stage and access audit.

| Scene | Conservatively charged GPU-hours | Ceiling |
|---|---:|---:|
| chair | 6.756 | 12 |
| drums | 4.313 | 12 |
| ficus | 3.451 | 12 |
| lego | 7.996 | 12 |

| Scene | Observed CPU seconds | Peak worker GPU MiB | Peak worker host HWM MiB |
|---|---:|---:|---:|
| lego | 6023.6 | 852 | 3063.5 |
| chair | 11518.1 | 11586 | 3008.2 |
| drums | 15815.2 | 7308 | 3047.7 |
| ficus | 12729.3 | 6178 | 3059.8 |

The conservative charge includes both runs, historical excluded/interrupted attempts, native preparation and evaluation; interrupted fits receive an additional full 30-minute allowance. CPU wall time is charged while holding a GPU; this is not a kernel profiler. Per-fit 300-step/30-minute allocations remain fixed. GPU process memory, CPU time and process VmHWM are sampled every 15 seconds after the resume monitor starts; these are observed peaks, not complete lifetime GPU peaks. Existing shared GPU jobs were checked before every stage.

## Artifacts and limitations

Full-resolution F/C panels, complete ordered arc frames, playable videos, quartile sheets, all-frame contacts, metrics, census and alternative-asset ambiguity drawings are under out/direct_curve_global_fit_probe/{run,rerun}/SCENE/evaluate/. Curated selected control points and active stable IDs are in curves/. FIGURES.md links the original outputs. Frozen protocol and input hashes are unchanged.

The domain has two nearby 33-frame arcs per scene; this does not establish arbitrary-view reconstruction. Drums/Ficus retain inherited GS posterior qualification limitations. The binary image detector is uncalibrated. Fitted curves use finite proposals, fixed capacity and local optimization. Visibility uses frozen GS depth and inherits its errors. Temporal defect proxies are not human defect rates. Comparability requires the frozen [0.8,1.25] ink ratio; no framewise ink deletion or post-hoc tuning was performed. Conclusions apply only to this preregistered bounded experiment.

Final engineering verification passed 570 checks. Exhaustive replay calibration covered 656 scene/run/view combinations; maximum RGB, alpha and wrapper errors were {'rgb_max': 0.0, 'alpha_max': 0.0, 'wrapper_max': 0.0}. CALIBRATION_SUMMARY.json retains per-frame legacy differences and exact source hashes.

The first administrative delivery verification attempt and its audit-filename correction are preserved in DELIVERY_VERIFICATION_ATTEMPTS.md. No scientific output was altered to satisfy verification.

[Complete comparison gallery](index.html) · [Portable proof](proof/VERIFICATION.json) · [Review method](REVIEW_METHOD.md)

