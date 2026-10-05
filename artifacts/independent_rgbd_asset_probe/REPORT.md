# Independent RGB-D fixed asset probe — NO_GO

This is an **extra-input, new-real-scene** experiment, not a vanilla-3DGS-only solution or a rerun of the four synthetic scenes. Official [TUM RGB-D fr1/desk](https://cvg.cit.tum.de/data/datasets/rgbd-dataset/download) provides measured Kinect depth and mocap poses. The archive SHA256 and exact F/C associations are frozen in `INPUTS.json`. F RGB/poses alone trained a vanilla 3DGS model; measured **F** depth built world-space line assets; measured **C** depth was evaluation-only. Neither mesh nor the four-scene TEST entered the method.

## Outcome and visual evidence

**Operational NO_GO** under `PROTOCOL.md` (hash in `PROTOCOL.sha256`). The fixed 3D asset has 472 editable IDs; `ASSET.json`/`.npz` and `EDITED_ASSET.json`/`.npz` preserve ID/topology and an edit changes rasterization in 168 C views. Yet the complete visual result is fragmented blobs/short pieces: desk objects remain hard to recognize as line art. The median image `quantile_050_frame_0335.png`, low/high ink frames, all seven temporal quantiles, `OCCLUSION_OBSERVATION.png`, `EDIT_OBSERVATION.png`, and the complete 552-frame video `../../out/independent_rgbd_asset_probe/full_domain_comparison.mp4` show the actual output. GS RGB Canny is a weak *non-asset* reference, not the old I arm; per-frame Kinect depth2d is evaluation-only, not a fixed asset. No independent human preference review has been performed.

Frozen gates, as recorded verbatim in `EVALUATION.json`:
- F contour length surviving multi-view filtering: **8.56%** (required ≥50%): fail. This is the earliest severe information-loss stage; retained curves alone do not make coherent line art.
- C sensor support: **66.48%** (required ≥80%): fail.
- C known sensor-occluded samples falsely visible: **21.97%** (required ≤10%): fail.
- Other passes: 0 empty C frames, ≥10 curves, an edit manifests in multiple C views, and a *predicted* occlusion/reveal event exists. `REVEAL_VALIDATION.json` states the particular reported event was **not confirmed** as visible-hidden-visible by sensor depth; do not call it physical occlusion success.
- C median 3D-ink/reference-ink ratios: depth2d **9.43×**, GS-RGB Canny **1.05×**; the matched-ink prerequisite fails for the depth reference. Do **not** claim superior equal-ink stability.

## Engineering, provenance, and boundaries

The RGB-only model trained 7000 iterations and its sealed hash was calibrated on F (`MODEL_CALIBRATION.json`, passed). F/C split: 92/460 cameras. F depth-only asset reconstruction and bitwise rerun of its asset/cloud passed (`REPRODUCTION.json`). `FINAL_ACCESS_AUDIT.json` passed, with zero C-depth reads during build, read-only raw-role audit, asset JSON/NPZ parity, and no mesh/old TEST access; engineering tests have a separate `TDD_GREEN.log`. All 552 full-domain frames were encoded and decoded with matching SHA256 in `VIDEO.json`; the video and large model remain regenerable server-side, not falsely claimed to be stored by Git. Git carries code, protocol, asset JSON/NPZ, image evidence, manifests, and report.

Limits: TUM RGB-D sensor registration, missing depth, asynchronous timestamps, imperfect RGB-only GS rendering, and a much broader real-scene camera domain can affect the result. The NO_GO applies to this frozen extraction and scene, not to every method with independent 3D measurements. This run does **not** rescue the original frozen-vanilla 3DGS-only question, because Kinect geometry and mocap are additional inputs.
