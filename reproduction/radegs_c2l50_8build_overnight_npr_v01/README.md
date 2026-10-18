# Overnight NPR, round 01

This commit implements one frozen round only. It tests camera-upright qualification of support planes and two-view visible-cross-section bottlenecks. Original C8/source GS are immutable. No Gaussian edit, source ownership production or NPR style is performed.

Results: DTU subject gates NO_GO; Ficus coarse structural interiors PARTIAL, exact part-boundary gate NO_GO. A new invocation must freeze a different hypothesis before running round 02. Never modify sealed round-01 evidence. The supervisor owns the 07:40/08:00 JST limits.

Read-only replay:

```bash
cd /home/u00134/3dgs_line/gaer_c2l50_8build_overnight_npr_v01
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python -B -m unittest discover -s reproduction/radegs_c2l50_8build_overnight_npr_v01 -p 'test_*.py' -v
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python -B reproduction/radegs_c2l50_8build_overnight_npr_v01/verify.py --readonly --replay
```

`env.py` deliberately addresses `rounds/r01`. Future mechanisms should use separate round modules or preserve this code snapshot so that r01 remains replayable. Dependencies are absolute read-only C8 raw caches, v01/v02 evidence and the old joint common display/hash helpers; exact hashes are in r01/SOURCE_MANIFEST.json. Only process-local CPU limits are set; no shared environment is modified. See r01/RUN_COMMANDS.md and METHOD_FREEZE_ZH.md.
