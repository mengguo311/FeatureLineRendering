# Path-C Deliverable: Matched-Precision + Matched-Density Coherence Pareto (the #1 defense figure)

Preempts the hostile-reviewer "consistent GARBAGE" attack (temporal win is a trivial byproduct of object-space parameterization, useless because precision stays texture-polluted). Three-way consensus (orchestrator + agy + this agent).

## Build (reuse banked artifacts — ~90% done; only sweep-glue is new)
Two scenes (chair, lego). Curves on the SAME held-out TEST split used for the banked 7-13x temporal-coherence result. Do NOT touch the method path; mesh EVAL-ONLY.
- OURS (object-space lines): sweep the line-acceptance threshold to trace out an operating curve.
- BASELINES: per-frame image-space Canny AND PiDiNet (reuse the Track N/O + CMEPI caches). Sweep their thresholds too.
- Axes: x = precision (P@1.5, held-out); y = temporal coherence (E_warp, POOLED across all lines/pixels — NOT per-line, NOT per-pixel-of-line — sparse sticky sets must not be flattered).

## The two confounds that MUST be neutralized (this agent's trap-catch)
1. DENSITY: fewer lines flicker less. Report a THIRD control axis = matched rendered line-pixel density (or matched recall). Compare ours vs baselines only at MATCHED precision AND MATCHED density.
2. NORMALIZATION: E_warp must be pooled over the whole line set, not averaged per-line.

## Frozen gate
At MATCHED precision AND MATCHED density, object-space coherence advantage >= 3x at EVERY shared operating point (both scenes).
- PASS: gap holds >=3x everywhere shared -> this is the paper's headline figure, temporal win proven orthogonal to the supervision ceiling.
- FAIL: if density-matching collapses the gap (advantage <3x at any shared point), that COLLAPSE becomes the headline instead — reported honestly, NOT buried. Either outcome is publishable; fabricating a gap is not.

## Deliverable
out/PARETO_RESULTS.md with both-scene frontier plots (out/pareto_{chair,lego}.png), the matched-P/matched-density comparison table, pooled-E_warp definition stated explicitly, and the verdict against the frozen gate. Do NOT commit until numbers are in and the gate is evaluated.
