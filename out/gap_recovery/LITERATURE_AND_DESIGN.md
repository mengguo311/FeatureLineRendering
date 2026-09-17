# Persistent evidence-gated 3D bridges — literature and design

2026-09-18. Research baseline: `9e643c2408954dffcfa8b298d5204e7314863a91`.
This is a falsifiable local repair experiment, **not an established novel method**.
Sources below were queried online in this session. F = opened original full text;
P = opened author/project/institutional abstract, not full technical verification;
S = search metadata only. No secondary summary is treated as a verified algorithm.

## Classification before recovery

* **G1 visible extraction gap:** an otherwise supported perceived stroke has a missing
  middle interval on a visible surface, with two existing 3D chain endpoints. Target.
* **G2 occlusion gap:** a carrier may already continue in 3D but its projection is
  hidden. Never patch this in screen space or loosen visibility to obtain a success.
* **G3 deliberate endpoint / different neighboring structures:** reject. Proximity
  and projected intersections do not establish physical connectivity.

Human G1 markings are evaluation annotations only; the selector must never read them.
If the audit cannot identify three clear G1 examples, the prescribed task-instance
gate fails. Do not manufacture gaps by deleting vertices or label ambiguous G2 as G1.

## Literature that changes the design

| Source / verification | Verified relevance and limits |
|---|---|
| David Mumford, **Elastica and Computer Vision**, author archive dates 1993. [Author archive](https://www.dam.brown.edu/people/mumford/vision/shape.html), [scanned original](https://www.dam.brown.edu/people/mumford/vision/papers/1993b--Elastica-Harvard.pdf). P; original scan opened but text extraction unavailable. | Classical continuation prior motivates short, smoothly turning connections. A cubic Hermite interpolant with length/turn bounds is only a low-degree proxy: this experiment does not solve the Euler-elastica variational problem or claim it as new. |
| David J. Field, Anthony Hayes, Robert F. Hess, **Contour integration by the human visual system: Evidence for a local “association field”**, 1993. [DOI](https://doi.org/10.1016/0042-6989(93)90156-Q). S; DOI access failed. | Background for good continuation only. No quantitative perceptual threshold is taken from an unread paper. |
| Mi-Suen Lee, Gérard Medioni, Chi-Keung Tang, **Tensor Voting**, 2000. [Author institutional record](https://researchportal.hkust.edu.hk/en/publications/tensor-voting-2/), [DOI](https://doi.org/10.1007/978-1-4615-4413-5_12). P; DOI full text unavailable. | Directional neighborhood aggregation is prior art. We do not implement or claim a new tensor-voting field; a local density check is merely an unsupported-space veto, not a surface or topology certificate. |
| Pierre Bénard, Jingwan Lu, Forrester Cole, Adam Finkelstein, Joëlle Thollot, **Active Strokes: Coherent Line Stylization for Animated 3D Models**, 2012. [Project](https://pixl.cs.princeton.edu/pubs/Benard_2012_ASC/index.php), [paper](https://gfx.cs.princeton.edu/pubs/Benard_2012_ASC/Benard_2012_ASC.pdf). F. | Image-space snakes track, connect and smooth line samples; separate brush paths provide coherent stylization. Their object/image separation is prior art. Fig. 2 cautions that screen continuity need not imply 3D connectivity. Here bridges are fixed offline 3D curves, not evolving per-frame snakes; GS visibility can remove their hidden parts. |
| Robert D. Kalnins, Philip L. Davidson, Lee Markosian, Adam Finkelstein, **Coherent Stylized Silhouettes**, 2003. [Project](https://pixl.cs.princeton.edu/pubs/Kalnins_2003_CSS/index.php). P. | Coherent brush parameterization on changing silhouette configurations is prior art. Persistent IDs alone are not a contribution. The opened project does not establish a particular GS occlusion algorithm. |
| Xiangyu Zhu, Dong Du, Weikai Chen, Zhiyou Zhao, Yinyu Nie, Xiaoguang Han, **NerVE: Neural Volumetric Edges for Parametric Curve Extraction from Point Cloud**, CVPR 2023. [Original paper](https://arxiv.org/pdf/2303.16465). F, Sec. 3 and supplement A.2. | Explicitly reconnects nearby degree-one vertices with compatible tangents, then fits curves. Endpoint linking plus good continuation is therefore **not novel**. Our experiment adds visibility-conditioned multi-view evidence to veto local bridges on an existing frozen carrier; it does not learn a volumetric edge representation. |
| Haiyang Ying, Matthias Zwicker, **SketchSplat: 3D Edge Reconstruction via Differentiable Multi-view Sketch Splatting**, ICCV 2025. [Original full text](https://arxiv.org/html/2503.14786v2). F, Sec. 4.2–4.3. | The closest overlap: parametric 3D curves, multi-view image optimization, endpoint merging, collinear gap closing and topology operations. Cannot claim the combination “3D bridge + image loss” as new. Here existing curves remain fixed; a small finite bridge set is accepted/rejected with visible contradiction versus occluded/unobservable evidence explicitly separated. Whether that restriction has practical value is the experiment, not a proven research contribution. |
| Yunfan Ye, Renjiao Yi, Zhirui Gao, Chenyang Zhu, Zhiping Cai, Kai Xu, **NEF: Neural Edge Fields for 3D Parametric Curve Reconstruction from Multi-view Images**, CVPR 2023. [arXiv](https://arxiv.org/abs/2303.07653). P; PDF access failed. | Learns a neural edge field from multi-view 2D edge observations and extracts parametric curves. Shared evidence/3D output principle; our finite local repair avoids training a reconstruction field. Exact NEF endpoint-repair rules are not verified here. |
| Chenggang Yang, Yuang Shi, **LineGS: 3D Line Segment Representation on 3D Gaussian Splatting**, 2024 preprint. [Full text v3](https://arxiv.org/html/2412.00477v3), [record](https://arxiv.org/abs/2412.00477). F. | Gaussian geometry supports refinement of initialized line segments. GS-neighborhood support and 3D line carriers are not new. We do not claim a verified LineGS gap-closing implementation or publication status beyond the preprint. |
| Changwoon Choi, Jaeah Lee, Jaesik Park, Young Min Kim, **3Doodle: Compact Abstraction of Objects with 3D Strokes**, 2024. [Full text](https://arxiv.org/html/2402.03690v2), [DOI](https://doi.org/10.1145/3658156). F. | Optimizes 3D Bézier abstraction and superquadric contours with multi-view perceptual evidence. Its stated wireframe/depth-order limitation differs from our mandatory depth clipping. Persistent stylizable curves or multi-view optimization are not ours to claim. |
| Cihan Topal, Cüneyt Akınlar, **Edge Drawing: A combined real-time edge and segment detector**, 2012. [Institutional publication abstract](https://research.itu.edu.tr/tr/publications/edge-drawing-a-combined-real-time-edge-and-segment-detector/), [DOI](https://doi.org/10.1016/j.jvcir.2012.05.004). P. | Anchor-guided edge tracing yields connected image segments. Such chains can provide orientation/continuation evidence but cannot certify 3D topology or become final per-frame ink. This first test uses fixed blurred Canny and nearest-edge gradient tangents to avoid introducing another detector variable. |

TEED's ICCVW 2023 primary search result was found, but its page could not be opened;
no performance or implementation claim relies on it. No detector sweep is planned.

## Minimal hypothesis and algorithm

**Persistent 3D Bridge Hypotheses × Multi-view Image Evidence** (PEGB, descriptive
name only): given fixed vanilla-only chains, does multi-view visible edge evidence
reject a wrong geometric continuation while retaining visibly useful G1 repairs?

1. Pair endpoints of different existing chains using distance relative to median
   Gaussian neighbor spacing and outward tangents. No image intersection creates a
   pair. One deterministic cubic Hermite proposal per pair, with fixed derivatives.
2. Bound arc/chord ratio and turn; require Gaussian-neighborhood support along the
   whole curve. This is a conservative air-gap check, not a learned surface model.
3. Project into TRAIN views with full K. GS-depth-hidden samples are **unevaluable**,
   not edge failures. Visible samples in front of unsupported/background depth or
   across an abrupt depth layer are a rejection condition. Edge DT and tangent
   evidence are measured in the middle of the gap, not just at its supported ends.
4. Require support in multiple camera directions, then rank by geometric confidence
   times image support. Each endpoint can participate in at most one accepted bridge.
   Freeze selected 3D vertices/IDs; original chain vertices are never altered.
5. Enforce both <=20 bridges and <=5% added visible length on each fitting view,
   plus a conservative 3D-length cap. Final video budget is audited independently;
   failure is not repaired by selecting on final cameras.

Object-only uses the same candidate curves and budgets, without image edge scores.
Visibility is identical for original, object-only and evidence-gated ink. Held-out
TRAIN/DEV views validate selected bridges; they cannot choose bridges or thresholds.
Canonical TEST/VAL images are never needed. No mesh, GT labels, dd3 normals, networks,
GS retraining, vertex pulling, endpoint deletion or per-frame inpainting is allowed.

The old GS-disc depth buffer is approximate and can itself cause G2 fragmentation.
Official full-SH RGB is used for display, not confused with that depth estimator.
Failure to see three genuine G1 cases, failure to improve the drawings, or failure
of the evidence veto is a NO-GO even if all unit tests pass.

## Audit acquisition frozen before viewing new results

Audit only TRAIN [1,27,53,79]. Chair reuses the hash-verified clean VRSS full pool,
not its selected subset. Lego and cadpartA regenerate the exact VRSS vanilla recipe
(16 TRAIN views, seed fraction .30, 100 pull steps, unchanged pruning/chaining).
No old cache with uncertain TRAIN provenance is loaded. Parameters are identical
across audit scenes; the audit does not optimize the candidate generator. Existing
historical reports are used only to identify unsafe lineage, never mesh labels.
Candidate generation is bounded to 10 minutes per scene after CPU smoke. The scene
decision and fixed bridge parameters will be committed in PREREG/MANIFEST before
evidence scoring, bridge selection or opening a new complete evaluation orbit.
