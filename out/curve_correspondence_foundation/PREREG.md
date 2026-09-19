# Explicit curve correspondence foundation preregistration

This is a new, non-learning correspondence experiment, informed by the corrected
local-pixel failure. It is not a repair or retuning of that experiment. Starting
HEAD: `42158159a037fee1b14c5ba2d8a7e5271ec1bc36`; branch:
`curve-correspondence-foundation`. This document, config.json, literature memo,
and input inventory must be committed and pushed before any new scene extraction,
match, or fit is executed. Synthetic tests are permitted before scene execution.
All numerical choices below are investigator-defined pilot gates, not guarantees
from the cited literature. No threshold changes after outputs, C, or DEV.

## Hypothesis and exact formulation

H_C: a useful, nontrivial subset of static image curves admits sufficiently certain
cross-view identities to reconstruct fixed 3D curves that predict held-out images,
survive qualified GS changes, and reject correspondence nulls. The sole formulation
is **unique epipolar-intersection alignment of ordered Canny segments, mutual
appearance-margin matching, closed three-view track graphs, and bounded robust
polyline bundle adjustment**. No neural field, learned feature network, surface,
mesh, old local depth search, gap completion, or final stroke module is used.

1. Use exactly the inherited native800/area400 reference convention, full K and
   pixel centers. White-composite reference RGB; inherited grayscale Gaussian
   sigma 1.2, Canny 50/120, aperture 3, L2gradient false. Trace the 8-neighbor edge
   graph, removing a diagonal adjacency if an orthogonal edge path already joins
   it. Degree !=2 vertices are endpoints/junctions and terminate paths. Closed
   loops start at the lexicographically first pixel with deterministic direction.
   Split at directed tangent turns >45 degrees using points 4 arc pixels to
   either side, strongest-first suppression within 6 arc pixels; split residual
   spans longer than 96 pixels into equal contiguous pieces. Retain original
   ordered pixels, endpoints, junction incidence, parent path, cumulative arc
   length, and all rejected pieces. Matching pieces need >=12 pixels arc length.
   Resample at <=2 pixels (uniform intervals including endpoints).
2. Consider all F camera pairs with camera-center angle about the frozen box
   center in [5,110] degrees. Fundamental matrices use full K and calibrated
   extrinsics. For each source sample, intersect its epipolar line with every
   target polyline segment; allow nearest endpoints within 1 pixel of that line.
   Merge intersections within 2 target arc pixels. Reject samples with multiple
   separated intersections, or target tangent/epipolar crossing angle <15 degrees.
   Repeat symmetrically. This is intersection of identified 2D curves, never
   independent per-pixel depth search. No candidate-count cap or top-k pruning.
3. Align the surviving intersections by target arclength. Either strictly forward
   or strictly reversed order is legal, but no change of orientation, many-to-one
   assignment, or crossing. Consecutive source gaps <=4 pixels and target gaps
   <=8 pixels; local arc slope in [0.25,4]. The longest contiguous legal run must
   cover >=60% of each curve and >=12 arc pixels in each; require >=7 samples.
   Reversal is global and swaps descriptor sides. RGB descriptor at each sample
   is the mean at normal offsets {2,4} on each side (six numbers), bilinearly
   sampled from RGB smoothed at sigma 1.2. Compare both global side conventions;
   retain the better convention but record both. Mean RGB RMS <=0.20. Pair cost
   is mean RGB RMS + 0.10*(1-minimum bilateral coverage). Symmetric alignment must
   agree at P90 <=2 arc pixels. Retain every geometrically proposed candidate
   and every failure reason. Select only mutual best candidates, with absolute
   runner-up margin >=0.025 AND best/runner-up <=0.8 at both ends. Missing second
   candidate has infinite margin. Near ties are rejected, never broken by IDs.
4. Enumerate closed triangles of selected segment identities from three distinct
   views. Every triangle must have consistent reversal parity and arc-transfer
   closure P90 <=2 pixels over >=7 samples / >=12 reference arc pixels. Merge
   triangles sharing an edge; reject a merged component if it contains two
   identities from one view or inconsistent alternative transfers. Propagate
   root arclength using fixed sorted graph traversal; every available edge must
   agree with that map at P90 <=2 pixels. A segment may belong to only one track;
   conflicting components are rejected together. No junction joining in 3D.
5. Freeze identity and sample correspondences BEFORE triangulation. Common arc
   support is sampled at <=4 reference pixels with >=4 knots. Triangulate each
   knot with deterministic all-pair DLT hypotheses; maximize number of <=2px
   inliers, then minimize clipped squared error; Huber 1px refinement on all
   observations. Require >=3 inliers, positive depth in all supporting cameras,
   frozen-box containment, one ray pair >=20 degrees and a second >=10 degrees.
   Reject failed knots and split at their gaps; each remaining span needs >=4
   knots / >=12 reference pixels. No interpolation across rejected knots.
