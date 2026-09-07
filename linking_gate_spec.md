# AGGRESSIVE 3D LINKING — precision-safe continuity gate (kill-test, NOT a build)

## READ FIRST — full project state (you may be a fresh session; trust this + on-disk files)
U-Tokyo M1 project. GOAL (locked): extract CLEAN, TEMPORALLY-STABLE 3D feature lines (crease/silhouette) from a
FROZEN 3DGS, for NPR line rendering. BANKED, held-out, method-core result: object-space lines are 3.4-11.5x more
temporally coherent than per-frame image-space Canny (popped-strokes 11.3/11.5/7.6x, Frechet 29.9/14.0/11.4x on
chair/lego/ficus). Paper is SHIPPED (temporal win + honest coverage-ceiling characterization). Per-scene seg
P/R@1.5: chair 0.657/0.596, lego 0.620/0.286, ficus 0.222/0.170. The shipped line drawings are RECOGNIZABLE but
ROUGH: fragmented linelets, choppy, some flat-region false positives — not clean continuous curves.
The coverage ceiling is REAL and was hit by three refuted attempts (geometry retrain, line-buffer epipolar test
NO-GO, geometric discriminators AUC~0.5). This task does NOT try to add coverage.

## THE TASK — user's "try A": pure POST-PROCESSING to clean the rough drawings
Connect the fragmented persistent 3D linelets into continuous polylines / close small gaps, to make the drawing
cleaner — WITHOUT adding coverage (no hallucinating missing structure) and WITHOUT breaking the temporal win.
This is a CHEAP KILL-TEST measuring whether aggressive linking improves continuity WITHOUT dropping precision and
WITHOUT hurting temporal coherence. Report the numbers against a frozen gate. Do NOT build a big framework;
agy's directive: cap at a conservative pass; if it can't clean the primary contours without artifacts, KILL it
and keep the shipped fragmented result honestly.

