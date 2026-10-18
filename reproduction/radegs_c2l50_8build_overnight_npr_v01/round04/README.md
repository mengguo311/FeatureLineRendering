# Overnight r04: complementary evidence coupling

Same frozen r03 appearance posterior + depth-qualified local/cross-view pixel graph, with original proxy seeds. Four fixed arms: coupled, no_cross (build links only), geometry_pair (appearance unary remains), unary_seeded. This is diagnostic image partitioning, not a new GS model or semantic GT. Original C8 and source GS stay immutable.

Use the readonly Python environment and `-B`; env.py constrains process affinity and numerical threads to two. Run `experiment.py --phase fit --scene all`, then `--phase reserved`; checked sealed units are skipped. Run `evaluation.py`, `delivery.py`, and `verify.py --readonly --replay`. The independent verifier checks exact saved arrays, source hashes, old protected worktrees, unit seals, and safe package members.

23 new tests: 18 graph/output behavior tests plus 5 same-matrix numerical repair tests. The first large unsealed solve was stopped for bounded runtime; its source/logs remain in the HDD engineering record. Large-system repair changes no graph, objective, seeds, residual or probability tolerance. Original small Ficus solver/results remain unchanged. See ENGINEERING_SOLVER_AMENDMENT.json for exact execution difference from the initial solver freeze.

HDD results: `/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_overnight_npr_v01/rounds/r04`. Read REPORT_ZH.md and stage gates for actual scientific outcomes. No later scientific round is launched by this code; finish.py seals r04 only. No source/kernel/style editing, GPU, training, model downloads, or subagents.
