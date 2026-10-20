Round009实际执行与复现记录

协议583f3896；实现c22af9ff；接受评测前SHA锁b636107e。所有命令在授权worktree串行运行，CUDA_VISIBLE_DEVICES为空、数值线程≤2、CPU[0,1]，由round009_common在数值模块导入前设置。

下列是已经执行的精确子进程命令。封存后不要在原目录重跑prepare/evaluate/validate写命令。

INHERITED_ATTACHMENT
```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_mesh_attachment.py
```
returncode=0; wall_seconds=0.1699868980795145; log=/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_009/runtime/inherited_attachment.log; SHA256=7cb7b30d47b28416a0a2849510e0efabc5f1e457117a2985b14b303c9dba72af

INHERITED_PATCH
```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_patch_attachment.py
```
returncode=0; wall_seconds=0.28459481289610267; log=/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_009/runtime/inherited_patch.log; SHA256=a08c3fd4513e72213aacdac61e90848a0109479773767fe259eb519ea4b0a911

INHERITED_CANDIDATE
```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_visibility_primitive.py
```
returncode=0; wall_seconds=0.31646054796874523; log=/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_009/runtime/inherited_candidate.log; SHA256=b3d72453f55f0aa5dad39ace17d35a09a57b9c2f7b763ba4cce716c0174d526d

INHERITED_ORACLE
```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_coverage_fixture.py
```
returncode=0; wall_seconds=0.2864925153553486; log=/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_009/runtime/inherited_oracle.log; SHA256=43272586b03b6a765bd717c0e8284284cf98db281a178a843033d01281a58dd3

INHERITED_TEMPORAL
```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_temporal_audit.py
```
returncode=0; wall_seconds=0.28736921260133386; log=/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_009/runtime/inherited_temporal.log; SHA256=f7ecb0bb3dea4971fc301306abd43c44a69728840a4752e1f3d150780d55616c

INHERITED_STAGE
```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_stage_attribution.py
```
returncode=0; wall_seconds=0.2907143132761121; log=/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_009/runtime/inherited_stage.log; SHA256=9e68a119676fc42de5ac47978a91e63ae6520e3cc3599712214755536930a198

PREPARE_EXECUTION
```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/run_round009.py prepare
```
returncode=0; wall_seconds=0.3333063069730997; log=/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_009/runtime/prepare_execution.log; SHA256=8a041dfe5d451065c1b23cc94a7bd44e9b0cda13ee7dd239867d5793cd9f6b94

EVALUATION_EXECUTION
```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/run_round009.py evaluate
```
returncode=0; wall_seconds=2.378584258724004; log=/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_009/runtime/evaluation_execution.log; SHA256=4c4b23b8164617c6a9861fd0569ca941d1fa3a5a7a90dc683dd9bd328cce5fbf

VALIDATION_EXECUTION
```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/run_round009.py validate
```
returncode=0; wall_seconds=2.292189175263047; log=/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_009/runtime/validation_execution.log; SHA256=2014337bed83d0f3bd86259f284f4d2fd0f8800c03d2537a32e2f9dad575b621

封存后的只读校验：
```bash
taskset -c 0,1 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/seal_round009.py --verify
```

只读科学重放可以导入run_round009.evaluate_case、negative_control、historical_replay，然后与raw NPZ/JSON逐项断言；不要调用会写STATUS/VALIDATION的validate入口。下面命令不改任何已封存科学文件。
```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python - <<'PY'
import sys
sys.path.insert(0, "experiments/partwise_sketch_hatching")
import run_round009 as run
import json
import numpy as np
for spec in run.P["cases"]:
    metrics, arrays = run.evaluate_case(spec)
    prefix = run.c.R / "raw" / spec["id"]
    assert metrics == json.loads(prefix.with_suffix(".json").read_text())
    old = dict(np.load(prefix.with_suffix(".npz")))
    assert set(arrays) == set(old)
    for key in arrays: np.testing.assert_array_equal(arrays[key], old[key])
negative, arrays = run.negative_control()
assert negative == json.loads((run.c.R/"negative_control.json").read_text())
old = dict(np.load(run.c.R/"raw/negative_control.npz"))
assert set(arrays) == set(old)
for key in arrays: np.testing.assert_array_equal(arrays[key], old[key])
assert run.historical_replay() == json.loads((run.c.R/"REGRESSION.json").read_text())
print("Exact read-only scientific replay passed")
PY
```
