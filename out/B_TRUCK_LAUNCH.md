# Experiment B — REAL captured textured object: launch record (2026-09-15)

## Dataset (frozen)
Tanks&Temples **Truck** (2DGS-preprocessed HF release), staged at data/realcap/tandt/truck.
- 251 images, PINHOLE undistorted, single shared intrinsic 1957x1091.
- COLMAP sparse/0: 136,029 SfM points — **poses ESTIMATED (SfM), NOT calibrated/perfect**. This is the reviewer objection under test.
- Bounded textured object (truck body + trailer, printed panels/plates/tarp) so per-frame Canny/DexiNed should genuinely boil. Honest reservation: Truck sits in a mildly unbounded courtyard, not a clean turntable object like chair/lego; foreground silhouette control (fg_only) is therefore load-bearing for a fair P_pop.

## Method path (frozen, no tuning by us)
Vanilla 2DGS shipped recipe = the authors' own COLMAP defaults: white_background off, depth_ratio 0.0 (repo advice for larger/real scenes), lambda_normal 0.05, lambda_dist 0.0, 30k iters. Native readColmapSceneInfo, no custom loader in the method path (colmap_loader.py was only a driver-side projection sanity check, PLAUSIBLE 72 pct median on-screen). Shipped M1b pipeline + temporal harness to run UNCHANGED afterward.

## Pre-registered go/no-go (FROZEN before any metric seen)
GO iff ALL: silhouette-controlled (fg_only) P_pop ratio >= 5x at 240 frames AND ink_churn ratio >= 8x consecutive frames AND consecutive-frame strip judged visibly steadier.
NO-GO if either number misses OR pipeline yields < 300 strokes/frame (primitive does not survive estimated poses + real photometry).
Mesh-free eval only (no GT mesh on real capture), matched-precision is the one non-transportable axis, stated as such. A NO-GO is a critical honest finding, not a failure.

## Status
Frozen vanilla 2DGS training LAUNCHED (pid 1231822, ~14 min to 30k, GPU1). Next fire: verify point_cloud/iteration_30000 landed, render orbit, run shipped M1b + temporal harness, score against the frozen gate. dss9 agent still login-expired (since ~9:02 Tokyo) so work driven driver-side; no method change, no fabrication.
