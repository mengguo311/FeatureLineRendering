# PHASE B STEP 1 — evidence-quality knee mapping + DexiNed rider

**VERDICT: MIDDLE BAND (pre-registered GO not met, pre-registered NO-GO not met).**
The knee is **located and real**: it sits between **f=0.50 and f=0.60**. But the only f above
0.40 that clears the temporal bar misses the pre-registered recall threshold by **0.0003**
(R@1.5 0.4797 against a 0.48 bar). Per the frozen rule this is **not acted on**.
My modal prior ("60% unbounded to f=0.70") was **wrong**; the 30% bucket hit.

Executes `ehyb_evidence_spec.md` Phase B step 1. Mesh EVAL-ONLY, no retrain, no re-pull, no
re-tune, no shipped json touched, not committed. Manifest **332/332 OK, 0 FAILED** before and after.

---

## 1. The table (lego, 240-frame TEST orbit 5->15, identical warp + Canny baseline)

Bar: OURS P_pop <= **0.069509** (= baseline 0.71907 / 10.345x).
**Stages are labelled, never mixed.** Temporal is computed on the **spec** mask (`z["keep"]`),
which is what `build_chains` consumes and what the shipped temporal path uses. Static P/R is
banked at both stages. None of these npz store `keep_tuned`, so a tuned-mask temporal cell is
not computable without a re-pull; it is **not** reported rather than substituted.

| arm | spec lin | tuned lin | chains | str/f | unmatched | **cut** | P_pop | Frechet x | **P_pop x** | tuned P | tuned R | bar |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| canny f=0.30 CTRL | 25,279 | 20,142 | 1,895 | 1,119 | 0.0340 | 0.0254 | 0.05942 | 13.98x | 12.10x | 0.6196 | 0.2856 | PASS |
| TEED f=0.30 | 26,759 | 22,062 | 2,227 | 1,305 | 0.0381 | 0.0231 | 0.06120 | 14.62x | 11.75x | 0.6563 | 0.4004 | PASS |
| TEED f=0.35 | 30,923 | 25,369 | 2,515 | 1,460 | 0.0380 | 0.0232 | 0.06127 | 14.61x | 11.73x | 0.6557 | 0.4253 | PASS |
| TEED f=0.40 | 35,028 | 28,539 | 2,846 | 1,640 | 0.0370 | 0.0225 | 0.05942 | 14.81x | 12.10x | 0.6535 | 0.4463 | PASS |
| **TEED f=0.50** | 42,815 | 34,385 | 3,339 | 1,944 | 0.0366 | **0.0327** | 0.06923 | 14.80x | **10.38x** | 0.6488 | **0.4797** | **PASS** |
| **TEED f=0.60** | 50,183 | 39,742 | 3,830 | 2,221 | 0.0347 | 0.0353 | 0.06997 | 15.05x | **10.27x** | 0.6445 | 0.5038 | **FAIL** |
| **TEED f=0.70** | 57,159 | 44,718 | 4,332 | 2,461 | 0.0337 | 0.0365 | 0.07025 | 15.33x | **10.24x** | 0.6428 | 0.5225 | **FAIL** |
| **DexiNed f=0.40** (rider) | 34,176 | 27,654 | 2,711 | 1,647 | 0.0342 | 0.0290 | 0.06326 | 15.46x | **11.36x** | **0.6594** | 0.4301 | PASS |
| *canny f=1.00 (VF100)* | *75,326* | *56,269* | *5,532* | *3,159* | *0.0311* | *0.0424* | *0.07344* | *16.46x* | *9.79x* | *0.6360* | *0.5572* | *FAIL* |

**BASE self-check (free).** The Canny baseline is linelet-independent and re-derived in all nine
runs: Frechet 1.20073-1.20424, P_pop 0.71874-0.71913, against the shipped 1.202460 / 0.719067.
Agreement to 0.15% / 0.05%. Every arm is on one measuring stick.

## 2. Verdict against the frozen rule — reported straight

| pre-registered branch | condition | met? |
|---|---|---|
| **GO** | some f>0.40 with tuned R >= 0.48 **AND** tuned P >= 0.5996 **AND** ratio >= 10.345x | **NO** |
| **NO-GO** | f=0.50 already fails the ratio bar | **NO** (f=0.50 passes at 10.38x) |
| **UNBOUNDED** | f=0.70 still clears | **NO** (10.24x, fails) |

The GO fails on a single criterion at a single arm: **TEED f=0.50 gives tuned R@1.5 = 0.4797
against the 0.48 bar — short by 0.0003.** Every f that comfortably clears the recall threshold
(0.60, 0.70) breaks the temporal bar; the one f that holds the temporal bar misses recall by
three ten-thousandths.

This lands in an unlabelled middle band, exactly as `LEGO_CEILING_AUTOPSY.md` did at its own
0.3663-vs-0.45 gate. **The bar is not re-tuned and the result is not acted on.** f=0.40 remains
the standing recommended operating point from Phase A.

## 3. The knee is real, and it is a fragmentation onset

The primary question is answered decisively even though the GO is not met.

**Temporal bar crossing:** between **f=0.50 (10.38x) and f=0.60 (10.27x)**, i.e. between
**1,944 and 2,221 strokes/frame** (spec linelets 42,815 -> 50,183).

**The mechanism is the `cut` term, and its onset is earlier and sharper than the bar crossing:**

| str/f | 1,119 | 1,305 | 1,460 | 1,640 | 1,944 | 2,221 | 2,461 | 3,159 |
|---|---|---|---|---|---|---|---|---|
| cut | 0.0254 | 0.0231 | 0.0232 | 0.0225 | **0.0327** | 0.0353 | 0.0365 | 0.0424 |

