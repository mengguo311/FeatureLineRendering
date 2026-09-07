# PB1b TIER-0 — cross-detector AGREEMENT-RANK rank-overlap screen

**VERDICT: lego primary arm PASSES tier-0 by 303 seeds out of 39,888; chair primary arm
FAILS by 108 out of 17,065; both sensitivity arms FAIL on both scenes.** Per the frozen
rule a tier-0 pass **buys only the right to spend tier-1 minutes and cannot greenlight a
pull**. So lego has earned a tier-1 seed-P/R LIFT test and nothing more; chair is closed.

The free finding matters more than the verdict: **the conjunctive operator is dominated by
the WEAKEST detector.** On both scenes the agreement set is closer to PiDiNet's selection
than to TEED's. That is a direction, and it points the wrong way.

No mesh, no GPU, no pull. Pure function of three banked seed-score vectors.
Script `scripts/pb1b_tier0.py`, raw `out/pb1b_tier0.json`.

---

## 1. Pre-registration, as frozen

**Operator (variant space capped at two, by design):** percentile-normalise each detector
score to [0,1], then elementwise **minimum**. **Geometric mean** is the single declared
sensitivity arm. A two-channel min (TEED+DexiNed, dropping the weak member) is reported as a
third arm. Nothing else, ever.

**Bar (necessary, NOT sufficient):** with `O_ref` = overlap(TEED top-k, DexiNed top-k) — a
channel swap already measured end-to-end as neutral-to-worse — PASS iff
`O(TEED, AGREE) <= O_ref`. Rationale: if agreement perturbs TEED *less* than a swap we know is
not worth taking, it cannot produce a materially different pipeline outcome.

**Orchestrator amendment, accepted and frozen before the run:** a tier-0 pass proves only that
the set *moves*, not that it moves in the right direction. It may not greenlight. Tier-1
seed-P/R LIFT is the real gate.

Operating points: lego f=0.40 (pool 99,721, k=39,888); chair f=0.30 (pool 56,884, k=17,065).
Both reproduce the banked seed counts exactly.

## 2. The verdict table

| scene | arm | O(TEED, arm) | O_ref | margin | tier-0 |
|---|---|---|---|---|---|
| **lego** | **AGREE_min3** (primary) | **0.7992** | 0.8068 | **-0.0076** | **PASS** |
| lego | AGREE_geo3 (sensitivity) | 0.8471 | 0.8068 | +0.0403 | FAIL |
| lego | AGREE_min2 (TEED+DexiNed) | 0.8763 | 0.8068 | +0.0695 | FAIL |
| **chair** | **AGREE_min3** (primary) | **0.8057** | 0.7994 | **+0.0063** | **FAIL** |
| chair | AGREE_geo3 (sensitivity) | 0.8527 | 0.7994 | +0.0533 | FAIL |
| chair | AGREE_min2 (TEED+DexiNed) | 0.8684 | 0.7994 | +0.0690 | FAIL |

**The primary arm's verdict is not robust.** It flips sign across the two scenes with margins
of 0.0076 and 0.0063 — **303 seeds of 39,888 on lego, 108 of 17,065 on chair**. A screen whose
outcome turns on a few hundred seeds out of tens of thousands is telling us the two things are
the same size, not that one is bigger.

## 3. The cross-model invariance question, answered empirically

This is the claim that motivated the candidate. Measured pairwise top-k overlap:

| pair | lego | chair |
|---|---|---|
| TEED vs DexiNed | 0.8068 | 0.7994 |
| TEED vs PiDiNet | 0.7062 | 0.7351 |
| DexiNed vs PiDiNet | 0.7322 | 0.7513 |

The three detectors agree on **71–81%** of their top-f selections. So the honest reading is
**partial** invariance: substantial agreement, with a real 19–29% disagreement that is the
raw material fusion would need. The citation was neither right nor wrong — it was the wrong
statistic for the question, and now it is measured rather than asserted.

But the decisive number is this: **agreement lands about as far from TEED as DexiNed does**
(0.7992 vs 0.8068 on lego; 0.8057 vs 0.7994 on chair). We already ran the DexiNed arm
end-to-end at matched density and it was neutral-to-worse — precision +0.006, recall -0.016,
P_pop ratio 12.10x -> 11.36x. The empirical prior for agreement is therefore the same
neighbourhood and the same expected outcome.

## 4. The free mechanistic finding — conjunction follows the weakest channel

Overlap of the primary agreement set with each single detector:

| agreement set vs | lego | chair |
|---|---|---|
| **PiDiNet** (weakest: lego P 0.6154 / R 0.3701) | **0.8376** | **0.8518** |
| DexiNed | 0.8243 | 0.8263 |
| **TEED** (best recall: lego P 0.6535 / R 0.4463) | **0.7992** | **0.8057** |

On **both** scenes the min-of-percentile set is **closest to PiDiNet and furthest from TEED**.
The mechanism is transparent: a carrier scores high under `min` only if **all three** detectors
rank it high, so the most restrictive channel dominates the ordering. Conjunction inherits the
weakest member.

Since PiDiNet is clearly the worst single detector on lego, this predicts tier-1 would show a
**recall loss** — the direction tier-0 by construction cannot see, and exactly the gap the
orchestrator's amendment was written to protect against.

**This is a post-hoc reading of the pairwise table, not a pre-registered result.** It updates
the prior sharply; it does not substitute for tier-1, and nothing is decided on it here.

## 5. Where this leaves candidate 1

- **chair: CLOSED** by the frozen bar. No tier-1, no pull.
- **lego: tier-1 earned, nothing more.** My prior that it clears tier-1 was 0.30 before this
  run; the weakest-channel finding drops it to roughly **0.12**, because the operator's
  own structure points at the detector with the worst recall on the scene whose binding
  constraint is recall.
- A defensible alternative, if the direction matters more than the pre-registration, is to
  drop PiDiNet and test `AGREE_min2`. But that arm **failed tier-0 on both scenes** by the
  widest margins in the table (+0.0695 / +0.0690) — it is nearly a relabeling of TEED. The
  two-channel version is too close to TEED to matter; the three-channel version moves, but
  toward the wrong detector. That is an unattractive pair of options and I report it as such.

## 6. Invariants

No mesh. No GPU. No pull. No stroke set touched. No shipped json modified. Not committed.
New artifacts: `scripts/pb1b_tier0.py`, `out/pb1b_tier0.json`, this file.
