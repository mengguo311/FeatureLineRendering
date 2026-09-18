# Multiscene foundation B: preregistration v1

Author: Codex, implementing research engineer; no independent reviewer is available.
Required initial HEAD: `6b098a5cb538fc4fc09d48d927dc97b77acc0b28`, branch
`multiscene-foundation`. This document and config.json must be committed and pushed
before any new scene training or perturbation render. Input byte hashing and camera
metadata inspection are permitted before that commit. No new outcome has been used.

## Question and changes from the prior protocol

Can TRAIN multi-view image evidence identify narrow, stable local 3D edge bands and
axial tangents, and does frozen vanilla GS support/visibility add stable value?
No field training, UDF, tracing, curves, connection, Beziers, final strokes, selector
tuning, mesh or mesh-derived evaluation is permitted. All four scenes run regardless
of another scene's result: lego, chair, drums, ficus, in that fixed order. The previous
decision memo is incorporated for scientific definitions; its complete byte hash and
the previous reports are in input_hashes.json. This document takes precedence where
explicitly changed. Manual requirements are retained as uncertified requirements,
not prerequisites to computing machine gates.

Changes are authorized by the new user decision: eight new vanilla posteriors,
four-scene evaluation without the old Lego-first transfer stop, and a new controlled
family. Existing drums_static is absent, so **all scenes use the new seed 1729 as
the Route-B parent**, fixed by run identity before its output exists. Existing legacy
GS assets are not substitutes. There is no outcome-dependent parent choice. Route B
is pipelined with Route A after each first-seed checkpoint is complete; it does not
wait for all training. No posterior is retrained after a quality failure.

GS training now excludes the probe DEV/TEST photographs. This strengthens held-out
claims relative to the old assets' unknown training provenance. The probe F/C images
are seen by both GS trainings; only the image-evidence fitting processes separate F
and C. Thus C is independent of the local fit, not independent of GS training.

## Route A: fixed source, data, training and eligibility

Clone Git objects, never working files, from the dirty external repository into
vendor/gaussian-splatting; checkout upstream
`472689c0dc70417448fb451bf529ae532d32c095`. Required training submodules are rasterizer
`59f5f77e3ddbac3ed9db93ec2cfe99ed6c5d121d` (GLM
`5c46b9c07008ae65cb81ab79cd677ecc1934b903`) and simple-knn
`44f764299fa305faf6ec5ebd99939e0508331503`. SIBR is not a training dependency.
The only semantic patch adds `--seed` (default 0) to train.py and passes it to
safe_state, replacing its three hardcoded zero seeds with that argument. Preserve
all other code. Record full diff, source tree hashes, imported binary paths/hashes,
build logs and environment. Reuse the previously verified stock rasterizer binary
only after checking its hash and matching pristine source; build simple-knn into an
isolated package directory. Compiler cstdint preinclude is allowed as a compatibility
build flag, never an algorithm change. Test seed injection on Python/NumPy/Torch CPU
and CUDA streams, repeatability and unchanged argument defaults.

Exactly seeds **1729 and 2718**, for each of the four scenes. Each run has a separate
staged data directory without points3d.ply, so the official 100,000-point random
initialization runs under its own seed. No existing point cloud, mesh or cached
initialization is copied. Same image bytes and metadata in both runs. Original
transforms_train indices 0..99 excluding DEV [2,22,42,62] and TEST
[5,15,25,35,45,55,65,75,85,95] gives 86 optimization views. Original val indices
[1,7,14,21,27,33,41,47,53,59,67,73,79,86,93,99] are staged as the official loader's
test split for reconstruction validation. Official `--eval` is enabled. Original
test photographs are never staged or read. Original train DEV/TEST photos remain
sealed from training and local fitting. Training data split changes are declared
here, not implemented by modifying the upstream loader.

