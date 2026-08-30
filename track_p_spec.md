# Track P — Temporal-Win Generalization (E_warp + per-stroke survival), the paper's headline

DECISION (orchestrator + agy, this cycle): The P>=0.85 post-hoc precision program is
FORMALLY ABANDONED — 5 independent geometric culls (geometry-gate, carrier-persistence,
2DGS-gate, hybrid-veto, NG-MEC) all failed the same way. NG-MEC NO-GO confirmed: chair
tops out P@1.5=0.68@R=0.66; lego recall floor 0.65 UNREACHABLE (R_max 0.37); the cull
even DEGRADES temporal coherence (C/B=0.889, fails 0.95 gate). Conditional Law is now a
stated SCOPE BOUNDARY, not a bug to fix. Pivot to hardening the ROBUST win.

## Goal
Prove the object-space temporal win generalizes ACROSS trajectories AND scenes, with a
reviewer-proof metric. Do NOT chase precision. Protect + quantify arm B (unculled).

## Arms (matched at f, held-out TEST cams only, mesh ONLY in eval)
- Arm A = per-frame TEED (image-space baseline)
- Arm B = unculled object-space TEED-seeded linelets (our method)
(No arm C / no cull — culling is abandoned and it hurt temporal.)

## Conditions: 6 = {chair, lego} x {T1_orbit, T2_orbit_zoom, T3_spline}
Reuse the Track O trajectory generators + look-at correction so every arm sees identical
frames. Run lego too (Track O was chair-only — that gap must close).

## Metrics
1. E_warp: optical-flow re-projected frame-to-frame stroke displacement error
   (per-frame flow warp of arm's strokes, matched, median displacement). Report the
   RATIO E_warp(A)/E_warp(B) per condition at the 240-frame window.
2. Per-stroke SURVIVAL: P(stroke lifetime > K frames) curves for A vs B, K in {2,4,8,16,32}.
   Headline stat = median stroke lifetime B / median lifetime A per condition.

## FROZEN GO/NO-GO (freeze scorer + write these thresholds to out/track_p_verdict.json
   with a code hash BEFORE computing any number)
- PRIMARY: worst-case-over-all-6-conditions  min_{s,t} E_warp(A)/E_warp(B) >= 2.0
- SECONDARY: per-stroke median-lifetime ratio B/A >= 2.0 in every one of the 6 conditions
- GUARD (temporal no-regress): B's 240f Frechet multiplier vs A must stay >= its
  Track O value on T1/T2/T3 for chair (no silent regression from refactor).
- GO => this is the paper's hardened headline; commit to m1b-milestone.
  NO-GO on any spline/lego condition => report the trajectory/scene dependence HONESTLY
  as the scope of the temporal claim (still a real contribution, just bounded).

## Invariants
mesh-never-in-method-path (mesh only in eval), held-out TEST only, protect temporal win,
never fabricate — every number from a real result file. Tag all figures --viz_tag track_p.
Verify protected manifest 332/332 before and after.

Write a thorough out/TRACK_P_RESULTS.md (verdict table + survival curves + per-condition
E_warp ratios). Report when the full 6-condition run completes.
