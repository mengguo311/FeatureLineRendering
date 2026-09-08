# GEOLINE STEP 1 — does 3-D surface geometry separate creases on a CLEAN GEOMETRIC SOLID?

Executes the user's frozen Step 1. `scripts/geoline_step1.py`, which **imports the DIAG-2DGS
estimators verbatim** (`diag2dgs.surfel3d_dihedral`, `diag2dgs.ribbon_dihedral`,
`diag2dgs.auc`, `diag2dgs.visible_mask_cloud`) rather than reimplementing them. Frozen lego
constants **rho = 4.0, xi = 0.25, n_min = 5**, no per-scene retuning of any kind.

**MESH EVAL-ONLY ATTESTATION.** The GT mesh is read exactly once, through
`tune_lib.Harness -> src.mesh_oracle`, to build the per-view crease distance transform that
assigns the TrueCrease / off-crease **labels**. `cadpartA_new.obj` is a symlink to
`cadpart_new.obj` (chamfered hex nut, 36 exactly-planar faces, 60 GT crease edges at dihedral
{40.89, 44.42, 49.11, 60, 90} deg). **No mesh quantity enters any signal, any cloud, any
normal field or any threshold.** Both signals consume only the frozen vanilla 3DGS. Nothing
was committed; no shipped json or pipeline file was modified.

---

## VERDICT

> **NO-GO on every gated cell, VAL and TEST, both arms, both negative-class definitions.**
> The hypothesis "K_geom revives geometric discriminators on textureless solids" is
> **falsified in its strong form**. It survives in a weak form that the numbers pin down
> precisely: on a clean solid the geometric cue stops being *anti*-predictive, which lego's
> premise failure said it would not, but it never becomes *discriminative*, and on the two
> HARD negative classes it collapses back to chance.

| frozen bar | required | best cell measured (TEST) | |
|---|---|---|---|
| AUC(dihedral; TrueCrease vs off-crease) | >= **0.80** | **0.6850** (`ribbon3dgs_vanilla`) | **FAIL** |
| median dihedral gap | >= **+25.0 deg** | **+16.67 deg** (`surfel3d_vanilla3dgs`) | **FAIL** |

No cell clears either bar, and no cell clears both. The two legs are not even maximised by the
same arm.

---

## 1. The gated table

Population: the 9,743 shipped cadpartA gated linelets (`out/linelets_cadpartA_gated_test.npz`,
post-DT-pull `p`), of which 3,049 survive the consensus prune. Labels recomputed per split.

### TEST split (views 5,15,...,95) — seen 9,743 | TrueCrease 4,674 | off-crease 3,877

| arm | negative class | AUC | med crease | med neg | **gap** | n | gate |
|---|---|---|---|---|---|---|---|
| `surfel3d_vanilla3dgs` | off-crease | 0.6336 | 50.86 | 34.19 | **+16.67** | 4324/3296 | NO-GO |
| `surfel3d_vanilla3dgs` | off-crease & DexiNed-hi | **0.4853** | 50.86 | 53.14 | **−2.28** | 4324/511 | NO-GO |
| `surfel3d_vanilla3dgs` | off-crease, prune survivors | **0.3672** | 50.58 | 59.37 | **−8.80** | 2466/389 | NO-GO |
| `ribbon3dgs_vanilla` | off-crease | **0.6850** | 10.20 | 5.72 | +4.48 | 4667/3877 | NO-GO |
| `ribbon3dgs_vanilla` | off-crease & DexiNed-hi | 0.5810 | 10.20 | 8.93 | +1.27 | 4667/610 | NO-GO |
| `ribbon3dgs_vanilla` | off-crease, prune survivors | 0.6120 | 26.36 | 14.02 | +12.35 | 2545/472 | NO-GO |
| `spread3dgs` (side-split-free) | off-crease | 0.6361 | 36.74 | 31.96 | +4.77 | 4324/3296 | NO-GO |

### VAL split (views 0,10,...,90) — seen 9,743 | TrueCrease 5,428 | off-crease 3,093

