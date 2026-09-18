# Corrected multiscene foundation preregistration

Author: Codex implementing research engineer. Initial branch
`multiscene-foundation-corrected`, HEAD
`5c5837ff5de68498d1c0388269808a30041a8774`.
This document and config.json are committed and pushed before any corrected scene
qualification. Synthetic software tests alone precede this freeze.

This is **not a blind correction**. The archived multiscene experiment remains
permanently UNDETERMINED. Its post-hoc native800/area400 diagnostic is known,
including the weak Drums and borderline Ficus reconstruction. No diagnostic row
is imported as a new qualification measurement. No result in either prior output
root is modified. The decision memo and prior preregistrations are incorporated by
byte hash; the prior multiscene protocol is copied in inherited_protocol.md.

## Sole measurement correction

Native image dimensions are exactly 800x800. Construct the centered stock camera
from original camera_angle_x (FoVy derived with the actual image aspect ratio),
using stock `ndc2Pix(v,S)=((v+1)*S-1)/2`. Preserve fx, fy, cx, cy explicitly.
World-to-camera matrices, photograph bytes and splits are unchanged. Store both
native_K and measurement K in config.json. General resampling uses
`u_destination=(u_source+0.5)*destination_size/source_size-0.5`, hence
`K_destination=A K_source` with A's translation `(scale-1)/2`. No independent
400px Gaussian rasterization is permitted in qualification, inference or display.

Render unmodified stock GS at 800. Independently compare the top-level stock
renderer to the native adapter at 800 on every measured camera/background, and
calibrate native anisotropic RGB/alpha compositing at 800 before resizing.
Unchanged calibration tolerance is 1/255. The stock wrapper/direct binding check
is retained. Unit tests additionally check a tighter 1e-6 synthetic stock equality.

Canonical 800->400 filter is the exact nonoverlapping 2x2 area mean: convert inputs
to float64, sum top-left, top-right, bottom-left, bottom-right in that order, divide
by four; do not quantize or clip. Test deterministic bytes, impulses/ramps, non-square
full-K coordinate/Jacobian mapping, unequal focal lengths and off-center intrinsics.
Source RGBA is decoded to float64/255, composite RGB at 800 on each background,
then area-average. Alpha is area-averaged separately. Photographic quality ROI is
reference downsampled alpha>=0.5; perturbation ROI is baseline downsampled native
alpha>=0.5. Every residual, edge map and ROI uses this one 400px convention.

Native contribution/depth distributions on each destination pixel are the equal
mixture of its four source-pixel event streams (weights divided by four), sorted
by depth. Average front transmittance over the same four pixels. Conditional
5/50/95% depths and all separated support layers are derived from that mixture,
not from averaged depth quantiles or a new 400px splat. Replay calibration at 800
must pass first. Delta is recomputed once from the seed1729 mixture median-depth
foreground samples divided by sqrt(fx400*fy400), over all 16 TRAIN views; all arms
reuse it. Pixel lookup uses the inherited nearest-center rule. Analytical full-K
projection and Jacobians use measurement K. Wide box, world coordinates and
perturbation parent selection are unchanged and verified against prior hashes.

## Frozen inputs and science

Exactly Lego, Chair, Drums, Ficus; seeds1729/2718; iteration30000 only. Reuse the
eight archived checkpoint bytes. Never train, replace a scene, add a seed, or select
an earlier checkpoint. Reuse all 36 interventions, every view/background and the
original parent hashes. config.json retains unchanged numerical detector, query,
probe, eligibility, control, native, surface, visual and gate settings. Preserved
TRAIN annotations are copied byte-for-byte before local output, with original
authorship and lack of independence. No improvement is planned. They are coarse
candidates, not certified cross-view spans; no manual gate is silently waived.

The complete inherited local experiment is required for each eligible scene:
F-only primary queries/fit, sealed C until F outputs are hashed, independent C
same-query full search and C-native coverage, every F LOO and all fixed detector
offsets, image-only and GS profiles over the entire box with all modes retained,
H_img and axial inference, frozen visibility during correction, global ambiguity
rejection, all qualified seed/dose repeats, no-GS/PCA/shifted/random controls,
coverage denominators and the diagnosis-only surface audit. No Gaussian-ID matching,
ICP or per-asset normalization. Native accepted, rejected and ambiguous outputs
are retained even if G1 fails. No DEV rescue, UDF, curve extraction, connection,
smoothing, Beziers, final strokes, mesh or old-selector modification.

