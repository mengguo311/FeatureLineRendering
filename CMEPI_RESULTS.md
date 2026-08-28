# CMEPI — Cross-Model Edge-Prior Invariance

**Question (frozen in `tier1/cmepi_spec.md` before any non-TEED number existed):** the arc's peak
finding is that a FROZEN ZERO-SHOT LEARNED edge prior (TEED/BIPED) buys rankable seeds that move
the held-out M1b f-frontier outward. Is that lift a property of **learned edge priors in general**,
or is it **TEED-specific overfitting**?

Held-out TEST throughout. Mesh EVAL-ONLY. No fine-tuning, no per-scene retuning of any detector.
Nothing committed.

New code, all additive:
`scripts/cmepi_cache_edges.py` (METHOD PATH, mesh-free — pluggable frozen detector, TEED cache
contract), `scripts/cmepi_{m1b,detector_chain,temporal,perview,pv_run}.sh`,
`scripts/cmepi_{table,detector_table,temporal_table}.py` (analysis only),
`--tag`/`--det_name`/`--thrs` on `recall_trackC_detector.py`, `--viz_tag` on
`m1b_stroke_temporal.py`. **No existing behaviour changed**: every added flag defaults to the
historical value. Vendored third-party: `ext/pidinet` (upstream clone, untouched),
`ext/dexined/weights`.

---

## Executive summary

**VERDICT: GO — the lift is reproduced by a non-TEED frozen learned prior. But the honest claim
is narrower than "invariance", and the narrowing is forced by our own data.**

- **What fires the rule.** `DexiNed` reproduces LIFT_P > 0 at **every one of the 5 band f values on
  chair AND on lego, under BOTH estimators, at BOTH thresholds tested** — so the rule fires under
  its strict and loose readings jointly and needs no adjudication. Best chair **+0.0625 interp /
  +0.0817 env** (thr 0.7, the pre-registered VAL-selected arm) against the TEED control's
  +0.0776 / +0.0940; best lego **+0.0335 / +0.0234** (thr 0.5) against TEED's +0.0296 / +0.0202.
  A **598× larger, architecturally unrelated network carries 80–87 % of TEED's chair lift and
  slightly exceeds it on lego. The lift is not TEED's alone.**
- **What is actually demonstrated: invariance across ARCHITECTURE AND CAPACITY at a FIXED TRAINING
  CORPUS — not across training data.** DexiNed is trained on **BIPED, the same corpus as TEED**.
  The one detector with a different corpus, **PiDiNet** (BSDS500-aug + PASCAL VOC Context),
  reproduces the chair lift and **reverses on lego at all three thresholds and both estimators**.
  PiDiNet is therefore exactly the spec's **CONDITIONAL** case and is reported as one. The thing
  that would have made this a cross-family result is precisely the thing that failed.
- **All the discrimination lives in chair; the lego leg of the rule carries no evidence about
  learned-ness.** On lego the *classical* un-blurred Canny beats every learned detector —
  `cannysharplow` **+0.0566 / +0.0477** > DexiNed +0.0335/+0.0234 > TEED +0.0296/+0.0202, and it
  beats TEED per-view on *precision* at t=+6.09, 10/10 views (its paired recall edge is weaker,
  +0.0293, t=+3.81, 9/10). On lego, edge density alone predicts the lift
  (Spearman +0.77, p=0.009) and every arm denser than the M1a Canny is positive while every
  sparser arm is negative. On **chair** the picture inverts: density predicts nothing
  (Spearman −0.37, p=0.33; no 2D feature reaches p<0.09) and every classical arm scores
  −0.15 … −0.23. This reproduces `TEED_GEN_RESULTS.md`'s conditional law unchanged.
- **The chair result survives without any estimator.** DexiNed@0.7 **strictly Pareto-dominates a
  Canny frontier point at all 5 band f and is dominated at none** — higher precision *and* higher
  recall than a real swept Canny operating point, no interpolation, no envelope. `cannysharp` and
  `cannysharplow` are dominated at every f. It also survives jackknifing every Canny frontier
  point, all three evaluation stages, both thresholds, and both f-readings; and it is already
  present at the seed stage and *decays* downstream, so pull/prune did not manufacture it.
- **Two boring explanations refuted, two conceded.** Refuted: **seed count** (`n_seeds` is
  bit-identical across arms at every matched f — every arm re-ranks one identical candidate pool)
  and **estimator manufacture** (the `beyond_canny_Rmax` branch never fires; `LIFT_P_lb ≡
  LIFT_P_env` everywhere). Conceded: **on lego, density/recall does explain it**, and **on chair
  the headline magnitude depends on the extended Canny frontier** — truncating it at f≤0.50 roughly
  halves DexiNed@0.7 to +0.0338/+0.0518 (sign unchanged).
