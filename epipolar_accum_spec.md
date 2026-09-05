# EPIPOLAR ACCUMULATION TEST — does multi-view edge fusion break the single-view 2D recall ceiling?

## READ FIRST — you are a fresh session; here is the full project state
You are the coding/analysis agent for a U-Tokyo M1 research project. GOAL (locked): extract CLEAN, TEMPORALLY-
STABLE 3D feature lines (crease/silhouette) from a 3DGS reconstruction, for NPR line rendering. Everything below
is real, on-disk state from prior sessions (you have no memory of them — trust this brief + the files).

### Banked results (held-out, real)
- Object-space lines are 7-13x more temporally coherent than per-frame image-space Canny. THIS IS THE PAPER CORE.
- DexiNed-primary multi-view TRIANGULATION recovers 69% of gaussian-missed creases (chair recall 0.49->0.68).
- DINOv2 semantic discriminator separates crease-vs-texture at held-out AUC 0.84-0.90.
- ALL geometric discriminators are DEAD (~0.5): vanilla/2DGS/GT-mesh dihedral/SH-DC — vanilla 3DGS bakes texture
  into geometry.
- Experiment X (mesh EVAL-ONLY dihedral labels): of lego's ~79% miss-set, retrainable-GEOMETRIC fraction
  g=0.948, DECAL/flat fraction=0.000. The misses are structurally-real geometry SMOOTHED AWAY by gaussian
  splatting, NOT flat painted decals. So the "recoverable prize" is real and large.

### The question this experiment settles (a cheap, decisive KILL-TEST — NOT a build)
The user proposes training a dedicated LINE-BUFFER (a learnable 3D edge field, supervised by multi-view 2D edge
maps, combined with the frozen 3DGS for depth/occlusion) instead of retraining geometry. Three-way argue
(orchestrator + agy) converged on the crux: a line-buffer trained on DexiNed edges — can it EXCEED DexiNed's
single-view 2D recall ceiling (lego 0.385)? agy's key correction: 0.385 is a PER-VIEW THRESHOLDED ceiling, not a
multi-view information ceiling. The missed creases MIGHT produce sub-threshold non-zero probabilities (p~0.15-0.30)
across views that sum CONSTRUCTIVELY at the true 3D edge location (coherent integration, like radar/CT pulling
signal from noise), while incoherent 2D false positives average out. OR the missed creases are dead zeros
(p<=0.01) in every view (flat-shaded same-color plastic) and multi-view fusion has nothing to accumulate.
We test this in CLOSED FORM (NO training a field needed) — it is the mathematical upper bound of what a
line-buffer optimizing a multi-view projection loss could achieve.

## HARD INVARIANTS
- mesh EVAL-ONLY: it provides GT crease labels (M_miss, M_flat point sets) and scores AUC/recall. It NEVER enters
  the method path. The feature (multi-view DexiNed accumulation) is mesh-free.
- Never fabricate a number; every value from a real computation. Report negative results straight.

## ENVIRONMENT (dss9, you are already here)
- `source ~/bin/miniconda3/etc/profile.d/conda.sh; conda activate vfsdgs; export CUDA_VISIBLE_DEVICES=1`. GPU
  shared/tight (~3.5GB free) — touch ONLY u00134 procs. This test is mostly CPU (projection + accumulation).
