# RED–GREEN evidence

- Protocol/inputs frozen in commit 4f604fd before tests and production code.
- 9 behavior tests written and committed in 0ef3609; RED.log: nine missing-module errors, exit 1, no implementation yet.
- GREEN_attempt1.log: nine behaviors pass, exit 0.
- Added independent unknown-alpha anchor test; RED_unknown.log: 16 invalid anchors versus expected zero, exit 1.
- Fixed known-only anchors and known-only neighbor transport; GREEN.log: all 10 pass, exit 0.
- Source/tests/runner hash seal in IMPLEMENTATION_SEAL.json precedes any F/C or arc array decoding by the experiment.
- Kernel Landlock smoke test rejects reading non-allowlisted original-worktree GO_Y.txt. Original scientific inputs are allowed individually read-only; only this worktree and /dev/null writable.

- Audit post-processing RED: SIGCHLD signal incorrectly counted as unknown file syscall (AUDIT_RED.log, exit 1). Parser now explicitly counts signal records while still rejecting genuinely unknown syscall records. Frozen science unchanged. FINAL_TESTS.log: 14 tests pass.
- Actual independent replay: 366/366 assets and all non-runtime metrics identical. Actual sealed resume: all ten units verified and skipped, no science recomputation.
