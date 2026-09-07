# E-BAND — per-dihedral-band miss decomposition on lego

**VERDICT: MIDDLE BAND by the letter; a decisive DO-NOT-BUILD for candidate 4 in
substance.** The pre-registered NO-GO (UNCOVERED >= 0.60) did not fire, but the GO failed
on three of its four requirements, and **both mandatory instrument checks failed**. Per the
locked spec the decomposition is reported and **not acted on**.

The headline finding is not the one the experiment was designed to produce: **the
2D carrier-coverage frame at tau = 1.5 px is uninformative on lego at this carrier density.**
Crease points are covered *less often* than random foreground pixels.

Executes `ehyb_evidence_spec.md` Phase B gate as locked. Mesh EVAL-ONLY via banked caches only.
No stroke set touched, no score built, no shipped json modified, not committed.
Manifest **332/332 OK, 0 FAILED**. Script `scripts/e_band.py`, raw `out/e_band_lego.json`,
log `logs/e_band.log`.

---

## 1. Setup and reproduction control

Seed set, fixed and pre-registered: **TEED f=0.40**, seeds = round(0.4 x 99,721) = **39,888**;
spec keep **35,028**. Population: visible GT crease **points** on lego held-out TEST views,
**n = 1,748,144**, taken from the banked z-peeled cache `cache/dexp0_gt_lego_a30.npz`
(per-view `idx`/`uv`), joined to the banked per-point dihedral in
`out/xy/xy_expX_lego_p1c.npz`. **theta_nan = 0** — every population point carries a dihedral.

**Reproduction control passes.** Global UNCOVERED = **0.3663**, reproducing
`LEGO_CEILING_AUTOPSY.md` Figure B exactly. UNCOVERED does not depend on the seed set, so this
is the right invariant to check. Ranked/culled do depend on it, and TEED ranks in more of the
covered carriers than the autopsy's ngmecv2 set did (0.4583 vs 0.4475) while culling fewer
(0.1754 vs 0.1862) — consistent with TEED being the better ranker.

## 2. The table

Frame 1 is seed-level (autopsy convention). Frame 2 (A/B0/B1/B2) is output-level, CAP
convention, computed on that band's **missed** subset. Realised recall is in the **point**
frame; the banked spec-stage pixel-frame value for this arm is 0.6267 and the two frames are
not interchangeable.

| band | n | share of all | share of miss-set | UNCOVERED | **CULLED** | RANKED | realised R | conv | A | B0 | B1 | **B2** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| theta = 30.000 | 737,850 | 0.422 | **0.649** | 0.3804 | **0.2966** | 0.3230 | 0.4994 | 1.546 | 0.713 | 0.115 | 0.157 | 0.015 |
| 30.05–60 | 291,249 | 0.167 | 0.114 | 0.3832 | 0.0908 | 0.5259 | 0.7777 | 1.479 | 0.653 | 0.157 | 0.173 | 0.018 |
| 60–89.95 (control) | 211,294 | 0.121 | 0.068 | 0.3163 | 0.0687 | 0.6150 | 0.8162 | 1.327 | 0.713 | 0.106 | 0.173 | 0.008 |
| **theta = 90.000** | 424,799 | 0.243 | 0.151 | **0.3760** | **0.0938** | 0.5302 | **0.7983** | 1.506 | 0.704 | 0.120 | 0.164 | **0.012** |
| >= 90.05 | 82,952 | 0.047 | 0.019 | 0.2591 | 0.0833 | 0.6575 | 0.8732 | 1.328 | 0.800 | 0.077 | 0.120 | 0.002 |
| **GLOBAL** | 1,748,144 | 1.000 | 1.000 | **0.3663** | 0.1754 | 0.4583 | 0.6744 | 1.472 | — | — | — | — |

## 3. Both mandatory checks failed

**NULL CHECK — FAILED on every band, and inverted on three.**
Null = 20,000 uniform foreground pixels per view through the identical COVERED test.
Null covered rate = **0.6428**. Required margin: +10 points.

| band | COVERED | delta vs null | |
|---|---|---|---|
| theta = 30.000 | 0.6196 | **-2.31 pt** | FAIL |
| 30.05–60 | 0.6168 | **-2.60 pt** | FAIL |
| 60–89.95 (control) | 0.6837 | +4.10 pt | FAIL |
| **theta = 90.000** | 0.6240 | **-1.87 pt** | FAIL |
| >= 90.05 | 0.7409 | +9.81 pt | FAIL |

Globally, crease points are covered at 0.6337 against a random-foreground 0.6428. **A crease
point is very slightly *less* likely to have a carrier within 1.5 px than an arbitrary
foreground pixel.** With ~100k centres projected into a 640k-pixel frame the test is
density-dominated; it measures projected carrier density, not carrier presence at creases.
This is the CAP Class-A failure mode (0.729 vs 0.725) reappearing in the visibility-qualified
frame, and it is exactly what the null was written to catch.

