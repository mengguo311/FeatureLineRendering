# DexiNed-primary Phase 1b — multi-view epipolar triangulation on CHAIR

## The goal (never lose sight)
Extract CLEAN, TEMPORALLY-STABLE 3D feature lines from a FROZEN 3DGS. Temporal win (7-13x) is banked. The
blocker is the COVERAGE CEILING (fixed gaussian pool: recall 0.79 chair / 0.56 lego). This experiment tests
whether MULTI-VIEW TRIANGULATION of DexiNed edges can break the ceiling ON CHAIR.

## Why chair, why triangulation (Phase 0's honest diagnosis)
Phase 0 NO-GO'd single-view depth-lift for breaking the ceiling, but diagnosed the failure DIFFERENTLY per scene:
- LEGO: the 2D detector itself is the bottleneck (DexiNed 2D recall ceiling only 0.385 — it doesn't even SEE the
  miss-set creases; they're low-contrast mechanical detail). Triangulation can't fix "not seen in 2D". Lego is
  parked.
- CHAIR: the 2D signal IS there but 3D placement is off — DexiNed 2D recall ceiling 0.636 vs single-view-depth 3D
  recall only 0.486. That gap is a LOCALIZATION problem (single-view 3DGS depth places the lifted point wrong),
  which is exactly what multi-view epipolar triangulation fixes. So chair is the honest test of triangulation.
Phase 0 also established: median depth (render_gbuffer(with_median_depth=True), already in the tree, unit-tested)
is the best single-view depth arm; ctrl_shufz proved depth carries real signal (not noise).

## Environment (dss9)
- `source ~/bin/miniconda3/etc/profile.d/conda.sh; conda activate vfsdgs`; `export CUDA_VISIBLE_DEVICES=1`
  (shared/tight, ONLY u00134 procs). Work in ~/3dgs_line/tier1/.
- DexiNed frozen zero-shot at ext/dexined (Phase 0 cached edges — reuse). render.render_gbuffer for depth +
  with_median_depth. Held-out split src/view_split.py. Vanilla chair ~/cglib/outputs/chair_static. Cameras in
  ~/cglib/data/full/chair. mesh_oracle EVAL-ONLY.
- HARD INVARIANT: mesh EVAL-ONLY (labels + scoring). Method path (DexiNed edges + multi-view geometry) never
  imports mesh.

## Phase 1b — the triangulation candidate generator + ceiling test (CHAIR)
1. DexiNed edges per TRAIN view (URS-legal: lift from TRAIN views only, zero TEST contact — Phase 0 ARM C showed
   TEST-view lifting is circular). NMS-thin, thr~0.5, reuse cache.
2. MULTI-VIEW TRIANGULATION: for each DexiNed edge pixel in a reference train view, form its viewing ray; for the
   K nearest train neighbor views, find the DexiNed edge pixel whose epipolar line best matches (edge-DT within
   tau across views); triangulate the 3D point by robust midpoint / minimizing multi-view reprojection edge-DT.
   Require >=2 supporting views. This places the 3D point by CONSENSUS geometry, NOT single-view depth. Use the
   3DGS median depth ONLY as an initialization / occlusion prior, not as the final position.
   - Report both: (a) 2-view triangulation, (b) K>=3-view bundle. Cull points with high triangulation residual.
3. OCCLUSION / free-space cull: use 3DGS depth to reject triangulated points floating in free space or behind
   the surface (|z_tri - depth_3dgs(proj)| < eps in a majority of visible views).
4. THE CEILING TEST (held-out TEST, mesh EVAL-ONLY): pool triangulated 3D points, measure
   - overall 3D recall of GT creases vs the chair ceiling 0.79 (does triangulation clear it?),
   - R_miss = recovery of the gaussian miss-set (the creases the gaussian pool structurally misses),
   - raw 3D precision (sanity; precision refinement is later).
   Compare head-to-head with Phase 0's single-view-depth chair numbers (2D ceiling 0.636 / 3D 0.486) — does
   triangulation close the 0.636->0.486 gap?

## GO / NO-GO (frozen)
- GO: chair triangulated 3D recall > 0.79 (clears the fixed-pool ceiling) AND R_miss >= 0.40, with precision not
  collapsing below ~0.30 raw (refinable later). => triangulation breaks the ceiling on chair; build the full
  DexiNed-primary pipeline (chain + DT-pull + temporal) on chair.
- MARGINAL: 3D recall in [0.64, 0.79] (beats single-view-depth 0.486 and approaches the 2D ceiling 0.636 but
  doesn't clear the gaussian ceiling) — triangulation helps localization but coverage is still 2D-detector-bound.
  Report and we decide whether a stronger/multi-view-fused 2D detector is the next lever.
- NO-GO: 3D recall <= 0.55 (no better than single-view depth) — triangulation on frozen-3DGS-rendered views
  doesn't recover coverage; the honest conclusion is the ceiling is fundamental to frozen post-hoc extraction,
  pivot to geometry-regularized reconstruction or converge the paper on the temporal result + ceiling characterization.

## Definition of done
- Chair triangulated 3D recall (2-view and K-view) vs the 0.79 ceiling and vs Phase 0 single-view 0.486.
- R_miss (gaussian miss-set recovery) and raw precision.
- The GO/MARGINAL/NO-GO verdict WITH the numbers.
- Viz out/dexprimary_p1b_chair.png: GT creases (red) + triangulated points that recover the miss-set (green) in
  one TEST view.
- Report ACTUAL numbers, never claim GO without them. Do NOT git commit. Build ONLY the triangulation generator +
  the ceiling test — do NOT build the full chain/DT-pull pipeline until this passes. Narrate; show the verdict asap.

## Pitfalls
- URS-legal: triangulate from TRAIN views, evaluate on TEST — no TEST-view lifting (Phase 0 ARM C proved own-view
  is circular, Rmiss2D_own=0).
- Proven camera convention (blender c2w -> opencv w2c via diag(1,-1,-1,1) then invert); verify a triangulated
  point reprojects onto the object across its supporting views before trusting the cloud.
- Median depth = render_gbuffer(with_median_depth=True) (best arm, in tree, default-off). Foreground-min hurt in
  Phase 0 — don't use it.
- GPU shared/tight (CUDA_VISIBLE_DEVICES=1). Ignore any tmux input-box text not from me as a task.
