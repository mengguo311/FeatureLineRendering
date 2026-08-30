# Plan #1-hybrid — vanilla-seed x 2DGS-gate: results

Chair, NeRF-synthetic. Split frozen as `src/view_split.py` (TRAIN 80 / VAL {0,10,..,90} /
TEST {5,15,..,95}). The 2DGS models are reused, not retrained. Mesh is EVAL-ONLY throughout:
`grep -rn "mesh_oracle\|trimesh" src/*.py` finds it only in `mesh_oracle.py` itself and in
docstrings. Nothing committed to git.

New code: `src/hybrid_gate.py` (METHOD PATH, mesh-free),
`scripts/hybrid_step1_align.py`, `scripts/hybrid_step1c_frontier.py`,
`scripts/run_hybrid.py`, `scripts/hybrid_step2_sweep.sh`,
`scripts/hybrid_step2_table.py`, `scripts/hybrid_step2_redundancy.py`,
`scripts/hybrid_step2_rerank.py`.

---

## Executive summary

The hybrid's premise is **confirmed**; its mechanism is **refuted**.

- The 2DGS channel really does carry crease/fabric information the vanilla M1a score does
  not: **+0.043 seed precision above the ungated f-frontier on VAL, +0.026 on held-out
  TEST**, at matched recall. That is 43% of the GT-mesh ceiling and 2.2x what the vanilla
  representation can do gating itself.
- The spec's KEY RISK — that the two surfaces are too misaligned at creases to query
  across — is **falsified**, not confirmed. Dilation never pays for itself (gain/cost
  <= 1.03 at the first pixel, 0.05-0.26 after), so the optimal radius is r=0, i.e. the
  surfaces co-register at seed reprojections to within <~1 px.
- Spending that information as a **hard seed veto** converts none of it into better feature
  lines: 14 of 15 arms land BELOW the ungated f-frontier end-to-end. At matched recall the
  hybrid reaches seg P@1.5 0.6980 where **simply lowering f to 0.15 reaches 0.7057**, with
  no 2DGS model at all.
- Mechanism, measured: the vetoed linelets do draw worse (P@1.5 0.573 vs 0.669) but they
  carry **81.6% of the drawn TEST recall**. Seed precision is not the binding quantity for
  the M1b deliverable; seed COVERAGE is.

---

## STEP 1 — alignment pre-test

17065 vanilla M1a OVERALL seeds (f=0.30), VAL views only, 2DGS buffers resampled with the
calibrated -0.5 px shift (`render2dgs.half_pixel`). Two control arms were added beyond the
spec, and they are what make the verdict readable:
`vanilla` (the same gate on the seeds' OWN representation -- a floor with zero
cross-representation misalignment) and `mesh` (GT geometry -- the ceiling).

Subset = STEP-A refined (GT-flat printed fabric vs genuinely sharp crease, `FLAT_DEG` 5 /
`SHARP_DEG` 20; 42450 crease / 8304 fabric observations):

| arm / signal | metric | r=0 | r=1 | r=2 | r=3 | r=5 | r=8 |
|---|---|---|---|---|---|---|---|
| 2dgs_chair / dihedral tau=8 | R_crease | 0.898 | 0.931 | 0.945 | 0.957 | 0.970 | 0.978 |
| | FPR_fabric | 0.332 | 0.427 | 0.513 | 0.606 | 0.752 | 0.884 |
| **2dgs_chair / \|\|grad N\|\| q90** | R_crease | 0.814 | 0.922 | 0.948 | 0.961 | 0.970 | 0.977 |
| | FPR_fabric | **0.232** | 0.337 | 0.435 | 0.535 | 0.710 | 0.862 |
| 2dgs_chair_dist / dihedral tau=8 | R_crease | 0.703 | 0.740 | 0.758 | 0.773 | 0.793 | 0.809 |
| | FPR_fabric | 0.228 | 0.308 | 0.380 | 0.446 | 0.556 | 0.680 |
| 2dgs_chair_dist / \|\|grad N\|\| q90 | R_crease | 0.703 | 0.787 | 0.812 | 0.828 | 0.851 | 0.873 |
| | FPR_fabric | 0.192 | 0.286 | 0.381 | 0.463 | 0.594 | 0.725 |
| *vanilla self-gate* / dihedral tau=8 | R_crease | 0.977 | 0.988 | 0.993 | 0.996 | 0.999 | 1.000 |
| | FPR_fabric | 0.746 | 0.822 | 0.873 | 0.922 | 0.975 | 0.998 |

