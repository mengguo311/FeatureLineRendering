# Round007 reproduction and actual execution

Authorized branch: `partwise-sketch-hatching-p0p1-v01` in `/home/u00134/3dgs_line/partwise_sketch_hatching_p0p1_v01`.
Protocol commit `1f1ff148`; implementation `48d7c4aa`; source/input lock `6bdcd089`.
Candidate SHA remains `7ecb2e9f87e1a2fc201bfa6d691b96d3706b7e9c461bb198047cf49bf10feb96`.

All commands used this exact CPU prefix:

```bash
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 \
taskset -c 0,1 \
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
```

Append the following arguments, separately and serially. Execution receipts in round007 preserve exact child argv, returncode, wall time and runtime log SHA:

```text
experiments/partwise_sketch_hatching/round007_receipt.py TESTS_RED experiments/partwise_sketch_hatching/test_patch_attachment.py --backend endpoints
experiments/partwise_sketch_hatching/round007_receipt.py TESTS_GREEN experiments/partwise_sketch_hatching/test_patch_attachment.py --backend new
experiments/partwise_sketch_hatching/round007_receipt.py TESTS_RED_REPAIRED experiments/partwise_sketch_hatching/test_patch_attachment.py --backend endpoints
experiments/partwise_sketch_hatching/round007_receipt.py TESTS_GREEN_REPAIRED experiments/partwise_sketch_hatching/test_patch_attachment.py --backend new
experiments/partwise_sketch_hatching/round007_receipt.py INHERITED_CANDIDATE experiments/partwise_sketch_hatching/test_visibility_primitive.py --backend new
experiments/partwise_sketch_hatching/round007_receipt.py INHERITED_ORACLE experiments/partwise_sketch_hatching/test_coverage_fixture.py --backend new
experiments/partwise_sketch_hatching/round007_receipt.py INHERITED_TEMPORAL experiments/partwise_sketch_hatching/test_temporal_audit.py --backend new
experiments/partwise_sketch_hatching/round007_receipt.py INHERITED_STAGE experiments/partwise_sketch_hatching/test_stage_attribution.py --backend new
experiments/partwise_sketch_hatching/round007_receipt.py PREPARE_EXECUTION experiments/partwise_sketch_hatching/run_round007.py prepare
experiments/partwise_sketch_hatching/round007_receipt.py EVALUATION_EXECUTION experiments/partwise_sketch_hatching/run_round007.py evaluate
experiments/partwise_sketch_hatching/round007_receipt.py VALIDATION_EXECUTION experiments/partwise_sketch_hatching/run_round007.py validate
```

First RED: exit1, 5/8 pass. Initial GREEN: exit1, 7/8 pass due a test fixture integer-array injection bug. Both failures are preserved. Corrected RED: exit1, 5/8 pass; corrected GREEN: exit0, 8/8 pass. See `PRE_EVALUATION_NOTES_ZH.md` for exact correction. The initial GREEN is a historical development state, not the current file behavior. No acceptance fixture had been evaluated at correction time.

Candidate/oracle/temporal/stage: exit0, 11/9/5/7 tests pass. Prepare/evaluate/validate: exit0. Twelve ordinary cases, twenty-four chord rejections, one connected multidepth rejection. Deterministic replay compares 559 new arrays, 1634 round006 arrays, 860 round005 arrays, all metrics and negative controls exactly.

Prepare only hashes assets and verifies previous seals. Implementation was committed before prepare; ASSET_LOCK was committed before evaluate. Candidate and historical source bytes remain fixed. Wrapper runs `taskset -c 0,1 timeout 600 <same-python> <args>` and writes an atomic running receipt before launch and a completed receipt with actual return code afterward. The common module sets CUDA visibility empty and all numeric thread caps before scientific imports. No environment dump is used.

Seal/verify use the same prefix with:

```text
experiments/partwise_sketch_hatching/seal_round007.py
experiments/partwise_sketch_hatching/seal_round007.py --verify
```

Do not run prepare/evaluate or any write path into a sealed directory. Future replay requires a new authorized destination and a new source lock; changing the historical common module would invalidate its seal. Read-only seal verification is safe. Runtime logs are excluded from scientific manifest but bound by receipt SHA; reports/configs/sources remain in the authorized worktree.
