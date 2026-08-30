# TASK: fix frozen scorer, then LEGO frontier-lift generalization

## Part A — housekeeping (do first, small)
The XMEP frozen scorer was mis-specified (points/Pareto-envelope, full canny frontier)
vs the spec metric (segments/pull+prune[tuned+len], interpolated canny P@R, beyond-reach
excluded, canny frontier f<=0.50, reproduces published +0.0607). Fix the frozen scorer
script to compute the SPEC metric as primary, keep the mis-specified one only as a labelled
secondary, and recommit to m1b-milestone with an honest message noting the primary verdict
(pidinet_native_0.5 = PARTIAL at 0.456 of TEED; cross-model transfers at ~half strength,
threshold-within-detector matters more than detector-identity).

## Part B — LEGO frontier-lift generalization (the real experiment)
QUESTION: does the rankable-seed frontier-outward LIFT_P (TEED vs re-tuned Canny) that we
proved on chair GENERALIZE to lego (hard-surface, Canny purity 0.66)? This is DECOUPLED from
the absolute P>=0.85 & R>=0.65 gate, which lego ceiling-autopsy already proved unreachable
in principle (36.6% of GT creases have NO frozen-3DGS carrier => R_max ~0.63 < 0.65). That
ceiling is itself a publishable finding; do NOT chase the gate on lego.

METRIC: use the EXACT chair XMEP primary metric, unchanged — segments/pull+prune[tuned+len],
interpolated canny P@R, beyond-reach rows excluded, canny frontier f<=0.50. NO lego-specific
recall-band re-normalization (that risks cherry-picking the favorable slice). Held-out TEST
views only, no tuning on TEST. Re-verify the protected temporal manifest (expect 332/332 OK)
and keep mesh strictly eval-only (mesh_oracle for scoring, method path mesh-free).

FROZEN GO/NO-GO (commit the scorer BEFORE reading any lego number):
- GO (lift is scene-general): mean LIFT_P >= +0.030 in f-band [0.22,0.50]
  AND dP>0 (TEED beats Canny at matched f) on >= 80% of individual held-out TEST views.
- NO-GO (chair-only artifact): mean LIFT_P < +0.010 OR view-consistency < 80%.
- Between: PARTIAL, report straight.

Also report, for context: lego TEED best LIFT_P, at which f, P, R there, and the per-view
dP distribution (median, fraction>0). Write out/LEGO_GEN_RESULTS.md (thorough, honest,
cite the source json rows) + out/lego_gen_verdict.json. Do Part A first, then Part B.
