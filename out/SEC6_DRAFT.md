# §6 — Limitations (DRAFT v1)
*(All numbers from `RESULTS_MASTER.md`. Nothing here is softened; several of these limits
were established by our own pre-registered gates coming back negative.)*

**In-vitro scope.** Everything in this paper is measured on frozen 3DGS reconstructions of
two static NeRF-synthetic scenes with known poses and rendered depth — an in-vitro
geometric characterization, owned as such rather than patched. Every baseline shares the
same perfect-geometry assumptions (the accumulated baseline is *given* our exact rigid
flow), so the comparisons are internally fair, but n=2 synthetic scenes with perfect
geometry is the breadth we have; real captures, estimated poses, and more scenes are
future work, not implied results.

**The selectivity evidence is single-scene.** The §5.1 demonstration that our pipeline
actively suppresses texture edges — higher precision than its own seed edge field at
matched density — holds on chair only. On lego, per-frame Canny is *more precise than our
lines at every density we reach*; our advantage there is stability alone. Selectivity is
demonstrated on the texture-bound scene and not contradicted on the geometry-dense one.
The stability claim itself does not lean on this: §4.1's dominance rule compares stability
only at operating points the baselines actually share on both precision and density, so
§4's ratios survive on lego with no selectivity assumption at all.

**The temporal advantage is interior-only, and reverses at disocclusions.** Decomposing
the hardest cell (§4.4): the entire advantage is interior EMA-drift suppression — pop-rate
0.0214 vs the oracle accumulator's 0.0425, **1.98×**, over the 93–97 % of line pixels away
from occlusion boundaries — while inside disocclusion regions **our method is worse**
(0.407 vs 0.300): visibility-culled chain runs split and their endpoints shift. Our
pre-registered mechanism gate ("≥60 % of the accumulator's residual lies in disocclusion
regions") came back **33.3 %**, a NO-GO, so we claim **no** disocclusion-correspondence
mechanism for why 2D accumulation trails; the temporal bound is empirical.

**Precision is not solved — it is supervision-bound.** The crease-vs-texture signal exists
in frozen DINOv2 features (0.8401/0.9044 with mesh labels) but collapsed to **0.6371**
under our best mesh-free supervision, through a pre-registered 0.72 gate (NO-GO). The one
measured route forward — cross-scene transfer of a mesh-supervised probe — works in one
direction of the two tested (0.8245 chair→lego, 0.5626 reverse). Any deployment needing
crease-level precision on textured surfaces currently needs labeled scenes.

**Geometry cannot rescue it (K_geom ≈ 0).** This is not an artifact of our reconstruction:
even the **GT mesh's own dihedral scores AUC 0.3964** on crease-vs-decal, with
normal-dispersion class medians 0.32° apart. On decal-like structure there is no geometric
signal to find, for any method that seeds on geometry.

**Coverage is ceiling-bound.** Re-ranking the frozen carrier caps recall at R@1.5 =
**0.7908 (chair) / 0.5572 (lego)**; on lego **0.3663** of visible GT crease points have no
carrier within 1.5 px at all (flat decals prominent among them). Our lines cannot draw
what the carrier never represented, and §5.2 shows the recovery attempts we falsified.

**Further disclosed limits, collected.** Four limits disclosed elsewhere belong in this
list too: all pipeline constants were selected during development with mesh-scored
validation views (§3.4); the pooled-*mean* stability statistic failed its own 3× gate at
one point (2.42×, §4.2); no third-party static-curve method was compared (§2, an
evaluation boundary); and the shared operating points on lego sit at P@1.5 ≈ 0.63 with the
baseline's highest-precision configurations excluded by the dominance rule (§4.3).

**Evaluation dependency.** GT supervision (crease labels, precision/recall scoring) comes
from the mesh, confined to `mesh_oracle.py` and the eval scripts — the method path never
imports it (AST-verified per phase). The flip side of this hygiene: our quantitative
evaluation is only available where GT meshes exist, which is part of why the study is
in-vitro.
