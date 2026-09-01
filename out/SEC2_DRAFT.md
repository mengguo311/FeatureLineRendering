# §2 — Related Work (DRAFT v1)
*(Our own measurements cited here are ledger-exact from `RESULTS_MASTER.md`.)*

**Per-frame image-space edge detection.** Classical (Canny) and learned (DexiNed, TEED,
PiDiNet) detectors produce precise, dense 2D edge maps per rendered frame and are, for our
purposes, the **precision reference we trade against rather than claim to beat**: on the
geometry-dense scene, per-frame Canny on the same rendered inputs is more precise than our
lines at every density we reach (§5.1). What per-frame detection cannot supply is
identity over time — most of its strokes do not survive a single frame transition (§4.5)
— and §4 shows that even granting this family an oracle-flow temporal accumulator does
not close the stability gap at matched precision and density.

**3D edge and curve reconstruction from multi-view edges.** EMAP ("3D Neural Edge
Reconstruction", CVPR 2024) and its successors learn a neural **unsigned distance field to
edges** from multi-view 2D edge maps and extract parametric curves from it. This line of work fuses *edges of any kind*: the field
inherits whatever the 2D detector fires on, with no mechanism to distinguish a geometric
crease from a printed texture boundary. Our boundary characterization (§5.2) quantifies
exactly this blind spot as a representational fact rather than an implementation gap —
on decal-like structure, *no* geometric cue separates the classes, **including the
ground-truth mesh's own dihedral (AUC 0.3964)** — so edge-field fusion, like our carrier,
is semantics-blind by construction; the separating signal is semantic (§5.3) and
supervision-bound (§5.4).

**SketchSplat** [arXiv 2503.14786] optimizes parametric 3D edges differentiably against
multi-view 2D edge maps, and motivates its design in part by the observation that
detectors mis-fire on shading textures and produce view-inconsistent edge shifts. Two of
its ideas map onto our study with opposite outcomes. Its **curve-level aggregation** —
deciding at the curve, not the pixel — transfers well: our chain-level reads consistently
strengthen per-point signals (§5.3). Its **view-consistency premise** — that texture
mis-fires can be filtered because they are view-inconsistent — **does not transfer to our
setting**: on rigid, static scenes, printed *albedo* texture edges are fixed surface loci
and reproject almost as consistently as true creases (multi-view consistency 0.870 vs
0.937; §5.2), so a consistency filter cannot carry the crease-vs-texture decision here —
whereas the specular and shading-induced mis-fires that motivate the premise are a
different error population that our scenes barely contain. We read this as a domain statement, not a criticism of SketchSplat's results on its own
benchmarks. A fair question is why no EMAP/SketchSplat-style static-curve output appears
as a *stability* baseline: any static object-space curve set shares our by-construction
stability, so between static primitives the discriminating axes are precision, coverage
and density — which our §5 characterization addresses at the representation level (its
semantic-blindness result is representation-independent — even the GT mesh's dihedral
scores 0.3964 — and so applies to any edge-seeded method, theirs included; the coverage
ceiling, by contrast, is measured for our carrier only)
— and our frozen evaluation did not extend to third-party curve sets. We state this as an
evaluation boundary, not an implied superiority.

**Temporal coherence in stylized rendering.** Coherent line drawing and stylization
classically bind strokes to object space or propagate them with flow — the standard
answers to flicker. Our contribution to this literature is not the idea of object-space
binding but its **measurement discipline**: stability compared only at matched precision
AND matched line density, against an accumulator granted oracle flow, with pre-registered
gates and the failure envelope (disocclusion reversal, 1.72× floor) reported as part of
the claim.

**Feature lines from 3D representations.** Mesh-based feature-line extraction (ridges,
valleys, suggestive contours) presumes trustworthy surface geometry. A frozen 3DGS offers
no such thing at fine scales; §5's four-act arc measures how far post-hoc extraction can
go on such a carrier and where it stops — the ceiling (§5.1), the geometric blindness
(§5.2), and the supervision bound (§5.4).
