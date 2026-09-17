# Gap recovery cheap kill-test — frozen before bridge image scoring

Date 2026-09-18. Branch `gap-recovery`, base `9e643c2`. Numerical settings, source
hashes and input hashes are in `MANIFEST.json`. No parameter sweep or rescue run.

## Task and scene audit

Use **lego**, 1,986 original paths / 405 object-space bridge hypotheses. The identical
TRAIN-only carrier acquisition recipe was audited on chair (1,258 paths / 997
hypotheses) and cadpartA (26 paths / zero hypotheses). Old unverified caches were
excluded; chair's clean VRSS pool alone was reused by checksum. CadpartA's large
missing spans cannot be solved by the current local endpoint hypothesis pool.
Chair's principal visible omissions are not confidently three local G1 examples.

Lego has three concrete, independently located candidate G1 intervals, annotated
before edge scoring in `G1_AUDIT.json`: bridge **71** (base plate front left), **152**
(front edge near right corner), **153** (blue cylinder edge). All have different
existing chain endpoint pairs, are visible in TRAIN 1/27/79, and stay broken in a
diagnostic that disables occlusion. RGB supplies the visible continuation; no GT
overlay is used. Human labels never enter candidate scoring or selection.
The no-occlusion diagnostic is NOT a proposed renderer or a proof of exact geometry.

## Frozen protocol

* Seed/pull: original 16 canonical TRAIN indices, fixed .30 seed fraction and 100
  pull steps, unchanged linelet/prune/chain recipe. No TEST/VAL images or old labels.
* Audit: TRAIN [1,27,53,79]. Fit/select: TRAIN [1,14,27,41,53,67,79,93].
  Validation: TRAIN [2,22,42,62], absent from extraction and selection. These images
  are opened only after selected 3D paths are committed. No final camera selects ink.
* Final path: new 120-frame full 360-degree orbit derived from TRAIN camera **7**,
  median defloated-GS target, 24 fps, 400x400. Not generated/viewed before this freeze.
  Fixed panels 0/30/60/90. Full videos and every-frame contact sheets required.
* Brush: 1 px black, white background, cv2 antialias. Same GS-disc depth, same
  existing 3x3-min / 2% visibility rule for all variants. Official full-SH stock GS
  RGB beside drawings; the depth approximation is explicitly not called official.
* Baselines: original; object-only geometric ranking; same finite curves with
  multi-view image evidence. Original paths never removed, moved or reconnected.
* Both <=20 bridges AND <=5% added visible length. Enforce each fitting camera and
  3D total length; separately audit EVERY final frame. A final-frame excess fails
  the gate; no selection on final cameras to repair the budget. Do not equalize
  variants by adding low-confidence filler ink. Report actual lengths separately.
* Fixed Canny sigma 1.2 / thresholds 50,120; middle 60% of bridge; DT<=2 px,
  tangent cosine>=.75; >=70% joint sample support; >=3 supported fit cameras,
  support rate>=.6 among evaluable views; >=10-degree camera diversity.
  Hidden/outside views are neutral; visible contradiction is negative. GS front/
  background mismatch and visible depth jumps veto. See source/config for details.
* No mesh, GT labels, extra 2DGS normals, GS training, detector sweep, curve fitting
  against final views or changing the frozen candidate generator.

## All five criteria are necessary for GO

1. At least **2 of the 3** preregistered G1 intervals are visibly restored by the
   evidence variant in multiple views (and remain useful on the complete orbit).
   Exact pair IDs identify the loci; alternative bridges cannot receive credit
   merely for adding ink elsewhere. No overlay is needed to see the improvement.
2. Image evidence rejects at least one **visually wrong** object-only accepted
   connection. A numerical rejection alone is not proof of a wrong connection.
3. No accepted bridge creates an obvious penetration, cross-part shortcut or wrong
   contour lasting >0.5 s (13 consecutive frames at 24 fps). All selected bridges
   are included in the complete video and diagnostic, including failures.
4. Added visible length <=5% in every final frame, with visible continuity and
   shape-readability benefit at the fixed display scale. Tiny zoom-only changes or
   a nominal metric gain do not satisfy this. Internal inspection is not a blind
   human study and will not be described as one.
5. On the four unseen TRAIN/DEV validation views, a strict majority of accepted
   bridges must each have >=2 supporting views and >=.6 support rate among evaluable
   views, without depth/background veto. If zero bridges are accepted, this fails.

Any failure means NO-GO, preserve the complete artifacts, stop scene expansion.
No threshold tuning, mesh rescue, additional normals or 2D inpainting afterward.

## Scope and limitations

This is a local repair feasibility check, not a reconstruction or recall experiment.
Hypothesis count is not G1 count. The old depth estimator can create G2 fragmentation
or veto legitimate bridges; diagnose it, do not change it during this kill-test.
Original GS training provenance was not independently reconstructed; TRAIN-only
guarantees here apply to line extraction and bridge evidence. Camera metadata for
the full 100-frame source JSON is parsed by the existing loader, but only explicitly
allowed TRAIN camera objects and RGB enter method computations. Source hashes and
access logs supplement code review; they are not a native-code security sandbox.

The geometric and evidence toy tests establish semantics only. They do not count
as restored real gaps or visual success.
