# unit003 reproduction

Branch: partwise-sketch-hatching-p1-v02. Frozen source commit: 8d5214bddedcfee5fbee3e4542f3ca333d5c7849.
Output: /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_003. Source/input identities: SOURCE_LOCK.json. Protocol: PROTOCOL.json.
The original unit is sealed after reporting; do not run producers against sealed/historical outputs. Replay requires a newly authorized output directory and an explicit adapted runner. The original commands below are exact recorded child commands, not instructions to overwrite this unit.

All commands were wrapped by receipt_unit003.py under taskset -c0,1; CUDA disabled, numeric libraries1 thread, ffmpeg1 thread, timeout590s. The wrapper records UTC, original returncode, command, cwd and stdout SHA. Freeze follows successful tests/DEV and precedes all diagnostic still/orbit evaluations. Protocol's only candidate is75 of150 base seed pairs.

prepare: rc=0, wall=2.976s

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/run_unit003.py prepare
```

tests: rc=0, wall=2.975s

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/test_density_unit003.py
```

dev: rc=0, wall=9.946s

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/run_unit003.py dev
```

freeze: rc=0, wall=0.365s

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/run_unit003.py freeze
```

stills: rc=0, wall=27.303s

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/run_unit003.py stills
```

orbit: rc=0, wall=78.064s

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/run_unit003.py orbit
```

media: rc=0, wall=1.218s

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/run_unit003.py media
```

cold_replay: rc=0, wall=10.700s

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_003/source_snapshot/experiments/partwise_sketch_hatching_v02/run_unit003.py replay
```

validation: rc=0, wall=7.340s

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/validate_unit003.py
```

Actual outputs: videos/orbit.mkv and videos/edit.mkv (24frames each), figures/full_lamp_comparison.png, figures/base_comparison.png, figures/orbit_all_frames.png. Independent validator reconstructs masks and selection, compares every decoded frame, and saves METRICS.json/INDEPENDENT_VALIDATION.json. Cold replay used source_snapshot code in a fresh process. Preserve all historical NO_GO and143/UNKNOWN records.
