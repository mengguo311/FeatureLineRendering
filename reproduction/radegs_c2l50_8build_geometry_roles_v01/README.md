# Original C8 → source-Gaussian geometry roles (bounded pilot)

This is a source-only attribution diagnostic, not a trained/reconstructed surface model.
Uses original `c2l50_multiview05_v01/arms/C`, frozen raw caches and source PLY.
No core-selection labels are imported. Source parameters and ink remain unchanged.

New output root:
`/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_geometry_roles_v01`

Read `REPORT_ZH.md`, `COUNTS.json`, `ASSET_FORMAT_ZH.md`, `RUN_COMMANDS.md` there.
Full per-case measurements include all finite-footprint source EWA contributors.
`source_index` always refers to the original source PLY, never an ink Gaussian.
Role scores are uncalibrated evidence; UNKNOWN is not background.
Point PLY diagnostics do not replace the full-SH source model.

Read-only replay from this worktree:
```
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python -B reproduction/radegs_c2l50_8build_geometry_roles_v01/verify.py --readonly --replay
```

Dependencies are existing read-only joint code/native CPU library and scientific env,
recorded in SOURCE_MANIFEST. No installation, GPU or network is required.
Production scripts target the fixed new output root; do not rerun them on sealed units.
To roll back, simply use the unchanged old worktree/asset paths. Do not reset/stash/clean
any older worktree. This branch does not alter the working C2L50+8BUILD baseline.

Scientific result: local source-ID attribution is inspectable, but no line-assisted
cross-view physical patch was certified in this pilot. Negative controls and failures
are retained. No automatic continuation or whole-scene label propagation.
