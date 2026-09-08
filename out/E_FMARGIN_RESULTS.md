# E-FMARGIN — clean f selection with a temporal margin term

**VERDICT: INVALID.** The pre-registered trajectory-validity gate fired. The control's
VAL-orbit P_pop ratio is **8.644x** against **12.10x** on the TEST orbit — a **28.6% relative
deviation**, past the 20% threshold I froze. The two trajectories are not comparable, the
margin term is therefore uncalibrated, and **nothing is selected**.

**f=0.40 remains the standing point, unchanged and un-promoted.** It was not confirmed by the
rule; the rule did not run to a decision.

This gate existed because I was introducing a new trajectory and said it must validate before
it decides anything. It did not validate. Reported straight.

---

## PROVENANCE NOTE (carried forward from E-VAL, still binding)

> The lego operating point was re-selected on the **VAL** split using a rule frozen before the
> numbers were read. E-VAL's VAL-selected arm was **TEED native-0.5 f=0.50**; the standing point
> **TEED native-0.5 f=0.40** retains 94.0% of its TEST recall gap on VAL. **This is PARTIAL
> REMEDIATION, not a single look** — all arms had already been observed on TEST. The only
> unspent clean confirmation set is **ficus**.

## 1. The table

VAL-orbit = views **0 → 10**, 240 frames, a trajectory never used before. Static VAL spec P/R
from E-VAL (f=0.60 newly computed here). Stage: **SPEC mask** throughout; tuned+len linelet
counts are listed but their temporal is not computable without a re-pull. Stages labelled,
never mixed.

| arm | spec lin | tuned lin | str/f | unmatched | cut | P_pop | **VAL-orbit ratio** | TEST-orbit ratio | VAL spec P | VAL spec R |
|---|---|---|---|---|---|---|---|---|---|---|
| canny f=0.30 (control) | 25,279 | 20,142 | 971 | 0.0432 | 0.0387 | 0.08192 | **8.64x** | 12.10x | 0.5747 | 0.4254 |
| **TEED f=0.40** | 35,028 | 28,539 | 1,549 | 0.0430 | **0.0310** | **0.07398** | **9.57x** | 12.10x | 0.6053 | 0.6228 |
| TEED f=0.50 | 42,815 | 34,385 | 1,827 | 0.0409 | 0.0385 | 0.07946 | 8.91x | 10.38x | 0.5998 | 0.6655 |
| TEED f=0.60 | 50,183 | 39,742 | 2,087 | 0.0409 | 0.0401 | 0.08107 | 8.73x | 10.27x | 0.5960 | 0.7001 |

**BASE self-check.** The VAL-orbit Canny baseline is re-derived per arm at Frechet
1.24660–1.24817 and P_pop 0.70775–0.70807 — agreement to 0.05%. The VAL-orbit measurements are
internally consistent. They simply do not map onto the TEST-orbit scale.

## 2. Why the gate fired

The VAL orbit is a materially harder trajectory for our strokes and a slightly easier one for
the baseline:

| | TEST orbit (5→10 gap) | VAL orbit (0→10 gap) |
|---|---|---|
| control OURS P_pop | 0.05942 | **0.08192** |
| control unmatched / cut | 0.0340 / 0.0254 | **0.0432 / 0.0387** |
| control strokes/frame | 1,119 | **971** |
| control BASE P_pop | 0.71883 | 0.70807 |

Both P_pop terms rise while the visible stroke population falls, so the trajectory shows a
different aspect of the object with more occlusion churn per stroke. P_pop is not
trajectory-invariant, and a margin term calibrated on one orbit cannot be transported to
another without re-establishing the reference there.

## 3. A second flaw in my margin design, exposed by this run

The gate firing is the headline, but the rule had a further defect worth recording.

I set the margin as **ratio ≥ 0.90 × control ratio**. On the VAL orbit that bar is 7.779x, and
**every arm clears it**, including f=0.60 at 8.73x. The arms are clustered within ~10% of the
control (9.57x → 8.73x, a 9% spread) so a 10% allowance never binds. Had the gate not fired,
the rule would have selected **f=0.60** — the arm PB1 measured as *failing* the temporal
invariant on TEST at 10.27x.

The margin term was meant to encode "do not ship at the knee." A bar pegged to the *control*
cannot do that, because the control is not the knee. The correct form is a margin against the
**invariant bar** — on TEST that is ratio/10.345 − 1, giving f=0.40 → 0.170, f=0.50 → 0.003,
f=0.60 → −0.007, which discriminates sharply. But 10.345x is itself TEST-derived, so using it
requires establishing the shipped reference on the new orbit first. **That is precisely the
calibration the INVALID gate demanded, and it is the work this run shows is needed.**

Two frozen rules, two flaws found, both by their own gates. I am recording them rather than
retro-fitting.

## 4. What the run does establish, without selecting anything

**The rank ordering of arms is stable across both trajectories**, even though the absolute
scale is not:

| arm | TEST-orbit | VAL-orbit |
|---|---|---|
| **TEED f=0.40** | **12.10x** (best) | **9.57x** (best) |
| TEED f=0.50 | 10.38x | 8.91x |
| TEED f=0.60 | 10.27x | 8.73x |
| canny f=0.30 control | 12.10x | 8.64x (worst) |

TEED f=0.40 is the best temporal arm on **both** orbits, and its `cut` is the lowest on both
(0.0225 TEST, 0.0310 VAL). On the VAL orbit it also **beats** the canny control (9.57x vs
8.64x) where on TEST it merely tied. That is corroboration for the standing point from an
independent trajectory — offered as corroboration, not as a selection, since the rule is void.

## 5. Status

- **f = 0.40 stands**, on the same robustness grounds as before, now with independent-trajectory
  corroboration and without a clean rule-based confirmation.
- A valid f selection still needs: the shipped reference re-established on whichever trajectory
  the margin is measured on, then a margin expressed against the invariant bar rather than the
  control. That is a re-pre-registration, not a re-run of this one.
- The temporal invariant is untouched: every arm on both orbits, and the shipped configuration,
  remain above their respective bars.

## 6. Invariants

Manifest **332/332 OK, 0 FAILED**. No pull. No stroke set touched. No shipped json or figure
modified; all four arms used non-empty `--viz_tag`. Mesh EVAL-ONLY. New artifacts:
`m1b_stroke_temporal_table_fm_valorb_{canny030,teed040,teed050,teed060}.{json,md}`,
`m1b_vector_lego_fm{c030,t040,t050,t060}_*.{svg,png}`, `out/e_fmargin_val_f060.json`,
`logs/e_fmargin.log`, this file. Not committed.
