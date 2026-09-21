# Frozen top-k layered line probe, version 1

Base HEAD 9313e537bb2a7a4f998f75ae202a4a13872eb1ea; branch topk-layered-line-probe.
Approved plan: /home/u00134/topk_layered_line_detection_plan.md, copied verbatim
as APPROVED_PLAN.md. User instructions override its final commit/push instruction:
NO commit or push. Protocol, manifest and source hashes are frozen before production
implementation or viewing new scene outputs. Never change scientific thresholds
in this run. A layout change requires equal pre/post scientific array/metric hashes.

## Inputs, cameras and isolation

Scene order lego, chair, drums, ficus; frozen vanilla SH3 3DGS seed 1729, iteration
30000. Exact paths, SHA256 and all permitted camera matrices are in INPUTS.json,
whose hash is recorded below. No pruning/retraining, external normals, mesh, 2DGS,
SDF, learned detector, source-image supervision, or TEST. No photographs needed.
Reuse the established splits: TRAIN=[1,7,14,21,27,33,41,47,53,59,67,73,79,86,93,99];
F=[1,14,27,41,53,67,79,93]; C=[7,21,33,47,59,73,86,99]; DEV=[2,22,42,62].
F/C are disjoint inference/cross-check subsets of TRAIN. DEV is held out from
checkpoint optimization. Dataset `train` camera matrices only; no TEST matrices
or data are selected. All science runs are Landlock confined before asset decoding,
with strace -f -yy open/openat/openat2/creat audit including startup. Runtime/code
reads are explicitly allowlisted, data paths are file-only. Fail closed on audit.

G0 cheap calibration: native 800x800 TRAIN 1 in each scene; finish this four-scene
calibration even if one fails, then stop if any fail. G1 fixed TRAIN [1,27,53,79]
in each scene, native 800x800 (no downsampled contributor mixing). G2 constructs
from F, freezes samples, evaluates C and DEV. G3 uses fixed TRAIN and DEV stills
and 120-frame 24fps orbit, azimuth 22.5+360*t/120 degrees, elevation
25+8*sin(2*pi*t/120), centered on median Gaussian center with median TRAIN camera
radius. No later view selection. Full K, w2c, dimensions and FoV recorded per camera.
Pixel centers are integer coordinates; stock ndc2Pix(v,S)=((v+1)*S-1)/2.

## G0: prerequisite gate, before any line detector

Use hash-pinned stock CUDA renderer in src.foundation.native_render and its native
buffers (kernel 59f5f77e3ddbac3ed9db93ec2cfe99ed6c5d121d). Reuse native replay
rules from multiscene_layers.cpp: power>0 skipped; alpha=min(.99,opacity*exp(power));
alpha<1/255 skipped; next T<1e-4 terminates BEFORE that event. No disc/proxy renderer.
Small additive native-state reader permitted; preserve existing APIs. Reader may
run on CPU using native conics and sorted tile lists, never recompute approximate
geometry or sorting. Calibrate against stock GPU, existing NativeLayers, and
independent stock top-level renderer. Equal-depth ties preserve native tile order.
Store FIRST k accepted contributors in front-to-back order, not largest weights.
Initial k=8; k=4,16 sensitivity only, never rescue G0 by switching k.

Each valid event stores original PLY row id, center camera depth z, alpha, incoming
T, w=T*alpha, native SH RGB. Padding id=-1 and other fields zero. Center depths
are the renderer's ordering proxy, not inferred ray/surface intersections.
Validate IDs in range, depths equal original camera-space centers (abs/relative
1e-5), monotone z (tolerance 1e-6*max(1,abs(z))), no duplicate IDs per pixel,
finite values, contiguous padding, alpha/T/w ranges. Recomputed T and w abs error
<=2e-6. Top-k alpha=sum w must equal 1-product(1-alpha) within 2e-6.
Store separate omitted-tail RGB, tail alpha, and final residual transmittance.
Replay sum(top-k w*rgb)+tail_rgb+final_T*background must match stock white/black
RGB, alpha, public wrapper and independent top-level stock within max abs 1/255.
Also show truncated RGB (top-k + T_after_k*background); never hide the tail by
renormalizing or asserting exact RGB from k alone. NativeLayers depth/weight
prefix agreement tolerance 2e-6. Full K calibration includes fx!=fy and off-center
cx/cy at 40x48 synthetic size; native means2D error <=1e-4 pixel, world projection
and pixel-center convention must agree. Native800 scene cameras must match stock.

