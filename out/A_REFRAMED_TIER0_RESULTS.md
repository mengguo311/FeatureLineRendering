# A-REFRAMED TIER-0 — does a junction response add band selectivity over the rank we already use?

**VERDICT: NO-GO — and the mechanism is real.** The junction channel genuinely separates
lego's brick geometry from its stud tessellation at **AUC 0.705**, far above chance. But the
**TEED seed score we already rank with separates them better, at AUC 0.727.** The junction
signal is dominated by the existing evidence, margin **−0.022** against a required **+0.05**.

The mechanistic prediction was right; the channel is redundant.

Diagnostic only — selects nothing, builds nothing. Run on **VAL** views so TEST stays
untouched. Mesh EVAL-ONLY (banked crease points + banked per-point dihedral). No pull.
Banked TEED maps. Manifest **332/332 OK**. Not committed.

---

## 1. What was tested, and why it is not the candidate you proposed

The original candidate A — "a corner channel aimed at the 90-degree family because it is the
largest recoverable block at 24.85% of the miss-set with recall 0.229" — was refuted by E-BAND
(that band is 0.1505 of the miss-set, realised R **0.7983** against a global 0.6744, culled mass
0.0938). This run tests the **reframed** hypothesis, which is stronger and was untested:

> Stud barrels are 12-gon tessellations of a smooth cylinder, so their facet edges run parallel
> along the barrel with **no junctions**. Brick geometry is junction-dense. A junction response
> should therefore discriminate the two families.

Carrier labelling is 3D and view-independent: nearest GT crease point within one carrier NN
spacing (**0.005865**), then that point's banked dihedral.

| population | n |
|---|---|
| carriers within one spacing of a crease | 25,075 |
| **band90** (theta ∈ [89.95, 90.05)) — brick geometry | **4,768** |
| **band30** (theta ∈ [30.00, 30.05)) — stud tessellation | **11,651** |

Junction response is the structure tensor of the banked TEED map (sigma 2.0): the **small
eigenvalue** lambda2 as primary, where two orientations coexist, and the Harris response as a
declared sensitivity arm. Both are aggregated as the occlusion-aware mean over visible VAL
views using the frozen-3DGS z-buffer.

## 2. Result

Positive class = band90 (brick), negative = band30 (tessellation).

| channel | AUC | |
|---|---|---|
| **lam2** (junction, primary) | **0.7053** | mechanism confirmed |
| harris (sensitivity) | 0.6686 | mechanism confirmed, weaker |
| teed raw probability (control) | 0.6058 | |
| **teed_seedscore** (the rank we actually use) | **0.7271** | **best** |

Frozen bar: GO requires AUC(J) ≥ 0.65 **and** margin over the best control ≥ +0.05.

| | value |
|---|---|
| best J | 0.7053 |
| best control | 0.7271 |
| **margin** | **−0.0219** |
| **VERDICT** | **NO-GO** |

The AUC leg passes. The margin leg fails, and fails in the wrong direction: the junction
channel is not merely insufficient, it is **worse than the ranking signal already in the
pipeline**.

## 3. The finding worth keeping

**The physical hypothesis is confirmed.** A junction response separates lego's brick geometry
from its tessellation at 0.705 — the stud barrels really are junction-free by construction and
this is measurable from the banked edge maps alone.

**And it is already priced in.** The M1a TEED seed score reaches 0.727 on the same task without
being designed for it. Whatever band selectivity a junction detector offers, our existing
evidence channel has more of it.

This is the **third** instance of one pattern in Phase B:

| candidate | mechanism real? | beat the existing rank? |
|---|---|---|
| detector union | — | no: union 0.6429/0.4424 < TEED alone 0.6535/0.4463 |
| agreement-rank (min-of-percentile) | yes, channels non-redundant at 0.71–0.81 overlap | no: conjunction inherits the weakest channel |
| **junction rank** | **yes, AUC 0.705** | **no: 0.705 < 0.727** |

**The generalisation: TEED's ranking already encodes the structure these channels were built to
add. Adding a channel that correlates with band identity is redundant, not additive.** That is
now measured three independent ways and is the cleanest statement of why the rank lever is
exhausted on lego.

## 4. Actionability, stated before the run and unchanged by it

Even a PASS here would have been unactionable under the frozen theta=30 oracle. Tessellation
edges are **inside** the GT crease set, so suppressing them lowers measured recall *and*
precision; the payoff only appears under a theta ≥ 30.05 re-score, where the threshold audit
already measured precision collapsing **0.6360 → 0.3097** and concluded the change "is not an
improvement." The NO-GO therefore costs us nothing we could have spent.

## 5. Invariants

VAL views only — TEST untouched. Mesh EVAL-ONLY via banked caches. No pull, no stroke set
touched, no shipped json or figure modified. One G-buffer pass per VAL view. New artifacts:
`scripts/a_reframed_tier0.py`, `out/a_reframed_tier0.json`, `logs/a_reframed.log`, this file.
Not committed.
