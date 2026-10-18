# Outside-in bounded pilot

Read `OUTLINE_ZH.md`, `REPORT_ZH.md`, `FORMAT_ZH.md` in the output root:
`/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_outside_in_v01`.

Completed once: three-scene Stage A, conditional Ficus Stage B. C/D NOT_RUN after failed gates. Original C8 and source GS immutable. No new model or source parameter editing. No other agents. CPU affinity and numerical threads bounded to two.

Scientific Python (read-only):
`/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python -B`

Run new tests with `test_runner.py`. Independent check:
`verify.py --readonly --replay`.
The verifier prints JSON; redirect it to a **new** log if recording another replay. It never changes sealed results.

Scripts `preflight.py`, `freeze.py`, stage runners and review scripts document the actual one-time sequence. Frozen files and review scripts refuse overwrite. Do not rerun them on the sealed root. `run_stage_a.py` resumes completed units by checking seals. Stage B was conditional on the saved A gate; do not use it to bypass an upper NO_GO.

Dependencies are readonly original C8 inputs, original joint full-SH EWA shared library, and original geometry-roles finite-EWA responsibility implementation. Their exact hashes are in the source manifests. They are referenced, not bundled models/environments. No installation required.

Rollback is to use the old worktree/asset paths unchanged. Do not reset or clean any worktree. This branch is an isolated local research record; no push/merge.