Coverage gate: ROI=native alpha>=.5. Each scene requires nonempty ROI, captured
alpha sum(A_k)/sum(alpha_native) >=.90 on ROI, and >=.80 of ROI pixels must capture
>=.90 of their native alpha at k=8. These are minimum useful-distribution coverage
requirements, not an accuracy claim. Record distribution quantiles and k=4/16
controls. Missing tail remains explicit. Any failed G0 check =>
ENGINEERING_NOT_READY, scientific verdict NOT_EVALUATED, stop before G1.

## Frozen layer and evidence formulas (only implement after G0 passes)

A=sum(w); p=w/max(A,1e-12); mean=sum(p*z); variance=sum(p*(z-mean)^2);
H=-sum(p*log(max(p,1e-12))); z50=first cumulative p>=.5; front=first valid z.
At each pixel d=max(.002*front, median of valid absolute front-depth differences
in 5x5 neighborhood,1e-12). This scale is homogeneous in scene depth. Layer split
when adjacent (z_next-z)/d>3. Mass and weighted z are summed without tail
renormalization. Low-mass layers (<.05 native alpha) remain diagnostics, cannot
seed. Layer support requires A>=.5 and mass_l>=.1. Pair scale is max(d_x,d_y).
BC=sum_sharedIDs sqrt(p_x*p_y); D_id=sqrt(max(0,1-BC)); duplicate IDs prohibited.
D_front=abs(zfront_x-zfront_y)/d_pair. D_zdist=exact discrete weighted 1D W1/d_pair,
computed by union-depth CDF integration, not rank-wise subtraction.
r(t)=clip((t-1)/3,0,1), support=min(A_x,A_y), confidence=min(front mass/A).
E_occ= support * max(r(D_front),r(D_zdist)) * D_id * confidence.
E_layer= support * max-scale Hessian ridge of normalized variance or entropy,
restricted to neighborhoods with >=2 layers of mass>=.1 at >=5 of 9 neighbors,
separation>3*d and >=.75 consistent directed foreground/background signs.
Layer-count/front-mass transitions are saved separately as split/merge diagnostics.
E_shape=layer support * scale-normalized Hessian anisotropic response of separately
smoothed layer depth/d * local mean BC within that layer. Match layers to neighbors
by nearest depth within 3*d before smoothing; never average front/back layers.
Positive and negative Hessian polarity stored separately. Hessian scales [1.5,2.5,4]
pixels, eigenvalues ordered by abs, response abs(lambda_large)*exp(-.5*(ratio/.5)^2)
only ratio<.5. Max over scale, record scale and tangent. E_occ/E_layer/E_shape never
merged for primary decisions. ID turnover alone cannot seed any channel: depth
separation for occlusion/layer, nonzero depth curvature for shape are mandatory.

Robust channel scale=pooled TRAIN positive 99th percentile, freeze before F/C/DEV.
Store raw and normalized uncapped soft fields. Hysteresis grids high/low positive
response percentiles [(95,70),(90,60)] per view/channel, same rule all scenes; no
scene tuning. High seeds are NMS along normal; low continuation uses 8-neighbors,
axial tangent difference<=30 deg, step within 45 deg of tangent, same evidence
class/layer and BC>=.25. Band half-width=ceil(winning sigma); admit pixels only
above low threshold with compatible layer, preserving raw bands before cleanup.
No cleanup in primary output. Additional diagnostic union only. No global Top-N.

## Controls and G1 frozen gate

For each fixed view, save full weighted IDs+depth; expected depth gradient;
front and median gradients; no-ID depth W1; uniform event weights (same total A);
shuffled IDs (permute valid ID slots spatially within view, seed 20260921+view,
not global relabeling which preserves overlap); shuffled depths (permute valid z
slots with same seed+1000, sort each pixel afterward while retaining each paired
weight/ID); density-only broad Hessian ridge (previous center-KDE algorithm,
camera XY projection, unit center masses, all depths explicitly superposed);
RGB Canny(50,120), sigma1.2 of official 3DGS RGB, visual baseline only; k4/8/16.
No-ID removes BC/D_id factors only, preserving mandatory geometry gates.
Uniform uses A/n for each accepted event. Controls use same frozen extractor;
matched ink per view/class uses min positive pixel counts, deterministic rank and
raster-index ties; matched ink is a comparison only, not candidate output.

