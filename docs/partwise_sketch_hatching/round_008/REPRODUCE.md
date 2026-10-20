Round008 exact execution receipts and reproduction

Protocol commit 28b2343b; implementation c1c3e793; pre-acceptance SHA lock 7e5cddf8.
All commands were serial, affinity [0,1], numeric threads<=2, no GPU.

```bash
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 taskset -c 0,1 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/round008_receipt.py TESTS_RED experiments/partwise_sketch_hatching/test_mesh_attachment.py --backend unguarded
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 taskset -c 0,1 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/round008_receipt.py TESTS_GREEN experiments/partwise_sketch_hatching/test_mesh_attachment.py --backend new
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 taskset -c 0,1 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/round008_receipt.py TESTS_GREEN_FINAL experiments/partwise_sketch_hatching/test_mesh_attachment.py --backend new
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 taskset -c 0,1 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/round008_receipt.py INHERITED_PATCH experiments/partwise_sketch_hatching/test_patch_attachment.py --backend new
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 taskset -c 0,1 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/round008_receipt.py INHERITED_CANDIDATE experiments/partwise_sketch_hatching/test_visibility_primitive.py --backend new
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 taskset -c 0,1 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/round008_receipt.py INHERITED_ORACLE experiments/partwise_sketch_hatching/test_coverage_fixture.py --backend new
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 taskset -c 0,1 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/round008_receipt.py INHERITED_TEMPORAL experiments/partwise_sketch_hatching/test_temporal_audit.py --backend new
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 taskset -c 0,1 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/round008_receipt.py INHERITED_STAGE experiments/partwise_sketch_hatching/test_stage_attribution.py --backend new
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 taskset -c 0,1 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/round008_receipt.py PREPARE_EXECUTION experiments/partwise_sketch_hatching/run_round008.py prepare
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 taskset -c 0,1 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/round008_receipt.py EVALUATION_EXECUTION experiments/partwise_sketch_hatching/run_round008.py evaluate
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 taskset -c 0,1 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/round008_receipt.py VALIDATION_EXECUTION experiments/partwise_sketch_hatching/run_round008.py validate
```

The receipt wrapper records actual child argv, exit status, runtime and stdout/stderr SHA. RED exit1 (10 failures/12); GREEN and GREEN_FINAL exit0 (12/12); inherited patch/candidate/oracle/temporal/stage exit0 (8/11/9/5/7). prepare/evaluate/validate exit0. Initial GREEN predates the documented shortest-edge implementation correction; its receipt remains historical.

The frozen package had 8 valid and22 invalid inputs. All controls passed. Replay:181 new arrays;559 round007,1634 round006,860 round005 arrays; additionally180 candidate arrays checked after the adapter (a subset of prior outputs, not extra independent samples). All associated metrics exact.

Seal and read-only verification use the same prefix:

```text
experiments/partwise_sketch_hatching/seal_round008.py
experiments/partwise_sketch_hatching/seal_round008.py --verify
```

Do not rerun write commands into any sealed directory. Future replay must use a new authorized destination and source lock; do not edit historical common modules. Raw input files intentionally contain NaN/Inf negative controls; JSON fixture markers are strings and loader converts them only for validation. No oracle depth is supplied to the adapter or candidate. All reports/configs/source remain in the authorized worktree; runtime output is excluded from science manifest and bound by receipt hashes.
