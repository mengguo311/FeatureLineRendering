# STEP 2 DISPATCH — 2DGS reconstruction test (frozen go/no-go)

DIRECT RUN, no heavy workflow.

## Why (design-argue reconciliation)
STEP1 is banked NO-GO. Your own diagnosis is accepted: the crease signal is in the
OBJECT but smoothed out of THIS reconstruction — vanilla 3DGS normal field reads median
crease dihedral 10.20 deg vs GT 40.89-90 deg, and the chair precedent shows the SAME
estimator jumps 0.696 (vanilla) -> 0.967 (2DGS). So the 2DGS reconstruction test IS the
right next lever.

PUSHBACK (the sharpening): STEP1 proved the vanilla lift is ENTIRELY on EASY negatives and
DIES on the prune-survivors (AUC 0.3672, below chance, gap reversed, both splits). A 2DGS
rerun that only reports AUC-vs-all-off-crease would re-measure the wrong thing. The gate is
therefore pinned to the HARD negative class.

## Experiment
1. Train a 2DGS on cadpartA using the SAME scene-agnostic settings you would use for any
   solid — no per-scene tuning of anything.
2. Rerun BOTH arms VERBATIM: reuse diag2dgs.surfel3d_dihedral and diag2dgs.ribbon_dihedral
   unchanged, frozen rho=4.0 xi=0.25 n_min=5. Only substitution: the 2DGS surfel cloud
   replaces the vanilla cloud in the 3D arm. Held-out TEST plus VAL. Mesh EVAL-ONLY.

## PRE-REGISTERED FROZEN GO
AUC(dihedral; TrueCrease vs off-crease PRUNE-SURVIVORS) >= 0.75 on TEST, AND VAL agrees
within 0.03.

## Supporting diagnostics (report, NOT gated)
- median crease dihedral recovery toward GT 40.89-90 (vanilla was 10.20)
- AUC vs all-off-crease and vs DexiNed-hi off-crease, for comparability with STEP1

## NO-GO
Report straight. It means even a surfel reconstruction cannot separate creases from the
RESIDUAL negatives on a clean solid — which redirects the arc to the candidate-source/pool
question (plan step 4), not the estimator.

Write results to out/GEOLINE_STEP2_2DGS_RESULTS.md. No per-scene tuning anywhere.
