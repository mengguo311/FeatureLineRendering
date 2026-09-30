# RED–GREEN evidence

- Protocol/inputs frozen in commit 4f604fd before tests and production code.
- 9 behavior tests written and committed in 0ef3609; RED.log: nine missing-module errors, exit 1, no implementation yet.
- GREEN_attempt1.log: nine behaviors pass, exit 0.
- Added independent unknown-alpha anchor test; RED_unknown.log: 16 invalid anchors versus expected zero, exit 1.
- Fixed known-only anchors and known-only neighbor transport; GREEN.log: all 10 pass, exit 0.
- Source/tests/runner hash seal in IMPLEMENTATION_SEAL.json precedes any F/C or arc array decoding by the experiment.
- Kernel Landlock smoke test rejects reading non-allowlisted original-worktree GO_Y.txt. Original scientific inputs are allowed individually read-only; only this worktree and /dev/null writable.
