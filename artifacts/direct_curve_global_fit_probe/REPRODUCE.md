# Reproduction

Workdir `/home/u00134/3dgs_line/tier1`; interpreter `/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python`. No commit/push. Original assets are required locally at exact paths in INPUTS.json. Do not use TEST/DEV or substitute checkpoints. PROTOCOL.md and INPUTS.json must match FREEZE.json. Canonical scientific runs are `out/direct_curve_global_fit_probe/run/` and `rerun/`; `engineering/` is excluded.

Environment for all workers:
```
PYTHONPATH=.:tests
PYTHONDONTWRITEBYTECODE=1
OMP_NUM_THREADS=1
OPENBLAS_NUM_THREADS=1
MKL_NUM_THREADS=1
CUBLAS_WORKSPACE_CONFIG=:4096:8
CUDA_VISIBLE_DEVICES=0 # or1, as journaled
```

The executable commands are journaled with argv, environment, log hashes and source hashes in JOURNAL.jsonl. Prefix a command with `python artifacts/direct_curve_global_fit_probe/record.py LABEL` to preserve its log. Worker native opens are traced with:
```
strace -f -yy -e trace=open,openat,openat2,creat -o OUTPUT.strace \
  /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python \
  scripts/run_direct_curve_probe.py --scene SCENE --stage fit --run RUN
```
SCENE is each of lego/chair/drums/ficus. RUN must name a new empty output namespace. JSON manifests reject existing immutable names; array writers are not transactional. Never reuse an output namespace. After that scene's SEAL.json exists, run the same command with `--stage evaluate`; C is unreadable to the fit worker. The evaluation worker has read-only access to its sealed fit. RUN=rerun regenerates all native evidence and18 optimization runs independently before evaluation.

Compile the isolated quantile instrument before launching workers:
```
g++ -O3 -std=c++17 -shared -fPIC -fopenmp src/direct_curve_quantiles.cpp \
  -o out/direct_curve_global_fit_probe/setup/quantiles.so
```
It is inherited native replay arithmetic with explicit10/50/90 quantiles and first depth; not a newly approximated rasterizer. Pinned stock CUDA binary/wrapper hashes are enforced by src/foundation.py.

Tests:
```
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_direct_curve -v
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest discover -s tests -v
```

Preserve raw arrays, objective histories, all starts, all camera poses, manifests, access traces, videos and failed attempts. No layout change may alter scientific array or metric hashes. Timing fields are deliberately excluded from deterministic semantic comparison, while their original byte hashes remain recorded. Detector NaN tangents and empty-evidence distances are legitimate unknowns and must not receive positive credit.
