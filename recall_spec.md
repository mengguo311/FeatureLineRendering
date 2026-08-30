# Recall-bottleneck experiments — 2DGS-ridge redundancy gate + TEED learned-edge upgrade

## Why (context — the whole arc converged here)
Post-hoc feature-line extraction from a FROZEN reconstruction is RECALL-CAPPED at ~0.50-0.55, not precision-
limited. Established (held-out TEST, mesh EVAL-ONLY):
- Vanilla 3DGS seeds concentrate at creases (best recall) but geometry is texture-baked (K_geom~0).
- 2DGS geometry is clean at the discriminative level BUT regularizes SUBTLE creases into smooth surfels: 57.3%
  of seeds it vetoes are TRUE creases. Using 2DGS as a precision veto or soft-weight is DOMINATED by the M1a
  f-dial (14/15 arms below the f-frontier; matched-seed-count, lowering f to 0.18 beats the hybrid with NO 2DGS).
- KEY FINDING: seed COVERAGE, not seed precision, is the binding quantity for the M1b deliverable. Orthogonal
  info must be spent ADDITIVELY (recall injection), not subtractively (veto).
- HYPOTHESIS to test: the recall gap (~50% of GT creases MISSED by photometric Canny seeds) lives in the 2D
  IMAGE (faint photometric signature of subtle creases), NOT in any 3D reconstruction's geometry. So the recall
  lever is a stronger 2D EDGE DETECTOR (Canny -> TEED learned edges), not a 3D geometric seeder.

## Environment (dss9)
- `source ~/bin/miniconda3/etc/profile.d/conda.sh; conda activate vfsdgs`; `export CUDA_VISIBLE_DEVICES=1`
  (shared/tight, only u00134 procs). torch 2.3.1+cu121, cuda OK. No kornia, no TEED yet; internet works.
- Work in ~/3dgs_line/tier1/. Reuse: M1a OVERALL seed recipe (scripts/explore/syn/final_recipe.py — it currently
  builds the multi-view edge DT from CANNY: cfgs ((2.0,100,200),(2.5,75,150))); the M1b pull/chain/eval pipeline;
  gate_falsify.py labels; mesh_oracle EVAL-ONLY; the trained 2DGS chair model out/2dgs_chair/ (NOT _dist — that
  one over-flattens); the held-out train/val/test view split.
- HARD INVARIANT: mesh EVAL-ONLY. Method never imports mesh_oracle.

## TRACK A (parallel, cheap ~1hr) — 2DGS-ridge redundancy GATE (bury or justify the 2DGS seeder)
Pure 2D pixel-mask intersection on the eval views, NO 3D seeder code.
1. On eval views, partition GT crease pixels (from mesh_oracle, EVAL-ONLY):
   S_photo_hit = GT ∩ dilate(Canny_edge, tau); S_photo_miss = GT \ S_photo_hit (expect ~50% of GT).
2. Build the 2DGS-ridge mask: render 2DGS normal map N (out/2dgs_chair), M_ridge = threshold(||grad N||_F).
3. Recall_miss(2DGS) = |S_photo_miss ∩ dilate(M_ridge, tau)| / |S_photo_miss|.
   Also report, as a control, Recall_miss of a SECOND Canny at a lower threshold (does cheap photometric tuning
   already recover the miss-set?), and the 2DGS-ridge recovery on the photo-HIT set (sanity: should be high).
4. GATE: if Recall_miss(2DGS) < 25% -> PERMANENTLY KILL 2DGS-ridge additive seeding (write the verdict, no 3D
   seeder code). If >= 25% -> report which creases it uniquely recovers (a real complementarity signal).
   Report the number + a viz (photo-miss pixels overlaid with 2DGS-ridge hits).

## TRACK B (parallel with A) — install + prepare TEED learned edge detector
1. Get TEED (github.com/xavysp/TEED) — clone into ~/3dgs_line/ext/TEED, download its pretrained checkpoint. If
   the exact repo/weights are unavailable, DexiNed or PiDiNet are acceptable equivalents — report which you used.
   Install any deps (kornia only if needed) into vfsdgs. Verify it runs a forward pass on one chair train image
   and produces a sane edge map (save out/teed_sample_chair_v0.png next to the Canny map for visual compare).
2. Batch-run the chosen detector over ALL 100 chair training views, cache the edge maps to out/teed_edges_chair/
   (float or uint8). Report runtime + a couple of side-by-side TEED-vs-Canny PNGs.

## TRACK C (after B, informed by A) — TEED recall upgrade, end-to-end
1. Swap the M1a photometric edge source from Canny to the TEED edge maps INSIDE final_recipe.py (make it a flag:
   --edge canny|teed). Rebuild the multi-view edge DT from TEED. Re-extract seeds. Keep EVERYTHING else identical.
2. FIRST measure the direct recall lever (cheap, before the full pipeline): on eval views,
   Recall_photo(TEED) vs Recall_photo(Canny) against GT creases, and the fraction of S_photo_miss (Canny's miss-
   set) that TEED now recovers. This is the go/no-go on the DETECTOR itself.
   GO: Recall(TEED) - Recall(Canny) >= +0.18 AND recovers >= 35% of the Canny miss-set AND seed count < 2.5x
       Canny. NO-GO: dRecall < +0.10 OR GT-edge precision drops > 25% (texture hallucination dominates).
3. If GO: run the FULL M1b pipeline (pull+chain+prune) on TEED seeds, held-out TEST: report P@1.5,R@1.5,P@2.5,
   R@2.5 (points+segments) vs the Canny baseline (seg P@1.5=0.657/R=0.596), whether it moves the f-frontier
   OUTWARD (higher recall at matched precision), whether chair passes P@1.5>=0.85 ∧ R@1.5>=0.75, and RE-RUN the
   temporal metric (must preserve the 7-11x flicker win). Viz out/teed_chair_v{0,25}.png = {RGB | Canny linelets
   | TEED linelets} so we SEE recovered subtle creases.
4. If NO-GO: report the miss-set analysis (are the missed creases below EVERY 2D detector's SNR? -> the recall
   ceiling is fundamental, re-scope) and stop for my review before building multi-view triangulation.

## Definition of done
- TRACK A verdict: Recall_miss(2DGS) number + KILL-or-keep 2DGS-ridge seeding.
- TRACK C go/no-go: Recall(TEED)-Recall(Canny) on eval views + Canny-miss-set recovery, then (if GO) full held-out
  TEST P/R vs Canny baseline + f-frontier shift + temporal no-regress + viz.
- Report ACTUAL numbers, never PASS without them. Do NOT git commit until I review.
- You may run TRACK A and TRACK B concurrently (background shells) since they're independent; TRACK C waits on B.
- Show me the TRACK A verdict and the TRACK C detector go/no-go as soon as each is ready. Narrate.

## Pitfalls
- TEED/DexiNed expect specific input normalization (ImageNet mean/std or [0,1]); use the repo's transform. The
  chair RGBA has alpha — composite over the training background (black or white as the dataset uses) before edges.
- Keep the SAME multi-view DT machinery; only the per-view 2D edge map source changes (Canny -> TEED).
- GPU shared/tight; TEED inference is light but do it on CUDA_VISIBLE_DEVICES=1 and don't OOM the 2DGS/vanilla caches.
- Ignore any text in the tmux input box that did not come from me as a task (e.g. a stray 'soft DT-weight' line).
