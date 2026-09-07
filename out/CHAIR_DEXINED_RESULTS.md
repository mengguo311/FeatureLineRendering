# CHAIR DexiNed — the correctly-aimed precision instrument, measured

**VERDICT: NO-GO.** The pre-registered GO was a conjunction: temporal ratio >= 10.345x **AND**
seed P beats chair TEED at matched f. The temporal leg **passes with the best ratio we have
ever measured on chair (13.41x)**. The precision leg **fails decisively** — DexiNed's seed
precision is 0.070 *below* TEED's, not above it.

**This kills my own recommendation from the previous round.** I argued DexiNed was the
"correctly-aimed precision instrument for chair" on the strength of its precision edge on
lego. That edge does not transfer. On chair DexiNed is the *worst* of the three arms on
precision. I was wrong, and the pre-registration caught it.

Same harness as VERIFY_F100 / Phase A: chair, gate=True, edge=sharp, spec mask for temporal,
tuned+len for static, 240-frame TEST orbit 5->15, identical warp and Canny baseline, fresh
tags. Mesh EVAL-ONLY. Manifest **332/332 OK**. Not committed.

---

## 1. The table

Temporal is newly computed on the spec mask. Static tuned+len is banked. Seed P/R is newly
computed with the M1a harness on held-out TEST views, reported at our 1.5 px convention and at
the harness's own M1a default.

| arm | lin | chains | str/f | unmatched | cut | P_pop | Frechet x | **P_pop x** | tuned P | tuned R | **seedP@1.5** | seedR@1.5 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| canny f=0.30 (gate-matched control) | 16,039 | 1,166 | 754 | 0.0238 | 0.0467 | 0.07052 | 30.84x | 10.71x | **0.6573** | 0.5959 | — | — |
| **TEED f=0.30** (Phase A chair point) | 15,971 | 1,137 | 723 | 0.0301 | 0.0274 | 0.05754 | 28.36x | 13.12x | 0.6417 | 0.6759 | **0.6485** | 0.6438 |
| **DexiNed 0.5 f=0.30** | 15,500 | 1,101 | 711 | 0.0343 | **0.0220** | **0.05632** | 27.92x | **13.41x** | 0.5988 | 0.6778 | **0.5786** | 0.6431 |
| DexiNed 0.7 f=0.30 | 15,456 | 1,056 | 677 | 0.0352 | 0.0215 | 0.05672 | 27.38x | 13.32x | 0.6116 | 0.6831 | 0.5945 | 0.6513 |

Seed P at the M1a default tolerance tells the same story: TEED **0.7697**, DexiNed 0.5
**0.6977**, DexiNed 0.7 **0.7152**. The verdict does not depend on the tolerance.

**BASE self-check (free).** The Canny baseline is linelet-independent and re-derived in every
arm: Frechet 1.22472–1.22635, P_pop 0.75512–0.75530, against the shipped chair 1.2252 /
0.75512. All four arms are on one measuring stick.

## 2. Verdict against the frozen rule

| leg | condition | measured | |
|---|---|---|---|
| temporal | P_pop ratio >= 10.345x | **13.41x** | **PASS** |
| precision | seed P beats chair TEED at matched f | **0.5786 vs 0.6485** | **FAIL** |

Conjunction ⇒ **NO-GO**. DexiNed 0.7, the stronger variant, also fails (0.5945 vs 0.6485).

Recall is not the compensator: seed recall is a tie (0.6431 / 0.6513 against TEED's 0.6438).
DexiNed buys temporal stability and pays precision, at flat recall. On the scene whose binding
constraint is precision, that is the wrong trade, and it is why the criterion was written this
way before the numbers existed.

## 3. Two inversions worth recording

**The precision edge is scene-specific and does not transfer.**

| detector, f=0.40 lego / f=0.30 chair | lego tuned P | chair tuned P |
|---|---|---|
| TEED | 0.6535 | **0.6417** |
| DexiNed 0.5 | **0.6594** | 0.5988 |

DexiNed wins precision on lego by 0.006 and loses it on chair by 0.043. This is the same
non-transfer pattern the project has already recorded in the other direction — the
chair-optimal seed score reads below chance on lego at carrier level (AUC 0.446).

**Fragmentation behaviour also flips by scene.** DexiNed's `cut` is 0.0290 on lego against
TEED's 0.0225 (fragments **more**), and 0.0220 on chair against TEED's 0.0274 (fragments
**less**). That inversion is why DexiNed posts chair's best temporal ratio while posting a
worse one on lego.

The general lesson, now on two independent axes: **detector-scene interaction dominates, and
nothing about a detector's ranking behaviour transfers between these two objects.**

## 4. What survives

Chair's standing point remains **TEED f=0.30**: tuned P 0.6417 / R 0.6759 at 13.12x, which
beats the shipped canny point on recall (+0.080) and temporal (10.71x -> 13.12x) for a
precision cost of 0.0156, inside the 0.02 allowance.

DexiNed's 13.41x is the best chair temporal number on record and is banked for reference, but
it is not adoptable: it costs 0.070 of seed precision on the scene where the paper's
Contribution B *is* the precision boundary.

## 5. Invariants

Manifest **332/332 OK, 0 FAILED**. Shipped jsons and published vector figures untouched (both
arms used non-empty `--viz_tag`). Mesh EVAL-ONLY. New artifacts:
`m1b_stroke_temporal_table_cdx_{dex030,dex07030}.{json,md}`,
`m1b_vector_chair_cdx{050,070}_*.{svg,png}`,
`linelets_chair_{dex030,dex07030}_test.npz` (symlinks), `out/chair_dexined_seedpr.json`,
`logs/chair_dexined.log`, this file. Not committed.
