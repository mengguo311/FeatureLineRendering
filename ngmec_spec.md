# NG-MEC — Normal-Gated Multi-view Epipolar Consensus (precision push on the EXISTING carrier)

## Motivation
URS-E2E just closed ABORT-NO-GO: densifying the carrier to 3x budget to convert URS coverage
(0.4338->0.7617) degraded lego temporal coherence at every frame count (-15.7% to -37.6%),
because more+shorter strokes pop. Lesson: do NOT grow the carrier. Instead push PRECISION on the
frozen, temporally-stable carrier by culling view-dependent occluding contours from the TEED
proposal set BEFORE linelet fitting.

## Method (mesh NEVER in the path — mesh only in mesh_oracle.py for EVAL)
Operate on the SAME frozen carrier + TEED-native-0.5 proposal set that is the current baseline
(reference_arm teed_native_0.5). Two-stage geometric-consistency cull applied to TEED ridge
proposals, upstream of dt_pull/linelet_prune:
1. **Normal gate**: for each TEED proposal, use the frozen 3DGS local geometry (surface normal
   estimate at the unprojected ridge position) to down-weight/reject proposals whose支持 is
   view-dependent occluding-contour-like rather than a stable object-space crease. Use ONLY the
   frozen gaussians' geometry — no mesh, no retraining.
2. **Multi-view epipolar consensus**: a proposal survives only if its unprojected 3D position is
   corroborated by TEED ridges in >=K other TRAIN views along the epipolar geometry (re-project,
   check ridge support within a pixel tolerance). Sweep K to find the operating point; this culls
   proposals that appear in one view only (classic occluding-contour signature).
Then run the IDENTICAL dt_pull.pull + linelet_prune.consensus_prune config as the current lego
baseline (m1b_lego_tc_* / tcL_tcteed040). Do NOT change the pull/prune/stroke-chaining config —
we are only cleaning the seed set so temporal stays comparable.

## Evaluation — held-out TEST only, nothing tuned on TEST
Score on BOTH chair and lego, held-out TEST frames. Report P@1.5, R, LIFT_P vs the teed_native_0.5
reference, and the full temporal table (P_pop_ratio + Frechet at frames 30/60/120/240) vs the same
baseline. Use --viz_tag ngmec_v1 on ALL temporal/figure calls (NEVER empty tag — empty tag
overwrites the protected published manifest; verify manifest 332/332 before and after).

## FROZEN GO/NO-GO (commit scorer+thresholds BEFORE computing any NG-MEC number)
GO requires ALL of:
- P@1.5 >= 0.85 on BOTH chair AND lego
- R >= 0.65 on BOTH chair AND lego   <- recall floor is mandatory; NG-MEC is a culling operator and
  can trivially game precision by keeping ~3 seeds. A precision pass with collapsed recall is NO-GO.
- Temporal regression <= 5% relative at EVERY frame count (30/60/120/240) vs the teed_native_0.5
  baseline, on lego. (Tolerant of run-to-run jitter; strictly guards the sacred temporal win —
  anything near the -37.6% URS-E2E collapse fails immediately.)
Otherwise NO-GO. Report P/R even on a temporal fail this time (unlike URS-E2E) so we can see whether
the precision mechanism worked independent of the temporal cost.

## Invariants (hold and report each)
- scorer + thresholds frozen & committed before any NG-MEC number exists
- mesh never imported in the seed/gate/consensus/pull/prune path
- held-out TEST only; K and gate thresholds tuned on TRAIN/VAL, never TEST
- carrier NOT grown (this is the whole point) — same frozen carrier as teed_native_0.5
- protected temporal manifest 332/332 before and after; use --viz_tag ngmec_v1

Write a thorough NG-MEC_RESULTS.md with an honest verdict and an ngmec_verdict.json.