`cut` is flat-to-declining through 1,640 strokes/frame, then jumps **+45% for +19% strokes**
between f=0.40 and f=0.50. So the **fragmentation onset is between 1,640 and 1,944 strokes/frame**,
tighter than the bar crossing.

**Why the bar breaks later than the onset:** `unmatched` falls monotonically as f rises
(0.0381 -> 0.0337), because denser coverage leaves fewer strokes without a partner. That decline
partially masks the rising `cut`, so P_pop climbs slowly (0.05942 -> 0.06923 -> 0.06997 -> 0.07025)
and crosses the bar one arm later than the fragmentation actually begins.

**Phase A's claim is refined, not overturned.** Better evidence does not abolish the
fragmentation ceiling; it **moves it outward**. At every density where both are measured, TEED's
`cut` is below canny's: TEED sustains cut <= 0.0232 out to 1,640 strokes/frame, where canny is
already at 0.0254 with only 1,119. Canny broke the bar by 3,159 strokes/frame; TEED is still at
10.24x with 2,461. No intermediate canny temporal arm exists between 1,119 and 3,159, so a
strictly matched-density canny-vs-TEED comparison at ~1,944 is **not** available and is not claimed.

## 4. The DexiNed rider — candidate A is NOT falsified, but the evidence is unfavourable for lego

The rider is a near-perfect matched-density control: **1,647 vs 1,640 strokes/frame**.

| at matched density | TEED f=0.40 | DexiNed f=0.40 |
|---|---|---|
| tuned P@1.5 | 0.6535 | **0.6594** (best in table) |
| tuned R@1.5 | **0.4463** | 0.4301 |
| unmatched | 0.0370 | **0.0342** |
| **cut** | **0.0225** | 0.0290 (+29%) |
| P_pop ratio | **12.10x** | 11.36x |
| Frechet ratio | 14.81x | **15.46x** |

Readings, in order of what they license:

1. **DexiNed is a live channel, not a dead one.** It clears the bar at 11.36x. A cross-detector
   agreement rank is therefore not dead on arrival, and my Phase B argument did not overstate
   this: the rider was designed to falsify A cheaply and **it failed to falsify it**.
2. **But its contribution points the wrong way for lego.** DexiNed buys precision (+0.006) at the
   cost of recall (-0.016) and imports 29% more fragmentation at matched density. Lego's binding
   constraint is recall at fixed fragmentation. An agreement rank blending these channels would
   trade in the unfavourable direction here.
3. **It strengthens the "chair-later" call.** DexiNed posts the highest tuned precision of any arm
   measured. Chair's binding constraint is precision, and its whole Contribution B is a precision
   boundary. That is where an agreement rank should be tested if it is tested at all.

## 5. theta >= 30.05 flag (mandatory)

Every lego P/R numeral above is partly credited by the exactly-30.000-degree 12-gon stud
tessellation, whose facet edges sit ~3.2 px apart against a 1.5 px tau. `LEGO_THRESHOLD_AUDIT.md`
banks the sensitivity only for f=1.00 canny: **P@1.5 falls 0.6360 -> 0.3097** and R rises
0.5572 -> 0.6408 at a 30.05-degree GT threshold.

**Per-arm rescores were not computed.** Two consequences must be carried:

- The confound moves all arms in the same direction, so the *relative* ordering in section 1 is
  internally valid.
- But it is **not** neutral across f: raising f puts progressively more ink on smooth stud
  barrels, so the recall gains at f=0.50-0.70 are the **most theta-suspect in the whole table**.
  A middle-band result whose only appeal is recall bought at high f is exactly the result this
  caveat should make us least willing to act on. That reinforces the decision in section 2.

## 6. Calibration — I was wrong

Stated prior before the run: 60% unbounded to f=0.70, 30% knee between 0.50 and 0.70, 10% knee at
0.45-0.50. **The 30% bucket hit.** I over-weighted "unbounded" because TEED's `cut` was flat
across 1,305 -> 1,640 strokes/frame and I extrapolated that flatness. The flatness ended almost
immediately past the last arm I had measured. The lesson for Phase B: a flat mechanism variable
over a 26% density range does not license extrapolation over a 50% one.

## 7. What this establishes / does not

**Establishes.** The evidence-quality curve has a knee, at 1,944-2,221 strokes/frame on lego.
Its cause is `cut`-term fragmentation onset at 1,640-1,944 strokes/frame, partially masked by a
falling `unmatched`. Better evidence moves the ceiling out but does not remove it. DexiNed is a
viable second channel that trades recall for precision and fragments more.

**Does not establish.** (a) That f=0.50 is usable — it misses the frozen recall bar by 0.0003 and
is the most theta-suspect arm. (b) Any tuned-mask temporal cell for f>=0.50 (npz lack
`keep_tuned`). (c) Anything about chair or ficus at these f values. (d) That an agreement rank
fails — the rider did not falsify it, it only made it unattractive for lego.

## 8. Invariants

Manifest **332/332 OK, 0 FAILED**. Shipped jsons and published vector figures untouched (every
arm used a non-empty `--viz_tag`). New artifacts only:
`m1b_stroke_temporal_table_pb1_{teed050,teed060,teed070,dex040}.{json,md}`,
`m1b_vector_lego_pb1{t050,t060,t070,d040}_*.{svg,png}`,
`linelets_lego_{teed050,teed060,teed070,dex040}_test.npz` (symlinks), `logs/pb1_knee.log`,
this file. Not committed.
