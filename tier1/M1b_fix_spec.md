# Tier-1 / M1b-fix — Geometry-Gated DT to kill TEXTURE contamination

**Context:** M1b works mechanically (DT-pull moves linelets by the measured ~2.5px jitter; temporal
coherence WON: object-space flicker floor 0.27% vs image-space 2.13%, 8x). But the end-to-end gate
FAILS (chair P@1.5=0.69, target 0.85). Root cause, visible in out/m1b_chair_v0.png: seeds AND pulled
linelets land heavily on the chair's PATTERNED FABRIC — albedo/texture edges misread as geometric
creases, because the multi-view DT (used by both the M1a seed recipe and the M1b pull) is built on
RGB-Canny edges where a fabric print and a 30deg dihedral crease are photometrically identical.

Consensus pruning CANNOT fix this: texture edges are rank-3 view-consistent surface inliers, not
multi-view outliers. The fix is at the SIGNAL: gate the RGB-Canny edge by GEOMETRIC support from the
G-buffer (depth+normal), which is texture-blind.

**HARD INVARIANT — mesh-never-in-method-path.** Method touches ONLY gaussians + training RGB + cameras.
GT mesh is eval-only (mesh_oracle.py). Keep method modules free of any mesh import.

## Environment & assets (dss9)
- `source ~/bin/miniconda3/etc/profile.d/conda.sh; conda activate vfsdgs`, `CUDA_VISIBLE_DEVICES=1`.
- Work in `~/3dgs_line/tier1/`. Existing working code you MUST reuse:
  - `src/render.py` render_gbuffer -> {depth, normal, alpha} per view (this is the geometry source).
  - `src/dt_pull.py`, `src/linelet.py`, `src/linelet_prune.py`, `scripts/run_m1b.py` (the pull pipeline).
  - `scripts/explore/syn/final_recipe.py` (seed recipe; photo_edge_dt = the RGB-Canny DT to be gated).
  - `src/mesh_oracle.py` + `scripts/tune_lib.py` Harness (EVAL ONLY).
- Scenes: chair (dev/texture-stress), lego (hard-surface primary), ficus.

## STEP 0 — FALSIFICATION EXPERIMENT FIRST (do this before building anything)
The whole approach rests on one empirical claim: at a flat fabric print, the G-buffer geometry stays
FLAT (dihedral ~0, depth-step ~0) even though the color changes; at a true crease it does not. TEST IT.

- Write `scripts/explore/gate_falsify.py`. On chair, pick regions:
  (A) FABRIC-PRINT pixels: on the flat cushion where RGB-Canny fires but the surface is geometrically
      flat. (B) TRUE-CREASE pixels: on the wooden frame where a real dihedral edge exists.
  Label A vs B using the GT mesh (EVAL-ONLY here — this is a diagnostic, not the method): fabric =
  Canny-edge pixels with NO GT-mesh crease within 3px; crease = Canny-edge pixels WITH a GT crease within 2px.
- For each such pixel, compute the BILATERAL RIBBON measure from the rendered G-buffer (method-side,
  no mesh): sample depth+normal in two parallel ribbons Ω_L, Ω_R offset ±3px across the Canny edge
  direction (ribbon ~3px x 10px), fit a robust plane to each ribbon's back-projected 3D points, get
  dihedral theta = arccos(n_L·n_R) and depth-step Δd/d.
- Report the distributions: theta_95 and (Δd/d)_95 for FABRIC; theta_05 and (Δd/d)_05 for CREASE, plus
  histograms saved to out/gate_falsify_chair.png.
- DECISION (frozen thresholds, do not rationalize):
   * GATE CLEAN  -> fabric theta_95 <= 8deg AND (Δd/d)_95 <= 0.5%   AND crease theta_05 >= 18deg (or Δd_05>=2%).
                   Proceed with the vanilla bilateral ribbon gate; set operating theta=15deg, tau_depth=1.0%.
   * GATE LEAKS  -> fabric theta_95 >= 12deg  OR  (crease_theta_05 - fabric_theta_95) < 6deg.
                   Trigger PLAN B (below).
   * In between  -> report numbers, lean toward Plan B rank-1, ask before big build.
- PRINT the verdict clearly. This decides the architecture. Do NOT skip to building the gate before
  this runs.

