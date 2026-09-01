# Phase 1d — MESH-FREE SUPERVISION falsification (the path-B decider)

## Why this fire (three-way reconciliation)
Phase 1c GO is real but the probe was fit on MESH GT labels — EVAL-only, forbidden in the
method path. agy (adversarial) argued cross-scene chair->lego transfer is a TRAP as a gate
(asymmetric false-negative: chair fabric and lego decals are different categories, so a
NO-GO there wouldn't kill path B, only prove surface embeddings don't share coordinates
across categories). The dss9-agent synthesis wants the supervision route tested. Reconciled:
the ONE question that decides whether FAM-C is a real METHOD-PATH component vs an EVAL oracle
is — **does the DINOv2 discrimination survive when mesh is strictly EVAL-only?** Test that
directly and cheaply; keep cross-scene only as a demoted readout.

## The experiment (reuse the P1c harness/cloud; persist descriptors this time)
On BOTH chair (primary) and lego (secondary), Phase 1b ref40 triangulated clouds already used
in P1c. Train the SAME FAM-C linear probe (384-d frozen DINOv2 descriptors) but with
labels from MESH-FREE PSEUDO-LABELS only. Eval on held-out MESH GT (xsplit, same disjoint
3D x-halfspace protocol as P1c so numbers are directly comparable to 0.840/0.904).

Pseudo-label source (pick the cleanest mesh-free signal available; you choose, justify):
  - Option (b) preferred: geometry/photometric VOTES as noisy labels — e.g. take the
    top-confidence FAM-A high-contrast + FAM-B geometry-vote points as pseudo-positives and
    the low-signal bulk as pseudo-negatives, OR an unsupervised 2-cluster split of the DINO
    descriptors themselves (fully self-supervised, no geometry). Report which you used.
  - If you try more than one pseudo-label source, report each; the BEST mesh-free one sets
    the verdict.

## FROZEN GO / NO-GO (per-point xsplit AUC vs held-out mesh GT, chair primary)
  - GO (path B has a deployable method path): pseudo-label-trained FAM-C xsplit AUC >= 0.78
    AND clearly beats the FAM-A photometric baseline (~0.71). => proceed to build minimal
    precision pipeline (chain-gated).
  - NO-GO (method path dead without mesh supervision): xsplit AUC <= 0.72 (collapses toward
    the photometric baseline => DINOv2 buys nothing you can deploy) => CONVERGE THE PAPER
    (path C): frame DINOv2 discrimination as an EVAL-ONLY diagnostic ablation ("the missing
    discriminator is semantic surface identity, unrecoverable without labels"), and ship the
    banked temporal-coherence win (7-13x) as the core.
  - GRAY (0.72-0.78): partial; report honestly and LEAN toward converging the paper given the
    time-boxed (B)-then-(C) plan and the strong banked win.

## SECONDARY readout (free, since descriptors get persisted — NOT a gate)
Cross-scene transfer: fit the MESH-supervised FAM-C probe on chair, freeze, apply to lego
(and lego->chair). Report both AUCs. Interpret per agy's warning: a low number is NOT a
path-B kill, only a category-transfer datapoint. This just characterizes how category-bound
the surface-identity readout is (useful for the paper either way).

## Invariants (SACRED — do not violate)
  - mesh-never-in-method-path: pseudo-labels must be mesh-FREE; mesh only for the EVAL AUC.
    AST-verify the training-label path touches no mesh_oracle.
  - held-out xsplit evaluation only; report leakage-guarded chain-AUC too if cheap.
  - Do NOT touch the temporal-coherence banked result. Only u00134 procs, CUDA_VISIBLE=1.
  - Persist the DINO descriptors this run (P1c did not; that's why cross-scene needs a rerun).

Write a thorough out/DEXPRIMARY_P1D_RESULTS.md with the honest verdict. Negative result is a
FIRST-CLASS outcome here — it cleanly justifies converging the paper.