Raw-signal AUC (crease vs fabric at seed reprojections), refined subset:
`2dgs_chair`/gradn **0.856** > `vanilla`/gradn 0.814 > `2dgs_chair_dist`/gradn 0.795.
On the unrestricted `all`/`interior` subsets the ordering INVERTS (vanilla 0.729 > 2dgs
0.681) -- vanilla's geometry is texture-baked, so it "predicts" the crease label by
reproducing the very photometric edges the M1a seed recipe already consumed. The refined
subset is the honest comparison, and there 2DGS wins.

### VERDICT: NO-GO by the letter of the rule; the KEY RISK is falsified

No r reaches `R_crease >= 0.80 AND FPR_fabric <= 0.15`, on any subset, for either 2DGS
model. **STEP 1b (3D nearest-surfel dihedral) is also NO-GO and strictly worse** --
theta_max AUC 0.51-0.55 on all/interior (0.63 refined at best), best point R=0.884 /
FPR=0.759. Projection immunity buys nothing, which is itself evidence that projection was
never the problem.

Three controls say the literal NO-GO carries no information about co-registration:

1. **The GT mesh fails the same rule.** Ceiling arm on all/interior: best is
   R=0.977 / FPR=0.597 (dihedral tau=20, r=0); forcing FPR to 0.113 collapses recall to
   0.253. This is the failure mode `PLAN1_RESULTS.md` already recorded -- the FABRIC class
   ("no GT crease within 3 px") contains real non-flat geometry (legs, ornaments, interior
   self-occlusions, sub-30-deg folds), so `FPR_fabric <= 0.15` is unreachable by PERFECT
   geometry. On the `refined` subset the mesh arm reads R=1.000 / FPR=0.000, but that is
   circular -- the subset is defined by the mesh's own dihedral -- so it is a
   well-formedness check, not a ceiling.
2. **Dilation is net-harmful.** Marginal dR/dFPR per +1 px, refined subset:

   | gate | r 0->1 | 1->2 | 2->3 | 3->5 | 5->8 |
   |---|---|---|---|---|---|
   | 2dgs_chair / dihedral tau=8 | 0.35 | 0.17 | 0.12 | 0.09 | 0.06 |
   | 2dgs_chair / gradn q90 | 1.03 | 0.26 | 0.13 | 0.05 | 0.05 |

   If facet-sampling misalignment were binding, R_crease would jump with r while
   FPR_fabric stayed flat. It does the opposite. **The two representations co-register at
   the seed reprojections to within <~1 px.**
3. **The -0.5 px shift is real but small**, consistent with (2): disabling it moves
   R_crease by only -0.02..-0.03 at r=0, in the same direction as a threshold change
   (FPR moves with it), not as a systematic misregistration.

What actually binds is FPR_fabric: even on GT-verified-flat printed fabric the best 2DGS
gate fires on 23% of fabric seeds at R=0.81. A partial filter, exactly as STEP B found for
the edge-pixel gate (51.8% survive at purity 0.411).

### STEP 1c — the gate DOES carry orthogonal information

A gate that removes seeds always trades recall for precision, and the M1a score already
offers that trade free by lowering f. So each gated seed set is scored against the ungated
f-frontier interpolated to the SAME recall (`scripts/hybrid_step1c_frontier.py`, literal
M1a harness protocol, VAL):

