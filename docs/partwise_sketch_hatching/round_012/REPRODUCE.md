从授权工作树执行。round012_common在数值库导入前设置CUDA_VISIBLE_DEVICES为空、数值线程2及CPU affinity[0,1]。以下为真实收据中的精确命令和返回码；全部计算串行。封存后不要覆盖原产物。validate是封存前的逐值重放。

**RED_CENTER_REFERENCE** — returncode `1`; wall `0.155476171s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_physical_area_reference.py --center-gated
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_012/runtime/red_center_reference.log`

SHA256: `162daf63a2df288e8606b1bc3921c673230b829ea20d075dc08b0f44411c035d`

**GREEN_REFERENCE** — returncode `0`; wall `0.164386300s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_physical_area_reference.py
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_012/runtime/green_reference.log`

SHA256: `a0f4118b266d1b2e81f01bc13f32228de040de181429cff3366e1df13ed2001e`

**INHERITED_ATTACHMENT** — returncode `0`; wall `0.169280196s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_mesh_attachment.py
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_012/runtime/inherited_attachment.log`

SHA256: `7cb7b30d47b28416a0a2849510e0efabc5f1e457117a2985b14b303c9dba72af`

**INHERITED_PATCH** — returncode `0`; wall `0.323740378s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_patch_attachment.py
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_012/runtime/inherited_patch.log`

SHA256: `a08c3fd4513e72213aacdac61e90848a0109479773767fe259eb519ea4b0a911`

**INHERITED_CANDIDATE** — returncode `0`; wall `0.296842779s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_visibility_primitive.py
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_012/runtime/inherited_candidate.log`

SHA256: `b3d72453f55f0aa5dad39ace17d35a09a57b9c2f7b763ba4cce716c0174d526d`

**INHERITED_ORACLE** — returncode `0`; wall `0.286972987s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_coverage_fixture.py
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_012/runtime/inherited_oracle.log`

SHA256: `43272586b03b6a765bd717c0e8284284cf98db281a178a843033d01281a58dd3`

**INHERITED_TEMPORAL** — returncode `0`; wall `0.289607230s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_temporal_audit.py
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_012/runtime/inherited_temporal.log`

SHA256: `f7ecb0bb3dea4971fc301306abd43c44a69728840a4752e1f3d150780d55616c`

**INHERITED_STAGE** — returncode `0`; wall `0.282923076s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_stage_attribution.py
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_012/runtime/inherited_stage.log`

SHA256: `9e68a119676fc42de5ac47978a91e63ae6520e3cc3599712214755536930a198`

**INHERITED_CENTERED** — returncode `0`; wall `0.275548970s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_centered_coverage.py
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_012/runtime/inherited_centered.log`

SHA256: `20e630688203810bc4fdca982693c81008899a39e8244fe1f2b9cd40a9ead82b`

**INHERITED_AREA** — returncode `0`; wall `0.346067063s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/test_area_coverage.py
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_012/runtime/inherited_area.log`

SHA256: `04c410f1d9fc2d072239cb0abdc90dcd09ddf807d8356b4036b2719e66ae67eb`

**PREPARE_EXECUTION** — returncode `0`; wall `0.416132240s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/run_round012.py prepare
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_012/runtime/prepare_execution.log`

SHA256: `b524b682f3b83a9eef102a92ee5a2677bd8ffa9c12281638033306fbd2e12a2f`

**EVALUATION_EXECUTION** — returncode `0`; wall `4.586781874s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/run_round012.py evaluate
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_012/runtime/evaluation_execution.log`

SHA256: `a534ab2ae1a5eaf38927b7db02ef20156f241168e1bc14f9528b566e8982d341`

**VALIDATION_EXECUTION** — returncode `0`; wall `4.442520907s`

```bash
taskset -c 0,1 timeout 600 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/run_round012.py validate
```

stdout/stderr: `/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_012/runtime/validation_execution.log`

SHA256: `240926efaabef19c2b5e5f4c44de907f3d1ff856ef44b7f99987b2761f95207e`

RED_CENTER_REFERENCE为解析中心门控替身的两项预期失败；它不是旧renderer调用。正常72项单元测试通过，evaluate/validate返回0表示诊断执行完成。科学判定为MEASUREMENT_VALID_PHYSICAL_VISIBILITY_NO_GO。新172数组、历史4602数组及180个适配器比较一致。
