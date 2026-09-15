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

## Update 2026-09-15 15:0x (fire) — training COMPLETE, banked; M1b-ingestion blocker recorded
- Frozen vanilla 2DGS on Truck FINISHED 30k. Test PSNR: 7k 23.81 / 15k 24.48 / 30k **25.09** (train 26.69). 136k SfM pts -> **1,158,739** Gaussians. Checkpoint point_cloud/iteration_30000 (270M) on disk (gitignored per policy). Method path untouched (authors COLMAP defaults, no tuning).
- **NEXT-STAGE BLOCKER (honest, real):** the shipped M1a/M1b loaders in src/common.py are hardwired to SYNTHETIC Blender: load_cameras() reads data/full/{scene}/transforms_train.json (one shared camera_angle_x, fixed W/H) and load_gaussians() reads outputs/{scene}_static/point_cloud.ply at fixed H/W. Truck is COLMAP (per-image intrinsics, 1957x1091) with the trained ply under out/2dgs_truck/. So running the shipped M1b UNCHANGED on Truck is NOT possible as-is. scripts/colmap_loader.py already reads the COLMAP sparse but returns gs_io.Camera, not src.common.Camera, and does not wire the trained ply into extract_seeds.
- An adapter that feeds Truck (cams + gaussians dict + real rgb_paths) into the EXISTING OVERALL-score recipe is required. This sits on the method-path boundary (the photometric edge/score is the method) -> must be DESIGN-ARGUED with the agent before writing, to guarantee the recipe is byte-identical and only the data source changes. Not written this fire to avoid a silent method change.
- dss9 agent STILL login-expired (OAuth, since ~9:02 Tokyo; cannot restore from headless ssh). No fabrication. Pre-registered go/no-go UNCHANGED and still frozen.
