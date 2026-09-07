# DISCUSSION ROUND 1 — do FeatureGS / EdgeGaussians kernel pre-processing help our method? (NO CODE — analysis only)

You are the research partner (Fable 5.1) for a U-Tokyo Umetani-Lab M1 project. This is an ADVERSARIAL DESIGN
DISCUSSION, round 1 of 2. Give your honest expert analysis — NO code, NO shell, NO file edits. I (the orchestrator)
will push back hard on your answer; we are arguing toward the best idea, not agreeing. Write your analysis to
/tmp/m1b_round1.txt (use a single shell `cat > /tmp/m1b_round1.txt <<'EOF' ... EOF` at the very end) AND print it.

## OUR PROJECT (locked state — trust this)
GOAL: extract CLEAN, TEMPORALLY-STABLE 3D feature lines (crease/silhouette) from a 3DGS reconstruction, for NPR
line rendering. BANKED, held-out, method-core result: object-space lines are 3.4-11.5x more temporally coherent
than per-frame image-space Canny (popped 11.3/11.5/7.6x, Frechet 29.9/14.0/11.4x on chair/lego/ficus). Paper is
shipped: temporal win + honest coverage-ceiling characterization.
KEY FINDINGS (all held-out, mesh EVAL-ONLY):
- Coverage ceiling: re-ranking the fixed vanilla-3DGS gaussian pool caps recall (0.79 chair / 0.56 lego). Creases
  with NO gaussian carrier are unrecoverable by re-ranking.
- K_geom~0: vanilla 3DGS bakes texture into geometry. ALL geometric crease-vs-texture discriminators are DEAD,
  AUC~0.5 (vanilla normals/depth/SH-DC/center-PCA, 2DGS, even GT-mesh dihedral 0.396 on lego decals).
- DexiNed-primary multi-view TRIANGULATION recovers 69% of the gaussian-missed creases (chair recall 0.49->0.68).
- DINOv2 semantic discriminator separates crease-vs-texture at held-out AUC 0.84-0.90.
- Experiment X (mesh dihedral labels): of lego's ~79% miss-set, GEOMETRIC fraction g=0.948, DECAL fraction=0.000
  — the misses are structurally-real geometry SMOOTHED AWAY by gaussian splatting, NOT flat decals.
- Line-buffer epipolar-accumulation test: NO-GO. Multi-view mean of raw DexiNed over missed creases doesn't
  separate from flat points (lego AUC ~0.70, Recall@85%prec 0.000) — DexiNed's ~5px response tail contaminates
  edge-dense flat surface. So a trained edge-field supervised by DexiNed can't beat the single-view 2D ceiling.
- Aggressive 3D linking of the shipped linelets: MARGINAL — safe (precision/temporal preserved, temporal even
  improved) but continuity gain only +21%/+14% (< the +25% bar); it does NOT fix the fundamental fragmentation,
  because the fragmentation comes from the coverage ceiling (lines are broken where there's no carrier), not from
  weak linking. The rough line drawings are still "rough".
CONSTRAINTS: mesh is EVAL-ONLY, NEVER in the method path. The temporal-coherence win is the crown jewel and must
be protected. We work from a FROZEN 3DGS (post-hoc); a retrain pivot was tried and the geometry-retrain Exp Y was
also weak (dF1 +0.016 vs +0.15 needed). GPU is tight. Scenes: chair/lego/ficus (pretrained 3DGS + GT mesh).

## THE TWO PAPERS (their kernel pre-processing / geometry mechanisms)
1) FeatureGS (Jager et al., 2025, arXiv 2501.17655): adds a GEOMETRIC LOSS term to 3DGS training based on
   eigenvalue-derived 3D shape features of the per-Gaussian covariance AND of the local kNN neighborhood of
   Gaussian centers. Four variants: 'planarity' of a Gaussian (flatten it — make lambda3 small), and 'planarity'
   / 'omnivariance' / 'eigenentropy' of the kNN neighborhood (enforce locally-planar, low-structural-entropy
   arrangements, Manhattan-world man-made surfaces). Result on DTU: +30% geometric accuracy, 90% fewer Gaussians,
   90% fewer floaters, Gaussian CENTERS become directly usable as an accurate surface point cloud. Core idea:
   PRE-CONDITION the Gaussian kernels (flatten + planar-neighborhood-regularize) so centers snap onto the surface.
