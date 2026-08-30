# NG-MEC Stage 1 — de-risked: isolate the epipolar-consensus selectivity gain

Held-out TEST throughout. Mesh EVAL-ONLY (mesh_oracle.py); method path imports no mesh.
Protect the temporal-coherence win. Do NOT retune anything per-scene; carry chair's VAL
threshold (TEED 0.5) unchanged. Nothing published may change (keep Canny/TEED/union paths
bit-identical — verify as you did in TEED_GEN_RESULTS.md).

## Why this shape (context from analysis + agy argument)
- PROVEN binding quantity = SELECTIVITY, not localization (TRACK M: binary TEED mask swing
  +0.2408, 10/10 views; 15px misregistration reverses to -0.1066). NG-MEC's epipolar
  half IS cross-view selectivity — that is the component to test.
- PROVEN dead: vanilla-3DGS normals are AUC~0.5 for fabric-vs-crease on chair (K_geom~0).
  Therefore the normal gate MUST be strictly ADDITIVE (a non-vetoing recall anchor on
  hard-surface dihedral/silhouette), NEVER a veto. On flat/micro-texture regions it must
  delegate to the TEED 2D prior. If normals ever subtract from TEED proposals, that is a bug.
- We have never hit P@1.5>=0.85. So do NOT gate on the full combined target yet. Stage 1
  isolates whether multi-view epipolar consensus adds precision OVER raw TEED proposals
  WITHOUT destroying recall — on the texture-stress scene (chair) where it matters most.

## Build
Add an epipolar-consensus selectivity gate as a NEW additive/refinement edge source in
final_recipe.py (do not alter existing sources). For each TEED seed proposal, project into
K nearest held-out neighbor views along its epipolar line and measure edge support
(TEED-edge presence within tau px of the epipolar band). Keep a seed only if it has
multi-view support in >= m of K neighbors. This is a selectivity filter on TEED proposals;
it removes single-view hallucinations / view-dependent occluding contours. Sweep m/K
(e.g. K=4, m in {2,3,4}) and tau in {1.5, 2.5}. No mesh anywhere in this path.

## Measure (chair AND lego, held-out TEST)
1. dP@1.5 and dR@1.5 of (TEED + epipolar-consensus) vs raw TEED alone, across f in [0.22,0.50].
2. Temporal: Frechet + popping / flicker-win ratio at 240 frames for the winning arm.
3. Report per-view paired stats (like the t=13.69 you did for TRACK M).

## FROZEN GO / NO-GO (Stage 1)
- GO (proceed to Stage 2 = add the additive normal anchor + push toward P>=0.85/R>=0.65):
  epipolar consensus yields dP@1.5 >= +0.05 over raw TEED on chair held-out, AT COST OF
  <= 0.05 absolute recall drop (additive-not-destructive), AND flicker-win ratio stays
  >= 12.0x at 240 frames on chair (temporal no-regress vs the TEED baseline).
- NO-GO / rethink: dP@1.5 < +0.02 on chair, OR recall drop > 0.05 (consensus is culling
  true creases = localization not selectivity), OR flicker-win < 11.0x at 240 frames.
- CONDITIONAL: if it fires on lego (hard surface, epipolar bands clean) but not chair,
  that mirrors the purity-conditional law from TRACK L — report it as such, don't force it.

Write results to out/*.json + a thorough tier1/NGMEC_S1_RESULTS.md. Do not commit until I review.
