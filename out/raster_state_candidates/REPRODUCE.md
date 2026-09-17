# Reproduction and artifact boundaries

Branch `raster-state-candidates`, base `e0293bd`. The manifest is immutable.
Use a separate checkout with the code, PREREG and MANIFEST but without generated
scene results. Do not delete or overwrite this run. Inputs are the absolute paths
and SHA256s in `MANIFEST.json`; the existing pinned stock-renderer ABI adapter is
under `out/vrss/vendor/official_site` (ignored build artifact; see VRSS build records).
No external repository is changed by these commands.

Environment used: `/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python`, Torch 2.3.1
CUDA 12.1, A6000. Prefix each bounded run with `CUDA_VISIBLE_DEVICES=1
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4`. The scripts refuse another branch,
changed input hashes, noncanonical TRAIN indices, forbidden geometry/caches,
and existing stage access logs. NPZ/video files stay on the server; JSONs record
the scientific parameters, per-view observations, source IDs and checksums.

Sequential stages (all use `scripts/run_raster_candidates.py`):

1. `smoke` (timeout 120 s): small GPU render, original IDs, repeat, official RGB.
2. `baseline` (timeout 900 s): fresh clean M1a initialization.
3. `step1` (timeout 900 s): all 16 TRAIN channel/state panels and arrays.
4. `step2` (timeout 900 s): real and shifted ID-weighted anchors.
5. `step3` (timeout 900 s): full real clusters and matched null comparisons.
6. `step4_smoke` (timeout 120 s): 640 initial linelets, 2 TRAIN views, 5 steps.
7. `step4` (timeout 900 s): every arm, 100-step pull, prune, chaining.
8. Commit manifest/code/`lego/step4.json` (path checksums) before opening DEV.
9. `render_outputs` (timeout 900 s): all 120 frames, native and both ink matches.
10. `scripts/audit_raster_candidates.py` (timeout 120 s): TRAIN-only region/source
    diagnostics, count-matched cluster visual control; no candidate changes.

After primary NO-GO, run only `smoke`, `step1`, `step2`, `step3`, each with
`--scene chair --cheap`. This is a four-TRAIN-view transfer diagnostic with initial
linelet generation, not a complete chair NPR confirmation. No chair DEV/TEST run.

Tests: `python -m unittest discover -s tests -p 'test_*.py'`.

Important limits: raster-state/depth use the declared circular-disc proxy, not
stock anisotropic internal fragments. SH0 is RGB, not intrinsic albedo. Gaussian
covariance axes are not extra 2DGS normals. This run audits its own TRAIN-only
reads; it does not independently establish the original pretrained GS data split.