2) EdgeGaussians (Chelani et al., WACV 2025, arXiv 2409.12886): trains 3DGS FROM 2D EDGE MAPS (not RGB), with a
   GEOMETRIC REGULARIZATION that forces each Gaussian to be ELONGATED (anisotropic, lambda1 >> lambda2~lambda3~0)
   with its direction-of-largest-variance ALIGNED to the local edge direction (aligned to neighbors). The mean =
   an oriented 3D edge point, the principal axis = edge tangent. Then cluster by proximity+orientation and fit
   parametric edges. Handles edge-map sparsity (mask loss balancing edge/non-edge pixels) and occlusion. Core
   idea: SHAPE the Gaussian kernels into oriented 1D "filaments" that ARE the edge, directly giving point+tangent.

## THE QUESTION (analyze, don't just summarize)
Do these two papers' Gaussian-kernel PRE-PROCESSING ideas (FeatureGS eigenvalue/planarity flattening +
neighborhood-entropy regularization; EdgeGaussians anisotropic filament alignment to edge direction) offer
anything that could improve OUR method — either the FROZEN post-hoc extraction, or a scoped retrain — GIVEN our
banked findings above? Be specific and adversarial with YOURSELF. Address:

Q1. FeatureGS flattens Gaussians + regularizes neighborhoods so centers become accurate surface points. Our
   coverage ceiling is that fine creases have NO carrier (smoothed away). Could FeatureGS-style planarity/entropy
   PRE-conditioning of the frozen gaussians (as a post-hoc geometric cleanup of the existing cloud, no retrain)
   sharpen crease localization or expose creases at planar-patch INTERSECTIONS (two flattened planar neighborhoods
   meeting = a crease)? Or does "flatten everything planar" actively ERASE the very micro-geometry (the crease
   ridge) we need — i.e. is it anti-correlated with our goal?
Q2. EdgeGaussians shapes kernels into edge-aligned filaments trained FROM edge maps. This is exactly a retrain,
   and its supervision is 2D edge maps — so by our epipolar-accumulation NO-GO, it inherits the SAME 2D-detector
   recall ceiling and CANNOT recover the smoothed-away creases lego misses. Is that right, or does its EXPLICIT
   anisotropic edge-direction regularization (a strong geometric prior lambda1>>lambda2,lambda3 + neighbor
   alignment) extract MORE from the same 2D signal than our triangulation+DT-pull does — i.e. does the prior act
   as a denoiser/integrator that beats per-view thresholding the way we hoped multi-view accumulation would (but
   didn't)? Where exactly would it help vs where does the ceiling still bind?
Q3. The one genuinely transferable idea: is it FeatureGS's EIGENVALUE SHAPE-FEATURE as a per-gaussian/neighborhood
   DESCRIPTOR (planarity, omnivariance, eigenentropy) used NOT as a training loss but as a POST-HOC FEATURE for
   crease detection on the frozen cloud? We proved center-PCA / single-channel geometric discriminators are dead
   (AUC~0.5) on decals — but our g=0.948 finding says lego misses are REAL geometry, not decals. So on the
   geometric miss-set specifically (not decals), could a NEIGHBORHOOD eigen-feature (e.g. planarity drop /
   eigenentropy spike at a crease where two planar neighborhoods meet) be a discriminative crease signal that our
   earlier single-gaussian geometric tests missed because they used per-gaussian not NEIGHBORHOOD statistics? Or
   is this just the dead geometric discriminator again in a new hat?
Q4. Your single most honest recommendation: is there a CHEAP, decisive experiment worth running here (on the
   frozen cloud, mesh EVAL-ONLY, protecting temporal), or do both papers ultimately not move OUR needle because
   our bottleneck (smoothed-away carriers + 2D-detector ceiling) is upstream of anything a kernel-shape prior can
   fix? If there IS a worthwhile test, name it precisely with a pre-registered go/no-go. If NOT, say so plainly.

Be rigorous, cite our specific numbers, and DISAGREE with me where the evidence warrants. End by writing the full
analysis to /tmp/m1b_round1.txt.
