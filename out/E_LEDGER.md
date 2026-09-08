# E-LEDGER — canonical claim ledger for the evidence-frontier campaign

**Purpose.** Ten result documents exist; no single artifact states what is standing, what was
withdrawn, and what supersedes what. The measured cost of that gap: **the refuted figures
"24.85% of the lego miss-set" and "recall 0.229" were re-imported as live premises into four
separate briefs after E-BAND corrected them.** This file is the single source of truth.

**PRE-REGISTERED GATE:** GO iff **0 unsourced numerals** AND **0 contradictions** against the
banked jsons on an automated re-read. Verified by `scripts/e_ledger_check.py`; result in §10.

Every numeral below names its source file. Nothing here is new; nothing is recomputed.

---

## 1. STANDING OPERATING POINTS

| scene | shipped | evidence candidate | status |
|---|---|---|---|
| lego | canny f=0.30 — tuned P **0.6196** / R **0.2856** (`m1b_lego_gated_test.json`) | **TEED0.5 f=0.40** — tuned P **0.6535** / R **0.4463** (`m1b_lego_tc_teed_native_0.5_f0.40.json`), temporal **12.10x** (`..._ehyb_teed040.json`) | candidate **STANDS**, VAL-clean |
| chair | canny f=0.30 — tuned P **0.6573** / R **0.5959** (`m1b_chair_gated_test.json`), published temporal **11.35x** (`m1b_stroke_temporal_table.json`) | none | shipped point stands; TEED proposal **WITHDRAWN** (§3) |

lego published temporal (ungated arm): **11.494x** (`m1b_stroke_temporal_table.json`).

## 2. THE BREAKTHROUGH THAT SURVIVED

**Improving the evidence that ranks carriers moves the recall-vs-stability frontier outward at
zero temporal cost.** On lego, gate- and mask-matched (`..._vf100_gate030.json`,
`..._ehyb_teed040.json`):

| | canny f=0.30 | TEED f=0.40 |
|---|---|---|
| spec P@1.5 | 0.5826 | **0.6197** |
| spec R@1.5 | 0.4168 | **0.6267** |
| P_pop | 0.05942 | **0.05942** |
| P_pop ratio | 12.10x | **12.10x** |
| Frechet ratio | 13.98x | **14.81x** |

Mechanism, the double dissociation (`..._ehyb_teed040.json`, `..._vf100_f100spec.json`):
**+47% strokes at better evidence** lowers `cut` 0.0254 → **0.0225**; **+182% strokes at fixed
evidence** raises it to **0.0424**.

Held-out status: **CLEAN** on VAL, recall-gap retention **0.946** (`e_val_lego.json`).

## 3. WITHDRAWN RECOMMENDATIONS — mine, with what withdrew each

| recommendation | withdrawn by | measurement |
|---|---|---|
| DexiNed as "the correctly-aimed precision instrument for chair" | `CHAIR_DEXINED_RESULTS.md` | chair seed P **0.5786** vs TEED **0.6485** — loses by 0.070 |
| chair standing point TEED0.5 f=0.30 | `E_VAL_CHAIR_RESULTS.md` | VAL precision gap **−0.0452** against a **−0.02** allowance, 2.3x over |
| ficus as the consolidation confirmation | design argument | excluded by our own stated criterion; GT covers ~31% of geometric creases; negative EV |
| "corners are points not lines is an empirical question" → E-CORNER | design argument | chains cannot turn corners by construction; junctions are chain-termination sites; the proposed fix relocates the carrier, not the wall it chains into |

## 4. CLOSED CHANNELS — the rank lever is 0-for-4, on measurement

| channel | mechanism real? | beat the existing rank? | source |
|---|---|---|---|
| detector union | — | **no** — union 0.6429/0.4424 < TEED 0.6535/0.4463 | `m1b_lego_tc_union_native_0.5_f0.40.json` |
| agreement-rank (min-of-percentile) | yes — channels overlap only 0.71–0.81 | **no** — conjunction inherits the weakest channel; agreement sits closer to PiDiNet (**0.8376**) than TEED (**0.7992**) | `pb1b_tier0.json` |
| junction / corner response | **yes** — AUC **0.7053** | **no** — TEED seedscore **0.7271** | `a_reframed_tier0.json` |
| **multi-scale coarse/fine ratio** | **yes** — ms_alone **0.6501** > native **0.6058** | **no** — TEED seedscore **0.7270**; culled non-tess 0.6250 vs 0.7071 | `ms_ratio_tier0.json` |

Also closed: per-frame ink fusion (arithmetic, r ≤ 1.06%), DexiNed-primary, FeatureGS,
EdgeGaussians, 3Doodle, f=1.00, aggressive linking, geometric crease-vs-texture discriminators.

