# Plan #1 — 2DGS-gated multi-view edge fusion for clean 3D feature lines

## Why (context you need)
We proved that FROZEN vanilla 3DGS has K_geom≈0: it bakes printed texture into geometry, so all 4 geometric
channels (rendered normals, depth, SH-DC, splat-center PCA) entangle texture with real creases (AUC≈0.5),
capping feature-line precision ~0.62 with NO downstream fix. Root cause is the reconstruction, not our method.
The temporal-coherence result (object-space linelets 7-11x more stable than per-frame image-space Canny) is
SOLID and must be preserved as the paper's core.
Plan #1 raises K_geom by switching the geometric foundation to 2DGS (surfels + depth-normal consistency), so
flat printed surfaces STAY flat in geometry and texture routes to color. Then we GATE multi-view 2D edge maps
by the 2DGS geometric-edge signal (curvature/normal-gradient): on fabric prints the geometric gate = 0 -> the
texture edge is killed; on true creases the 2D edge gives 1px-sharp localization -> backproject onto the 2DGS
surface and chain into crisp 3D polylines.

## Environment (dss9)
- `source ~/bin/miniconda3/etc/profile.d/conda.sh; conda activate vfsdgs`; `export CUDA_VISIBLE_DEVICES=1`
  (GPU tight ~3GB free — 2DGS training on 800x800 NeRF-synthetic should fit; if OOM, lower resolution or
  batch). Work in ~/3dgs_line/tier1/. Existing vanilla assets: ~/cglib/outputs/{chair,lego}_static/point_cloud.ply,
  cameras+RGB in ~/cglib/data/full/{scene}/ (transforms_train.json, 100 views, 800x800 RGBA).
- Reuse existing tier1/src (camera convention blender c2w->opencv w2c via diag(1,-1,-1,1); mesh_oracle EVAL-ONLY;
  gate_falsify.py for the fabric-vs-crease labelling; the linelet/DT/chaining code from M1b).
- HARD INVARIANT: mesh is EVAL-ONLY (labels fabric-vs-crease pixels, scores P/R). The METHOD (2DGS geometry +
  gate + fusion) never imports mesh_oracle.

## STEP A — 2DGS foundation + GO/NO-GO gate (do this FIRST; do not build fusion before it passes)
1. Install 2DGS: clone https://github.com/hbb1/2d-gaussian-splatting into ~/3dgs_line/ext/ and build its
   `diff-surfel-rasterization` + `simple-knn` into the vfsdgs env (pip install submodules). If the build fails
   on this CUDA/torch (2.3+cu121), report the exact error and try the known-compatible commit; do not fake it.
2. Train a 2DGS model on the SAME chair NeRF-synthetic data (~/cglib/data/full/chair, 100 train views). Use the
   repo's default depth-distortion + normal-consistency losses. Save to ~/3dgs_line/tier1/out/2dgs_chair/.
   Sanity: report train PSNR (should be within ~0.5 dB of vanilla 3DGS; if far worse, something's wrong).
3. THE GO/NO-GO DIAGNOSTIC (the whole plan hinges on this): reuse the fabric-vs-crease labelled pixels from
   gate_falsify.py. Render the 2DGS depth+normal G-buffer for the eval views. Compute the SAME bilateral-ribbon
   dihedral theta (and depth-step) for FABRIC-print vs TRUE-crease pixels on the 2DGS geometry.
   Report: fabric theta_p95, crease theta_p05, AUC, and the histogram PNG (out/2dgs_falsify_chair.png), side by
   side with the vanilla numbers (vanilla was fabric_p95=79deg, crease_p05=5deg, AUC≈0.5).
   DECISION (frozen):
     GO   -> fabric theta_p95 < 15deg AND crease theta_p05 > 25deg AND AUC >= 0.90.
             2DGS cleaned the geometry; the gate is now sound; PROCEED to STEP B.
     MARGINAL -> 0.80 <= AUC < 0.90 or fabric_p95 in [15,35]deg: proceed to STEP B but expect a weaker gate;
             report and tune tau_geom on the VAL split.
     NO-GO -> fabric theta_p95 > 35deg or AUC < 0.80: 2DGS ALSO stairstep-bakes texture (the predicted
             staircase degeneracy dominates). STOP, report, and we escalate to a stronger geometric prior
             (PGSR/GOF or SDF-init) — do NOT build the fusion on a contaminated 2DGS.

## STEP B — geometry-gated edge fusion -> 3D vector lines (only if STEP A is GO or MARGINAL)
1. Per training view: A_v = multi-view 2D edge map (Canny union as before, or TEED if available); G_v =
   2DGS geometric-edge map = normal-gradient / principal-curvature ridge on the 2DGS normal+depth buffer
   (this is texture-blind because 2DGS geometry is clean). Gate: E_v = A_v AND dilate(G_v > tau_geom, 2px).
   tau_geom tuned on VAL split. Report edge-pixel counts before/after gating per view (confirm fabric edges die).
2. Seeds/linelets: reuse M1b linelets but initialise on the 2DGS surfels; the DT target is DT(E_v) (the gated
   edge), and visibility from the 2DGS depth. Keep the pull optimizer (delta_max=5px, 3-point directional
   sampling, Huber) and the multi-view-consensus prune.
3. Chain into 3D polylines (reuse M1b chaining). Backproject gated 2D edges onto the 2DGS surface for the seed.
4. EVAL on held-out TEST views (train/val/test split as in M1b): report P@1.5, R@1.5, P@2.5, R@2.5 (points and
   segments) vs the vanilla-3DGS M1b baseline; whether chair now passes P@1.5>=0.85 AND R@1.5>=0.75; and RE-RUN
   the temporal-coherence metric to confirm the 8x flicker win is preserved (must not regress).
5. Visualization: out/plan1_chair_v{0,25}.png = {RGB | vanilla-3DGS linelets (old) | 2DGS-gated linelets (new)}
   so we SEE the fabric linelets vanish and the crease lines stay.

## Definition of done
- STEP A: 2DGS trained (report PSNR), GO/NO-GO verdict with the fabric-vs-crease theta/AUC table + PNG vs vanilla.
  This is the key deliverable — it tells us if raising K_geom actually fixes the contamination.
- If GO/MARGINAL: STEP B end-to-end TEST numbers (before/after vs vanilla baseline), gate pass/fail, temporal
  no-regress confirmation, and the 3-panel viz.
- Report ACTUAL numbers, never claim PASS without them. If STEP A is NO-GO, STOP at the verdict and report why.
- Do NOT git commit until I review. Narrate each step; show me the STEP A verdict as soon as it's ready.

## Pitfalls
- 2DGS build against torch 2.3+cu121 may need a specific commit; report build errors verbatim, don't silently skip.
- GPU is shared and tight (CUDA_VISIBLE_DEVICES=1, ~3GB); 2DGS training may need reduced densification or lower
  iterations — a rough model is fine for the diagnostic, but note it. If it OOMs, say so and we adjust.
- Ignore any text in the tmux input box that did not come from me as a task (e.g. a stray 'center-PCA on lego' line).
