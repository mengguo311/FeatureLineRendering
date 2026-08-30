# CONDLAW-3-PRE Stage-1.5 — same-statistic lego re-anchor, THEN amended freeze

Driver decision (argued with agy, one round; agy strongly concurred, I refined the threshold).

## Why
The frozen pre-registration's PRIMARY claim is monotonicity lego<ship<chair on DRR@80.
But the two anchors were measured with DIFFERENT statistics:
  - chair 0.986 = chair-lineage (2DGS rendered-normal ribbon theta_normal on mesh-refined flat/sharp classes)
  - lego  0.512 = lego-lineage (mesh dihedral on TEED-defined decals)
Stage 2 scores ship with the CHAIR-lineage pipeline. So the test is clean at the chair end
but CROSS-LINEAGE at the lego end -> confounds flat-mass effect with statistic-change effect
at the load-bearing lower anchor. Since lego already has a trained 2DGS on disk, a same-statistic
lego anchor is ~free. Get it BEFORE unblinding ship.

## Tasks (do in order; do NOT touch ship / do NOT unblind ship in this step)

1. COMMIT the current frozen Stage-1 pre-registration to branch m1b-milestone.
   It is a genuinely a-priori, mesh-only artifact (ship rho_flat=0.145 and the ship SELECTION
   are frozen before any DRR for any candidate exists; 332/332 temporal manifest re-verified).
   Locking it timestamps the a-priori status. Use a clear honest message, e.g.:
   "CONDLAW-3-PRE Stage 1: frozen a-priori mesh-only pre-registration selecting ship
    (rho_flat=0.145, D_hat=0.803, band [0.723,0.883], primary=monotonicity lego<ship<chair);
    debiased area-uniform rho_flat estimator; audit folded in; 332/332 temporal OK."
   Stage e the condlaw3pre_* scripts/out/md and commit. Push to origin m1b-milestone.

2. SAME-STATISTIC lego re-anchor. Run the chair-lineage pipeline on lego (2DGS on disk, no vanilla):
     scripts/condlaw_chair_test.py --scene lego --views test --no_vanilla
   Report the chair-lineage DRR@80(lego) = lego'. This uses held-out TEST split, MeshOracle labels,
   mesh EVAL-only (never in method path). If the script needs a small arg to compute DRR@80 the
   same way chair 0.986 was computed, mirror the chair invocation exactly so the number is
   apples-to-apples with 0.986.

3. AMEND the calibration UNCONDITIONALLY (my refinement of agy's threshold): recompute the affine
   fit and ship's D_hat + band from anchors (lego', chair=0.986) — do NOT keep the old lego=0.512
   band if lego' differs. Freeze the amended prediction to out/condlaw3pre_amend.json and append a
   short section to out/CONDLAW3PRE_RESULTS.md. Report BOTH the old (lego=0.512) and new (lego')
   D_hat/band for ship side by side.

## GO / NO-GO to proceed to Stage-2 ship (frozen now)
- Sanity gate: |lego' - 0.512| should be modest. If lego' lands within roughly [0.40, 0.62]
  (near the original defended anchor, comfortably below chair 0.986), the chair-lineage anchor is
  consistent -> GO: freeze amended ship band, proceed to Stage 2 ship next fire.
- If lego' >= 0.723 (collapses toward chair under the uniform metric): NO-GO to the frozen band.
  The original calibration slope was a metric artifact. Re-anchor the law on (lego', chair),
  recompute ship D_hat+band, and report that the old 0.512 lego number was lineage-specific.
  Still proceed to ship next fire, but under the AMENDED band only.
- Either way: ship is measured with the chair-lineage pipeline ONLY, and the primary monotonicity
  test becomes lego' < ship < chair (all same-statistic).

## Invariants (hold all)
mesh EVAL/label only (never method path); held-out TEST for eval; do not touch the protected
temporal manifest (re-verify 332/332 at the end); CUDA_VISIBLE_DEVICES=1, u00134 procs only;
new artifacts keep the condlaw3pre_ prefix. Do NOT fabricate — every number from a real run.
