# Persistent boundary feasibility v1 — stage S0/S1 protocol

**Status:** preregistered *engineering/annotation preparation*, not a scientific GO/NO-GO protocol. This is our proposed fixed-object-space NPR research, distinct from Weiren Hao / Tomohiko Mukai's per-view line fields and Zhang et al.'s RaDe-GS renderer. No original-method claims are inherited from either.

## Input and output contract

- Input: frozen vanilla 3DGS PLY and original TRAIN camera calibration/images from `/home/u00134/cglib` for Lego and Chair. No scene representation retraining, external sensor depth, evaluation mesh, synthetic GT depth, or TEST image/array may enter generation, calibration, annotation or rendering.
- Output asset (future stages only): one immutable object-space graph of line IDs, 3D control points, topology and style per scene. Camera may affect only projection and a single frozen visibility operator; no per-view point motion, mask learned to hide errors, stroke reselection or 2D final ink. Export/readback and one edit must update every view. Silhouettes whose generators roll across the surface are not silently promised by fixed curves; required rolling contours would trigger a separately named view-dependent product contract.
- Visual goal: readable whole-object structures in full-frame stills and complete uncut camera arcs at comparable actual visible ink, with no incorrect floaters, doubles or unstable gaps. Mesh metrics are reporting-only. Internal agent image inspection is not independent human visual approval.

## Construction and isolation

- F camera indices for each scene: `[1,14,27,41,53,67,79,93]`, exactly the historical construction convention in `out/curve_correspondence_foundation/PREREG.md`. S1 annotation contact sheets may decode **F TRAIN images only**. They are explicitly not independent data: old agents have seen related results.
- C camera indices `[7,21,33,47,59,73,86,99]` are **reserved from curve construction** until an asset and all method parameters are sealed. They belong to the frozen GS TRAIN distribution and were used in older research; they are not a new blind generalization set. Do not open C images during this phase. The old DEV convention `[2,22,42,62]` is also TRAIN and historically used; do not open it for S0/S1 or recycle it as untouched validation. TEST `[5,15,25,35,45,55,65,75,85,95]` remains sealed, including byte hashing.
- The exact training history of these pre-existing PLY checkpoints (photographs, SfM, possible test access) is **unverified**. Do not assert any view was unseen by GS. This phase certifies only the new downstream process's access boundary.
- No outcome is approved by a cartoon/synthetic geometry test; those tests only qualify the analyzer. Annotators may specify 2D line intent, cross-view identity and uncertainty on F; neither evaluation mesh nor 3D truth may be used. Our own machine/assistant annotations, if made, are exploratory and not independent human evidence. This branch will not claim human-specified feasibility until a genuine annotation and review exist.

## S1 cheapest falsifier, before automatic extraction

1. Present full-frame, unaltered TRAIN-F image contact sheets with visible camera index to collect required structure, optional structure, rolling contour and background/exclusion labels. Freeze annotation time/curve budget and a complete scene-level necessary-line list *before* any C viewing. Present ambiguous identities as alternatives, not forced matches.
2. Write analytic point-anchor feasibility tests from full intrinsics/extrinsics: exact common 3D point, inconsistent positive-depth observations, underdetermined same-ray/near-parallel, and invalid/behind-camera observations. Return residuals, positive-depth flags and conditioning; no hardwired scientific cutoff. Pixel tolerance, camera domain, curve capacity, starts, visibility and visual acceptance must be calibrated solely on F and sealed in a later amendment **before** asset fitting/C inspection. No interpolation of missing line spans is accepted as evidence.
3. Human-assisted fixed-asset reference, if later built, is only an existence witness under its bounded inputs, not a strict mathematical upper bound or automatic success. Failure can reflect annotation/camera/solver limitations and requires a reasoned INVALID/UNDETERMINED/STOP classification rather than an impossibility claim.

## Current stage acceptance, controls and prohibitions

- S0 pass: source hashes recorded, F/C/old DEV/TEST roles and overlapping history disclosed, distinct branch/worktree pushed; no mesh/TEST/C/DEV decoding.
- S1 engineering pass: RED→GREEN analytic solver tests, full-F contact sheets for both scenes actually decode and show frame IDs, annotation template with no invented marks, output image decoding verified; no scientific feasibility verdict.
- No threshold tuning on C/DEV, no claim from an 8-frame author-method proxy to a fixed 3D asset. Novelty requires later comparison to LineGS, CurveGaussian, CGGT/EMAP and Hao/Mukai's future-work scope; ID lifting or curve fitting alone is not novel.
- Every reached stage will be committed and pushed on this isolated branch. External publications and upstream source retain their author ownership.
