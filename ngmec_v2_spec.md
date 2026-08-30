# NG-MEC-v2 — additive multi-cue line scoring (the core precision push)

CONTEXT: CONDLAW-3-PRE Stage 2 PASSED (ship D_hat pred 0.772, measured 0.713, band
[0.692,0.852]; ordering lego'<ship<chair confirmed). That side-result is DONE. We now
attack the actual paper deliverable: precision gate P@1.5>=0.85 at R>=0.65 on BOTH chair
AND lego, temporal win preserved.

FIRST: commit the validated CONDLAW-3-PRE Stage 2 unblinding to branch m1b-milestone with
an honest message (it's a validated result; the Stage 1/1.5 gates were frozen at 92ce75f
BEFORE ship trained — timestamp is tamper-evident). Message should state PASS on both
tests, predicted-vs-measured 0.772 vs 0.713, and that this closes the Conditional Law as a
3-point pre-registered relation. Then start NG-MEC-v2.

DESIGN (revised after adversarial review — two of the naive stages have failed-as-veto
precedents, so DO NOT rebuild them):
- Proposals: frozen zero-shot TEED edges (BIPED weights) — our validated rankable seed source.
- Cue 1 (2DGS normal, NOT vanilla): dihedral/normal-dispersion score from the 2DGS surfel
  model (vanilla-3DGS normals are AUC~0.5 = DEAD; 2DGS gave AUC 0.958). Emit a CONTINUOUS
  score, not a binary gate.
- Cue 2 (multi-view epipolar consensus): for each proposal pixel, project across the held-out
  view set and score cross-view geometric agreement. Emit CONTINUOUS consensus confidence.
- AGGREGATION: additive log-odds  S = w_teed*S_teed + w_2dgs*S_normal + w_epi*S_consensus.
  NO sequential hard vetoes (ECO veto = NO-GO on lego; TGAP prior = anti-predictive as a
  gate). Spend orthogonal info ADDITIVELY — this is our KEY FINDING. Tune weights on chair
  TRAIN views only; evaluate frozen on held-out TEST views of BOTH chair and lego.

INVARIANTS: mesh NEVER in method path (mesh only via mesh_oracle.py for eval labels);
held-out eval; re-verify the 332/332 temporal manifest does not regress (temporal speedup
must stay >=7.0x vs per-frame Canny).

FROZEN GO/NO-GO (commit the threshold script BEFORE reading the final numbers):
- GO: min(P_chair@1.5, P_lego@1.5) >= 0.85 AND min(R_chair, R_lego) >= 0.65,
  temporal speedup >= 7.0x preserved.
- EARLY ABORT: if consensus culling drops recall below R=0.60 before P@1.5 reaches 0.80 on
  either scene during tuning, halt (signals over-culling of valid non-planar lines) and
  report which cue is over-penalizing.
Report to out/NGMEC_V2_RESULTS.md with a per-scene P/R table, weight values, and the
frozen-verdict json. Do not fabricate; every number from a real scored artifact.
