# GEOLINE STEP 5 — rejected-candidate mechanism analysis: bad ranker, or bad cut?

`scripts/geoline_step5.py`. Existing artifacts only: the f = 1.00 pooled linelets already on
disk for all four solids, plus the ten held-out gbuffers per solid that the oracle labels
require. No pipeline change, no retuning of anything.

**MESH EVAL-ONLY ATTESTATION.** The GT mesh, via `tune_lib.Harness -> src.mesh_oracle`,
supplies the oracle labels only. Oracle-good is a median held-out-view GT-crease distance of
at most 1.5 px, oracle-bad is more than 3.0 px, the same convention as Steps 1 and 2. No mesh
quantity enters any method-path signal. Nothing committed.

---

## VERDICT

> **THRESHOLD-LIMITED. Reported as NOT-GENERAL about the frozen thresholds, with ZERO
> retuning, exactly as the pre-registration requires.**
>
> The consensus statistic **does** order oracle-good above oracle-bad on the icosahedron, at
> AUC **0.8219**. What fails is the frozen cut. The shipped rule keeps only **28.3 percent**
> of genuinely good candidates there, against 41 to 53 percent on the other three solids,
> because the icosahedron's inlier-ratio distribution is shifted down by roughly a factor of
> two while the 0.50 threshold stays put.
>
> **The single number that explains Step 4:** the median oracle-good linelet on the
> icosahedron has an inlier ratio of **0.279**, which is *below* the frozen 0.50 cut. More
> than half of all genuinely good candidates are discarded before ranking can matter. On the
> cube the median good linelet sits at 0.517, just *above* the cut. Step 4's R 0.2598 is that
> distributional accident, not a geometric one.

**Margin disclosure.** RANKER-LIMITED required AUC below 0.70 **and** at least 0.10 below the
mean of the other three. The relative clause missed by **0.0096** (delta −0.0904 against
−0.10), which is razor-thin and is disclosed rather than buried. The absolute clause was not
close: 0.8219 against a 0.70 bar, clear by 0.12. So the verdict does not hinge on the narrow
leg. The honest summary is *mostly threshold, with a real but secondary ranker gradient*,
since the AUC ordering tracks the failure ordering exactly.

**Mechanism leg NOT RUN.** The pre-registration gates it on RANKER-LIMITED, which did not
fire. The crease-ambiguity and compromise-signature measurements were therefore not computed,
and my symmetry-aliasing hypothesis remains untested. It is implemented in the script and
ready if a later step licenses it.

---

## 1. The primary legs

| solid | AUC(inlier ratio) | AUC(−median resid) | keeps oracle-GOOD | keeps oracle-BAD | retention |
|---|---|---|---|---|---|
| gcube | **0.9404** | 0.8736 | **0.526** | 0.011 | 0.268 |
| cadpartA | 0.9019 | 0.8826 | 0.458 | 0.045 | 0.222 |
| gprism | 0.8948 | 0.8615 | 0.413 | 0.026 | 0.188 |
| **gicosa** | **0.8219** | 0.7840 | **0.283** | **0.003** | **0.121** |

Both statistics agree on the ordering, and both put the icosahedron last. But an AUC of 0.82
is a working ranker, not a broken one.

**The rule is not malfunctioning on the icosahedron, it is operating far too conservatively.**
It keeps the smallest share of good candidates *and* the smallest share of bad ones, 0.003.
That is the signature of a fixed threshold meeting a shifted distribution, not of a statistic
that has stopped discriminating.

## 2. Where the frozen cut lands — the transport failure, quantified

| solid | median inlier ratio (all) | median inlier ratio (oracle-good) | 0.50 sits at this percentile | cut by ratio | cut by median resid | cut by n_vis |
|---|---|---|---|---|---|---|
| gcube | 0.211 | **0.517** | 72.6th | 0.726 | 0.732 | 0.000 |
| cadpartA | 0.203 | 0.472 | 77.3rd | 0.773 | 0.778 | 0.000 |
| gprism | 0.183 | 0.432 | 80.8th | 0.808 | 0.812 | 0.000 |
| **gicosa** | **0.104** | **0.279** | **87.7th** | 0.877 | 0.879 | 0.000 |

A single constant of 0.50 lands anywhere between the 72.6th and the 87.7th percentile
depending on the solid. That fifteen-point spread is the whole of Step 4's NOT-GENERAL result.
**No frozen pair of thresholds serves all four solids**, and per the pre-registration that is
reported as a finding, not repaired.

Two structural observations that fall out for free:

- **The two clauses are near-redundant.** The ratio clause and the median-residual clause
  remove almost identical fractions on every solid, 0.877 against 0.879 on the icosahedron and
  0.726 against 0.732 on the cube. They are cutting essentially the same linelets, so the rule
  has one effective degree of freedom, not two.
- **Visibility is never the binding clause.** The `n_vis >= 3` requirement removes 0.000 of the
  pool on all four solids and can be disregarded in any redesign.

## 3. A design-argue correction, recorded because it changed the test

The intuitive signature, residuals landing on a symmetry-equivalent wrong edge at similar
depth, **cannot occur as stated**. A linelet holds one 3D position optimised against all views
jointly, so it cannot lie on edge E in one view and on E-prime in another. When views disagree
about which edge a candidate belongs to, the pull settles it at a compromise position on
neither, and the residual is then large and roughly uniform across views rather than small to
a wrong target. Searching for small-residual-to-wrong-edge would have found nothing and we
would have rejected the hypothesis for the wrong reason. The compromise signature is high
median residual together with low inlier ratio, and both aggregates are already on disk, so it
is testable without re-running the pull whenever a later step licenses it.

## 4. What this licenses, and what it does not

It licenses **replacing the fixed pair of constants with a scene-independent rule that is still
no-knob**, since the evidence is now specific: the statistic ranks, the constants do not
transport, one clause is redundant, and the visibility clause is inert. It does **not** license
retuning 0.50 or 1.5 on any scene, and none was performed.

It does not resolve why the icosahedron's distribution is shifted. Symmetry aliasing and
silhouette crowding both remain live and both remain untested, because the mechanism leg was
correctly gated off.

Two cautions on the numbers above. The good and bad classes exclude the 1.5 to 3.0 px band by
construction, so these AUCs describe a gapped boundary and are not a forecast of ranking
performance at the tolerance, the same caveat that explained Step 3's under-conversion. And
oracle-good is a per-linelet centre label, whereas the deliverable metric scores rendered
segments, so the retention percentages are not directly convertible into recall.

## 5. Artifacts

`out/geoline_step5.json`, `scripts/geoline_step5.py`. Inputs were
`out/linelets_cadpartA_step3pool.npz` and `out/linelets_{gcube,gicosa,gprism}_step4.npz`,
all pre-existing. Nothing committed.
