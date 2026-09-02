# §3 — Method (DRAFT v1)
*(Protocol constants are the ledger's; the pipeline is described structurally — its
operating points are swept in §4, not fixed here.)*

## 3.1 The invariant, first

One rule governs everything downstream, and we state it before the pipeline: **the
ground-truth mesh never enters the method path** — a runtime and test-time guarantee whose
development-time boundary we disclose in §3.4. It is confined to a single evaluation
module (`mesh_oracle.py`) that labels held-out GT crease points and scores
precision/recall — nothing the pipeline computes, at any stage, reads it (AST-verified
per phase). Every signal the method consumes comes from the frozen 3DGS itself (gaussian
positions, opacities, rendered depth/normal/alpha buffers) and from rendered images of the
80 training views; the 10 test views and all test trajectories are held out from every
fitting step.

## 3.2 A coarse object-space carrier, corrected by image-space evidence

The design splits the labor between two unequally reliable sources. The **carrier** is
coarse and 3D: the frozen gaussian cloud (de-floatered by opacity and a k-NN spacing
test) anchors *where in space* feature lines may live and supplies visibility — but its
fine-scale geometry is untrustworthy (§5.2), so it is never asked to localize an edge.
The **corrector** is precise and 2D: per-view edge probability maps from **TEED** — a
frozen, zero-shot, BIPED-trained detector of 58,910 parameters, chosen among frozen
detectors on validation views and never fine-tuned — NMS-thinned, thresholded at 0.5, and
converted to sub-pixel **distance-transform (DT) fields**, one per training view. Short oriented 3D segments ("linelets" — a position, a unit tangent, and a half-length,
one per kept carrier seed, initialized from the carrier's local structure) are then
optimized by gradient descent so that samples along their projections descend these DT
fields *in many views simultaneously* — the multi-view DT pull, run for a fixed iteration
budget with a per-step displacement cap. A linelet that sits on a real 3D feature
line finds a consensus position that is on-edge in most views at once; one seeded on a
single-view artifact cannot. Robust per-view statistics accumulated during the pull provide the acceptance
criterion — a linelet is kept iff it is visible in ≥3 pull views with inlier fraction
≥0.50 and median on-edge residual ≤1.5 px (frozen defaults) — and a single keep-fraction
knob over the carrier's seed ranking traces the operating curve that §4 sweeps.

## 3.3 From linelets to renderable, stable strokes

Accepted linelets are non-maximum-suppressed in 3D and greedily chained into polylines
using tangent and collinearity consistency, yielding a static set of object-space 3D
strokes — computed **once** for the frozen scene. Rendering at a novel camera is then
projection plus occlusion: each vertex is tested against the 3DGS z-buffer (a 3×3-min
window with a small relative tolerance), strokes are split into visible runs, and runs
are rasterized at one pixel. Temporal stability is not enforced by any tracking,
smoothing, or hysteresis — there is nothing to track, because the primitive is static in
object space; §4 measures what this buys and §4.4 what it costs (the visibility split is
exactly why our advantage reverses at disocclusion boundaries).

## 3.4 Where the invariant stops: hyperparameter provenance

The AST-checked invariant of §3.1 is a statement about the *runtime* method path. We
extend it, honestly, to the experimenter: the frozen view split (80 train / 10 validation
/ 10 test) governs all selection — pipeline constants (detector and threshold, de-floater
cutoffs, acceptance defaults, chaining tolerances) were chosen during development using
scores on *validation* views, and those development-time scores did use the evaluation
oracle; that is a disclosure, not a violation, because every number this paper reports is
computed on the 10 held-out **test** views and on test-anchored trajectories that no
selection step ever consumed, under gates frozen before the numbers existed. What
pre-registration covers here is the reported evaluation, not the existence of a
development loop — and with n=2 scenes there is no held-out *scene*, a scope limit §6
owns. This loop is also why §5.4 matters beyond the discriminator: deploying on a
mesh-less scene would require mesh-free selection, whose strongest tested form §5.4
bounds; the tested mitigation is cross-scene transfer of development-time choices
(0.8245 in the one direction that worked).

**Frozen constants (committed defaults, printed for reproduction).** De-floater:
opacity > 0.1 and k-NN (k=8) mean spacing < 3× its median. Detector: TEED, probability
NMS-thinned, threshold 0.5. DT pull: 100 gradient steps, learning rate 0.35, per-step
displacement cap 5.0 px. Acceptance: visible in ≥3 pull views, inlier fraction ≥0.50,
median residual ≤1.5 px. Chaining: 3D NMS radius 1.0× local spacing, k=10 neighbors,
tangent cosine ≥0.60, collinearity cosine ≥0.50, gap ≤4.0× spacing, ≥3 nodes per stroke.
Visibility: 3×3-min z-buffer window, relative tolerance 0.02. Seed construction and
half-length initialization follow the released implementation (`src/seeds.py`,
`src/dt_pull.py`), which we release.

## 3.5 What the method does not contain

No mesh in the runtime path (§3.1, provenance in §3.4). No per-frame optimization. No
temporal filter. No learned component beyond the frozen zero-shot 2D detector whose
evidence the DT pull aggregates. The
evaluation protocol (matched precision-and-density comparison, pooled warp metric,
interior restriction) is specified with the experiments in §4.1, because it is shared by
every baseline rather than being part of the method.