## STEP 1 — build the gate (if STEP 0 says CLEAN)
- `src/geom_gate.py`: per view, M_geom = bilateral-ribbon mask (theta>=theta_thresh OR Δd/d>=tau_depth),
  computed from render_gbuffer depth+normal only (texture-blind). Then
  DT_pull_k = distanceTransform( Canny_RGB_k AND dilate(M_geom_k, 2px) ).
  KEEP the zero-distance valley on the Canny pixels (mask only SELECTS which Canny edges survive; it must
  NOT move the sub-pixel locus — this preserves the 0.27% temporal win).
- Wire this gated DT into dt_pull.py IN PLACE of the raw photometric Canny DT. Keep the optimizer
  identical: δ_max=5px, 3-point directional sampling, Huber δ≈2px, visibility gating.
- DUAL-THRESHOLD gating (seeds vs pull):
   * Seed gate (high recall): theta>=12deg OR Δd/d>=0.8%   -> filter the M1a seed proposal so we don't
     even seed on fabric, but faint creases survive.
   * Pull gate (high precision): theta>=20deg OR Δd/d>=1.5%.
- Anti-chatter: if hard binary gating drops a subtle crease in/out across adjacent trajectory frames,
  replace the hard mask with a logistic soft weight w=sigmoid((theta-theta_thresh)/tau) on the DT cost.

## STEP 2 — PLAN B (only if STEP 0 says LEAKS)
Rank-1: multi-view world-normal consensus — back-project the two ribbons to WORLD space across several
views, require Var_views(world dihedral) small (real crease: view-invariant world normals; albedo splat
ripple: camera-relative, varies with view). Rank-2: world-space dihedral SIGN stability along the edge.
Rank-3: depth-step-only gate (texture-immune but blind to coplanar creases; fast-path only).
Report which you used and why.

## STEP 3 — HONEST EVALUATION (institute NOW regardless of STEP 0 outcome)
- Freeze a view split: e.g. 80 train (pull), 10 val (tune gate thresholds/iterations), 10 test (report).
  The 2 old eval views must NOT be the only reporting views. Report P@1.5/R@1.5 and temporal on TEST ONLY.
- Temporal-floor guard: after the gate, recompute the flicker/temporal metric on held-out test views and
  confirm it did NOT regress from 0.27% (the gate must not reintroduce flicker via threshold chattering).
  Use A_temp = mean_t || π_{t+2}(L) - 2π_{t+1}(L) + π_t(L) || along the test trajectory; must stay ≤ baseline+0.02%.

## Definition of done
1. STEP 0 verdict printed with the fabric-vs-crease (theta, Δd) numbers + gate_falsify_chair.png. This is
   the single most important deliverable — it tells us if the whole approach is a clean win.
2. If CLEAN: run gated M1b on chair AND lego, report BEFORE/AFTER (raw-Canny vs geom-gated) P@1.5,R@1.5
   @1.5px and @2.5px, on the held-out TEST split; whether chair now passes P@1.5>=0.85 ∧ R@1.5>=0.75;
   n_linelets, runtime, VRAM; and confirm the temporal floor did NOT regress (A_temp table).
3. New viz out/m1b_gated_chair_v*.png (RGB | raw-Canny linelets | geom-gated linelets) so we can SEE the
   fabric linelets disappear.
4. Report ACTUAL numbers, never claim PASS without them. If STEP 0 says LEAKS, do STEP 2 rank-1 and report.
5. Do NOT git commit until I review. Stop after the gated run + temporal guard and show the numbers table.

## Pitfalls
- STEP 0 uses the GT mesh ONLY to LABEL fabric-vs-crease pixels for the diagnostic; the gate ITSELF
  (geom_gate.py) must use only the G-buffer, no mesh. Keep them in separate files.
- Reuse the proven camera convention (blender c2w -> opencv w2c via diag(1,-1,-1,1) then invert).
- Robust plane fit over ribbons (least-squares with a Huber/Tukey reweight or RANSAC-lite) — a couple of
  floater pixels in a ribbon shouldn't swing the dihedral.
- Batch on GPU; don't python-loop per edge pixel per view for the falsification (vectorize the ribbon sampling).
- Verify the gate did not just delete everything: report edge-pixel counts before/after gating per view.
