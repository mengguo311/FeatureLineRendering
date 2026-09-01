# PHASE 1d — mesh-free supervision falsification (the path-B decider)
# **VERDICT: NO-GO — the Phase 1c GO does not survive without in-scene mesh supervision**

Spec `tier1/phase1d_spec.md`. The question: is the DINOv2 crease-vs-texture discrimination a
deployable METHOD-PATH component, or an EVAL oracle that only works because the probe saw
in-scene mesh labels? Answer, by measurement: **an EVAL oracle.** Trained on the best
mesh-free pseudo-labels available, the FAM-C probe collapses from 0.8401 to **0.6371** on
chair (frozen NO-GO bar: ≤ 0.72) — below even the photometric baseline it needed to beat.

Per the pre-registered three-way plan, this is a FIRST-CLASS negative result: it cleanly
converges the paper (path C) on the banked temporal-coherence win (7–13×), with the ceiling
characterization + this falsification as the honest supporting story.

Setup: Phase 1b ref40 clouds, Phase 1c harness and xsplit protocol (fit on one 3D
x-halfspace, evaluate on the held-out one) so every number is directly comparable to Phase
1c's mesh-supervised 0.8401 (chair) / 0.9044 (lego). DINO descriptors persisted this run
(`out/dexp1d_feats_{chair,lego}.npz`, 226/290 MB). Mesh enters ONLY at final-AUC time.

**Supervision hygiene (SACRED invariant, verified):** pseudo-labels are built by
`src/edge_semantics.{crease_vote,pseudo_labels_votes,pseudo_labels_cluster}` — a METHOD-PATH
module whose transitive import closure is {common, render, visibility, edge_semantics}, AST-
verified mesh-free; the functions take only feature arrays (FA, FB, DD), no label argument.
Every pseudo-label threshold was frozen a priori from physics (vote = mean percentile of
normal_angle + depth_curv + luma_step, signs fixed by "a crease is a geometric discontinuity
with a shading step", alpha_drop excluded as sign-undecidable a priori; pos = top 15 %,
neg = bottom 50 %). Nothing was tuned against any mesh AUC.

---

## The measurement

Two mesh-free supervision sources (both reported; best sets the verdict):
- **PL-VOTE**: pseudo-positives/negatives from the frozen geometry+photometric vote.
- **PL-CLUSTER**: fully self-supervised — k-means (k=8) on the DINO descriptors, clusters
  oriented crease/texture by the mesh-free vote (a cluster is positive iff its mean vote
  exceeds the global mean).

| chair (primary) | label agreement w/ GT | FAM-C xsplit AUC | FAM-A xsplit AUC | guarded chain |
|---|---|---|---|---|
| **PL-VOTE** | 0.773 | **0.6371** | 0.7326 | 0.6016 |
| PL-CLUSTER | 0.694 | 0.6168 | 0.7317 | 0.6506 |
| raw vote V alone (no probe, no DINO) | — | 0.6329 | — | — |
| *mesh-supervised ceiling (recomputed)* | — | *0.8395* | *0.7112 (P1c)* | *0.8205 (P1c)* |

| lego (secondary) | agreement | FAM-C xsplit | FAM-A xsplit | guarded chain |
|---|---|---|---|---|
| PL-VOTE | 0.740 | 0.5819 | 0.4222 | 0.5468 |
| **PL-CLUSTER** | 0.665 | **0.6569** | 0.5637 | 0.6662 |
| raw vote alone | — | 0.6488 | — | — |
| *mesh-supervised ceiling (recomputed)* | — | *0.9046* | — | *0.8913 (P1c)* |

Sanity: the recomputed mesh ceilings match Phase 1c to the 3rd decimal (0.8395 vs 0.8401,
0.9046 vs 0.9044) — same harness, so the collapse is attributable to the supervision source
and nothing else.

## The frozen gate

| gate (chair, best mesh-free FAM-C xsplit AUC) | bar | measured |
|---|---|---|
| GO | ≥ 0.78 and clearly beats FAM-A (~0.71) | — |
| GRAY | 0.72 – 0.78 | — |
| **NO-GO** | ≤ 0.72 | **0.6371** — and it does NOT beat FAM-A (0.7326) |

