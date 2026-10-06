# Attribution and capacity diagnostics v02

Actual bounded diagnostics for the original Lego/Chair full-SH3 checkpoints. See [Chinese report](../../artifacts/gaer_attribution_capacity_v02/REPORT_ZH.md), [frozen protocol](../../artifacts/gaer_attribution_capacity_v02/PROTOCOL.json), and [run/resume commands](../../artifacts/gaer_attribution_capacity_v02/REPRODUCE.md).

`run.py` runs full-N fixed-T linear oracles, sparse complete native ROI records, paired DC/logscale probes, and four-view known-target box-constrained ink fits. `operators.py` reuses the verified native color forward/backward. `query.cu` adds only read-only sparse replay and FP64 linear certificates. `solver.py` implements bounded monotone FISTA with frozen stopping rules. `shape.py` applies the isolated, conditional screen covariance patch before native radius/tiling; no production renderer or input checkpoint is edited.

The primary target uses continuous old darkness on E=L>.2 with both weak and zero-ink outside regions penalized. Whole-image MSE against original continuous L is a separate metric. Per-view/shared use the same four known target frames; no generalization claim. Old one-pixel/one-vote outputs remain unchanged.

All outputs are confined to the new experiments/artifacts/ignored out directories, with PID/resource guards, atomic result seals and input/source hashes. Current results include unconverged fits and visual acceptance pending; read the report before interpreting any negative result as a representation limit.
