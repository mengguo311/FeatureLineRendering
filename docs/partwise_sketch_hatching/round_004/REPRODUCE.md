# Round 004 reproduction and preserved execution failure

Worktree: `/home/u00134/3dgs_line/partwise_sketch_hatching_p0p1_v01`
Branch: `partwise-sketch-hatching-p0p1-v01`.

All scientific commands use this CPU prefix (no environment was printed):

```bash
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 \
taskset -c 0,1 \
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
```

Append each exact argument sequence below. The wrapper launches the same
interpreter via `taskset -c 0,1 timeout 600`, caps threads and hides CUDA.

```text
experiments/partwise_sketch_hatching/round004_receipt.py TESTS_RED experiments/partwise_sketch_hatching/test_stage_attribution.py --backend broken
experiments/partwise_sketch_hatching/round004_receipt.py TESTS_GREEN experiments/partwise_sketch_hatching/test_stage_attribution.py --backend new
experiments/partwise_sketch_hatching/round004_receipt.py TESTS_GREEN_FINAL experiments/partwise_sketch_hatching/test_stage_attribution.py --backend new
experiments/partwise_sketch_hatching/round004_receipt.py INHERITED_TESTS experiments/partwise_sketch_hatching/test_temporal_audit.py --backend new
experiments/partwise_sketch_hatching/round004_receipt.py PREPARE_EXECUTION experiments/partwise_sketch_hatching/run_round004.py prepare
experiments/partwise_sketch_hatching/round004_receipt.py EVALUATION_EXECUTION experiments/partwise_sketch_hatching/run_round004.py evaluate
experiments/partwise_sketch_hatching/round004_receipt.py VALIDATION_EXECUTION experiments/partwise_sketch_hatching/run_round004.py validate
experiments/partwise_sketch_hatching/round004_receipt.py CONFIRMATION_EXECUTION experiments/partwise_sketch_hatching/confirm_describe_round004.py
```

RED: return 1, four expected toy failures and three skips. GREEN and
GREEN_FINAL: return 0, seven passes. GREEN_FINAL followed the added independent
rounded-ray diagnostic; no toy assertion or lamp threshold changed. Inherited:
return 0, five passes. Prepare/evaluate/confirmation: return 0.

The validation outer exec session **94299 returned 143**. Its child completed
the saved validation and final JSON log, but its exit status is **UNKNOWN**.
There is intentionally no original `VALIDATION_EXECUTION.json` success receipt.
`SESSION_FAILURE.json`, `VALIDATION.json`, the complete runtime log, and the
separate successful confirmation preserve this distinction. The source was
not changed or rerun to erase the failure.

The preparation shell also contained an unused misspelled empty variable
`CUDA_VISIBLE_DEVICESSES=''`; the correct `CUDA_VISIBLE_DEVICES=''` and the
program's own resource controls were present. Initial shell setup used
unavailable `python` (return 127), then succeeded with system `python3` for JSON
only. Initial `git add` was rejected by sparse checkout; explicit `--sparse`
staged only the authorized new files. Neither event performed science or
changed an evaluation result.

Source/protocol and asset locks were committed before stage evaluation.
Recovery source/data locks were committed before confirmation. All originals
remain frozen. Do not rerun these commands over this sealed science directory;
a replay needs separate authorized output paths and a new bound source lock.

Seal and verification, with the same prefix:

```text
experiments/partwise_sketch_hatching/seal_round004.py
experiments/partwise_sketch_hatching/seal_round004.py --verify
```

The seal excludes runtime stdout/stderr; actual receipts and recovery hashes
bind the corresponding logs. Science status remains matched-control NO_GO
because eight of 61 cases have no permitted control. Existing 53 control slots
are all supported; they represent 25 unique sample/frame combinations.
