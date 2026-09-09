# BUFFER-EDGE MISS-SET DETECTABILITY — plan (frozen before execution)

**VERDICT: NO-GO as frozen**, on the Jaccard leg. The detection leg passed and the
perfect-geometry arm cleared both bars, so this is **NOT an unconditional kill**. The Jaccard
failure is a specification defect I introduced, described in section 4, and the user should
decide whether to re-register that leg before anything is re-run.

## Question
Do convolutional edge operators on the FROZEN-GEOMETRY render buffers see the GT crease
pixels the shipped pipeline currently misses? If no buffer sees them, no combination of
buffers can break the ceiling and the branch closes.

Deliberately NOT a buffer x operator preference matrix. The featviz L15 numbers already show
the variance lives in which reconstruction produced the buffer, not in which kernel is applied:
cadpart's on-crease normal-discontinuity is 3.29 deg on vanilla against 23.17 deg on 2DGS, a
7x swing, while on vanilla cadpart the on-crease/off-crease separation is **negative**
(3.29 vs 4.42). One frozen operator, many buffers, is therefore the informative allocation.

**MESH EVAL-ONLY.** The mesh supplies the GT crease labels, the miss set, and the
perfect-geometry oracle arm. No mesh quantity enters any mesh-free buffer.

## Definitions, all frozen, no per-scene tuning
- **Scenes**: cadpartA, lego. **Views**: all 10 held-out TEST views, pooled.
- **Miss set**: GT crease pixels whose distance to the shipped pipeline's rendered line mask
  exceeds 1.5 px. The shipped mask is `linelets_<scene>_gated_test.npz` at its `keep`,
  rasterised by the same `run_m1b.raster_segments` that produces every banked P/R number.
- **Off-crease foreground**: alpha > 0.5 and more than 3.0 px from any GT crease. This is the
  campaign's standing negative-class convention.
- **One frozen operator**: Sobel gradient magnitude, L2 across channels for vector buffers.
  For the two DERIVED maps (depth-disc, normal-disc) the map itself is the response, because
  they are already first-derivative maps and applying Sobel again would make them Laplacians
  and handicap them by construction. The Sobel-on-derived variant is reported as a
  sensitivity so the choice is visible rather than assumed.
- **Threshold rule**: per buffer, per scene, per view, the response threshold is the 90th
  percentile of that response over off-crease foreground, i.e. **FPR = 10% exactly, by
  construction**, the same rule everywhere. Nothing is tuned to any scene.
- **Detection**: a miss-set pixel counts as detected if a thresholded pixel lies within 1.5 px
  of it, the campaign's standing tolerance.

## Buffers
Mesh-free: vanilla depth, depth-disc, vanilla normal, normal-disc, alpha, 2DGS normal.
**Perfect-geometry oracle arm** (EVAL-ONLY, never a method): GT-mesh-rendered depth, and the
normal derived from that exact depth by back-projection. This arm is what makes a negative
unconditional.

## FROZEN GO/NO-GO
- **GO** iff some mesh-free buffer detects **>= 25%** of the cadpartA miss set **AND >= 15%**
  of the lego miss set at FPR <= 10%, **AND** the two best buffers' detected miss subsets have
  **Jaccard <= 0.70** (genuinely complementary, not redundant).
- **NO-GO** otherwise.
- **UNCONDITIONAL KILL** if the perfect-geometry arm also misses those bars: the ceiling is
  then in the asset and the label set rather than in the reconstruction, no buffer and no
  combination can move it, and the branch closes instead of being retried with another kernel.
- Combination, if it ever happens, is parameter-free union/max only. No weights.

## Author's prior, recorded so it can be wrong
cadpart passes on the 2DGS normal buffer and fails on every vanilla buffer; lego fails on all
of them including perfect geometry; the honest outcome is a branch that works only on clean
solids with a second reconstruction, which is where Step 2 already left us.

---

# RESULTS

## 1. Miss-set detection, all buffers, FPR = 10% by construction

Fraction of the shipped pipeline's uncovered GT crease pixels that each buffer detects within
1.5 px, pooled over all 10 held-out TEST views.

| buffer | cadpartA (44,625 miss px) | lego (239,853 miss px) | bar |
|---|---|---|---|
| **2dgs_normal** | **0.9870** | **0.2081** | **clears both** |
| 2dgs_normal_disc | 0.9871 | 0.1288 | fails lego |
| normal_disc | 0.0852 | **0.4348** | fails cadpart |
| normal | 0.0508 | 0.3185 | fails cadpart |
| depth_disc | 0.0215 | 0.2959 | fails cadpart |
| depth | 0.0203 | 0.2306 | fails cadpart |
| alpha | 0.0397 | 0.1065 | fails both |
| *normal_disc_sobel (sens)* | *0.0865* | *0.4037* | sensitivity |
| *depth_disc_sobel (sens)* | *0.0214* | *0.1501* | sensitivity |
| **ORACLE mesh_normal** | **1.0000** | **0.7002** | oracle |
| ORACLE mesh_normal_disc | 1.0000 | 0.6002 | oracle |
| ORACLE mesh_depth | 0.6810 | 0.4712 | oracle |