**CONVERSION-TRANSFER CHECK — FAILED, and the model is wrong in kind.**
Control band conversion 1.3272 against global 1.4716, delta 0.1444 > 0.10. Worse, **every
conversion exceeds 1.0**, which is impossible for a true covered-to-realised map. The cause is
mechanical: `raster_segments` draws linelet **segments** of half-length l, so a linelet inks
crease points that have no carrier centre within 1.5 px. Centre-coverage is therefore not an
upper bound on realised recall, and the autopsy's 0.912 was an artifact of one particular
seed set and stage rather than a transferable factor. **No recall projection is made.**

## 4. Verdict against the locked go/no-go, on the exactly-90-degree family

| branch | condition | measured | fired? |
|---|---|---|---|
| **NO-GO** (structural) | UNCOVERED >= 0.60 | 0.3760 | no |
| **GO** (necessary) | UNCOVERED <= 0.45 | 0.3760 | yes |
| | COVERED-but-culled >= 0.25 | **0.0938** | **no** |
| | null passes | **FAIL** | **no** |
| | conversion transfers | **FAIL** | **no** |

**MIDDLE BAND.** Report, do not act. Candidate 4 is not built.

The GO's culled requirement missed by a factor of 2.7, not a knife edge. The 90-degree band
has the **second-smallest** ranking-reachable mass of any band measured.

## 5. The premise behind candidate 4 does not survive

Candidate 4 was motivated by the 90-degree family being "the largest recoverable block, recall
only 0.229." Two things are wrong with that.

**It is not underperforming in the frame the pipeline optimises.** Its realised recall here is
**0.7983 against a global 0.6744** — one of the better-recalled bands, not the worst. The
0.2294 figure comes from Experiment X's **3D** recall at 0.00508 against the frozen
**DexiNed-triangulation** cloud: a different metric space and a different candidate set. The
number was transplanted across pipelines.

**It is not the largest recoverable block.** By culled (ranking-reachable) mass the ordering is
the exactly-30.000-degree tessellation family at **0.2966**, then 30.05–60 at 0.0908, then
theta=90 at 0.0938. The 30-degree family carries **3.2x** the 90-degree family's reachable
mass and **64.9%** of the entire miss-set — and it is the family the threshold audit shows we
arguably should not draw at all.

**Recommendation: strike "largest recoverable block" from the spec's closed-branch list.**

## 6. The one null-calibrated result that does survive

CAP calibrated the true-void class against chance: B2 fires on **8.0%** of random foreground
pixels. Measured here on each band's missed subset:

| band | B2 share of missed |
|---|---|
| theta = 30.000 | 0.015 |
| 30.05–60 | 0.018 |
| 60–89.95 | 0.008 |
| **theta = 90.000** | **0.012** |
| >= 90.05 | 0.002 |

Every band is 4x to 40x **below** chance. **No band is void-limited**, including the
90-degree family. Whatever is suppressing recall anywhere on lego, it is not the absence of a
gaussian within 3 px.

## 7. Post-hoc note, explicitly not used to license anything

The null invalidates the *absolute* COVERED rate. It does not obviously invalidate the
*cross-band* culled comparison, because culled = covered AND not-seeded, and the second factor
is seed-set-relative and varies 3.2x across bands where the first is near-constant. That would
mean section 5's ordering carries real information about the TEED ranking.

This is post-hoc reasoning about a rule I wrote in advance and which failed. **It is recorded
as a hypothesis for a future pre-registration, not as a result, and nothing in this dispatch
is built on it.** The locked spec said a null failure makes the decomposition uninterpretable,
and that is how the verdict is scored.

## 8. The free banked read did not deliver

`m1b_stroke_temporal_table_abl_carrier_persistence.json` is **chair-only and contains a
120-frame cell only** — no lego arm and no 240-frame cell. It therefore does **not** bear on
the prune-side temporal question it was read to answer. Reported straight; the question stands
open, and any prune-side build still owes its own measured 10.345x gate.

## 9. What this establishes

**Establishes.** (a) The 2D projected carrier-coverage frame at tau=1.5 px is not a usable
diagnostic on lego — it sits at the density floor, which retro-explains why the autopsy's own
pre-registered coverage gate failed at 0.3663 < 0.45 and why its strong claim was correctly
forbidden. (b) Candidate 4 is dead: wrong target, on a premise transplanted across metric
spaces. (c) No band is void-limited. (d) The ranking-reachable mass on lego is concentrated in
the tessellation family we do not want to draw.

**Does not establish.** (a) Anything about whether a better rank helps globally — the
instrument is too blunt to attribute it band-wise. (b) Any temporal claim whatsoever. (c)
Anything about chair or ficus. (d) That coverage is fine — UNCOVERED is uninformative here,
not favourable.

**Invariants.** Manifest 332/332 OK. Shipped jsons and figures untouched. Mesh read only
through banked caches. One small G-buffer pass per TEST view for carrier visibility, matching
the autopsy's own practice — so this run is not literally CPU-only, and that is stated rather
than glossed. New artifacts: `scripts/e_band.py`, `out/e_band_lego.json`, `logs/e_band.log`,
this file. Not committed.
