# Unit010 exact execution receipts

All compute stages run serially on CPU. Negative controls retain rc1; the outer batch interruption143 is retained separately.

## EXECUTION_baseline.json
Return code: 0; wall seconds: 19.158538084942847
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/length_cli.py preview --asset /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_010/inputs/asset.json --output /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_010/outputs/baseline
```

## EXECUTION_cold_regenerate.json
Return code: 0; wall seconds: 13.947283999994397
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/length_cli.py regenerate --recipe /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_010/cold_request/recipe.json --output /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_010/outputs/cold_regenerate
```

## EXECUTION_cold_replay.json
Return code: 0; wall seconds: 17.057032207027078
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/length_cli.py replay --bundle /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_010/outputs/edited --output /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_010/outputs/cold_replay
```

## EXECUTION_cold_request.json
Return code: 0; wall seconds: 0.417626507114619
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/run_unit010.py cold_request
```

## EXECUTION_dev.json
Return code: 0; wall seconds: 15.213360926136374
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/run_unit010.py dev
```

## EXECUTION_edited.json
Return code: 0; wall seconds: 14.34912966331467
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/length_cli.py edit --asset /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_010/inputs/asset.json --part base --length-world 0.12 --output /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_010/outputs/edited
```

## EXECUTION_freeze.json
Return code: 0; wall seconds: 0.6672465959563851
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/run_unit010.py freeze
```

## EXECUTION_history.json
Return code: 0; wall seconds: 0.5657914290204644
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/run_unit010.py history
```

## EXECUTION_layers.json
Return code: 0; wall seconds: 38.03214608458802
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/run_unit010.py layers
```

## EXECUTION_media.json
Return code: 0; wall seconds: 2.7723937947303057
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/run_unit010.py media
```

## EXECUTION_no_edit.json
Return code: 0; wall seconds: 5.527744052931666
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/length_cli.py edit --asset /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_010/inputs/asset.json --part base --length-world 0.18 --output /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_010/outputs/no_edit --azimuths 30
```

## EXECUTION_orbit.json
Return code: 0; wall seconds: 76.1594914002344
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/run_unit010.py orbit
```

## EXECUTION_prepare.json
Return code: 0; wall seconds: 0.3150061327032745
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/prepare_unit010.py
```

## EXECUTION_reject_existing.json
Return code: 1; wall seconds: 0.36525189876556396
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/length_cli.py preview --asset /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_010/inputs/asset.json --output /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_010/outputs/edited
```

## EXECUTION_reject_historical.json
Return code: 1; wall seconds: 0.3653550297021866
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/length_cli.py preview --asset /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_010/inputs/asset.json --output /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_009/forbidden_unit010_write
```

## EXECUTION_tests.json
Return code: 0; wall seconds: 3.129049082286656
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/test_length_unit010.py
```

## EXECUTION_validate.json
Return code: 0; wall seconds: 12.816630593966693
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/validate_unit010.py
```

## EXECUTION_zoom.json
Return code: 0; wall seconds: 60.516312952153385
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/run_unit010.py zoom
```

The final handoff script only summarizes saved validated outputs. Sealing runs after the report/source commit; runtime stdout is outside the science manifest.