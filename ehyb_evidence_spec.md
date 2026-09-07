# E-HYB + EVIDENCE-FRONTIER PUSH — release the full potential of evidence-quality seeding

## LOCKED GOAL (re-read)
Extract CLEAN, TEMPORALLY-STABLE 3D feature lines from a FROZEN vanilla 3DGS, NPR line rendering. BANKED crown
jewel: object-space lines 3.4-11.5x more temporally coherent than per-frame image-space Canny (held-out; lego
P_pop 0.063 vs 0.719 = 11.49x). mesh EVAL-ONLY, never in method path. Protect the temporal win.

## THE BREAKTHROUGH THIS BRANCH CHASES (from the hybrid discussion)
The recall-vs-stability frontier is NOT a strict trade. Adding carriers at FIXED evidence quality trades temporal
for recall (f=1.00: ratio 11.5x->2.8x, dead). But IMPROVING THE EVIDENCE QUALITY that ranks/places carriers moves
the frontier OUTWARD at ZERO temporal cost. Banked proof on lego (gate-matched, mask-matched, same pull/prune, 240
-frame TEST orbit):
    seed score      f     P@1.5   R@1.5   P_pop ratio   Frechet ratio
    canny (shipped) 0.30   0.583   0.417    12.10x        13.98x
    canny           0.40   0.583   0.482    11.61x (cost) 13.95x
    TEED            0.40   0.620   0.627    12.10x (FREE)  14.81x   <-- STRICTLY DOMINATES shipped on ALL axes
TEED puts MORE strokes on screen than canny-f0.40 (1,640 vs 1,424) yet pays ZERO temporal penalty, because
better-placed carriers chain into longer coherent curves so the split/merge `cut` term does not inflate. The seed
SCORE does the work, not the seed COUNT. "Evidence, not ink" — image-space detectors imported as a RANKING signal
over object-space carriers cost zero flicker by construction.

## THE MANDATE (user, verbatim intent): be bold, aggressive, iterate, release the FULL potential of this direction
Do NOT write paper. PUSH the evidence-quality frontier as far as it goes. The question is: how far outward can a
better evidence channel move the recall-vs-stability frontier before it hits the real signal ceiling? Try
aggressively, falsify cheaply, iterate.

## CLOSED BRANCHES — do NOT re-open (wasted effort, already measured)
- Per-frame image-space INK fused into the frame: dead by arithmetic (r<=1.06%, 12 strokes of 615).
- DexiNed-primary (lift DexiNed to 3D): precision 0.16-0.18, mesh-free discriminator died (Phase1d/1e 0.44-0.66 vs 0.72).
- Detector UNION / multi-cue additive fusion: union < best single; NG-MEC-v2 == TEED alone; ECO ~0 on lego.
- FeatureGS planarity/entropy preproc: anti-correlated (erases needle carriers), capped +0.036 F1.
- EdgeGaussians filament retrain: any-view integrator, cardinality-bound, no crease-vs-texture.
- 3Doodle compact strokes: 16-48 strokes can't cover 1,897 components; CLIP 3.57x too coarse; = baseline/citation.
- f=1.00 (more carriers, fixed evidence): fragmentation NO-GO.
- Aggressive 3D linking: +21%/+14% < +25% bar; fragmentation follows coverage not weak linking.
- Geometric crease-vs-texture discriminators: dead ~0.5 (precision-side, but the recall-side E1 was never run).
- HARD CEILING that no image-space evidence escapes: 48.96% of lego miss-set is the exactly-30.000-deg 12-gon
  stud tessellation, rendered as smooth cylinders (photo p50 28.3, recall 0.1035) — invisible to ANY detector.
  Plus the cardinality bound (DexiNed 11,697 < 12,937 edge px/view on lego). Evidence-quality wins are won on the
  OTHER half; the exactly-90-deg corner family (24.85%, recall 0.229) is the largest recoverable block.

## PHASE A — E-HYB (confirm the TEED domination reproduces under the VERIFY_F100 harness). ~45 min.
Lego, gate=True, edge=sharp, spec mask + tuned+len stage, 80 TRAIN views, held-out TEST, 240-frame TEST orbit
5->15, identical warp + Canny baseline, fresh --tag/--viz_tag. Reuse the exact temporal path (scripts/
m1b_stroke_temporal.py). Arms: TEED f=0.30, 0.35, 0.40 (0.40 is the reproduction control). Static P/R already
banked — compute the TEMPORAL cell for each. Also compute the CHAIR temporal cell for the best TEED f (Track C
banks chair static dRecall +0.270 / LIFT_P +0.0607 but no temporal cell under this harness).
  GO: some TEED f gives lego tuned+len R@1.5 >= 0.40 AND P@1.5 >= 0.5996 AND P_pop ratio >= 10.345x. Prior 0.90 GO.
  Carry the 30.05-deg caveat (lego P falls 0.636->0.310 at theta>=30.05; applies to all arms equally).
  Verify manifest 332/332 untouched. Do NOT modify shipped jsons.

## PHASE B — PUSH EVIDENCE QUALITY AS FAR AS IT GOES (the aggressive part). Argue design each step with me first.
The frontier-moving variable is EVIDENCE QUALITY of the per-carrier seed score. TEED beat Canny for free. So push:
candidate directions to argue + falsify (pick the highest-EV each iteration, cheapest-falsification-first):
  1. STRONGER learned detectors as the ranking signal: PiDiNet, DexiNed, or an ENSEMBLE/agreement score across
     {TEED, PiDiNet, DexiNed} used as the carrier RANK (not union-ink). Does a cross-detector AGREEMENT rank beat
     single TEED? (CMEPI cross-model invariance was banked earlier — build on it.)
  2. MULTI-VIEW evidence integration done RIGHT for ranking (not the pointwise pooling that NO-GO'd): rank a
     carrier by the multi-view-consistent TEED response along its own tangent (tangential matched filter), using
     the frozen 3DGS depth for occlusion — evidence, not ink, so temporally free.
  3. Push the operating point: with a better evidence score, how high can f go before temporal breaks? Map the
     NEW frontier curve (evidence-quality curve) vs the old f-curve; find the knee.
  4. The 90-deg corner family (24.85%, the largest recoverable block): a targeted evidence channel for corners
     (junction/corner detector as rank) — can we specifically recover the recoverable half?
  5. Chair (texture-stress, the scene where evidence quality matters most): replicate the lego win, map its frontier.
Each iteration: argue the design with me (Fable/Opus, no-code synthesis), pick ONE, pre-register a go/no-go
(recall gain at fixed-or-better P@1.5 AND P_pop ratio >= 10.3x), run it, analyze honestly, git commit+push to
evidence-frontier, then argue the next. Be bold — try the aggressive version, falsify cheaply. Negative results
are fine and get reported straight. The temporal ratio >= 10.3x bar is the ONE hard invariant besides mesh-EVAL-ONLY.

## ENVIRONMENT
conda vfsdgs, CUDA_VISIBLE_DEVICES=1, only u00134 procs, GPU tight (~3.5GB). Branch evidence-frontier. Reuse
tier1/src + scripts (grep first). Do NOT launch heavy multi-agent dynamic workflows for routine runs — direct.
Report ACTUAL numbers. mesh EVAL-ONLY. Ignore stale input-box text not from the orchestrator.

## THIS DISPATCH: run PHASE A (E-HYB) now. Report the table + GO/NO-GO. Then STOP and wait — I will argue Phase B
step 1 with you before dispatching it.
