# DE-DEBRIS v2 — cross-stroke dihedral test (pre-registered BEFORE running)

## Discriminator chosen: OPT-C, 3-D crease support, as a TWO-SIDED cross-stroke dihedral

**Why C and not A or B, argued a priori, before any image.**
- **A (trunk 10th-percentile angle floor)**: the same evidence-STRENGTH signal that over-pruned
  in v1, merely lowered. The fill exists because the trunk's ranker rejected it for weak
  evidence, so no percentile of the trunk's strength distribution *provably* keeps it.
- **B (trunk-endpoint connectivity)**: fails provably. The top-hole edges form an isolated
  inner hexagon and the STEP3-only render draws essentially nothing on it, so those dashes
  attach to no trunk stroke and connectivity deletes them by construction.
- **C**: tests WHAT THE STROKE SITS ON, not how strong the evidence was. The three named
  features lie on real dihedrals — ledge/chamfer **40.89 to 44.42 deg**, top-hole wall
  **90 deg**, hex-side verticals **60 deg** — while a floating mid-face stub sits on a flat
  face at **0 deg**. The separation is a property of the geometry and is independent of
  evidence strength, which is exactly what v1 lacked.

## The test
Per fill-stroke vertex, the frozen `gate2dgs.ribbon_normal_theta` two-sided estimator, via the
frozen `diag2dgs.ribbon_dihedral`, on the **2DGS normal buffer**, medianed over 20 TRAIN views.
It samples the surface normal on BOTH sides of the stroke and returns the angle between them,
so a flat face reads ~0 regardless of how bright any edge response was.

**Threshold = 30 degrees, the project's own shipped crease definition** (`mesh_oracle`
`angle_deg=30.0`). Not fitted: it sits between the two populations with margin on both sides,
below every named feature's GT dihedral (40.89 minimum) and far above a flat face (0). Banked
support: Step 2 measured this estimator on the 2DGS buffer for cadpartA at median **40.04 deg
on-crease against 0.06 deg off-crease**, a ~700x separation.

**Majority rule**: keep a fill stroke iff **>= 50%** of its vertices read >= 30 deg, i.e. most
of what we draw must sit on a dihedral. Trunk is never gated and stays byte-identical.

## PRE-REGISTERED IMAGE GO/NO-GO
**GO** iff (1) **all three** named features survive — ledge line, top-hole edges, right-face
verticals — AND (2) the wavy front-face stroke and the mid-face stubs are gone AND (3)
cut <= 0.0102. **NO-GO otherwise, reported straight**, and we keep the 70-stroke merge.

Reported not gated: stroke count, median verts, total arc, P_pop + cut, mesh P/R.
Declared polyhedron-scope limit on the inherited min-length and straightness filters restated.