Bars were 0.25 on cadpartA and 0.15 on lego. **Exactly one mesh-free buffer clears both:
`2dgs_normal`.**

## 2. The dominant effect is the reconstruction, not the kernel

On cadpartA the 2DGS normal buffer detects **98.7%** of the miss set while every vanilla
buffer detects **under 9%**, a 12x to 49x gap from changing which reconstruction produced the
buffer. The Sobel-versus-derived-map sensitivity moves the same numbers by less than 0.002.
This is the claim the design argue made from the featviz L15 separations, now measured
directly: **a preference matrix over kernels would have spent its budget on the axis that
barely moves.**

## 3. The winning buffer INVERTS between the two scenes

| scene | best mesh-free buffer | its score | where 2dgs_normal ranks |
|---|---|---|---|
| cadpartA | 2dgs_normal | 0.9870 | 1st |
| lego | normal_disc (vanilla) | 0.4348 | **5th of 7**, at 0.2081 |

The only buffer clearing both bars scrapes the lego bar at 0.2081 while four vanilla buffers
beat it there. That is the same non-transport pattern that killed the threshold family in
Steps 6 to 10, and it matters for what comes next: **picking the best buffer per scene would
be per-scene selection by the back door.** Only a parameter-free union or max taken over all
buffers identically is admissible, which is what the plan already required.

The inversion is consistent with banked evidence: the 2DGS normal regulariser reads a planar
face at near zero and is scope-limited to clean solids, scoring 0.3307 on lego against
vanilla's 0.3875 in DIAG2DGS.

## 4. The Jaccard leg failed on MY specification defect

As frozen, the leg selects "the two best buffers" by detection fraction. On cadpartA the two
highest entries are `2dgs_normal_disc` and `2dgs_normal`, which are **the same underlying
buffer under two operators**, so their Jaccard is **1.0000 by construction** and the leg fails.

That is a defect in my specification, not a property of the data. In the design argue I warned
that derived maps are deterministic functions of their parents and should be treated as
operator outputs rather than as buffers, then listed them as buffers anyway and failed to
exclude that redundancy from my own top-2 rule.

**Under the evidently-intended reading, two distinct parent buffers, the leg passes clearly:**

| scene | two best DISTINCT buffers | Jaccard | bar |
|---|---|---|---|
| cadpartA | 2dgs_normal_disc, normal_disc_sobel | **0.0877** | <= 0.70 |
| lego | normal_disc, depth_disc | **0.3042** | <= 0.70 |

Both are far inside the bar, so the buffers are genuinely complementary: on cadpart the 2DGS
and vanilla normal buffers detect almost disjoint parts of the miss set, and on lego the
normal and depth families overlap on only 30% of what they find.

**I am not re-gating.** The frozen verdict is NO-GO. But a one-line specification fix, select
the top two among distinct parent buffers, flips it to GO, and that call is the user's to make
before any re-run rather than mine to make after seeing the answer.

## 5. The perfect-geometry arm CLEARS the bars, so this is not an unconditional kill

`ORACLE mesh_normal` detects **1.0000** of cadpartA's miss set and **0.7002** of lego's. The
ceiling is therefore **not** in the asset or the label set. Perfect geometry does see the edges
we currently miss, and at least 70% of lego's miss set is geometrically present.

Two cautions on reading that. It is an upper bound on geometry-based detection **given
geometry we can never have mesh-free**; the lego stud family is real in the mesh and merely
absent from the photographs and from the reconstruction, so the oracle seeing it does not make
it recoverable. And it does not contradict the earlier DIAG2DGS result where a GT-mesh arm
scored AUC 0.3964 on lego: that measured discrimination between crease and decal-distractor
loci with a ball-based dihedral, whereas this measures whether an edge operator fires near a
missed crease pixel. Different questions, not in conflict.

## 6. A methodological hole I am disclosing

**There is no null control in this run.** The bars of 0.25 and 0.15 were set by judgement, not
calibrated against what a random detector at the same 10% FPR would achieve after 1.5 px
dilation. The cross-buffer comparisons are safe, since every buffer shares the FPR, the
tolerance and the miss set, and a 12x ratio between 2DGS and vanilla on cadpart is far beyond
anything a null could explain. But **a marginal absolute pass, specifically lego's 0.2081,
should not be over-read**, and a null arm belongs in any follow-up.

## 7. Artifacts

`out/bufferedge.json`, `out/bufferedge_det_{cadpartA,lego}.npz` (per-buffer detected miss
subsets, for the pairwise Jaccard matrix also stored in the json), `scripts/bufferedge.py`,
`logs/bufferedge.log`. Nothing committed.
