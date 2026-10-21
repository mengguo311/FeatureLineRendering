# Unit002 execution record

Commands below are the exact completed attempts, not instructions to overwrite sealed output.
All computations were serial, CPU affinity 0,1; CUDA_VISIBLE_DEVICES empty;
OMP/OPENBLAS/MKL/NUMEXPR threads1, PYTHONDONTWRITEBYTECODE1, and
TMPDIR=/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/orchestration/scratch.
The receipt wrapper adds a590s timeout and retains original return codes.
Do not invoke old producers/common.OUT/CLI: they target unit001. Future replay
requires a newly authorized output directory, with historical files read-only.

```text
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/audit_unit002.py
```

Return code: 0; seconds: 10.299978958908468

```text
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/run_unit002.py dev
```

Return code: 0; seconds: 12.352023644838482

```text
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/run_unit002.py freeze
```

Return code: 0; seconds: 0.36531641939654946

```text
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/run_unit002.py hidden
```

Return code: 0; seconds: 0.5157646909356117

```text
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/replay_unit002.py
```

Return code: 0; seconds: 6.633586346637458

```text
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/run_unit002.py stills
```

Return code: 0; seconds: 62.018280213698745

```text
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/test_contours_unit002.py
```

Return code: 0; seconds: 0.41542921494692564

```text
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/test_renderer.py
```

Return code: 0; seconds: 0.5156296347267926

```text
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/test_contours_unit002.py --mode surface_fragments
```

Return code: 1; seconds: 0.4156902590766549

```text
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/validate_unit002.py
```

Return code: 0; seconds: 2.1214805003255606

Orbit original command and wrapper rc143/child UNKNOWN are in EXECUTION_orbit_INTERRUPTED.json. No science output was rewritten during recovery.
Source replay used source_snapshot in a fresh process and wrote only replay/base_030.png. It reproduced the actual PNG and six saved layers.
