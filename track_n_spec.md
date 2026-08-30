# TRACK N: Cross-model edge-prior invariance (consensus-only, chair PRIMARY + lego control)

## Rationale (frozen decisions)
- lego joint gate is ABANDONED: 5th independent NO-GO. Max recall at f=1.0, zero culling = 0.466 pts / 0.557 seg << 0.65 floor. Recall is monotone in keep_frac (2989/2989 audited). This is a representation ceiling of the frozen vanilla-3DGS carrier, NOT a gate problem. Do NOT retune lego for recall.
- Normal gate is REFUTED and DROPPED: every tau_n>0 hurt precision monotonically (tau_n=0.40 -> dP -0.0621); honest selection = tau_n=0. Reason: at a real crease the frozen-3DGS normal is discontinuous, |n.v| arbitrary. Pipeline is now CONSENSUS-ONLY (multi-view epipolar consensus cull), no normal gate.
- Paper reframed: (1) temporal-coherence core [PROTECT, do not regress], (2) chair precision via learned-edge-prior + epipolar consensus, honest per-scene conditional law (chair-yes / lego-no).

## Task
Reuse the EXACT consensus-only pipeline from NG-MEC (tau_n=0) but swap the TEED edge proposer for two other frozen zero-shot learned edge detectors:
  - PiDiNet (zero-shot, table5/BSDS pretrained weights, no finetune)
  - DexiNed (zero-shot, BIPED pretrained weights, no finetune)
Keep everything else identical: same carrier, same DT-pull+prune[tuned] primary stage, same f-grid {0.22,0.30,0.40,0.50}, same held-out TEST split, same mesh_oracle eval (mesh NEVER in method path), same reference arm teed_native_0.5.

Run on chair (PRIMARY, precision claim) AND lego (CONTROL, to confirm the dichotomy persists — expect chair-yes/lego-no).

## Metrics to emit (out/track_n_invariance.json)
For each {detector x scene}: rows with f,P,R,P25,R25,n; mean_dP (points & segments) vs teed_native_0.5 at matched f; dR at matched f.
Also emit the chair temporal ratios at 30/60/120/240 frames for the winning consensus arm of EACH detector vs baseline (protect temporal: report relative regression).

## FROZEN GO / NO-GO
- GO (invariance CONFIRMED): BOTH PiDiNet AND DexiNed show, on chair, mean_dP >= +0.006 (points) with |dR| <= 0.005, AND replicate the dichotomy (lego mean_dP < +0.003). Temporal must not regress worse than -8.5% at 240f (parity with TEED's -8.41%).
- NO-GO (TEED-specific): if either detector gives chair mean_dP < +0.003 on points, the lift is NOT a general property of learned edge priors -> restrict paper to TEED as an empirical case study + temporal core.
Rationale for the +0.006 bar (deliberately below TEED's own +0.011): we want SIGN-CONSISTENT transfer + same conditional law, not identical magnitude; a hard +0.010 bar would be circular against TEED itself.

## Notes
- If PiDiNet/DexiNed weights aren't present, download to ~/3dgs_line/tier1/weights/ (zero-shot only, no training). If a detector genuinely can't be obtained, run the one that can and clearly mark the other as BLOCKED in the json.
- Write a thorough track_n_invariance.md summary. Commit nothing unless the whole track closes.
