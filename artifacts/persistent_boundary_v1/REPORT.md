# Persistent boundary feasibility: S0 complete, S1 engineering ready (not science)

**Decision:** `S0_COMPLETE / S1_ENGINEERING_READY / HUMAN_INTENT_NOT_COLLECTED / SCIENCE_NOT_EVALUATED`.

## What actually ran

- Isolated Git branch `persistent-boundary-feasibility-v1`, based on F1 commit `8dd29e1c68feae723e6d17417eea381251bf1e5f`. Pre-scene protocol and `PROVENANCE.json` committed/pushed as `e407a845cf047654789526bb41e06db9c91bd7b4`.
- Both source TRAIN camera JSONs contain 100 frame records. Frozen PLY and JSON sha256 are in `PROVENANCE.json`. Original GS training-photo/SfM split has **not** been authenticated; C is only a reserved curve-construction set and is not a GS-unseen set. No TEST image, C image, historical DEV image, evaluation mesh or GT depth was decoded for this stage.
- `src/persistent_boundary/contact.py` selects exactly eight TRAIN-F source images in each of Lego/Chair; `artifacts/persistent_boundary_v1/F_CONTACT_SOURCES.json` lists every source opened by that routine. The synthetic test leaves every non-F frame absent to catch accidental access. This is application-level evidence, **not** an OS-level Landlock/strace proof of zero unrelated process reads.
- `lego_F_contact.png`, `chair_F_contact.png`: real 4×2 full-scene images with frame labels; visual inspection confirmed eight nonblank views per scene. They are **annotation inputs**, not algorithm outputs or novel feature lines. The per-frame original pixels remain at source resolution; the montage is 400px tiles for browsing.
- `src/persistent_boundary/feasibility.py`: full-K calibrated ray least-squares consistency for *annotated matching point anchors only*. Reports conditional pixel residuals, cheirality, rank, singular values and condition number. It does not validate whole 3D curves, identity, topology, appearance, correct geometry or visibility. Caller supplies pixel tolerance; no experimental acceptance threshold was selected from images.
- TDD: each new behavior test failed for its missing behavior before minimal implementation; final command `python -W error -m unittest tests.persistent_boundary.test_feasibility tests.persistent_boundary.test_contact -v` returned **7 passed**, no warnings. Covered exact common point, identical-ray underdetermination, behind-camera negative depth, weak baseline condition, mismatched observations, invalid negative tolerance and F-only montage synthetic guard.

## What is not done / not claimed

- `ANNOTATION_TEMPLATE.json` is intentionally blank. No independent human has specified required structural lines or cross-view identity. Agent/model visual inspection cannot count as independent human feasibility review. There is **no human-assisted fixed 3D asset**, no automatic asset, no C/DEV result, and no scientific GO/STOP.
- Missing: calibrated science thresholds, annotations and uncertainty alternatives, fixed-asset construction, edit demonstration, full-arc rendering, held-out curve assessment, ink-matched nulls, LineGS/CurveGaussian/CGGT comparison. Earlier direct-curve and G1 negatives remain scoped to their frozen formulations; this branch has not superseded them.
- Hao/Mukai own the per-view raster-field method; Zhang et al. own RaDe-GS. Nothing in these montage/anchor outputs is their official quality or our claimed new algorithmic result.

## Next gate

Collect a bounded, explicit human intention statement on TRAIN-F images: which structural lines *must* be present to make a legible Lego/Chair line drawing, which are optional, and which are rolling contours rather than fixed structure. At least two F views per necessary correspondence should be marked (or marked unknown/ambiguous), with time and scope recorded. **Before** using those marks for any fixed asset, freeze per-scene line/curve budget, camera domain, repeated annotation/error calibration, visibility operator and visual decision criteria in a new protocol amendment. If a necessary line cannot be consistently assigned to a fixed 3D carrier, record a conditional contract failure; do not smooth/bridge the mismatch. Human assistance is diagnostic and must stay out of any future automatic method.
