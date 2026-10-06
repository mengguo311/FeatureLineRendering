# Reproduce

Run from this branch/worktree with the existing verified dependencies and Python:

```bash
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B experiments/gaer_rgb_union_voting_v01/tests/test_contract.py
PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B experiments/gaer_rgb_union_voting_v01/tests/test_native.py
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B experiments/gaer_rgb_union_voting_v01/run.py --scene both
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B experiments/gaer_rgb_union_voting_v01/curate.py
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B experiments/gaer_rgb_union_voting_v01/verify.py
```

No installation or build is required. `binding.py` loads the verified attribution binary from `/home/u00134/3dgs_line/gaer_attribution_buffer_v01/out/gaer_attribution_buffer_v01`, the stock binary from the old native foundation, and read-only fullSH3 APIs. Exact float32 source fields/RGB come from `/home/u00134/3dgs_line/image_space_edge_foundation_v1/out/image_space_edge_foundation_v1/{dev_fields,fixed_fields,raw}`. Absolute models/cameras, source field hashes, archival RGBA and metadata hashes are in PRODUCTION_FREEZE.json. These existing datasets/models/binaries are required; no portable model is included.

The runner freezes protocol + every method source hash BEFORE the first production vote. It independently handles both scenes and logs a scene failure without suppressing the other scene. `--scene lego` / `--scene chair` resume separately. Each sealed unit checks config and every output byte before skipping; original arrays accumulate in Python from the eight saved per-view counters. All final files use atomic replacement, and seal completion is atomic. An interrupted unsealed unit can be recomputed under the same freeze; a changed sealed input/method/output is rejected and retained as evidence. Production source must not be edited after freezing.

For a fresh rerun, preserve the existing artifacts and run in a new isolated worktree with the three stage paths absent except TASK/launch. All other dependencies remain read-only. The runner only writes experiments/gaer_rgb_union_voting_v01, artifacts/gaer_rgb_union_voting_v01 and ignored out/gaer_rgb_union_voting_v01. Resource checks fail on foreign GPU0 PIDs and fixed storage reserves/cap; no foreign process termination.

Downloads contain all original-N votes, rankings and fixed set IDs plus native 800x800 per-pixel winners/fallback/source fields. Raw K8 contributor buffers and full-T contribution maps remain in ignored out with seals, not model files. Media include native resolution selected-only originals, contribution diagnostics, two reserved views, mandatory center baseline and visibility-matched random controls. No videos are needed for this stage. SOURCE_MAP and MEDIA_MANIFEST contain SHA256 provenance; verify.py performs independent dictionary scalar checks and decodes exported media.

To reproduce the final readable presentation after the frozen runner, use:

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B artifacts/gaer_rgb_union_voting_v01/CURATE_MEDIA.py
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B experiments/gaer_rgb_union_voting_v01/verify.py
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B artifacts/gaer_rgb_union_voting_v01/FINALIZE.py
```

`FINALIZE.py` requires the saved initial PRODUCTION_RUNNER_RECEIPT.json and tests/RESUME.json from this completed run. These keep initial and resume wall times separate. CURATE_MEDIA adds display-only unit-gain frequency features and nearest-neighbor native ROIs; it never changes frozen winners, rankings, sets or evaluation. Original sealed production media remain intact. Source hashes of both postproduction scripts are recorded separately.