- **The temporal-coherence win is intact, and DexiNed does not regress it — it slightly improves
  it.** All 332 protected published files verify byte-identical (332/332 OK). Chair @240 frames:
  **DexiNed 13.33×**, TEED 13.12×, PiDiNet 12.90×, Canny 10.71×. On lego every learned arm beats the classical `cannysharplow`, which is the only arm that regresses (9.67× vs Canny's 11.61×).
- **The matched-budget per-view test (10 TEST views, paired) sharpens both halves.** On **lego**
  DexiNed **strictly dominates Canny on both precision and recall in 10/10 views** (segP +0.0359,
  t=+9.08) at a margin that lands on top of TEED's (+0.0364, t=+8.15) — the swap costs essentially
  nothing, with no estimator involved. *(Both are measured against Canny; no DexiNed-vs-TEED paired
  test was run, so this is a comparison of two effect sizes, not a test of their difference.)* On **chair** every CMEPI arm *loses* precision
  at matched budget (DexiNed@0.7 segP −0.0187, t=−4.53, **0/10 views**) while gaining recall
  (+0.0756, t=+5.97, 10/10); **TEED is the only arm that gains on both axes**. The chair lift of a
  non-TEED prior is therefore a better recall-for-precision exchange rate than the f-dial offers,
  not a win at equal budget.
- **The single biggest weakness, stated up front:** DexiNed's chair lift **does not replicate on
  the other 10-view split at the M1a seed stage** — VAL is negative at all four thresholds and
  every f (best −0.0151) and flips to +0.0343 on TEST, while TEED is stable across splits
  (+0.0539 VAL / +0.0665 TEST). No M1b frontier was ever computed on VAL for **any** arm, control
  included, so the M1b headline is test-only across the board. Chair split-to-split swings at the
  seed stage are the same size as the chair effect.

## 0. Reproduction controls, run before any CMEPI number was read

| control | result |
|---|---|
| **New pluggable cacher reproduces the published TEED cache** — `scripts/cmepi_cache_edges.py --det teed --scene chair` vs `out/teed_edges_chair` | **100/100 views bit-identical**, `max\|delta\| = 0.00000000` on both `native` and `ms` |
| **Canny DP self-check** inside `recall_trackC_seeds.py` (recomputed Canny photometric DT vs the cached `final_evid_<scene>.npz`) | `max\|d\|=0.000000 mean\|d\|=0 frac>1e-3=0.000000` on **both** scenes |
| **The Canny M1a ranking vector, regenerated inside the CMEPI run, is bit-identical** to the published one | `finalscore_overall_{chair,lego}__canny.npy` still match their pre-experiment sha256 (and equal the published `finalscore_overall_<scene>.npy`) |
| **Published TEED numbers reproduce exactly** | chair teed05 best LIFT_P **+0.0776 interp / +0.0940 env**; lego teed best **+0.0346 / +0.0223** in `[0.22,0.50]` — identical to `TEED_GEN_RESULTS.md` |
| **Published 2D detector numbers reproduce exactly** | lego TEED nms@0.5: R_GT 0.505, dRecall **+0.329** (`TEED_GEN_RESULTS.md` prints +0.330, a
difference-of-rounded-values artifact of 0.505−0.175; the unrounded value is +0.32919), P_GT 0.683,
rec_miss 0.428, 14,842 px/view; canny_m1a 0.175 / 0.637 / 8,102 — identical to `TEED_GEN_RESULTS.md` |
| **Nothing published was perturbed** | `sha256sum -c out/CMEPI_protected_manifest.sha256` → **332/332 OK** (manifest built 14:06, every CMEPI M1b json written 14:20–14:40) |
| **Independent re-implementation of the LIFT_P estimator** (written from scratch, `teedgen_verdict.py` never imported) | **749 numbers compared, max abs diff 0.000e+00** |
| **Downstream pipeline bit-identical across arms** | diffing `args` across all 59 chair / 78 lego arm jsons: the *only* keys that differ are `{f, score, tag}`. The other 36 (`edge sharp`, `gate`, `steps 100`, `lr 0.35`, `delta_max 5.0`, `len_thr 0.9`, `pull_split train`, `eval_split test`, …) are identical |

Two files inside the protected manifest were *rewritten* during the run — the two
`finalscore_overall_<scene>__canny.npy` — and both still hash OK. That is a positive
reproducibility datum, recorded here rather than left silent.

**One pre-existing invariant breach was found and repaired.** The eight published stroke-path
figures `out/m1b_vector_{chair,lego}_{A_ours,B_baseline}.{svg,png}` had been overwritten by
earlier experiments (they differed from publication commit `1f023c6` — e.g.
`m1b_vector_lego_A_ours.svg` 278,653 B on disk vs 172,741 B in the commit). They were backed up
to `out/cmepi_backup/vectors_predrift/` and **restored to the published commit**;
`git diff 1f023c6 -- out/m1b_vector_*` is now empty. The root cause — `_dump_vis()` writes those
four names with no tag, so *every* invocation clobbers them — is now guarded by `--viz_tag`
(default `""` reproduces the published names exactly).

---

## 1. The three detectors — and why these three

Every checkpoint is published, frozen, and used zero-shot. Nothing is fine-tuned; no threshold or
weight is tuned per scene. Each detector is run on **its own repository's preprocessing contract**
(read off the originating source, not guessed) — forcing one shared normalisation would measure
robustness-to-wrong-input, which is the opposite of a zero-shot transfer test.

| detector | architecture | parameters | training corpus | contract | ckpt sha256 (16) |
|---|---|---|---|---|---|
| **TEED** *(control)* | TED | **58,910** | BIPED | BGR − [104.007,116.669,122.679], no /255; `sigmoid(model(x)[-1])` | `0322caf70f588355` |
| **DexiNed** | DexiNed | **35,215,245** | **BIPED** *(same as TEED)* | BGR − [103.939,116.779,123.68], no /255; single fused logit tensor, sigmoid outside | `bd4c603ef71113b4` |
| **PiDiNet** | PiDiNet (carv4, sa, dil) | **710,149** | **BSDS500-aug + PASCAL VOC Context** *(different)* | RGB /255 + ImageNet mean/std; `net(x)[-1]`, **sigmoid already applied inside** | `80860ac267258b5f` |

This is a two-axis design, and it is the reason the result can be scoped rather than just asserted:

- **DexiNed isolates ARCHITECTURE AND CAPACITY.** Same training corpus as TEED, 598× the
  parameters, entirely different network. If it reproduces the lift, the effect is not about the
  TED architecture or about 58K parameters being uniquely lucky.
- **PiDiNet isolates TRAINING CORPUS TOO.** Neither the architecture nor the data is shared with
  TEED. If *it* reproduces the lift, the effect is not about BIPED at all.

The M1a score vectors bear this out independently of any frontier number: **the two BIPED-trained
detectors cluster and the differently-trained one does not.** Spearman ρ against the published
TEED score on chair — DexiNed 0.843–0.917 across thresholds, PiDiNet 0.824–0.872, with
ρ(TEED, canny) = 0.843 for reference. No two of the 16 new score vectors are byte-identical, and
none equals the TEED or the Canny score.

**A stronger "the BIPED-trained detectors cluster" claim does NOT survive checking and is
withdrawn.** Recomputed on chair: within-detector adjacent-threshold ρ spans **0.891–0.985**
(DexiNed 0.7↔0.9 = 0.891, 0.3↔0.5 = 0.985) while cross-detector ρ spans **0.824–0.917**
(DexiNed@0.7↔TEED = 0.917, PiDiNet@0.9↔TEED = 0.824). These **overlap** — the largest
cross-detector similarity (0.917) exceeds the smallest within-detector one (0.891) — so the M1a
score vectors do **not** separate by training corpus. The architecture-vs-corpus decomposition in
this report rests on the frontier results alone, not on score-vector similarity.

Caching cost (100 views × 2 scales, one A6000): TEED 112 ms/view, PiDiNet 218–222, DexiNed 378–382.

---

## 2. What was held bit-identical, and what the swap actually touches

The cache contract is byte-compatible with the TEED cache — white-composited RGBA over the same
background the 3DGS was trained with, two scales (1.0 and 0.64 = 512 px, TEED's training
resolution) quantised by the identical `int(round(H*s/8))*8` rule, `native` = the 1.0 map, `ms` =
elementwise max, raw probability (no per-image contrast stretch, which would not be comparable
across views), float16, `v<view:03d>.npz`, all 100 views. That compatibility is what lets
`final_recipe.set_edge_source(source="teed", cache=<new dir>)` read it with **zero code change**.

**Scope the claim honestly: the learned detector enters the pipeline in exactly one place.** It
feeds the M1a photometric distance transform, hence the per-gaussian ranking vector passed as
`--score`. It does **not** feed the M1b DT-pull field, which is built with `--edge sharp` (a Canny
edge map) in **every** arm including the CMEPI ones. This is a **learned seed-ranker** result, not
a learned-edge-pipeline result.

---

## 3. Protocol — thresholds selected on chair VAL, transferred to lego unchanged

`key=native` is fixed for every detector, matching the TEED headline arm, so **threshold is the
only tuned degree of freedom**. It was selected on **chair VAL only** (seed-level M1a f-frontier,
`out/trackC_seeds_chair_cmepi.json`) over `thr ∈ {0.3, 0.5, 0.7, 0.9}` and then transferred to
lego **unchanged** — exactly what TEED did (chair VAL picked 0.5; lego reused 0.5 zero-shot).
Selected: **PiDiNet 0.9, DexiNed 0.7**. The nominal **0.5** arm is also run on both scenes for
direct parity with the published TEED headline, and lego additionally gets PiDiNet 0.7 (its own
VAL pick) as a sensitivity arm.

| chair VAL, seed-level best LIFT_P | thr 0.3 | thr 0.5 | thr 0.7 | thr 0.9 | selected |
|---|---|---|---|---|---|
| PiDiNet | −0.0207 | +0.0024 | −0.0159 | **+0.0129** | **0.9** |
| DexiNed | −0.0300 | −0.0255 | **−0.0151** | −0.0194 | **0.7** |
| *TEED (published, same measure)* | — | *+0.0682* | — | — | — |

**This must be read as a weakness, not a strength.** Every DexiNed threshold is *negative* at every
f on the chair-VAL M1a seed measure, against the TEED control's +0.0682 — the detector that
carries the GO verdict was selected as the least-negative of four negatives, and showed **no
val-side lift at the stage where val evidence was taken**. It is not a protocol violation (the M1a
seed stage is not the M1b post-pull stage, and the selection never saw TEST), but **no M1b
frontier was computed on val for any arm, control or CMEPI** — the M1b headline is test-only
across the board, for the published TEED result as much as for these.

---

## 4. 2D detector metric, before any pipeline

`scripts/recall_trackC_detector.py`, tau=2 (the script's `TAU_MAIN`, the tau every chair go/no-go
number was quoted at), same mesh oracle, same GT crease set (chair 228,079 @30°, lego 971,793 —
identical to the published run), all arms NMS-thinned so stroke width is not a confound.
`rec_miss` = fraction of the M1a-Canny miss-set recovered.

**chair, held-out TEST**

| arm | R_GT | dRecall | P_GT | Pdrop | rec_miss | px/view | FP occ | FP fold | FP hall | P_line |
|---|---|---|---|---|---|---|---|---|---|---|
| canny_m1a *(defines the miss-set)* | 0.326 | — | 0.531 | — | — | 5,058 | 0.514 | 0.142 | 0.344 | 0.839 |
| **TEED nms@0.5** *(published control)* | 0.628 | +0.302 | 0.510 | +0.040 | **0.515** | 7,728 | 0.447 | 0.127 | 0.426 | 0.792 |
| TEED nms@0.9 *(published)* | 0.524 | +0.197 | 0.534 | −0.005 | 0.390 | 6,038 | 0.557 | 0.132 | 0.311 | 0.855 |
| **DexiNed nms@0.7** *(headline)* | 0.537 | +0.211 | 0.474 | +0.107 | **0.418** | 7,112 | 0.435 | 0.110 | 0.455 | 0.761 |
| DexiNed nms@0.5 | 0.571 | +0.245 | 0.440 | +0.172 | 0.457 | 8,131 | 0.364 | 0.106 | 0.530 | 0.703 |
| **PiDiNet nms@0.9** *(headline)* | 0.233 | **−0.093** | 0.486 | +0.085 | **0.121** | 3,025 | 0.821 | 0.058 | 0.121 | 0.938 |
| PiDiNet nms@0.5 | 0.371 | +0.044 | 0.417 | +0.215 | 0.247 | 5,330 | 0.489 | 0.082 | 0.429 | 0.750 |
| *cannysharplow (0,20,60)* | 0.961 | +0.635 | **0.229** | **+0.569** | 0.946 | 40,894 | 0.079 | 0.073 | 0.848 | 0.347 |

**lego, held-out TEST**

| arm | R_GT | dRecall | P_GT | Pdrop | rec_miss | px/view | FP occ | FP fold | FP hall | P_line |
|---|---|---|---|---|---|---|---|---|---|---|
| canny_m1a *(defines the miss-set)* | 0.175 | — | 0.637 | — | — | 8,102 | 0.726 | 0.068 | 0.206 | 0.925 |
| **TEED nms@0.5** *(published control)* | 0.505 | +0.329 | 0.683 | **−0.073** | **0.428** | 14,842 | 0.565 | 0.129 | 0.306 | 0.903 |
| TEED nms@0.9 *(published)* | 0.407 | +0.232 | 0.662 | −0.039 | 0.321 | 11,811 | 0.624 | 0.102 | 0.274 | 0.907 |
| **DexiNed nms@0.7** *(headline)* | 0.356 | +0.180 | 0.657 | **−0.031** | 0.273 | 10,409 | 0.665 | 0.098 | 0.238 | 0.918 |
| DexiNed nms@0.5 | 0.406 | +0.231 | 0.670 | **−0.052** | 0.325 | 11,696 | 0.636 | 0.109 | 0.255 | 0.916 |
| **PiDiNet nms@0.9** *(headline)* | 0.069 | −0.107 | 0.419 | **+0.342** | 0.025 | 3,964 | 0.797 | 0.030 | 0.173 | 0.900 |
| PiDiNet nms@0.5 | 0.225 | +0.049 | 0.566 | +0.111 | 0.151 | 7,885 | 0.657 | 0.065 | 0.278 | 0.879 |
| *cannysharplow (0,20,60)* | 0.893 | +0.718 | 0.751 | −0.180 | 0.874 | 42,169 | 0.374 | 0.239 | 0.387 | 0.904 |

Two things to read off, one of which corrects a tempting over-claim:

1. **DexiNed behaves like TEED at the 2D level too** — on lego its precision goes *up* against the
   arm it replaces (−0.031/−0.052 drop, i.e. a gain), the same "adding recall buys purity on lego"
   signature TEED shows (−0.073). PiDiNet@0.9 on lego does the opposite (+0.342 drop).
2. **The tempting claim "the lift is independent of 2D recall" is NOT supported and is not made
   here.** PiDiNet@0.9 on chair does have negative dRecall (−0.093) and 12.1 % miss-set recovery
   yet still scores +0.0263 / +0.0306 at M1b — but across the *learned* chair arms the lift orders
   almost perfectly with recovery: **Spearman(rec_miss, best LIFT_P) = +0.943** over the six
   TEED/DexiNed/PiDiNet arms. *(Arm-set matters and is stated rather than glossed: including
   `union05`, which is also a learned-derived arm, drops it to +0.52, p=0.23; §6(a)'s density
   analysis uses the wider 9-arm set.)* The counterexamples are the two classical arms —
   `cannysharplow` (94.6 % recovery, −0.2265) and `cannysharp` (86.2 % recovery, −0.1700) — both of
   which also collapse 2D precision (P_GT 0.229 / 0.239 vs the learned arms' 0.417–0.534; P_line 0.347
   vs the learned arms' 0.703–0.938).
   **The defensible statement is: lift tracks miss-set recovery bought at adequate 2D precision;
   raw recall alone is not sufficient.** That is a quality-of-recall claim, not recall-independence.

---

## 5. M1b held-out TEST f-frontier — the decisive table

Identical `run_m1b.py` path and identical published-baseline flags for every arm; **only `--score`
differs.** Each arm is scored against the **published** Canny f-frontier already swept and
densified under the same `m1b_<scene>_tc_` prefix (chair 14 points out to f=1.00, lego 16).
Segments headline stage `AFTER pull+prune[tuned+len]`, tau=1.5.

### Reading the two estimators — measured, not assumed

`LIFT_P` interpolates the Canny frontier to the arm's recall; `LIFT_P_lb` uses the Pareto envelope.
**`LIFT_P_lb` is NOT the conservative one here and its name is inoperative:**

- The `beyond_canny_Rmax` lower-bound branch **never fires** — no arm on either scene reaches the
  Canny dial's own R_max (chair closest is 0.0348 short, lego 0.0290). So `LIFT_P_lb ≡ LIFT_P_env`
  everywhere below and **no denominator is ever switched**: the estimator cannot have manufactured
  a lift that way.
- **On chair** the Canny frontier is strictly P-decreasing in R, so the envelope is the **generous**
  estimator (`LIFT_P_lb ≥ LIFT_P` at every row), inflated purely by the coarseness of the Canny
  f-grid. Scoring the Canny arm against *itself* at off-grid recalls gives a null envelope-lift of
  **+0.0009 … +0.0290**. An arm below its own null has not cleared the frontier.
- **On lego** the Canny frontier's P *rises* with R, so the envelope returns the global maximum
  precision for every arm at every f: lego's envelope lift degenerates to "arm precision minus
  Canny's single best precision" and does no recall matching. A self-scoring null there is
  **negative** (−0.0104 … −0.0164 in band, measured as the Canny frontier's own in-band grid points
  minus its global max P), so lego envelope numbers are conservative. **Note the two nulls are
  computed by different procedures and are not directly comparable:** chair's is the per-arm gap
  (`canny_P_at_R` − `canny_P_env_at_R`) over all in-band arm rows. Applying the chair recipe to lego
  gives −0.0062 … −0.0241; applying the lego recipe to chair gives +0.0238 … +0.0290. The sign and
  the conclusion are the same under either recipe.

**Therefore: treat the interpolated column as primary on chair, and require an arm to be positive
on BOTH columns before calling it above the frontier.** Every DexiNed arm, the TEED control, and
PiDiNet@0.5 satisfy that. PiDiNet@0.9 does not (see below).

### chair — LIFT_P per f (interpolated / Pareto-envelope)

Canny frontier: 14 swept f, R ∈ [0.4678, 0.7908], P ∈ [0.3606, 0.7057].

| arm | f=0.50 | f=0.45 | f=0.40 | f=0.35 | f=0.30 | *f=0.22* | *f=0.15* | best in band | n>0 / 5 |
|---|---|---|---|---|---|---|---|---|---|
| **TEED@0.5** *(control)* | +0.0776 | +0.0620 | +0.0607 | +0.0504 | +0.0416 | *+0.0170* | *−0.0078* | **+0.0776** | **5/5** |
| | +0.0940 | +0.0686 | +0.0626 | +0.0529 | +0.0650 | *+0.0260* | *+0.0128* | **+0.0940** | **5/5** |
| **DexiNed@0.7** *(headline)* | **+0.0625** | +0.0595 | +0.0559 | +0.0338 | +0.0182 | *−0.0168* | *−0.0478* | **+0.0625** | **5/5** |
| | **+0.0817** | +0.0774 | +0.0699 | +0.0518 | +0.0348 | *−0.0069* | *−0.0198* | **+0.0817** | **5/5** |
| DexiNed@0.5 | +0.0518 | +0.0430 | +0.0279 | +0.0163 | +0.0004 | *−0.0316* | *−0.0633* | +0.0518 | 5/5 |
| | +0.0686 | +0.0593 | +0.0524 | +0.0351 | +0.0220 | *−0.0196* | *−0.0330* | +0.0686 | 5/5 |
| PiDiNet@0.5 | +0.0389 | +0.0386 | +0.0277 | +0.0226 | +0.0154 | *−0.0065* | *−0.0277* | +0.0389 | 5/5 |
| | +0.0541 | +0.0479 | +0.0361 | +0.0268 | +0.0425 | *+0.0071* | *−0.0007* | +0.0541 | 5/5 |
| **PiDiNet@0.9** *(headline)* | +0.0263 | +0.0130 | +0.0053 | **−0.0013** | **−0.0161** | *−0.0336* | *−0.0416* | +0.0263 | **3/5** |
| | +0.0306 | +0.0211 | +0.0124 | +0.0008 | +0.0129 | *−0.0198* | *−0.0305* | +0.0306 | 5/5 |
| *cannysharp (classical)* | | | −0.1700 | | −0.1746 | *−0.1575* | | −0.1700 | 0/2 |
| *cannysharplow (classical)* | | | −0.2325 | | −0.2265 | *−0.2081* | | −0.2265 | 0/2 |

*(first row per arm = interpolated, second = envelope; italic f are outside the frozen band)*

### lego — LIFT_P per f (interpolated / Pareto-envelope)

Canny frontier: 16 swept f, R ∈ [0.1826, 0.5572], P ∈ [0.5985, 0.6360] — **not a trade-off curve**;
its precision rises *almost* monotonically with f (3 tiny non-increasing steps), so its best point
is essentially "keep everything" — strictly, the max-precision point is **f=0.95 (P=0.6360436)**,
3.2×10⁻⁵ above the f=1.00 endpoint (P=0.6360114); see §10.10.

| arm | f=0.50 | f=0.45 | f=0.40 | f=0.35 | f=0.30 | *f=0.22* | *f=0.15* | best in band | n>0 / 5 |
|---|---|---|---|---|---|---|---|---|---|
| **TEED@0.5** *(control)* | +0.0193 | +0.0219 | +0.0260 | +0.0281 | +0.0296 | *+0.0346* | *+0.0402* | **+0.0296** | **5/5** |
| | +0.0127 | +0.0140 | +0.0174 | +0.0197 | +0.0202 | *+0.0223* | *+0.0245* | **+0.0202** | **5/5** |
| **DexiNed@0.5** | +0.0277 | +0.0312 | +0.0316 | +0.0306 | **+0.0335** | *+0.0307* | *+0.0303* | **+0.0335** | **5/5** |
| | +0.0199 | +0.0226 | **+0.0234** | +0.0216 | +0.0230 | *+0.0182* | *+0.0118* | **+0.0234** | **5/5** |
| **DexiNed@0.7** *(headline)* | +0.0296 | +0.0295 | +0.0305 | +0.0301 | +0.0304 | *+0.0305* | *+0.0296* | **+0.0305** | **5/5** |
| | +0.0218 | +0.0210 | +0.0221 | +0.0208 | +0.0195 | *+0.0175* | *+0.0098* | **+0.0221** | **5/5** |
| PiDiNet@0.5 | −0.0063 | −0.0060 | −0.0091 | −0.0123 | −0.0133 | *−0.0124* | *−0.0068* | −0.0060 | **0/5** |
| | −0.0150 | −0.0159 | −0.0207 | −0.0246 | −0.0270 | *−0.0308* | *−0.0348* | −0.0150 | **0/5** |
| PiDiNet@0.7 | −0.0036 | −0.0046 | −0.0051 | −0.0076 | −0.0077 | *−0.0071* | *−0.0072* | −0.0036 | **0/5** |
| | −0.0126 | −0.0148 | −0.0174 | −0.0198 | −0.0223 | *−0.0277* | *−0.0383* | −0.0126 | **0/5** |
| **PiDiNet@0.9** *(headline)* | −0.0166 | −0.0234 | −0.0281 | −0.0330 | −0.0382 | *−0.0424* | | −0.0166 | **0/5** |
| | −0.0283 | −0.0356 | −0.0430 | −0.0511 | −0.0622 | *−0.0777* | *−0.1003* | −0.0283 | **0/5** |
| *cannysharp (classical)* | +0.0202 | | +0.0258 | | +0.0349 | *+0.0450* | | **+0.0349** | 3/3 |
| *cannysharplow (classical)* | +0.0344 | | +0.0463 | | **+0.0566** | *+0.0697* | | **+0.0566** | 3/3 |

### The f-range where LIFT_P > 0 — including outside the band

| detector / scene | interpolated | envelope |
|---|---|---|
| TEED, chair | {0.22 … 0.50} | {0.15 … 0.50} |
| DexiNed@0.5 & @0.7, chair | **{0.30 … 0.50}** | **{0.30 … 0.50}** |
| PiDiNet@0.5, chair | {0.30 … 0.50} | {0.22 … 0.50} |
| PiDiNet@0.9, chair | {0.40 … 0.50} | {0.30 … 0.50} |
| TEED, lego | {0.15 … 0.70} | {0.15 … 0.70} |
| DexiNed@0.5 & @0.7, lego | **{0.15 … 0.50}** *(every swept f)* | **{0.15 … 0.50}** |
| PiDiNet, all thresholds, lego | ∅ | ∅ |

All ranges are contiguous, with no interior gaps. **The chair result is band-local and this must be
stated:** on chair every CMEPI arm turns negative at f=0.15, and all but one turn negative at
f=0.22 — the exception is PiDiNet@0.5, still **+0.0071 on the envelope** at f=0.22 (but −0.0065
interpolated). The TEED control is positive at f=0.22 on both estimators (+0.0170 / +0.0260) and
at f=0.15 on the envelope (+0.0128), though **TEED too is negative at f=0.15 interpolated
(−0.0078)** — the published caveat that its gain reverses below f≈0.22. **TEED's positive f-range
on chair is still wider than any non-TEED arm's on both estimators.** The band `[0.30, 0.50]` was frozen in the spec
before any number existed, so this is not post-hoc band selection — but it is exactly the region
where the non-TEED lift exists, and under the *previously published* TEED band `[0.22, 0.50]` no
CMEPI arm would be positive at every f.

### Carried fraction of the TEED lift

| scene | arm | interp | carried | envelope | carried |
|---|---|---|---|---|---|
| chair | **DexiNed@0.7** | +0.0625 | **0.80** | +0.0817 | **0.87** |
| chair | DexiNed@0.5 | +0.0518 | 0.67 | +0.0686 | 0.73 |
| chair | PiDiNet@0.5 | +0.0389 | 0.50 | +0.0541 | 0.58 |
| chair | PiDiNet@0.9 | +0.0263 | 0.34 | +0.0306 | 0.33 |
| lego | **DexiNed@0.5** | +0.0335 | **1.13** | +0.0234 | **1.15** |
| lego | DexiNed@0.7 | +0.0305 | 1.03 | +0.0221 | 1.09 |
| lego | PiDiNet@0.5 / @0.7 / @0.9 | −0.0060 / −0.0036 / −0.0166 | −0.20 / −0.12 / −0.56 | −0.0150 / −0.0126 / −0.0283 | −0.74 / −0.62 / −1.40 |

A 598×-larger, architecturally unrelated network trained on the same corpus carries **80–87 %** of
the chair lift and **slightly exceeds** TEED on lego. A network trained on a different corpus
carries **50–58 %** on chair at thr 0.5, but only **33–34 %** at its pre-registered headline thr 0.9
— and **none** on lego at any threshold.

---

## 6. Attempts to refute the DexiNed result

Five boring explanations were tested against the chair leg (the only leg that discriminates
learned from classical). Two are refuted, two are conceded as real limits, one is a residual gap
that cannot be closed without running new arms.

| candidate explanation | verdict | decisive number |
|---|---|---|
| **(a) Edge density** — any detector at that pixel density would do it | **REFUTED on chair, SUPPORTED on lego** | chair Spearman(px/view, LIFT_P) over 9 non-Canny arms = **−0.37 (p=0.33)**; no 2D feature (R_GT, P_GT, P_line, dRecall, rec_miss, FP fractions) reaches p<0.09. Within-detector the direction is inconsistent: TEED denser=better, DexiNed **sparser**=better (0.7 > 0.5). Single counterexample: PiDiNet@0.9 has **0.60× Canny's pixels**, dRecall −0.093, 12.1 % miss-set recovery — and still lifts +0.0263/+0.0306. **On lego the opposite holds**: Spearman = **+0.77 (p=0.009)**, and the separation is exact at Canny's own density — every arm denser than the M1a Canny is positive, every sparser arm negative. |
| **(b) Seed count / f confound** | **REFUTED** | `n_seeds` is **identical across every arm at every matched f, both scenes** (chair 8,533/12,514/17,065/…; lego 14,958/21,939/29,916/…), because `n_seeds = round(f·M)` with M = 56,884 / 99,721. Every arm is a **re-ranking of one identical candidate pool**. The `tuned` prune is a fixed rule (`tau_in=1.0, resid3=True`), applied identically, never per-arm fitted. |
| **(c) The estimator manufactured it** | **REFUTED** | The `beyond_canny_Rmax` lower-bound branch **never fires** (0 arms, both scenes) → `LIFT_P_lb ≡ LIFT_P_env` everywhere, no denominator switched. And the chair result survives with **no estimator at all**: see the Pareto check below. |
| **(c′) The extended frontier inflates the chair magnitude** | **CONCEDED (magnitude, not sign)** | Truncating the Canny frontier at f≤0.50 roughly halves the headline — DexiNed@0.7 **+0.0625/+0.0817 → +0.0338/+0.0518**; DexiNed@0.5 +0.0518/+0.0686 → +0.0163/+0.0351; TEED +0.0776/+0.0940 → +0.0607/+0.0650. Sign never flips. The headline compares arms at f=0.45–0.50 against Canny points at f≈0.55–0.65 (f=0.50 brackets between Canny 0.60 and 0.65; f=0.45 between Canny 0.55 and 0.60), i.e. an **unequal seed budget** — legitimate under "can the f-dial buy this?", but it is not "more precise at the same budget". |
| **(c″) At matched budget DexiNed is not better** | **CONCEDED on chair** | Matched-f dP vs Canny (equal seed count, no interpolation), f=0.30→0.50: DexiNed@0.5 −0.0585,−0.0461,−0.0281,−0.0178,−0.0050 (**negative 5/5**); DexiNed@0.7 −0.0457,−0.0294,−0.0106,+0.0003,+0.0082 (negative 3/5); TEED −0.0155,−0.0038,+0.0104,+0.0157,+0.0204 (negative 2/5). On **lego** DexiNed@0.5 is +0.030…+0.039 at every band f and **strictly dominates** Canny. So on chair the learned prior buys recall at a better exchange rate than the f-dial; it does not buy precision at equal budget. |
| **(d) One-view artefact** | see §8 | 10 TEST views against lifts of +0.02…+0.06. Resolved there by a paired per-view test. |
| **(e) Cherry-picked threshold** | **REFUTED — no TEST leakage** | The VAL rule picked the *worse* TEST arm in **3 of the 4** threshold transfers (PiDiNet chair: picked 0.9, best-on-TEST 0.5; DexiNed lego: transferred 0.7, best-on-TEST 0.5; PiDiNet lego: transferred 0.9, band-best on TEST 0.7 at −0.0036 vs 0.9's −0.0166). DexiNed chair is the only one where VAL picked the better arm — i.e. the selection is, if anything, anti-correlated with TEST. Not load-bearing either way: **both** DexiNed thresholds are 5/5 on both scenes under both estimators, so GO fires whichever is chosen; the threshold only moves the magnitude. |
| **residual gap (not closed)** | — | On chair, "classical" and "density" are **perfectly confounded**: every classical arm ever run is ≥7.1× Canny density (`cannysharp` 7.08×, `cannysharplow` 8.09×), while the learned arms all sit between **0.60× and 2.14×** — so there is **no classical M1b arm anywhere in the ~1×–7× window** the learned arms occupy. Closing it would require creating new arms; that was not done, to avoid polluting the published `m1b_<scene>_tc_*` glob. |

### The estimator-free version of the chair result

Pure Pareto domination against **real swept Canny operating points** — no interpolation, no
envelope, no frontier model:

| chair, band f∈[0.30,0.50] | dominates a real Canny point | is dominated by one |
|---|---|---|
| TEED@0.5 *(control)* | **5/5** | 0/5 |
| **DexiNed@0.7** *(headline)* | **5/5** | **0/5** |
| DexiNed@0.5 | 4/5 | 0/5 |
| PiDiNet@0.5 | 4/5 | 0/5 |
| PiDiNet@0.9 *(headline)* | **1/5** | 0/5 |
| *cannysharp* | **0/2** | **2/2** |
| *cannysharplow* | **0/2** | **2/2** |

Worked example, chair f=0.50: DexiNed@0.7 reaches **P 0.5604 / R 0.7546**, dominating the *actual*
swept Canny points at f=0.50 (0.5522 / 0.7224), f=0.55 (0.5240 / 0.7385) and f=0.60
(0.4997 / 0.7538) — higher on **both** axes than each.

Note this test is harsher on `PiDiNet@0.9` than LIFT_P is: it dominates a Canny point at only
**1 of 5** band f. The estimator-free chair evidence is carried by DexiNed@0.7 (and TEED), not by
the PiDiNet headline arm.

On **lego** the same test is non-discriminating, as everywhere else on that scene: DexiNed
dominates at 5/5 and is dominated at 0/5 — but so do `cannysharp` (3/3, dominated 0/3) and
`cannysharplow` (3/3, dominated 0/3). Lego PiDiNet@0.5 both dominates (5/5) *and* is dominated
(5/5), i.e. it sits inside the frontier's spread rather than beyond it — consistent with its
negative LIFT_P.

### Where the lift is created, and whether it survives the protocol choices

- **Not manufactured downstream.** The chair DexiNed@0.7 lift is already present at the seed stage
  under the M1b protocol (`BEFORE` +0.0826/+0.0948) and **decays** to the headline +0.0625/+0.0817.
  Pull/prune did not create it.
- **Stage robustness.** Band-best interpolated LIFT_P for chair DexiNed@0.7 across the three
  evaluation stages: segments-tuned+len **+0.0625**, segments-spec **+0.0672**, points **+0.0466** —
  sign robust. But under the *points* protocol DexiNed@0.5 is positive at only 2/5 band f and @0.7
  at 3/5, whereas TEED holds 5/5 in all three stages.
- **Jackknife.** Dropping any single Canny frontier point leaves every headline sign intact
  (worst chair DexiNed@0.7 +0.0625; lego DexiNed@0.5 +0.0334; lego PiDiNet stays negative).
- **Split replication (the uncomfortable one).** At the M1a seed stage, where both splits exist,
  **chair DexiNed flips sign** (thresholds in the order 0.3 / 0.5 / 0.7 / 0.9 for both rows):
  VAL −0.0300 / −0.0255 / −0.0151 / −0.0194 — negative at all four thresholds and every f — vs
  TEST −0.0002 / +0.0108 / +0.0343 / +0.0047. TEED is stable
  (VAL +0.0539 → TEST +0.0665 at f=0.30) and every classical Canny is strongly negative on both.
  On **lego** almost every arm replicates across splits to within 0.005 — the exceptions are
  `cannyunblur` (|Δ| 0.0117), `cannysharp` (0.0095) and `dexined_native_0.3` (0.0053), none of them
  a headline arm. This is a different protocol from
  the M1b headline — and no M1b frontier was ever computed on VAL for any arm, control included —
  so it is a flag, not a refutation. It is the single number a hostile reviewer should be handed.

---

## 7. Temporal no-regress

Same trajectory (TEST views 5→15, look-at-corrected orbit), same forward-warp metric, same
BASELINE (naive image-space Canny re-traced independently every frame) for every row. The
published control rows are read from the **published** tables, not recomputed. `P_pop ratio` =
BASELINE / OURS; higher means our strokes flicker less. CMEPI arms are the pre-registered
VAL-selected thresholds, at the same f the published control tables used.

**chair, f = 0.30**

| arm | P_pop OURS (30/60/120/240) | **P_pop ratio** | Fréchet med OURS | Fréchet ratio |
|---|---|---|---|---|
| canny *(published control)* | 0.096 0.079 0.072 0.071 | 8.25× 9.74× 10.43× **10.71×** | 0.322 0.160 0.080 0.040 | 4.29× 8.03× 15.68× 30.84× |
| **TEED** *(published control)* | 0.093 0.068 0.059 0.058 | 8.50× 11.35× 12.85× **13.12×** | 0.347 0.174 0.087 0.043 | 3.99× 7.44× 14.47× 28.36× |
| **DexiNed@0.7** *(CMEPI)* | 0.096 0.068 0.059 **0.057** | 8.25× 11.28× 12.70× **13.33×** | 0.356 0.180 0.090 0.045 | 3.88× 7.20× 14.00× 27.36× |
| PiDiNet@0.9 *(CMEPI)* | 0.097 0.071 0.061 0.059 | 8.09× 10.80× 12.39× **12.90×** | 0.359 0.181 0.091 0.045 | 3.83× 7.16× 13.85× 27.14× |

**lego, f = 0.40**

| arm | P_pop OURS (30/60/120/240) | **P_pop ratio** | Fréchet med OURS | Fréchet ratio |
|---|---|---|---|---|
| canny *(published control)* | 0.234 0.144 0.091 0.062 | 3.44× 5.30× 8.11× **11.61×** | 0.628 0.332 0.171 0.086 | 2.40× 4.20× 7.46× 13.95× |
| **TEED** *(published control)* | 0.230 0.139 0.084 0.059 | 3.49× 5.48× 8.69× **12.10×** | 0.598 0.316 0.162 0.081 | 2.52× 4.42× 7.86× 14.81× |
| **DexiNed@0.7** *(CMEPI)* | 0.223 0.137 0.085 0.062 | 3.60× 5.57× 8.63× **11.67×** | 0.593 0.313 0.160 0.080 | 2.54× 4.47× 7.94× 14.95× |
| PiDiNet@0.9 *(CMEPI)* | 0.220 0.136 0.088 0.060 | 3.65× 5.61× 8.39× **11.90×** | 0.587 0.308 0.158 0.080 | 2.56× 4.53× 8.04× 15.05× |
| ***cannysharplow*** *(published, the lego static winner)* | 0.240 0.148 0.097 **0.074** | 3.35× 5.16× 7.55× **9.67×** | 0.563 0.297 0.152 0.076 | 2.67× 4.70× 8.39× 15.81× |

**No regress on either scene, and the published trade-off reproduces with two new detectors.**

- On chair **DexiNed slightly improves the win** — 13.33× at 240 frames against TEED's 13.12× and
  Canny's 10.71×. PiDiNet is 12.90×, within 2 % of TEED and well above Canny.
- On lego all three learned arms land between 11.67× and 12.10×, against Canny's 11.61×.
- **The decisive row is the last one.** `cannysharplow` — the *classical* arm that beats every
  learned detector on lego's static f-frontier (+0.0566 / +0.0477) — is the **only** arm that
  regresses temporally: **9.67× vs the 11.61× baseline, −17 %**. Both new learned detectors avoid
  that, exactly as TEED does. This reproduces `TEED_GEN_RESULTS.md`'s finding — *the un-blurred
  Canny buys the lego static number and pays for it in temporal coherence* — with two detectors
  that did not exist in that experiment. **On lego the learned prior's argument is temporal, not
  static.**
- Fréchet ratios sit slightly below Canny's for every learned arm on chair (27.1–28.4× vs 30.8×),
  which is the same pattern the published TEED result already showed. **A tempting "they just draw
  more strokes" explanation is wrong here and is not offered:** at chair f=0.30 DexiNed draws
  **fewer** strokes than the Canny arm, not more — 677 vs 754 strokes/frame, 1,056 vs 1,166 in the
  stroke graph. The learned arms trade a little Fréchet stability for the P_pop win they take; the
  P_pop ratio is the metric the published temporal claim is stated in, and on that metric they win.

`--viz_tag` was passed on every run, so the four published
`out/m1b_vector_<scene>_{A_ours,B_baseline}.{svg,png}` figures were untouched; the CMEPI renders
went to `out/m1b_vector_<scene>_cmepi{,L}_{pidinet,dexined}_*`.

---

## 8. Paired per-view significance

Every M1b number above is a **mean over 10 held-out TEST views**, and the per-view spread on chair
is wide relative to the effect — the per-view **paired differences** below span 0.032–0.132
(max−min) with sds of 0.0095–0.0401, against LIFT_P values of +0.02…+0.06 — so a mean difference
could in principle be carried by one or two views. So the orderings are re-read as **paired per-view differences at MATCHED f** (f=0.40, the
middle of the band): same view, same protocol, **same seed count**, only the frozen detector
differs. The published TEED result was quoted with exactly this test, so the comparison is
symmetric. Stage is `pull+prune[spec]` — the stage the saved keep-mask defines — not the headline
`tuned+len` stage; it is the same stage the published per-view numbers used.

**chair, f = 0.40, paired over TEST views {5,15,…,95}**

| A vs canny | segP mean d | t | views A>B | segR mean d | t | views A>B |
|---|---|---|---|---|---|---|
| **TEED@0.5** *(control)* | **+0.0065** | +2.04 | **8/10** | +0.0677 | +5.93 | 10/10 |
| **DexiNed@0.7** *(headline)* | **−0.0187** | −4.53 | **0/10** | **+0.0756** | **+5.97** | **10/10** |
| DexiNed@0.5 | −0.0349 | −8.38 | 0/10 | +0.0717 | +6.10 | 10/10 |
| **PiDiNet@0.9** *(headline)* | −0.0191 | −6.36 | 0/10 | +0.0418 | +8.69 | 10/10 |
| PiDiNet@0.5 | −0.0235 | −4.66 | 0/10 | +0.0555 | +5.19 | 10/10 |

**lego, f = 0.40**

| A vs canny | segP mean d | t | views A>B | segR mean d | t | views A>B |
|---|---|---|---|---|---|---|
| **TEED@0.5** *(control)* | **+0.0364** | **+8.15** | **10/10** | +0.1450 | +7.23 | 10/10 |
| **DexiNed@0.7** *(headline)* | **+0.0359** | **+9.08** | **10/10** | **+0.1216** | **+5.11** | **10/10** |
| DexiNed@0.5 | +0.0379 | +8.85 | 10/10 | +0.1235 | +5.28 | 10/10 |
| PiDiNet@0.9 *(headline)* | −0.0224 | −3.63 | 0/10 | −0.0132 | −0.79 | 5/10 |
| PiDiNet@0.7 | +0.0016 | +0.22 | 6/10 | +0.0534 | +2.24 | 6/10 |
| PiDiNet@0.5 | −0.0018 | −0.24 | 5/10 | +0.0634 | +2.57 | 6/10 |

This is the sharpest result in the experiment, and it cuts both ways.

- **On lego, DexiNed strictly dominates Canny on BOTH axes in 10 out of 10 views, at a margin that
  lands on top of TEED's.** segP +0.0359 (t=+9.08) vs TEED's +0.0364 (t=+8.15); segR +0.1216
  (t=+5.11) vs +0.1450. **Both are paired against Canny; no DexiNed-vs-TEED paired test was run**,
  so this is two effect sizes coinciding, not a measured test of their equivalence. At **equal seed budget**, with no estimator and no frontier model,
  the swap TEED→DexiNed costs essentially nothing. This is the strongest evidence in the report
  that the lift is a property of the learned prior rather than of TEED.
- **On chair every CMEPI arm loses precision at matched budget — significantly, in 0 of 10 views —
  and gains recall in 10 of 10.** DexiNed@0.7: segP **−0.0187 (t=−4.53)**, segR **+0.0756
  (t=+5.97)**. **TEED is the only arm that gains on both axes** (segP +0.0065), and even that is
  weak (t=+2.04, 8/10). So the chair LIFT_P of the non-TEED detectors is **entirely a recall gain
  converted through the f-frontier**: they buy recall at a better exchange rate than the f-dial,
  they do not beat Canny at equal budget. This is consistent with §6's matched-f dP and must be
  stated whenever the chair number is quoted.
- **PiDiNet's lego reversal is significant, not noise.** At its headline threshold it is worse than
  Canny on both axes (segP −0.0224, t=−3.63, 0/10; segR −0.0132, 5/10); at 0.5 and 0.7 it is
  precision-neutral with a weak recall gain (t=+2.24 to +2.57, only 6/10 views).
- **The recall gains are large and unambiguous everywhere** — 10/10 views with t between +5.1 and
  +8.7 for every learned arm on chair. Whatever else is in dispute, the learned priors reliably
  reach GT crease geometry the blurred M1a Canny does not.

---

## 9. The verdict, against the rule frozen before any number existed

> **GO (invariance CONFIRMED)**: at least ONE non-TEED learned detector reproduces LIFT_P>0 for
> f in [0.30,0.50] on chair AND non-negative best-LIFT_P on lego.
> **NO-GO (TEED-specific)**: all non-TEED learned detectors give LIFT_P<=0 across f in [0.30,0.50]
> on chair.
> **CONDITIONAL**: lift holds on chair but reverses on lego for all detectors.

| leg | evidence | fires? |
|---|---|---|
| **GO** | **DexiNed at both thresholds**: chair 5/5 band f positive under **both** estimators (best +0.0625/+0.0817); lego 5/5 positive under **both** (best +0.0335/+0.0234). Satisfies the "at some f" and "at every f" readings jointly, and survives requiring both estimators. | **YES** |
| NO-GO | 4 of 4 chair-run non-TEED arms are positive somewhere in band | no |
| CONDITIONAL *(global)* | DexiNed does not reverse on lego | no |
| **CONDITIONAL *(PiDiNet alone)*** | chair positive at every band f (thr 0.5); lego negative at every band f, both estimators, all three thresholds | **YES — reported as a per-detector result** |

**==> GO fires, carried by DexiNed. CONDITIONAL fires for PiDiNet alone.**

The rule application is robust to every reading and estimator combination tested: the strict
reading ("positive at every band f, under both estimators, on both scenes") returns the same two
DexiNed arms as the loose one ("positive at some f, under either estimator"); jackknifing any
single Canny frontier point leaves every headline sign intact; the pre-registered VAL-selected arm
(DexiNed@0.7) is itself a carrier, so the result does not depend on picking the best-on-TEST
threshold; and on lego the matched-budget paired per-view test puts DexiNed level with TEED and
above Canny on both axes in 10/10 views (t=+9.08).

**But "invariance CONFIRMED" is the wrong headline for what this shows, and the spec's own wording
should not be quoted without the three narrowings the data forces:**

1. The carrier **shares TEED's training corpus** (BIPED). What is demonstrated is invariance across
   **architecture and capacity**, 58,910 → 35,215,245 parameters. The detector that would have
   demonstrated corpus-invariance is the one that reversed.
2. **The lego leg of the rule carries no evidence about learned-ness** — a classical un-blurred
   Canny passes it harder than any learned detector (+0.0566/+0.0477 vs DexiNed's +0.0335/+0.0234),
   and on lego edge density alone predicts the lift (Spearman +0.77, p=0.009). **All the
   learned-vs-classical discrimination lives in chair.** What the lego leg *does* show, via §7, is
   that the classical winner is the only arm that pays for it in temporal coherence.
3. **On chair the non-TEED lift is a recall-for-precision exchange rate, not a win at equal
   budget** — at matched f every CMEPI arm is precision-negative in 0/10 views (§8), and only TEED
   gains on both axes.

The defensible statement is therefore: **the TEED lift is reproduced by a second, architecturally
unrelated, 598×-larger frozen zero-shot prior trained on the same corpus, at 80–87 % of its
magnitude on chair and 103–115 % on lego, with no temporal regression — so it is not TEED-specific.
Whether it is corpus-general remains open, and the one test of that available here failed.**

---

## 10. Caveats that must travel with this result

1. **Scope.** Invariance is demonstrated **across detector architecture and capacity (58,910 →
   35,215,245 parameters) at a fixed training corpus (BIPED)**. It is **not** demonstrated across
   training corpora: the only detector with different training data reverses on lego.
2. **PiDiNet is CONDITIONAL, not GO** — the spec's CONDITIONAL leg is satisfied exactly, restricted
   to PiDiNet, and that is the honest per-detector finding even though the global rule returns GO.
3. **PiDiNet's "positive at every band f on chair" belongs to threshold 0.5, not to the
   pre-registered headline 0.9.** At 0.9 the interpolated estimator is **3/5** (−0.0161 at f=0.30,
   −0.0013 at f=0.35). Its 5/5 under the envelope is an artefact of Canny-grid discretisation: at
   f=0.30 the arm's recall is 0.639646 and a Canny grid point sits at 0.639620 — **2.6×10⁻⁵ below
   it** — so the envelope's `r >= R` test skips that point and falls to the next, flipping the
   value from −0.0161 to +0.0129. The envelope estimator is discontinuous at Canny grid points and
   can be flipped by a 26-ppm recall perturbation.
4. **On lego the lift is not learned-prior-specific.** The largest lego band lift belongs to a
   *classical* arm — `cannysharplow` +0.0566/+0.0477, beating TEED (+0.0296/+0.0202) and DexiNed
   (+0.0335/+0.0234). `cannysharp` also beats both. **Only chair discriminates learned from
   classical** (there the same two arms score −0.15 … −0.23). This carries forward
   `TEED_GEN_RESULTS.md`'s conditional law unchanged: learned selectivity is required where native
   Canny purity is low (chair 0.28) and optional where it is high (lego 0.66).
5. **The chair lift is band-local.** Every CMEPI arm is negative at f=0.15, and all but one at
   f=0.22 (PiDiNet@0.5 is +0.0071 on the envelope there, −0.0065 interpolated). TEED is positive at
   f=0.22 on both estimators and at f=0.15 on the envelope — but **TEED is also negative at f=0.15
   interpolated (−0.0078)**, which is its own published caveat, not a CMEPI-specific one.
6. **`LIFT_P_lb` is the generous estimator on chair and degenerate on lego** (see §5). Do not read
   it as a conservative bound in this table.
7. **Val asymmetry, and the chair seed-stage sign flip.** DexiNed's chair-VAL M1a seed lift is
   negative at **every** threshold and every f (best −0.0151) against the TEED control's +0.0682 —
   thr 0.7 was selected as the *least negative of four negatives*. At the same seed stage it flips
   to **+0.0343 on TEST**, while TEED is stable across splits (+0.0539 → +0.0665). Chair
   split-to-split swings there are the same size as the chair effect. **No M1b frontier was ever
   computed on val — for any arm, control included** — so the M1b headline is test-only
   throughout, for the published TEED result as much as for these.
7b. **The chair headline magnitude is frontier-dependent, and matched-budget precision is not
   won.** Truncating the Canny frontier to f≤0.50 roughly halves DexiNed@0.7 (+0.0625/+0.0817 →
   +0.0338/+0.0518; sign unchanged). At **matched f** — equal seed count, no interpolation —
   DexiNed@0.7 is *negative* at 3 of 5 band f on chair (−0.0457 at f=0.30). The chair claim is
   "buys recall at a better exchange rate than the f-dial", not "more precise at the same budget".
   On lego, by contrast, DexiNed@0.5 dominates Canny at matched f at every band f (+0.030…+0.039).
7c. **`dexined_native_0.5`'s chair "every f" claim hangs on 4×10⁻⁴** (f=0.30 interp = +0.0004).
   The every-f reading should be quoted from the pre-registered carrier `dexined_native_0.7`
   (+0.0182 there), not from 0.5.
7d. **A nominal threshold is not a matched operating point across detectors.** TEED's raw sigmoid
   floors at ≈0.4377 and never approaches 0; DexiNed and PiDiNet span the full [0,1]. "All at 0.5"
   would compare different operating points, which is why the threshold was swept and selected on
   VAL rather than fixed at TEED's value.
8. **The swap is a seed-ranker swap.** The learned detector enters only the M1a ranking vector; the
   M1b DT-pull field is a Canny edge map (`--edge sharp`) in every arm.
9. **Ten TEST views, and the matched-budget precision loss on chair.** Per-view paired differences
   on chair span 0.032–0.132 (sd 0.0095–0.0401) against lifts of +0.02…+0.06. *(An earlier draft
   quoted a per-view absolute spread of "0.05–0.12"; that figure is not reproducible from any file
   on disk — `cmepi_perview_*.json` stores only paired differences — so it has been replaced with
   what the files actually contain.)* The paired test (§8) resolves it: on lego DexiNed beats
   Canny on both axes 10/10 views (t=+9.08), but **on chair every CMEPI arm is precision-negative
   at matched f in 0/10 views** while gaining recall 10/10. Only TEED gains on both axes, and only
   weakly (t=+2.04, 8/10). Never quote the chair LIFT_P without this.
10. **A ±0.0001 discrepancy exists in `TEED_GEN_RESULTS.md`'s lego envelope table (line 244)** — 4
    of 6 cells differ from the current files in the 4th decimal (e.g. f=0.50 published +0.0128 vs
    +0.0127). Cause identified: that table was computed against a Canny frontier lacking the f=0.95
    point, whose P=0.636044 raises the envelope by 0.000032 over f=1.00's 0.636011. The published
    doc's parenthetical "the lego numbers are unchanged by densification" is off by that amount.
    Immaterial to every conclusion; recorded rather than left silent. **No published file was
    edited.**

---

## 11. Artefacts

| file | contents |
|---|---|
| `out/cmepi_table.json` | per-f LIFT_P (both estimators) for every arm, both scenes, band statistics, carried fractions, the verdict |
| `out/cmepi_detector_table.json` | the 2D detector metrics of §4 |
| `out/cmepi_temporal_table.json` | the temporal no-regress table of §7 |
| `out/cmepi_perview_{chair,lego}.json` | the paired per-view test of §8 |
| `out/trackC_seeds_{chair,lego}_cmepi.json` | seed-level VAL/TEST frontiers used for threshold selection |
| `out/trackC_detector_{chair,lego}_cmepi_{pidinet,dexined}.json` | raw 2D detector runs |
| `out/cmepi_cache_{pidinet,dexined,teed}_{chair,lego}.json` | cache provenance: params, ckpt sha256, contract, runtime, per-view stats |
| `out/{pidinet,dexined}_edges_{chair,lego}/` | the cached probability maps, 100 views each |
| `out/cmepi_arms_{chair,lego}{,_provenance}.json` | the arm definitions and their frozen-zero-shot provenance |
| `out/m1b_{chair,lego}_tc_{pidinet,dexined}_native_*_f*.json` + `linelets_*` | the 63 M1b arms |
| `out/cmepi_sample_{pidinet,dexined,teed}_{chair,lego}_v{0,5,25}.png` | {RGB \| Canny \| detector native \| detector ms} panels |
| `out/CMEPI_protected_manifest.sha256` | the 332 published files, hashed before the run |
| `out/cmepi_backup/preflight/` | file-level backup of all 332 (the manifest gives detection, not recovery) |

---

## 12. Final integrity check

Run after every CMEPI artefact was written:

```
$ sha256sum -c out/CMEPI_protected_manifest.sha256      ->  332/332 OK, 0 FAILED
$ git diff --stat 1f023c6 -- out/m1b_vector_             ->  (empty)
$ ls out/m1b_{chair,lego}_tc_*.json | grep -cv '_f[0-9]' ->  0
```

Four tracked source files differ from publication commit `1f023c6`, all pre-dating this
experiment except the one flag added here, and all default-preserving:
`scripts/explore/syn/final_recipe.py` (+205, the `EDGE_SOURCE` switch, default `"canny"`),
`scripts/run_m1b.py` (+13, `--score` with `SCORE_OVERRIDE=None`),
`scripts/m1b_stroke_temporal.py` (+44, incl. this experiment's `--viz_tag`, default `""`),
`src/mesh_oracle.py` (+37/−22, `MESH_ORACLE_MAX_ELEMS` chunking and OOM-halving — bit-neutral by
construction, `scatter_reduce "amin"` is order-independent, and both TEST-split oracle caches
already existed so it never executed here). The manifest protects **outputs, not code**; this
paragraph is the code half of the same claim. **Nothing was committed.**
