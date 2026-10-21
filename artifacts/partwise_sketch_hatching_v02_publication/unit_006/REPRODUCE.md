本记录是已执行命令/原始退出码；封存目录禁止覆盖重跑。新生产必须迁移到新授权unit并保留本结果。

EXECUTION_cold: rc=0, wall=0.917238s

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/run_unit006.py cold
```

EXECUTION_finish: rc=0, wall=0.415494s

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/finish_unit006.py
```

EXECUTION_generation: rc=0, wall=69.635044s

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/run_unit006.py run
```

EXECUTION_history: rc=0, wall=0.365254s

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/audit_unit006.py
```

EXECUTION_loader_cli: rc=0, wall=0.265010s

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/reconstruction_dataset.py /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_006/dataset
```

EXECUTION_lock: rc=0, wall=0.365256s

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/lock_unit006.py
```

EXECUTION_prepare: rc=0, wall=0.365212s

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/prepare_unit006.py
```

EXECUTION_prerefine: rc=0, wall=0.315108s

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/refine_protocol_unit006.py
```

EXECUTION_recovery: rc=0, wall=3.726367s

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/recover_validation_unit006.py
```

EXECUTION_recovery_freeze: rc=0, wall=0.315292s

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/freeze_recovery_unit006.py
```

EXECUTION_validate: rc=1, wall=4.228311s

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/validate_unit006.py
```

EXECUTION_visual_record: rc=0, wall=0.315289s

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/record_visual_unit006.py
```

所有命令均通过receipt_unit006.py约束CPU affinity[0,1]、数值线程1、CUDA不可见、590秒超时，TMPDIR使用已指定scratch。stdout/stderr只在runtime，科学seal仅收据绑定其SHA。
