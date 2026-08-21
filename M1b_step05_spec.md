# STEP-0.5 : ALBEDO(SH-DC)-STEP falsification  (mesh-never-in-method invariant holds; mesh only LABELS pixels in the diagnostic)

## Why
STEP-0 geometry gate is falsified: fabric bilateral dihedral theta p95=79deg overlaps true-crease p05=5deg. Geometry cannot separate print from crease on frozen vanilla 3DGS (the fabric pseudo-geometry is baked as real tilted splats -> so ANY normal/coplanarity feature is poisoned by the same 79deg tilt, including a point-to-plane coplanarity ratio). Do NOT reuse fitted normals.

## Hypothesis (INVERT the gate)
Use ALBEDO not geometry. A printed line = a DISCONTINUITY in view-independent diffuse base color (SH degree-0 DC term); the underlying material/surface is continuous. A true geometric crease = same material on both sides => the SH-DC albedo is CONTINUOUS across it even though the rendered/shaded image shows an edge. So:
  fabric-print pixels  -> LARGE SH-DC albedo step
  true-crease pixels   -> SMALL SH-DC albedo step
The gate then SUPPRESSES (removes) high-albedo-step edges rather than confirming creases with geometry.

## Task = FALSIFICATION FIRST (do not build the gate yet)
Reuse the labeling/pixel-sampling from gate_falsify.py (same fabric-print vs true-crease pixel sets, mesh labels EVAL-ONLY).
For each labeled edge pixel, compute ONE scalar: bilateral SH-DC albedo-step
  s = || c_L - c_R ||   where c_L,c_R = mean SH degree-0 DC RGB (the 3 f_dc channels -> RGB via 0.5+SH_C0*f_dc, NO view-dir eval) of the frozen Gaussians on the two sides of a +/-3px bilateral ribbon (same ribbon geometry as gate_falsify).
Report the distributions: fabric s (p05,p50,p95) vs crease s (p05,p50,p95), on chair AND lego, TEST views only.

## Frozen decision thresholds (report verdict explicitly)
- GATE CLEAN (albedo-suppression viable): fabric s_p05 >= 1.6 * crease s_p95  (clear separation, print bright vs crease dull in albedo).
- GATE LEAKS: fabric s_p05 <= crease s_p95  (overlap) OR separation ratio < 1.2.
If CLEAN: next fire builds albedo_suppress.py (remove seeds whose bilateral albedo-step > tau, tau at the crossover), re-run held-out P/R, temporal-floor guard must not regress (object tol flicker ~0.9% must stay ~3x below image).
If LEAKS: albedo inversion also dead -> fall back to HONEST SCOPING (report lego/CAD hard-surface as primary gate scene; chair as texture-FP-density stress only).

## Constraints
- CUDA_VISIBLE_DEVICES=1, only u00134 processes, GPU tight ~3GB.
- Output: out/m1b_albedo_step_falsify_{chair,lego}.json + a 2-panel histogram png.
- DO NOT commit/publish anything to GitHub this run. Just run the diagnostic and print the verdict.
