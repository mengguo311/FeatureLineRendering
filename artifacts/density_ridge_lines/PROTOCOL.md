# Preregistered density-ridge feasibility protocol — version 1

Frozen before implementing or viewing any experiment masks. Base commit:
`bcf8260ac194191a9d9c1b28e21d3c82a5c3f0a0`, branch `density-ridge-lines`.
The protocol SHA256 is recorded separately before implementation. No scientific
parameter changes after scene results; deviations must be a separate exploratory
appendix and cannot rescue the primary decision. Layout-only changes are allowed.

## Scope and inputs

This is a **2D orthographic PCA-projection diagnostic**, with all depths superposed
and no visibility filtering. It cannot establish multi-view or 3D persistence,
physical surfaces, calibrated normals, or persistent 3D strokes. Only frozen
vanilla-3DGS PLY attributes are allowed. No images, mesh, 2DGS, SDF, learned detector,
or retraining. Fixed scene order: lego, chair, drums, ficus. Each exact input is:
`out/multiscene_foundation/training/{scene}/seed_1729/checkpoints/point_cloud/iteration_30000/point_cloud.ply`.
Record SHA256 and vertex count for each. Preserve all previous field/density artifacts.

## Frame, population and grid

Reuse `scripts.render_3dgs_fields.robust_frame`, `deterministic_sample`, and
`limits_xy` exactly: frame from centers with opacity at least its 25th percentile;
median center, covariance about that center, descending PCA eigenvectors with
existing handedness convention. Crop from the old 24,000-index sample, seed
`1701 + sum(ord(c) for c in scene)`: 0.5–99.5 percentile bounds plus 3% margins.
All finite PLY centers contribute to KDE (no opacity culling or score sampling).
Reject nonfinite/invalid inputs instead of silently dropping them. Local 24-NN
metrics are evaluated for every center in batches of 16,384 against the complete
cloud, using the existing mathematically tested field functions; self is included
in the 24 neighbors, matching the old atlas.

Grid is pixel-centered, with W=ceil(640*span_x/max(span_x,span_y)),
H=ceil(640*span_y/max(span_x,span_y)), exact crop boundaries. Pixel pitch used for
filters is the grid metric (near-isotropic, rounding discrepancy recorded).
Pad by 40 pixels per side for KDE; contributions outside this padded rectangle
have zero effect under the finite raster approximation. Record selected indices
and counts; these are spatial, never score-selected. Do not reflect edge mass.

## Adaptive continuous fields

Float64 arithmetic. Bilinear splat each center with unit count mass into the
padded grid. Pilot density is Gaussian smoothing sigma=4 px, truncate=4, zero
boundary. Sample the pilot bilinearly at centers; g is the geometric mean of
positive samples. Bandwidth h=clip(2*sqrt(g/max(pilot,1e-15)),1,4) px, quantized to
nearest log-distance member of [1,sqrt(2),2,sqrt(8),4]. For each bandwidth, smooth
its bilinear count and attribute sums with the same normalized discrete Gaussian
kernel (truncate=4, zero boundary), then sum. D=sum K is the retained count-density
denominator in expected centers/pixel, N_a=sum K*a, A=N_a/max(D,1e-15).
Save D, all N_a, A, pilot, bandwidth assignments, support and confidence.
This is a center-cloud KDE, not the learned covariance-mixture density PDF.

Confidence C=D/(D+0.25). Support S is D>=0.05, eroded by a radius-3 Euclidean disk
(including zero outside crop). d99 is the pooled 99th percentile of D>0 over all
four cropped grids. Density factor Q=clip(log1p(D)/log1p(d99),0,1).
Shared coupling W=C*sqrt(Q). Preserve support without masking continuous fields.

Fixed channel order and definitions:
1. **SH-DC color:** a=clip(0.5+0.28209479177387814*f_dc,0,1). Normalized KDE RGB.
   E_color=W*sqrt(sum over RGB and x,y of (Gaussian derivative at sigma=1 of A)^2).
2. **Axial orientation:** normalize covariance smallest-axis n, a=n*n^T (all 9
   entries, including symmetric duplicates). This is invariant to independent
   sign flips. T=N/D; coherence c=clip((3*lambda_max(T)-1)/2,0,1).
   E_axis=W*sqrt(sum over all tensor entries and x,y of (dT)^2
   +0.25*sum over x,y of (dc)^2), derivatives sigma=1.
   Display sqrt(diag(T)) as XYZ RGB, with coherence saved separately.
3. **Opacity:** a=sigmoid(opacity logit).
4. **Flattening:** a=1-s_min/s_mid from exp(log-scales).
5. **24-NN planarity:** a=(lambda_2-lambda_3)/max(lambda_1,1e-20), descending local
   center covariance eigenvalues, clipped to [0,1].
6. **Axis/PCA agreement:** a=abs(dot(n_cov,n_localPCA)).
7. **Surface proxy:** a=cuberoot(flattening*planarity*agreement), constructed per
   center BEFORE KDE.
For scalar channels detector field F=W*A, explicitly combining density with the
normalized attribute. For color/axis F=clip(E/e99,0,1), where e99 is the channel's
pooled 99th percentile of positive supported E. No per-scene contrast normalization.
Save original normalized attributes, RGB/tensor, energy, and detector field F.

## Detector and baseline

