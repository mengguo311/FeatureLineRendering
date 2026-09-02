# NEXT STEP — CONVERGE PATH-C PAPER (three-way unanimous: path B PERMANENT NO-GO)

CONTEXT (already done by orchestrator, do NOT redo):
- Phase 1f IS ALREADY COMMITTED + PUSHED by the orchestrator as commit ad574b5
  ("Phase 1f chain-gate appendix diagnostic: STRUCTURAL NO-GO ..."). Do NOT re-commit it.
  Verify with `git log --oneline -2` — you should see ad574b5 at HEAD. `git status` for
  out/phase1f_* and phase1f_spec.md should be clean/tracked.
- Three-way consensus (orchestrator + agy adversarial + your own 1f synthesis) = CONVERGE
  PAPER. Path B is a PERMANENT NO-GO on TWO independent structural barriers:
  (a) mesh-free supervision gap (legal lego->chair transfer AUC 0.5626 = chance, Phase 1e),
  (b) 1D-continuity severing under ANY post-hoc keep/drop on a fixed candidate set — even an
      in-scene mesh ORACLE: point-gating guard 0.6372, chain-pool ceiling 0.8782<0.90,
      chain_mean TEST P@1.5 0.6458 < baseline 0.6573 (Phase 1f).

YOUR TASK (path-C camera-ready finalization — NO new experiments, NO new scoring, NO GPU
unless a figure render strictly needs it):
1. INTEGRATE Phase 1e/1f as the pre-emptive reviewer knockout in the paper appendix +
   the relevant results section. The reviewer trap to disarm explicitly: "why not just
   train a lightweight discriminator / chain-pool to filter texture edges?" Answer with the
   ceiling characterization: even an in-scene mesh oracle cannot satisfy P@1.5>=0.71 AND
   topology-guard>=0.90 simultaneously (the topological trilemma). Every number must trace
   to out/phase1e_*.json / out/phase1f_*.json — cold-read grep must stay clean.
2. Frame this as Contribution 2 (structural-impossibility analysis of post-hoc candidate
   filtering), keeping Contribution 1 = the banked temporal-coherence win (7-13x / the
   pre-registered floor). Do NOT inflate; keep the honest floor framing already locked.
3. Resolve the residual camera-ready item (Fig5 finalization) and run one more whole-paper
   cold-read integrity pass: figure/table drift check, number-grep against source jsons,
   reference integrity. Report PASS/NO-GO with the fix list.
4. Do NOT touch mesh-free arms, do NOT reopen path B, do NOT alter any banked headline
   number. mesh-never-in-method-path invariant SACRED (mesh only in eval/oracle).
5. When done, write out/PHASE1G_CONVERGE.md summarizing what was integrated + the cold-read
   verdict. The orchestrator will commit+push it.

Escape-clear discipline: this file is your task. Nothing above should trigger a commit —
the orchestrator handles git.
