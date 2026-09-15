# Experiment B — Truck M1a seeds DONE; next = mesh-free carrier build + temporal go/no-go

Status 2026-09-15 (driver-side; agent login-expired since ~09:02 Tokyo, `/login` needs
interactive OAuth, unrecoverable headlessly — driver ran the shipped recipe directly).

## DONE THIS FIRE (verified, frozen recipe, option (a) verbatim)
- Blocker #4 CLEARED: render.render_gbuffer + photo_edge_dt run on the Truck ingestion
  source. cam0 gbuffer 1.1s, alpha_fg_frac 0.740, depth_finite 0.919.
- photo_edge_dt on real jpg (opaque -> else branch, no alpha composite): edge_px_frac
  0.0187 vs synthetic target ~0.03. Real photometry did NOT blow past 3% (courtyard is
  low-texture / defocused) — the #3 density-drift worry did not materialize. Cfgs FROZEN.
- M1a seeds (scripts/truck_seeds.py full): 902,732 de-floatered gaussians -> 198,601 seeds
  (overall recipe, keep_f 0.22, N_VIEWS 25, EDGE_CFGS frozen). 484s. Saved
  out/truck_m1a_seeds.npz. NO method change: only common.load_cameras/load_gaussians
  redirected to src/truck_ingest (camera+gaussian adapter).
- NOTE the pre-registered falsifiable prediction (#2 background-edge contamination) is NOT
  yet testable — seeds were extracted but not yet scored/rasterised. 198,601 seeds is a
  large fraction; whether they land on the truck vs courtyard is the open question the
  carrier build + render will answer. Do NOT conclude either way yet.

## NEXT STEP (carrier build, mesh-free) — the method path is separable
run_m1b.py lines 245-296 (seeds -> linelet.init -> dt_pull.build_field -> dt_pull.pull ->
linelet_prune.consensus_prune) are ALL mesh-free. Only lines 311+ (Harness -> mesh_oracle)
need the GT mesh, which Truck lacks. Build a mesh-free Truck runner that:
1. Redirects common.load_cameras/load_gaussians to truck_ingest (as truck_seeds.py does).
2. Reuses out/truck_m1a_seeds.npz (do NOT re-extract — 484s).
3. dt_pull.build_field(scene, g, keep, cams, rgb_paths, views, ...) takes cams/rgb_paths
   EXPLICITLY; scene arg is only a cache key -> pass "truck". Use view_split.split(251)
   for TRAIN/VAL/TEST (generic, n_views param).
4. Runs linelet init + pull + consensus_prune, SAVES out/linelets_truck.npz. STOP before
   the Harness banner — do NOT import tune_lib for Truck (no mesh).
Then run scripts/m1b_stroke_temporal.py (fg_only) + boiltest for ink_churn on Truck for the
FROZEN go/no-go: fg_only P_pop >=5x @240f AND ink_churn >=8x consecutive AND strip visibly
steadier; NO-GO if either misses OR <300 strokes/frame. Matched-precision non-transportable
(no GT mesh). LOOK at the render before claiming steadiness.

## HARD DISCIPLINE
Mesh eval-only (Truck has none -> mesh-free only). Frozen recipe, no per-scene tune. Object
space. Report the go/no-go straight — a NO-GO (esp. from background-edge contamination) is a
critical honest finding. Do not re-inflate any audited-killed claim.
