# Round006 reproduction and actual commands

Authorized worktree `/home/u00134/3dgs_line/partwise_sketch_hatching_p0p1_v01`, branch `partwise-sketch-hatching-p0p1-v01`.
Protocol commit `b586abad`, implementation `504ee52a`, pre-evaluation SHA lock `370fd9a7`.

Use this CPU prefix:

```bash
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 \
taskset -c 0,1 \
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
```

Append each command separately, serially:

```text
experiments/partwise_sketch_hatching/round006_receipt.py TESTS_RED experiments/partwise_sketch_hatching/test_visibility_primitive.py --backend legacy
experiments/partwise_sketch_hatching/round006_receipt.py TESTS_RED_COMMITTED experiments/partwise_sketch_hatching/test_visibility_primitive.py --backend legacy
experiments/partwise_sketch_hatching/round006_receipt.py TESTS_GREEN experiments/partwise_sketch_hatching/test_visibility_primitive.py --backend new
experiments/partwise_sketch_hatching/round006_receipt.py INHERITED_ORACLE experiments/partwise_sketch_hatching/test_coverage_fixture.py --backend new
experiments/partwise_sketch_hatching/round006_receipt.py INHERITED_TEMPORAL experiments/partwise_sketch_hatching/test_temporal_audit.py --backend new
experiments/partwise_sketch_hatching/round006_receipt.py INHERITED_STAGE experiments/partwise_sketch_hatching/test_stage_attribution.py --backend new
experiments/partwise_sketch_hatching/round006_receipt.py PREPARE_EXECUTION experiments/partwise_sketch_hatching/run_round006.py prepare
experiments/partwise_sketch_hatching/round006_receipt.py EVALUATION_EXECUTION experiments/partwise_sketch_hatching/run_round006.py evaluate
experiments/partwise_sketch_hatching/round006_receipt.py VALIDATION_EXECUTION experiments/partwise_sketch_hatching/run_round006.py validate
```

Both RED executions return1 (three failures, two passes, six skips). GREEN returns0 (11 passes). Inherited oracle/temporal/stage return0 (9/5/7 passes). Prepare/evaluate/validate return0. Evaluation completes18 acceptance and20 regression cases; replay checks1634 new arrays plus860 original round005 arrays and every metric exactly.

Two execution details are retained rather than rewritten:

1. Initial `git add` lacked `--sparse` and failed; the shell continued to the first development RED before the protocol commit. See `FREEZE_EXECUTION_NOTE_ZH.md`. The unchanged RED was repeated after committing, before candidate implementation and all acceptance evaluation.
2. The actual validation outer shell accidentally spelled its CUDA variable `CUDA_VISIBLE_DEVICESIS=''`. The wrapper's first import, `round006_common`, unconditionally sets the correct `CUDA_VISIBLE_DEVICES=''`, numeric thread limits and affinity before spawning the child and before scientific imports. No torch or GPU execution occurred. All child argv are preserved verbatim in execution receipts. For exact shell replay of that one invocation, substitute the misspelled outer variable; the correct prefix above is preferred and produces the same enforced child setup.

Wrapper child command is `taskset -c 0,1 timeout 600 <same-python> <arguments>`, with recoverable started/completed receipt and exact return code. No environment is dumped.

Seal and verify with the CPU prefix and these arguments:

```text
experiments/partwise_sketch_hatching/seal_round006.py
experiments/partwise_sketch_hatching/seal_round006.py --verify
```

Do not rerun prepare/evaluate into sealed round006. Any future independent replay needs a new authorized output destination and explicit source lock. Historical seals and sources are immutable. Runtime stdout/stderr is excluded from science manifest but hashes are bound by receipts. No lamp render, video, GPU operation, download, push or merge was performed.