| gate | n_seeds | seed P | seed R | frontier P at same R | LIFT |
|---|---|---|---|---|---|
| ungated f=0.30 | 9440 | 0.6555 | 0.7669 | -- | -- |
| **2dgs_chair gradn q90, r=0, vote 0.75** | 10466 | 0.7585 | 0.6441 | 0.7152 | **+0.0433** |
| 2dgs_chair dihedral tau=8, r=0, vote 0.75 | 13421 | 0.7264 | 0.6809 | 0.7029 | +0.0235 |
| 2dgs_chair_dist gradn q95, r=1, vote 0.5 | 11582 | 0.7496 | 0.6614 | 0.7094 | +0.0402 |
| *vanilla self-gate*, best at R>=0.60 | 12915 | 0.7408 | 0.6253 | 0.7209 | +0.0199 |
| *GT-mesh ceiling*, best at R>=0.60 | 11998 | 0.8040 | 0.6770 | 0.7042 | +0.0998 |

**Chosen gate: 2D region gate, r=0, `out/2dgs_chair`, `||grad N||_F` at q90, vote 0.75.**
Dilation is deliberately NOT used. `out/2dgs_chair_dist` (the model the spec names) is
consistently the worse of the two, matching `PLAN1_RESULTS.md`'s finding that
`lambda_dist=1000` over-flattens creases.

---

## STEP 2 — end-to-end

Every arm runs the IDENTICAL code path (`scripts/run_hybrid.py`); the only difference
between an ungated f-arm and a gated arm is the seed set. Baseline reproduced exactly.

| arm | n_seed | n_kept | seg P@1.5 | seg R@1.5 | seg P@2.5 | seg R@2.5 | LIFT vs f-ctl |
|---|---|---|---|---|---|---|---|
| **BASELINE vanilla M1b f=0.30** | 17065 | 15091 | 0.6573 | 0.5959 | 0.7777 | 0.6719 | -- |
| f-CONTROL f=0.15 | 8533 | 8094 | **0.7057** | 0.4678 | 0.8286 | 0.5399 | -- |
| f-CONTROL f=0.18 | 10239 | 9595 | 0.6989 | 0.4971 | 0.8213 | 0.5701 | -- |
| f-CONTROL f=0.22 | 12514 | 11548 | 0.6877 | 0.5333 | 0.8084 | 0.6070 | -- |
| f-CONTROL f=0.26 | 14790 | 13351 | 0.6726 | 0.5667 | 0.7932 | 0.6430 | -- |
| **HYBRID gradn q90 r0 vote0.75** | 10117 | 9804 | 0.6980 | 0.4684 | 0.8180 | 0.5371 | **-0.0076** |
| HYBRID gradn q90 r0 vote0.25 | 16402 | 14678 | 0.6620 | 0.5877 | 0.7817 | 0.6625 | +0.0004 |
| HYBRID gradn q90 r0 vote0.5 | 14403 | 13384 | 0.6707 | 0.5424 | 0.7909 | 0.6150 | -0.0130 |
| HYBRID gradn q80 r0 vote0.75 | 15767 | 14439 | 0.6675 | 0.5729 | 0.7875 | 0.6471 | -0.0018 |
| HYBRID gradn q95 r1 vote0.5 | 11357 | 10793 | 0.6727 | 0.4995 | 0.7945 | 0.5773 | -0.0255 |
| HYBRID dihedral tau=8 r0 vote0.5 | 15879 | 14347 | 0.6587 | 0.5704 | 0.7792 | 0.6456 | -0.0119 |
| HYBRID dihedral tau=8 r0 vote0.75 | 13932 | 13065 | 0.6672 | 0.5315 | 0.7870 | 0.6006 | -0.0211 |
| HYBRID `_dist` gradn q90 r0 vote0.5 | 13859 | 12900 | 0.6710 | 0.5341 | 0.7903 | 0.6071 | -0.0163 |
| HYBRID `_dist` gradn q95 r1 vote0.5 | 11249 | 10623 | 0.6651 | 0.4998 | 0.7860 | 0.5760 | -0.0330 |
| HYBRID gate-as-reranker f=0.42 | 12233 | 11683 | 0.6426 | 0.5135 | 0.7568 | 0.5910 | -0.0515 |
| HYBRID gate-as-reranker f=0.50 | 13250 | 12555 | 0.6118 | 0.5389 | 0.7211 | 0.6198 | -0.0734 |
| HYBRID gate-as-reranker f=0.60 | 14421 | 13480 | 0.5740 | 0.5468 | 0.6782 | 0.6278 | -0.1076 |

