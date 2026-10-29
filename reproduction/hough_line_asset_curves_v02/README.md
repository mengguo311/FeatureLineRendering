# Complete dedicated line-Gaussian refinement pilot

This bounded CPU pilot preserves every source line kernel. It compares the original
ordered carrier, direct TLS-guided endpoint-constrained cubic fitting, and local
9+9-direction sparse Hough guidance with the same fitter and fidelity gates.
Only dedicated line NPZ/PLY assets and camera metadata are used. Source Gaussian
models are excluded even from hashing. No gap is joined, no parent is welded,
and no width, opacity, color, or source ID is altered.

The immutable configuration and cameras are in the output unit. The execution
deadline includes implementation and reporting. Run each scene serially in the
order scan24, ficus, scan65; finish one scene's export and cold reload/render
before starting the next. No parameter sweeps are supported.

Python environment (existing, no install):
`/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python`

Entry points: `runtime.py` freezes config/cameras once; `test_core.py` contains four
correctness fixtures; `audit_inputs.py before|after` checks allowed locked inputs;
`run_scene.py SCENE` fits and exports; `render_scene.py SCENE` independently reloads,
verifies, and renders; `finish.py` writes diagnostics, the Chinese report, source
snapshot, and machine-readable result. Use `run_logged.py LABEL SCRIPT [ARGS...]`
for start/exit receipts. Labels cannot be reused. Do not rerun this completed pilot.

`curves.npz` stores world-space Bezier controls, degree 1 or 3, original piece
intervals, parent IDs, per-kernel curve index/parameter, source kernel IDs, and
local normalization origins/scales. Inverse: world = local * scale + origin.
Unchanged original pieces are degree-1 curves represented by collinear Bezier
controls. `provenance/` holds original metadata, not refined geometry.

Complete saved PLY files retain all original fields except positions and rotations.
The NPZ covariance is rotated without changing eigenvalues. The mature renderer
uses raw log-scale/logit/quaternion semantics, white backgrounds, floor 0.12² and
original cameras. It never loads a full scene model. Its EWA rendering is an
approximation and has no source-surface occlusion.

All geometric gates are discrete checks; they do not establish physical accuracy.
Roughness reduction is a diagnostic, not a quality oracle. No H4 or held-out claim.