| arm | negative class | AUC | med crease | med neg | **gap** | n | gate |
|---|---|---|---|---|---|---|---|
| `surfel3d_vanilla3dgs` | off-crease | 0.6294 | 49.98 | 33.44 | +16.54 | 4901/2683 | NO-GO |
| `surfel3d_vanilla3dgs` | off-crease & DexiNed-hi | **0.4156** | 49.98 | 57.67 | **−7.70** | 4901/282 | NO-GO |
| `surfel3d_vanilla3dgs` | off-crease, prune survivors | **0.3443** | 50.51 | 59.20 | **−8.70** | 2480/360 | NO-GO |
| `ribbon3dgs_vanilla` | off-crease | 0.6332 | 8.96 | 5.96 | +3.01 | 5428/3093 | NO-GO |
| `ribbon3dgs_vanilla` | off-crease & DexiNed-hi | 0.5132 | 8.96 | 7.37 | +1.59 | 5428/391 | NO-GO |
| `ribbon3dgs_vanilla` | off-crease, prune survivors | 0.5779 | 22.73 | 16.60 | +6.13 | 2600/409 | NO-GO |
| `spread3dgs` (side-split-free) | off-crease | 0.6367 | 36.50 | 30.94 | +5.56 | 4901/2683 | NO-GO |

**VAL and TEST agree to within 0.006 AUC on every primary cell.** The verdict is not a split
artefact and there is no selection to disclose: the bars were frozen before either ran.

---

## 2. What DID change versus lego, and what did not

| arm | lego (banked) | cadpartA TEST | |
|---|---|---|---|
| 3-D dihedral, AUC | **0.4110** | **0.6336** | sign flips, crosses chance |
| 3-D dihedral, median gap | **−17.33 deg** | **+16.67 deg** | sign flips |
| ribbon on vanilla 3DGS, AUC | **0.3875** | **0.6850** | sign flips |
| ribbon on vanilla 3DGS, gap | **−5.94 deg** | **+4.48 deg** | sign flips |

Every sign flips. **Lego's premise failure was genuinely scene-specific and does not
transport**, which is a real positive result for the user's reasoning: on lego the dihedral
was *higher* at the distractors than at the creases, and the GT-mesh arm failed too. Here the
creases really are the high-dihedral class. The clean solid did what it was supposed to do.

It just is not enough. +0.13 to +0.18 of AUC above chance against a bar that needs +0.30.

---

## 3. The finding that actually decides Step 2: the lift is on the EASY negatives

`surfel3d_vanilla3dgs` reads AUC 0.6336 against all off-crease loci, **0.4853 against
detector-confident off-crease loci, and 0.3672 against the off-crease loci that survive the
consensus prune** — below chance, with the gap sign reversed, on both hard classes and on both
splits.

The negatives the geometric cue can reject are the ones the shipped pipeline **already
rejects**. Against the residual population that a Step-2 cull would actually face, the cue is
worth nothing or less than nothing. A 45-degree threshold applied there would remove true
creases faster than false candidates.

That is a direct, pre-Step-2 answer: **the proposed 45-degree cull cannot pay on this
substrate as currently reconstructed**, and running it would only re-measure this.

---

## 4. Is it the radius? No. (DIAGNOSTIC ONLY — never read as the gate)

The frozen R = rho * median(l) = 4.0 x 0.02841 = **0.11363**, on a part whose chamfers are
0.10 and 0.20 wide, so the ball at an off-crease locus routinely contains a real crease. That
is the DIAG-2DGS section-2 scale conflict reproducing here. The full sweep, printed beside the
frozen value exactly as `diag2dgs` does, shows the verdict does **not** depend on the choice:

| rho | R | measurable | dihedral AUC | gap | spread AUC |
|---|---|---|---|---|---|
| 0.5 | 0.01420 | 0.605 | 0.6278 | +11.20 | 0.5869 |
| 1.0 | 0.02841 | 0.984 | 0.6245 | +18.85 | 0.6006 |
| **1.5** | 0.04261 | 0.990 | **0.6697** | **+26.25** | 0.6482 |
| 2.0 | 0.05681 | 0.983 | 0.6614 | +25.33 | 0.6297 |
| 3.0 | 0.08522 | 0.956 | 0.6473 | +19.00 | 0.6386 |
| **4.0 (frozen)** | 0.11363 | 0.891 | **0.6336** | **+16.67** | 0.6361 |
| 6.0 | 0.17044 | 0.867 | 0.6422 | +15.99 | 0.6278 |

