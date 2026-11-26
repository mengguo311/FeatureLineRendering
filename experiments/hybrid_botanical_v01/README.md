# Hybrid Vector-Gaussian Botanical Primitive (`hybrid_botanical_v01`)

Standalone implementation of **Topic 2**: unifying 1D parametric B-spline skeletons & Dual-Arc pointed-tip leaf boundary splines with 2D per-leaf 3DGS Gaussian surfels into a single 3-tier editable botanical representation.

- **Tier 1 (`LathePotPrimitive`)**: Coaxial rotational ceramic pot & soil base.
- **Tier 2 (`BotanicalTreeGraph`)**: 100% root-connected 4-level B-spline branching tree (`5 Primary Trunks -> 50 Secondary Branches -> 189 Rosette Stalks -> 472 Petiole Links = 716 B-splines`) obeying Leonardo da Vinci's pipe-model radius law + Bishop-frame bound bark Gaussians.
- **Tier 3 (`DualArcTrimmedLeafPatch`)**: `472` cambered 2D Gaussian leaf patches coupled to pointed-cusp ($C^0$) / smooth-margin ($C^2$) Dual-Arc Cubic B-Splines regularized by a learned single-plant **Eigen-Leaf PCA Prior**.

## Quick Run (Isolated on Physical GPU 1)

```bash
PY=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python

# Run unit tests
CUDA_VISIBLE_DEVICES=1 $PY -m unittest discover -s tests -v

# Run full 3-tier reconstruction + all 4 flagship applications
CUDA_VISIBLE_DEVICES=1 $PY scripts/run_hybrid_botanical_v01.py
```

## Exported Assets (`outputs/ficus_hybrid_v01/`)
- `hybrid_botanical_completed.ply`: Standard 3DGS `.ply` model (`298,015` Gaussians).
- `hybrid_skeleton_and_dual_arc_leaves.obj`: 3D CAD mesh/wireframe of all `716` branch splines + `472` Dual-Arc leaf loops.
- `hybrid_botanical_primitive.json` & `HYBRID_BOTANICAL_V01_REPORT.json`.
