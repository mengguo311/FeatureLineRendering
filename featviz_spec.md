# FEATURE-LAYER VISUALIZATION — full set, all scenes (a from-scratch teardown of our 3DGS model)

## PURPOSE
The user wants to re-derive our whole approach from first principles by SEEING every layer of the 3DGS model: what signal exists at each layer and where the line signal is lost. Produce a COMPLETE set of per-layer feature visualizations for ALL scenes. This is a VISUALIZATION / DIAGNOSTIC task — NOT a metric run, NOT a paper task. mesh is EVAL-ONLY (GT crease overlay for reference only, never feeds the method).

## SCENES (all four)
- chair, lego, ficus  (textured NeRF-synthetic; PLY at ~/cglib/outputs/<scene>_static/point_cloud.ply)
- cadpartA (clean textureless solid, chamfered hex-nut; locate its trained 3DGS PLY — check ~/3dgs_line/tier1 out/ and bcr/ ; if only mesh+phase1b cloud exist, use whatever trained gaussians Exp Y / CADPART_M1B produced)
2DGS surfel models exist for cadpartA/chair/lego (out/2dgs_*), NOT ficus.
Meshes for all in ~/3dgs_line/bcr/meshes/NeRF_Mesh/<scene>_new.obj (EVAL-ONLY overlay).

## PICK ONE FIXED HELD-OUT CAMERA per scene (a clear 3/4 view) and render EVERY layer from that SAME camera so the layers overlay pixel-aligned. Also emit for chair/lego one second view for the temporal/normal panels if cheap. Save all to out/featviz/<scene>_<layer>.png at >=800px. Use src/render.py render_gbuffer (alpha/depth/normal) and src/render2dgs.py; matplotlib for point-lattice/histograms.

## LAYER SET TO PRODUCE per scene (number them L1..L18; skip only if asset truly absent, and SAY which skipped):
### Input/output
- L1 rendered RGB (held-out view)
- L2 GT source image same-ish view (if available) for fidelity contrast
### Gaussian primitive layer
- L3 Gaussian-center point lattice (project all gaussian means to the image, scatter; color by depth). Show density.
- L4 Anisotropic ellipse plot (draw each gaussian's projected 2D covariance as an ellipse, subsample if >50k; color by anisotropy ratio max_scale/min_scale). Highlight needle-like (ratio>10) in hot color — these are our crease seeds.
- L5 Opacity alpha heatmap over gaussians (scatter colored by opacity); mark floaters (low alpha, off-surface).
- L6 Gaussian scale distribution: (a) histogram of max-axis length, (b) spatial heatmap of local median gaussian size. THIS visualizes the "textureless->big gaussians" effect — annotate median size per scene so cadpart(big) vs lego(small) is visible.
### Render buffers (z-buffer family)
- L7 Depth / z-buffer (depth_median), turbo colormap
- L8 Rendered normal map (normal buffer, RGB-encoded)
- L9 Alpha / accumulation buffer (silhouette/occupancy)
- L10 Depth-discontinuity map (gradient magnitude of depth -> silhouettes)
- L11 Normal-discontinuity map (angle between neighboring normals -> creases should light up here)
### Feature / signal layer
- L12 Multi-view edge detector on the RGB render (Canny AND TEED if available) overlaid
- L13 GT-mesh crease edges projected to this view (EVAL-ONLY reference, thin red)
- L14 Our candidate SEEDS scatter vs GT crease overlay (show seed precision visually: how many seeds land on a real crease)
- L15 Buffer-vs-GT alignment: overlay L11 normal-discontinuity (or the geometric cue) with L13 GT creases — does the geometric signal sit on true creases?
### Diagnostic comparison (highest teardown value)
- L16 vanilla-3DGS normal (L8) vs 2DGS-surfel normal SIDE BY SIDE for the scenes with 2DGS (cadpart/chair/lego). Annotate median crease dihedral each reads (we measured vanilla ~10deg vs 2DGS ~40deg vs GT 40-90) — this is THE reason geometric discriminators live on clean solids and die on texture.
- L17 Our extracted line drawing (current best per scene) with GT crease faint underneath — coverage at a glance.
- L18 (montage) a single contact-sheet PNG per scene tiling L1,L3,L4,L7,L8,L11,L14,L16 so the user sees the whole stack at once.

## RENDERING NOTES
- conda vfsdgs, CUDA_VISIBLE_DEVICES=1, only u00134 procs, direct run NO heavy multi-agent workflow.
- Reuse existing render_gbuffer / render2dgs code paths; write ONE script scripts/featviz_all.py that loops scenes x layers, robust to a missing asset (print SKIP <scene> <layer> <reason>). Persist a manifest out/featviz/FEATVIZ_MANIFEST.md listing every file made + every skip + the per-scene annotations (median gaussian size, vanilla vs 2DGS dihedral, seed precision, n gaussians).
- Do NOT retune anything, do NOT run metrics beyond what a panel needs, do NOT git commit until I say. Keep it to visualization.
- When done, report in the tmux the manifest path + counts (how many PNGs, which skips) so I can pull them.

## PRIORITY ORDER (in case of time/GPU limits): do cadpart + lego FIRST fully (cleanest contrast), then chair, then ficus (ficus has no 2DGS so L16 skipped). Emit the L18 montage last per scene.
Begin now, direct run.