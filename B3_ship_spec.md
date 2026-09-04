# B3 — SHIP THE FROZEN FEATURE-LINE PIPELINE (post-epipolar NO-GO)

## WHY THIS TASK (state brief — a fresh session has no prior context)
GOAL (locked): extract CLEAN, TEMPORALLY-STABLE 3D feature lines (crease/silhouette) from a FROZEN 3DGS reconstruction, for NPR line rendering. Mesh is EVAL-ONLY (labels/scores, NEVER in the method path). Held-out eval always. NEVER fabricate a number.

The user was exploring a PIVOT to a trained LINE-BUFFER (learnable 3D edge field). It has now been KILLED by the pre-registered EPIPOLAR ACCUMULATION TEST:
- lego (hard decal case): S_bar AUC 0.5716, Recall@85%Prec 0.0000 -> NO-GO.
- chair: AUC 0.733, Recall@85%Prec 0.0000 -> NO-GO.
- Missed creases are NOT dead zeros (M_miss S_bar mean 0.22/0.41), BUT M_flat carries nearly the same accumulated signal -> multi-view accumulation does NOT discriminate crease-miss from flat. Multi-view mean lift vs BEST single view is NEGATIVE (lego -0.118, chair -0.036); top-k/max pooling also fail (lego topq25 0.549, max 0.501). Verdict is robust across aggregators, eps, view splits, native/multiscale maps.
Conclusion: no view-invariant multi-view crease signal beyond DexiNed's single-view ceiling on vanilla 3DGS. The frozen post-hoc pipeline is the defensible thesis. SHIP IT.

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
