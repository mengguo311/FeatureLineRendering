# EPIPOLAR ACCUMULATION TEST — combined results (lego primary, chair secondary)

Pre-registered kill-test for the LINE-BUFFER pivot (`tier1/epipolar_accum_spec.md`). Closed form, no field
trained. Script `scripts/epi_accum.py` (frozen md5 `bf2e3486a5006970938a944ca7bd801c`, cv2 4.5.5); per-scene
reports `out/epi/EPI_ACCUM_{lego,chair}.md`, JSON `out/epi/epi_accum_{lego,chair}.json`, figures
`out/epi/epi_accum_{lego,chair}.png` + `_inspect_v*.png`, arrays `out/epi/epi_{labels,samples,scores}_*.npz`.
Mesh EVAL-ONLY throughout (labels + the image-space negative gate); the feature is mesh-free.

## FORMAL VERDICT (frozen rule: GO if AUC>=0.80 AND R@85P>=0.55; NO-GO if AUC<=0.65 OR R@85P<=0.42)

| scene | |M_miss| / |M_flat| | S_bar AUC | Recall@85%Prec | single-view AUC (mean / best) | paired multi-view lift | verdict |
|---|---|---|---|---|---|---|
| **lego** (primary) | 437,138 / 436,700 | **0.698** | **0.000** | 0.644 / 0.758 | +0.049 AUC | **NO-GO** (R@85P) |
| chair (secondary) | 73,371 / 73,371 | **0.859** | **0.000** | 0.738 / 0.828 | +0.133 AUC | **NO-GO** (R@85P) — knife-edge |

