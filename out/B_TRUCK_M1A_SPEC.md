# Experiment B — next step spec: M1a seeds on Truck (design-argue on agent revival)

Status 2026-09-15 (driver-side, agent login-expired since ~09:02 Tokyo, unrecoverable headlessly).
Camera+gaussian adapter DONE and validated (src/truck_ingest.py, commit 96b4372; conv A R.T
on-screen 0.324 vs 0.169, common.project smoke on-screen 0.428, 251 cams / 2.58M gaussians).
ALL 6 hygiene items verified landed against JSON (3-of-4, 9.78x, lego SAFE retracted,
Canny-boil FAIL, boiltest.json fg-consistent solid ink_churn 3.3-6.8x, dd3_meshpr.json
P@1.5 0.814/R@1.5 0.421 reproduces STEP3 zero-knob). Frontier = run SHIPPED M1b on Truck.

## THE BLOCKER (why not run driver-side blind)
run_m1b.py consumes `finalscore_overall_{scene}.npy` (per-gaussian M1a score) + m1a_seeds.
No `finalscore_overall_truck.npy` exists. m1a_seeds.py (scripts/explore/syn) IS self-contained
and MESH-FREE, but was written for the NeRF-synthetic layout and bakes choices that are NOT
obviously transportable to a real COLMAP capture. These MUST be argued, not defaulted:

1. N_VIEWS=25 hardcoded — on Truck's 251 COLMAP frames, which 25? train split? even stride?
2. photo_edge_dt: RGBA->composite-on-white branch assumes synthetic alpha. Truck jpgs are
   opaque real photos with a real background (courtyard) — the blurred-Canny union will now
   fire on BACKGROUND clutter, not just the object. Need a foreground/bounded-object gate or
   the seed field is dominated by scene edges. THIS IS THE KEY DESIGN QUESTION.
3. EDGE_CFGS (2.0,100,200)/(2.5,75,150) tuned to ~3% edge density on clean synthetic renders;
   real photometry (noise, texture, lighting) will blow past 3%. Do we hold cfgs FROZEN
   (honest: shipped recipe unchanged, accept whatever density) or is that a per-scene tune?
   PRE-REGISTER: FROZEN cfgs = the defensible choice; any retune = method drift, forbidden.
4. G-buffer render pass: m1a_seeds needs rendered normals/depth per view via src.render on the
   Truck cameras. truck_ingest supplies cams+gaussians; confirm render.py runs on this source
   unchanged.

## Pre-registered go/no-go (UNCHANGED, restate before running)
GO iff ALL: fg_only P_pop ratio >=5x @240f AND ink_churn ratio >=8x consecutive AND
consecutive-frame strip visibly steadier. NO-GO if either misses OR <300 strokes/frame.
Mesh-free eval only; matched-precision non-transportable (no GT mesh on real capture).
A NO-GO is a critical honest finding. Expectation to log NOW (falsifiable): background-edge
contamination (#2) is the most likely NO-GO driver — if seeds land on courtyard edges the
carrier will be noisy and strokes/frame may exceed 300 but P_pop ratio collapse. Freeze this
prediction so we cannot rationalize either outcome after the fact.

## First action on revival
Argue #2 (foreground gate on real photos) FIRST — it is the one place the shipped recipe does
not obviously transport. Options: (a) run shipped recipe verbatim, accept background edges,
report honestly; (b) mask to the object via the sparse COLMAP point hull (mesh-free, geometry
only). (a) is the cleaner test of "does the SHIPPED pipeline survive real poses"; (b) risks a
hidden per-scene assist. Lean (a) unless argued otherwise. Direct run, no 15-agent workflow.
