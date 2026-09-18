# Nonconfirmatory resolution/camera diagnosis

Written after observing Lego and Chair400px qualification failures and the single
Lego TRAIN1 diagnostic. This is explicitly post-hoc diagnosis, not a new positive
foundation result or a replacement for PREREG/config.json.

For all four fixed scenes and both fixed final30,000-iteration seeds, render the
same16 TRAIN and16 validation cameras on black/white backgrounds at native800px
using the official centered projection (pixel principal point399.5). Compare to
800px RGBA-composited GT and area-downsample both to400px. Also retain the already
measured registered K400 render. No new views, parent, seed, dose, training step,
image evidence, thresholds or method output is selected. Report every seed/view.

Store metrics and actual RGB/error panels under diagnostics/resolution/. No
eligibility field or pass/fail threshold is assigned in this diagnostic. It cannot
make an ineligible original route eligible. If the original prerequisites stop the
run, local inference/glyphs remain unreached regardless of these diagnostic values.

Run one diagnostic renderer on GPU1 after its new training queue has completed,
check>=6GiB free before launch, two CPU threads. It may overlap RouteB on GPU0.
Sources/imports and allowed photo paths are recorded, with Landlock and strace.
Use a durable detached worker, logs and exit statuses. Preserve all original outputs.
