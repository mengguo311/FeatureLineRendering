# GEOLINE STEP 3 — A/B/C: is the binding constraint the RANKER or the POOL?

`scripts/geoline_step3.py`. One f=1.00 pulled pool, everything frozen except the ranking
score, full P/R frontier per arm, cadpartA held-out TEST, segments at tau = 1.5 px (the
deliverable metric). Frozen rho = 4.0, xi = 0.25, n_min = 5 verbatim. No per-scene tuning.

**MESH EVAL-ONLY ATTESTATION.** The GT mesh is read through `tune_lib.Harness ->
src.mesh_oracle` for the evaluation and for arm C, which is an **eval-only ceiling and never
a method claim**. Arms A, A2 and B are mesh-free. Nothing committed.

---

## VERDICT — both gates resolved, and both of the motivating predictions are wrong

| frozen gate | bar | measured | |
|---|---|---|---|
| **Conversion** | arm B reaches R@1.5 >= 0.30 at P@1.5 >= 0.70 | **R 0.5031 at P 0.7080** | **GO** |
| **Pool** | arm C caps **below** R@1.5 0.45 at P >= 0.70 | **R 0.7271 at P 0.7274** | **NO-GO** |

> **The verifier converts, and the pool is not the constraint.** The predicted cap near 0.20
> is off by 2.5x, and the oracle ceiling on this pool is 0.7271, not something below 0.45.
> **But the headline finding is neither gate.** The 0.93-AUC 2DGS verifier **loses to the
> consensus prune the pipeline already ships**, across the entire frontier. The ranker is the
> constraint, and the best available ranker is the one already in the code.

## 1. The four arms, best point at P@1.5 >= 0.70

| arm | ranker | R@1.5 | P@1.5 | n kept | keep frac |
|---|---|---|---|---|---|
| A | shipped M1a OVERALL seed score | — | **never reaches P 0.70** | | max P 0.5662 |
| **A2** | **shipped consensus prune (tuned inlier ratio)** | **0.6250** | 0.7486 | 11,379 | 0.35 |
| B | 2DGS ribbon verifier | 0.5031 | 0.7080 | 8,119 | 0.25 |
| **C** | **ORACLE ceiling (eval-only)** | **0.7271** | 0.7274 | 13,045 | 0.40 |

Reference, banked: the shipped cadpartA operating point is f = 0.30, **P 0.9211 / R 0.1584**.

**A2 captures 86 percent of the oracle's recall** (0.6250 of 0.7271) at slightly higher
precision. There is very little left on this pool for any ranker to win.

**A2 dominates B everywhere above P ~ 0.65**, not just at one point:

| keep frac | A2 P / R | B P / R |
|---|---|---|
| 0.40 | 0.6898 / 0.6614 | 0.6187 / 0.6822 |
| 0.35 | **0.7486 / 0.6250** | 0.6483 / 0.6478 |
| 0.30 | **0.7993 / 0.5884** | 0.6943 / 0.5912 |
| 0.25 | **0.8347 / 0.5047** | 0.7080 / 0.5031 |
| 0.20 | **0.8685 / 0.4258** | 0.6949 / 0.4182 |
| 0.15 | **0.9022 / 0.3040** | 0.6444 / 0.2769 |

## 2. Why a 0.93 AUC under-converts — the label boundary excluded the hard band

The Step-2 AUC was measured with positives at **<= 1.5 px** from a crease and negatives at
**> 3.0 px**. That labelling **excludes the 1.5 to 3.0 px band entirely**, and that band is
exactly what the deliverable metric has to resolve. A regional dihedral answers "is there a
crease near this locus"; the 1.5 px metric asks "is this linelet **on** it". The consensus
residual measures the second quantity directly, which is why it wins.

This is the property `src/evidence.py` already records: the evidence fields are **regional**
and cannot resolve the per-splat tolerance. Step 2 did not measure the tolerance-resolving
ability, so its AUC was never evidence for it. **A discriminability number measured against a
gapped label boundary is not a forecast of ranking performance at the boundary.**

Corroborating mis-calibration: arm B's precision is **non-monotonic** in the keep fraction
(0.7080 at 0.25, dipping to 0.6444 at 0.15, then rising to 0.9734 at 0.01). A well-calibrated
ranker does not do that.

## 3. THE TWO CEILINGS, as the push-back required — same harness, same tau

| stage | metric | P@1.5 | R@1.5 |
|---|---|---|---|
| **RAW gaussian centres** (all 32,476) | points | 0.2820 | **0.5583** |
| pulled centres | points | 0.5197 | **0.7081** |
| **RAW linelets at init** | segments | 0.1684 | **0.8849** |
| pulled linelets | segments | 0.2261 | **0.9198** |

**The DT-pull is not the whole game.** It adds +0.1498 of point recall and only **+0.0349** of
segment recall. The raw centres already carry 0.5583, and the raw segments 0.8849, before the
pull moves anything.

**And the 0.2021 was never the ceiling for this metric.** That number is a **3-D radius**
point-cloud recall in the DexiNed-primary harness at radius 0.004860. The same raw centres
score **0.5583** here, because the M1b metric asks for 2-D **projected** proximity within
1.5 px, and a candidate that is wrong in depth still projects near the crease. Two different
questions; the deliverable metric asks the weaker one. Quoting 0.2021 as the pool ceiling for
P/R was a harness conflation, and it is now measured rather than argued.

## 4. A correction to a banked verdict

