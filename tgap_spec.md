# TGAP — TEED-Gated Adaptive Pull+Prune (lego primary, held-out TEST)

## Why (from CAP)
CAP proved lego's recall miss is NOT a representational void: rho_B2 = 0.0799 (gate 0.30),
B2 true-void only 1.31% = below chance. Topology is present in the 3D carrier -> KEEP it.
BUT the Class-A "candidate was nearby" test is near-VACUOUS on lego (72.9% missed vs 72.5%
random foreground, 0.4pt margin). So GLOBAL prune relaxation just retraces the mapped P/R
frontier by spending near-uniform noise. The binding quantity (per the TEED breakthrough) is
SELECTIVITY-AT-HIGH-RECALL. Therefore: relax the prune ONLY where the learned edge prior agrees.

## Method (object-space, mesh NEVER in path; TEED = frozen zero-shot BIPED weights, EVAL-independent)
Spatially modulate NMS suppression radius r and min-length L_min by the projected 2D TEED edge
response E in [0,1] at each candidate's projected uv:
  r(x)     = r_base * (1 - alpha * E(x))
  L_min(x) = L_base * (1 - beta  * E(x))
High-TEED regions get relaxed pruning + stronger DT-pull; texture/background keeps strict prune.
Linelet/polyline definitions unchanged. Pick alpha,beta on VAL only, freeze, report TEST.

## Three arms (all lego TEST, f-frontier by sweeping f)
- A  baseline: current tuned+len prune (the committed headline).
- B  TGAP: TEED-gated adaptive relaxation as above.
- C  CONTROL (TEED-blind): GLOBAL relaxation of r_base,L_min tuned to MATCH arm B's recall.
     This isolates selectivity: if B only beats A because of extra recall, C matches it.

## FROZEN go/no-go (decide BEFORE looking at TEST)
GO iff ALL hold on lego held-out TEST:
  1. f-frontier LIFT_P: B moves the lego frontier OUTWARD, best LIFT_P >= +0.030
     (measured the same way as the TEED breakthrough's +0.0607 on chair).
  2. B beats C on the frontier at matched recall (selectivity is real, not just recall):
     LIFT_P(B) - LIFT_P(C) >= +0.015. If B ~= C, the gate FAILS (global would have done it).
  3. Precision no-regress: at matched recall vs A, no precision drop.
  4. TEMPORAL HARD VETO: object-space inter-frame coherence < 2.0% relative degradation vs A,
     and keeps >= 8x margin over per-frame Canny. Any temporal regress => NO-GO regardless.
NO-GO on any => report straight as a negative result; do not tune to pass.

## Invariants
- mesh only via mesh_oracle for EVAL; method imports nothing from it.
- held-out TEST for all reported numbers; alpha/beta/global-r tuned on VAL only.
- CUDA_VISIBLE_DEVICES=1, u00134 procs only.
- Write out/TGAP_RESULTS.md (honest, per-arm frontier + temporal table) + out/tgap_*.json.
- Do NOT commit until validated. First commit CAP (validated diagnostic) with an honest message.