6. Jointly refine the one shared polyline with fixed cameras and identities.
   Data residual: exact closest point on the observed polyline restricted to
   +/-2 pixels of the frozen corresponding arclength. Add a 0.2-weight image
   correspondence anchor and 0.05-weight second difference in fixed delta units;
   Huber 1px, at most 100 function evaluations, per-coordinate bounds +/-2delta
   around the triangulated knots. No new knots, extension, joining or topology
   change. Accept only F RMS <=1.5px, tangent median <=15 degrees, positive depth,
   baseline criteria, and the original support. Retain all failed fits. Stable
   IDs are hashes of sorted image segment identities and supported knot interval.
7. Image-only is the exact generator above. GS-aided is the same identities,
   triangulations and fits, with a separate post-fit support/visibility veto:
   each knot must have >=3 supporting F views with calibrated native800/area400
   GS support and front transmittance >=0.8. Use unchanged contribution-layer
   support and 2delta margin. Hidden <=0.1; intermediate visibility is uncertain.
   Require >=80% passing knots, and retain only contiguous passing spans >=4
   knots / >=12 pixels; no change to remaining geometry. Thus GS can reject
   image associations but cannot select an ambiguous identity. Both arms retain
   the same image-only fit certificate. This minimal GS prior can win only by
   removing false image matches without destroying useful coverage.

## Inputs, order and isolation

Reuse the corrected config, exact cameras, photo hashes, checkpoints, wide boxes,
fixed delta, seeds 1729/2718, all nine qualified doses per eligible parent, and
native contribution caches with hashes. No GS training or new doses. F =
[1,14,27,41,53,67,79,93]; C = [7,21,33,47,59,73,86,99]; DEV = train
[2,22,42,62]. TEST [5,15,25,35,45,55,65,75,85,95] remains sealed.
Lego then Chair, regardless of earlier scene failures. Both use identical code
and thresholds. Lego is CONTROLLED_ONLY because seed2718 replay failed prior
calibration; its seed2718 cannot certify invariance. Chair uses both routes.
Drums and Ficus have no eligible parent: record INSUFFICIENT_POSTERIOR_QUALITY,
do not execute a stress test on ineligible inputs, and do not block core verdicts.

Primary generation reads F alone. Freeze all F geometry/identities/topology and
hash artifacts before C/DEV evaluation. C independently re-extracts, re-matches,
and fits with no F initialization, then comparison occurs in the evaluator.
Every F leave-one-view-out reruns track formation and fitting on the remaining
graph (unchanged pairwise data may be reused; no primary 3D initialization).
Repeat every qualified GS prior on identical image identities, with no Gaussian
IDs, ICP or per-asset scaling. Image-only posterior repeats are invariant by
construction and do not count as measured GS benefit. Landlock exact scientific
file allowlists and native open traces enforce stage isolation. Evaluators have
read-only access to frozen outputs. Administrative byte hashing is separate from
decoding evidence; TEST bytes are not opened even for new provenance inventory.

## Controls and evaluation (run even after early failures)

- Image-only and GS arms above, plus all qualified posterior repeats.
- Shifted-curve association null: move each view's complete ordered curve and
  descriptor together by the fixed 32-pixel view-dependent offsets from the old
  control, without dropping pieces or changing counts. Coordinates may leave the
  image; no artificial wraparound segment is created. Match/follow cycles/fit
  with the same rules. Evaluate against unshifted C/DEV evidence.
- Randomized graph null: independently permute target segment IDs within each
  camera pair (seed 20260919), preserving pair edge counts and alignments, then
  run the same cycles and fitting. Nonexistent target arc support is rejection.
- Pairwise-only ablation: fit each mutually accepted pair without requiring a
  cycle or third view; minimum triangulation inliers/support is 2 only in this
  ablation. Same F residual and held-out scoring. It cannot certify primary yield.
- No-order ablation: permit the independent unique epipolar intersections without
  monotonicity/slope/reversal-parity tests, retaining identity cycles and geometry
  checks. This is a diagnostic arm only, never an output rescue.
- Reuse the corrected F-only original-position PCA linelets as visual reference,
  explicitly not correspondence truth. Document old local-pixel zero yield.

Held-out scoring projects frozen geometry at <=delta/2 world arc spacing. Report
all in-frame points, out-of-frame points, foreshortened directions, known-hidden
and uncertain points separately. Main image prediction gate uses all in-frame
samples, equally weighting views; GS visibility-stratified scores are additional
and cannot excuse a failed all-in-frame gate. This conservative measure may
penalize occluded curves, a declared limitation shared by all arms. Use detector
distance and unoriented tangent, with no manual-label substitution. Nearest edge
in held-out scoring is a prediction residual, not evidence for generation.
Per-track coverage requires at least 80% of its projected samples jointly within
2px and 20 degrees in a view. Missing/empty denominators fail necessary gates.

## Necessary per-scene machine gates

G0: inputs/caches/hash checks, confinement, zero forbidden reads, correct sampling,
eligible posterior route, completed F/C/DEV/controls, finite fits and TDD validity.
Resource/implementation failures are ENGINEERING_NOT_READY, not scientific STOP.

