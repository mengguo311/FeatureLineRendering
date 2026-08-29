# Track O — temporal-coherence trajectory stress-test: **NO-GO**, and the offender is the *easy* trajectory

Chair, TEED + NG-MEC, three held-out 240-frame trajectories, held-out TEST cams only.
No mesh is imported anywhere in this track (`scripts/track_o_temporal.py` is mesh-free; the
scene centre is the median gaussian position). Metric operator identical to
`m1b_stroke_temporal_table_*` — `sequence_metrics` is imported and called, not reimplemented,
and is invoked twice per trajectory so B and C are scored by the same code against the same
baseline frames. Protected manifest **332/332 OK, 0 failures**.

## Verdict

| trajectory | B 240f | C 240f | C/B 240f | C ≥ 8.0× | C/B ≥ 0.95 |
|---|---|---|---|---|---|
| T1 orbit *(sanity anchor)* | 14.32× | **12.73×** | **0.8892** | ✓ | **✗** |
| T2 orbit + zoom | 12.85× | **12.64×** | 0.9841 | ✓ | ✓ |
| T3 multi-axis spline | 11.10× | **11.49×** | 1.0351 | ✓ | ✓ |

- min-over-trajectories arm-C 240f multiplier = **11.49×** ≥ 8.0 → **PASS**
- min-over-trajectories C/B 240f = **0.8892** < 0.95 → **FAIL** (offender: **T1_orbit**)

### CALL: **NO-GO** — one criterion fails, on one trajectory.

Per the frozen NO-GO branch: **fall back to arm B (unculled) as the temporal headline, and
keep C only for the precision table.** Arm B is trajectory-robust — min 240f multiplier
**11.10×**, comfortably clearing 8.0× on all three motions.

## The suspected failure mode did not happen — the opposite did

The spec's hypothesis was view-boundary popping when the epipolar-consensus angle threshold is
crossed mid-trajectory, i.e. the cull should hurt most on *hard* motion. The data say the
reverse:

| trajectory | motion difficulty | C/B 240f |
|---|---|---|
| T1 orbit | easiest (smooth, constant angular velocity) | **0.8892** ← worst |
| T2 orbit + zoom | scale/parallax stress | 0.9841 |
| T3 multi-axis spline | hardest (elevation swing, non-constant velocity) | **1.0351** ← cull *helps* |

**NG-MEC culling is temporally neutral-to-beneficial exactly where it was predicted to fail,
and costs ~11% of the coherence gain only on the smooth orbit.** On T3 the culled arm is
*better* than the unculled one (1.035), and on T2 it is within 1.6%. There is no
consensus-angle-crossing pathology.

A plausible reading, offered as a hypothesis and not as a measured claim: on the smooth orbit
the unculled linelets include view-consistent-but-redundant strokes that happen to warp
stably, so removing them costs coherence; under harder motion those same strokes are the
unstable ones, so removing them helps. Testing that would need a per-stroke survival analysis
which Track O did not run.

## Full table — all frame windows, all trajectories

Multiplier = P_pop(per-frame TEED) / P_pop(arm). Arm A is per-frame TEED on the rendered
frame (not Canny): Track O's question is whether the object-space carrier beats the *same*
learned detector applied per frame.

| trajectory | frames | A P_pop | B P_pop | **B mult** | C P_pop | **C mult** | C/B |
|---|---|---|---|---|---|---|---|
| T1 orbit | 30 | 0.8533 | 0.0928 | 9.20× | 0.0995 | 8.58× | 0.9325 |
| | 60 | 0.8439 | 0.0679 | 12.43× | 0.0759 | 11.11× | 0.8937 |
| | 120 | 0.8390 | 0.0588 | 14.28× | 0.0678 | 12.38× | 0.8673 |
| | **240** | 0.8239 | 0.0575 | **14.32×** | 0.0647 | **12.73×** | **0.8892** |
| T2 orbit+zoom | 30 | 0.8607 | 0.1186 | 7.26× | 0.1183 | 7.27× | 1.0024 |
| | 60 | 0.8484 | 0.0863 | 9.83× | 0.0868 | 9.77× | 0.9938 |
| | 120 | 0.8382 | 0.0704 | 11.90× | 0.0714 | 11.73× | 0.9856 |
| | **240** | 0.8342 | 0.0649 | **12.85×** | 0.0660 | **12.64×** | **0.9841** |
| T3 spline | 30 | 0.8866 | 0.2533 | 3.50× | 0.2440 | 3.63× | 1.0382 |
| | 60 | 0.8580 | 0.1439 | 5.96× | 0.1376 | 6.23× | 1.0452 |
| | 120 | 0.8359 | 0.0934 | 8.95× | 0.0882 | 9.48× | 1.0592 |
| | **240** | 0.8127 | 0.0732 | **11.10×** | 0.0707 | **11.49×** | **1.0351** |

### Two observations worth carrying into the paper

1. **The win is trajectory-robust in magnitude.** At 240f every arm on every trajectory
   exceeds 11×, against a published claim of 8.5–13.1×. The headline survives non-trivial
   camera motion.
2. **Short windows on hard motion are where the win is weakest.** T3 at 30 frames is only
   3.50× (B) / 3.63× (C), against 9.20× / 8.58× for the smooth orbit. The multiplier climbs
   with window length on every trajectory, so *the reported range depends strongly on both
   the window and the motion* — quoting a single number without stating both would overclaim.
   This is the most important caveat Track O surfaces and it applies to the existing published
   figures too, which were all measured on T1-like motion.

## Configuration

| | |
|---|---|
| arms | A = per-frame TEED (thr 0.5, NMS-thinned, same tracer as B/C) · B = `tcteed` linelets, no cull · C = `ngmecf030`, NG-MEC consensus cull |
| matched f | both B and C at **f = 0.30** (17 065 linelets each; B keep 15 971, C keep 15 993) |
| chains | B → 1 137 strokes, C → 1 144 strokes |
| trajectories | T1 `orbit_cameras(5→15)` verbatim · T2 same arc, radius × (1 + 0.35·sin 2πs) · T3 azimuth spline through TEST cams {5,25,45,65,85} + elevation swing 0.30·sin 3πs + time warp s + 0.15·sin 2πs |
| all cameras | look-at corrected about the median-gaussian centre, so the object stays framed and every arm sees identical cameras |

## Invariants

| invariant | status |
|---|---|
| mesh never in method path | held — no mesh import anywhere in Track O |
| held-out cams only | held — trajectories built solely from TEST views {5,15,…,95} |
| identical metric operator | held — `m1b_stroke_temporal.sequence_metrics` imported, called twice per trajectory |
| B and C matched | held — same f=0.30, same chaining parameters, same baseline frames |
| no fabricated numbers | held — every value read from `out/track_o_temporal.json` |
| protected manifest | **332/332 OK, 0 failures** |
| CUDA_VISIBLE_DEVICES=1, own procs only | held |

**Artifacts.** `scripts/track_o_temporal.py`; `out/track_o_temporal.json` (includes the
verdict block); `out/track_o_smoke.json`; `out/linelets_chair_ngmecf030_test.npz`;
`logs/track_o.log`.