G1 passes only if full method beats BOTH front-depth and depth-W1 in >=3/4 scenes:
several (>=3) recognizable coherent bands across >=3/4 fixed views, visibly cleaner
or more complete at matched ink, and gain also apparent in uncapped responses.
For those scenes full must visibly outperform shuffled depth; ID mechanism may be
claimed only where no-ID and shuffled-ID are materially worse (>=.05 absolute
long-component ink fraction reduction AND visible deterioration in >=3 views).
If ID controls approximately equal full, report no ID mechanism; cannot claim full
mechanistic GO. Long-component means skeleton length>=24; this proxy cannot
replace actual sheets. Ficus always separately reported. Subjective inspection is
model review, not independent human study. Stop before lifting if G1 fails.

## Conditional G2/G3

Only after G1 PASS implement ray-depth lifting X=c2w*(z*K^-1[u,v,1],1), IDs solely
provenance. Store class/polarity/layer, pixel/camera, z gap, mass, weighted ID
histogram, dominant foreground/background pair and 2D tangent. Cluster TRAIN F
samples within .01*median camera depth AND BC>=.25, class/layer agreement; require
>=3 views with >=15 deg baseline. Fit unoriented tangent from multiview image
constraints, no covariance-PCA primary tangent. Never join depth-order conflicts.
Freeze before C/DEV evidence opens. G2 requires >=.60 visible length within 3px of
same evidence class in >=3/4 scenes, no scene carrying majority of supported length;
shuffled-ID and 32px shifted-camera nulls >=.15 absolute worse, plus convincing
complete source/held-out sheets. Visibility uses native T and layer separation.
If pass: trace compatible short paths, tangent change<=30deg and neighbor distance
<=.02*median camera depth; render scale-width paths with native occlusion for G3.
G3 requires clean recognizable shape, continuity, correct occlusion and no visible
orbit popping in >=3/4 scenes versus depth/density/matched controls. Complete
120-frame video mandatory, no selected-frame-only verdict. No mesh metrics gate.

## Output schema, execution and validation

artifacts/topk_layered_probe: immutable protocol/input/source hashes, TDD.jsonl,
command logs, GATES.json, verification/access audit, full figures and final summary.
out/topk_layered_probe/{run,rerun}: identical deterministic scientific outputs.
G0 per scene NPZ includes k16 event ids/z/alpha/T/w/rgb, topk alpha and residuals
for k4/8/16, stock white/black RGB/alpha, native projection checks, K/w2c; JSON
metrics and complete labeled RGB/alpha/tail/depth/variance/entropy/ID sheets.
G1 NPZ adds all raw responses, orientation/scales, layer arrays, thresholds, NMS,
raw hysteresis bands and every control; contact sheets show every fixed view/stage.
G2 NPZ/JSON samples/provenance/reprojections; G3 paths and full orbit only if reached.
Absent gated stages are NOT_RUN, never fabricated or silently replaced.

Strict vertical-slice TDD: add one failing behavior test, record expected RED,
minimal implementation, GREEN before next behavior. JSONL journal records command,
exit code, output hash, source/test hashes, phase and expected result; preserve logs.
Targeted and full unittest discovery, PNG/video decode, NPZ semantics, access and
source audit, deterministic full reached-stage rerun with byte/array/metric hash
comparison. Full suite may rebuild existing tested native libraries: hash before
and after, require equality or document/restore. No unrelated process termination.
GPU0, OMP/BLAS/MKL=1, bounded sequential G0; no expensive G2/G3 before gates.
Final report /home/u00134/codex_astra_topk_layered_probe_report.md includes commands,
all gates/limitations/changed files. Verify original HEAD and no commits/pushes.

INPUTS.json SHA256: `fd3e6a6885c0099d1a3af908eeb4aaca564cb87db0e2e5300fd59976fee46c86`

APPROVED_PLAN.md SHA256: `018a2e21d70f9d9148c037d55e3f8701e0aa7b1f61d5bdaa428c44cc014340b1`

BASE_SOURCES.json SHA256: `f6fb62857183aefff657d80faef8fe59d34e44edb4fbb19005419e4e47261e5e`
