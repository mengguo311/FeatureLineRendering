# PARETO-3: disocclusion decomposition of the accumulated-baseline residual (the mechanism behind lego-T3 1.72×)

CONTEXT: PARETO-2 NO-GO on the letter at exactly ONE cell — lego × T3 adversarial spline,
worst pop>2px advantage 1.72× (< the frozen 2× floor) at Canny 50/150 @ α=0.85. Three-way
consensus (agy conceded R2): freeze 1.72× as a conservative lower bound vs the oracle-flow
ceiling; do NOT run RAFT (weaker baseline → would inflate our number = defending). Instead
DECOMPOSE where the residual advantage lives, to test whether the gap is a STRUCTURAL
disocclusion-correspondence limit no 2D accumulation can bypass.

## Build (reuse ALL PARETO-2 infra; only region-masking + per-region tally is new)
- Fix the operating point: lego, T3_spline, best accumulated baseline = Canny 50/150 @
  α=0.85 (the 1.72× point); dominating OURS point = the min-pop OURS row at that shared point
  (recompute from out/pareto2_lego_T3_spline.json — the OURS row that achieves P≥baseline and
  px≤baseline with lowest pop>2px). Report both methods' per-pixel pop>2px map over all 239
  transitions.
- DISOCCLUSION MASK per transition t→t+1: a frame-t line-mask ON pixel is "disocclusion" if
  its oracle forward-warp lands where (a) t+1's rendered depth disagrees with the warped
  depth beyond an epsilon (occluded), OR (b) the warp leaves the interior/frame. Reuse the
  exact rigid-flow warp + rendered depth already in scripts/pareto2_flowacc.py. Freeze
  epsilon a priori from the depth-map scale (e.g. 2% of median scene depth) BEFORE tallying.
- TALLY: of the accumulated baseline's residual pop>2px pixels, what FRACTION lie in
  disocclusion regions vs interior? Same split for OURS (expected: OURS' depth-test drops
  disoccluded lines entirely, so OURS residual should be interior-dominated / tiny).
- Report per-region pop>2px RATE (not just fraction) so the mechanism is quantitative:
  baseline interior-pop vs disocclusion-pop, OURS interior-pop vs disocclusion-pop.

## FROZEN GO/NO-GO (three-way, do not move after numbers exist)
- GO (mechanism generalizes → strengthens the bounded claim): ≥60% of the accumulated
  baseline's residual pop>2px pixels lie in disocclusion regions at this point.
- NO-GO (residual is diffuse interior instability): <40% in disocclusion regions → the claim
  stays purely empirical/bounded, no mechanism sentence.
- GRAY (40–60%): report as partial-mechanism, quote the number, no strong causal sentence.

## Output
out/PARETO3_RESULTS.md (honest, thorough), out/pareto3_lego_T3_disocc.json,
scripts/pareto3_disocc.py, optional out/pareto3_disocc_overlay.png. Mesh EVAL-only; the
disocclusion mask uses only rendered depth + poses (method-path clean). If GO, add ONE
mechanism sentence to the paper's temporal-coherence section draft. This is a path-C
hardening control, not a path-B revival.

NOTE: dss9 coding agent hit its Fable session limit (resets 3am Asia/Tokyo). Pick this up at
the next bare-prompt fire after reset; work persists on disk. Everything needed is in
out/pareto2_lego_T3_spline.json + scripts/pareto2_flowacc.py.
