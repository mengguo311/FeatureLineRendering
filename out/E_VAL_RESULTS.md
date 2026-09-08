# E-VAL — clean re-selection of the lego operating point on the VAL split

**VERDICT: CLEAN.** The VAL selection rule picks a TEED arm, and the VAL recall gap over the
shipped canny point is **+0.2401**, far above the 0.14 CLEAN bar. The TEED-over-canny
dominance is **not a selection artifact**: it retains **92.7–94.6%** of its TEST recall gap on
an independent split, across every TEED arm tested.

**One thing the rule did that the standing claim did not: it selected f=0.50, not f=0.40.**
Reported straight in §4, along with a design flaw in my own frozen rule.

---

## PROVENANCE NOTE (mandatory, carried with every downstream use of these numbers)

> The lego operating point was re-selected on the **VAL** split {0,10,…,90} using a rule
> frozen before the numbers were read. The VAL-selected arm is **TEED native-0.5, f=0.50**;
> the standing point **TEED native-0.5, f=0.40** is the second-highest-recall eligible arm and
> retains 94.0% of its TEST recall gap on VAL.
> **This is PARTIAL REMEDIATION, not a single look.** All eight arms had already been observed
> on TEST before this run. It converts "selected on TEST" into "selected on VAL with TEST
> previously seen" — materially better than the status quo, and weaker than a true held-out
> single look. The only fully clean confirmation set remaining is **ficus**, which has never
> been used for any selection and on which no TEED run exists.

## 1. Why this was necessary — the concrete finding

`src/view_split.py` freezes VAL as the split "used to pick gate thresholds / iteration counts"
and TEST as "never seen by the pull, never used to choose a threshold. Report here."

A disk-wide query of every lego result json returned **zero runs with `eval_split != 'test'`**.
Not one lego arm had ever been evaluated on VAL. The standing choice of detector, detector
threshold and f was therefore made by reading TEST, out of 100+ arms in the banked sweep, in
violation of the project's own frozen protocol.

Clean by contrast, and unaffected: the DT pull consumed TRAIN only (`pull_split: train`), so
no linelet was ever optimised against VAL or TEST.

## 2. The table

Stage: **SPEC mask only** (`z["keep"]`). The TEED and DexiNed npz do not store `keep_tuned`,
so tuned+len is not computable without a re-pull. Stated, never mixed. No re-pull was done —
linelets are static 3D, so only rasterisation and scoring changed views. TEST columns are
banked and were read, not recomputed.

| arm | keep | VAL P@1.5 | VAL R@1.5 | TEST P | TEST R | ΔP (VAL−TEST) | ΔR (VAL−TEST) |
|---|---|---|---|---|---|---|---|
| canny f=0.30 (shipped baseline) | 25,279 | 0.5747 | 0.4254 | 0.5826 | 0.4168 | −0.0079 | +0.0086 |
| canny f=0.40 | 33,133 | 0.5758 | 0.4900 | 0.5832 | 0.4817 | −0.0075 | +0.0083 |
| TEED0.5 f=0.30 | 26,759 | 0.6061 | 0.5643 | 0.6201 | 0.5666 | −0.0140 | −0.0023 |
| TEED0.5 f=0.35 | 30,923 | 0.6061 | 0.5964 | 0.6212 | 0.5993 | −0.0151 | −0.0029 |
| **TEED0.5 f=0.40** (standing) | 35,028 | **0.6053** | **0.6228** | 0.6197 | 0.6267 | −0.0144 | −0.0039 |
| **TEED0.5 f=0.50** (VAL-selected) | 42,815 | **0.5998** | **0.6655** | 0.6143 | 0.6707 | −0.0145 | −0.0052 |
| TEED0.9 f=0.30 | 26,549 | 0.6049 | 0.5444 | 0.6178 | 0.5452 | −0.0129 | −0.0008 |
| DexiNed0.5 f=0.40 | 34,176 | 0.6070 | 0.6006 | 0.6211 | 0.6052 | −0.0141 | −0.0046 |

VAL is uniformly a slightly harder split for precision (every arm reads 0.008–0.015 lower) and
essentially neutral for recall. That offset is arm-independent, so the comparison is stable.

## 3. Verdict against the frozen rule

Rule: maximise VAL spec R@1.5 subject to VAL spec P@1.5 ≥ (baseline VAL P − 0.02) = **0.5547**.
Seven of eight arms cleared the precision floor.

