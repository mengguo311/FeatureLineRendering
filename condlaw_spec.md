# CONSOLIDATE — Freeze the Conditional Law as paper Result 2 + honest lego precision ceiling

STATUS: lego precision-gating is now CLOSED from three independent directions:
  - ECO/NG-MEC (epipolar consensus): real but small on chair, NOTHING on lego.
  - TGAP (TEED-gated pull relaxation): all 4 gates fail on lego, LIFT_P=-0.0107, prior ANTI-predictive.
  - DIAG-2DGS (2DGS/mesh dihedral gate): NO-GO; fails on the GT MESH too. Split-free normal-dispersion gap between TrueCrease and DecalDistractor = 0.32 deg on ground truth. <1% of lego surface flat at measurable scale; inter-crease distance (0.0098) == surfel spacing.
No further precision-gate is worth building on lego: the geometry is physically underdetermined at ground truth. Confirmed by orchestrator + agy adversarial round this fire.

This is an ANALYSIS/DIAGNOSTIC-ONLY task. NO new method-path file. NO change to run_m1b.py. Mesh read for EVAL/LABELS only (mesh_oracle), as permitted. Held-out TEST throughout. Do NOT touch or recompute any m1b_stroke_temporal_* file; verify the protected manifest unchanged (sha256sum -c out/CMEPI_protected_manifest.sha256, expect 332/332 OK). Nothing on a default path. Commit ONLY if the frozen gate below GO's.

## Goal
Freeze the paper's Result 2 (the Conditional Law) with ONE clean load-bearing scalar per scene, so the honest story is stated in numbers, not prose. The scalar (agy-selected): 
  DRR@80 = Distractor Rejection Rate at >=80% TrueCrease recall, i.e. on the GT-mesh dihedral/dispersion statistic, sweep the operating point to the threshold where TrueCrease recall (fraction of TrueCrease loci scored ABOVE threshold) >= 0.80, and report the fraction of DecalDistractor loci correctly scored BELOW it. DRR@80 = 0.50 means chance (indistinguishable); DRR@80 high means geometry cleanly separates decals/distractors from creases.

Reuse EXISTING artifacts wherever they already contain the needed per-linelet statistic:
  - lego: out/diag2dgs_lego_test.{json,npz} (already has the split-free spreadmesh dispersion + surfel3d dihedral per labelled linelet on GT mesh). Compute DRR@80 for BOTH the GT-mesh arm (spreadmesh / mesh3d) and the 2DGS surfel arm.
  - chair: use the PLAN1 / TEED_GEN artifacts that produced the AUC 0.967 rendered-normal-ribbon result on chair's printed-fabric class (out/*.json referenced by PLAN1_RESULTS.md). If the per-locus statistic is cached, compute DRR@80 directly; if only AUC is stored, derive DRR@80 from the stored score arrays. Do NOT retrain anything. If chair's per-locus arrays are not on disk, say so explicitly and report chair's AUC 0.967 as the ceiling proxy with a clearly-labelled note (no fabrication).

## Deliverable: out/CONDLAW_RESULTS.md
A 2-row table (chair, lego) x columns: {scene, class-contrast source, statistic, DRR@80 (mesh arm), DRR@80 (2DGS arm if available), AUC (for cross-ref), n_TrueCrease, n_Distractor}. Plus:
  - the one-sentence honest lego precision-ceiling statement (draft below; refine to match measured numbers, do NOT overclaim):
    "On the hard-surface lego scene, static geometric crease precision is intrinsically bounded: at ground truth the true-crease and TEED-confident non-crease loci are geometrically indistinguishable (normal-dispersion gap 0.32 deg, DRR@80 ~= <fill measured>), because lego is micro-relief end-to-end (<1% of the surface flat at measurable scale) and the inter-crease spacing equals the reconstruction resolution — so texture/relief-vs-crease disentanglement is underdetermined from surface differential geometry alone, independent of the 3DGS reconstruction."
  - the contrasting chair statement (learned prior buys rankable seeds because a genuinely flat printed-fabric class exists there).
  - explicit restatement of the protected temporal-coherence win (7-13x object-space vs per-frame Canny, held-out) as Result 1, untouched.

## FROZEN GO/NO-GO (report the verdict straight)
Compute DRR@80 for both scenes on the GT-mesh arm.
  - CONDITIONAL LAW CONFIRMED (GO): DRR@80(chair) >= 0.80 AND DRR@80(lego) <= 0.55.
      => the law is a real dichotomy; commit CONDLAW_RESULTS.md to m1b-milestone with an honest message; this closes the precision arc.
  - NO-GO / LAW WEAKER THAN CLAIMED: if DRR@80(chair) < 0.80 (chair separability weaker than the AUC 0.967 implied) OR DRR@80(lego) > 0.55 (lego not actually at chance) -> do NOT commit; report the discrepancy straight and flag for the next fire; the conditional-law narrative needs revision.
Report every number with its source file. Do NOT fabricate; if an input array is missing, say so and mark that cell N/A.

## Invariants (unchanged, sacred)
- mesh NEVER in the method path; only mesh_oracle for eval/labels here.
- held-out TEST only; any threshold-selection on VAL, report TEST beside it.
- protected temporal results untouched; verify manifest 332/332 OK.
- CUDA_VISIBLE_DEVICES=1, only u00134 procs, GPU ~3GB.
- new artifacts under a CONDLAW_ / condlaw_ prefix only; overwrite nothing.
