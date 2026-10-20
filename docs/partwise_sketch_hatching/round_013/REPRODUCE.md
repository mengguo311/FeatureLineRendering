本轮命令与返回码记录（授权分支`partwise-sketch-hatching-p0p1-v01`，cwd为该worktree）：

```bash
PY=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
```

执行入口`round013_common.py`在导入数值库前清空CUDA可见设备、限制OMP/BLAS线程为2并设置affinity[0,1]。收据包装器执行`taskset -c 0,1 timeout 600 "$PY" ...`，保存完整argv、退出码、耗时与日志SHA。以下是**已经执行**的原命令；封存后不要在同一目录重跑写入型prepare/evaluate/validate。

```bash
"$PY" experiments/partwise_sketch_hatching/round013_receipt.py RED_OLD_RENDERER_VALID experiments/partwise_sketch_hatching/test_planar_fragments.py --old
# rc=1: 1 expected assertion failure, 2 pass, 5 skipped
"$PY" experiments/partwise_sketch_hatching/round013_receipt.py GREEN_FRAGMENTS_VALID experiments/partwise_sketch_hatching/test_planar_fragments.py
# rc=0: 8 pass
"$PY" experiments/partwise_sketch_hatching/round013_receipt.py PREPARE_EXECUTION experiments/partwise_sketch_hatching/run_round013.py prepare
# rc=0; source/input lock committed as 06dafa85 before evaluation
"$PY" experiments/partwise_sketch_hatching/round013_receipt.py EVALUATION_EXECUTION experiments/partwise_sketch_hatching/run_round013.py evaluate
# rc=0; measurement valid, candidate NO_GO
"$PY" experiments/partwise_sketch_hatching/round013_receipt.py VALIDATION_EXECUTION experiments/partwise_sketch_hatching/run_round013.py validate
# rc=0; 1045 new arrays and all case metrics exact
```

九组继承测试均通过，各命令形式为`"$PY" experiments/partwise_sketch_hatching/round013_receipt.py RECEIPT experiments/partwise_sketch_hatching/TEST.py`：

| RECEIPT | TEST | 通过数 | 返回码 |
|---|---|---:|---:|
| INHERITED_ATTACHMENT | test_mesh_attachment | 12 | 0 |
| INHERITED_PATCH | test_patch_attachment | 8 | 0 |
| INHERITED_CANDIDATE | test_visibility_primitive | 11 | 0 |
| INHERITED_ORACLE | test_coverage_fixture | 9 | 0 |
| INHERITED_TEMPORAL | test_temporal_audit | 5 | 0 |
| INHERITED_STAGE | test_stage_attribution | 7 | 0 |
| INHERITED_CENTERED | test_centered_coverage | 6 | 0 |
| INHERITED_AREA | test_area_coverage | 6 | 0 |
| INHERITED_REFERENCE | test_physical_area_reference | 8 | 0 |

所有执行收据与原始科学产物位于`/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_013/`。`RED_OLD_RENDERER`及`GREEN_FRAGMENTS`是修正开发夹具之前的报错记录，返回1，不能混作有效RED/GREEN。有效收据带`_VALID`。

只读封存检查：

```bash
"$PY" experiments/partwise_sketch_hatching/seal_round013.py --verify
```

只读数学重放（不会调用带写入的`validate()`；仍需遵守当前资源/时间授权）：

```bash
"$PY" - <<'PY'
import sys,json
sys.path.insert(0,'experiments/partwise_sketch_hatching')
import round013_common as c
import run_round013 as r
import numpy as np
c.verify_lock()
c.verify_prior()
count=0
for spec in r.P['cases']:
    m,a=r.evaluate_case(spec)
    assert m==json.loads((c.R/'raw'/(spec['id']+'.json')).read_text())
    saved=dict(np.load(c.R/'raw'/(spec['id']+'.npz')))
    assert set(a)==set(saved)
    for k in a:
        np.testing.assert_array_equal(a[k],saved[k])
        count+=1
assert r.historical_replay()['all_exact']
print({'arrays_exact':count})
PY
```

`FAILURE_LOCALIZATION.json`是从保存的数组读取所有失败不变性门槛的位置：对各`ordering_gates`中false项计算`variant_NAME_KEY != candidate_KEY`，记录全部不同坐标及对应raw/clean visible、owned、occluded数值。它不调用候选，也不改变任何门槛。每个原始NPZ的SHA已绑定。

协议冻结`f3e2ee1b`，实现`cd731762`，源码/输入锁`06dafa85`。报告提交和最终产物身份以本轮`SEAL.json`、`SHA256_MANIFEST.json`、`STATUS.json`为准。历史封存不可重写。恢复与下一步以本轮`NEXT.json`为准。