| | value |
|---|---|
| VAL-selected arm | **TEED0.5 f=0.50** |
| VAL recall gap over baseline | **+0.2401** (CLEAN ≥ 0.14, LEAK < 0.07) |
| TEST recall gap over baseline | +0.2538 |
| **recall-gap retention VAL/TEST** | **0.946** |
| **PRECISION GAP — VAL** | **+0.0250** |
| **PRECISION GAP — TEST** | **+0.0317** |
| **precision-gap retention** | **0.790** |

**VERDICT: CLEAN.**

**Retention across every arm** — the result does not hinge on which arm the rule picked:

| arm | VAL ΔR | TEST ΔR | **retention** | VAL ΔP | TEST ΔP | retention |
|---|---|---|---|---|---|---|
| TEED0.5 f=0.30 | +0.1389 | +0.1497 | 0.928 | +0.0314 | +0.0375 | 0.837 |
| TEED0.5 f=0.35 | +0.1710 | +0.1825 | 0.937 | +0.0314 | +0.0386 | 0.813 |
| **TEED0.5 f=0.40** | **+0.1974** | +0.2099 | **0.940** | +0.0306 | +0.0371 | 0.825 |
| TEED0.5 f=0.50 | +0.2401 | +0.2538 | 0.946 | +0.0250 | +0.0317 | 0.790 |
| TEED0.9 f=0.30 | +0.1190 | +0.1283 | 0.927 | +0.0302 | +0.0352 | 0.857 |
| DexiNed0.5 f=0.40 | +0.1753 | +0.1884 | 0.930 | +0.0323 | +0.0385 | 0.838 |

Every TEED arm retains 92.7–94.6% of its recall gap and 79–86% of its precision gap.

**A prediction of mine was partly wrong, recorded.** I pre-registered the expectation that
recall would survive and precision might not, because the TEST precision edge of +0.034 sits
inside the 0.016–0.038 between-split spread of a ten-view mean. Recall survived at 94%.
**Precision also survived**, at 79–86% — it shrank about three times as much as recall, so the
direction of the prediction held, but the hedge that it might vanish did not.

## 4. The rule selected f=0.50, and my rule had a flaw

The frozen rule is purely static: maximise recall subject to a precision floor. It contains
**no temporal term**. Because the precision floor barely binds, the rule is monotonically drawn
toward larger f and picks the largest f in the shortlist. Had I included f=0.60 or f=0.70 it
would have picked those — and PB1 measured both as **failing** the 10.345x temporal invariant
(10.27x and 10.24x). That is a design flaw in my pre-registration and I am not going to
retro-fit the rule to hide it.

What the flaw does and does not affect:

- **It does not affect the CLEAN verdict.** The question E-VAL was dispatched to answer is
  whether the TEED-over-canny dominance is selection-inflated. It is not, on every arm.
- **It does leave the choice of f unsettled.** Adding the temporal bar as a hard constraint
  does not change the pick — TEED f=0.50 measures 10.38x and passes — but it passes with
  **0.04x of margin** where f=0.40 has **1.76x**, and PB1 located the fragmentation knee
  immediately above f=0.50 (10.38x → 10.27x at f=0.60).

**Recommendation: the detector claim is settled and CLEAN; the f claim is not.** f=0.40 remains
the defensible operating point on robustness grounds, not because f=0.50 violates a rule. A
clean f selection needs its own pre-registration carrying a temporal **margin** term rather
than a bare pass/fail bar.

## 5. What E-VAL does not fix

- TEST was already seen for all eight arms (the provenance note above).
- VAL is now spent as a selection set and can no longer serve as clean confirmation.
- Only the spec stage is measurable; the tuned+len headline stage would need a re-pull.
- The M1a seed evidence consumed 25 spread views including 3 VAL and 3 TEST — an arm-equal
  leak inherited from the M1a recipe, disclosed in `RECALL_RESULTS.md` and untouched here.
- The 3DGS was fit on all 100 views, arm-equal and disclosed project-wide.

## 6. Invariants

Manifest **332/332 OK, 0 FAILED**. No re-pull, no stroke set touched, no shipped json or figure
modified. Mesh EVAL-ONLY via the pre-existing VAL oracle cache
(`cache/oracle_lego_a30_v0-10-…-90.npz`). One Harness G-buffer pass per VAL view. New
artifacts: `scripts/e_val.py`, `out/e_val_lego.json`, `logs/e_val.log`, this file.
Not committed. **Ficus GPU not spent** — reporting first, as instructed.
