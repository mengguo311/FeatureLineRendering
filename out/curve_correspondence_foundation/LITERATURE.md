# Targeted literature and adversarial check

Verified 2026-09-19 before new method outputs. This is targeted reading, not an
exhaustive review or benchmark. Links below are original papers/author sources;
reading levels are explicit. No performance ranking is imported into this test.

| Source and verified scope | Consequence for this experiment |
|---|---|
| [Schmid & Zisserman, Automatic Line Matching across Views, CVPR 1997](https://www.robots.ox.ac.uk/~vgg/publications/1997/Schmid97/schmid97.pdf), abstract and matching formulation | Epipolar-constrained appearance matching and third-view disambiguation are classical. A calibrated correspondence pipeline is not novel. |
| [Fabbri & Kimia, Multiview Differential Geometry of Curves](https://arxiv.org/abs/1604.08256), abstract | Theory distinguishes stationary curves, occluding contours and nonrigid curves. Static-edge assumptions cannot certify every silhouette. |
| [Usumezbas, Fabbri & Kimia, From Multiview Image Curves to 3D Drawings, ECCV 2016](https://arxiv.org/html/1609.05561v1), introduction and curve-sketch/topology sections | Describes Curve Sketch's epipolar hypothesis pairs and confirmation views, then explicit curve connectivity. Epipolar tangencies, gaps, redundant fragments and topology are established difficulties. We abstain at tangencies and never infer unsupported connections. |
| [Ohta & Kanade, Stereo by Two-Level Dynamic Programming, IJCAI 1985](https://www.ijcai.org/Proceedings/85-2/Papers/093.pdf), introduction and sections 2–3 | Ordered correspondence paths and connected-edge consistency predate modern networks. Their scanline ordering has exceptions. Our order is only along a single split curve with one global reversal; it is not a global front-to-back scene ordering claim. We use explicit unique-intersection order checking, not their full DP method. |
| [Liu et al., 3D Line Mapping Revisited (LIMAP), CVPR 2023](https://b1ueber2y.me/projects/LIMAP/limap.pdf), sections 3.1–3.3 | Full line systems include degeneracy handling, track association, junction/point/vanishing-point structure and robust reprojection refinement. Two-view line residual alone cannot certify identity. Our sparse curve test is simpler and does not claim to outperform LIMAP or reproduce its structural machinery. |
| [NEF](https://arxiv.org/html/2303.07653v2), sections 3.1–3.2 | Learns an edge field from images, then fits parametric curves. Our correspondence-first diagnostic avoids a learned field; persistent parametric reconstruction is already established. |
| [EMAP](https://arxiv.org/html/2405.19295v1), introduction, representation and extraction overview | Learns distance and direction through a UDF and extracts parametric edges. The present image-only arm is not EMAP and cannot establish superiority over it. Explicit correspondence ambiguity is the test object, not a new representation. |
| [EdgeGaussians](https://arxiv.org/html/2409.12886v1), abstract and section 3.2 | Optimizes Gaussians for edge images. Its edge-trained primitive semantics cannot be assigned to the frozen RGB GS. We neither retrain nor identify edges using Gaussian IDs. |
| [CurveGaussian](https://arxiv.org/html/2506.21401), abstract and method overview | Couples Bézier curves and Gaussians with direct optimization and topology changes. Gaussian-to-curve reconstruction and direct curve optimization are not new. Our fixed identity certificates and invariance audit are a narrower experiment. |
| [SketchSplat](https://arxiv.org/html/2503.14786v2), method overview, detector and initialization sections | Differentiable parametric sketch splatting already exists; default geometry-assisted detector inputs and EdgeGS initialization differ from fixed Canny on RGB. No default performance result supplies evidence for this frozen-input experiment. |

The 2000 Schmid/Zisserman Oxford repository record was search-visible but direct
access returned 403; detailed claims here rely on the accessible 1997 paper.
The CVF LIMAP PDF returned 403; the author's identical-title PDF was accessible.
The CMU Ohta/Kanade landing page returned 503; the IJCAI paper was accessible.
The original 2010 Curve Sketch paper was not separately read; the 2016 authors'
account is the verified source for the limited description above.

The strongest adversarial objections remain: coarse Canny segments may change
identity under fragmentation; constant-color edges have weak descriptors;
epipolar tangency can prevent along-curve localization; cycles can consistently
match repeated parts; shadows can be static and still be visually irrelevant;
camera coverage can make strict three-view support too sparse. BA may reduce
residual without curing a wrong identity, so it begins only after identity is
frozen and is bounded. GS filtering trivially leaves retained geometry unchanged;
only measured coverage/error improvement can justify its contribution.

Novelty ceiling: an audited, preregistered feasibility/abstention experiment under
fixed inputs and qualified radiance-posterior perturbations. Neither correspondence
graphs, curve BA, fixed 3D polylines nor matched-ink NPR are claimed as inventions.
STOP concerns this frozen minimal formulation, not an impossibility theorem for
classical curve SfM or all cross-view correspondence.