G1 yield: >=12 primary tracks with centroids separated >=4delta (deterministic
hash-order packing); >=300 total supported projected arc pixels averaged over
the eight F views; >=6 occupied 32px cells in each of >=4 F views. Every primary
track has >=3 distinct views and the frozen baseline diversity; >=25% have >=4
views. Do not count knots as independent tracks or fragmented duplicates as yield.

G2 prediction: F RMS <=1.5px and tangent median <=15 degrees; C and DEV each have
view-equal distance median <=1.5px, P90 <=3px, tangent median <=15 degrees,
P90 <=30 degrees, joint distance<=2px/angle<=20 support >=80%. >=80% of tracks
must be supported in >=2 C views; >=50% in >=2 DEV views. Failing outputs remain.

G3 repeatability: independent C fit, every F LOO, every eligible seed and every
qualified dose must achieve bidirectional supported arc coverage >=80%, symmetric
distance median <=0.5delta/P90 <=delta, tangent median <=10/P90 <=20 degrees, and
total 3D length change <=15%. Geometry matching is mutual nearest sampled curve
tubes, with max2delta/20 degrees, competing tube distance margin >=0.5delta;
no IDs or alignment. Report counts and unmatched curves, not just matched errors.

G4 identity and nulls: all accepted tracks satisfy cycle/order certificates and
pairwise ambiguity margins. Shifted and randomized null C/DEV-supported projected
length each <=1/3 primary; primary must have positive supported length. Pairwise
and no-order ablations cannot have both >=80% primary supported held-out length
and joint prediction within 0.05 of primary. Otherwise this test fails to show
the claimed need for the correspondence mechanism; do not relabel ablations nulls.
Report all alternatives, rejection rates and detector false-match diagnostics.

G5 GS benefit: stable GS arm passes G1-G4, and on DEV reduces unsupported projected
length >=25% with supported length loss <=10%, OR increases supported length
>=20% with joint precision drop <=0.02. Both-zero errors do not establish benefit.
Apply the criterion for every qualified posterior. Detector benefit is a machine
proxy; independent visible-domain interpretation remains manual.

M visual (genuinely independent, otherwise pending): three reviewers, at least two
prefer coherent shape and less clutter at matched ink; identify >=6 coherent
shape-relevant spans in separated regions, including >=2 internal structures.
No persistent wrong-depth/cross-part/texture/shadow double structure dominating
>=13 video frames. Fixed paths and visibility unexplained flicker <=5% on clearly
visible spans. Silhouette/shadow/highlight/repeated-texture/junction/multilayer
failure buckets are explicit. Prior coarse internal boxes remain diagnostic only;
no certified annotation or independent reviewer is fabricated.

Decisions: G0 invalid => ENGINEERING_NOT_READY/UNDETERMINED. Image-only G1-G4 pass
and GS has no stable G5 benefit/harm => PIVOT_IMAGE_ONLY (visual status disclosed).
GS G1-G5 pass => CURVE_CORRESPONDENCE_GO_MANUAL_PENDING, upgraded to FOUNDATION_GO
only if independent M passes. Valid necessary correspondence gate failure in both
arms => STOP_CORRESPONDENCE. CONTROLLED_ONLY/SEED_ONLY qualify routes. Scene-level
negative is determinate without manual review. Both core scenes must pass for any
core GO; no averaging, replacement scene, hand-picked subset or threshold rescue.

## Outputs, TDD and completion

All new code, tests, logs and artifacts live in this directory; previous branches
and results stay unchanged. Observe RED then GREEN then refactor for extraction,
full-K candidates, axial/reversal handling, arc alignment, cycle/ambiguity checks,
robust triangulation, bounded curve BA, support classification, geometry-only
repeat matching, controls, gates, reporting, isolation and visual serialization.
Keep exact commands, exit codes, source hashes and raw logs in TDD_LEDGER.md.

Actual extraction overlays, candidate/ambiguity panels, rejected-cycle/order
panels, stable-color tracks and F/C/DEV projections are mandatory even if empty.
All arms get native comparison sheets. If any persistent primary/ablation/null
curve is nonempty, generate 120 frames at 24fps at 400px, the inherited 360-degree
25+8*sin(2phi) elevation orbit with phase22.5, and all-frame contact sheets.
No mesh is used for evaluation or display. Fixed cardinality: deterministic hash
prefix min(12, smallest nonempty arm count); zero arms remain visibly empty.
Fixed ink: freeze prefixes on F to 60% of the smallest nonempty arm's F ink;
report <=5% tolerance success or incomparability, never alter width/geometry.
DEV subsets remain fixed. Review images are randomized, stripped of arm labels,
with the identity key outside the blinded package. Zero independent review is
claimed until an actual independent review exists.

Budget: 8 hours per scene scientific execution, separate implementation time.
Use cached calibrated layers; no new expensive posterior optimization. Continue
all failure diagnostics after an early gate fails, but do not build final fields
or strokes. Final checks: targeted and complete repository suites, JSON/Markdown
totals, every PNG decode, every MP4 decoded 120 frames, forbidden-input audit,
all eight checkpoint hashes and preserved archives. Inventory large server-only
arrays exactly. Commit/push logical changes without force-push or PR; verify clean
worktree and local/upstream/remote equality. Write the requested external report.
