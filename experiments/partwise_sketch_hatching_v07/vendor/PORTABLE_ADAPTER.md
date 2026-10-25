# Portable delivery adapter

`linked_source_cli.py` and `runtime.py` are final-delivery engineering adapters. The modules named in `VENDORED_PROVENANCE.json` are byte-for-byte copies from v06 unit010's saved source snapshot. Their historical scientific scope and limitations remain unchanged. No new experiment, selector, target, style, path or source model is derived here.

Runtime dependencies: Python 3, NumPy, SciPy, plyfile, Pillow, and `g++`. The package contains source code, bindings, original PLYs, saved camera and actual proxy assets; it does not bundle a Python environment. Data paths resolve from this file's package location, so moving the entire package does not require historical output roots. Absolute paths in metadata/provenance identify historical producers and are not runtime dependencies. Both compiled CPU libraries are built in the explicitly supplied NEW output folder. CUDA is disabled, numeric threads are set to one, and Linux CPU affinity is limited to two cores before numerical imports.

Examples, after changing to the package root:

```bash
python -B code/linked_source_cli.py mapping --scene lego --ids 49033 174330
python -B code/linked_source_cli.py render --scene lego --out /absolute/new/replay_lego --verify
python -B code/linked_source_cli.py render --scene lego --out /absolute/new/replay_lego_hybrid --hybrid --verify
python -B code/linked_source_cli.py render --scene chair --out /absolute/new/replay_chair --verify
```

`mapping` returns the complete-row authored region binding, retained UNKNOWN/reason, actual paper/ink strengths, and frozen v05 unit005 aggregated path support for each requested original PLY row. Aggregated path support does not identify a unique stroke-to-kernel attachment. Latest Lego region bindings and paper/ink strengths are separate artifacts with separate historical provenance.

`render` loads the real complete original PLY; evaluates full SH3 source colors; applies the saved per-original-row paper override; and renders actual source, paper and accepted-alpha-times-transmittance ink support. The source checkpoint, geometry, covariance, opacity and original SH remain unchanged. It writes `FRAME.npz`, raw RGB PNGs and `RELOAD_RECEIPT.json`; verification compares the saved reference at tolerance 1e-6 and records exact equality separately. Support PNG is a scalar support visualization, not an edited RGB frame.

Optional Lego `--hybrid` reconstructs the exact saved unit010 `local_raw` arm from unit008 target/old-region arrays and unit010 LOCAL partitions, with saved proxy styles and fixed camera. It additionally verifies `local_ink` and `local_raw`. This is **original Gaussian paper + original-ID-gated proxy ink**, not native Gaussian hatching. No unit001-proxy/latest-link cross-combination is made. The local raw arm is not the BUILD-effect-matched arm.

The CLI renders the one packaged historically exposed camera. It provides reusable package-local source/assets and a real linked-source path; it is not a GUI editor, native CUDA certification, semantic/physical ownership, a novel-view quality claim or a repair of earlier failed locality tests. Pre-existing proxy-only editors must not be described as source-linked because this CLI exists.
