# Round005 exact execution commands

Worktree `/home/u00134/3dgs_line/partwise_sketch_hatching_p0p1_v01`, branch
`partwise-sketch-hatching-p0p1-v01`. Protocol commit `d92e2a6a`, implementation
`c6c65a00`, source/input lock `d73d0e3c`. No lamp render was performed.

Every command below used this exact CPU prefix:

```bash
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 \
taskset -c 0,1 \
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
```

Append each argument sequence separately, serially:

```text
experiments/partwise_sketch_hatching/round005_receipt.py TESTS_RED experiments/partwise_sketch_hatching/test_coverage_fixture.py --backend broken
experiments/partwise_sketch_hatching/round005_receipt.py TESTS_GREEN experiments/partwise_sketch_hatching/test_coverage_fixture.py --backend new
experiments/partwise_sketch_hatching/round005_receipt.py INHERITED_TEMPORAL experiments/partwise_sketch_hatching/test_temporal_audit.py --backend new
experiments/partwise_sketch_hatching/round005_receipt.py INHERITED_STAGE experiments/partwise_sketch_hatching/test_stage_attribution.py --backend new
experiments/partwise_sketch_hatching/round005_receipt.py PREPARE_EXECUTION experiments/partwise_sketch_hatching/run_round005.py prepare
experiments/partwise_sketch_hatching/round005_receipt.py EVALUATION_EXECUTION experiments/partwise_sketch_hatching/run_round005.py evaluate
experiments/partwise_sketch_hatching/round005_receipt.py VALIDATION_EXECUTION experiments/partwise_sketch_hatching/run_round005.py validate
```

The wrapper writes a started receipt before execution, launches the same Python
under `taskset -c 0,1 timeout 600`, and atomically replaces the receipt with the
actual child exit code and stdout/stderr SHA256. CUDA is hidden and numeric
threads capped before imports. It never prints the environment.

RED returns 1: five intentional oracle failures, four skips. GREEN returns 0:
nine tests pass. Inherited temporal and stage return 0: five and seven tests
pass respectively. Prepare/evaluate/validate return 0. Full replay checks all
20 cases, all 860 arrays by exact value, all saved metrics and historical seal.

Source and controls were committed before evaluation. The oracle GREEN ran
before the later addition of an `AA_owner` output field used only by the figure
writer; no tested geometry/metric routine changed afterward. The full frozen
implementation was exercised by evaluation and exact replay.

Seal and verification use the same CPU prefix:

```text
experiments/partwise_sketch_hatching/seal_round005.py
experiments/partwise_sketch_hatching/seal_round005.py --verify
```

Do not rerun preparation/evaluation into the sealed round. A future replay
requires separately authorized output paths and an explicit source lock;
never alter the current or historical sealed artifacts. Runtime logs are
excluded from the science seal but their hashes are bound in sealed receipts.
