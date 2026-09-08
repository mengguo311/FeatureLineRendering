# E-TRAJ-CHAIR — does the chair temporal claim survive a second trajectory?

**VERDICT: SAFE, on all three arms, with the primary and the control in the SAME band.
No paper action required.**

The published chair configuration measures **10.18x** on a trajectory it has never been
evaluated on, against a SAFE bar of 8.0x and the published envelope floor of 3.44x.

**My BREACH worry was overblown and I want that on the record.** I predicted chair might swing
like lego's −28.6% and land near 8.1x. It swung **−10.3%** and landed at 10.18x. Chair's
trajectory sensitivity is roughly a third of lego's, and it is **bidirectional** — one arm
improved.

Guards honoured: the VAL orbit was fixed as **views 0 → 10**, the same deterministic rule
E-FMARGIN used for lego, chosen before any number was read and with no path selection. Both
the published and control verdicts are reported separately. Raw per-orbit ratios are emitted
for all three arms.

Mesh EVAL-ONLY. No pull. No stroke set touched. Manifest **332/332 OK**. Not committed.

---

## 1. The table

VAL orbit = views 0 → 10, 240 frames, never used before. TEST orbit = views 5 → 15, banked.

| arm | chains | str/f | unmatched | cut | OURS P_pop | **VAL-orbit** | TEST-orbit | **swing** | band |
|---|---|---|---|---|---|---|---|---|---|
| **ungated (PUBLISHED)** | 1,184 | 470 | 0.0225 | 0.0399 | 0.06239 | **10.18x** | 11.35x | **−10.3%** | **SAFE** |
| gated canny f=0.30 (control) | 1,166 | 468 | 0.0202 | 0.0319 | 0.05211 | **12.18x** | 10.71x | **+13.7%** | **SAFE** |
| TEED0.5 f=0.30 | 1,137 | 451 | 0.0302 | 0.0220 | 0.05217 | **12.17x** | 13.12x | **−7.2%** | **SAFE** |

**Bands AGREE** — published 10.18x SAFE, control 12.18x SAFE. Nothing to report separately,
and nothing averaged.

**BASE self-check.** The VAL-orbit Canny baseline is re-derived per arm at Frechet
0.98260–0.98323 and P_pop 0.63450–0.63510 — agreement to 0.1%. Internally consistent.

## 2. Per-orbit calibration, applied as E-FMARGIN's lesson demanded

The bar is **0.9 × the ungated arm's ratio on the same orbit**, never imported across
trajectories:

| orbit | per-orbit bar | ungated | gated canny | TEED f=0.30 |
|---|---|---|---|---|
| VAL (0→10) | **9.16x** | 10.18x clears | 12.18x clears | 12.17x clears |
| TEST (5→15) | 10.21x | 11.35x clears | 10.71x clears | 13.12x clears |

**The E-FMARGIN validity gate passes here.** That gate fires when the control's ratio moves
more than 20% between orbits. On lego it fired at 28.6% and voided the rule. On chair the
swings are 10.3%, 13.7% and 7.2% — all inside the gate. **The gate is doing real work: it
rejected lego where the trajectories genuinely differ and admits chair where they do not.**

## 3. The finding: lego's 28.6% swing is not a general property

| scene | control swing, TEST orbit → VAL orbit |
|---|---|
| lego | **−28.6%** (12.10x → 8.64x) |
| **chair** | **+13.7%** (10.71x → 12.18x) |

Chair's swings are smaller and go **both ways**. So trajectory sensitivity is a **scene
property**, not a property of the metric. Chair's temporal numbers are trajectory-robust;
lego's are not, and lego's E-FMARGIN INVALID verdict therefore stands — any future
temporal-margin rule on lego still needs per-orbit calibration first.

**Mechanism.** The chair VAL orbit involves less inter-frame motion: the baseline's Frechet
falls 1.2252 → 0.9826 and its P_pop falls 0.755 → 0.635, so the per-frame detector has an
easier time. Our strokes improve too (ungated 0.06656 → 0.06239), but for the ungated arm the
baseline improves more, which compresses the ratio. For the gated arm ours improves far more
(0.07052 → 0.05211) and the ratio grows. Visible stroke population also drops sharply,
751 → 470 per frame, so the two orbits show materially different aspects of the object.

## 4. The "thin margin" flag from E-VAL-chair is retired

I flagged that the gated canny chair arm sits at 10.71x, only 3.5% over the TEST-derived
10.345x bar — the thinnest configuration measured on either scene. That flag was **TEST-orbit
specific**. On the VAL orbit the same arm reaches 12.18x and clears its per-orbit bar by 33%.
The thin margin was a property of one trajectory, not of the chair configuration.

## 5. One ordering oddity, reported not resolved

The arm ordering flips between orbits. On TEST: ungated 11.35x > gated 10.71x. On VAL:
gated 12.18x > ungated 10.18x. Both clear comfortably on both orbits, so nothing is at stake,
but it means **arm ranking by temporal ratio is not trajectory-stable on chair** and no
chair operating point should be selected on a temporal ranking from a single orbit.

## 6. What this settles

- **The chair temporal claim is trajectory-robust.** The published configuration holds at
  10.18x on an unseen trajectory, comfortably inside the published 3.44x–11.49x P_pop envelope.
  No disclosure sentence is required.
- **The crown jewel is not the fragility I feared.** The open risk that motivated this
  experiment is closed.
- **Lego remains the trajectory-sensitive scene**, and its temporal-margin rule remains
  un-calibrated. That is unchanged and still open.
- Chair operating-point selection must not use single-orbit temporal ranking (section 5).

## 7. Invariants

Manifest **332/332 OK, 0 FAILED**. VAL orbit fixed deterministically as views 0 → 10 before
any measurement, matching the lego rule. No re-pull, no stroke set touched, no shipped json or
figure modified; all three arms used non-empty `--viz_tag`. Mesh EVAL-ONLY. New artifacts:
`m1b_stroke_temporal_table_etraj_valorb_{ungated,gated,tcteed}.{json,md}`,
`m1b_vector_chair_etrj{u,g,t}_*.{svg,png}`, `logs/e_traj_chair.log`, this file. Not committed.
