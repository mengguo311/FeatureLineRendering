# Unit009 exact execution receipts

Commands below were executed serially. Original return codes are retained; expected rejection controls are not successes.

## EXECUTION_baseline.json
Return code: 0; wall seconds: 14.195356533396989
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/density_cli.py preview --asset /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_008/outputs/baseline/asset.json --output /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_009/outputs/baseline
```

## EXECUTION_cold_replay.json
Return code: 0; wall seconds: 14.610366645734757
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/density_cli.py replay --bundle /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_009/outputs/edited --output /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_009/outputs/cold_replay
```

## EXECUTION_cold_request.json
Return code: 0; wall seconds: 0.41548497369512916
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/run_unit009.py cold_request
```

## EXECUTION_cold_reselect.json
Return code: 0; wall seconds: 13.406007593031973
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/density_cli.py reselect --recipe /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_009/cold_request/recipe.json --output /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_009/outputs/cold_reselect
```

## EXECUTION_dev_after.json
Return code: 0; wall seconds: 4.726034501101822
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/density_cli.py edit --asset /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_008/outputs/baseline/asset.json --part stem --density 0.5 --output /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_009/dev_after --azimuths 0
```

## EXECUTION_dev_before.json
Return code: 0; wall seconds: 4.873955767136067
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/density_cli.py preview --asset /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_008/outputs/baseline/asset.json --output /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_009/dev_before --azimuths 0
```

## EXECUTION_edited.json
Return code: 0; wall seconds: 13.45007515605539
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/density_cli.py edit --asset /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_008/outputs/baseline/asset.json --part stem --density 0.5 --output /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_009/outputs/edited
```

## EXECUTION_freeze.json
Return code: 0; wall seconds: 0.4149494180455804
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/run_unit009.py freeze
```

## EXECUTION_history.json
Return code: 0; wall seconds: 0.966605459805578
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/run_unit009.py history
```

## EXECUTION_media.json
Return code: 0; wall seconds: 1.8198359538801014
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/media_unit009.py
```

## EXECUTION_prepare.json
Return code: 1; wall seconds: 0.417780838906765
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/prepare_unit009.py
```

## EXECUTION_prepare_recovered.json
Return code: 0; wall seconds: 0.3648570249788463
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/prepare_unit009.py
```

## EXECUTION_prepare_recovery.json
Return code: 1; wall seconds: 0.31776824686676264
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/prepare_unit009.py
```

## EXECUTION_reject_existing.json
Return code: 1; wall seconds: 0.31756962090730667
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/density_cli.py preview --asset /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_008/outputs/baseline/asset.json --output /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_009/outputs/edited
```

## EXECUTION_reject_historical.json
Return code: 1; wall seconds: 0.315161791164428
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/density_cli.py preview --asset /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_008/outputs/baseline/asset.json --output /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_008/outputs/baseline
```

## EXECUTION_tests.json
Return code: 0; wall seconds: 1.6702549057081342
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/test_density_unit009.py
```

## EXECUTION_validate.json
Return code: 0; wall seconds: 2.426906785927713
```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/validate_unit009.py
```
