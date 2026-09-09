# STEP 7 — NO-CODE DESIGN ARGUE (no code, no run; synthesis + adversarial critique only)

Context: Step 6 measured the threshold-family ceiling. Verdict = FRAGILE GO. Deleting the shipped median-residual clause and thresholding the inlier-ratio at a SINGLE GLOBAL keep-fraction 0.22 puts all 4 solids over R0.35 @ P0.70 — but at exactly 1 of 25 grid points, margins +0.0082 (cube R) and +0.0200 (icosa P). Untested: temporal cost, non-regression vs cadpartA shipped 0.4206/0.8139, and any 5th solid.

## The two candidate next steps — critique BOTH, do not just pick.

### CANDIDATE A: ADOPT the clause deletion + global kf 0.22 as the new frozen rule, then run its missing validation legs (temporal + non-regression + a 5th held-out solid cylinder+box).

### CANDIDATE B: REJECT kf 0.22 as fragile AND as covertly per-scene-adaptive, and instead seek a PHYSICALLY-MEANINGFUL ABSOLUTE threshold on the ratio statistic (a single number applied identically, no per-scene percentile) — scene-agnostic BY CONSTRUCTION per the discipline.

## MY PUSH (argue back on these, do not concede reflexively):
1. keep-fraction 0.22 is a PERCENTILE of each solid own inlier-ratio distribution. That READS the scene distribution to pick the cut — so the actual threshold VALUE differs per scene. Is that a frozen scene-agnostic constant, or a smuggled per-scene adaptation dressed as a constant? Defend or concede.
2. A 1-of-25 admissible point with +0.008 margin is indistinguishable from a 4-solid coincidence. The DECISIVE cheap falsification is a 5th held-out solid at the FROZEN kf 0.22 (clause off, NO re-fit). If it fails there, the GO was noise.
3. Deleting the median-residual clause removes the operative precision guardrail (Step 6 showed max_med=1.5 was the binding clause). What is the temporal/precision-robustness cost of running WITHOUT it?

## CONVERGE ON ONE experiment with a PRE-REGISTERED go/no-go. My proposed frozen design (challenge it):
- Build the 5th solid cylinder+box via the make_cad path (~4 GPU-min), stand up 3DGS + pull field, held-out TEST.
- Run the EXACT frozen candidate: median-residual clause OFF, global kf 0.22, applied identically. NO per-object tuning, NO re-fit of 0.22. Report P/R@1.5.
- ALSO report (info only) whether any single ABSOLUTE ratio threshold clears all 5 — to answer push #1.
- GO/NO-GO (frozen NOW): the 5th solid must reach R>=0.35 at P>=0.70 at the UNCHANGED kf 0.22. If it does, kf 0.22 survives an out-of-sample solid and adoption is defensible. If it does not, we report the fragile GO as a 4-solid artifact and pivot to CANDIDATE B (absolute/physical threshold).

Answer as: expert synthesis, then adversarial critique of my design, then your ONE converged experiment + go/no-go. NO CODE, NO RUN yet.
