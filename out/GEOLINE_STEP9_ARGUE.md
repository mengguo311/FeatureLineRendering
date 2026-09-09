# STEP 9 DESIGN ARGUE — NO CODE, NO GPU. You are my adversarial partner, not a yes-man. Push back where I am wrong.

## Where we are (agreed facts from Step 5/6/8)
The multi-view consensus statistic RANKS good>bad within every solid (AUC 0.82-0.94 over 5 solids incl. the concave gstep). But its DISTRIBUTION is not comparable across objects: the realized absolute cut at each object's own optimum spans 0.30 (icosa) to 0.68 (gstep), 2.25x. No absolute constant and no percentile/keep-fraction constant clears all 5. The threshold-on-a-scalar family is dead.

## The trap I want us to NOT fall into
"Make the statistic comparable" most naively means per-scene self-normalization to a percentile/rank. But that IS the keep-fraction family Step 8 just falsified (a percentile constant cannot span the distributions that produce the 2.25x spread). So comparability CANNOT come from the statistic's own within-scene rank alone. It must come from either (A) an EXTERNAL scene-agnostic PHYSICAL variable that the raw statistic is confounded by, divided out; or (B) abandoning global magnitude comparison entirely for a spatially-LOCAL / relative decision. I claim any "normalization" that only reads the statistic's own distribution is already refuted and off the table.

## Two candidates
- CAND A (physical de-confound): the per-object distribution shift is driven by a measurable nuisance covariate (local candidate/gaussian DENSITY, n_visible_views, local gaussian SCALE, or convex/concave crease fraction). Divide the raw consensus statistic by that physical quantity -> distributions collapse -> ONE frozen absolute cut clears all 5. Scene-agnostic by construction (physical, no per-object knob).
- CAND B (local decision): replace the global cut with a spatially-local top-k / local-contrast decision (keep candidates that are locally extremal in their neighborhood), so no cross-object magnitude comparison ever happens. Scale-free by construction.

## My proposed CHEAPEST-FALSIFICATION-FIRST experiment (zero GPU, banked data only)
Before building EITHER normalizer, run the discriminating diagnostic on the 5 solids' already-on-disk per-candidate statistics + labels:
1. For each solid compute its "realized optimal absolute threshold" t*_obj (already have these: 0.30..0.68).
2. Regress t*_obj (and/or the full good/bad statistic distributions) against candidate PHYSICAL object-level covariates: mean local candidate density, mean n_visible, mean gaussian scale, concave-edge fraction, object world-scale.
3. VERDICT: if ONE physical covariate linearly explains the shift (e.g. R^2>=0.8 over 5 points, and dividing it out shrinks the 5 admissible-interval intersection from EMPTY to non-empty) -> CAND A is alive, pursue it. If NO physical covariate explains it (magnitude is irreducibly object-bound) -> CAND A dead, pivot to CAND B local decision.

## Your job (NO CODE this turn)
Expert synthesis + adversarial critique. Specifically:
(a) Is my "self-normalization is already refuted" claim airtight, or is there a comparability transform that reads only the statistic yet is NOT a percentile (e.g. fitting a 2-component mixture per scene and using the posterior)? If so it is a third candidate C — argue its merit vs A/B.
(b) 5 objects is a tiny regression n=5 — is the covariate diagnostic even powered, or am I fooling myself? Propose the honest version (rank correlation? leave-one-out?).
(c) Which of A/B/C is highest-EV and cheapest to falsify FIRST, and what is the exact frozen go/no-go number? Converge to ONE experiment. Do NOT start coding — answer in prose, I will push back then we dispatch.