S_bar = occlusion-aware (3DGS mean depth, 3x3-min z-buffer, eps_rel 0.02 = the pipeline's rule) mean over all
100 training views of RAW, un-thresholded DexiNed native probability, sampled bilinearly at the projected GT
point (photo-index offset (-0.5,-0.5) calibrated on the hit-set = tri_edges' halfpix convention). RAW-map
continuity was asserted at run time (11,475 distinct values on a 1/9 sub-grid; 10% of pixels in (0.02,0.5)).
Both classes are balanced and TEST-visible under the same mesh-depth rule that defined M_miss.

## What the numbers actually say (read these before acting on the verdict)

1. **The spec's NO-GO mechanism ("missed creases are dead zeros") is NOT what lego shows.** Only 11.1% of
   lego's M_miss (48,379 pts) are undetected by the pipeline's own 2D rule (NMS-thinned native >= 0.5 within
   1.5 px) in every visible view; those are true dead zeros (S_bar p50 0.0098, AUC 0.22 vs flat). The other
   88.9% are detected in at least one view (per-point detection rate p50 0.19) and score AUC 0.76 vs flat.
   M_miss S_bar mean 0.220 (p50 0.204) vs M_flat 0.122 (p50 0.072).
2. **The lego failure is a spatial-resolution limit of DexiNed supervision, decided by the negative class.**
   DexiNed's response tail contaminates flat surface out to ~5 px of any edge: flat S_bar 0.136 at 3-4 px,
   0.097 at 4-5, 0.073 at 5-6, 0.062 at 6-8, 0.036 at 8-12 px (M_miss 0.220). Lego has almost no surface
   farther than that from an edge: of the 972,959-point flat pool (3 px margin), 17% survive 4.5 px, 2.9%
   survive 6 px, 0.3% survive 8 px. Margin sweep (positives fixed, balanced): 3 px 0.698/0.000 NO-GO;
   4.5 px 0.791/0.508 MARGINAL (162k negs); 6 px 0.831/0.665 GO (27.7k); 8 px 0.865/0.803 GO (2.5k).
   The pre-registered class definition (3 px = the project's 2*tau negative convention) gives NO-GO; a
   margin chosen after seeing which one crosses GO would be a forking path, so it is reported as sensitivity
   only. The image-space clean-negative arm is DEGENERATE on lego (95-99% of negatives have no view farther
   than 3 px from a projected crease-like edge; the plotted 0.97/1.0 points score a 4.5% remnant and must be
   ignored).
3. **No mesh-free analysis choice rescues lego at the pre-registered class definition**: across map
   (native/ms) x sampling (bilinear / 3x3-max) x eps (0.02 / 0.005) x views (100 / train-80) x aggregator
   (mean, median, trimmed, top-quartile, max, logit-mean, 3 px silhouette peel) the best AUC is 0.713 and
   R@85P never exceeds 0.003. The 30.000-degree tessellation family (49% of M_miss, smooth-shaded stud
   barrels) scores AUC 0.588; real creases (theta >= 30.05) reach AUC 0.803 but still R@85P 0.000.
4. **Chair is a knife-edge NO-GO.** AUC 0.859 is GO-level; R@85P is exactly 0 at the headline configuration
   but 0.147 with a different random negative subsample at the same 3 px margin, 0.652 with the ms map,
   0.56-0.77 with the tight eps arms, 0.715-0.808 at 3D margins >= 4.5 px (GO), and 0.839-0.886 in the
   image-space clean-negative arm (valid on chair: 11-30% of negatives lack a clean view). The R@85P
   criterion on chair is decided by a thin sliver of negatives on curved rails / silhouette contours that
   accumulate silhouette contrast coherently; the AUC half of the rule is robust.
5. **Multi-view accumulation is real but modest on lego**: paired lift over the same points +0.049 AUC
   (range -0.017 .. +0.112; +0.005 vs the best single view); on chair +0.133 (+0.085 vs the best view).
   The max-over-views (any-view) aggregator is worse than the mean on both scenes (lego 0.612, chair 0.674):
   incoherent false positives do NOT average out under max, they do under mean, as agy predicted.

## A label bug found by review, fixed, and an inherited project-wide issue it exposes

- **As-run (first version) vs corrected.** The first flat class was built from `face_adjacency` edges of the
  OBJ as trimesh loads it. The NeRF-synthetic OBJs use v/vt/vn triplets, so every hard-shaded crease / UV seam
  is an OPEN BOUNDARY edge with no adjacency: 71% (lego) / 59% (chair) of the first "flat" points sat within
  3 px of a real sharp edge and scored like creases (AUC 0.572 lego / 0.733 chair, both NO-GO). The corrected
  flat class excludes merged-mesh edges >= 10 deg plus boundary and non-manifold edges (lego: 713,686 vs
  374,572 topological >= 10 deg edges). Corrected: lego 0.698, chair 0.859. Both versions are NO-GO on
  R@85P; the AUC and the mechanism reading changed materially.
- **Inherited: `src/mesh_oracle.py` builds the GT crease set from the same split-vertex adjacency.** The
  banked a30 crease set covers only **37.4% (lego) / 43.1% (chair)** of the geometric >= 30 deg edges
  (position-merged mesh); the banked set is a strict subset (99.3% / 100% contained). Every prior
  mesh-scored recall/ceiling number (including the 0.385 single-view ceiling and Experiment X's 79% miss)
  was scored against that topology-selected subset. A geometric-a30 arm with the same visibility, cloud and
  radius rule as Experiment X gives frozen-cloud 3D recall **0.175 on lego** (banked subset 0.199, non-banked
  0.159) and **0.598 on chair** (0.665 / 0.545): the never-counted creases are slightly HARDER, not easier,
  and their accumulation AUC is lower (lego 0.617, chair 0.820, R@85P 0). This does not change the
  epipolar verdict, but the orchestrator should decide whether the banked GT definition needs a disclosure.

## Definition-of-done checklist

- |M_miss| / |M_flat|: lego 437,138 / 436,700 (438 flats + 64 misses dropped for having no 3DGS-visible view);
  chair 73,371 / 73,371. Flat rule and margin stated above (3 px-equiv = 0.01016 / 0.01031 world).
- eps: 0.02 relative (pipeline rule); tight arm 0.005. Depth-test calibration on mesh-visible TEST samples:
  3DGS keeps 86.1% (lego) / 91.9% (chair) of mesh-visible samples at eps 0.02 and passes 20.7% / 17.1% of
  mesh-occluded ones; dz/z p50 +0.0024 / +0.0028.
- DexiNed pre-threshold extraction confirmed (sigmoid fused map, float16, no NMS/threshold/stretch).
- Distribution plot: `out/epi/epi_accum_lego.png` (panel a); ROC/PR and margin sensitivity in the same figure.
- Verdict vs frozen thresholds: NO-GO (lego), NO-GO (chair) — with the sensitivity and mechanism notes above
  for the orchestrator + agy reconciliation. No line field was built. Nothing committed.

## Caveats

- An adversarial code review (21 agents) ran on the first script version; all 8 confirmed findings were
  fixed before the corrected run (label topology, geometric arm, NMS-faithful detection proxy, paired lift,
  per-class zero-visibility handling, z-buffer lookup convention, balanced single-view PR curve, script
  hash). An INDEPENDENT RE-COMPUTATION from the saved arrays (fresh code, numbers frozen before reading the
  JSON; `scratchpad/recompute_epi.py`) reproduces both headlines to 1e-9 (lego 0.69839854 / 0.0; chair
  0.85868071 / 0.0) and all 16 margin-sweep cells to 5e-9 once the script's balancing convention is
  replicated; with an independent random draw the cells move by <= 0.018 AUC / 0.03 R@85P (inside the
  seed-to-seed spread) and every GO/MARGINAL/NO-GO label is stable across seeds 0-5. It also shows the
  R@85P criterion's brittleness: on lego, 2,093 headline negatives (0.48%) outrank the positive 99th
  percentile and deleting the top 5,000 negatives lifts R@85P only to 0.055 (NO-GO is structural); on
  chair, 278 negatives (0.38%) outrank it and deleting the top 1,000 lifts R@85P 0.00 -> 0.53, the top
  5,000 -> 0.80 (NO-GO is knife-edge). Not audited by that check: the production of nat_bil / vis_loose /
  cls / d10_flat themselves (covered by the code review's confirmed-ok list).
- The chair photo-index offset calibration optimum (-0.5,-1.0) sits on the edge of the 5x5 search grid
  (lego: (-0.5,-0.5), interior); a 0.5 px matter at most.
- Positives are the pre-registered banked M_miss; see the inherited-issue note for what that set is.
