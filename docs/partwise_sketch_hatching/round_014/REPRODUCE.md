本轮均在授权worktree与分支执行。以下命令已真实执行；封存后不要重新运行本目录的写入型prepare/evaluate/validate。完整argv、退出码、耗时、日志SHA在round014各执行收据。

```bash
PY=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
"$PY" experiments/partwise_sketch_hatching/round014_receipt.py RED_EXACT_SET experiments/partwise_sketch_hatching/test_exact_triangle_set.py --old
# rc=1: 1 expected failure, 7 skipped
"$PY" experiments/partwise_sketch_hatching/round014_receipt.py GREEN_EXACT_SET experiments/partwise_sketch_hatching/test_exact_triangle_set.py
# rc=0: 8 pass
"$PY" experiments/partwise_sketch_hatching/round014_receipt.py PREPARE_EXECUTION experiments/partwise_sketch_hatching/run_round014.py prepare
# rc=0; then ASSET_LOCK committed as ffc519d3
"$PY" experiments/partwise_sketch_hatching/round014_receipt.py EVALUATION_EXECUTION experiments/partwise_sketch_hatching/run_round014.py evaluate
# rc=0; 10/10 repair GO
"$PY" experiments/partwise_sketch_hatching/round014_receipt.py VALIDATION_EXECUTION experiments/partwise_sketch_hatching/run_round014.py validate
# rc=0; 1045 new arrays exact and all historical replays exact
```

包装器统一设置CUDA不可见、OMP/BLAS线程≤2，子进程命令为`taskset -c 0,1 timeout 600 "$PY" ...`。十组继承测试形式为`"$PY" experiments/partwise_sketch_hatching/round014_receipt.py RECEIPT experiments/partwise_sketch_hatching/TEST.py`，均rc=0：

| RECEIPT | TEST | 通过数 |
|---|---|---:|
| INHERITED_ATTACHMENT | test_mesh_attachment | 12 |
| INHERITED_PATCH | test_patch_attachment | 8 |
| INHERITED_CANDIDATE | test_visibility_primitive | 11 |
| INHERITED_ORACLE | test_coverage_fixture | 9 |
| INHERITED_TEMPORAL | test_temporal_audit | 5 |
| INHERITED_STAGE | test_stage_attribution | 7 |
| INHERITED_CENTERED | test_centered_coverage | 6 |
| INHERITED_AREA | test_area_coverage | 6 |
| INHERITED_REFERENCE | test_physical_area_reference | 8 |
| INHERITED_FRAGMENTS | test_planar_fragments | 8 |

旧8项片段测试接新候选的原命令（rc=0，8 pass）：

```bash
"$PY" experiments/partwise_sketch_hatching/round014_receipt.py CANDIDATE_FRAGMENTS -c "import sys; sys.path.insert(0,'experiments/partwise_sketch_hatching'); import round014_common; import test_planar_fragments as t; import planar_fragments_exact as n; import unittest; t.new=n; unittest.main(module=t,verbosity=2)"
```

只读seal核验：

```bash
"$PY" experiments/partwise_sketch_hatching/seal_round014.py --verify
```

源码/配置锁和所有原始NPZ均由最终SHA256_MANIFEST/SEAL绑定。仅阅读的数学重放可导入`run_round014`，逐例调用`evaluate_case`与保存的JSON/NPZ作精确比较，并调用`historical_replay`；不要调用带写入的`validate`覆盖已封存科学单元。所有原失败值见round013/FAILURE_LOCALIZATION，新旧九格对照见本轮REPAIR_SITES。下一步以NEXT.json为准。
