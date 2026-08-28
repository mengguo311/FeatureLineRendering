# CONDLAW — the Conditional Law as paper Result 2, frozen to one scalar per scene

**Status: GO — CONDITIONAL LAW CONFIRMED** (frozen gate, `condlaw_spec.md`).
Analysis/diagnostic only. No method-path file changed, no retraining, mesh read solely as
`mesh_oracle` for eval/labels, held-out TEST throughout. Protected temporal manifest
re-verified **332/332 OK** (`sha256sum -c out/CMEPI_protected_manifest.sha256`; the file has
366 lines = 332 hashes + 34 comment lines).

---

## The scalar

**DRR@80** = Distractor Rejection Rate at >=80% TrueCrease recall.

```
recall(t)    = frac( TrueCrease scored >= t )        non-increasing step function
rejection(t) = frac( Distractor scored <  t )
t*           = max{ t : recall(t) >= 0.80 }          maximises rejection s.t. the constraint
DRR@80       = rejection(t*)
```
Computed exactly by sweeping every observed score (`scripts/condlaw_drr.py:drr_at_recall`) —
no interpolation, no tie fudging. Achieved recall is reported beside every value and is
0.8000x in every row.

### CORRECTION to the spec's calibration sentence
`condlaw_spec.md` states *"DRR@80 = 0.50 means chance"*. **That is wrong** — it is the AUC
convention, not this metric's. A statistic with no class information has a diagonal ROC, so
at TPR 0.80 the FPR is also 0.80 and specificity = **0.20**.

This was **measured, not asserted**: permuting the class labels within the pooled scored
population gives a null mean of **0.1993–0.2007** across all seven lego signals
(`out/condlaw_lego_null.json`) and all six chair rows (`out/condlaw_chair_null.json`),
95% null band ~[0.186, 0.214].

**Chance floor = 0.200.** The correction does not flip either gate, but it does change how
lego is described — see the honest statement below.

---

## Result 2 — the two-row table

| scene | class-contrast source | statistic | DRR@80 (mesh arm) | DRR@80 (2DGS arm) | AUC | n_TrueCrease | n_Distractor |
|---|---|---|---|---|---|---|---|
| **chair** | mesh-FLAT(<5°) printed fabric **vs** mesh-SHARP(>20°) crease, Canny-edge pixels, TEST views {5,15,…,95} | rendered-normal ribbon (`theta_normal`) | **N/A** — mesh arm has no normal buffer; on `theta_depth` it is **1.000 but circular** (the classes are *defined* by that statistic) | **0.9858** [0.9848, 0.9866] | 0.9757 | 39 564 | 134 805 |
| **lego** | TrueCrease (GT-crease dist ≤1.5 px) **vs** DecalDistractor (>3.0 px **and** TEED>0.5), linelets, TEST views {5,15,…,95} | mesh dihedral / mesh normal-dispersion | **0.5123** [0.4976, 0.5281] (dihedral) · **0.1691** [0.1570, 0.1841] (dispersion) | 0.3249 (surfel dihedral) · 0.2826 (surfel dispersion) | 0.3964 / 0.4675 | 28 826 | 3 814 |

Bracketed = 95% stratified-bootstrap CI (400 resamples, seed 20260828).
Chance floor for every cell = **0.200**.

**Sources.** chair → `out/condlaw_chair_test.json` + `out/condlaw_chair_test.npz`,
CIs `out/condlaw_chair_null.json`. lego → `out/diag2dgs_lego_test.npz` (pre-existing) via
`out/condlaw_lego_drr.json`, CIs/null `out/condlaw_lego_null.json`.

---

## Chair — provenance, and why it had to be recomputed

The published *"normal-theta AUC 0.967"* (`PLAN1_RESULTS.md`, STEP A) lives in
`out/2dgs_falsify_chair_full.json` at `refined / 2DGS[default] / sharp / theta_normal`
(auc **0.9668167777092631**, n_fab 83109, n_cre 28688). Two problems blocked reading DRR@80
off it:

1. **No per-locus arrays exist.** `scripts/explore/gate_falsify_2dgs.py` writes only summary
   percentiles (`json.dump`, line 509); it contains no `np.save`/`savez` at all. An
   exhaustive sweep of `out/`, `cache/`, `scripts/explore/` found no chair artifact holding
   the continuous `theta_normal` per locus. The nearest, `cache/hybrid_step1_chair.npz`,
   holds VAL-split M1a *seeds* (17 065) with `mesh_theta` and labels, but the normal-ribbon
   signal survives there only as 240 **thresholded boolean** arrays → at best a 5-point ROC.
   `cache/plan1_chair_2dgs_chair_patch_sharp_tg12_dl2_hp_v80.npz` is a raw depth/fg render
   cache with no labels.