Official defaults at the pinned source, white background for all synthetic scenes,
resolution=-1 (800px source images), SH degree 3, 30,000 iterations; all optimizer,
densification, loss and schedule values are explicitly in config.json. Save/test at
7,000 and 30,000; only final 30,000 is eligible. No appearance-selected checkpoint.
Network GUI binds localhost, a distinct port per worker. Four CPU threads per
training process, at most one new training per physical GPU. Check at least 16 GiB
free before each launch, and at least 30 GiB free disk. Wait 60 seconds between
resource checks, maximum six hours of resource waiting per job. A job exceeding six
hours of training is ENGINEERING_NOT_READY, not a negative scientific result.
Durable detached worker, logs and exit-status JSON. Never signal other users' jobs.
No restart after OOM/failure except a proven pre-training packaging/CLI error that
made zero optimization steps; preserve both logs. Do not change recipe to fit memory.

Final stock RGB at 400px is evaluated on 16 TRAIN and 16 validation views, on white
and black backgrounds. The official training report additionally records 800px
quality. ROI for quality is original RGBA alpha >=0.5, fixed independent of renders.
Per scene/seed/background/split: mean ROI PSNR >=25 dB, worst-view PSNR >=20 dB,
mean ROI SSIM >=0.90, worst-view SSIM >=0.80. These deliberately allow more diverse
independent reconstructions than synthetic equivalence; a pass is adequate input
quality, not a state-of-the-art reconstruction claim. Pairwise seed eligibility
additionally requires mean PSNR gap <=2 dB and mean SSIM gap <=0.03 on each split
and background. On each view/background, seed-to-seed ROI RMSE must be <=1.5 times
the larger seed-to-GT RMSE (plus 1e-6), and seed-to-seed mean SSIM >=0.90. This
relates posterior disagreement to actual reconstruction error instead of imposing
the 40 dB synthetic gate. All conditions conjunctive, no failed view discarded.
Both individual seeds and their relation must pass for Route A to be valid.

## Route B: predetermined renderer-aware family

Use seed 1729 final checkpoint, even if Route A's pair relation fails. Its individual
quality and native calibration must pass. Canonical parent rows: lowest floor(N/2)
SHA256 hashes of UTF-8 `20260919:parent:<row>`, computed and frozen before rendering
any intervention. At least 20% baseline foreground contribution in **every** TRAIN
view must belong to affected parents. Children inherit SH and rotation; no row
matching is used in the science. Row permutation is only an IO check.

Let a be parent sigmoid opacity, q a fixed split fraction, b=q*a. For two coincident
equal-footprint children, alpha-composited opacity is (c+b)g-c*b*g^2, where g is the
projected Gaussian footprint. Choose

`c=(a-b)*(1/2-b/3)/(1/2-2*b/3+b*b/4)`.

This minimizes the integrated squared opacity residual over an ideal isolated 2D
Gaussian footprint (`dA` proportional to `dg/g`, g in [0,1]). It accounts for the
cross term rather than matching only peak alpha. It is NOT an image-equivalence
guarantee: cutoff, clamping, ordering, occlusion, depth-dependent projection and SH
view direction remain actual-renderer effects. c and b must remain in (0,1); invalid
parameters fail, they are not clipped into validity.

Family **redistribute** uses co-located equal-covariance children with q in
`[1/32,1/16,1/8,1/4,1/2]`. Family **moment_split** uses q=1/4 and doses
`d=[0.025,0.05,0.10,0.20]`. Let w1=c/(b+c), w2=b/(b+c), maximum local scale s and
axis e (first index breaks ties). Child centers are
`mu1=mu-sqrt(w2/w1)*d*s*e`, `mu2=mu+sqrt(w1/w2)*d*s*e`.
Both covariances are `Sigma-d^2*s^2*e*e^T`. The opacity-weighted mixture mean and
covariance are exactly preserved algebraically. This is not a physical volumetric
density assertion. Opacities stay c,b. Parent replacement order is child1,child2.

