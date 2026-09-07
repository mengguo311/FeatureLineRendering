# DISCUSSION — hybrid image-space (DexiNed) + object-space (ours) line synthesis. Viable? (NO CODE)

Adversarial feasibility analysis. You hold the full project state in context (round-1 FeatureGS/EdgeGaussians,
VERIFY_F100 NO-GO, the 3Doodle analysis). NO code, NO file edits except writing the final analysis to
/tmp/m1b_hybrid.txt via one cat heredoc at the end, then print it. I will push back hard.

## THE USER'S IDEA (verbatim intent)
"Produce BOTH image-space and object-space lines at the same time, then COMBINE them. Use OUR method (object-
space, temporally stable) PLUS the DexiNed method (image-space, high coverage) to synthesise usable line
segments." I.e. each frame draws two line sources — our stable object-space chains AND per-frame DexiNed image-
space edges — and we fuse them into one final line drawing that is both high-coverage AND temporally stable.

## THE CENTRAL TENSION YOU MUST RESOLVE (do not dodge it)
Our ENTIRE banked contribution is that object-space lines are 3.4-11.5x more temporally coherent than per-frame
image-space Canny/DexiNed (held-out; P_pop 0.063 vs 0.719 lego = 11.49x). Per-frame DexiNed edges are exactly the
flickering baseline we beat. Naively ADDING per-frame DexiNed strokes into the final drawing re-injects the
flicker we sell against — it would drag the fused P_pop toward the image-space baseline in proportion to how much
DexiNed ink we add. So "combine" only survives if the DexiNed contribution is made temporally stable BEFORE or DURING
fusion, or is used as evidence rather than as drawn ink. Quantify how much flicker a given fusion ratio reintroduces.

## WHAT WE ALREADY TRIED THAT IS ADJACENT (judge novelty against these — be specific)
- DexiNed-PRIMARY (Phase 0/1b/1c): seed from DexiNed edges, multi-view TRIANGULATE to 3D (so the DexiNed signal is
  lifted to a STABLE object-space curve, not drawn per-frame). Phase 1b recovered 69% of the gaussian miss-set
  (chair 0.49->0.68) but the triangulated cloud precision was 0.16-0.18; the crease-vs-texture discriminator to
  clean it (DINOv2) was killable mesh-free (Phase 1d/1e, best mesh-free gate 0.4458 vs 0.72 bar). Epipolar
  accumulation of raw DexiNed over the miss-set was NO-GO (lego AUC 0.698, R@85P 0.000; 5px response tail).
- ECO (epipolar consensus) and the "adaptive acceptance field" idea (relax the 3DGS carrier requirement where the
  multi-view edge evidence is strong): ECO gave chair +0.0146, bounded; the additive-not-subtractive-flower
  principle (orthogonal info must ADD recall, not veto precision) came out of the soft-DT-weight falsification.
- The f=1.00 sweep: buying recall by adding more object-space strokes wrecked temporal via the split/merge (cut)
  term (P_pop ratio 11.5x -> 2.8x). Adding MORE ink of any kind that fragments is temporally expensive.

## KEY MEASURED DECOMPOSITION (use it)
P_pop = unmatched + cut. Shipped lego: 0.0370 unmatched (mostly correct hidden-line removal) + 0.0256 cut.
Per-frame DexiNed/Canny image-space P_pop ~0.719. So an image-space stroke that is NOT lifted to a persistent 3D
locus carries ~0.7 pop by itself.

## QUESTIONS (verdict each, use our numbers, disagree where warranted)
Q1. Is the user's idea DISTINCT from DexiNed-primary, or is it the same thing? Precisely: DexiNed-primary already
   fuses DexiNed with our method, but by LIFTING DexiNed to object-space (triangulation) FIRST, so the fused
   output stays stable. The user's phrasing suggests drawing BOTH image-space (per-frame) AND object-space
   (persistent) lines and combining at the image/stroke level. If it means per-frame DexiNed ink in the final
   frame, it re-injects flicker (quantify: at fusion ratio r of image-space ink, fused P_pop ~ (1-r)*0.063 +
   r*0.719 to first order — state the exact bar r must stay under to keep >= 10.3x). If it means something else,
   state the ONE interpretation that is both novel and temporally safe.
Q2. Is there a temporally-safe fusion that genuinely ADDS coverage? Candidates: (a) use per-frame DexiNed ONLY as
   a CONFIDENCE MASK / evidence channel that re-weights or gates our object-space chains (evidence, not ink — no
   flicker), (b) lift DexiNed to a PERSISTENT per-frame-consistent 3D structure first (= DexiNed-primary, already
   measured), (c) draw DexiNed ink only where it is MULTI-VIEW-CONSISTENT (temporally stable subset) — but our
   Phase-1b data says off-crease DexiNed edges are 87% multi-view consistent (texture edges ARE stable 3D
   structure), so "consistent" does not mean "crease". Which of (a)/(b)/(c) is not already closed, and what is its
   ceiling given the miss-set signal problem (49% of lego miss-set is smooth 30-deg studs invisible to DexiNed too)?
Q3. The honest decomposition of "usable line segments": our shipped lines are LOW-RECALL (lego R@1.5 0.286) but
   HIGH-STABILITY; DexiNed per-frame is HIGH-RECALL (its 2D recall is the ceiling everything else inherits) but
   ZERO-stability-in-3D and NO crease-vs-texture selectivity. Fusing them, what does the union actually buy on OUR
   metrics (P@1.5, R@1.5, P_pop ratio) that we have not already measured via f=1.00 (more strokes) or DexiNed-
   primary (lifted DexiNed)? Is there any fusion point on the recall-vs-stability frontier that DOMINATES the
   shipped point on BOTH axes, or does everything we have measured say the frontier is a strict trade?
Q4. Decisive: ONE cheap experiment with a pre-registered go/no-go, OR state plainly this reduces to an
   already-closed branch (DexiNed-primary / f-sweep) and why. If there IS a novel temporally-safe fusion (most
   likely the (a) evidence-gate reading), define it precisely and give the metric + frozen bar: it must raise
   R@1.5 on lego by a stated amount WITHOUT dropping P@1.5 > 0.02 AND keeping P_pop ratio >= 10.3x (90% of shipped).
   State your prior.

Write the full analysis to /tmp/m1b_hybrid.txt. Do NOT launch a heavy multi-agent workflow — direct rigorous
analysis from context plus targeted reads. Cite our banked numbers. Disagree with me AND with the user's framing
where the evidence warrants — the goal is the best idea, not agreement.
