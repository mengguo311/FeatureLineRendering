# Experiment B — Truck real-capture, MESH-FREE go/no-go IN FLIGHT

Status 2026-09-15 (driver-side; agent login-expired since ~09:02 Tokyo, `/login` needs
interactive OAuth — unrecoverable headlessly, driver ran the shipped path directly).

## CORRECTNESS BUG FOUND + FIXED THIS FIRE (important, not a method change)
Tanks&Temples Truck ships HALF-RESOLUTION images (979x546) but the COLMAP `cameras.json`
intrinsics are FULL-res (1957x1091, fx~1163). The shipped gbuffer renders at cam W/H
while `photo_edge_dt` reads the on-disk jpg, so:
  (a) carrier build CRASHED: geom_gate `edge & support` shape mismatch (546,979) vs (1091,1957);
  (b) WORSE, the earlier M1a seed extraction had silently sampled the 546x979 photo-edge DT
      at projected pixel coords up to ~1956 (clamped to the image edge) -> CONTAMINATED seeds.
FIX (src/truck_ingest.py): rescale K + W/H to the ACTUAL on-disk image size (standard 3DGS
resolution downscale, applied consistently to BOTH render and photo paths). Poses/method
untouched. Old seeds backed up to out/truck_m1a_seeds_BADRES.npz.bak; seeds RE-EXTRACTED
(202s) with correct cameras -> 198,601 seeds (keep_f 0.22, unchanged count is coincidental;
the SCORES differ because the photo channel now samples correctly).

## MESH-FREE CARRIER BUILT (verified, frozen chair recipe VERBATIM)
scripts/truck_carrier.py replicates run_m1b.py lines 245-296 exactly: f=0.30, edge=sharp,
gate theta20/tau0.015/dilate2, steps100, pull_split=train (view_split.split(251): TRAIN 200 /
VAL 26 / TEST 25), tau_in1.5/min_ratio0.50/max_med1.5. STOPS before the mesh Harness.
Result (out/linelets_truck_gal_test.npz):
  270,820 seeds (top-0.30 of OVERALL score) -> 270,820 linelets init (med half-len 0.027 world)
  -> pull 31.8s (moved median 2.46px, p90 5.00, n_vis median 23)
  -> prune KEEP 239,020 / 270,820 (88.3%), inlier_ratio median 1.000, median_resid 0.49px.
818s total. Chained (m1b_stroke_temporal): 239,020 linelets -> NMS 126,906 -> **16,171 strokes**
(med 4 vtx). >> 300/frame floor -> the primitive SURVIVES estimated poses + real photometry.
That alone falsifies the NO-GO "<300 strokes" branch.

## TEMPORAL go/no-go RUNNING (scripts/truck_temporal.py, background pid 1295944)
Reuses SHIPPED operators VERBATIM (frame_data/sequence_metrics P_pop fg_only; boiltest.churn
ink_churn). Frame sequence = REAL consecutive capture cameras (COLMAP poses), NOT a synthetic
orbit — the honest sequence for a real capture. 240-frame P_pop horizon + 30-frame ink strip.
SLOW: ~22s/frame at 16k strokes -> ~90min. Writes out/B_TRUCK_TEMPORAL.json +
out/viz/truck_consecutive_strip.png.

## FROZEN go/no-go (unchanged): GO if fg_only P_pop ratio>=5x @240f AND ink_churn ratio>=8x
consecutive AND strip visibly steadier AND >=300 strokes/frame. NO-GO if either misses or <300.
Matched-precision NON-transportable (no GT mesh) — reported not gated.

## NEXT FIRE
1. Read out/B_TRUCK_TEMPORAL.json (numbers from JSON, not prose).
2. scp out/viz/truck_consecutive_strip.png to mac /tmp/evf and LOOK — judge "visibly steadier"
   honestly (real capture: expect Canny to boil on the truck's textured tarp/wheels; the strip
   decides the eyeball axis).
3. Commit verdict. If GO: crown claim survives real estimated poses — a genuine milestone but
   report the matched-precision caveat straight. If NO-GO on a ratio: that is a CRITICAL honest
   finding (crown may be a synthetic-perfect-pose artifact), report it straight, do NOT re-tune.

## HARD DISCIPLINE HELD
Mesh eval-only (Truck has none -> fully mesh-free). Frozen recipe, no per-scene tune. Object
space. No audited-killed claim re-inflated. Bug fix is data-plumbing only.
