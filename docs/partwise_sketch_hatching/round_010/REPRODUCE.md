所有命令从授权工作树执行；共同导入round010_common设置CUDA_VISIBLE_DEVICES为空及数值线程2，子进程taskset限定CPU0/1。计算串行执行。以下为收据记录的实际子命令，不是建议命令。原目录已封存，禁止在该目录覆盖重跑；重放验证命令只在封存前执行。

**RED_LEGACY** — returncode `1`; wall `0.280610364s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_centered_coverage.py --legacy
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_010/runtime/red_legacy.log`

SHA256: `fe405b351e8937b732e515dfec78744aeba33e89809b3cd5692bb105c8b0df7a`

**GREEN_COVERAGE** — returncode `0`; wall `0.301811293s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_centered_coverage.py
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_010/runtime/green_coverage.log`

SHA256: `b2d8dc407309369564a39fa0c8ade91fba9f9583e76db702cff94042e5edee95`

**INHERITED_ATTACHMENT** — returncode `0`; wall `0.156855146s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_mesh_attachment.py
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_010/runtime/inherited_attachment.log`

SHA256: `fedb6ac74bea47d6f34307e30136cf113fdd5bd9b14a510579395a204b853f52`

**INHERITED_PATCH** — returncode `0`; wall `0.322183469s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_patch_attachment.py
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_010/runtime/inherited_patch.log`

SHA256: `a08c3fd4513e72213aacdac61e90848a0109479773767fe259eb519ea4b0a911`

**INHERITED_CANDIDATE** — returncode `0`; wall `0.296650197s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_visibility_primitive.py
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_010/runtime/inherited_candidate.log`

SHA256: `b3d72453f55f0aa5dad39ace17d35a09a57b9c2f7b763ba4cce716c0174d526d`

**INHERITED_ORACLE** — returncode `0`; wall `0.293831224s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_coverage_fixture.py
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_010/runtime/inherited_oracle.log`

SHA256: `43272586b03b6a765bd717c0e8284284cf98db281a178a843033d01281a58dd3`

**INHERITED_TEMPORAL** — returncode `0`; wall `0.284543782s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_temporal_audit.py
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_010/runtime/inherited_temporal.log`

SHA256: `f7ecb0bb3dea4971fc301306abd43c44a69728840a4752e1f3d150780d55616c`

**INHERITED_STAGE** — returncode `0`; wall `0.284721088s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_stage_attribution.py
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_010/runtime/inherited_stage.log`

SHA256: `9e68a119676fc42de5ac47978a91e63ae6520e3cc3599712214755536930a198`

**PREPARE_EXECUTION** — returncode `0`; wall `0.402537308s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/run_round010.py prepare
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_010/runtime/prepare_execution.log`

SHA256: `57d386878b7c01695fdd40ce2f24a001b4a60b1aee0becb502c497d0478fb07d`

**EVALUATION_EXECUTION** — returncode `0`; wall `2.832175398s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/run_round010.py evaluate
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_010/runtime/evaluation_execution.log`

SHA256: `d02f0e99d7794e19c859a34d8b0dd9711284a97e9aed5d5f405cbf4b43b430c8`

**VALIDATION_EXECUTION** — returncode `0`; wall `2.617558615s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/run_round010.py validate
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_010/runtime/validation_execution.log`

SHA256: `36d243f0386694c51154d35ff10497b0c6cf998b08db9da197ba7cd6e1e3f452`

RED_LEGACY为旧模板真实失败，6项中3项失败；GREEN_COVERAGE6项通过，继承52项通过。evaluate和validate均0，7案例/586新数组和3407历史科学数组及180适配器输出逐值一致。
