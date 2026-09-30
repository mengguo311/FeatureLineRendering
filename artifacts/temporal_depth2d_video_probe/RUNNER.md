# Run, resume and inspect

Use the existing CPU environment; the runner allocates no GPU:

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python scripts/launch_temporal_depth2d_probe.py
```

The launcher double-forks, starts a new session and keeps stdout/stderr/syscall trace in `out/temporal_depth2d_video_probe/run.{log,strace}`; PID is in `run.pid`. The initial launch used the same double-fork mechanism and its PID is also recorded as `runner.pid`. It remains independent of the coding session. Status is `run/STATE.json`. Do not launch concurrent processes on the same output: flock rejects them.

Run the same command to resume. All existing unit seals and every sealed file are verified against the immutable implementation/protocol metadata. A complete unit is skipped. A partial unit is explicitly discarded and recomputed, never silently accepted. There is no within-path frame checkpoint; the maximum recomputed unit is one complete 33-frame path. A changed science implementation or corrupted seal is rejected. Atomic publication renames the directory only after all outputs and hashes are complete.

The registered deterministic replay uses a distinct output:

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python scripts/launch_temporal_depth2d_probe.py \
  --output out/temporal_depth2d_video_probe/rerun --rerun-kill
```

It repeats F/C census and the one kill unit with unchanged parameters. It does not restart scientific selection. The 45-minute ceiling applies per invocation; completed-unit seal verification remains possible on resume. Elapsed time is recorded in each unit; interrupted invocations must be disclosed rather than counted as a single uninterrupted allocation.

After both processes finish:

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python scripts/audit_temporal_depth2d_probe.py
```

`AUDIT.json` reconstructs resumed strace open calls, rejects successful scientific reads outside the frozen allowlist and writes outside the worktree, verifies unit seals, and rehashes all original input files. `RERUN.json` compares every PNG/video byte and vector-array member plus all metrics except elapsed time. `RERUN_ACCESS_AUDIT.json` audits the replay independently.

Interpret `NO_GO_KILL` as failure of this frozen candidate to meet the relative-control gates. Seven candidate/control paths are intentionally absent; their native baseline paths and all original source videos remain fully documented. Source input files, raw photos, meshes and other branches must never be edited to resume this experiment.