2. **The published views are not the held-out split.** That script picks views with
   `np.linspace(0, 99, 8)` → `[0,14,28,42,57,71,85,99]`. Against frozen `src/view_split.py`
   (TEST = {5,15,…,95}, VAL = {0,10,…,90}), **six of those eight are TRAIN views** and only
   view 85 is TEST. The published 0.967 is therefore largely in-sample.

So `scripts/condlaw_chair_test.py` re-runs the diagnostic — **pure inference**, no training —
importing the estimator, arms, labelling and refinement thresholds from
`gate_falsify_2dgs` **verbatim**, changing only (a) the view list and (b) an array dump.

**Faithfulness check (mandatory before believing the TEST number).** Re-run on the original
eight views (`out/condlaw_chair_repro.json`) reproduces the published AUCs to 6 decimals:

| row | published (`2dgs_falsify_chair_full.json`) | this harness (`condlaw_chair_repro.json`) |
|---|---|---|
| 2DGS[default] theta_normal, refined | 0.9668167777092631 | **0.966817** |
| 2DGS[default] theta_normal, headline | 0.8039150133789597 | **0.803915** |
| 2DGS[default] theta_depth, refined | 0.7401274308855779 | **0.740127** |
| vanilla-3DGS theta_normal, refined | 0.6959678298783764 | **0.695969** |
| GT-mesh theta_depth, refined | 1.0 (tautological) | **1.000000** |

Class counts match exactly (n_fab 83109, n_cre 28688/28693). The harness is faithful.

**Chair, all rows, frozen TEST split** (`out/condlaw_chair_test.json`):

| arm \| statistic | classes | AUC | DRR@80 | boot95 | n_cre | n_dist |
|---|---|---|---|---|---|---|
| 2DGS[default] \| theta_normal | refined | 0.9757 | **0.9858** | [0.9848,0.9866] | 39564 | 134805 |
| 2DGS[default] \| theta_normal | headline | 0.8457 | 0.7861 | [0.7832,0.7890] | 66212 | 192014 |
| GT-mesh \| theta_depth | headline (non-circular) | 0.8620 | 0.7999 | [0.7978,0.8026] | 66216 | 192014 |
| GT-mesh \| theta_depth | refined | 1.0000 | 1.0000 | — | 39565 | 134805 |
| GT-mesh \| theta_normal | either | — | **N/A** (no normal buffer) | — | 0 | 0 |
| vanilla-3DGS \| theta_normal | refined | 0.6967 | 0.4409 | [0.4339,0.4471] | 39343 | 80047 |
| 2DGS[default] \| theta_depth | refined | 0.7750 | 0.6480 | [0.6446,0.6514] | 39565 | 134805 |

The held-out number (0.9858) is **better** than the in-sample one (0.9785 on the original
views, `out/condlaw_chair_repro.json`), so the published claim is not a train-view artefact.

Independently, a **certified bound derived from the stored percentiles alone**
(`scripts/condlaw_chair_bound.py` → `out/condlaw_chair_bound.json`) pins the original-view
value to DRR@80 ∈ **[0.900, 0.990]** with no interpolation — the measured 0.9785 falls inside
it, a second consistency check.

---

## Lego — the ceiling, attacked from every side

`out/diag2dgs_lego_test.npz`, TEST views {5,15,…,95}, 49 860 linelets. `crease` and `decal`
are disjoint (verified: 0 overlap). AUC orientation follows `scripts/diag2dgs.py:544`
(positive class = TrueCrease), so **AUC < 0.5 means the statistic is anti-predictive**.

Because most lego statistics are anti-predictive, three orientation policies are reported and
the flattering one is never chosen silently (`out/condlaw_lego_drr.json`):

| signal | arm | AUC | frozen (sign +1) | VAL-picked sign+threshold → TEST | TEST-oracle sign (upper bound) |
|---|---|---|---|---|---|
| `mesh3d_rho4_xi0.25_nmin5` | GT-mesh | 0.3964 | 0.2790 | **0.5123** (rec 0.8004) | **0.5123** [0.4976,0.5281] |
| `spreadmesh_rho4_xi0.25_nmin5` | GT-mesh | 0.4675 | 0.1046 | 0.1620 (rec 0.8048) | 0.1691 [0.1570,0.1841] |
| `surfel3d_rho4_xi0.25_nmin5` | 2DGS | 0.4110 | 0.1847 | 0.3265 | 0.3249 |
| `spread2dgs_rho4_xi0.25_nmin5` | 2DGS | 0.5645 | 0.2826 | 0.2878 | 0.2826 |
| `surfel3d_perlinelet` | 2DGS | 0.3611 | 0.1357 | n/a (absent in VAL) | 0.4067 |
| `ribbon2dgs` | 2DGS | 0.3307 | 0.1626 | n/a | 0.5167 |
| `ribbon3dgs_vanilla` | 2DGS | 0.3875 | 0.1645 | n/a | 0.3952 |

