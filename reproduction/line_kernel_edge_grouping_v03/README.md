# Complete C8 line-kernel grouping pilot

This is the single frozen pilot for `units/unit_001`, executed on 2026-10-29.
It assigns original line kernels to provisional edge identities without changing
positions, covariance, opacity, scale, width or row order. Original parent IDs
are provenance only; they do not enter candidate eligibility or link scores.

The output root is
`/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_grouping_v03/units/unit_001`.
Read its `REPORT_ZH.md`, `CONFIG.json`, `DECISION.json` and
`INDEPENDENT_AUDIT_SUMMARY.json` before using these hypotheses.

- `grouping.py`: actual control-derived tangent seedlets, global spatial
  continuation, sparse block Hough proposals and reconciliation, shared ambiguity
  and curvature safeguards, and exact kernel membership traces.
- `pilot.py`: frozen config/cameras, full-scene exports, isolated low-level legacy
  helper adapter, Gaussian-only images, and cold-load geometry verification.
- `driver.py`: strict serial owned-child execution with durable real exit receipts.
- `test_grouping.py`: four regression fixtures, including actual cross-parent
  grouping, parent-ID permutation, curved chains, parallel edges and X/T crossings.
- `audit_diagnostics.py`: independent saved-result audits and diagnostic rendering;
  it does not regroup or tune any parameter.
- `finish.py`: verifies saved seals and produces the Chinese report and final index.

The existing interpreter was
`/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python`.
All execution used `-B`, CPU affinity at most two cores and BLAS at most two threads.
No packages were installed and no source scene Gaussian model was opened.

The runner is intentionally one-shot: it refuses to overwrite frozen outputs and
contains the original administrative deadline. Do not restart it over this unit.
Read `MEMBERSHIP_SCHEMA.json` for reason codes. `score` is a geometric link score,
not a probability, and every primary identity is provisional. `UNKNOWN=-1` remains
visible in full-asset displays. Gray also includes assigned groups outside the
highlighted selection, so gray must not be interpreted as an UNKNOWN mask.

Canonical `EXTENDED.ply` retains every original PLY field byte-for-byte.
`DISPLAY.ply` and `DISPLAY_GAUSSIANS.npz` are explicitly colored display copies.
Native PNGs use unchanged opacity/width and fixed original cameras. Enlarged crop
panels are display-only; no connector geometry is ever rasterized.

The pilot completed all three original assets. It demonstrated limited local
cross-parent joins, but not broad long-curve grouping; the Hough arm did not
outperform the strong spatial/tangent baseline under these frozen rules.
