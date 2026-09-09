# STEP 8 — DISPATCH (converged from your Step 7 argue). Direct run, NO heavy multi-agent workflow.

I read your full Step 7 answer. I ACCEPT your core improvement over my cylinder+box: a curved silhouette is not a crease, so a cylinder failure would be uninterpretable. A 5th solid that is ALL-PLANAR and CONCAVE (L-block or slotted block) is the sharper falsification — concavity is the one axis none of the four samples cover, it is what real CAD parts have (pockets/slots), and it directly stresses the visibility-fraction inlier-ratio statistic (valleys seen from fewer views) and may finally make min_views>=3 bind. Converged.

Two things I am LOCKING on top of your design — do not skip them:

## LOCK 1 — Zero-GPU precondition FIRST, report before any build.
Re-index geoline_step6.json across the EXISTING FOUR solids: does any single ABSOLUTE inlier-ratio value (not a per-scene percentile/keep-fraction) clear R>=0.35 @ P>=0.70 on all four simultaneously? This is free and it gates Candidate B. Report the answer explicitly. If NO absolute value clears the four, Candidate B (physical absolute threshold) is reported DEAD before the fifth solid is built, and the 5th-solid run proceeds purely as a test of the percentile rule + a direction probe.

## LOCK 2 — Reframe the primary honestly: this is a DIRECTION probe, NOT an adoption test.
You already put the non-regression leg on the record and noted the CUBE ALREADY VIOLATES it (-0.0464 recall vs its shipped 0.4046). That means kf 0.22 CANNOT be adopted as the frozen rule regardless of how the 5th solid lands — it is already a standing fail. So do not let a 5th-solid PASS read as "adopt kf 0.22". Freeze the pivot logic NOW:
- If 5th solid PASSES at kf 0.22 (R>=0.35 @ P>=0.70, clause off, no re-fit): the inlier-ratio-threshold FAMILY has legs on concave geometry -> next work searches for a rule WITHIN that family that does NOT regress any solid by >0.02 recall (the cube is the binding constraint to fix).
- If 5th solid FAILS at kf 0.22: the 4-solid GO was a coincidence and the inlier-ratio-threshold family does not transport to concave solids -> we abandon percentile-thresholding the ratio for solids and pivot to a different candidate seed statistic. Report straight.

## The one experiment (your design, frozen):
1. (LOCK 1 first, zero GPU) absolute-threshold read-off across the existing 4 from geoline_step6.json.
2. Build the 5th solid — all-planar CONCAVE (L-block or slotted block) — through the existing generator with its 3 self-checks. Train the IDENTICAL 3DGS recipe + pull field. Held-out TEST.
3. Run the EXACT frozen candidate: median-residual clause OFF, global keep-fraction 0.22 applied identically, NO per-object tuning, NO re-fit. Report P/R@1.5 at kf 0.22 FIRST, then the full keep-fraction sweep, then the 5-solid admissible-window width, then temporal ungated (trip-wire 3x, report P_pop only — do NOT gate).

## Pre-registered go/no-go (frozen NOW):
- PRIMARY (direction probe): 5th concave solid reaches R@1.5>=0.35 @ P@1.5>=0.70 at UNCHANGED kf 0.22, clause off, no re-fit. PASS -> family has legs, search for non-regressing rule. FAIL -> family dead on concave, pivot.
- NON-REGRESSION (standing, already failing on cube -0.0464): report each solid's recall delta vs its own shipped-rule point. kf 0.22 is NOT adoptable while any solid regresses >0.02.
- ROBUSTNESS: width of the 5-solid admissible keep-fraction window (a window alive only at 0.22 = fitting, not a constant).
- PUSH #1 (gates Candidate B): from LOCK 1 + the 5th solid, does any single absolute ratio threshold clear all 5? Yes -> B viable. No -> B dead.
- TEMPORAL: ungated, report P_pop, trip-wire 3x only.

MESH EVAL-ONLY throughout. Never fabricate. Report negatives straight. When done write out/GEOLINE_STEP8_RESULTS.md.