Selected family: scale-normalized positive Hessian ridge response, inspired by
Frangi's eigenvalue anisotropy criterion, not a claim to reproduce full Frangi or
Steger. Reference: https://doi.org/10.1007/BFb0056195 . Scales sigma=[1.5,2.5,4] px
for all classes/scenes. H=sigma^2 * Gaussian second derivatives of F; eigenvalues
ordered by absolute magnitude |l_small|<=|l_large|. At each scale:
R=abs(l_large)*exp(-0.5*(abs(l_small)/(abs(l_large)*0.5+1e-15))^2), only where
l_large<0 and abs(l_small)/max(abs(l_large),1e-15)<0.5. Otherwise zero.
Save max response and winning scale. For ridge seed selection, nonmaximum-suppress
the response at each scale along its l_large eigenvector, sampling +/-1 pixel
bilinearly; retain >= both and > at least one. Take max of suppressed responses.
Broaden seeds with radius-1 disk maximum filter (nominal 3-pixel band). Clip
selection scores to S. Crossings/merged adjacent bands can exceed nominal width.

Baseline is a simple Gaussian-gradient energy (not Canny of a scatterplot).
For scalar channels B=norm(gradient F at sigma=1). For color/axis B=their normalized
energy F, so the baseline tests discontinuity without Hessian ridge selection.
Broaden B with the same radius-1 disk maximum filter, clipped to S. The baseline
may form wider patches: quantify this and show it rather than forcing thin edges.

Selection per channel pools pixels from all four scenes in the fixed order and
row-major index order. Budget=floor(0.06*sum supported pixels); take the smaller of
budget and positive candidate counts in either method. Rank descending score,
stable tie-break by scene then pixel index. Select exactly K pixels in each method.
These are the raw masks. Thresholds are pooled, never optimized per scene; a scene
may receive more or less ink. Report actual per-scene ink and pooled thresholds.

Cleanup removes 8-connected components of area <12 px in BOTH methods. No opening,
closing, bridging, hole filling, or skeleton-based geometric repair. Save these
cleaned-unmatched masks. For final matched masks let Kclean be the smaller pooled
remaining area; trim the excess method by its original score within its cleaned
mask, same stable ranking. No cleanup after trimming. Save raw, cleaned-unmatched,
and final cleaned/matched masks so trimming/cleanup cannot conceal fragmentation.
Exact ink matching is POOLED per channel; per-scene mismatch is explicitly reported.

## Metrics and frozen decisions

Report every raw/cleaned-unmatched/final method/scene/channel: pixel count, ink/full
canvas, ink/support, support overlap, 8-connected component count, fragment count
(components whose skeleton has <24 pixels), long-component ink fraction (area in
components with >=24 skeleton pixels / mask area), skeleton length, and median
local width 2*distance-to-background sampled at skeleton pixels. Empty metrics=0.
These are topology proxies, not correctness. Also report retention through cleanup,
pooled equality, density/source correlations, and exact parameters.

A scene/channel MACHINE PASS needs: final ink/support in [0.015,0.12], support
overlap>=0.98, long-component fraction>=0.60, at most 80 fragments per 10,000
supported pixels, >=0.65 raw ink retained, and long-component fraction >= baseline
minus 0.05. A channel MACHINE GO requires >=3/4 scene passes and median
(primary long fraction - baseline long fraction)>=0.05. MACHINE PIVOT requires
>=2/4 passes without GO; otherwise MACHINE STOP. Global MACHINE GO requires >=2
channel GOs; PIVOT requires >=1 GO or >=2 PIVOT channels; otherwise STOP.

Visual review of each of 28 scene/channel results uses the full atlas and summary,
never only favorable crops. Label:
- PASS: several coherent, recognizable object-related broad bands, limited stipple,
  with a useful simplification versus the ink-matched gradient baseline.
- PARTIAL: some meaningful bands but substantial fragmentation, density domination,
  merged layers, blob rims, or no clear baseline advantage.
- FAIL: predominantly flecks/blobs, unrecognizable geometry, or misleading boundaries.
Channel VISUAL GO requires >=3 PASS and zero FAIL; PIVOT requires >=2 PASS/PARTIAL;
otherwise STOP. Final channel GO requires BOTH machine and visual GO; PIVOT if not
GO and either machine or visual is GO/PIVOT; otherwise STOP. Global final GO needs
>=2 final GO channels; PIVOT if any channel is GO/PIVOT; otherwise STOP.
Only a final GO channel justifies proposing a later 3D ridge-tracing feasibility
experiment. PIVOT may motivate further 2D controls, not a persistence claim.
Earliest failure (field mixing, ridge response, selection, cleanup, or baseline
comparison) must be recorded for every scene/channel. Visual verdicts are subjective
model inspection, not a blinded human study or ground-truth accuracy evaluation.

## Deliverables and checks

Canonical `out/density_ridge_lines/`; curated PNG/JSON/report/protocol in
`artifacts/density_ridge_lines/`. Per-scene atlas seven columns and five rows:
source normalized continuous field, density-coupled detector input, ridge response,
final broad-line overlay, matched baseline overlay. Summary four scenes by seven
channels. Include a raw-versus-clean audit contact sheet per scene if necessary to
inspect cleanup. Shared channel display scales, common crop; titles explicitly say
2D orthographic PCA, no demonstrated 3D persistence. Raw masks remain in NPZ.

Before implementation write tests for KDE constant-field normalization/mass,
independent axial sign invariance through tensor KDE, broad curved ridges vs blobs
and seeded noise, deterministic pooled exact-ink matching including ties and empty
inputs, and cleanup preserving broad curves. Run new and existing field/density
tests, full unittest discovery, decode all PNGs, validate all NPZ arrays, and run
the entire extraction/rendering again from PLY with bytewise SHA256 comparisons.
Record environment, commands, source/output hashes, protocol hash and preservation
hashes. No commit or push. Write final operational report to
`/home/u00134/codex_astra_density_ridge_report.md`.