Every dose is rendered and reported; all qualified doses enter G3, no preferred
dose is selected. Report PSNR/SSIM/P99/child contribution against increasing dose,
including nonmonotonicity (do not impose a monotone fit). In addition to affected
coverage >=20%, smaller children must collectively contribute >=0.5% of original
foreground mass in each view; otherwise that dose is trivial/ineligible. This
prevents vanishing new primitives from buying an invariance claim.

Unchanged synthetic qualification: baseline alpha>=0.5 ROI, raw float stock RGB,
every 16 TRAIN view on black and white: PSNR>=40 dB, SSIM>=0.995 (minimum channel
mean, Gaussian sigma1.5/window11/population moments), P99 of max-channel error
<=8/255. Empty ROI invalid. The same comparisons on DEV cameras are made only
after local output freezing, with no DEV photographs required. A DEV-ineligible
dose has no interpretable DEV invariance claim. No qualifying dose makes Route B
INVALID, not STOP_B. Route A may still independently test posterior stability.

## Shared local probe and immutable sampling

Resolution 400x400, white RGBA composite, area resize, gray uint8 Gaussian sigma1.2
then OpenCV Canny(50,120), aperture3/L2gradient=False. 5x5 edge-coordinate PCA gives
an unoriented tangent; require >=3 edge pixels and minor/major ratio<=0.25, otherwise
direction is undefined. Nearest-edge distance and nearest valid tangent are distinct:
undefined tangents never become zero angular error. Integer pixel coordinates and
full K homogeneous projection/Jacobian. Native raster adapter supports fx/fy/cx/cy;
reject nonzero skew rather than approximate it; analytical geometry supports full K.

TRAIN/F/C/DEV/TEST, primary [1,27,53,79] and exchange [7,33,59,86] query views and
seed 20260918 remain as in the previous config. For each query view choose one edge
pixel per occupied 8px grid cell by SHA256 `20260918:query:view:y:x`, then take the
64 lowest hashes. No image-content ranking beyond Canny and no refill of empty
cells. Background diagnostics: 16 foreground pixels/view at DT>=6, same hash rule.
Query pixel lists are hashed before inference; primary F and reverse C processes
have separate input allowlists. The C run on original F queries occurs only after F
output hashes are frozen; C-native queries are a separate coverage diagnostic.

Baseline wide box: center quantiles .001/.999, each side expanded by 10% original
diagonal. No primitive removed. >1% outside contribution on any TRAIN view is an
input-validity failure. Delta: median across TRAIN foreground rays of conditional
median native contribution depth / sqrt(fx*fy). Freeze from seed1729 once; every
seed/dose uses the same coordinates, box, delta and queries; no ICP or rescaling.
Full ray-box intersection, sample count max(256,ceil(2*length/delta)+1), cap2048;
if spacing>delta/2 after capping, resolution inadequate. Preserve every local
minimum, including endpoints and flat minima (one representative with full plateau
extent). Refine every bracket twice with eight uniform samples. No GS depth
initialization or GS-only search interval. Preserve full profiles for every arm.

Unit-weight per-view DT residuals, truncated at6px. The image-only profile uses all
in-frame views. The GS profile uses only native-visible views, at least3 with a pair
of camera rays separated>=20deg. At each profile minimum, freeze visibility during
local correction. Local correction: at most5 Gauss-Newton steps with Moore-Penrose
inverse of image constraints, total displacement bounded by delta, step<=delta/2;
retain the ray-only estimate also. Reject a visibility-class change. Evaluate the
five query offsets (0,0),(1,0),(-1,0),(0,1),(0,-1) as detector sensitivity; these do
not replace the original query or select a better output. Leave-one-F-view-out
reruns full search. Every mode and all near-optimal alternatives are retained.

