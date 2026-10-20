所有命令从授权工作树执行，round011_common在导入数值库前设置CUDA_VISIBLE_DEVICES为空及数值线程2，taskset限定CPU0/1，计算串行。以下是实际执行命令。原目录封存后禁止覆盖重跑；validate为封存前的精确重放。

**RED_POINT** — returncode `1`; wall `0.326107253s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_area_coverage.py --point
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_011/runtime/red_point.log`

SHA256: `defbb94e1243b77a7f149024f3d374d1fe3a79cdb5617e25e8f1d6067da7588f`

**GREEN_AREA** — returncode `0`; wall `0.354780961s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_area_coverage.py
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_011/runtime/green_area.log`

SHA256: `81185f6775845c693cde59528259d617e069ce7730ec728aa47605f68643ad7d`

**INHERITED_ATTACHMENT** — returncode `0`; wall `0.195693026s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_mesh_attachment.py
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_011/runtime/inherited_attachment.log`

SHA256: `abfc014e2fdbeebcc2cad3ccab3f61ffc9a32e27bfa090d05ebf3991bdba440d`

**INHERITED_PATCH** — returncode `0`; wall `0.330891306s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_patch_attachment.py
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_011/runtime/inherited_patch.log`

SHA256: `da0b2558c758f1b9776ebcba451f2f7778ff372a5da14c4f6a38c86e3004e2db`

**INHERITED_CANDIDATE** — returncode `0`; wall `0.301076362s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_visibility_primitive.py
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_011/runtime/inherited_candidate.log`

SHA256: `b3d72453f55f0aa5dad39ace17d35a09a57b9c2f7b763ba4cce716c0174d526d`

**INHERITED_ORACLE** — returncode `0`; wall `0.290648482s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_coverage_fixture.py
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_011/runtime/inherited_oracle.log`

SHA256: `43272586b03b6a765bd717c0e8284284cf98db281a178a843033d01281a58dd3`

**INHERITED_TEMPORAL** — returncode `0`; wall `0.282302710s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_temporal_audit.py
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_011/runtime/inherited_temporal.log`

SHA256: `f7ecb0bb3dea4971fc301306abd43c44a69728840a4752e1f3d150780d55616c`

**INHERITED_STAGE** — returncode `0`; wall `0.290501701s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_stage_attribution.py
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_011/runtime/inherited_stage.log`

SHA256: `9e68a119676fc42de5ac47978a91e63ae6520e3cc3599712214755536930a198`

**INHERITED_CENTERED** — returncode `0`; wall `0.274101235s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_centered_coverage.py
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_011/runtime/inherited_centered.log`

SHA256: `b2d8dc407309369564a39fa0c8ade91fba9f9583e76db702cff94042e5edee95`

**PREPARE_EXECUTION** — returncode `0`; wall `0.365860993s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/run_round011.py prepare
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_011/runtime/prepare_execution.log`

SHA256: `bd0c498cc3cf8fed961226de767b1b8c021b8612f73d6b150001a1fd96b6d6cb`

**EVALUATION_EXECUTION** — returncode `0`; wall `4.567364454s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/run_round011.py evaluate
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_011/runtime/evaluation_execution.log`

SHA256: `a38ca6d9c28547565f9db4058b41440ef86ee39a19533572ad5107fcf4d82007`

**VALIDATION_EXECUTION** — returncode `0`; wall `4.271776579s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/run_round011.py validate
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_011/runtime/validation_execution.log`

SHA256: `15f77095c0f572d264a49ffd0f9566d35de7be15cb497c3fdff2b78cc8cc4b1a`

RED_POINT为两项真实面积失败；正常64项单元测试通过。接受和重放均返回0，609个新数组、3993个历史数组、180个适配器比较精确一致。
