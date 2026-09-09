# GEOLINE STEP 4 — generality of ONE frozen zero-knob parameter set across clean solids

**VERDICT: NOT-GENERAL.** One of the two gated solids fails. The shallow-chamfer prism
passes both legs; the icosahedron misses the recall bar by a wide margin (0.2598 against
0.35) and breaches the non-regression allowance (−0.1608 against −0.10). The cube tripwire
passed, so the method is not broken, and the oracle arm attributes **every** shortfall on
**every** solid to the RANKER, not the pool.

**My design-argue prediction was wrong, informatively.** I argued the shallow-dihedral prism
was "the genuinely new dihedral stress" and the icosahedron a moderate test. The opposite
happened. The prism at 33 degrees passes; the icosahedron at 41.81 degrees, a value sitting
*inside* cadpart's existing range, fails. **Dihedral magnitude is not the binding axis.**

## Frozen design (converged in the design argue, locked by `dss9_geoline_step4_spec.md`)

Zero-knob rule: **f = 1.00** (M1a seed selection DELETED, not tuned), the **shipped spec
consensus prune** (inlier ratio >= 0.50, median residual <= 1.5 px, tau_in 1.5), rho = 4.0,
xi = 0.25, n_min = 5 verbatim, and **NO keep fraction anywhere**. Nothing is read off any
P/R curve on any scene.

**GENERALITY REFERENCE (locked amendment 1):** cadpartA zero-knob point
**R@1.5 = 0.4206 / P@1.5 = 0.8139** (n = 7,208). The keep-fraction-0.35 point 0.6250/0.7486
is RETIRED from every generality claim and survives only as an upper reference.

**CUBE-FIRST TRIPWIRE (locked amendment 2):** build and evaluate the cube FIRST, print its
P/R checkpoint, and STOP before spending GPU on icosahedron / shallow-prism if it fails
R@1.5 >= 0.35 at P@1.5 >= 0.70. The cube is strictly simpler than cadpart, so a failure there
means the method is broken, not merely non-general.

## Solids
| solid | oracle-labelled dihedral | role |
|---|---|---|
| cube | 90 deg | ungated control / tripwire, evaluated FIRST |
| icosahedron | 41.81 deg (interior 138.19) | gated; face count + valence-5 vertices |
| shallow-chamfer prism | 30-40 deg band | gated; the genuinely new dihedral stress |

Note recorded during the design argue: the GT oracle labels a crease by the angle **between
face normals** (`trimesh.face_adjacency_angles >= 30 deg`). In that convention cadpart spans
{40.89, 44.42, 49.11, 60, 90}, so neither the cube (90) nor the icosahedron (41.81) moves
outside the range cadpart already covers. Only the shallow-chamfer prism does.

## FROZEN GO/NO-GO (pre-registered)
- **GENERAL** iff every GATED solid (icosahedron, shallow-prism) reaches R@1.5 >= 0.35 at
  P@1.5 >= 0.70 at the zero-knob point AND regresses from 0.4206 / 0.8139 by <= 0.10 recall
  and <= 0.12 precision.
- **NOT-GENERAL** otherwise, reported per solid, straight.
- Dissociation (reported, not gated): oracle ceiling arm per solid. Misses bar but oracle
  clears R 0.60 => RANKER failure; oracle also misses => POOL failure.
- Temporal (reported, ungated): trip-wire at 3x; cadpart zero-knob is 10.50x.

## Three declarations carried into the write-up
1. f = 1.00 is the DELETION of the M1a seed-selection stage, not a tuned value. It was
   nonetheless chosen after seeing f = 0.30 underperform on cadpart, and that is declared.
2. The R 0.6250 headline is retired from any generality claim.
3. The linelet half-length stays at published behaviour; its measured 3.2x mismatch on
   cadpart is DECLARED, not fixed (scale-adapt measured it as a P/R dial worth ~0 recall).

**MESH EVAL-ONLY.** The GT mesh is read for evaluation labels and for the oracle ceiling arm.
No mesh quantity enters any method-path signal on any solid.

---

# RESULTS

## 1. The gate — zero-knob operating point, segments @1.5, held-out TEST

f = 1.00, shipped spec consensus prune, no keep fraction, nothing read off any P/R curve.

