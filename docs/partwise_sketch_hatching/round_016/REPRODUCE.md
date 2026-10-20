Round016实际执行命令与返回码。所有命令在授权worktree执行；串行、CPU affinity 0,1、线程≤2。协议083da186、实现a61db174、输入锁be1e1a4f在评价前提交。

这些是原执行记录；evaluate/prepare禁止覆盖已封存输出。`seal_round016.py --verify`只读验证当前seal，可在封存后运行。

**RED_AXIAL：rc=1**

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_planar_axial_reference.py --broken
```

收据 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/RED_AXIAL.json`；日志 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/runtime/red_axial.log`；日志 SHA256 `4db37e89cc6941619e1fb5068bbf957b6a532e0e6c729292c3ed691bf11a2f7b`。

**GREEN_AXIAL：rc=0**

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_planar_axial_reference.py
```

收据 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/GREEN_AXIAL.json`；日志 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/runtime/green_axial.log`；日志 SHA256 `6d7143d09f2c2a9a2295bb84a764eb6bb86e4b97a775e4ea011ae18dc37590ba`。

**RED_METRICS：rc=1**

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_planar_temporal_metrics.py --broken
```

收据 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/RED_METRICS.json`；日志 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/runtime/red_metrics.log`；日志 SHA256 `2cee301b5b82332b10c22c07cac66cc102ec60930097e6221a0ee400970fa364`。

**GREEN_METRICS：rc=0**

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_planar_temporal_metrics.py
```

收据 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/GREEN_METRICS.json`；日志 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/runtime/green_metrics.log`；日志 SHA256 `45b5296f758ea6883fee1e9b4f1181b4e2499bc9e451e125731f9cb7b8aa3be3`。

**TEST_MESH_ATTACHMENT：rc=0**

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_mesh_attachment.py
```

收据 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/TEST_MESH_ATTACHMENT.json`；日志 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/runtime/test_mesh_attachment.log`；日志 SHA256 `abfc014e2fdbeebcc2cad3ccab3f61ffc9a32e27bfa090d05ebf3991bdba440d`。

**TEST_PATCH_ATTACHMENT：rc=0**

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_patch_attachment.py
```

收据 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/TEST_PATCH_ATTACHMENT.json`；日志 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/runtime/test_patch_attachment.log`；日志 SHA256 `a08c3fd4513e72213aacdac61e90848a0109479773767fe259eb519ea4b0a911`。

**TEST_VISIBILITY_PRIMITIVE：rc=0**

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_visibility_primitive.py
```

收据 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/TEST_VISIBILITY_PRIMITIVE.json`；日志 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/runtime/test_visibility_primitive.log`；日志 SHA256 `b3d72453f55f0aa5dad39ace17d35a09a57b9c2f7b763ba4cce716c0174d526d`。

**TEST_COVERAGE_FIXTURE：rc=0**

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_coverage_fixture.py
```

收据 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/TEST_COVERAGE_FIXTURE.json`；日志 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/runtime/test_coverage_fixture.log`；日志 SHA256 `43272586b03b6a765bd717c0e8284284cf98db281a178a843033d01281a58dd3`。

**TEST_TEMPORAL_AUDIT：rc=0**

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_temporal_audit.py
```

收据 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/TEST_TEMPORAL_AUDIT.json`；日志 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/runtime/test_temporal_audit.log`；日志 SHA256 `f7ecb0bb3dea4971fc301306abd43c44a69728840a4752e1f3d150780d55616c`。

**TEST_STAGE_ATTRIBUTION：rc=0**

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_stage_attribution.py
```

收据 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/TEST_STAGE_ATTRIBUTION.json`；日志 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/runtime/test_stage_attribution.log`；日志 SHA256 `9e68a119676fc42de5ac47978a91e63ae6520e3cc3599712214755536930a198`。

**TEST_CENTERED_COVERAGE：rc=0**

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_centered_coverage.py
```

收据 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/TEST_CENTERED_COVERAGE.json`；日志 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/runtime/test_centered_coverage.log`；日志 SHA256 `b2d8dc407309369564a39fa0c8ade91fba9f9583e76db702cff94042e5edee95`。

**TEST_AREA_COVERAGE：rc=0**

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_area_coverage.py
```

收据 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/TEST_AREA_COVERAGE.json`；日志 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/runtime/test_area_coverage.log`；日志 SHA256 `0b081d1d2e05ad9bd7ab7f779f40f29ac2f28efa07915c446b2659353cc0e6dd`。

**TEST_PHYSICAL_AREA_REFERENCE：rc=0**

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_physical_area_reference.py
```

收据 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/TEST_PHYSICAL_AREA_REFERENCE.json`；日志 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/runtime/test_physical_area_reference.log`；日志 SHA256 `a0f4118b266d1b2e81f01bc13f32228de040de181429cff3366e1df13ed2001e`。

**TEST_PLANAR_FRAGMENTS：rc=0**

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_planar_fragments.py
```

收据 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/TEST_PLANAR_FRAGMENTS.json`；日志 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/runtime/test_planar_fragments.log`；日志 SHA256 `345a5c3a44bef793beede49a90a1d8b8a61cca5845b2e8191bef1ec794e5a836`。

**TEST_EXACT_TRIANGLE_SET：rc=0**

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_exact_triangle_set.py
```

收据 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/TEST_EXACT_TRIANGLE_SET.json`；日志 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/runtime/test_exact_triangle_set.log`；日志 SHA256 `1edecc8d77d7ddf38979b386f52f80c2493e9054596b03d295f70a46125d553a`。

**CANDIDATE_FRAGMENTS：rc=0**

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -c 'import sys;sys.path.insert(0,'"'"'experiments/partwise_sketch_hatching'"'"');import round016_common;import test_planar_fragments as t;import planar_fragments_exact as n;import unittest;t.new=n;unittest.main(module=t,verbosity=2)'
```

收据 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/CANDIDATE_FRAGMENTS.json`；日志 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/runtime/candidate_fragments.log`；日志 SHA256 `1cbfee29c2a842a7a9cd923f63675e27be612bbfd5dc96990052216cf81564ea`。

**PREPARE_EXECUTION：rc=0**

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/run_round016.py prepare
```

收据 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/PREPARE_EXECUTION.json`；日志 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/runtime/prepare_execution.log`；日志 SHA256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`。

**EVALUATION_EXECUTION：rc=0**

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/run_round016.py evaluate
```

收据 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/EVALUATION_EXECUTION.json`；日志 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/runtime/evaluation_execution.log`；日志 SHA256 `9923e1d678dbcbba98e2bca33fec99d66cdb7fbbfd70d390c1c2b77db1b30999`。

**VALIDATION_EXECUTION：rc=0**

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/run_round016.py validate
```

收据 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/VALIDATION_EXECUTION.json`；日志 `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_016/runtime/validation_execution.log`；日志 SHA256 `fc7a55398ad7c943d5fb7d4c2354c423e627a8e73c49fee1b8ae0b79a408c69a`。

只读seal复核：

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/seal_round016.py --verify
```

原始正常测试108次全部通过；两个故意错误替身各6项、各3失败，均预期rc=1。新输出496数组及历史7360科学数组+180适配器数组均精确重放。