The `common` measurable scope agrees (mesh dihedral 0.5143, dispersion 0.1520 —
`out/condlaw_lego_drr_common.json`), so the result is not a masking artefact.

### Adversarial probe — actively trying to break 0.55
Reporting one at-chance statistic is weak evidence for a ceiling, so
`scripts/condlaw_lego_probe.py` attacks it (`out/condlaw_lego_probe.json`):

| attempt | best DRR@80 |
|---|---|
| A. each GT-mesh/2DGS statistic, best orientation | 0.5123 |
| B. **learned multivariate combiner**, logistic on rank-normalised features, **fit on VAL → TEST** — 2-feature mesh / 4-feature | 0.4911 / 0.4992 |
| C. stricter TEED-confidence distractor definitions | 0.5123 |
| D. flattest 10/25/50% of decals, scored by a *different* feature | 0.4241 / 0.4434 / 0.4546 |

**Best over 11 non-circular attempts: 0.5123.** Three further rows reached 1.000, 0.418 and
0.209 but are **circular** (the decal subset was selected *by* the same feature that then
scored it) and are excluded and labelled as such in the JSON — the identical defect that makes
chair's refined GT-mesh row 1.000. Multivariate geometry does not rescue lego: giving the
combiner all four statistics *lowers* DRR@80 to 0.4992.

### Why the analogous chair class cannot even be built on lego
Chair's result rests on a genuinely flat printed-fabric class. On lego that class is **empty**
at ground truth (`out/diag2dgs_lego_test.json` → `flatness_premise`, verified directly):

- decals with mesh normal-dispersion < 5°: **0 of 3814 (0.000%)**; < 10°: **0 (0.000%)**
- surface flat fraction at scale 0.01: **0.69%** (<5°) — `out/diag2dgs_lego_surface_flatness.json`
- median dispersion gap crease − decal = **−0.3198°** (44.518 vs 44.838) — the spec's "0.32 deg"
- linelet median half-length **0.010007** ≈ all-seen median inter-crease distance **0.009806**;
  surfel median max-scale **0.011334** — `out/diag2dgs_lego_scale.json`, `diag2dgs_lego_test.json`

The mesh **dihedral** tells the same story from the other direction: decals are *sharper* than
creases (median **88.43°** vs **45.05°**, gap −43.38°) — lego's distractors sit on stud
micro-relief, which is more creased than the labelled crease loci.

---

## The honest lego precision-ceiling statement

> On the hard-surface lego scene, static geometric crease precision is intrinsically bounded:
> at ground truth the true-crease and TEED-confident non-crease loci are geometrically
> indistinguishable under normal dispersion (median gap **0.32°**; **DRR@80 = 0.169**,
> 95% CI [0.157, 0.184], *at or below* the 0.200 chance floor), and the mesh dihedral
> separates them only in the **anti-crease** direction (decals sharper than creases,
> 88.4° vs 45.1°; best-orientation DRR@80 **0.512**, i.e. above chance but far below any
> usable gate, and only by preferring the *flatter* locus as the crease). This holds because
> lego is micro-relief end-to-end — **0.69%** of the surface flat at measurable scale, and
> **zero** of 3814 distractors flat below 5° or 10° — and the inter-crease spacing (**0.0098**)
> equals the reconstruction resolution (linelet half-length **0.0100**, surfel scale
> **0.0113**). Texture/relief-vs-crease disentanglement is therefore underdetermined from
> surface differential geometry alone, independent of the 3DGS reconstruction.

*(Refined from the spec's draft on two measured points: the ceiling is stated against the
correct 0.200 chance floor, not 0.50; and "at chance" is attached to the dispersion statistic,
which is genuinely at/below chance, rather than to the dihedral, which carries real but
anti-predictive signal.)*

## The contrasting chair statement

> On chair the same measurement is decisive — **DRR@80 = 0.9858** (95% CI [0.9848, 0.9866],
> AUC 0.9757, held-out TEST) — because a genuinely flat printed-fabric class *exists* there:
> 134 805 loci that the GT mesh certifies flat below 5° while the image shows a strong edge.
> A learned/rendered prior buys rankable seeds on chair because there is a flat class to rank
> against. The gain is reconstruction-dependent, not automatic: on identical pixels and
> labels, vanilla 3DGS reaches only **0.4409** — it bakes the print into geometry — while 2DGS
> reaches 0.9858. The dichotomy is *class-structural*, not merely a difference of degree:
> on lego the corresponding class has **zero** members.

