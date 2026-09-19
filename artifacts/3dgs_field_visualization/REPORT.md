# Frozen vanilla 3DGS posterior-field visualization

## Scope

Scenes: Lego, Chair, Drums, Ficus. Each scene uses the independently trained `seed_1729`, iteration-30000 vanilla 3DGS checkpoint. No mesh, 2DGS, SDF, depth supervision, or retraining is used.

## Definitions and caveats

Vanilla 3DGS has no calibrated surface or stored surface normal. The visualizations therefore separate observable parameters from heuristic proxies:

- **Candidate normal:** eigen-axis of the smallest Gaussian covariance scale. It is axial (`n` and `-n` are identical), not an oriented normal.
- **Flattening:** `1 - s_min / s_mid`; high values mean a splat is disk-like, not that it lies on a surface.
- **Local center-cloud planarity:** `(lambda_2 - lambda_3) / lambda_1` from the covariance of the 24 nearest Gaussian centers.
- **Axis agreement:** `|n_cov dot n_PCA|`, comparing the Gaussian's smallest axis with the local center-cloud PCA normal.
- **Surface-likeness proxy:** geometric mean of flattening, local planarity, and axis agreement. It is a diagnostic, not a probability.
- **Mixture slice:** `sum_i alpha_i exp(-0.5 d_i^T Sigma_i^-1 d_i)` on the global PCA mid-plane. It is an opacity-weighted posterior occupancy proxy, not an SDF or true density.

Every atlas uses a common 0–1 color range within each scalar definition. The view is an orthographic projection in each scene's global PCA frame, with all sampled means shown and no visibility filtering.

## Main observation

The frozen 3DGS posterior is not a single coherent surface field. It contains strong object-shaped organization, but this organization differs sharply among parameter channels:

1. Gaussian flattening is generally high, while local center-cloud planarity is only modest.
2. Candidate covariance axes often agree with local PCA normals, but a substantial minority is incoherent.
3. The Gaussian-mixture cross-sections contain isolated blobs, long filaments, holes, and scene-specific large-splat bands rather than a stable zero-level surface.
4. Surface-like regions are easiest to see on leaf sheets and major object boundaries, while texture-heavy interiors and thin supports remain noisy or multi-layered.

## Quantitative medians

| Scene | Gaussians | Opacity | Flattening | Local planarity | Axis agreement | Surface proxy |
|---|---:|---:|---:|---:|---:|---:|
| Lego | 310,475 | 0.523 | 0.956 | 0.289 | 0.789 | 0.528 |
| Chair | 256,690 | 0.248 | 0.856 | 0.303 | 0.748 | 0.496 |
| Drums | 360,012 | 0.206 | 0.919 | 0.303 | 0.817 | 0.531 |
| Ficus | 284,835 | 0.049 | 0.999 | 0.386 | 0.973 | 0.700 |

The mismatch between very high flattening and modest local planarity is central: individual Gaussians are frequently flat, but their centers do not necessarily sample one smooth sheet.

## Scene observations

### Lego

The object silhouette is visible in every channel, but covariance-axis colors form small orientation patches rather than a globally smooth normal field. The base and large outer panels have relatively coherent axis agreement; cabin/interior and tread regions remain mixed. The mixture slice contains dense islands around the body and base plus long thin extensions from large anisotropic splats.

### Chair

The outer shell is recognizable, but interior texture and thin structures have mixed orientation and lower surface-likeness. The bright vertical band in the mixture slice is not a plotting bug: selected splats include scales up to `0.171`, versus a selected-splat median maximum scale of `0.0224`, and multiple high-opacity, very elongated Gaussians intersect the slice plane. This is exactly the kind of posterior artifact that prevents interpreting the mixture as a clean surface.

### Drums

The main rounded body has more coherent candidate-axis orientation than its thin supports and textured regions. Local planarity remains moderate despite high Gaussian flattening. The mixture slice is fragmented into several dense islands and filamentary structures rather than one continuous shell.

### Ficus

Leaves and major plant sheets show the strongest flattening and axis/PCA agreement of all four scenes. However, opacity is extremely low for most Gaussians (median `0.049`) and the pot/stem region dominates the mixture slice. High orientation agreement therefore does not imply uniformly strong rendered support.

## Reproducibility

- Script: `scripts/render_3dgs_fields.py`
- Geometry/field functions: `src/field_visualization.py`
- Tests: `tests/test_field_visualization.py`
- Outputs: `out/3dgs_field_visualization/`
- Each scene samples 24,000 Gaussian means deterministically.
- Each mixture slice uses the 1,500 highest-relevance splats intersecting the PCA mid-plane.
- Raw sampled fields and slice arrays are saved as compressed NPZ files.
