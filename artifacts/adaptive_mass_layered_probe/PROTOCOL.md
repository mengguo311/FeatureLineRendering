# Frozen adaptive mass layered probe amendment v1

Branch adaptive-mass-layered-line-probe; base HEAD 062d7ce73a740e1a817c82e57e516b395e45f417.
User approved replacement of fixed Top-8 engineering representation only.
INHERITED_PROTOCOL.md is incorporated in full. Its G1/G2/G3 formulas, scientific
gates, controls, splits, view selection, tolerances and stop rules remain unchanged.
No commit or push. Preserve every prior fixed-k artifact/output byte-for-byte.

## Replacement G0 representation
Primary tau=.90; diagnostic tau=.95. For each pixel use native final alpha
1-native_final_T and retain the shortest FIRST accepted front-to-back prefix
whose sum of float32 native-rule Talpha (accumulated float64) >= tau*native_alpha,
or Kmax events, or end of accepted stream. Diagnose Kmax 32,64,128 at both taus.
Empty native alpha has zero events; foreground ROI is native alpha>=.5.
No weight ranking, approximate projection or substitute sorting. Native conics,
original point_list and ranges are the sole contributor stream. Preserve native
equal-depth tie order and stream positions. A C++ reader using prior calibrated
native CPU replay arithmetic is allowed as in the inherited protocol; it consumes
actual pinned CUDA state, never CPU geometry projection/sorting. Deterministic
two-pass count/fill, flat CSR int64 offsets and original IDs, float32 z, alpha,
incoming T, Talpha, RGB, stream-position provenance. No dense HxWx128 allocation.
Native final T and replay final T remain separate; explicit full omitted tail RGB,
alpha and final background residual. Stop prefix storage at target, still traverse
remaining accepted stream to calculate tail. Float64 cumulative target avoids
rounded ratios changing stopping decisions. No tolerance relaxations.

G0 TRAIN view1 native800 for lego/chair/drums/ficus, all six representations each.
Report ROI and all-pixel K p50/p75/p90/p95/p99/max, target-reached fraction,
aggregate captured/native alpha, stored and total accepted events, CSR bytes and
dense-equivalent bytes. Choose smallest common Kmax with primary tau=.90 giving
>=.90 aggregate foreground alpha AND >=.80 foreground pixels each capturing >=.90
native alpha in every scene, with ALL inherited noncoverage checks passing.
If none through128 passes STOP ENGINEERING_NOT_READY; scientific NOT_EVALUATED.
Do not use tau=.95 to rescue primary G0. Reached-target fraction for .95 reports .95;
its fraction reaching .90 is separately reported. Finish all four calibrations.

## Frozen compression before any line outputs
Inherited d=max(.002*front, median valid abs front differences in 5x5,1e-12).
Adjacent relative depth gap >3 splits a layer. Exclude central self difference;
valid neighbor means both front depths >0, outside image excluded. Max retained
layers=4, earliest depth layers retained; overflow stays an explicit residual,
never merged across a gap. Minimum seeding mass=.05*native_alpha, plus inherited
absolute layer mass>=.1 and A>=.5 support. Keep all layer diagnostics in layer CSR,
contributor-to-layer assignment and per-pixel retained/overflow/tail mass and RGB.
Layer mass/depth/histograms use original absolute weights, no tail renormalization.
Only implement compression after adaptive G0 qualifies; no line outputs before freeze.

## Conditional science and execution
G1/G2/G3 are verbatim inherited. Keep k4/8/16 early-prefix controls and add tau .95
and all Kmax sensitivities, never per-scene rescue. Complete native resolution
contact sheets, soft fields and raw bands at each reached applicable stage.
No evidence maps/controls or video claims for unreached stages. G2 F-only construction
then C/DEV evaluation; TEST sealed throughout. GPU1, sequential scenes, OMP/BLAS/MKL=1.
Leave unrelated processes intact. Landlock before assets, strace native opens
including startup, explicit audited imports. Strict one behavior RED/minimal GREEN
before next test, journal commands/source/output hashes. Full targeted/suite
verification and full deterministic reached-stage rerun. Native800 figure panels,
fixed scales, all representations; layout changes preserve array/metric hashes.
Inspect every final figure. Report commands, changed files, gates, tests, findings,
limitations in /home/u00134/codex_astra_adaptive_mass_layered_probe_report.md.

Output family artifacts/adaptive_mass_layered_probe and out/adaptive_mass_layered_probe.
G0 each scene/config NPZ flat events/offsets, native RGB/alpha, tail, camera, diagnostics;
JSON calibration/memory/coverage, full sheets; GATES smallest common Kmax.
Run and rerun exclusive-create. Later stages only on prior PASS.

INPUTS.json SHA256: `fd3e6a6885c0099d1a3af908eeb4aaca564cb87db0e2e5300fd59976fee46c86`

INHERITED_PROTOCOL.md SHA256: `b4fbd872283d0392ef5d11b38a620f5ed37bf2342b5ed3f4f35ac5b9b7d455a6`

APPROVED_PLAN.md SHA256: `018a2e21d70f9d9148c037d55e3f8701e0aa7b1f61d5bdaa428c44cc014340b1`

PRESERVED_FIXED_K.json SHA256: `a1c31ae3fe36dd4d3c2c8637a2ff69062732bef3eb4488480700c30db208181f`

BASE_TRACKED.json SHA256: `e7dcd278055dd6ff311d8ed73be6d6b01864c788f6d39732dfa985340591b760`