Unchanged parent quality: in each TRAIN/validation and black/white group, mean
PSNR>=25, minimum PSNR>=20, mean SSIM>=.90, minimum SSIM>=.80. Route A requires both
seeds plus mean PSNR gap<=2, SSIM gap<=.03, pair mean SSIM>=.90 and every pair RMSE
<=1.5*larger reference RMSE+1e-6. Route B needs seed1729 quality/calibration and at
least one dose with every RGB pair PSNR>=40, SSIM>=.995, P99<=8/255, every affected
mass>=.20 and minor-child mass>=.005. All qualified doses enter repeatability.
Calibration and outside-box mass<=.01 are unchanged prerequisites.

G0-G5 numerical rules are exactly inherited_protocol.md and config.json. G1>=64
separated accepted positions; G2 C coverage/joint support>=.80; G3 all repetitions
pass both-direction .80 matching, .5delta median/1delta P90 distance, 10/20 degree
median/P90 angle and <=.15 count change; G4 shift acceptance<=real/3 and random-axis
error ratio<=.5. G4 GS benefit retains its independent visible-domain evaluation
requirement, not a detector-based substitute. A 0/0 null statistic cannot pass.
Manual G2 precision, G4 benefit and G5 remain pending without independent labels.
Neither this author nor any internal inspection is independent human review.

## Scope and prespecified decisions

Eligibility is per posterior/scene. Run the complete local probe wherever Route A
or Route B is valid, regardless of all other scenes. Report three levels:
per eligible scene; core synthetic Lego and Chair separately (conjunctive, no
averaging); expanded scope needs >=3 eligible scenes including Drums or Ficus.
If that scope requirement fails, expanded status is INSUFFICIENT_POSTERIOR_QUALITY,
without erasing determinate eligible-scene conclusions. A scene with no eligible
parent has that same quality status; non-quality validity failures remain explicit.

User-authorized labels, frozen now: FOUNDATION_GO requires all machine and truly
independent manual gates. MACHINE_FOUNDATION_GO_MANUAL_PENDING requires all required
machine gates pass, with annotation/review-dependent components explicitly pending;
it is not FOUNDATION_GO and does not certify GS gain. PIVOT_IMAGE_ONLY requires
stable image localization and evidence of absent/harmful stable GS benefit under
the unchanged gates; pending independent interpretation is disclosed. STOP_B means
a valid eligible route fails necessary observability/repeatability/non-null or
visual-structure machine gates. CONTROLLED_ONLY / SEED_ONLY identify invariance
scope and append machine/manual status, never hide a machine failure. Engineering
validity blockers alone produce ENGINEERING_NOT_READY / UNDETERMINED.

Failure does not end diagnostic reporting. Generate real deterministic fixed-view
glyph PNGs/contact sheets for every reached local arm, including empty outputs,
all counts and failure profiles. Video-stage triggering is applied **per eligible
scene**: G1 and G2 machine pass triggers the unchanged 120-frame 24fps 400px orbit;
other scenes cannot block it. Fixed views, orbit, glyph length/width, hash subsets
and matched-ink rules are unchanged. If video stage is unreached, say so explicitly;
never fabricate a schematic or an unrelated clip. Make a randomized A/B review
package for reached images with the identity key stored outside that package.
This prepares a blinded independent review; no review is claimed to have occurred.

## Execution, isolation and verification

Use new results only under this root. Reuse original read-only inputs and approved
runtime sources/binaries. No training commands. Landlock restricts each child
process before asset/photo access; strace audits native opens. F/C/DEV evaluators
have separate allowlists; evaluation cannot write primary outputs. Hash queries
before inference and F outputs before C or DEV. TEST stays sealed. Byte hashing
provenance is distinct from decoding image evidence.

Strict observed RED-GREEN-REFACTOR; keep raw commands, times, test/source hashes and
failed attempts. Test new local components on deterministic synthetic geometry
before scene use. End with separately executed targeted and full repository suites,
programmatic JSON/Markdown/gate consistency, PNG decode, reached MP4 decoded frame
counts, checkpoint/input/hash checks and forbidden-input audit. Inventories include
large server-side arrays and traces. Qualification budget2hours/scene and local
budget8hours/scene are unchanged; setup/development separate. Do not label a timeout
as scientific failure. All small logical commits are pushed to the required branch;
no PR, force push or other-branch change. Final local/upstream/remote equality and
clean worktree are recorded externally to avoid a self-referential commit hash.
