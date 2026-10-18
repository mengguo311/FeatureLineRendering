# Outside-in v02 bounded diagnostic

One completed pilot on scan24, scan65 and Ficus. Original C2L50+8BUILD arms/C and source GS are immutable inputs. This implementation neither modifies Gaussian models nor generates semantic ground truth.

Stage A uses jointly observed depth samples to propose a supporting-plane/background separation, or an explicitly isolated alpha-coverage proxy. Stage B uses one shared XYZ/Lab/coverage-width model fitted on both construction views; RGB-only and XYZ-only models have the same sample and region budgets. This differs from independently segmented image graphs. It does not guarantee connected semantic parts.

**Result:** scan24/scan65 Stage A NO_GO; Ficus A GO_PROXY, B NO_GO. Real K=3/K=5 multi-region hypotheses exist, but trunk and leaves remain mixed. Stages C/D were not run. No automatic v03.

Use the read-only scientific environment, not a newly installed environment:

```bash
cd /home/u00134/3dgs_line/gaer_c2l50_8build_outside_in_v02/reproduction/radegs_c2l50_8build_outside_in_v02
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python -B -m unittest discover -p 'test_*.py' -v
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python -B verify.py --readonly --replay
```

All numeric evidence and Chinese documentation are in `/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_outside_in_v02`. `RUN_COMMANDS.md` describes the already executed stages. Do not rerun writers against sealed directories. Replay performs no saves. `env.py` pins this process to two CPUs, limits numerical threads and disables CUDA access without modifying the shared environment.

Read-only dependencies: original C8 registry/raw caches; original joint renderer, full-SH loader and its existing compiled CPU library; v01 frozen references and RGB-only hierarchy; original official SH evaluator. `SOURCE_MANIFEST.json` and `REPLAY_DEPENDENCIES.json` enumerate exact file hashes. Returning to the old worktree is the rollback; no reset/checkout of old worktrees is needed.
