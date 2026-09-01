# PARETO-2: oracle-flow temporally-accumulated 2D edge baseline (the memoryless-strawman defuse)

THREE-WAY CONSENSUS (agy + dss9 agent agree): the #1 unaddressed reviewer threat to the
temporal-coherence claim is that our Canny/PiDiNet baselines are MEMORYLESS. Defuse it by
building the STRONGEST possible temporally-accumulated 2D baseline and putting it on the SAME
three-axis Pareto as OURS. If even an oracle-flow accumulator cannot close the gap, no RAFT
variant can.

## Build (reuse banked infra; interior-restricted --fg_only like PARETO-1)
- Baselines to accumulate: per-frame Canny (the banked (50/150) plus the sweep points already
  in pareto_{scene}.json) and PiDiNet (nms_thin). For each, add a temporally-accumulated
  variant: edge_t_acc = rethreshold( EMA_alpha * warp(edge_{t-1}_acc; ORACLE FLOW) + (1-alpha)*edge_t ).
- ORACLE FLOW = the EXACT rigid flow we already use in PARETO-1 (rendered depth + the two
  camera poses, identical warp operator). NOT RAFT. This is deliberately the strongest baseline.
- Sweep accumulation strength alpha in {0.0 (=memoryless, sanity=PARETO-1), 0.3, 0.5, 0.7, 0.85}
  x the existing detector-threshold sweep. Each (detector,thr,alpha) is one Pareto point.
- Metrics: identical to PARETO-1 — P@1.5 (mesh EVAL-only oracle DTs), density (line px/frame),
  pooled pop-rate P(d>2px) and P(d>3px), pixel flicker (1px XOR/union), pooled-mean E_warp.
- Scenes chair+lego; trajectories T1 orbit AND T3 spline (the stress condition — floor matters
  less there so it is the honest hard case). Disocclusion regions expected to tear for the
  accumulated baseline; report pop-rate restricted to disocclusion pixels if cheap.

## FROZEN GO/NO-GO (three-way, do not move after numbers exist)
- GO (temporal claim SURVIVES): OURS pop>2px advantage >= 3x at EVERY shared matched-P-and-density
  point vs the BEST accumulated baseline, on BOTH scenes.
- NO-GO (re-scope honestly, do NOT defend): advantage < 2x at ANY shared point, OR the accumulated
  baseline MATCHES our precision at matched density.
- In between (2x-3x): report as a bounded/qualified claim, headline the pop/flicker floor-free stat.

Write out/PARETO2_RESULTS.md (thorough, honest), out/pareto2_{chair,lego}.{json,png},
out/pareto2_verdict.json, scripts/pareto2_flowacc.py. Mesh EVAL-only; method path mesh-free.
Reuse banked f-sweeps + PARETO-1 warp glue; only the accumulation loop + rethreshold is new.
