# Track O — Temporal-Coherence Trajectory Stress-Test (harden the CORE)

## Why
Precision arc (Tracks L/M/N/NG-MEC) has converged: chair cull marginal-dP ~+0.01..+0.022, lego ~0. Cross-model invariance shown (TEED/PiDiNet/DexiNed). Framing = NG-MEC is a view-inconsistency INVARIANCE mechanism (not an N=2 "law"). We STOP chasing precision.
The paper lives or dies on the TEMPORAL-COHERENCE win (linelets 8.5-13.1x more coherent than per-frame Canny/TEED). ALL prior temporal numbers were on a SMOOTH CIRCULAR ORBIT. Untested: does the win (and does NG-MEC culling) survive NON-TRIVIAL camera motion? Suspected failure mode = view-boundary popping when the epipolar-consensus angle threshold is crossed mid-trajectory.

## Task
Freeze the winning pipeline TEED + NG-MEC. On chair (texture-stress, held-out TEST cams only; mesh_oracle for eval ONLY, never in method path), build 3 held-out camera trajectories, each 240 frames:
  T1 = smooth orbit (the existing baseline motion — sanity anchor)
  T2 = orbit + radial zoom (in/out) — tests scale/parallax
  T3 = multi-axis spline (azimuth+elevation swing, non-constant angular velocity) — tests consensus-angle crossings
For each trajectory compute the existing stroke temporal-coherence metric (flow-warped Chamfer ratio vs per-frame) for THREE arms:
  A = per-frame TEED (2D baseline, no object-space carrier)
  B = TEED + object-space linelets, NO cull (unculled)
  C = TEED + NG-MEC cull (the winner)
Report ratio (coherence multiplier vs per-frame A) at frame windows {30,60,120,240} for B and C on all three trajectories. Also report C/B ratio (does culling degrade temporal stability?).

## Frozen GO / NO-GO (decide the paper claim)
Using the SAME metric definition as m1b_stroke_temporal_table_*:
- GO (temporal win is trajectory-robust, culling is safe):
    * min over {T1,T2,T3} of arm-C 240-frame multiplier >= 8.0x  AND
    * for every trajectory, C/B 240-frame coherence ratio >= 0.95  (cull preserves >=95% of unculled temporal stability)
- NO-GO (popping / motion-fragile): any trajectory where C 240f multiplier < 8.0x OR C/B < 0.95 -> report the offending trajectory, quantify the drop, and we fall back to reporting arm B (unculled) as the temporal headline while keeping C only for the precision table.
Report both B and C numbers regardless so the decision is data-driven. No fabricated numbers; write out/track_o_temporal.json + a short out/TRACK_O_RESULTS.md.

## Invariants
mesh NEVER in method path (eval only). Held-out cams only. Do not touch non-u00134 procs. CUDA_VISIBLE_DEVICES=1.
