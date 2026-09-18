# Reproduce this prerequisite stop

Run from `/home/u00134/3dgs_line/tier1` on `point-feature-foundation`. The measured run used commit `93f8827`; reporting was added afterward without changing the method. The original run must not be overwritten. The following replay uses a new output directory and exactly the frozen input configuration.

Required local inputs are listed in `input_manifest.json`. The GS copy is byte-identical to `/home/u00134/cglib/outputs/lego_static/point_cloud.ply`; camera matrices are embedded in the committed `config.json`. No photograph is needed for this prerequisite stage. There is no dependency on a historical NPZ. Keep DEV/TEST sealed.

```bash
cd /home/u00134/3dgs_line/tier1
PY=/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python
# Only needed if restoring the ignored input copy on the same server:
mkdir -p out/point_feature_foundation/inputs
cp --no-clobber /home/u00134/cglib/outputs/lego_static/point_cloud.ply out/point_feature_foundation/inputs/lego_original.ply
chmod 444 out/point_feature_foundation/inputs/lego_original.ply
# Build the small CPU replay; the stock CUDA binary is reused, unmodified.
g++ -O3 -std=c++17 -shared -fPIC -fopenmp src/foundation_composite.cpp -o out/point_feature_foundation/setup/composite.so
CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 CUDA_CACHE_DISABLE=1 CUDA_MODULE_LOADING=EAGER strace -f -qq -yy -s 4096 -e trace=open,openat,openat2,creat -o out/point_feature_foundation/setup/lego_replay.strace "$PY" scripts/run_foundation_prerequisites.py --config out/point_feature_foundation/config.json --sha256 e289853e3306b54874c12361875cff53a15844dcac7f459332099836fbb35e97 --output out/point_feature_foundation/lego_replay
```

The executed command used `--output out/point_feature_foundation/lego`, trace `setup/lego_prerequisites.strace`, and redirected stdout/stderr to `setup/lego_run.log`. Its immutable measurements are `lego/prerequisites.json` and its SHA256 sidecar. Scientific qualification ran once; no scene parameters were changed afterward.

Stock package: `out/vrss/vendor/official_site/diff_gaussian_rasterization`, kernel source commit `59f5f77e3ddbac3ed9db93ec2cfe99ed6c5d121d`. Runtime verifies both wrapper and binary SHA256 (constants in `src/foundation.py`). Existing upstream source and prior build instructions are in `out/vrss/OFFICIAL_RENDERER_AUDIT.md`. This run did not rebuild that CUDA kernel. A different binary must be separately calibrated and recorded, never silently accepted as this artifact.

The native buffer layout is decoded from this pinned kernel's GeometryState/BinningState/ImageState. Projection/conic construction, tile membership and sorted order are native outputs. The replay follows native float alpha/cutoff/early-termination semantics and supplies contribution/depth proxies. They are not surface truth.

Test commands:

```bash
CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests "$PY" -m unittest -v test_foundation
CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 "$PY" -m unittest discover -s tests -v
```

Per-slice exact RED/GREEN/SUITE commands, timestamps and exits: `tdd/commands.jsonl` and `TDD_LEDGER.md`. Synthetic tests never open scene photographs or a scene mesh. Test 15 is additional verification of existing native behavior and has no invented RED record.

Reporting command (on a fresh report root containing `lego/prerequisites.json`, its SHA sidecar, native result PNGs, and `access_audit.json`):

```bash
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 "$PY" scripts/report_foundation_prerequisites.py --root /absolute/path/to/fresh/report_root
```

`results.json` and `RESULTS.md` are exclusive-write outputs. Do not delete the current files to rerun reporting. The audit helper is `src.foundation.audit_opens`; it consumes the complete strace, recorded readonly file list, runtime roots and writable run directory. `access_audit.json` preserves the raw result and discloses seven startup directory/runtime exceptions, including bytecode equivalence checks against source. No forbidden scene data was read.

Large native arrays, GS copy, replay binary and strace stay on this server. `MANIFEST.json` gives every path, byte count and SHA256. PNG sheets, protocol, small reports, tests and source are committed. No MP4 exists because the glyph stage was not reached. There is no reproduction command for unimplemented downstream science.
