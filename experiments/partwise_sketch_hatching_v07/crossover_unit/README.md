# Saved material-layout × carrier embedding crossover

Unit010 separates two saved plane-slicer path families from their embedding on the original or already denoised carrier. `OO` and `CC` preserve unit002 saved paths; `OC` and `CO` move only their face/bary coordinates to the other embedding. Every arm uses the original first-hit occluder. No new smoothing, field solve or parameter scan.

Actual outputs and immutable protocol/input/source/camera locks:
`/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_010`.

The experiment found no whole-object improvement. Both path families lost visible support on the denoised embedding; returning the denoised-generated layout to the original carrier did not reveal a useful hidden visual benefit. This is a limited response decomposition, not physical surface truth or a comparison of two generator algorithms.

## Replay

Use the existing read-only interpreter and a nonexistent output directory within unit010:

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B /home/u00134/3dgs_line/partwise_sketch_hatching_gaussian_link_v07/experiments/partwise_sketch_hatching_v07/crossover_unit/replay_crossover.py --out /mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_010/user_replay_001 --view orbit_241_24_5.3
```

The new-process replay rerasterizes all four proxy-ink arms and restores 45 arrays exactly at the exposed rear view. Original-GS source/paper/S are verified cached layers, not a second cold GS render. Dependencies include NumPy2.2.6, SciPy1.15.3, Open3D0.20.0 and Pillow12.2.0. Runtime fixes two-core affinity, one numerical thread, empty CUDA visibility and unit010-only output. It requires the frozen local source paths and old read-only data; it is not a standalone portable package.

## Verification and limits

Expected missing-module RED is preserved. Four GREEN groups exercise independent unequal path families, material roundtrip, analytic flat/fold/curved shared-edge carriers, topology/label rejection and a true same-label foreground occluder. The audit checks saved diagonals, independent barycentric coordinate sums, source-row/weight locks and actual PNG composition. The material visibility diagnosis pairs only within each layout family.

All original PLY rows, geometry/fullSH/opacity/order and selection/paper/ink weights remain fixed. New stroke IDs refer to immediate saved layouts, not Gaussian ownership. The 756 new paths have proxy anchors, without per-path original-Gaussian certification. Six distinct evaluation cameras are exposed; three rear frames do not certify temporal stability. Prior negative results remain unchanged.