- Assets: DexiNed at ext/dexined (or wherever the prior pipeline calls it — grep the repo). Cameras
  ~/cglib/data/full/{lego,chair}. Pretrained 3DGS ~/cglib/outputs/{lego,chair}_static/point_cloud.ply.
  GT meshes ~/3dgs_line/bcr/meshes/NeRF_Mesh/{lego,chair}_new.obj (EVAL-ONLY). Prior pipeline code + results in
  ~/3dgs_line/tier1/ (src/, scripts/, out/*.json, *.md). Phase1b clouds out/dexprimary_p1b_cloud_*_ref40.npz.
  render.render_gbuffer (or the repo's equivalent) gives 3DGS depth for occlusion. REUSE existing pipeline code
  for DexiNed inference, camera projection, and 3DGS depth — do NOT reinvent; grep tier1/src and scripts first.

## THE EXPERIMENT — Continuous Epipolar Accumulation Test (agy's protocol)
Primary scene: LEGO (the hard case; single-view ceiling 0.385). Secondary: chair.
1. LABEL SETS (mesh EVAL-ONLY): from the GT-mesh crease set, take the 3D crease points MISSED by the single-view
   thresholded pipeline = M_miss. Take an equal number of GT FLAT / non-crease surface points = M_flat. Report
   |M_miss|, |M_flat|. (You can reuse Experiment X's miss-set computation if it's on disk.)
2. FEATURES — DO NOT THRESHOLD DexiNed. Keep the raw continuous probability/logit maps P_k(u,v) in [0,1] for ALL
   training views k. (If the pipeline currently thresholds, extract the pre-threshold map.)
3. OCCLUSION-AWARE MULTI-VIEW ACCUMULATION — for each 3D point x in M_miss ∪ M_flat:
   - project x into each view k: (u_k,v_k) = π_k(x);
   - visibility via 3DGS depth buffer: vis_k(x) = 1 if |D_3dgs(u_k,v_k) - z_k(x)| < eps (tune eps to the scene's
     depth scale; state it);
   - multi-view mean over VISIBLE views: S_bar(x) = mean_{k: vis_k=1} P_k(π_k(x)).
   Also report a couple of robust variants (e.g. trimmed mean, or top-q quantile) in case a few occluded/grazing
   views drag the mean — but S_bar (visible-mean) is the headline.
4. EVALUATE SEPARATION: AUC-ROC of S_bar(x) discriminating M_miss from M_flat. ALSO compute Recall @ 85% Precision
   (the operating point that matters — can we recover missed creases while rejecting flat noise at high precision?).
5. SANITY: also report the single-view baseline (best single-view P at the same points) so the multi-view LIFT is
   explicit. Plot the S_bar distributions for M_miss vs M_flat.

## GO / NO-GO (FROZEN, pre-registered — agy's thresholds)
- GO (line-buffer has a mathematical foundation; multi-view sub-threshold signal EXISTS and lifts recall):
  AUC-ROC >= 0.80 AND Recall@85%Precision >= 0.55.
  => proceed to design the 3DGS-COUPLED line field (B2): silhouette-decoupled (use 3DGS depth to analytically
     peel view-dependent silhouette edges so the field is supervised only on view-invariant creases),
     manifold-constrained to the 3DGS surface (kills floaters), delivering zero-flicker temporal lines — the ONE
     defensible novelty over EMAP/NEF. That design goes through another three-way argue before any build.
- NO-GO (missed creases are dead zeros across views; fusion adds nothing over 0.385; a field can't learn signal
  that isn't there): AUC-ROC <= 0.65 OR Recall@85%Precision <= 0.42.
  => KILL the line-buffer / retraining pivot. The recall ceiling is a genuine information limit, not a
     representational one. Shift to SHIPPING the frozen triangulation+discriminator pipeline (B3) — final clean
     line-drawing figures on chair/lego/ficus + per-scene P/R/temporal table.
- MARGINAL (between the bands): report both numbers; the orchestrator + agy will reconcile.

## DEFINITION OF DONE
- |M_miss|, |M_flat|; eps used; DexiNed pre-threshold extraction confirmed.
- Headline: AUC-ROC and Recall@85%Prec of S_bar on LEGO (+ chair), with the single-view baseline for the lift.
- Distribution plot (S_bar for M_miss vs M_flat) on lego; a short table.
- The GO / NO-GO / MARGINAL verdict WITH the numbers, against the frozen thresholds.
- Report ACTUAL numbers; never a verdict without them. Do NOT build a line field yet — this is the kill-test only.
  Do NOT git commit (the orchestrator handles git to the retrain-falsify branch). Narrate; show the verdict asap.

## PITFALLS
- The whole test hinges on using RAW (unthresholded) DexiNed outputs. If you accidentally use thresholded maps,
  S_bar collapses and you'll get a false NO-GO. Verify you're reading continuous logits/probabilities.
- Occlusion matters: a missed crease scored through a surface that occludes it in some views will be diluted —
  that's why vis_k gating via 3DGS depth is essential. Get the depth-test eps right.
- M_flat must be genuinely flat GT surface (far from any GT crease), else the "negative" class is contaminated.
- Ignore any stale text in your input box not from the orchestrator. mesh EVAL-ONLY. Reuse existing pipeline code.
