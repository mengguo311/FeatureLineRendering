# Abstract + §1 Introduction (DRAFT v1)
*(All numbers from `RESULTS_MASTER.md`.)*

## Abstract

Line drawings rendered from per-frame image-space edge detection flicker: strokes appear,
vanish, and re-form with every camera step. We present an **interior temporal
stabilization primitive** for feature lines bound to a *frozen* 3D Gaussian Splatting
reconstruction: static object-space 3D polylines, projected per frame with a visibility
test. This is deliberately not a general 3D line detector: view-dependent silhouettes are out
of scope by construction, exhaustive recovery of geometric creases is a ceiling we measure
rather than hide, and at disocclusion boundaries our stability advantage reverses — a
limit we quantify. Per-frame 2D detection remains the precision reference we trade
against rather than claim to beat. What the
primitive buys is stability where it counts: on a three-axis protocol that compares
methods only at **matched precision and matched line density**, our lines pop
**1.72–8.35×** less per scene×trajectory condition (two synthetic scenes × two
trajectories, four conditions; a third trajectory appears in the stroke-level results)
than the strongest 2D baseline we could construct — an EMA accumulator
driven by *oracle* rigid flow, so no estimated flow can improve its inputs — with 1.72× as the frozen
conservative floor at the adversarial worst cell, and ≥9.8× less than memoryless
detectors. A second contribution characterizes why the primitive's precision is bounded
rather than patching it: coverage is capped by the frozen carrier; the missing creases
carry no geometric signal even under the ground-truth mesh (AUC 0.3964); the
crease-vs-texture signal *exists* in frozen DINOv2 features (AUC 0.8401/0.9044) yet
collapses to 0.6371 under our best mesh-free supervision through a pre-registered 0.72
gate — precision is supervision-bound under our frozen protocol, not solved. Every
experimental gate in the paper was frozen before its numbers existed; all outcomes,
including the unfavorable ones, are reported.

## 1. Introduction

Stylized and technical renderings of 3D scenes want *lines* — creases, seams, part
boundaries — and they want those lines to hold still. A line drawing produced by running
an edge detector on every rendered frame is precise frame-by-frame but temporally
incoherent: most of its strokes do not survive even one frame transition. With 3D Gaussian
Splatting (3DGS) now a standard scene representation, we ask a narrow question: given a
*frozen* 3DGS — no retraining, no densification — can feature lines be bound to the
reconstruction so that they are *stable* under camera motion? We answer for the interior
of the object only, and we say up front what this work is **not**: it is not a general 3D
line detector — it does not attempt exhaustive recovery of dihedral creases (a ceiling we
measure, not hide), it does not draw view-dependent silhouettes (all methods, ours and
baselines, are evaluated interior-restricted), and its stability advantage *reverses* at
disocclusion boundaries, which we quantify rather than average away.

The difficulty in evaluating such a primitive is that temporal-stability claims are cheap:
a method looks stable if it draws fewer lines, easier lines, or vaguer lines. Our protocol
closes these doors. Every method traces an operating curve over precision and line
density, and stability is compared only at operating points shared on *both* axes; the
stability statistic is pooled per line-pixel through an exact rigid-flow warp, so vanished
lines are charged automatically. And because per-frame detection has an obvious repair —
warp and accumulate edges over time — we build the strongest member of that family we know
how to construct: an EMA accumulator given our own *oracle* rigid flow with an
occlusion-aware fallback — no estimated flow can improve on its inputs, though we make no
claim over accumulator designs beyond this family.

Against this ceiling, the primitive's advantage is **1.72–8.35×** fewer popped line-pixels
per condition (≥5.19× in three of four; the fourth — the maximum-occlusion-flux spline on
the geometry-dense scene — sets the frozen 1.72× floor), and ≥9.8× against memoryless
detectors at every shared point. The advantage is interior (1.98× at the hardest cell) and
is a property of the parameterization: it is invariant to the acceptance threshold across
the full sweep where measured, while per-frame detectors destabilize as they sparsify.

Precision is the other half of the story, and we do not claim to have solved it. Per-frame
image-space detection is the precision reference this primitive trades against: on the
texture-bound scene our lines exceed the seed edge field's precision at matched density —
evidence of genuine multi-view selectivity — but on the geometry-dense scene per-frame
Canny stays more precise at every density we reach. Rather than patch this gap with an
in-scene oracle, we characterize it: a four-act forensic bounds the achievable precision
(carrier coverage ceiling; no geometric cue on the miss-set, even from the GT mesh; the
separating signal exists in frozen semantic features; and it collapses without mesh
supervision through a pre-registered gate), ending at a named, one-direction-tested route
forward. The boundary is the contribution; pretending it away is not.

**Contributions.** (verbatim from the contribution box)
1. **A temporally stable interior line primitive for frozen 3DGS** — 1.72–8.35× less
   popping than an oracle-flow accumulated 2D baseline at matched precision and density
   (≥5.19× in three of four conditions; 1.72× frozen floor), ≥9.8× vs memoryless
   detection; per-frame 2D detection remains the precision reference we trade against,
   not a baseline we claim to beat in general.
2. **A measured precision boundary** — the four-act characterization ending
   supervision-bound under our frozen protocol (signal exists 0.8401/0.9044; mesh-free
   0.6371 vs a 0.72 gate; transfer 0.8245 one direction), with every recovery attempt we
   falsified reported.
3. **Pre-registered gates as method** — every gate frozen before its numbers existed and
   evaluated on its letter, unfavorable outcomes included. The mesh-free guarantee is a
   runtime and test-time property; development-time model selection used mesh-scored
   *validation* views, disclosed in §3.4.