## 5. SUPERSEDED NUMBERS — do not re-import

| retired figure | replaced by | source |
|---|---|---|
| 90-deg family = **24.85%** of lego miss-set | **0.1505** | `e_band_lego.json` |
| 90-deg family recall **0.229** | realised R **0.7983**, above the global **0.6744** | `e_band_lego.json` |
| 90-deg family = "largest recoverable block" | culled **0.0938**, second-smallest; the 30.000-deg tessellation family is largest at **0.2966** culled and **0.649** of the miss-set | `e_band_lego.json` |
| Experiment X g=0.948 / decal=0.000 | g_literal **1.000**, a tautology by construction | `XY_RETRAIN_FALSIFY_RESULTS.md` §X.1 |

The 0.229 originates in Experiment X's **3D** metric against the DexiNed triangulation cloud —
a different metric space and candidate set from the 2D pipeline frame.

## 6. THE TESSELLATION WALL

Rank-reachable mass on lego, per band, weighted by share of all crease points
(`e_band_lego.json`; parts sum to the measured global culled **0.1754**):

| | reachable mass |
|---|---|
| 30.000-deg tessellation | **0.125** (71%) |
| all non-tessellation bands | **0.050** (29%) |

A perfect non-tessellation re-rank adds at most **+0.050** global recall. Raising f draws mass
roughly in proportion, so ~71% of what it buys is tessellation. Precision on that family falls
**0.6360 → 0.3097** at a 30.05-deg threshold (`LEGO_THRESHOLD_AUDIT.md`).

## 7. RULE FLAWS FOUND BY THEIR OWN GATES

| rule | flaw | caught by |
|---|---|---|
| E-VAL selection rule | purely static — no temporal term; monotonically drawn to large f; selected f=0.50 | `E_VAL_RESULTS.md` §4 |
| E-FMARGIN margin term | pegged to the control, which is not the knee; every arm cleared; would have selected f=0.60, an arm measured at **10.27x**, below the invariant | `E_FMARGIN_RESULTS.md` §3 |
| E-FMARGIN trajectory gate | fired correctly — control swung **28.6%** between orbits, so the bar cannot be transported | `E_FMARGIN_RESULTS.md` §2 |

## 8. TRAJECTORY ROBUSTNESS — both risks closed SAFE

| arm | TEST orbit | VAL orbit (0→10) | swing | band |
|---|---|---|---|---|
| lego published (ungated) | 11.494x | **8.663x** | −24.6% | **SAFE** |
| chair published (ungated) | 11.35x | **10.18x** | −10.3% | **SAFE** |
| lego gated canny control | 12.10x | 8.64x | −28.6% | — |
| chair gated canny control | 10.71x | 12.18x | +13.7% | — |

Sources: `..._etraj_lego_valorb_ungated.json`, `..._etraj_valorb_{ungated,gated}.json`,
`..._fm_valorb_canny030.json`. **Trajectory sensitivity is a scene property**: lego swings
~25–29%, chair ~7–14% and in both directions.

## 9. OPEN ITEMS

1. **lego f choice unsettled.** VAL selected f=0.50; robustness argues f=0.40 (12.10x with
   1.76x of margin vs f=0.50's 0.04x). A valid selection needs a margin against the invariant
   bar, re-established per orbit.
2. **Selection provenance is partial remediation.** All arms were observed on TEST before VAL
   re-selection. Ficus is the only unspent set and is not recommended (§3).
3. **Chair has no promoted evidence point.** E-VAL-chair returned MIDDLE.
4. **Chair operating points must not be selected on single-orbit temporal ranking** — the arm
   ordering flips between orbits (`E_TRAJ_CHAIR_RESULTS.md` §5).

## 10. GATE RESULT

`scripts/e_ledger_check.py` re-reads every named banked json and compares it to the numeral
asserted here. Rule: **the banked value must round to the numeral at the precision asserted.**

| | |
|---|---|
| numerals checked | **54** |
| unsourced | **0** — every check names its banked json |
| contradictions | **0** |
| **GATE** | **GO** |

**A third rule flaw, found by this gate and recorded rather than hidden.** The v1 checker used
an absolute tolerance of 5e-4, which on a magnitude-10 ratio demands four-decimal agreement
from a numeral written to two. It flagged 10 "contradictions" that were all the banked value
correctly quoted to 2dp (12.0970 -> 12.10, 11.3454 -> 11.35, and so on). A further 3 were
3-significant-figure claims checked at 4dp. **Zero were real contradictions.** The defect was
in the gate, not the ledger; the fix reads the asserted precision instead of guessing it from
magnitude. This is the third pre-registered rule this campaign whose own gate exposed a flaw in
it — after the E-VAL selection rule and the E-FMARGIN margin term (section 7).

Raw result: `out/e_ledger_check.json`.
