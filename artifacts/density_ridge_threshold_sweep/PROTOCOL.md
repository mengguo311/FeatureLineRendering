# Frozen mask-budget sweep

Requested on branch density-ridge-threshold-sweep, base
e4695a498a055ae056ef649f8700ea31b59b6a5e. Written before implementation and
inspection of new masks. No scientific pass or optimized threshold is defined.

Read only the existing verified out/density_ridge_lines/{scene}_ridge_grids.npz.
Scene order: lego, chair, drums, ficus. Channel order: color, axis, opacity,
flattening, planarity, agreement, surface. Preserve all source arrays and files.
Never recompute fields, Hessian responses, NMS, support, broad scores, projection,
or checkpoints. Reference is the saved committed-protocol ridge_clean, including
its historical baseline matching trim; it is not the fresh 6% result.

For each channel independently, pool saved ridge_scores on saved support in scene
then row-major order. Rank positive scores descending, stably. Fresh budgets are
6%, 12%, 20%, 35% of total support; requested count=floor(budget*total support),
selected count=min(requested, positive supported candidates). Report exhaustion
if any. Remove 8-connected components of area <12 separately in each scene.
No baseline matching, second trim, bridging, or scientific tuning after viewing.
Save all raw and cleaned masks and assert both stages are nested in budget order.
Fixed area cleanup is monotone: every surviving lower-budget component is
contained in a component at least as large at higher budget. Thus cleanup cannot
break nesting. Component counts and skeleton-based metrics need not be monotone.

Report raw/clean selected pixels, support/canvas coverage, pooled threshold,
components, fragments (skeleton length <24), long-component ink fraction (area in
components with skeleton length >=24 divided by ink), and width using the existing
metric definitions. Do not treat topology or pooled coverage as accuracy.

Figures: native-resolution seven-column scene atlases with saved full Hessian
response context (existing pooled display p99), original final mask, and fresh
6/12/20/35% cleaned masks. Masks are cyan on the same saved dim color/density
background; print per-scene count/support and percentage. Focus sheets for opacity
and flattening show all four scenes and all levels at 2x nearest-neighbor scale.
An all-scene summary includes both focus channels and all mask levels, with the
seven-channel detail supplied by the scene atlases. No interpolation of masks.

Test before implementation: exact pooled count, stable ties/nesting, positive
candidate exhaustion, monotone 8-connected cleanup, failure on nonnested arrays,
and real-grid 6% raw/cleaned-unmatched reproduction. Run new/full tests; decode
every PNG; verify finite values, boolean shapes, source hashes, independently
recompute masks/counts/metrics; complete saved-grid rerun with bytewise hashes.
Inspect all figures and record unblinded qualitative findings, distinguishing
coherent added structure from clutter/fill. Any layout changes must preserve
NPZ and metrics hashes. No post hoc scientific pass; no commit or push.
