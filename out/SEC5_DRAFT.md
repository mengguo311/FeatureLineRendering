# §5 — The precision boundary: a four-act characterization (DRAFT v1)
*(Contribution B, diagnostic. All numbers from `RESULTS_MASTER.md`; Fig 6–8, Tab 3–4.
Throughout, the GT mesh labels and scores only — it never enters the method path.)*

## 5.1 Act 1 — the ceiling exists, and what it does and does not mean

The primitive of §4 operates at a bounded precision, and the bound begins with coverage:
re-ranking the frozen gaussian pool — keeping *everything* — caps pipeline recall at
R@1.5 = 0.7908 (chair) / 0.5572 (lego); the pool's own 2D coverage is 0.7382 / 0.6337, and
on lego 0.3663 of visible GT crease points have no carrier within 1.5 px at all (Fig 6).
Some of those uncovered creases are flat decals with literally zero geometric footprint.

This admission invites a specific attack, so we answer it here rather than in a rebuttal:
*if the lines live on a baked radiance carrier, is §4's stability just the passive
reprojection of 2D edges — an inherited artifact that this ceiling proves?* No, and the
matched-density protocol of §4.1–4.2 is the direct evidence. On the texture-bound scene,
the carrier surface under a high-contrast fabric edge is indistinguishable from the
carrier under a crease — on this population the fabric-bound rows of Act 2 apply directly
(the albedo-step gate leaks, 0.1235 vs 0.1211, and multi-view consistency does not
separate, 0.870 vs 0.937), and the geometric cues of Tab 3 are at or below chance on the
decisive decal population — yet at matched line density our extracted set is substantially **more precise than the
photometric edge field itself** (P@1.5 0.662 at 4,947 px/frame vs per-frame Canny 0.532 at
5,973 px/frame; Fig 2): the pipeline actively **suppresses** texture edges that enjoy the
same carrier support and the same image contrast as the creases it keeps. That is genuine
multi-view selectivity performed by the object-space aggregation — work the carrier could
not have done for us (Act 2) and the 2D edge field did not do for us (Fig 2) — not passive
reprojection. (We disclose the converse case with equal prominence: on lego, where strong
image edges largely *are* creases, per-frame Canny is more precise than our lines at every
density; there our advantage is stability only.) The ceiling, then, bounds *which* creases
the primitive can carry — it says nothing against *how stably* it carries them, which is
§4's claim and survives at matched precision and density.

## 5.2 Act 2 — no geometric cue separates the miss-set (K_geom ≈ 0)

Could a better geometric gate recover the uncovered creases or reject the texture? On the
decisive population (lego decals vs true creases), every geometric channel is at or below
chance (Tab 3): 2DGS surfel dihedral 0.4110, rendered-normal ribbons 0.3307/0.3875, and —
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
chain-level read, against ≈0.71 photometric and ≈0.65 geometric baselines (Fig 7). Read
honestly, the probe recognizes *which surface* a point lies on — fabric field vs piping,
stud field vs decal — a surface-identity readout rather than an edge-type detector. The
signal the primitive needs exists, in features every modern pipeline already has.

## 5.4 Act 4 — and it is supervision-bound under our frozen protocol

The signal exists (0.8401/0.9044) — but it collapses under mesh-free supervision: trained
on our best mesh-free pseudo-labels (physics-frozen geometric-photometric votes, and a
fully self-supervised clustering variant), the same probe falls to **0.6371** on chair
through a pre-registered 0.72 gate (0.9046 → 0.6569 on lego), beneath even its photometric
baseline. The failure mode is instructive: the pseudo-labels' errors are systematic, not
noisy, and the richer representation learns them the more faithfully — zero denoising. One
route stays open, and we measured it: the mesh-supervised probe transfers chair→lego at
**0.8245**, nearly matching lego's in-scene ceiling, though not in reverse (0.5626).
Precision is therefore **supervision-bound under our frozen protocol** — with labeled
training scenes as the named, tested-in-one-direction path forward.

## 5.5 What the boundary buys

This characterization is what licenses §4's scope. The arc — coverage bounded by the
carrier (5.1), the miss-set geometrically invisible (5.2), the discriminator semantic and
extant (5.3), its mesh-free readout falsified through a frozen gate (5.4) — explains
*why* we ship a stability primitive at a measured precision rather than patching precision
with an in-scene oracle: every patch we tested either equals chance, stays
detector-bound, or requires supervision the method path is not allowed to touch. The
boundary is measured, disclosed, and has exactly one open door.
