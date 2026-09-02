## Appendix A — Can a discriminator patch the boundary? A pre-emptive falsification
*(All numbers from `RESULTS_MASTER.md` §4, sourced in `phase1e_test_eval.json`,
`phase1e_scores_meta.json`, `phase1f_test_eval.json`, plus banked ledger numbers
quoted unchanged; full protocol and caveats in `PHASE1E_GATE_CHECK.md` /
`PHASE1F_CHAIN_GATE.md`.)*

The natural reviewer objection to §5 is operational: *"the crease-vs-texture signal
exists (0.8401/0.9044) — why not just train a lightweight discriminator, or pool it over
chains, and filter the texture edges out?"* We ran that experiment, both ways, before a
reviewer could ask — as two post-lock falsification probes under the paper's own
discipline: thresholds frozen on VAL views only, TEST evaluated exactly once per arm, and
the method-path invariant intact (every gate SCORE is mesh-free at the target scene; the
in-scene mesh-supervised probe appears only as a labelled oracle upper bound, never as a
result). The candidate set is the Phase-1b chair triangulated cloud (272,366 points), and
the metric is the same macro segment-raster P@1.5px convention as the pipeline baseline
it must beat (0.6573 at recall 0.5959, quoted from its banked run, never re-run).

**A.1 Mesh-free gating converts nothing (the supervision barrier, at the cloud level).**
The only deployment-legal transfer discriminator at chair — fit on the *other* scene's
mesh labels — carries AUC 0.5626 (chance; §5.4's 0.8245 is the *reverse* direction, fit
on chair's own mesh, and is therefore not legal as a chair gate). Gated at matched
recall, it moves precision from 0.3189 (ungated) to 0.3216. The best in-scene mesh-free
gate (the physics-frozen geometric-photometric vote of §5.4) reaches **0.4458** at recall
0.6156 — far under both the 0.6573 baseline and the probes' frozen 0.71 GO bar — and
already breaks crease connectivity (topology guard 0.8811, bar 0.90). NO-GO, with margin.

**A.2 Even the oracle cannot filter its way through (the topological trilemma).** The
same cloud gated by an in-scene *mesh-supervised* probe (in-sample AUC 0.9578 — the
loosest possible upper bound, and mesh-in-the-loop, so an oracle by construction) reaches
P@1.5 **0.7970** at matched recall — and retains only **0.6372** of the
baseline-covered GT crease segments: per-point selection drops the low-scoring bridge
points that keep 1D chains connected. Chain-mean pooling — the reviewer's fix, run
exactly as proposed on the label-pure chain structure of §5.3 (1,692 components) —
repairs part of that (guard 0.6372 → 0.7481 mean-pooled, 0.7970 median-pooled) at a real
precision cost (point-oracle 0.7970 → chain-gated 0.6458, *below* the 0.6573 baseline),
and its ceiling is structural: keeping **every** chain with
no thresholding at all already caps the guard at **0.8782 < 0.90**, because the 42.36 %
of candidates no proximity+direction chain absorbs are precisely the bridging points.
Across every tested gate — mesh-free or oracle, point-gated or chain-pooled — no
tested operating point attains precision ≥ 0.71, recall ≥ the baseline's 0.5959, and
topology ≥ 0.90 *simultaneously*. That is the trilemma, and it is a property of the
repair class: post-hoc keep/drop filtering of a fixed candidate cloud trades precision
against 1D continuity for every ranking we could construct, up to an in-sample oracle.

**A.3 What this hardens.** Two independent barriers now stand between the cloud and a
deployable precision fix: the supervision gap (mesh-free discrimination is chance-level
where it is legal, §5.4 and A.1) and the continuity severing (even oracle ranking cannot
threshold without fragmenting chains, A.2). Fixing either alone is measurably
insufficient; a build that wanted this precision would need *topology-aware
construction* — connectivity as a constraint during line formation, not a casualty of
filtering after it — plus labeled scenes. This is why §5's boundary ships as a measured
boundary: the obvious patches are not merely unattempted, they are falsified. Probe
scope, disclosed: cloud-level results are chair-only (n=1 scene); the oracle bound is
in-sample (loosest); the cloud is rasterised as points inside the segment-raster
convention (its 272k points saturate recall at 0.9540 ungated, so the NO-GO is not a
rasterisation artifact).
