# Confound-isolation: does chair's crown ink_churn advantage survive COLMAP-magnitude pose error?

**Driver-side, 2026-09-15** (dss9 agent login-expired all day; built defensively as a SWEEP with a sigma=0 self-validation gate to substitute for the mandated agent design-argue). Mesh-free, frozen shipped chair carrier (1166 strokes), boiltest churn protocol (8 consecutive orbit frames 100-107), per-frame INDEPENDENT rigid jitter on eval cams only; method/carrier/gaussians untouched. `out/posenoise_chair.json`.

## Motivation
Exp B (real-capture Truck, COLMAP poses) came back **NO-GO** (ink_churn 1.10x, need >=8x). Two unseparated confounds for the collapse: (1) estimated poses jitter object-space strokes on reprojection; (2) Truck is larger-scale/specular/less-uniformly-textured than chair. This isolates (1) on the scene where the crown is strongest.

## Self-validation gate: PASS
L0 (sigma=0) reproduces the banked boiltest chair **28.16x** exactly. The harness is sound; the sweep is not void.

## The sweep (x-axis = EMPIRICALLY MEASURED induced mean on-screen displacement, px)

| level | sigma rot / trans | induced px | ours churn | Canny churn | ratio (Canny/ours) |
|---|---|---|---|---|---|
| L0 | 0 / 0 | 0.000 | 0.0159 | 0.4488 | **28.16x** |
| L1 | 0.02deg / 0.0005r | 0.877 | 0.0334 | 0.4907 | **14.70x** |
| L2 | 0.05deg / 0.001r | 1.473 | 0.1098 | 0.6372 | 5.81x |
| L3 | 0.10deg / 0.002r | 2.287 | 0.1216 | 0.6551 | 5.39x |
| L4 | 0.20deg / 0.005r | 8.672 | 0.4742 | 0.9162 | 1.93x |
| L5 | 0.50deg / 0.01r | 21.869 | 0.6560 | 0.9101 | 1.39x |

**Truck reference induced px: ~0.38 (half-res eval) / ~0.76 (full-res)** COLMAP BA reproj residual. (Caveat, carried from the exp-B addendum: residual is NOT proven equal to extrinsic pose error; this mapping is the honest best estimate, not exact.)

## Pre-registered reading -> conclusion
At Truck's induced magnitude (~0.4-0.8 px), the chair ratio sits between L0 (0 px, 28x) and L1 (0.88 px, 14.7x) — i.e. **~15x, still well above the 8x crown gate**. The advantage does NOT collapse toward ~1x until pose noise reaches ~8-22 px, an order of magnitude worse than Truck's residual.

Therefore, per the frozen pre-registration: **the Truck NO-GO is a TEXTURE/SCENE confound, not a COLMAP-pose-error artifact.** The crown ink_churn advantage is NOT primarily a perfect-pose artifact — a chair-like textured scene would retain a large advantage at Truck's estimated-pose noise level. The honest retry for Exp B is a *chair-like* real capture (uniformly textured, bounded, smaller scale), not a re-scoping of the thesis to "perfect-pose only".

## Honest bounds (do NOT overclaim)
- Pose error DOES degrade the advantage (28x -> ~15x at ~0.88 px); it is not free. The crown is robust to COLMAP-magnitude noise, not immune to pose error in general.
- The per-frame INDEPENDENT noise model is conservative (real COLMAP poses may be smoother/correlated, which would shrink the effect further — strengthening the conclusion — but this is not measured here).
- Single scene (chair). This isolates confound (1) on the strongest crown case; it does not by itself prove Truck's specific gap is fully explained by texture — it proves pose error at Truck's magnitude is INSUFFICIENT to explain the Truck collapse.
- Does NOT resurrect the Truck result to GO. Exp B remains a banked NO-GO on that object. This finding redirects the retry, it does not overturn the negative.
