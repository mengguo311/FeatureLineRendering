# Round 003 reproduction and failure preservation

Working directory: `/home/u00134/3dgs_line/partwise_sketch_hatching_p0p1_v01`.
Branch: `partwise-sketch-hatching-p0p1-v01`.

All scientific commands used this prefix (no environment was printed):

```bash
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 \
taskset -c 0,1 \
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
```

The regression commands, each bounded by `timeout 120`, were:

```text
experiments/partwise_sketch_hatching/test_temporal_audit.py --backend broken
experiments/partwise_sketch_hatching/test_temporal_audit.py --backend new
```

Actual results: broken 3 failures + 2 skips, return 1; new 5 passes, return 0.
The broken backend is a deliberately faulty toy metric, not the original
renderer. Both receipts bind the same test SHA.

The remaining commands appended these exact arguments to the prefix above:

```text
experiments/partwise_sketch_hatching/round003_receipt.py PREPARE_EXECUTION experiments/partwise_sketch_hatching/run_round003.py prepare
experiments/partwise_sketch_hatching/round003_receipt.py ORBIT_EXECUTION experiments/partwise_sketch_hatching/run_round003.py orbit
experiments/partwise_sketch_hatching/round003_receipt.py ZOOM_EXECUTION experiments/partwise_sketch_hatching/run_round003.py zoom
experiments/partwise_sketch_hatching/round003_receipt.py SUMMARY_EXECUTION experiments/partwise_sketch_hatching/run_round003.py summarize
experiments/partwise_sketch_hatching/round003_receipt.py VALIDATION_EXECUTION experiments/partwise_sketch_hatching/validate_round003.py
experiments/partwise_sketch_hatching/round003_receipt.py CONFIRMATION_EXECUTION experiments/partwise_sketch_hatching/confirm_round003.py
experiments/partwise_sketch_hatching/round003_receipt.py FAILURE_EXPORT_EXECUTION experiments/partwise_sketch_hatching/export_round003_failures.py
```

The receipt wrapper launches the same interpreter under `taskset -c 0,1
timeout 600`, captures stdout/stderr under `round_003/runtime/`, and records
actual argv, return code, wall time and log SHA. Prepare/orbit/summary/
confirmation/failure-export returned 0. The zoom outer tool session
returned 143 while its child subsequently completed all data; **child exit
code is unknown**, and no `ZOOM_EXECUTION.json` was invented. Validation
returned 1 only at its final terminal print after writing complete results;
the original source, traceback, complete files and return code remain.

Do not rerun these commands over this completed science directory. A future
replay requires separately authorized output paths, preserved inputs and a
new frozen lock. The source/protocol freeze precedes lamp evaluation; the
validation and recovery locks precede their corresponding data-only runs.
No scientific gate or exclusion changed after outcomes were opened.

Seal and verify commands use the same CPU prefix:

```text
experiments/partwise_sketch_hatching/seal_round003_recovered.py
experiments/partwise_sketch_hatching/seal_round003_recovered.py --verify
```

The prior round's verification command was:

```text
experiments/partwise_sketch_hatching/seal_round002_validated.py --verify
```

It verified all 164 prior manifest entries. New figures use English labels;
the result/limitation report is `REPORT_ZH.md`. No new video was encoded:
this audit exactly reused the 60 input views of the previously fully decoded
orbit/zoom videos, and newly saved all 60 actual raster/provenance outputs.