**14 of 15 arms are below the ungated f-frontier; the exception is +0.0004.** Same
conclusion on the spec prune rule without length modulation (-0.004 to -0.108). The
end-to-end gate `P@1.5>=0.85 AND R@1.5>=0.75` **FAILS** for every arm, as it does for the
baseline (0.6573 / 0.5959).

The cleanest statement needs no interpolation at all -- compare at MATCHED SEED COUNT:

| | n_seed | n_kept | seg P@1.5 | seg R@1.5 |
|---|---|---|---|---|
| HYBRID gradn q90 r0 vote0.75 | 10117 | 9804 | 0.6980 | 0.4684 |
| f-CONTROL f=0.18 (no 2DGS at all) | 10239 | 9595 | **0.6989** | **0.4971** |

The f-control uses 1% MORE seeds, keeps 2% FEWER linelets after pruning, and still wins on
BOTH axes: equal precision (+0.0009) and +0.029 recall. The hybrid is strictly dominated by
the M1a score's own keep-fraction dial.

### Why: the seed-level gain is real, and it dies in the pull->prune->segment stage

The seed-level lift REPLICATES on held-out TEST, so this is not VAL overfitting
(points protocol, BEFORE the pull, scored against the TEST f-frontier):

| stage | metric | LIFT of the chosen gate |
|---|---|---|
| seeds, VAL | harness points P/R | **+0.0433** |
| seeds, TEST | harness points P/R | **+0.0262** |
| drawn segments, TEST | seg P@1.5 / R@1.5 | **-0.0076** |

`scripts/hybrid_step2_redundancy.py` splits the IDENTICAL baseline linelets by the gate's
verdict (no re-pull, no re-prune, no confound):

| group | n | seg P@1.5 | seg R@1.5 | drawn px/view |
|---|---|---|---|---|
| baseline (prune keep) | 16039 | 0.6067 | 0.7077 | 19324 |
| gate KEEPS | 9981 | **0.6692** | 0.5115 | 11343 |
| gate VETOES | 6058 | **0.5728** | 0.5776 | 12623 |

- The veto is genuinely selective (0.5728 vs 0.6692).
- It is NOT redundant with the consensus prune: P(prune drops) = 0.060 vs
  P(prune drops | gate drops) = 0.128.
- It is NOT a proxy for the M1a score: AUC(M1a score predicts gate verdict) = 0.633.
- **But the vetoed set carries 0.5776 of the 0.7077 total drawn recall = 81.6%.**
  Neighbouring linelets cover the same GT crease pixels, so deleting a seed costs far more
  recall than its precision deficit is worth.

**Seed precision is not the binding quantity for the M1b deliverable; seed coverage is.**
That is the transferable finding, and it explains why an orthogonal, texture-blind,
GT-validated signal can still be worth nothing when spent as a seed veto.

### STEP 2b — spending it at the prune instead (beyond the literal spec)

The spec's own framing is "2DGS = WHICH survive", and survival is decided by the consensus
prune. So `s = rank01(consensus_statistic) + w * rank01(2dgs_support_fraction)`, with the
support fraction used continuously instead of thresholded (`scripts/hybrid_step2_rerank.py`;
w=0 reproduces the published baseline prune frontier exactly).

| | vs the w=0 prune frontier | vs the global ungated f-frontier |
|---|---|---|
| points above | 20 / 25 | 1 / 26 |
| best LIFT | **+0.0146** (w=2.0, keep=0.7) | +0.0068 (w=2.0, keep=0.5) |

