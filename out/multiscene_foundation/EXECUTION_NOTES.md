# Execution notes and limits

No mathematical threshold, scene, seed, training hyperparameter, parent, dose,
query or image split changed after preregistration. The Phase-0 protocol already
documented the changes from the previous run: four scenes, real independent
training, separate posterior eligibility, a renderer-aware fixed perturbation
ladder, and seed 1729 as every scene's predetermined parent. It did not reuse a
previous invalid clone/split amplitude or select a new amplitude after rendering.

Two packaging repairs occurred. The isolated simple-knn build required preincluded
standard headers; its tracked source was unchanged. The first eight launches then
failed in CUDA initialization before Scene construction, initialization-point
creation or optimization. Their logs are preserved. A RED test reproduced this
failure, and a GREEN test verified CUDA initialization before Landlock followed by
denial of an unstaged image read. Official safe_state resets Python, NumPy and Torch
RNG afterward. Each scene/seed subsequently ran once for 30,000 iterations; there
was no retraining after quality failure.

The frozen 400px camera retained the prior protocol's principal point 200. The
official centered raster projection places it at 199.5 for a 400px pixel grid.
This half-pixel mismatch was discovered after eligibility failures. A separate
single-view comparison with the upstream renderer also exposed strong resolution
dependence: training at 800px and directly rendering at 400px is not equivalent to
rendering at 800px and area-resizing the image. Stock/native numerical calibration
at an identical camera passed; that calibration does not certify an appropriate
photographic sampling convention. The original results remain unchanged.

The all-eight diagnostic was explicitly scoped and committed in
POSTHOC_DIAGNOSTIC_PLAN.md before those extra renders. It evaluates the same frozen
TRAIN/validation views on both backgrounds at native800 and area-resized400.
It is post-hoc, descriptive and nonconfirmatory. It neither replaces the registered
400px gate nor establishes that another resolution would pass every prerequisite.
White-trained GS may also have background-dependent opacity error, and Drums has
substantial reconstruction error even in the diagnostic. A new protocol should
resolve camera/pixel/resolution conventions before any new outcome inspection;
this run does not perform or authorize an adaptive rescue.

The original TRAIN DEV/TEST-index files were byte-hashed for Phase-0 provenance.
They were not decoded or used for training/qualification/fitting/visual review.
The original dataset's separate test photographs were not opened. TRAIN source
photos and the 16 validation photos were the only image inputs to active stages.
The native file-open audit includes interpreter startup before confinement and
records explicit source-directory/cache exceptions. A stale timestamp bytecode
cache was rejected by Python, with a source-file fallback observed in the trace;
the audit discloses that fact rather than claiming bytecode/source equality.

The implementing assistant authored four coarse target candidates and twelve
challenge rectangles per scene from fixed TRAIN contacts, before local outputs.
These are not the required independently verified cross-view spans. No independent
annotator or blind reviewer was available. G2 manual and G5 are UNCERTIFIED; no DEV
annotation was made. These missing certifications are separate from the earlier
posterior-quality validity stop.

Only the synthetic-tested local core was implemented: full-K geometry, fixed edge
tangents and query hashing, whole-box multimodal search, local image Hessian and
axial direction, native contribution layers, shifted maps and bidirectional
matching. No scene local inference, old-PCA/no-GS/random-axis control comparison,
surface-sample diagnosis, deterministic glyph output or video was reached. Their
end-to-end orchestration is not claimed complete. Existing repository tests for
older stroke modules were run as regression tests only; those methods were not
used in this experiment. No mesh, full UDF, curve, connected linelet, Bezier,
final stroke or selector tuning entered this round.

All scientific labels follow PREREG. A controlled dose's RGB/coverage pass is a
property of that intervention at the registered renderer/cameras. It does not
override parent reconstruction quality or constitute a local invariance pass.
The validity stop therefore says nothing affirmative or negative about foundation
hypothesis B. No failed scene is rescued by a macro mean.
