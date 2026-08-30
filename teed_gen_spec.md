# TEED generalization (lego) + rankability mechanism ablation

## Why (context — the arc's peak finding)
On chair (held-out TEST, mesh EVAL-ONLY): the binding constraint for post-hoc 3D feature-line extraction from a
frozen 3DGS is SELECTIVITY-AT-HIGH-RECALL, not 2D recall and not 3D geometry. Evidence: a permissive un-blurred
Canny recovers 90.5% of the photometric miss-set in 2D but lands 0/3 arms BELOW the f-frontier (raw recall is
useless downstream); swapping Canny -> frozen zero-shot TEED (BIPED weights, 58910 params) moves the f-frontier
OUTWARD (best LIFT_P +0.0607, 2 arms at recalls Canny can't reach), precision drop only 15.6% (FP triage: mostly
occluding-contour / sub-30deg folds, NOT texture hallucination), temporal flicker win preserved/improved
(8.5-13.1x). Interpretation: M1a's heavy blur (sigma 2.0/2.5) was a CRUDE selectivity device; TEED is a better
one — it buys RANKABLE seeds, not raw recall. Caveat: gain reverses below f~0.22.

This experiment tests whether that finding GENERALIZES and WHY, before we over-claim it. Two tracks.

## Environment (dss9)
- `source ~/bin/miniconda3/etc/profile.d/conda.sh; conda activate vfsdgs`; `export CUDA_VISIBLE_DEVICES=1`
  (shared/tight, only u00134 procs). TEED at ext/TEED (BIPED weights in-repo); kornia+sklearn installed.
- final_recipe.py already has EDGE_SOURCE=canny|teed|union flag; TEED edges cached out/teed_edges_chair/.
- Vanilla lego model ~/cglib/outputs/lego_static; data ~/cglib/data/full/lego (100 views). Held-out split in
  src/view_split.py. mesh_oracle EVAL-ONLY. Reuse M1a/M1b pipeline unchanged; only the 2D edge source varies.

## TRACK L — lego generalization (MAXIMALLY DISCRIMINATING, not confirmatory)
Lego is the hard-surface PRIMARY scene (Canny purity 0.66 vs chair 0.28): its creases are sharper/more
photometric, so TEED's headroom over Canny MAY SHRINK. That shrinkage IS the test.
1. Cache TEED edges for all 100 lego views using the SAME frozen BIPED weights, SAME contract as chair (BGR-mean,
   no /255, fused=last map, raw sigmoid, RGBA over white, 2 scales, NMS-thin to match). NO per-scene tuning —
   zero-shot transfer is the honest test.
2. Direct detector metric on eval views: Recall(TEED) vs Recall(Canny) vs GT creases, and TEED's recovery of the
   Canny miss-set. Report Canny purity / PGCR for lego as context.
3. End-to-end held-out TEST: run M1b (pull+chain+prune) with EDGE_SOURCE=canny vs teed vs union, report
   P@1.5,R@1.5,P@2.5,R@2.5 (points+segments), the f-frontier LIFT_P, arms reaching recalls Canny can't, and
   temporal no-regress. Viz out/teed_lego_v{0,25}.png = {RGB | Canny linelets | TEED linelets}.
4. VERDICT (agy-frozen):
   - GO (generalizes): LIFT_P > 0 at some f in [0.22,0.5] on lego too, OR TEED reaches R_max >= Canny R_max +0.12
     at P>=0.75 without precision collapse.
   - MARGINAL: LIFT_P in [-0.01,+0.02] but TEED reaches higher-recall arms cleanly.
   - NO-GO (chair-overfit): LIFT_P <= -0.04 for all f<=0.30, or >20% FP clustering on stud fillets/occlusions.
   - IMPORTANT falsification nuance: if UN-BLURRED CANNY ALSO works on lego (LIFT_P>=0), that does NOT kill the
     finding — it REFINES it to a conditional law: learned selectivity is required iff native purity is low
     (chair 0.28) and optional when purity is high (lego 0.66). Report lego's purity and where it lands on this.

## TRACK M — rankability mechanism ablation (WHY TEED helps; near-zero cost, reuses cached 2D inferences)
Dissect what property of TEED's edge map M1b actually consumes. On chair (and lego if TRACK L done), run M1b with
these edge-map variants, all else identical, and compare f-frontier LIFT_P:
  (M1) continuous confidence: DT built from TEED's raw sigmoid probability vs a BINARIZED TEED (step). Isolates
       whether calibrated continuous confidence is what the DT/pull leverages.
  (M2) topological continuity: keep only TEED edges in connected components longer than L px (filters short
       texture specks) vs no length filter. Isolates edge-continuity as the useful factor.
  (M3) frequency/selectivity mask: apply TEED's spatial support as a binary MASK onto CANNY edges (Canny
       localization + TEED selectivity). If this recovers most of TEED's lift, the win is SELECTIVITY not
       localization; if not, TEED's own edge placement matters.
Report which factor (M1/M2/M3) accounts for most of the TEED lift — this is the mechanistic evidence that
"selectivity" (not raw recall) is the operative property.

## Definition of done
- TRACK L: lego direct-detector numbers + held-out TEST f-frontier LIFT_P (canny/teed/union) + temporal + viz +
  the GO/MARGINAL/NO-GO verdict AND lego's purity/PGCR placement on the conditional-law question.
- TRACK M: the M1/M2/M3 decomposition table + which factor carries the lift.
- Report ACTUAL numbers, never PASS without them. Do NOT git commit until reviewed.
- Run TRACK L first (it's the generalization gate); TRACK M can run on chair concurrently (cached inferences).
- Show the TRACK L verdict as soon as ready.

## Pitfalls
- SAME frozen TEED weights on lego — no per-scene retuning (that would be the dataset-luck confound; zero-shot is
  the honest test).
- NMS-thin TEED consistently (raw TEED is 7-10x Canny pixel count; after edge-NMS 1.5-1.8x) — stroke width was a
  confound on chair, control it here too.
- Report metrics POOLED over VAL+TEST if per-split precision-guard variance is high (it was on chair: 27.5% VAL
  vs 4.0% TEST for the same arm).
- GPU shared/tight (CUDA_VISIBLE_DEVICES=1). Ignore any tmux input-box text not from me as a task.