**NO-GO, with margin, on both criteria.** Lego confirms (best 0.6569 vs ceiling 0.9046).

## Why it failed — the diagnosis, which is the publishable part

1. **Zero denoising.** The classic weak-supervision hope — a strong feature space averages
   out label noise — did not materialize: the FAM-C probe lands AT its supervision's own
   quality (probe 0.637 ≈ raw vote 0.633 on chair), never above it. The pseudo-labels'
   errors are not noise; they are SYSTEMATIC (high-contrast texture edges get pseudo-
   positive, shallow shaded seams get pseudo-negative), and a probe faithfully reproduces
   systematic bias.
2. **DINOv2's strength is exactly what turns against it.** Under biased labels, FAM-A
   (weak, 5-d) OUTPERFORMS FAM-C (384-d) on chair — 0.733 vs 0.637. The surface-identity
   memorization that made FAM-C win Phase 1c (it knows *which surface* a point is on) makes
   it the BEST possible fit to the pseudo-labels' surface-correlated mistakes. The richer
   the representation, the more faithfully it learns the wrong thing.
3. **The self-supervised route fares no better** (0.617/0.657): DINO clusters are clean
   surface segments, but *orienting* them crease-vs-texture needs exactly the semantic bit
   that no mesh-free signal provides. The information is not missing from the descriptors —
   the mesh-supervised ceiling proves it is there — it is unreachable without labels.

## SECONDARY (demoted per the spec — a datapoint, not a gate)

Cross-scene transfer of the MESH-supervised probe (descriptors now persisted, so this is free):

| direction | AUC | within-scene ceilings |
|---|---|---|
| **chair → lego** | **0.8245** | 0.8395 → 0.9046 |
| lego → chair | 0.5626 | 0.9046 → 0.8395 |

Honestly flagged both ways: chair→lego at 0.8245 nearly matches lego's within-scene ceiling —
so "unrecoverable without labels" must be stated precisely: unrecoverable without *some*
mesh-labeled scenes; a probe fit on labeled training scenes CAN transfer, in one direction of
the two tested. The reverse direction (0.5626) is agy's category-asymmetry in the flesh: the
lego-trained probe learned lego-specific surface identities. One seed scene is not a method;
a multi-scene training set might be — that is a future-work sentence for the paper, not a
path-B revival on this evidence (the deciding gate was the in-scene mesh-free route, and it
is dead).

## What goes into the paper (path C convergence)

- Core: the banked temporal-coherence win (7–13×, untouched).
- The coverage-ceiling characterization: Phase 0 (single-view lift ≈ chance on lego, the
  edge-map cardinality bound), Phase 1b (triangulation as a real localization fix, MARGINAL,
  detector-bound), Phase 1c (the missing discriminator is semantic surface identity —
  DINOv2 separates at 0.84–0.90 with in-scene labels), and Phase 1d (that separation is
  supervision-bound: mesh-free training collapses it to ~0.64; framed as an EVAL-ONLY
  diagnostic ablation, with the chair→lego 0.82 transfer as the honest asterisk).

## Honest caveats

- Two pseudo-label sources were tried, both frozen a priori; a cleverer mesh-free teacher
  (e.g. multi-view-consistent shading decomposition) could in principle do better — but the
  vote's agreement (0.77) was already above what its probes achieved, so the bottleneck is
  the bias structure, not the agreement level.
- The lego FAM-A-on-votes AUC of 0.42 (below chance) is the same bias mechanism: the vote's
  luma component is anti-correlated with lego creases (P1c measured luma_step sign −1 there).
- `nanmean of empty slice` warnings are benign (candidates never visible in any ref view).
- Nothing committed; only Phase 0's additive `M src/render.py` remains in the working tree.

Artifacts: `scripts/dexprimary_p1d.py`, `--dump_feats` in `scripts/dexprimary_p1c.py`,
pseudo-label builders in `src/edge_semantics.py`, `out/dexp1d_feats_{chair,lego}.npz`,
`out/dexprimary_p1d.json`, `logs/dexp1d_*.log`.
