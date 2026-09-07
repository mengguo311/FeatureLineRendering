# DISCUSSION — is 3Doodle's method viable / useful for OUR frozen-3DGS feature-line project? (NO CODE, analysis)

Adversarial feasibility discussion. You already hold our full project state in context (round-1 FeatureGS/
EdgeGaussians analysis + the f=1.00 VERIFY_F100 NO-GO). NO code, NO file edits except writing your final analysis
to /tmp/m1b_3doodle.txt via a single cat heredoc at the end, then print it. I will push back hard.

## THE PAPER — 3Doodle (Choi et al., SIGGRAPH 2024, arXiv 2402.03690)
"Compact Abstraction of Objects with 3D Strokes." Reconstructs a SPARSE set of 3D strokes from MULTI-VIEW IMAGES,
no sketch dataset, no mesh, no NeRF. Two primitive families, optimized end-to-end by DIFFERENTIABLE rendering:
- VIEW-INDEPENDENT: 3D cubic Bezier curves (4 control points each) = the view-independent 3D feature lines
  (ridges/valleys/sharp edges/texture edges). Orthographic-projection approximation makes a 3D cubic Bezier
  project to a 2D cubic Bezier (their Theorem 1), so rendering the curve to a 2D stroke canvas is differentiable.
- VIEW-DEPENDENT: contours of a union of SUPERQUADRICS (implicit f(x)=1, union = min of implicits) = the smooth
  occluding-contour outline whose 3D locus moves with viewpoint.
- OPTIMIZATION: directly optimize the compact parameters (control points + superquadric shape/scale/pose) to
  minimize PERCEPTUAL losses — CLIP + LPIPS — between the rendered stroke image and the input multi-view images.
  Coarse-to-fine, superquadrics first then Bezier, a robustness loss for mixed scenes. Output <1.5 kB, ~tens of
  strokes. Tested on NeRF-synthetic (Bezier-only there); compares against NEF, ARF, Suggestive Contours, CLIPasso.

## WHY THIS MIGHT MATTER TO US (and why it might not) — be adversarial
Our project: extract CLEAN, TEMPORALLY-STABLE 3D feature lines from a FROZEN vanilla 3DGS, NPR line rendering.
Banked crown jewel: object-space lines 3.4-11.5x more temporally coherent than per-frame Canny (held-out). Our
line drawings are ROUGH/fragmented; the fragmentation follows the coverage ceiling; f=1.00 buys static recall
(lego 0.29->0.56) but WRECKS temporal via fragmentation (P_pop ratio 11.5x->2.8x, NO-GO). Two kernel-preproc
papers (FeatureGS/EdgeGaussians) were argued non-viable last round. mesh EVAL-ONLY is sacred; we run from a
FROZEN 3DGS (post-hoc) and protect the temporal win.

## QUESTIONS (answer each with a verdict, use our banked numbers, disagree with me where warranted)
Q1. 3Doodle optimizes PARAMETRIC 3D primitives (Bezier + superquadrics) end-to-end against perceptual losses on
   the raw multi-view IMAGES — NOT against a detector's edge maps, and NOT re-ranking a fixed gaussian pool. Does
   this ESCAPE our two hard bottlenecks — (a) the coverage ceiling (no-carrier creases) and (b) the DexiNed 2D
   recall ceiling / the epipolar NO-GO — because its supervision is the images + CLIP/LPIPS semantics rather than
   thresholded edges? Or does the perceptual loss just re-introduce the SAME missing-signal problem (the 30.000-deg
   stud tessellation is smooth in the images too, so CLIP/LPIPS sees no line there either)?
Q2. The COMPACTNESS + PARAMETRIC continuity (each stroke is a smooth cubic Bezier, tens of strokes total) directly
   attacks our FRAGMENTATION problem — a Bezier is continuous by construction and its 3D locus is fixed, so it
   should be temporally coherent BY CONSTRUCTION, like our object-space linelets but without the split/merge
   flicker that killed f=1.00. Is 3Doodle's representation strictly BETTER than our linelet+chain for the temporal
   goal? Where does it break — does perceptual-loss optimization of a tiny parameter set sacrifice the geometric
   FIDELITY/recall we measure at 1.5px (i.e. it draws a pretty abstract sketch, not an accurate feature-line map)?
Q3. Compatibility with our FROZEN 3DGS. 3Doodle takes multi-view images and needs NOTHING pre-built (no mesh, no
   NeRF). We have the images AND a frozen 3DGS that gives depth/occlusion/silhouette for free. Could we run
   3Doodle's differentiable-Bezier optimization but (i) initialize the Bezier control points from our Phase-1b
   triangulated cloud / our linelets instead of random, and (ii) use the frozen 3DGS depth as an occlusion/visibility
   prior in the rendering (which 3Doodle lacks — it has no depth), and (iii) supervise against DexiNed edge maps
   OR the raw images? Is a "3DGS-anchored 3Doodle" a real, novel, buildable direction, or does it inherit the same
   ceilings dressed up as strokes? Name where the 3DGS actually adds information 3Doodle doesn't already have.
Q4. The competitor threat + honest recommendation. 3Doodle already runs on NeRF-synthetic (our exact scenes:
   lego/chair/ficus family) and beats NEF/Suggestive-Contours on abstraction — and its 3D strokes are static, so
   they'd inherit temporal coherence FOR FREE just like ours. Is 3Doodle a BASELINE we must cite/compare against
   (does it threaten our crown jewel the way a static-curve baseline would?), a COMPONENT we could build on
   (3DGS-anchored strokes), or NEITHER? Give ONE cheap decisive experiment with a pre-registered go/no-go if there
   is a worthwhile test, or state plainly it doesn't move our needle and exactly why. Be concrete about metrics.
Note our real difference: 3Doodle optimizes for PERCEPTUAL abstraction (CLIP/LPIPS "looks like a sketch"); WE
optimize for geometric feature-line ACCURACY (P/R@1.5 vs GT mesh crease set) + temporal coherence. These are
different objectives — address whether that difference makes 3Doodle irrelevant to our metric, or a reframing
opportunity for our whole thesis.

Write the full analysis to /tmp/m1b_3doodle.txt. Do NOT launch a heavy multi-agent workflow — a direct rigorous
analysis from context + a couple of targeted repo/paper reads is what I want. Cite our numbers.
