# Experiment B — Truck camera adapter RESOLVED (2026-09-15, driver-side)

## What was blocking
Previous fire: frozen vanilla 3DGS Truck trained (2.58M gaussians, iter 30000), ply
field-identity to the crown `load_gaussians` path VERIFIED, but the M1b feature-line
pipeline needs `common.Camera` (K + w2c) and there was no camera adapter for Truck's
COLMAP-estimated poses. Flagged "camera-only adapter to be design-argued with agent."
Agent has been login-expired (interactive OAuth `/login`, unrecoverable headlessly) since
~09:02 Tokyo, so resolved driver-side per the loop's driver-side authority.

## What landed
`src/truck_ingest.py` — alternate camera+gaussian SOURCE for the SHIPPED M1b pipeline.
NOT a method change (the feature-line method is convention-agnostic on K+w2c; this is the
ingestion analogue of readColmap vs readNerfSynthetic in the trainer).
- Camera source = `out/3dgs_truck/cameras.json` written by the FROZEN training itself, so
  the eval uses byte-identical cameras to the rendered model.
- Convention (graphdeco camera_to_JSON): position=camera center world, rotation=c2w
  (OpenCV +Y down/+Z fwd) => w2c_R=R.T, w2c_t=-R.T@pos.
- Gaussian loader parses scale_0..2 / rot_0..3 / f_dc_0..2 byte-identically to
  common.load_gaussians.

## Validation (numeric, honest — NO visual verdict this fire, no vision tool in cron)
- Convention A/B (scripts/truck_cam_ab.py): A (R.T) on-screen median **0.324** vs
  transposed B (R) **0.169** — A clearly dominates. 404k dense splatted px at cam0.
- In-front frac median 0.667 on all 2.58M gaussians (incl. courtyard background floaters);
  consistent with the earlier 72.2% on-screen for the 136k on-surface SfM points.
- Smoke through SHIPPED common.project: 251 cams, 2.58M gaussians, image paths resolve,
  cam0 on-screen frac 0.428, SMOKE OK.
- NOT yet done: LOOK at a render (deferred — no vision tool this fire), run M1b + temporal
  harness, score the frozen go/no-go. Those are the next fire.

## Frozen go/no-go (UNCHANGED, restated)
GO iff ALL: fg_only P_pop ratio >=5x @240f AND ink_churn ratio >=8x consecutive AND strip
visibly steadier. NO-GO if either misses OR <300 strokes/frame. Mesh-free eval only;
matched-precision non-transportable (no GT mesh on real capture). A NO-GO is a critical
honest finding, not a failure.

## Note on launch record
out/B_TRUCK_LAUNCH.md says "2DGS" — superseded: project pivoted to vanilla 3DGS because the
2DGS ply lacks scale_2 (not method-identical to crown carriers). The frozen model of record
is out/3dgs_truck (3DGS, 2.58M pts).
