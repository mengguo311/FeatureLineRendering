# §5 — The precision boundary: a four-act characterization (DRAFT v1)
*(Contribution B, diagnostic. All numbers from `RESULTS_MASTER.md`; Fig 6–8, Tab 3–4.
Throughout, the GT mesh labels and scores only — it never enters the method path.)*

## 5.1 Act 1 — the ceiling exists, and what it does and does not mean

The primitive of §4 operates at a bounded precision, and the bound begins with coverage:
re-ranking the frozen gaussian pool — keeping *everything* — caps pipeline recall at
R@1.5 = 0.7908 (chair) / 0.5572 (lego); the pool's own 2D point coverage is 0.7382 /
0.6337 — on chair the pipeline's recall exceeds point coverage because rasterized segments
interpolate *between* carriers, so the binding form of the ceiling is lego's, where 0.3663
of visible GT crease points have no carrier within 1.5 px at all and interpolation cannot
manufacture one (Fig 6).
Some of those uncovered creases are flat decals with literally zero geometric footprint.

This admission invites a specific attack, so we answer it here rather than in a rebuttal:
*if the lines live on a baked radiance carrier, is §4's stability just the passive
reprojection of 2D edges — an inherited artifact that this ceiling proves?* Not on the
evidence — though the evidence is single-scene, as §6 states plainly. On the texture-bound scene,
the carrier surface under a high-contrast fabric edge is indistinguishable from the
carrier under a crease — on this population the fabric-bound rows of Act 2 apply directly
(the albedo-step gate leaks, 0.1235 vs 0.1211, and multi-view consistency does not
separate, 0.870 vs 0.937), and the geometric cues of Tab 3 are at or below chance on the
decisive decal population — yet our extracted set is substantially **more precise than the photometric edge field
itself** — P@1.5 0.662 at 4,947 px/frame vs per-frame Canny 0.532 at 5,973 px/frame, and,
in the dominance-consistent direction (ours denser AND more precise), 0.636 at 7,942
px/frame vs the same 0.532 (Fig 2): the pipeline actively **suppresses** texture edges that enjoy the
same carrier support and the same image contrast as the creases it keeps. That is genuine
multi-view selectivity performed by the object-space aggregation — work the carrier could
not have done for us (Act 2) and the 2D edge field did not do for us (Fig 2) — not passive
reprojection. The converse case gets equal prominence: on lego, where strong image edges
largely *are* creases, per-frame Canny is more precise than our lines at every density;
there our advantage is stability only. The ceiling, then, bounds *which* creases
the primitive can carry — it says nothing against *how stably* it carries them, which is
§4's claim and survives at matched precision and density.

## 5.2 Act 2 — no geometric cue separates the miss-set (K_geom ≈ 0)

Could a better geometric gate recover the uncovered creases or reject the texture? On the
decisive population (lego decals vs true creases), no geometric channel is usable (Tab 3;
several score *below* chance — decals locally out-score creases — so even sign-flipped
they reverse the intended semantics): 2DGS surfel dihedral 0.4110, rendered-normal ribbons 0.3307/0.3875, and —
the controlling result — the **GT mesh's own dihedral, 0.3964**, with normal-dispersion
medians 44.52° vs 44.84°: given *perfect* geometry, the two classes differ by 0.32°. The
low-level photometric escape routes close the same way: the SH-DC albedo-step gate leaks
(fabric p50 0.1235 vs crease 0.1211), and multi-view consistency does not separate
(texture 0.870 vs crease 0.937 — printed patterns are rigid surface loci too). Coverage
recovery fares no better: single-view photometric lifting equals its chance control
(R_miss 0.0952 vs 0.0940), and multi-view triangulation, though a genuine localization
fix, stays detector-bound at MARGINAL (recall 0.6753 / miss-set recovery 0.6914; Fig 6b).

## 5.3 Act 3 — the separating signal exists

The missing discriminator is not hiding in geometry; it is semantic. A linear probe on
frozen zero-shot DINOv2 features separates crease from texture at AUC **0.8401 / 0.9044**
(chair / lego, held-out spatial split), 0.8205 / 0.8913 under the leakage-guarded
chain-level read, against ≈0.71 photometric and ≈0.65 geometric probe baselines on the candidate
population — a different population and feature set from §5.2's decal test, which is why
a nonzero geometric number here does not contradict K_geom≈0 there (Fig 7). Read
honestly, the probe recognizes *which surface* a point lies on — fabric field vs piping,
stud field vs decal — a surface-identity readout rather than an edge-type detector. The
signal the primitive needs exists, in features every modern pipeline already has — though
Act 4 shows that reading it out is supervision-bound.

## 5.4 Act 4 — and it is supervision-bound under our frozen protocol

The signal exists (0.8401/0.9044) — but it collapses under mesh-free supervision: trained
on our best mesh-free pseudo-labels (physics-frozen geometric-photometric votes, and a
fully self-supervised clustering variant), the same probe falls to **0.6371** on chair
through a pre-registered 0.72 gate (on lego 0.9046 — the ceiling as recomputed in this
study; 0.9044 in Act 3's split — falls to 0.6569), beneath even its photometric baseline:
the best mesh-free number *anywhere* is the chair photometric probe at 0.7326 — touching
the gate on one scene, 0.5637 on the other — while the semantic probe collapses on both. The failure mode is instructive: the pseudo-labels' errors are systematic, not
noisy, and the richer representation learns them the more faithfully — zero denoising. One
route stays open, and we measured it: the mesh-supervised probe transfers chair→lego at
**0.8245**, nearly matching lego's in-scene ceiling, though not in reverse (0.5626).
Precision is therefore **supervision-bound under our frozen protocol** — with labeled
training scenes as the named, tested-in-one-direction path forward. Appendix A closes the
loop at deployment granularity: used as an actual gate on the line-candidate cloud, the
deployment-legal direction of that transfer (0.5626, chance) leaves precision untouched,
and even an in-scene mesh oracle cannot filter the cloud to the pipeline's precision
without severing crease connectivity.

## 5.5 What the boundary buys

This characterization is what licenses §4's scope. The arc — coverage bounded by the
carrier (5.1), the miss-set geometrically invisible (5.2), the discriminator semantic and
extant (5.3), its mesh-free readout falsified through a frozen gate (5.4) — explains
*why* we ship a stability primitive at a measured precision rather than patching precision
with an in-scene oracle: every patch we tested either equals chance, stays
detector-bound, requires supervision the method path is not allowed to touch, or — when
granted that supervision as an explicit oracle — fragments the very chains it is meant to
purify (Appendix A). The boundary is measured, disclosed, and has exactly one open door:
labeled scenes feeding a topology-aware construction, not a post-hoc filter.
