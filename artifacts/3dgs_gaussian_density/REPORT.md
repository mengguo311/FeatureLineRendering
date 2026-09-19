# Frozen vanilla 3DGS Gaussian-kernel density

Lego, chair, drums and ficus use the existing seed_1729 / iteration_30000 PLYs. Only centers, log-scales, wxyz quaternions and opacity logits are read; no images, mesh, 2DGS, SDF or retraining.

## Definitions and interpretation

- `rho_occ(x) = sum alpha_i exp(-d_i^2/2)`: renderer-style **unnormalized kernel sum**, dimensionless and potentially greater than one. It is not renderer transmittance/compositing or occupancy probability.
- `rho_pdf(x) = sum alpha_i exp(-d_i^2/2) / ((2*pi)^(3/2) prod_j s_ij)`: **determinant-normalized Gaussian PDF mixture**, in inverse scene-coordinate volume. Weights are not divided by sum(alpha), so its whole-space integral is sum(alpha), not one.
- Both are **posterior proxies, not physical density or surfaces**. Separate scene coordinate systems are not physically calibrated; shared colors compare numerical proxies only.

## Planes, numerical method and truncation

An opacity-weighted PCA uses all centers. The first two eigenvector signs are canonicalized by their largest-magnitude component; axis 3 is their cross product. Offsets are inverse weighted-ECDF q25/q50/q75 of center coordinates along axis 3. Each axis-1/2 ROI uses weighted q0.005..q0.995 plus 5% span padding. The same ROI/grid is used for all three planes; tails and centers outside the ROI may still contribute inside it.

Every kernel is considered, in source PLY order. A radius-12 Mahalanobis ellipsoid is intersected with each plane. A conservative conditional bounding rectangle restricts its raster footprint; individual samples beyond radius 12 are zeroed. There is **no top-N cap**. These are explicitly **tail-truncated point samples**, not exact full infinite-support sums. The per-point absolute tail bounds are exp(-72) times sum(alpha) for occupancy and sum(PDF peak amplitudes) for PDF. These mathematical bounds exclude floating-point roundoff. Direct rotation/scale whitening uses all three learned axes, without covariance pseudoinversion, scale regularization or an exponent floor. All-kernel, untruncated evaluations at both field maxima independently check each slice (relative differences recorded in JSON). Values below the absolute tail bound have no guaranteed relative accuracy; the far-left distribution tails describe the truncated field. The PDF display floor (1e-6) exceeds every reported tail bound.

The 768x768 grids do not resolve the smallest learned scales (~1e-8). Kernel hit counts and zero fractions expose this limitation. Point-sampled histograms/CDFs describe equally weighted locations in these finite 2D ROIs, **not 3D volume distributions**, pixel-integrated densities or resolution-converged peaks. Zero entries are truncation/numerical zeros, not proven empty space. No claim of resolution convergence is made; extrema of the continuous field can be much larger.

## Figures and display ranges

Each 4320x3600 atlas contains three linear-occupancy slices, three log10-PDF slices, an occupancy log-value histogram, a PDF CDF including the zero atom, and a sampling/extreme-kernel audit. Atlas color limits pool the three planes of that scene; distribution plots use unfloored raw positive values. The 5280x3740 comparison uses **one identical occupancy Normalize and one identical log-PDF Normalize** across all scenes/planes.

Shared occupancy limits: [0.0, 5.4245818707040705]; shared log10-PDF limits: [-6.0, 6.080588393024247]. Upper limits are p99.8 of all 12 grids pooled with equal sample weight. PDF display floor is 1e-6; zeros and lower positive values share its floor color. Upper saturation and lower-floor fractions are in JSON. There is no per-panel rescaling in the comparison. Nearest-neighbor display avoids invented smoothness.

## Kernel and sampling audit

| Scene | Kernels | Opacity median | Min scale | Max scale | Max axis ratio | PDF tail bound |
|---|---:|---:|---:|---:|---:|---:|
| lego | 310,475 | 0.5147 | 1.43e-08 | 0.338 | 1.12e+07 | 2.16e-15 |
| chair | 256,690 | 0.2514 | 1.22e-08 | 0.278 | 1.96e+06 | 9.95e-13 |
| drums | 360,012 | 0.2003 | 1.44e-08 | 0.166 | 2.59e+06 | 2.51e-14 |
| ficus | 284,835 | 0.0491 | 1.57e-08 | 0.242 | 9.65e+05 | 1.24e-16 |

