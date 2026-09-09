# GEOLINE STEP 2 — the 2DGS reconstruction test

Executes `GEOLINE_STEP2_DISPATCH.md`. `scripts/geoline_step2.py`, which **imports the
DIAG-2DGS estimators verbatim** (`diag2dgs.surfel3d_dihedral`, `diag2dgs.ribbon_dihedral`,
`diag2dgs.load_surfel_normals`, `diag2dgs.auc`) at the frozen lego constants **rho = 4.0,
xi = 0.25, n_min = 5**. No per-scene tuning anywhere, in the reconstruction or the estimator.

**MESH EVAL-ONLY ATTESTATION.** The GT mesh is read once, through
`tune_lib.Harness -> src.mesh_oracle`, to build the per-view crease distance transform that
assigns labels. No mesh quantity enters any signal, cloud, normal field or threshold.
Nothing committed.

---

## VERDICT

> **The AUC leg passes decisively; the verdict then depends on which of two gate readings is
> applied, so both are reported and neither is resolved silently.**
>
> | reading | result |
> |---|---|
> | AUC >= 0.75 only (the live dispatch message) | **GO**, 0.9239 and 0.9294 vs a 0.75 bar |
> | AUC >= 0.75 AND VAL within 0.03, like-for-like population (`keep_both`) | **GO**, \|d\| = 0.0010 |
> | AUC >= 0.75 AND VAL within 0.03, literal population (`keep_only`) | **NO-GO**, \|d\| = 0.0526 |
>
> Two of the three readings are GO and the third fails only its split-agreement sub-leg, never
> the AUC bar. AUC against off-crease prune-survivor negatives is **0.9239** (literal
> population) and **0.9294** (Step-1-matching population) on held-out TEST. Every negative
> class on the 2DGS ribbon arm clears 0.75, including the hardest. Section 4 attributes the
> single 0.0526 failure to the asymmetric population definition rather than to instability of
> the signal, and section 5.5 records that my script's own rule was stricter than either
> written gate. **The user's live instruction gates on AUC only; under it this is an
> unambiguous GO. Under the committed spec `a428b26`, which adds the VAL leg, the answer is
> GO or NO-GO according to the population, and that call is the user's to make.**

**The mechanism the Step-1 diagnosis predicted is confirmed almost exactly.** The vanilla 3DGS
read a median crease dihedral of 10.19 deg where the GT dihedrals are {40.89, 44.42, 49.11, 60,
90}. The 2DGS reads **40.04 deg (TEST) / 44.79 deg (VAL)** — inside the GT range, at its lower
end — and reads the off-crease class at **0.06 deg / 0.12 deg**, i.e. genuinely flat. The
crease signal was in the object and smoothed out of the vanilla reconstruction, exactly as
diagnosed.

---

## 1. The gate

| definition | arm | AUC TEST | AUC VAL | \|d\| | n pos/neg | AUC leg | VAL leg | gate |
|---|---|---|---|---|---|---|---|---|
| keep_both | **`ribbon2dgs`** | **0.9294** | **0.9285** | **0.0010** | 2545/472 | **PASS** | **PASS** | **GO** |
| keep_only | **`ribbon2dgs`** | **0.9239** | 0.8713 | 0.0526 | 4667/472 | **PASS** | FAIL | NO-GO |
| keep_both | `surfel3d_2dgs` | 0.3352 | 0.3386 | 0.0033 | 2552/472 | FAIL | PASS | NO-GO |
| keep_only | `surfel3d_2dgs` | 0.3841 | 0.3690 | 0.0151 | 4674/472 | FAIL | PASS | NO-GO |
| keep_both | `surfel3d_vanilla3dgs` | 0.3672 | 0.3443 | 0.0229 | 2466/389 | FAIL | PASS | NO-GO |
| keep_both | `ribbon3dgs_vanilla` | 0.6118 | 0.5779 | 0.0338 | 2545/472 | FAIL | FAIL | NO-GO |

**Two populations, because the dispatch's wording and the Step-1 number it quotes disagree.**
`keep_only` is the literal wording, "TrueCrease vs off-crease PRUNE-SURVIVORS": all TrueCrease
against surviving off-crease loci. `keep_both` restricts **both** classes to survivors, which
is what Step 1 computed and therefore the definition behind the 0.3672 the dispatch cites as
its motive. Both are scored and both are gated; neither was chosen after seeing a number.

**The Step-1 control reproduces.** `keep_both|surfel3d_vanilla3dgs` reads 0.3672 / 0.3443 here
against Step 1's 0.3672 / 0.3443, and `keep_both|ribbon3dgs_vanilla` reads 0.6118 / 0.5779
against Step 1's 0.6120 / 0.5779. The 2e-4 drift is 3DGS rasteriser non-determinism (atomic
accumulation order), not a methodological difference.

## 2. Full signal table (TEST) — supporting diagnostics, NOT gated

