# Raster-state → IDs → multi-view clusters → persistent linelets

Frozen before implementation/results; base e0293bd, branch raster-state-candidates.
Primary lego; secondary chair. Every stage writes its own arrays, JSON and panels.
No mesh, mesh-derived caches, extra 2DGS normals, TEST RGB, or GS training.
Official RGB is the previously verified stock renderer. Evidence uses the existing
Gaussian-disc raster-state approximation, **not internal official anisotropic
fragments**. Gaussian normals are vanilla covariance axes, not certified surfaces.

## Audited starting point

`src/render.py` and `src/dt_pull.py` have full-K projection. The separate renderer
in `scripts/poster_repro.py` still uses fx for both coordinates; extract its fragment
logic into a reusable module with full K, remap/top-weight tests, and an old-script
compatibility wrapper. Do not call its TEST-view CLI or rank-max fusion. Stable
weight ranking differs from frontmost-k. Empty-empty comparisons must be zero.
Use float64 for segmented transmittance to avoid global float32 prefix cancellation;
record differences from the historical depth implementation in smoke diagnostics.

Current M1a→linelet→100-step pull→consensus prune→3D chaining is mesh-free when M1a
receives explicit canonical TRAIN indices. Regenerate initial M1a linelets under
this protocol; do not rename an old cache. A is this clean initialization and its
frozen downstream result. Historical clean Lego TRAIN53 image was inspected to
pre-mark three visually useful missing regions: cab roof, track assembly, bucket
lower lip. Pixel boxes (400px, excluding labels) are in manifest; evaluation only.

## Six arms and two comparisons

A = clean M1a. B = A+top-k weighted-overlap candidates. C = A+SH0 Lab candidates.
D = A+top-k+SH0+entropy/margin/depth variance/normal dispersion candidates.
Depth, mean normal and alpha responses are diagnostic channels, not extra D sources.
N1/N2 = A+null versions of D, with the same aggregation, linelet cap and downstream.
Also run B- and C-specific matched null aggregation diagnostics so a union null is
not misrepresented as a quantity-matched top-k null.

N1 independently permutes ID labels per view AFTER legitimate geometric anchoring;
it isolates shared-ID aggregation without making null points trivially off-object.
It cannot alone prove semantic utility. N2 shifts source responses/tangents by a
fixed (47,31) px, then samples within covered pixels. Report actual valid counts.
Matched null statistics use the same accepted observation count per view/source
(minimum available across real/N2), and identical <=3000-cluster budgets. Main real
arms use their full observations; N1/N2 main arms use the matched D comparison.

(i) Raw coverage: all initial finite 3D linelets, before pull/prune/chaining, plus
new-only/source diagnostics. (ii) Downstream: identical sharp TRAIN DT, 100 steps,
prune/chaining/brush/visibility for every arm. Additions may change neighbor graphs;
retain A source labels to report interactions, not assume unchanged A trajectories.

Native drawings and **two separately matched** drawings are mandatory: actual DEV
mean projected visible length, and actual antialiased ink area. Each match selects
one persistent global path subset from a deterministic hash order, never per-frame
2D deletion. This is post-freeze display calibration expressly requested by the
protocol, not candidate tuning. Report both metrics and residual mismatch; matching
one is not claimed to match the other. >3% residual cannot support a matched claim.

## Split, trajectory, fixed parameters

The same 16 explicit canonical TRAIN indices as the clean prior acquisition are
used for primary raster evidence, M1a and pull. DEV validation [2,22,42,62] and the
new orbit stay sealed until paths/parameters are committed. TEST remains unopened.
Camera JSON metadata can be parsed as a whole; only authorized camera objects enter
method calculations. Original GS training split is not independently re-established.

Orbit: 120 unskipped frames, 24fps, full azimuth, elevation **25±8 degrees** fixed
analytically, target median Gaussian centers, radius from TRAIN1. This avoids the
previous 87-degree trajectory without selecting a visually successful path. Fixed
frames 0/30/60/90. Black 1px antialiased ink, white background, no GT overlay.

All numeric thresholds are in MANIFEST.json. k8 is primary; k4 sensitivity is
reported on each TRAIN view, not selected post hoc. Each field has its own physical
operator/threshold and <=600 NMS pixels/view; no rank-max fusion. ID anchors use
weighted centers on the median contributor layer, local dominant-ID bounds, and
<=3px reprojection; median-depth backprojection is diagnostic only. Clusters require
shared IDs, proximity, tangent consistency and >=3 TRAIN views separated by >=15°.
Each cluster produces one bounded linelet; source tags/covariance/support survive.

Secondary: only if D shows clear matched-ink benefit does chair get the full run.
Otherwise four TRAIN views [1,27,53,79] provide a cheap Step1–3 transfer diagnostic
and initial linelet generation only; no full chair downstream or DEV video.

## GO/NO-GO (all key conditions required)

1. G1: at least 2/3 pre-marked structures become recognizable in D raw 3D projection;
   mere higher pixel density, spikes or texture clusters do not count.
2. G2: each claimed source must visibly outperform its quantity-matched null. As an
   auxiliary persistence threshold, supported-cluster yield (>=3 views) must be at
   least 1.5x the stronger null at matched observation counts; this is an effect-size
   check, not a statistical significance claim. N1 failure alone is not evidence.
3. G3: at least two marked structures survive the common downstream into final D.
4. G4: D is visibly richer/readable under actual DEV length AND area matching without
   a Gaussian grid, texture clutter, wrong-depth strokes or persistent penetration.
5. G5: all new runtime ink is attached to frozen 3D paths; full-video inspection must
   not show obvious added flicker/instability. Auxiliary metrics cannot override it.

Failure at G1/G2/G3 still requires remaining RGB/union stages and intermediate
outputs. A top-k failure is reported separately, never concealed by union RGB.
Overall failure stops expansion; do not tune thresholds or raise ink to rescue it.
Human region markings never enter anchoring, aggregation, pull or selection.