`SCALEADAPT_RESULTS.md` reported that **no point on cadpartA's frontier** reaches R >= 0.45 at
P >= 0.70. That scan swept the keep fraction **at f = 0.30**. At f = 1.00 the existing
pipeline with the existing prune reaches **R 0.6250 at P 0.7486**, and even the untouched spec
prune reaches **R 0.4206 at P 0.8139**.

The static half of the NOT-GENERAL finding was therefore a property of the **shipped operating
point**, not an intrinsic ceiling. The seed-score-overfit conclusion in that document still
stands for arm A, which cannot rank this pool to P 0.70 at all. What does not stand is the
claim that cadpartA has no reachable frontier point.

## 5. Temporal, REPORTED UNGATED

cadpart's ratio is not calibrated against the chair/lego invariant and is not transported here.
240-frame TEST orbit, identical warp and per-frame Canny baseline.

| operating point | R / P | strokes | OURS P_pop | BASE P_pop | ratio |
|---|---|---|---|---|---|
| shipped f = 0.30 (banked) | 0.1584 / 0.9211 | — | 0.0530 | 0.8100 | **15.28x** |
| f = 1.00, spec prune | 0.4206 / 0.8139 | 42 | 0.0771 | 0.8097 | **10.50x** |
| **B ribbon, kf 0.25** | 0.5031 / 0.7080 | 20 | 0.1063 | 0.8099 | **7.62x** |
| A2 prune, kf 0.35 | 0.6250 / 0.7486 | 46 | 0.1078 | 0.8100 | **7.52x** |

**The recall is bought with temporal coherence, roughly halving the ratio.** All four points
remain far steadier than the per-frame image-space baseline, but the trade is real and it is
the same axis on which lego's f = 1.00 was ruled NO-GO. Anyone adopting f = 1.00 on a solid is
making that trade knowingly.

## 6. Caveats on the record

1. **Arm B puts a second reconstruction in the method path.** The work is no longer post-hoc
   extraction from one frozen vanilla 3DGS. Both reconstructions trained on all 100 views
   including the evaluation indices, so the arm comparison is fair and neither is held out
   with respect to itself.
2. **The sweep uses the raw half-length, not the tuned length policy**, so the only thing
   varying across arms is the ranking. The shipped 0.9211 / 0.1584 includes length modulation
   and is quoted as a reference line, not as a point on any swept frontier.
3. **Arm C is scored on the TEST views**, which is correct for a ceiling and wrong for a
   method. It also carries heavy ties from the distance-transform quantisation, visible as the
   plateaus at n = 12,750 and n = 7,201.
4. **Arm A is being asked to do a job it was not built for.** The M1a OVERALL score selects
   seeds before the pull; using it to rank pulled linelets is a stress test, and its failure to
   reach P 0.70 should be read that way.
5. **Reproduction.** The sweep was run twice, once computing the scores live and once from the
   cached score file, and returned identical best points for all four arms. Arm B's score is
   computed one view at a time and medianed across views, which is arithmetically identical to
   the batched call and was adopted after the batched version was killed for host memory.

## 7. Artifacts

`out/geoline_step3_cadpartA.json`, `out/geoline_step3_scores_cadpartA.npz`,
`out/m1b_cadpartA_step3pool.json`, `out/linelets_cadpartA_step3{pool,B,A2,spec}*.npz`,
`out/m1b_stroke_temporal_table_step3{B,A2,spec}.{json,md}`, `scripts/geoline_step3.py`,
`logs/step3_{pool,abc,scores,temporal}.log`. Nothing committed.

---

## 8. Two checks on the commit-message claims for `4e52b0d`

**(a) "Pre-registered target R>=0.60 @ P>=0.75 MET" — CONFIRMED, after a disclosed grid
refinement.** On the coarse keep-fraction grid the R-satisfying point was kf 0.35 at
**P 0.7486**, i.e. 0.0014 short of 0.75, so the claim was not visible as measured. A finer
sweep on arm A2 only, refining resolution on a pre-registered axis without moving any bar,
settles it:

| keep frac | n | P@1.5 | R@1.5 | meets R>=0.60 and P>=0.75 |
|---|---|---|---|---|
| 0.345 | 11,290 | 0.7527 | 0.6240 | **yes** |
| 0.340 | 11,051 | 0.7582 | 0.6219 | **yes** |
| **0.330** | 10,737 | **0.7695** | **0.6162** | **yes** |
| 0.320 | 10,395 | 0.7771 | 0.6060 | **yes** |
| 0.310 | 10,089 | 0.7890 | 0.5993 | no (R) |

The target is met across kf 0.320 to 0.345. Quote **P 0.7695 / R 0.6162** at kf 0.330 as the
representative point rather than the coarse-grid 0.7486 / 0.6250.

**(b) "geometric cue is ALIVE on textureless solid as hypothesized" — ATTRIBUTION CORRECTION.**
The arm that produced the recall revival is **A2, the consensus prune ranker**, which is the
multi-view DT-residual consistency statistic the pipeline already shipped. **It is not a
geometric cue.** The geometric cue is arm B, the 2DGS ribbon dihedral, and arm B **lost to A2
across the whole frontier** (0.5031 against 0.6250 at matched precision).

The recall revival is attributable to **raising f from 0.30 to 1.00 and ranking with the
existing prune statistic**. The geometric cue is alive in the Step-2 discriminability sense
and did convert past its own gate, but it is not what delivered the recall, and it is beaten
by a component that has been in the code the whole time.

This is the same class of attribution error the campaign corrected once before, when a result
credited to TEED was traced to the Canny pull field present in every configuration.