---

## FROZEN GO/NO-GO — verdict

Gate: **GO iff DRR@80(chair) >= 0.80 AND DRR@80(lego) <= 0.55.**

| scene | designated statistic (spec Goal) | DRR@80 | bar | verdict |
|---|---|---|---|---|
| chair | rendered-normal ribbon on the printed-fabric class (the AUC-0.967 lineage) | **0.9858** [0.9848,0.9866] | ≥ 0.80 | **PASS**, decisively |
| lego | GT-mesh dihedral / dispersion, best over both statistics, all three orientation policies, and 11 non-circular adversarial attempts | **0.5123** [0.4976,0.5281] | ≤ 0.55 | **PASS** (upper CI 0.528 < 0.55) |

### => CONDITIONAL LAW CONFIRMED (GO)

**Disclosed tension — the one reading that is not a clean pass.** The gate text says
*"compute DRR@80 for both scenes on the GT-mesh arm"*, but for chair that arm is not
executable as written: `theta_normal` does not exist on the mesh (no normal buffer), and on
`theta_depth` over the refined classes it is **circular** (those classes are defined by that
very statistic → 1.000 by construction). The nearest non-circular substitute — chair's GT-mesh
dihedral on *headline* classes, whose definition (crease-distance only) genuinely matches
lego's — gives **DRR@80 = 0.799916, 95% CI [0.7978, 0.8026]**: it lands on the 0.80 bar,
**8×10⁻⁵ below it**, with a CI straddling the bar in both directions. It is statistically
indistinguishable from the threshold and no verdict should hang on it either way.

The verdict rests on the spec's **specific** designation of the chair source (Goal section:
the AUC-0.967 rendered-normal-ribbon result on the printed-fabric class), which is
unambiguous and passes with room to spare, rather than on a general shorthand that is
literally unexecutable for chair. Recorded here so the choice is auditable, not buried.

Note also the class-definition asymmetry: chair's distractor class is restricted to
mesh-flat loci, lego's is not. That asymmetry is **not** a methodological flaw — it *is* the
law. The restriction is impossible to apply on lego because the flat class is empty.

---

## Result 1 — protected temporal-coherence win, untouched

Restated, not recomputed. `out/m1b_stroke_temporal_table_tc_tcteed.json` (+ paired control
`..._tc_tccanny.json`), chair, **TEST views only**, trajectory 5→15. Object-space carrier (A)
vs per-frame image-space Canny re-traced each frame (B), identical depth-based forward warp:

| frames | P_pop A | P_pop B | **ratio (teed)** | ratio (canny control) |
|---|---|---|---|---|
| 30 | 0.0928 | 0.7889 | **8.50×** | 8.25× |
| 60 | 0.0679 | 0.7705 | **11.35×** | 9.74× |
| 120 | 0.0588 | 0.7558 | **12.85×** | 10.43× |
| 240 | 0.0575 | 0.7551 | **13.12×** | 10.71× |

i.e. the published **8.5–13.1×** popping reduction (7–13× across both variants). Frechet
residual ratios over the same sweep: 3.99× → 28.36×. Every byte of this is covered by the
protected manifest and re-verified **332/332 OK** after all work in this fire.

---

## Artifacts written (all `condlaw_`-prefixed; nothing overwritten)

| path | contents |
|---|---|
| `scripts/condlaw_drr.py` | exact DRR@R core + lego driver (3 orientation policies) |
| `scripts/condlaw_null.py` | permutation null + bootstrap CI (lego) |
| `scripts/condlaw_chair_test.py` | faithful chair re-run on TEST, dumps per-locus arrays |
| `scripts/condlaw_chair_bound.py` | certified DRR@80 interval from stored percentiles |
| `scripts/condlaw_chair_null.py` | permutation null + bootstrap CI (chair) |
| `scripts/condlaw_lego_probe.py` | adversarial attempts to break the 0.55 bar |
| `out/condlaw_chair_{test,repro}.{json,npz}` | chair rows + per-locus arrays (TEST / repro) |
| `out/condlaw_chair_{bound,null}.json` | chair certified bound; chair CIs + null |
| `out/condlaw_lego_drr{,_common}.json` | lego rows, own / common scope |
| `out/condlaw_lego_{null,probe}.json` | lego CIs + measured chance floor; adversarial probe |
| `logs/condlaw_chair_{repro,test}.log` | run logs |

Run on `CUDA_VISIBLE_DEVICES=1`, u00134 processes only, ~3 GB peak.