## NON-NEGOTIABLE CONSTRAINTS (the two ways this silently fails)
1. TEMPORAL: linking MUST be done ONCE in 3D OBJECT-SPACE on the PERSISTENT linelets (shared across all frames),
   with a VIEW-INDEPENDENT criterion, topology FROZEN once. NEVER per-frame in 2D image space (that re-introduces
   flicker and destroys the paper's only headline). Watch the "big-stroke popping paradox": merging N small
   linelets into 1 long polyline can turn 5 tiny 2px pops into 1 massive 50px pop — flicker severity scales with
   stroke LENGTH. THEREFORE the temporal metric MUST be ARC-LENGTH-WEIGHTED popped ratio, not stroke count.
2. PRECISION: aggressive linking bridges TRUE gaps (real discontinuities) and connects FALSE-POSITIVE linelets
   (lego flat-region noise) into long spurious curves; and it ROUNDS sharp corners (chair legs, lego studs) and
   SHORTCUTS across depth discontinuities (chair arm -> chair back "spiderwebbing"). A connected 20px spurious
   contour is perceptually far worse than 5 disconnected 2px speckles. So continuity gain must be bought with
   NO meaningful P/R drop.

## ENVIRONMENT (dss9) & INPUTS
- `source ~/bin/miniconda3/etc/profile.d/conda.sh; conda activate vfsdgs; export CUDA_VISIBLE_DEVICES=1`. Shared,
  ONLY u00134 procs. Mostly CPU. Work in ~/3dgs_line/tier1/. GIT BRANCH = aggressive-linking (already created).
- Inputs: shipped PERSISTENT 3D linelets. Chair: out/linelets_chair_ngmecv2_final_test.npz (or the exact shipped
  chair linelet file — grep the ship spec / master table to confirm which npz backs the shipped chair P/R
  0.657/0.596). Lego: out/linelets_lego_ngmecv2_final_test.npz (confirm against shipped lego 0.620/0.286).
  Each linelet has 3D points + per-linelet tangent. Multi-view DexiNed edge maps + 3DGS depth via the existing
  pipeline (reuse tier1/src + scripts — grep first, don't reinvent). GT mesh EVAL-ONLY for P/R scoring.
- The pipeline ALREADY does DT-pull + basic chaining. This test is MORE AGGRESSIVE linking ON TOP of that.

## ALGORITHM (agy-selected: graph endpoint-linking with tangent gating + bridge evidence + hard caps)
Greedy endpoint-to-endpoint 3D graph connector:
1. Candidate pair: endpoint p_i of stroke S_a, endpoint p_j of stroke S_b, candidate iff ||p_i - p_j|| < d_max.
2. Geometric gating (prevents corner rounding + spiderwebbing):
   - tangent alignment cos(t_i, t_j) > tau_angle;
   - bridge colinearity |t_i . (p_j-p_i)/||p_j-p_i|| | > tau_colinear;
   - depth-discontinuity guard: reject the bridge if the straight 3D segment crosses a 3DGS depth discontinuity
     (i.e. the bridge passes through free space / jumps surfaces) — use 3DGS depth along the segment.
3. Bridge EVIDENCE check (prevents connecting-through-noise/void): sample K points along segment p_i->p_j,
   project into VISIBLE training views (3DGS-depth occlusion test), require mean multi-view DexiNed response
   along the bridge > tau_edge. This is the key guard that separates "real gap in a true line" from "void".
4. Freeze topology once (view-independent), then render/score.

## SWEEP (small, decisive)
- Max gap d_max in {1.0, 2.0, 3.0} x median linelet segment length (report the median).
- Bridge verification: ON vs OFF (proves the DexiNed multi-view bridge check is what protects precision).
Run on BOTH chair (tests corner-rounding) AND lego (tests flat-noise bridging) — their failure modes are opposite.

## METRICS (compute for baseline shipped linelets AND each linked variant)
- Continuity C = total polyline arc length / #connected components (mean 3D stroke length). Higher = better.
- Precision P@1.5 and Recall R@1.5 (segment-level, GT EVAL-ONLY). Linking should NOT change R much; watch P.
- Temporal Phi_pop = (sum over popped strokes of length) / (sum over all strokes of length) — ARC-LENGTH-WEIGHTED
  popped ratio over the held-out camera trajectory (same warp operator as the banked temporal eval). Report the
  banked Phi_pop baseline and the linked Phi_pop.

## FROZEN GO / NO-GO (agy's tightened thresholds — pre-registered)
- GO (there exists an operating point WITH bridge-verification ON where ALL hold):
  * continuity C increases by >= +25% on chair AND lego;
  * P@1.5 drops by <= 0.010 on chair, <= 0.015 on lego (<= 0.010 ficus if run);
  * temporal Phi_pop stays >= 95% of banked (Phi_pop_linked <= 1.05 x Phi_pop_banked).
  => adopt that operating point; produce clean linked line-drawing figures (chair/lego/ficus) ours-vs-shipped.
- NO-GO (every setting reaching >=25% continuity either bridges lego flat noise (lego P@1.5 drop > 0.015) OR
  rounds chair corners / spiderwebs OR degrades Phi_pop > 5%):
  => KILL linking. Freeze the shipped fragmented linelets; document the fragmentation honestly as an intrinsic
     property of object-space extraction under a frozen 3DGS (a limitations paragraph).
- MARGINAL: report all numbers; orchestrator + agy reconcile.

## DEFINITION OF DONE
- Confirm which shipped npz backs chair/lego (P/R match 0.657/0.596, 0.620/0.286).
- Table: baseline vs each (d_max x bridge on/off) variant — C, P@1.5, R@1.5, Phi_pop — chair AND lego.
- Median linelet length reported; the depth-discontinuity guard and bridge-evidence guard confirmed active.
- The GO / NO-GO / MARGINAL verdict WITH numbers against the frozen thresholds.
- Viz: for the best GO operating point (or the closest), side-by-side shipped-fragmented vs linked line drawing
  on chair AND lego from a held-out view, so corner-rounding / spiderwebbing / noise-bridging is visually checkable.
- Report ACTUAL numbers; never a verdict without them. Do NOT git commit (orchestrator handles git to the
  aggressive-linking branch). Narrate; show the verdict asap.

## PITFALLS
- The bridge-evidence + depth-discontinuity guards are what make this precision-safe — do NOT skip them. The
  ON-vs-OFF comparison is the proof they work.
- Temporal metric MUST be arc-length-weighted (the big-stroke-popping paradox), else linking games the count.
- Use the SAME warp operator / trajectory as the banked temporal eval, else Phi_pop isn't comparable.
- mesh EVAL-ONLY. Ignore any stale input-box text not from the orchestrator. Reuse existing pipeline code.