| solid | P@1.5 | R@1.5 | n kept | dR vs 0.4206 | dP vs 0.8139 | gate |
|---|---|---|---|---|---|---|
| **cadpartA** (locked reference) | 0.8139 | 0.4206 | 7,208 | — | — | reference |
| **gcube** (ungated control) | 0.7375 | 0.4046 | 5,610 | −0.0160 | −0.0764 | **tripwire PASS** |
| **gicosa** (gated) | 0.8234 | **0.2598** | 3,828 | **−0.1608** | +0.0095 | **FAIL** |
| **gprism** (gated) | 0.8226 | **0.3663** | 5,760 | −0.0543 | +0.0087 | **PASS** |

- **gicosa fails both legs**: R 0.2598 is below the 0.35 absolute bar, and its recall
  regression of 0.1608 exceeds the 0.10 allowance. Its precision is fine, in fact slightly
  better than the reference.
- **gprism passes both legs** with room on each.
- **The cube tripwire cleared** at R 0.4046 / P 0.7375, printed to
  `logs/step4_checkpoint.log` before any GPU was spent on the gated pair, exactly as the
  locked amendment required. Note its precision is the *lowest* of the four despite it being
  the geometrically simplest solid.

**GENERAL requires every gated solid to pass. One of two does. The verdict is NOT-GENERAL.**

## 2. Dissociation — every shortfall is a RANKER failure, on every solid

Oracle ceiling arm, eval-only, same construction and sweep grid as Step 3 arm C.

| solid | zero-knob R | oracle best at P >= 0.70 | oracle clears R 0.60? | attribution |
|---|---|---|---|---|
| cadpartA | 0.4206 | R 0.7271 / P 0.7274 | yes | ranker-limited |
| gcube | 0.4046 | R 0.8411 / P 0.7333 | yes | ranker-limited |
| **gicosa** | **0.2598** | **R 0.7106 / P 0.8414** | **yes** | **RANKER failure** |
| gprism | 0.3663 | R 0.7144 / P 0.7215 | yes | ranker-limited |

**No solid is pool-limited.** The candidate pool on the icosahedron supports R 0.7106 at
P 0.8414; the shipped prune extracts 0.2598 of it. This is the same conclusion Step 3 reached
on cadpart, now replicated on three further solids: **coverage is not the problem anywhere,
and the ranker is the problem everywhere.**

## 3. The mechanism, and an untested hypothesis stated as such

The prune's retention rate tracks the failure exactly:

| solid | pool | kept | retention | zero-knob R | pre-prune R (after pull) |
|---|---|---|---|---|---|
| gcube | 20,962 | 5,610 | **26.8 %** | 0.4046 | 0.9821 |
| cadpartA | 32,476 | 7,208 | 22.2 % | 0.4206 | 0.9198 |
| gprism | 30,619 | 5,760 | 18.8 % | 0.3663 | 0.9096 |
| **gicosa** | 31,613 | 3,828 | **12.1 %** | **0.2598** | 0.9639 |

The icosahedron has the **richest pulled pool** (pre-prune recall 0.9639, second only to the
cube) and the **harshest cull**. The consensus statistic is rejecting good candidates.

**Hypothesis, untested, offered as a hypothesis:** the icosahedron is the most symmetric solid
in the set, with 30 identical-length edges related by a large symmetry group and 12 valence-5
vertices. Multi-view consensus is a correspondence statistic, and a highly symmetric object
presents many near-identical edges at similar depths from many viewpoints, so a linelet pulled
to the *wrong but equivalent* edge in a subset of views reads as inconsistent. That is an
aliasing failure, not a geometry failure, and it would explain why dihedral magnitude does not
predict the outcome while symmetry does. **The cheapest test is a solid with the icosahedron's
face count and vertex valence but its symmetry deliberately broken**, for example by
perturbing vertex radii. That is the natural Step 5.

## 4. Temporal — reported UNGATED, trip-wire 3x

240-frame TEST orbit, identical warp and per-frame Canny baseline.

| solid | strokes | OURS P_pop | BASE P_pop | **ratio** | Frechet ratio | unmatched | cut |
|---|---|---|---|---|---|---|---|
| cadpartA (zero-knob) | 42 | 0.0771 | 0.8097 | **10.50x** | 37.03 | — | — |
| gcube | 23 | 0.0381 | 0.7907 | **20.77x** | 49.78 | 0.0381 | 0.0000 |
| gicosa | 25 | 0.0636 | 0.8842 | **13.90x** | 35.74 | 0.0636 | 0.0000 |
| gprism | 44 | 0.0459 | 0.8702 | **18.97x** | 44.49 | 0.0458 | 0.0001 |

