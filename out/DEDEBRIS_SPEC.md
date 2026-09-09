# NEXT POLISH — DE-DEBRIS the merge fill (visual-first, object-space, direct run no heavy workflow)

Your MERGE GO was honest and I accept it: 1.90x arc, cut 0.0001, trunk byte-identical. But you
flagged the real cost yourself — a dozen short off-crease stubs on flat faces + one visibly wavy
front-face stroke. On a polyhedron those read as DEBRIS / lines drawn where no edge exists. That
is the CLEAN leg and the "don't draw clean lines in the wrong place" invariant, not a P/R nitpick.
So the next step is to REMOVE that debris WITHOUT touching the trunk and without losing the real
newly-drawn completeness (ledge line, top hole edges, right-face verticals).

## Adversarial framing (push back on me if wrong)
Claim: the stubs survive because min-length + RANSAC straightness is a SHAPE test, and a short
off-crease mark can be perfectly straight. What they lack is CARRIER SUPPORT — a true crease has a
depth/normal discontinuity under it and dense DexiNed cloud evidence along its whole length; a
false stub sits on a flat face with thin, one-sided support. So gate the FILL strokes (never the
trunk) on an OBJECT-SPACE support score, physical/scale-relative, NOT a per-scene tuned count:
  - per fill stroke, fraction of its vertices whose local DexiNed-cloud density (within a
    pixel-anchored radius) exceeds the merged-set median => drop strokes below a fixed fraction
    (propose 0.5, justify from the width criterion, not fitted per scene);
  - AND/OR require the stroke to lie on a depth OR normal discontinuity in the frozen 2DGS buffers
    (you already have liftarm depth_disc / normal_disc maps) — a flat-face stub has neither.
The wavy front-face stroke: either it fails the support gate, or tighten RANSAC (raise inlier
threshold) so a bendy chain splits/drops. Do NOT special-case it by hand.

## PRE-REGISTERED VISUAL GO/NO-GO (worded on the image, not P/R)
GO if the de-debrised still: (a) NO LONGER shows the flat-face stubs or the wavy front stroke
(clean), (b) STILL keeps the ledge line + top-hole edges + right-face verticals that the merge
newly drew (does not regress completeness below the merge on the real edges), and (c) strip stays
steady, cut <= 0.0102. NO-GO if it also strips real completeness or the debris survives — report
straight and we keep the merge as-is.
Reported-not-gated: stroke count, median verts, total arc, P/R, P_pop + cut. Expect arc to DROP
slightly (debris removed) — that is correct, not a regression.

## Deliverable
Re-render out/featviz/stroke_cadpartA_merge_still.png (overwrite is fine, git has the prior) PLUS
a NEW clean vs merge side-by-side diff stroke_cadpartA_dedebris_diff.png showing exactly which
fill strokes were dropped, + the consecutive-frame strip. Same camera, same stroke settings.
Write results to out/DEDEBRIS_RESULTS.md with the support-gate threshold and its scale-relative
justification, and the declared polyhedron-scope limit restated. Object-space only, mesh
EVAL-ONLY, never fabricate, report negatives straight. Direct run, no heavy multi-agent workflow.
