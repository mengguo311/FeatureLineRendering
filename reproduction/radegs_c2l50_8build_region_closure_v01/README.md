# C8 region-closure pilot (Gaussian assets remain immutable)

Scientific outcome: NO_GO for persistent line-guided source regions, not a claim that C8 lacks useful shape information.

Readonly inputs: original C2L50+8BUILD arms/C, original full-SH source GS, joint CPU EWA. This code does not read mainlines/core-selected labels. Run artifacts are under `/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_region_closure_v01`.

Use existing readonly `official_code_fix_v01/env/bin/python -B`. `test_runner.py` runs 21 current tests. `verify.py --readonly --replay` checks seals, source hashes, full source/ink render arrays, graph/no-line candidates, transfer and protected worktrees without rewriting evidence. See HDD `RUN_COMMANDS.md` for the executed sequence; do not run mutation scripts over sealed outputs.

Boundary hypotheses are diagnostic image regions. No line filling/deletion, direct-curve product, physical surface model, source GS edit, GPU, training or mesh. Open branches remain legal. No subsequent pilot is scheduled.

Rollback: use the untouched original worktree and original arms/C/joint assets. Never reset/clean/stash/revert them. The new branch is local only; no push/merge.