Native anisotropic conics, tile IDs and stock depth order are decoded from the
unmodified renderer. Replay stock alpha clamp .99, cutoff1/255, and skip-triggering
early termination T<1e-4. Calibrate RGB on both backgrounds and alpha recovered
from white-minus-black, maximum errors<=1/255 on every TRAIN pixel, every eligible
asset. Native per-pixel contributing depths/weights are retained, not just mean or
top-k. Front transmittance before z-2delta: >=.8 visible, <=.1 hidden, else uncertain.
Retain 5%-95% conditional mass layers, splitting adjacent depths at gaps>2delta,
expand each interval by2delta. This labels GS support; it never truncates search.
Accept GS-arm modes only with support in >=3 visible views. Rejected modes remain
in saved profiles and no-GS. H_img contains only J^T*n*n^T*J, sigma=1px; its smallest
eigenvector is axial. No GS/regularization Hessian is added.

Accept a mode only if lambda1/lambda2<=.1, lambda3/lambda2<=25,
sqrt(5.99/lambda2)<=delta, F RMS DT<=1.5px, median axial reprojection error<=10deg,
and no alternative within .5px RMS and transverse distance>2delta. Undefined or
foreshortened directions (norm(J*t)*delta<.25px) are excluded with denominator
counts reported. Deduplicate accepted points greedily by fixed query hash at
distance delta; preserve raw results. No confidence ranking or manual selection.

## Controls, audits and gates

no-GS uses identical box, query count, resolution, detector, residuals and mode
rules, with all in-frame views and no support rejection. Shifted association rolls
view j maps by (32*((j%3)-1),32*(((j+1)%3)-1)); exclude a32px border for every view.
Random axes use NumPy default_rng(20260918), Gaussian3-vectors normalized, at the
same positions. No arm is allowed to change glyph width/length.

Old PCA control is rebuilt F-only, not read from historical 16-view caches. To avoid
using the uncalibrated disc proxy, its seed score is the mean exp(-DT^2/(2*2^2))
over native-visible F views at each original GS center, requiring >=3 views; keep
the best30%, ties by row hash. Use the old init_linelets maximum PCA eigenvector,
radius3 times the global median local8-neighbor maximum splat scale; no pull,
prune, chainer or selector tuning. This explicitly adapted **F-only center-PCA
control** is not asserted identical to the old disc-based pipeline. Compare its
original centers; nearest control direction at B queries is diagnosis only.

Surface sample audit is diagnosis only: 128 hash-selected query/background native
5/50/95% depth locations, radii2/4/8delta. Fit/holdout by fixed delta/2 occupied
cells, cell parity hash, no clone leakage. Report equal-cell and contribution
weights, heldout single-plane/quadratic/two-plane/volume residuals, covariance-axis
agreement. Sheet requires>=30cells, heldoutP90<=.15h, tangent-plane spread>=.1,
adjacent-scale/bootstrap normalP90<=15deg and posterior repeatability. Two-plane
requires>=15cells/side, >=30% heldout gain, normal angle>=25deg and supported
intersection within delta. Otherwise layered/blob/sparse/unstable. No fit feeds
queries, positions, tangents or acceptance. Missing audit evidence remains unknown.

G0: input isolation/hash/calibration/resolution pass and at least one valid route.
G1: >=64 delta-separated positions, each satisfying all local acceptance rules.
G2 machine: >=80% accepted positions have >=2 evaluable C views; among evaluable
positions >=80% joint DT<=2px and direction<=20deg support. DEV manual precision
>=.85, >=.10 above center-PCA, and >=half positions evaluable in >=2 DEV views;
manual component UNCERTIFIED without independent labels.
G3: every LOO, C same-query, eligible seed and every qualified dose: bidirectional
geometric matching>=.8 within2delta/20deg; position median<=.5delta,P90<=delta;
axis median<=10deg,P90<=20deg; accepted count change<=15%. Match same-query modes
first with one-to-one minimum-cost assignment; add delta/2 glyph sample/cell
coverage. No Gaussian ID, ICP, asset scaling or intersection-only denominator.
G4: shifted acceptance<=real/3 and median projection-angle error<=half random.
GS gain requires independent clearly-visible-domain DEV precision loss<=.02 with
>=25% fewer diagnosed wrong-depth points, or precision>=.85 for both and >=20%
more reliable supported positions. A zero error denominator cannot count as gain.
Without such labels, GS gain remains UNCERTIFIED; machine proxies are descriptive.
G5: inherited target coverage and matched-ink review, three actual independent
reviewers, at least two prefer structure and fewer irrelevant lines. UNCERTIFIED
without them. No machine statistic can certify G5.

