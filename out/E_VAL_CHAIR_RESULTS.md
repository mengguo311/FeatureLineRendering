# E-VAL-CHAIR — does the chair precision cost survive an independent split?

**VERDICT: MIDDLE — report, do not act.** But the informative result is not the verdict.

**The chair point I proposed in this campaign, TEED0.5 f=0.30, blows its own precision
allowance on VAL by 2.3x** — a gap of **−0.0452** against the **−0.02** allowance it passes on
TEST (−0.0184). The frozen rule did not select it; it selected **TEED0.5 f=0.22** instead, an
arm with no measured temporal cell.

**Blast radius, stated precisely:** the paper **ships canny f=0.30** on chair. TEED f=0.30 was
*my* proposed standing point from Phase A and was never shipped. This corrects my
recommendation, not the shipped work.

**My prior was wrong.** I priced the precision leg at 0.50 to hold. It failed decisively.

---

## PROVENANCE NOTE (binding, as on lego)

> Chair was in the pre-E-VAL state: a disk-wide query found **zero** chair runs with
> `eval_split != 'test'`, so the chair operating point was selected by reading TEST out of
> ~30 arms. This re-selects on VAL with a rule frozen beforehand. **PARTIAL REMEDIATION, not a
> single look** — all seven arms had already been observed on TEST. Ficus remains the only
> unspent clean set.

## 1. The table

Stage: **SPEC mask** only (chair npz do not store `keep_tuned`). No re-pull. Temporal is the
**banked TEST-orbit** ratio, reported **alongside** and deliberately **not** in the selection
rule, per the E-FMARGIN lesson that the invariant bar must be re-established per orbit.

| arm | spec lin | tuned lin | VAL P | VAL R | TEST P | TEST R | **TEST→VAL ΔP** | TEST-orbit ratio |
|---|---|---|---|---|---|---|---|---|
| canny f=0.30 (shipped) | 16,039 | 15,091 | 0.4787 | 0.7255 | 0.6067 | 0.7077 | **−0.1280** | 10.71x |
| **TEED0.5 f=0.22** (VAL-selected) | 11,890 | 11,140 | **0.4613** | 0.7609 | 0.6091 | 0.7393 | −0.1478 | not measured |
| **TEED0.5 f=0.30** (my proposal) | 15,971 | 14,770 | **0.4335** | 0.8082 | 0.5883 | 0.7985 | −0.1548 | 13.12x |
| TEED0.5 f=0.35 | 18,445 | 16,865 | 0.4165 | 0.8363 | 0.5710 | 0.8297 | −0.1545 | not measured |
| TEED0.5 f=0.40 | 20,795 | 18,838 | 0.4023 | 0.8555 | 0.5537 | 0.8508 | −0.1514 | not measured |
| TEED0.9 f=0.30 | 15,802 | 14,452 | 0.4252 | 0.8136 | 0.5867 | 0.8033 | −0.1615 | not measured |
| DexiNed0.5 f=0.30 | 15,500 | 13,956 | 0.3927 | 0.8157 | 0.5447 | 0.8133 | −0.1520 | 13.41x |

## 2. Verdict against the frozen rule

VAL precision floor = 0.4787 − 0.02 = **0.4587**. Only **one** arm clears it: TEED0.5 f=0.22 at
0.4613, by 0.0026.

| | value |
|---|---|
| VAL-selected arm | **TEED0.5 f=0.22** |
| VAL recall gap | **+0.0354** (CLEAN ≥ 0.0605, LEAK < 0.0303) |
| TEST recall gap | +0.0316 — retention **1.121** |
| **PRECISION GAP — VAL** | **−0.0174** (within the −0.02 allowance) |
| **PRECISION GAP — TEST** | +0.0024 |
| **VERDICT** | **MIDDLE** |

MIDDLE means report and do not act. Two further reasons not to act even if it had cleared:
the selected arm has **no measured temporal cell**, and it sits 0.0026 above a floor that is
itself split-dependent.

## 3. The finding: chair precision is severely split-dependent, and learned detectors more so

Every chair arm loses **0.128 to 0.162** precision moving from TEST to VAL. Compare lego, run
through the identical code path in E-VAL, where the same drop was **0.008 to 0.015**.

| scene | TEST→VAL precision drop |
|---|---|
| lego (E-VAL, 8 arms) | −0.0075 … −0.0151 |
| **chair (this run, 7 arms)** | **−0.1280 … −0.1615** |

An order of magnitude larger. The uniformity across arms, and the fact that lego shows almost
nothing under the same code, is the internal control: **this is a property of chair's splits,
not a bug in the harness.**

And it is not uniform across detectors. Canny drops **least** (−0.1280); every learned detector
drops 0.148–0.162. **TEED's precision is more split-sensitive than Canny's**, which is exactly
why the TEED-minus-canny precision gap widens from −0.0184 on TEST to −0.0452 on VAL and blows
the allowance.

Recall, by contrast, transfers cleanly on chair: canny 0.7077 → 0.7255, TEED f=0.30
0.7985 → 0.8082, and the selected arm's recall gap actually *grows* on VAL (retention 1.121).

**Same qualitative pattern as lego — recall robust, precision fragile — but on chair the
fragility is large enough to invert a shipped-quality decision.** A plausible mechanism is that
chair's VAL views expose more of the floral-fabric region where learned detectors fire hardest,
but that is a hypothesis this run does not test and I am not claiming it.

## 4. Temporal invariant check (alongside only, not in the rule)

**No arm dips below the 10.345x invariant.** All measured cells clear it:

| arm | TEST-orbit ratio | margin over bar |
|---|---|---|
| canny f=0.30 | 10.71x | **+3.5% — thin** |
| TEED0.5 f=0.30 | 13.12x | +26.8% |
| DexiNed0.5 f=0.30 | 13.41x | +29.6% |

No loud flag is warranted. Noting for the record that the shipped canny chair point carries only
3.5% of margin over the invariant, the thinnest of any configuration we have measured on either
scene, and that four of the seven arms have no measured temporal cell at all.

## 5. What this changes

- **My Phase A designation of TEED f=0.30 as chair's standing point is withdrawn.** It is not
  defensible on an independent split: −0.0452 precision against a −0.02 allowance.
- **The shipped chair row is unaffected** — the paper ships canny f=0.30, which is the baseline
  here, not a candidate.
- **The lego result is unaffected.** E-VAL returned CLEAN there with 0.940 recall retention and
  0.79–0.86 precision retention. Chair does not generalise it; chair contradicts the precision
  half of it.
- **The honest cross-scene statement is now:** the TEED evidence win is a *recall* win that
  transfers across splits on both scenes, and a *precision* win only on lego. On chair TEED
  trades, and the trade does not survive an independent split.
- Any future chair operating-point claim needs its precision measured on both splits before it
  is proposed, not after.

## 6. Invariants

Manifest **332/332 OK, 0 FAILED**. Mesh EVAL-ONLY via the banked chair VAL oracle cache. No
re-pull, no stroke set touched, no shipped json or figure modified. Temporal never entered the
selection rule. New artifacts: `scripts/e_val_chair.py`, `out/e_val_chair.json`,
`logs/e_val_chair.log`, this file. Not committed.
