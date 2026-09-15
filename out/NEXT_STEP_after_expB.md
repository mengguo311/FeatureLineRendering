# Exp B COMPLETE (real-capture Truck) — NO-GO. Next step for agent on revival.

## Result (banked, out/B_TRUCK_TEMPORAL.json, mesh-free, fg_only, 240 consecutive REAL cams)
- P_pop ratio Canny/ours = 1.55x  (pre-reg need >=5x -> MISS)
- ink_churn ratio = 1.10x         (pre-reg need >=8x -> MISS)
- strokes/frame = 1515            (need >=300 -> PASS: primitive DOES survive estimated poses)
- VERDICT: NO-GO. Carrier built fine (16171 strokes from 239020 linelets); the TEMPORAL-STABILITY ADVANTAGE collapses.

## Honest interpretation (do NOT overclaim either direction; this needs the confound isolated)
Absolute: ours churn 0.82 < Canny 0.90 (still better), but NOT 8x. On synthetic PERFECT poses chair=28x/lego=9.2x.
Two unseparated confounds for the collapse:
  (1) ESTIMATED (COLMAP) poses -> object-space strokes reproject with pose error -> they jitter too; the by-construction stability erodes. This is the fatal-and-fixable reviewer objection MATERIALIZED.
  (2) Truck may be less uniformly textured / larger-scale / more specular than chair-lego -> smaller intrinsic gap.

## Pre-registered CHEAP confound-isolation ablation (design-argue then run, mesh-free):
Take the SYNTHETIC chair (where we already have 28x with PERFECT poses). Inject POSE NOISE of COLMAP magnitude (estimate Truck reprojection RMS, apply matched rotation+translation jitter to chair eval cams ONLY, method/carrier UNTOUCHED). Re-run the SAME temporal harness.
  - If chair ratio collapses toward ~1x under matched pose noise -> the crown advantage is largely a PERFECT-POSE ARTIFACT. Thesis must be re-scoped to "perfect-pose synthetic" and stated as a HARD limitation.
  - If chair ratio stays high under pose noise -> the Truck NO-GO is a TEXTURE/scene confound, and a more chair-like real capture (fabric toy) is the honest retry.
This ablation is the make-or-break for what the paper can claim. Freeze go/no-go BEFORE running.

## Thesis status: the real-pose test came back NO-GO. Do NOT re-inflate the crown to real capture. Report negative straight.

## Driver addendum 2026-09-15 20:43 (agent still login-expired) — COLMAP reproj magnitude measured
Read Truck COLMAP points3D.bin directly (read-only): n=136,029 points.
reproj residual (FULL-res 1957px): mean 0.764 px, median 0.664, p90 1.41, p95 1.70, max 3.99.
At the half-res eval (979px) that is ~0.38 px mean.
INTERPRETATION (honest, bounded): the bundle-adjustment residual is SUB-PIXEL, i.e. COLMAP
converged TIGHTLY on Truck. Residual is NOT the same as extrinsic pose error (a well-constrained
residual can still hide pose drift under weak-baseline degeneracy), so this does NOT by itself
prove poses are near-perfect. BUT it weakens the pure pose-error explanation and shifts weight
toward confound (2): Truck is larger-scale, specular tarp/wheels, less uniformly textured than
chair/lego -> smaller intrinsic temporal gap. The chair pose-noise ablation is STILL the make-
or-break, and this sub-pixel number is the honest magnitude to inject (matched, not guessed).
NOT launched this fire: the pose-noise injection is subtle and the loop mandates design-arguing
it with the dss9 agent, which is login-expired (headless /login unrecoverable). Awaiting agent
revival OR an interactive /login to run it adversarially rather than solo.