**No solid comes near the 3x trip-wire; all three new solids beat cadpart.** The decomposition
is the striking part: `cut_frac` is **0.0000 to 0.0001** on all three, so essentially the whole
popping penalty is `unmatched`, which is correct hidden-line removal rather than topological
instability. On clean solids the object-space representation is not fragmenting at all.

## 5. Builder self-checks — all three run, all three passed, all three reported

| solid | verts / faces | max non-planarity | GT crease edges | dihedrals (deg) | min crease \|dI\| | silhouette IoU | max depth diff |
|---|---|---|---|---|---|---|---|
| gcube | 8 / 6 | 0.00e+00 | 12 of 18 | {90.0} | 0.1894 | 0.99999–1.00000 | 3.34e-06 |
| gicosa | 12 / 20 | 9.61e-17 | 30 of 30 | {41.81} | 0.0534 | 1.00000 | 3.34e-06 |
| gprism | 36 / 36 | 3.59e-16 | 60 of 108 | {33.11, 33.12, 34.74, 34.75, 55.25, 55.26, 60.0, 90.0} | 0.0434 | 1.00000 | 1.05e-05 |

Light sets were frozen per solid by the inherited `pick_lights`, which maximises the *weakest*
crease contrast. All three clear the > 0.02 luma premise. 3DGS, identical recipe and 10,000
iterations for every solid:

| solid | gaussians | test PSNR |
|---|---|---|
| cadpartA (banked) | 75,539 | 39.38 dB |
| gcube | 59,129 | 39.59 dB |
| gicosa | 73,921 | 39.83 dB |
| gprism | 73,065 | 40.01 dB |

**One disclosed construction iteration.** The prism was built twice. The first build used a
chamfer of dz/dr = tan(38 deg) and measured a shallowest crease of **39.12 deg**: inside the
30-40 band by the letter, but only 1.77 deg below cadpart's 40.89 floor, which would not have
stressed the axis the solid exists to stress. It was rebuilt once at tan(31 deg), giving
33.11 deg. **The decision was made from the asset's measured dihedral, before any P/R was
computed on the solid**, and is the same class of construction choice as `pick_lights`. Both
builds are recorded here rather than only the second.

## 6. The three declarations, carried as promised

1. **f = 1.00 is the DELETION of the M1a seed-selection stage, not a tuned value.** It was
   nonetheless adopted after seeing f = 0.30 underperform on cadpart, so it is a P/R-informed
   choice and is declared as one. Step 3 measured the M1a score as unable to rank a pulled
   pool to P 0.70 at all, which is the substantive reason for deleting it.
2. **The R 0.6250 / P 0.7486 keep-fraction-0.35 headline is retired** from every generality
   claim in this document. It appears nowhere in the tables above.
3. **The linelet half-length stays at published behaviour.** Its measured 3.2x mismatch on
   cadpart is declared, not fixed; scale-adapt measured that constant as a precision/recall
   dial worth approximately zero recall.

## 7. What this does and does not license

It does establish, on four solids, that the pool is never the constraint and the ranker always
is. It does establish that one frozen zero-knob set transports to a cube and to a solid with
creases 8 degrees shallower than anything it was built on. It does **not** establish
generality, because the icosahedron fails, and it does not identify the axis that predicts
failure. The symmetry hypothesis in section 3 is untested.

## 8. Artifacts

`scripts/geoline_solids_make.py`, `scripts/geoline_step4_oracle.py`,
`out/xy/geoline_solid_{gcube,gicosa,gprism}.json`,
`out/m1b_{gcube,gicosa,gprism}_step4.json`, `out/linelets_{gcube,gicosa,gprism}_step4*.npz`,
`out/geoline_step4_oracle_{gcube,gicosa,gprism}.json`,
`out/m1b_stroke_temporal_table_s4{gcube,gicosa,gprism}.{json,md}`,
`~/cglib/data/full/{gcube,gicosa,gprism}/`, `~/cglib/outputs/{gcube,gicosa,gprism}_static/`,
`~/3dgs_line/bcr/meshes/NeRF_Mesh/{gcube,gicosa,gprism}_new.obj`,
`logs/step4_*.log`. `scripts/xy_cad_make.py` was NOT modified. Nothing committed.