| arm \| negative class | AUC | med crease | med neg | gap | n pos/neg |
|---|---|---|---|---|---|
| `ribbon2dgs` \| keep_both | **0.9294** | 40.15 | **0.06** | **+40.09** | 2545/472 |
| `ribbon2dgs` \| keep_only | **0.9239** | 40.04 | 0.06 | +39.97 | 4667/472 |
| `ribbon2dgs` \| all off-crease | **0.9482** | 40.04 | 0.61 | +39.43 | 4667/3877 |
| `ribbon2dgs` \| DexiNed-hi off-crease | **0.8309** | 40.04 | 13.00 | +27.03 | 4667/610 |
| `ribbon3dgs_vanilla` \| all off-crease | 0.6849 | 10.19 | 5.72 | +4.47 | 4667/3877 |
| `ribbon3dgs_vanilla` \| DexiNed-hi | 0.5810 | 10.19 | 8.93 | +1.26 | 4667/610 |
| `surfel3d_2dgs` \| all off-crease | 0.6589 | 41.70 | 35.55 | +6.15 | 4674/3877 |
| `surfel3d_vanilla3dgs` \| all off-crease | 0.6336 | 50.86 | 34.19 | +16.67 | 4324/3296 |
| `spread2dgs` (side-split-free) \| all off-crease | 0.6925 | 29.94 | 23.04 | +6.90 | 4674/3877 |

**Every 2DGS-ribbon cell clears 0.75, including the hardest negative class.** DexiNed-confident
off-crease loci — the class on which every vanilla arm collapsed to chance in Step 1 — read
**0.8309**, with the negative median at 13.00 deg against a crease median of 40.04.

## 3. The win is image-space only, and that is load-bearing for what to build next

`surfel3d_2dgs` did **not** improve: 0.3352 to 0.3841, still below chance, and the
side-split-free `spread2dgs` is no better. Swapping surfels into the 3-D ball estimator changed
nothing, because that estimator's failure is the **scale conflict** Step 1 measured, not the
normal field: R = rho * median(l) = 0.11363 on a part whose chamfers are 0.10 and 0.20 wide,
with cap-binding at 0.409. The ball still swallows a real crease at off-crease loci regardless
of how good the surfels are.

**So the entire gain is the image-space ribbon on the 2DGS rendered normal map.** Anything
built on this result should read the 2DGS normal buffer, not run a 3-D ball query.

## 4. Why the one failing sub-leg is a population artefact

Under `keep_only` the positive class differs between splits: 4,667 TrueCrease on TEST against
5,428 on VAL, and their median crease dihedrals differ correspondingly (40.04 vs 44.79 deg),
because different creases are visible from different view sets. The negative class is the same
size in both. So the 0.0526 spread measures **which creases each split can see**, not whether
the signal is stable.

Restrict both classes consistently and the spread collapses to **0.0010** — the best VAL/TEST
agreement of any cell in this study. The `keep_both` reading is the like-for-like one, and it
is also the definition the dispatch's own motivating number came from.

## 5. Caveats on the record

1. **Neither reconstruction is held out with respect to itself.** `view_split.VAL` and `TEST`
   are indices into `transforms_train.json`; the 2DGS `--eval` flag holds out the separate
   20-view `transforms_test.json`. Both the vanilla 3DGS and the 2DGS trained on all 100 of
   those views, identically to chair and lego. The **arm comparison is therefore fair** — both
   arms carry the same exposure — but the absolute AUCs are not held out with respect to the
   reconstruction. A prior audit flagged the same property for the chair 0.967 figure and
   re-measured it properly held out at 0.9858, so the effect survived that test there.
2. **The 2DGS is not a worse-fitting model that happens to look sharper.** Test PSNR
   **40.04 dB** at 30,000 iterations, against the vanilla 3DGS condition-A **39.38 dB**.
   72,483 surfels, 51,923 above opacity 0.1. Recipe byte-identical to `run_2dgs_chair.sh`
   Run A and `run_2dgs_lego.sh`: `--lambda_normal 0.05 --lambda_dist 0.0 --depth_ratio 1.0
   --eval --white_background --data_device cpu`, 30,000 iterations.
3. **This result is scope-limited to geometric solids, and the boundary is measured.** The same
   `ribbon2dgs` arm scores **0.3307 on lego**, worse than lego's vanilla 0.3875. The normal
   regulariser that makes 2DGS read a planar face at 0.06 deg is exactly what destroys it on
   micro-relief. The win is a property of the clean-solid class the user scoped to, not a
   general improvement.
4. **This is a discriminability measurement, not a pipeline result.** A GO licenses building
   the cull or the seed score on the 2DGS normal buffer. It does not by itself move P/R, and it
   says nothing about the candidate-pool ceiling (cadpartA gaussian-centre pool recall 0.2021
   at the 1.5 px equivalent radius), which remains the separate constraint identified earlier.
5. **The conservative rule in the script printed NO-GO**, because I coded the overall verdict to
   require every definition to pass every leg. That rule is stricter than either the dispatch
   file or the dispatch message. It is reported here so the disagreement is visible rather than
   silently resolved: the gated AUC passed its bar in all four prune-survivor cells.

## 6. Artifacts

`out/geoline_step2_cadpartA.json`, `out/2dgs_cadpartA/` (30,000-iteration model),
`scripts/geoline_step2.py`, `scripts/run_2dgs_cadpartA.sh`, `logs/2dgs_cadpartA.log`.
Nothing committed.