| Scene / plane | Plane / grid-bbox / hit kernels | Occupancy max | Positive PDF log10 range | Zero % |
|---|---:|---:|---:|---:|
| lego / Lower (q25) | 37,645 / 30,776 / 23,737 | 18.37 | -31.46 .. 9.96 | 12.82 |
| lego / Middle (q50) | 33,186 / 26,114 / 19,311 | 11.24 | -31.46 .. 8.61 | 8.77 |
| lego / Upper (q75) | 34,179 / 27,254 / 21,080 | 9.604 | -31.46 .. 9.43 | 7.07 |
| chair / Lower (q25) | 46,786 / 25,907 / 21,257 | 4.772 | -31.38 .. 9.73 | 9.63 |
| chair / Middle (q50) | 49,738 / 28,383 / 23,292 | 8.84 | -31.61 .. 9.38 | 6.05 |
| chair / Upper (q75) | 27,420 / 17,656 / 14,776 | 8.555 | -31.62 .. 9.00 | 12.30 |
| drums / Lower (q25) | 48,901 / 32,189 / 22,726 | 3.259 | -31.19 .. 8.99 | 39.04 |
| drums / Middle (q50) | 60,108 / 42,919 / 32,629 | 6.296 | -31.19 .. 9.70 | 32.49 |
| drums / Upper (q75) | 39,570 / 29,792 / 23,520 | 9.026 | -31.19 .. 9.02 | 33.33 |
| ficus / Lower (q25) | 55,193 / 51,848 / 26,770 | 6.424 | -30.46 .. 9.04 | 51.46 |
| ficus / Middle (q50) | 76,891 / 72,044 / 38,198 | 7.19 | -30.48 .. 9.10 | 44.43 |
| ficus / Upper (q75) | 66,607 / 62,594 / 31,483 | 10.56 | -30.43 .. 8.54 | 46.68 |

## Extreme contributors and apparent bands

Broad or narrow bands are plausible learned-kernel features: the saved PLYs contain extremely anisotropic kernels. They are not sufficient evidence of a surface. The following audit identifies the largest middle-plane contributor by summed occupancy samples (a discrete ROI statistic), and the strongest contributor at the PDF grid maximum. Full top-eight lists for both definitions at each maximum and by grid sum, plus global scale/anisotropy/PDF-peak extremes, include source vertex IDs, centers, rotations, scales and opacities in `density_statistics.json`. The middle-plane maximum-sum occupancy column is also checked at five positions (row occupancy-weighted q10/q30/q50/q70/q90) using an independent all-kernel sum. This checks the sampled band against the checkpoint parameters without assuming that a single extreme kernel explains it.

- **lego**: middle-plane occupancy-sum leader ID 3502, 1.61% of sampled sum, alpha=0.9792, local scales=[0.04032166137771707, 0.07521242603930284, 0.05718471974877418], axis ratio=1.87. PDF-maximum leader ID 127623 supplies 99.9976% of that sample (alpha=0.6828, scales=[0.0037410679826584818, 1.4888839066416723e-05, 7.192809926190721e-05], axis ratio=251). The five-point band check at PCA x=0.6803 has maximum relative reference difference 6.79e-15 across both fields. 34,716 kernels have minimum scale below 1e-6; 33,731 have axis ratio above 10,000.
- **chair**: middle-plane occupancy-sum leader ID 4389, 2.57% of sampled sum, alpha=0.9999, local scales=[0.06954819978148048, 0.016878049743565545, 0.03553694136146354], axis ratio=4.12. PDF-maximum leader ID 188540 supplies 99.9976% of that sample (alpha=0.6163, scales=[0.011163377653878467, 3.004875860000295e-05, 3.852417372944978e-05], axis ratio=372). The five-point band check at PCA x=-0.6446 has maximum relative reference difference 7.67e-15 across both fields. 78,404 kernels have minimum scale below 1e-6; 40,127 have axis ratio above 10,000.
- **drums**: middle-plane occupancy-sum leader ID 1424, 9.46% of sampled sum, alpha=0.2625, local scales=[0.06375341579155062, 0.05015008109753008, 0.018285977503464296], axis ratio=3.49. PDF-maximum leader ID 168123 supplies 99.9992% of that sample (alpha=0.6124, scales=[1.1484243334434043e-05, 0.005879478494762553, 2.361813311640572e-05], axis ratio=512). The five-point band check at PCA x=-0.0216 has maximum relative reference difference 1e-13 across both fields. 38,306 kernels have minimum scale below 1e-6; 33,640 have axis ratio above 10,000.
- **ficus**: middle-plane occupancy-sum leader ID 8, 3.05% of sampled sum, alpha=0.9963, local scales=[0.03764660861592971, 0.04009613840889182, 0.05226245461098983], axis ratio=1.39. PDF-maximum leader ID 11122 supplies 99.9983% of that sample (alpha=0.9996, scales=[0.00835002694776028, 0.005154155660468904, 2.5673597147564654e-07], axis ratio=3.25e+04). The five-point band check at PCA x=-0.9992 has maximum relative reference difference 3.86e-14 across both fields. 109,260 kernels have minimum scale below 1e-6; 91,052 have axis ratio above 10,000.

## Reproduction and files

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /home/u00134/bin/miniconda3/envs/scgs/bin/python -m scripts.render_3dgs_gaussian_density
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /home/u00134/bin/miniconda3/envs/scgs/bin/python -m scripts.verify_3dgs_gaussian_density
```

`*_density_grids.npz` stores the raw float64 occupancy/PDF arrays, u/v, frame, offsets/origins, candidate IDs, per-kernel hit counts and grid sums. `density_statistics.json` stores source hashes, software versions, definitions, numerical parameters, summaries, display limits and extreme contributors. Raw NPZs stay in ignored `out/3dgs_gaussian_density/`; curated PNGs, statistics and this report are copied to `artifacts/3dgs_gaussian_density/`. `verification.json` records test/decode/rerun checks after generation. No commit or push is performed.