Before local outputs, the implementing assistant may mark TRAIN-only target/challenge
regions, with author/time/hash and explicitly internal status. Do not invent twelve
cross-view corresponding spans if they cannot be identified reliably. Prepare all
TRAIN contacts for diagnosis. DEV annotations follow frozen outputs and remain
internal unless an actual independent annotator participates. Missing reviewers do
not stop machine science, but block FOUNDATION-GO and certified PIVOT claims.

Actual deterministic glyph images are supplied for every reached local arm,
including empty/failure outputs, native counts and fixed64 spatial-hash subsets.
Glyphs x+-delta*t, black1px AA, stock RGB reference plus white display; fixed TRAIN
1/27/53/79 and DEV2/22/42/62. Occlusion on/off diagnosis. Ink budget60% of center-PCA
64-glyph mean F ink, choose fixed hash prefix once, require5% match in F and DEV;
otherwise mark incomparable. Video stage only if all four scenes pass G1 and G2
machine:120frames,24fps,400px,full orbit, phase22.5deg,elevation25+8sin(2phi),
target baseline box center, radius median TRAIN camera distance to target. No
post-hoc viewpoint choice. All frames/contact sheets and frame-count verification.

## Decisions and execution stops

Per-scene and macro summaries; no average can rescue a failed scene. Run all eight
trainings/all nine doses in each scene unless a real engineering failure prevents
that action. Record failed/missing stages explicitly. At least one valid route in a
scene triggers its full machine local probe and controls even if the other route
fails. All reached measurements/failures remain in reports.

FOUNDATION-GO requires Route A stability, qualified Route B stability, all four
scenes' G0-G5 including genuinely certified manual gates. SEED_ONLY requires the
independent route's machine observability/stability/controls in all scenes but no
qualified controlled route; report manual limitations separately. CONTROLLED_ONLY
requires analogous controlled-route machine success but failed/ineligible independent
route; weak evidence, never general posterior invariance. When both machine routes
pass but manual gates are missing, verdict UNDETERMINED with machine states, not a
new positive label. PIVOT_IMAGE_ONLY requires certified local image success and
stable no-GS with absent/harmful GS benefit. STOP_B requires a valid route and
machine evidence of multimodal/unstable local bands or certified irrelevant-edge
dominance; G1 failure accompanied by recorded degeneracy/multimodality/instability
is a scoped negative result. Insufficient eligible inputs or incomplete calibration,
isolation, annotation-dependent interpretation or resource failure is UNDETERMINED
or ENGINEERING_NOT_READY, never hidden by another scene's success.

Native prerequisite budget2hours/scene, local probes8hours/scene (many more arms than
the previous30min); build/setup/development reported separately. Fail closed on
nonfinite data, mismatched input hashes, forbidden reads or failed calibration.
Engineering repairs that preserve frozen mathematical behavior may be tested and
logged; recipe/threshold/algorithm changes need a new preregistration and must not
overwrite this run. Strict observed RED/GREEN tests before new production behavior,
with commands and raw failures in TDD_LEDGER.md. Targeted/full suites, every committed
PNG decode and MP4 frame count, Markdown/JSON cross-check, manifest paths/sizes/SHA.
Small conventional commits pushed only to origin/multiscene-foundation. No PR,
history rewrite or changes to the dirty source worktree. Final clean worktree and
HEAD/upstream/remote equality recorded in the external report.
