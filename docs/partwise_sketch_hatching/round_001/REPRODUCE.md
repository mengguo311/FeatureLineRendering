# Round 001 reproduction

This is a CPU-only procedural GT diagnostic, not a RaDe-GS reconstruction.
All commands run from the authorized worktree on branch
`partwise-sketch-hatching-p0p1-v01`. Do not rerun `prepare` or `run` over the
sealed round: replay into a separately authorized output directory after
freezing that replay's path/config. The current runner intentionally refuses
to overwrite a completed `metrics.json`.

Protocol commit: `da8c8387`. Implementation commit: `cf805102`.
Pre-evaluation source/mesh lock commit: `ee654a05`.
Exact file identities are in `ASSET_LOCK.json`; the final manifest binds
outputs and documentation separately.

Python:
`/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python`

Algorithm tests:

```bash
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 \
taskset -c 0,1 \
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python \
experiments/partwise_sketch_hatching/test_p0.py
```

The same test source was run against deliberately unimplemented functions
(RED: 9 errors, exit 1), then the implementation (GREEN: 9 passes, exit 0).
The source hash of the test did not change. These are actual unittest runs,
not synthetic failure scores.

The original scientific execution command is in `round_001/EXECUTION_INITIAL.json`.
It uses `timeout 600`, two-core affinity, and the locked source/config/mesh.
The runner sets CUDA visibility to empty before importing numeric packages;
it never imports torch or invokes a GPU backend.

The frozen original runner retains a known final JSON serialization error
(`numpy.bool_`), encountered after all renders and full video decoding.
The failure and complete partial records were preserved. Amendment commit
`cab754db` freezes `recover_summary.py`, which verifies identities and
completeness, then writes the same predicates using native Python booleans.
Its exact successful command and return code are in `EXECUTION_RECOVERY.json`.
`EXECUTION.json` links both receipts. This was a data-only summary recovery,
not a second rendering run or a change in evaluation thresholds.

The shared environment was not changed. A 29.5 MB public wheel,
`imageio-ffmpeg==0.6.0`, was installed with `pip --no-deps --target
.runtime_p0`. Its Python distribution declares BSD-2-Clause; the bundled
FFmpeg 7.0.2 binary reports GPL-3.0-or-later through `-L`. No binary is committed to git.
The exact binary SHA-256 is recorded with each video. A total of zero
dataset/model bytes was downloaded.

Useful artifacts:

- `assets/lamp_mesh.npz`: original procedural mesh with GT face part IDs.
- `strokes/*.npz`: stable IDs, face indices, barycentric paths and ink values.
- `references/analytic_*.npz`: independently ray-intersected continuous
  lathe depth and part masks, never used to generate the triangulated paths.
- `stills/`: all frozen views for all three styles and single-part edits.
- `frames/`, `videos/`, `camera_trajectories.json`: genuine per-camera 3D
  rendering and full MP4 decode records.
- `metrics.json`: raw per-view metrics, timings, gate results and limitations.
- `runtime/`: execution stdout/stderr, outside the sealed scientific file list.

The lock binds the analytic fixture recipe, triangulated asset and code.
It does not imply independence of the object's authored geometry from its
analytic reference. That reference can diagnose discretization and
implementation, not real reconstruction accuracy.
