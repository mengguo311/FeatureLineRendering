# Universal Scene-Agnostic Botanical 3DGS Pipeline (`universal_botanical_v01`)

Generalizable, **zero-manual-annotation, zero-scene-hardcoding** 3D Gaussian Splatting decomposition, adaptive multi-family support discovery, vein-immune curved-lamina organ partitioning, and silhouette-preserving spline hybrid representation tested across **5 diverse plant species & support regimes**:

1. **`Ficus`** (NeRF-Synthetic): Axisymmetric ribbed ceramic pot + 5 woody trunks + narrow acuminate green leaflets.
2. **`Brassica`** (sPlant / Canola): Potless herbaceous plant + green cylindrical stalks + broad, veined, ruffled cabbage/canola blades.
3. **`Bonsai`** (Mip-NeRF 360): Slatted wooden stand + black rectangular planting tray + gnarled trunk + pink ornamental blossom clusters.
4. **`Garden`** (Mip-NeRF 360): Glossy tabletop apron + non-axisymmetric clay vessel + dried tan palm fronds & seed pods.
5. **`Flowers`** (Mip-NeRF 360): Open outdoor flowerbed carpet + upright bronze/burgundy broad Canna blades & orange flower stalks.

## Quick Commands

```bash
PY=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python

# 1. Run unit tests (write-isolation, periodic B-spline, 3-family support, 0.0000 wind-leak invariant)
CUDA_VISIBLE_DEVICES=1 $PY -W error::SyntaxWarning -m unittest discover -s tests -v

# 2. Run full 5-scene zero-annotation reconstruction, held-out benchmark & visual panels
CUDA_VISIBLE_DEVICES=1 $PY scripts/run_universal_5scene_benchmark.py

# 3. Run cross-species 6-preset stylization, same-plant mosaic, 3D manifold deformation, pruning & sprouting showcase
CUDA_VISIBLE_DEVICES=1 $PY scripts/run_cross_species_editing_showcase.py

# 4. Run 12-style avant-garde 3DGS-native NPR anthology (all 12 styles on ONE plant across all 5 scenes)
CUDA_VISIBLE_DEVICES=1 $PY scripts/run_12style_npr_anthology.py
```
