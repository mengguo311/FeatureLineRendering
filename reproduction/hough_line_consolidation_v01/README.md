# Bounded Hough feasibility on the accepted C8 line reconstruction

This is an independent NumPy adaptation of 3D line Hough voting, inspired by
Dalitz, Schramke and Jeltsch, IPOL 2017, https://www.ipol.im/pub/art/2017/208/.
The reviewed author source is pinned in the parent orchestration directory to
`3f2910f6534775e57fa449a8d555be3b5a031aee`. No author source code is copied.
This is not an exact author-code reproduction and does not implement M2/H3
multiview link confirmation, the full M3 study, or H4 Bezier voting.

The exact accepted input is C2L50 + 05 8BUILD **arm C**, at base code commit
`a25b78758716debb2e55841d305389d564187576`. It is fixed fused input
postprocessing. Original source GS, edge detection and lifting stay frozen.
Independent edge samples are not original source Gaussian center truth.

## Plain serial runner

The existing environment is:

```
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
```

From this directory, the stage command syntax is `python -B run_logged.py LABEL
SCRIPT [ARGS]`. Executed stages are recorded with their exact commands in the
owned output `logs/` directory. Each stage saves intermediate outputs directly;
there is no dependency on a continuing model conversation. Labels are unique
and prior log files cannot be overwritten.

The scripts are `audit.py`, `test_core.py`, `test_budget.py`, `real.py`,
`synthetic.py`, `diagnostics.py`, and `finish.py`. `config.json` contains the
frozen parameters and a hard deadline for this authorized one-shot pilot.
Do not rerun against the completed output directory. No automatic continuation
or next scientific tuning round is authorized by these scripts.

## Method contracts

- `audit.py`: checks every INPUT_LOCK hash and reconstructs all line means from
  optimized control+basis; exports all samples and ordered observation provenance.
- `core.py`: B0 independent fits, exhaustive legal B1 adjacency, 2048 non-consuming
  RANSAC proposals, H0 unweighted sparse votes, H1 separate density/tangent/
  confidence toggles. Unknown confidence has neutral weight one, explicitly
  uncalibrated. All methods use identical downstream eligibility, endpoint gap
  rules, 5-step Huber orthogonal refinement, and at most 32 final refiner attempts.
  B1 retains its complete legal candidate list even when its geometry budget is
  exhausted. Proposal computation is different; counts and runtime are reported.
- Directions are near-uniform Fibonacci hemisphere samples, with sparse normal
  plane bins. The coarse width covers a conservative angular drift estimate.
  A local PCA initialization and 25-direction fine accumulator precede the shared
  final refiner. This deliberately small implementation can lose lines when
  coarse bins mix structures; the fixed real ROI demonstrated this failure.
- Whole input fragments must remain near-linear. Curved/unqualified fragments,
  endpoints, and exact duplicate junction support are preserved. Peak membership
  is non-destructive and permits crossings to belong to multiple hypotheses.
- Finite supported intervals are split within each original fragment. No interval
  is extended across a new gap. Candidate link identity never licenses rendering.
  `verify_gap` returns UNKNOWN/inferred for this M1 backend, always no-connect.
- Synthetic truth is stored in `EVALUATION_ONLY` files and passed only to the
  evaluation function, never to the proposer, fitter, or verifier. Ties in PR
  scores enter together. Empty precision and no-positive recall are null.

## Real rendering and retained engineering failures

`real.py` imports only reviewed low-level `format` and `renderer` helpers from
the mature joint source/ink CPU renderer. It does not import or call old
production/finalization entrypoints. Full SH3 and source filter are preserved;
all final images use one joint depth sort and original-source occlusion. Colored
group/peak projections are labeled X-RAY diagnostics.

The first real run revealed an engineering bug: the limit applied only to
successful hypotheses, allowing more than 32 final refiner calls. Its code and
outputs are retained under `code_snapshots/uncapped_engineering_run` and
`real/scan24`; those are excluded from the scientific comparison. A real-input
RED regression caught B2/H0/H1 violations, then GREEN verified the shared cap.
Valid real results are under `real_budgeted/scan24`.

A separate B0 regression found that the shared line NMS wrongly skipped
independent collinear fragments. B0 now bypasses that NMS. `repair_b0.py`
recomputed its 160 synthetic outputs from the exact saved inputs, preserving old
outputs and source under `engineering_history/B0_independence`. All five real
B0 replays remained bitexact. B1/B2/H0/H1 results and parameters were unchanged.

The synthetic stage persisted all 800 runs and 24 ablations, but the command
wrapper was observed to exit 143 before saving its child-exit receipt.
`logs/M1_transport_observed.json` records that failure; the child exit code is
UNKNOWN, not fabricated as zero. `finish.py` checks persisted numerical outputs
before reporting them. All source-input hash checks and no-edit constraints
remain separate from scientific success.
