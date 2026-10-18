# C8-guided local surface partition: three bounded rounds

Base `24622a61f1c3b1c6d0ca6b42aee8276b4db57587`, branch `gaer-c2l50-8build-surface-partition-v01`.
Scientific input is **original** `c2l50_multiview05_v01/arms/C`, not a selected core-line asset.

This completed pilot found no original-line cross-view qualified primitive. It preserves all negative results. No fourth round, no new Gaussian model or production NPR edit is scheduled.

Use the existing read-only Python and `-B`:

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python -B reproduction/radegs_c2l50_8build_surface_partition_v01/test_runner.py
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python -B reproduction/radegs_c2l50_8build_surface_partition_v01/verify.py --readonly --replay
```

`env.py` limits CPU affinity and BLAS to two threads and disables CUDA visibility. It imports frozen `geometry_roles_v01` and `joint_gs_v01` read-only modules and `joint_gs_v01/build/libjoint.so` through explicit paths. No installation, compilation, network, original-worktree checkout or modification is performed. The source-only renderer is approximate CPU EWA/fullSH, not the official CUDA rasterizer.

Results: `/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_surface_partition_v01`. See REPORT_ZH.md, the three ROUND reports, ASSET_FORMAT_ZH.md, SOURCE_MANIFEST and CODE_CONFIG_FREEZE in each round. Historical production commands are recorded in RUN_COMMANDS.md. Entry scripts refuse to overwrite existing gate reviews; sealed measurement/model units can be verified and reused by the underlying functions. Do not re-run the full scripts over sealed results merely to obtain a fresh exit code.

Rollback consists of using the old worktree and original C8/joint assets; this branch has no production replacement. Never reset or clean the old worktrees. ROLLBACK_RECEIPT and read-only verify protect their HEAD/index/status and source hashes.

PLY outputs here are source-ID diagnostic point clouds only. They are not reconstructed surfaces, Gaussian parameter assets, or mesh data.
