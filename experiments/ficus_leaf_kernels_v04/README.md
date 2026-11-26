# Ficus Closed-Leaf Spatial Detection, M1+M2 Per-Leaf Kernel Partitioning, Multi-Style & 3D Leaf Deformation

Standalone isolated workspace (`/home/u00134/.gemini/antigravity/scratch/ficus_leaf_kernels_v01`, pinned to physical `GPU 1`) for Ficus 3DGS closed-leaf spatial region delineation, `M1+M2` per-leaf Gaussian kernel extraction (`297,343` kernels across `472` discrete 3D leaves), same-plant multi-style composition (`v03`), and petiole-hinged per-leaf 3D geometric deformation (`v04`).

## Quick Commands (Isolated on Physical GPU 1)

```bash
PY=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python

# 1. Run unit tests (isolation + contour + M1/M2 + v03 multi-style + v04 deformation invariants)
CUDA_VISIBLE_DEVICES=1 $PY -m unittest discover -s tests -v

# 2. Run v03 M1+M2 6-preset gallery & 3 same-plant mixed-style leaf showcases
CUDA_VISIBLE_DEVICES=1 $PY scripts/run_ficus_v03_multistyle.py

# 3. Run v04 petiole-hinged per-leaf 3D geometric deformation, Jacobian ablation & dynamic GIFs
CUDA_VISIBLE_DEVICES=1 $PY scripts/run_ficus_v04_deformation.py
```

## Outputs
- `outputs/ficus_leaf_baseline_v01/`: initial `472`-leaf kernel partition & 3D closed leaf contours.
- `outputs/ficus_multistyle_v03/`: canonical `m1_m2_per_leaf_kernels.npz` (`297,343` kernels), 6-preset galleries & mixed-style plant renders.
- `outputs/ficus_leaf_deform_v04/`: `v04_phenology_deformed_kernels.npz`, `DEFORM_V04_REPORT.json`, 7-mode deformation panels, Jacobian covariance transport ablation zooms, and dynamic 3D breeze/morph animated GIFs.
