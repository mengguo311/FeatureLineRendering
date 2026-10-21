# Actual unit005 commands and return codes

Working directory: `/home/u00134/3dgs_line/partwise_sketch_hatching_p1_v02`

Each child inherited CPU affinity0,1, numeric threads1, CUDA disabled and the required task scratch TMPDIR. Raw stdout/stderr are retained outside the science manifest and SHA-bound by receipts.

## prepare

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/run_unit005.py prepare
```
Return code: 0; wall seconds: 0.365323

## freeze

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/run_unit005.py freeze
```
Return code: 0; wall seconds: 0.365027

## tests

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/test_asset_cli_unit005.py
```
Return code: 0; wall seconds: 1.467316

## baseline

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/asset_cli.py preview --asset /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_005/inputs/unit004_diagnostic_preview.asset.json --output /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_005/outputs/baseline
```
Return code: 0; wall seconds: 14.904425

## edited

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/asset_cli.py edit --asset /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_005/inputs/unit004_diagnostic_preview.asset.json --output /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_005/outputs/edited --part shade --width 1.5
```
Return code: 0; wall seconds: 14.194737

## cold_replay

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_005/source_snapshot/experiments/partwise_sketch_hatching_v02/asset_cli.py replay --bundle /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_005/outputs/edited --output /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_005/outputs/cold_replay
```
Return code: 0; wall seconds: 13.109855

## named_unit003_baseline

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/asset_cli.py preview --asset /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_005/inputs/unit003_baseline.asset.json --output /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_005/outputs/named_unit003_baseline --azimuths 30
```
Return code: 0; wall seconds: 4.879823

## validation

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/validate_unit005.py
```
Return code: 0; wall seconds: 1.920852

## media

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/run_unit005.py media
```
Return code: 0; wall seconds: 1.624641

## history

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/run_unit005.py history
```
Return code: 0; wall seconds: 0.515477