Peak AUC over the whole sweep is **0.6697**, still 0.13 short. The gap leg alone does clear
+25 at rho 1.5 and 2.0, but the AUC leg never comes within reach, so no radius produces a GO
and **retuning rho was not the missing ingredient**. Reported because it was measured, not
because it changes the verdict.

Two further sensitivities, both null: restricting the cloud to front-surface gaussians
(lego's `--visible_only`, which the lego headline also had off) changes nothing at all
(32,476 of 32,476 gaussians already qualify, AUC identical to 4 decimals); and the
side-split-free `spread` statistic, which has no tangent and no side assignment to blame,
lands at 0.6361 / 0.6367, i.e. the same place. **The estimator's construction is not the
problem.**

---

## 5. The mechanism, and the one honest rescue path

`ribbon3dgs_vanilla` puts the **median rendered dihedral at a true crease at 10.20 deg**, on a
part whose GT crease dihedrals are 40.89 to 90 deg. The vanilla 3DGS normal field is smoothed
to roughly a quarter of the true angle. The signal is not absent from the object; it is absent
from **this reconstruction of it**.

That is a reconstruction ceiling, and there is a banked precedent for lifting it. On chair, the
identical ribbon estimator scores **AUC 0.696 on vanilla 3DGS and 0.967 on 2DGS**, against a
GT-flat printed-fabric negative class. Our cadpartA vanilla number, **0.6850**, sits almost
exactly on chair's vanilla number. If that vanilla-to-2DGS transport holds here, a 2DGS
reconstruction of cadpart would clear the 0.80 bar comfortably.

*Provenance of that pair, stated because it is doing real work here.* The 0.967 originates in
`PLAN1_RESULTS.md` step A, **which is no longer on disk**; it survives as a quotation in
`out/DIAG2DGS_RESULTS.md` (lines 28, 43, 244) and `out/CONDLAW_RESULTS.md` (lines 58, 209,
225), and the 0.696 vanilla control is in the `scripts/diag2dgs.py` module docstring.
`CONDLAW_RESULTS.md` line 74 records that **the published 0.967 was largely in-sample**, and
re-measured the same estimator on the same class properly held out at **0.9858
[0.9848, 0.9866]**, clearing an 0.80 bar decisively. So the precedent survives its own audit,
but it is a *different negative class* (flat printed fabric) than ours, which makes it an
analogy for the transport, not a prediction of the number.

**This is the load-bearing limitation of this run and it is declared, not buried:** no 2DGS
model exists for any cadpart scene (`out/2dgs_*` covers chair and lego only), so the 3-D arm
was fed the vanilla 3DGS de-floatered cloud (32,476 gaussians, unoriented shortest-covariance
normals, opacity weights). The arm is named `surfel3d_vanilla3dgs`, not `surfel3d`, throughout.
**It is therefore NOT comparable to lego's 0.4110 on the reconstruction axis**, only on the
substrate axis where lego's own vanilla control read 0.3875.

---

## 6. Declared substitutions and their justification

1. **Cloud.** As above: vanilla 3DGS in place of 2DGS surfels, forced by asset availability.
2. **Negative class.** Lego's negative is "> 3.0 px from a crease AND TEED-high", where the
   detector condition exists to make the negatives hard (printed decals). cadpart has one
   uniform albedo and zero decals by construction, and no TEED cache was ever built for it.
   Both readings are reported and gated: plain off-crease (the user's phrasing, primary) and
   off-crease with the repo's cadpart DexiNed cache standing in for TEED (the lego rule).
   They do not merely agree on the verdict, they disagree on the *direction* of the effect,
   which is section 3 and is the most useful thing in this document.
3. **Linelet set.** The shipped gated cadpartA linelets at f=0.30, not a TGAP pull file
   (none exists for this scene). All 9,743 are scored; the 3,049 prune survivors are reported
   as the `keep_only` sensitivity.

## 7. Artifacts

`out/geoline_step1_cadpartA_test.json`, `out/geoline_step1_cadpartA_val.json`,
`out/geoline_step1_cadpartA_test_sweep.json`, `scripts/geoline_step1.py`. Nothing committed.
