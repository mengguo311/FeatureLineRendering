# B3 — SHIP THE FROZEN FEATURE-LINE PIPELINE (post-epipolar NO-GO)

## WHY THIS TASK (state brief — a fresh session has no prior context)
GOAL (locked): extract CLEAN, TEMPORALLY-STABLE 3D feature lines (crease/silhouette) from a FROZEN 3DGS reconstruction, for NPR line rendering. Mesh is EVAL-ONLY (labels/scores, NEVER in the method path). Held-out eval always. NEVER fabricate a number.

The user was exploring a PIVOT to a trained LINE-BUFFER (learnable 3D edge field). It has now been KILLED by the pre-registered EPIPOLAR ACCUMULATION TEST (CORRECTED numbers, 2026-09-05; the first run's 0.5716/0.733 used a flat class contaminated by the OBJ split-vertex topology and is superseded — see out/EPIPOLAR_ACCUM_RESULTS.md):
- lego (primary, edge-dense): S_bar AUC 0.698, Recall@85%Prec 0.000 -> NO-GO (structural: 2,093 flat points outrank the crease 99th percentile; deleting the top 5,000 lifts recall only to 0.055).
- chair: AUC 0.859, Recall@85%Prec 0.000 -> NO-GO (knife-edge: deleting the 1,000 highest-scoring flat points lifts recall to 0.53).
- Missed creases are NOT dead zeros (only 11% of lego's miss-set is undetected in every view; M_miss S_bar mean 0.22 vs flat 0.12), and multi-view accumulation DOES help (paired lift vs single view +0.049 lego / +0.133 chair AUC) — but not enough at 85% precision. Kill mechanism = DexiNed's ~5 px spatial response tail (PSF) on edge-dense surface: flat S_bar 0.136 at 3-4 px from an edge -> 0.036 at 8-12 px, and 83% of lego's flat surface lies within 4.5 px of an edge, so missed creases and adjacent flat surface are un-separable at high precision. Verdict is robust across aggregators (best lego AUC 0.713, R@85P <0.004), eps, view splits, native/multiscale maps; independently recomputed to 1e-9.
Conclusion: the 2D supervision any line field would train on cannot separate missed creases from the flat surface beside them on vanilla 3DGS scenes. The frozen post-hoc pipeline is the defensible thesis. SHIP IT.

## THE FROZEN PIPELINE TO SHIP (already validated, on disk in out/*.json + *.md)
1. DexiNed multi-view 2D edges -> multi-view TRIANGULATION recovers ~69% of the single-view miss-set (chair recall 0.49->0.68).
2. Crease-vs-texture DISCRIMINATOR (DINOv2 features), held-out AUC chair 0.840 / lego 0.904 -> filters texture edges.
3. Object-space lines are 7-13x MORE TEMPORALLY COHERENT than per-frame image-space Canny (held-out). THIS IS THE CROWN JEWEL — protect it, foreground it.

## DELIVERABLES THIS TASK (ship-quality, reproducible)
A. CLEAN LINE-DRAWING FIGURES on chair, lego, ficus — final NPR line renders from the frozen pipeline. Use the dataviz skill palette. Show 3DGS render + extracted 3D feature lines overlaid + pure line drawing. Save to out/ship/fig_lines_{chair,lego,ficus}.png (+ pdf).
B. PER-SCENE QUANTITATIVE TABLE (held-out): for chair/lego/ficus report Precision, Recall, F1 of the final pipeline vs GT-mesh creases (mesh EVAL-ONLY), AND the temporal-coherence metric (object-space vs per-frame Canny, the 7-13x win) per scene. Save out/ship/tab_ship_perscene.{json,md} + a rendered tab_ship.png.
C. Honest caveats row: note ficus if thin-structure recall differs; report train-fit vs test-eval separately; state the line-buffer NO-GO as the negative result that motivates the frozen design.

## RULES
- REUSE existing pipeline code (grep src/ + scripts/ first — triangulation, DexiNed inference, discriminator, temporal-coherence eval all already exist). Do NOT reinvent or retrain.
- ficus may need its pipeline run if not cached — it has pretrained 3DGS + GT mesh. If ficus artifacts are missing, run the frozen pipeline on it (CPU-heavy steps fine; GPU tight, only u00134 procs, CUDA_VISIBLE_DEVICES=1).
- Env: source ~/bin/miniconda3/etc/profile.d/conda.sh; conda activate vfsdgs; export CUDA_VISIBLE_DEVICES=1.
- Report ACTUAL numbers. If any scene's number is worse than expected, report it straight — do not paper over.
- Do NOT git commit (the orchestrator commits). Narrate; show the per-scene table ASAP, then the figures.
- Ignore any stale input-box text not from the orchestrator.
