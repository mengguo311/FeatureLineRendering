# Round 002 reproduction

This is one bounded repair of the frozen procedural GT lamp walker. It is
not a new reconstruction experiment, a new scientific method comparison, or
an independent temporal stability evaluation. Original round 001 code and
sealed outputs remain unchanged.

All commands are run from
`/home/u00134/3dgs_line/partwise_sketch_hatching_p0p1_v01`, on
`partwise-sketch-hatching-p0p1-v01`, with CPU affinity `[0,1]`, CUDA hidden,
and OMP/BLAS threads capped at two. No torch or GPU backend is invoked.

Freeze history:

- `f8827fd5`: amendment and regression source, before RED and implementation.
- `b6eb26fb`: repaired implementation, replay runner, original-test adapter,
  progress/coverage audit and sealer, after real RED/GREEN algorithm tests.
- `c9f748b2`: source/config/mesh asset lock, before any lamp replay.
- `216ad365`: data-only validation amendment after the terminal print failure.
- `cd80a313`: validation source and completed evidence-byte lock.

Exact test invocations:

```bash
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 \
taskset -c 0,1 timeout 120 \
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python \
experiments/partwise_sketch_hatching/test_walk_progress.py --backend old

CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 \
taskset -c 0,1 timeout 120 \
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python \
experiments/partwise_sketch_hatching/test_walk_progress.py --backend new

CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 \
taskset -c 0,1 timeout 120 \
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python \
experiments/partwise_sketch_hatching/test_original_with_v2.py
```

These commands are equivalent to the receipts' subprocess argv: the receipt
wrapper set those same known environment variables and affinity before
launch. No environment was printed. RED: 4 tests, 2 failures, return 1;
GREEN: the same 4 tests, all pass, return 0. The adapter executes the
unchanged original nine tests against `core_walk_v2`, all pass, return 0.
The field-sign regression only compensates a global field sign with the
seed integration sign; it is not evidence for arbitrary face-local sign flips.

Actual replay:

```bash
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 \
taskset -c 0,1 timeout 600 \
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python \
experiments/partwise_sketch_hatching/run_round002.py run
```

The receipt is `round_002/EXECUTION.json`; stdout/stderr is
`round_002/runtime/replay.log`, outside the science seal. `prepare` copied
the prior asset bytes and wrote a new lock; that lock was committed before
`run`. Never repeat `prepare` or `run` over a completed round. A further
replay requires a separately authorized directory and its own frozen lock.
The runner refuses to overwrite final metrics.

Actual replay return code is **1**, after 204.764 seconds: the final
terminal `json.dumps` in unchanged `run_p0.py:223` still rejected a NumPy
boolean. The file writer had already saved complete `metrics.json`, all
100 timings, trajectories and three full video-decode records. The
original return code and failed status are retained in `EXECUTION.json`
and `FAILURE_PRINT.json`. No render or metric file was rewritten.

The committed data-only validation checks source/evidence hashes,
recomputes the unchanged predicates, verifies all 84 PNGs, and fully
re-decodes all three MP4s, matching every original decoded-frame hash:

```bash
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 \
taskset -c 0,1 timeout 120 \
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python \
experiments/partwise_sketch_hatching/validate_round002_outputs.py
```

Validation returned **0** in 2.261 seconds; see `VALIDATION.json` and
`VALIDATION_EXECUTION.json`. Do not rerun it over completed validation.

Audit and seals:

```bash
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 \
taskset -c 0,1 timeout 120 \
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python \
experiments/partwise_sketch_hatching/audit_round002.py

taskset -c 0,1 \
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python \
experiments/partwise_sketch_hatching/seal_round.py --verify

taskset -c 0,1 \
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python \
experiments/partwise_sketch_hatching/seal_round002_validated.py --verify
```

`core_walk_v2.py` imports unchanged geometry/renderer/metric functions from
`core.py`; only walking and the generator's choice of walker are versioned.
Sampling, seed/layer IDs, counts, requested lengths, field rules, ink,
renderer and masks remain fixed. The runner reuses `run_p0.evaluate` with
the new module and output directory. Its JSON writer converts NumPy
scalars to Python scalars for saved files; the separate terminal print
failure is retained as described above. Runtime traces record both half-path termination
causes and realized arc lengths.

`REPAIR_AUDIT.json` compares every saved stroke with the sealed original,
checks identical seed anchors and IDs, and reports exact edge-coordinate
continuity, ownership, attachment, cycle counts, realized lengths and
termination reasons. Image ink/support differences are descriptive and
include all four frozen views for all three styles. They do not establish
visual superiority. The same `.runtime_p0` FFmpeg dependency is reused
without installations or downloads.