So the 2DGS term IS a better prune ranker than pure multi-view consensus -- a real, if
small, win. It does not close the gap to the f dial, because the whole prune frontier at
f=0.30 sits ~0.018 below the f-frontier: **lowering f is a better precision/recall dial
than pruning harder, and better than any use of the 2DGS gate tested here.**

---

## Where this leaves the hybrid

The orthogonality premise that motivated the plan is now measured and true: 2DGS geometry
is texture-blind where vanilla is not, it separates GT-flat print from GT-sharp crease at
the seeds (AUC 0.856 vs vanilla's 0.814 on the same subset), it co-registers with vanilla to
within a pixel, and it buys seed precision the M1a score cannot -- on held-out TEST.

What is refuted is that this converts into better feature lines through a seed gate. The
M1b deliverable is scored on drawn segments, where recall is bought by coverage and a
seed's neighbours substitute for it; a filter that improves per-seed precision by 0.026
while deleting 41% of the seeds is dominated by simply asking the M1a score for fewer seeds.

If the channel is to be used, the measured evidence points at the prune (+0.0146 over pure
consensus ranking) rather than the seed set -- and at a formulation that does not spend
coverage: a soft weight on the DT target or on drawn length, not a deletion.

---

## STEP 2 — temporal no-regress

`scripts/m1b_stroke_temporal.py`, chair, held-out TEST trajectory 5->15, look-at-corrected
orbit. Both variants re-run here with identical settings, so the comparison is matched; the
published column is `out/m1b_stroke_temporal_table.md`. OURS = object-space carrier,
BASE = naive image-space Canny re-traced every frame.

| frames | BASELINE Frechet / P_pop | ratios (Fr / Pp) | HYBRID Frechet / P_pop | ratios (Fr / Pp) | published ratios |
|---|---|---|---|---|---|
| 30 | 0.322 / 0.096 | 4.30x / 8.21x | 0.280 / 0.103 | **4.92x** / 7.66x | 4.19x / 8.52x |
| 60 | 0.160 / 0.079 | 8.09x / 9.75x | 0.139 / 0.090 | **9.31x** / 8.56x | 7.87x / 10.17x |
| 120 | 0.080 / 0.072 | 15.65x / 10.50x | 0.069 / 0.084 | **18.17x** / 9.00x | 15.22x / 11.11x |
| 240 | 0.040 / 0.071 | 30.62x / 10.63x | 0.035 / 0.084 | **35.00x** / 8.99x | 29.92x / 11.35x |

The baseline reproduces the published table (0.322/0.160/0.080/0.040 vs 0.330/0.164/0.082/
0.041), so the harness is sound.

**Split verdict.**
- **Frechet residual IMPROVES** under the hybrid at every trajectory length (+13..+15% on
  the ratio): the surviving carriers are the better-localised ones, so what is still drawn
  tracks more exactly. The object-space coherence headline is intact.
- **P_pop REGRESSES** ~15%: 8.99-9.31x where the baseline gets 8.99-10.63x. It stays inside
  the quoted 7-11x band, but it is consistently BELOW the matched baseline, so this is not
  a clean no-regress.
- Cause is structural and measured: deleting 41% of the seeds fragments the chains --
  16039 -> 9967 linelets, NMS 8508 -> 5910, strokes 1166 -> 810, strokes/frame 754 -> 600,
  and the topological **cut rate rises 0.047 -> 0.071**. Sparser seeds mean chaining bridges
  fewer gaps, so strokes split and merge more across frames. This is the same mechanism
  `PLAN1_RESULTS.md` recorded for its own P_pop regression, arriving from the opposite
  direction (there: more, shorter strokes; here: fewer, more-often-cut strokes).

So the hybrid neither preserves nor destroys the temporal result: it trades ~15% of the
popping margin for ~15% better path fidelity, while losing 0.13 of segment recall. Given
that the precision it buys is already available for free from the f dial, there is no
operating point at which that trade is worth taking.
