# GEOLINE STEP 4 — generality of ONE frozen zero-knob parameter set across clean solids

**STATUS: IN PROGRESS.** Plan persisted before execution (context-loss insurance).

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
