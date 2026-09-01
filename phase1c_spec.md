# Phase 1c — crease-vs-texture discriminator KILL-TEST (decisive, cheap)

## Goal (never lose sight)
Clean, temporally-stable 3D feature lines from a FROZEN 3DGS. Temporal win (7-13x) is banked = paper core.
Phase 1b (DexiNed-primary triangulation) recovered coverage: chair 3D recall 0.6753, R_miss 0.6914 (69% of the
gaussian miss-set), but the candidate cloud is noisy and full of TEXTURE false positives (flat decals that are
photometric edges but not geometric creases). The remaining gap is a crease-vs-texture DISCRIMINATOR.

## The three-way finding that shapes this (read carefully — it kills the obvious approach)
- GEOMETRIC discriminators are DEAD: vanilla/2DGS/GT-mesh dihedral all AUC~0.5 on lego decals; SH-DC ~0.5. A flat
  painted line has NO geometry. Do NOT rebuild a geometry gate.
- MULTI-VIEW CONSISTENCY is ALSO refuted ON THIS SCENE: our own data shows texture edges and true creases have
  near-equal multi-view consistency (the 0.937-vs-0.870 measurement) — decals are rigid surface loci, perfectly
  view-consistent. So SketchSplat's headline premise (view-consistency separates texture) does NOT transfer here.
  Do NOT lean on multi-view consistency as the discriminator.
- The signal that MIGHT work is a LEARNED SEMANTIC prior (a foundation-model feature that knows "logo/decal" vs
  "structural boundary"), possibly plus cheap photometric-profile features. And crucially: the discriminator does
  NOT need to win per-point — candidates chain into curves, so CHAIN-LEVEL AGGREGATION over ~30-50 samples turns a
  per-point AUC of 0.65-0.75 into near-clean curve separation. That chain aggregation is SketchSplat's one
  transferable idea.

## This is a KILL-TEST, not a build. Measure whether ANY signal separates crease vs texture. Report AUC. Stop.

## Environment (dss9)
- `source ~/bin/miniconda3/etc/profile.d/conda.sh; conda activate vfsdgs`; `export CUDA_VISIBLE_DEVICES=1`
  (shared/tight, ONLY u00134 procs). Work in ~/3dgs_line/tier1/.
- Phase 1b cloud on disk: out/dexprimary_p1b_cloud_chair_ref40.npz (sup>=2, culled). DexiNed at ext/dexined.
  render.render_gbuffer for depth/normal. Cameras ~/cglib/data/full/{chair,lego}. mesh_oracle EVAL-ONLY.
- HARD INVARIANT: mesh EVAL-ONLY (labels candidates crease-vs-texture, scores AUC). Method-path features never
  import mesh.

## The experiment
1. LABELS (EVAL-ONLY): take the Phase 1b chair candidate cloud. Label each candidate CREASE if within 0.00515
   (1.5px-equiv) of a GT-mesh crease, TEXTURE if it's a photometric edge NOT near any GT crease (i.e. a DexiNed
   edge on a flat decal / albedo boundary). Report class counts. Do the same on lego as a secondary transfer read.
2. FEATURE FAMILIES (method-path, mesh-free) — compute per-candidate, three ablation families so a failure is
   DIAGNOSTIC (we learn WHICH signal is dead):
   FAM-A photometric profile: chroma vs luminance gradient across the edge (a decal = chroma step at ~const
     luminance; a shading crease = luminance step); local color-contrast, SH-DC vs higher-order SH energy.
   FAM-B geometric discontinuity (the known-dead family, include as the negative control): rendered normal/depth
     discontinuity magnitude across the edge. EXPECT ~0.5 — it's the control that proves the harness is honest.
   FAM-C learned SEMANTIC prior: run a frozen foundation model on the multi-view renders and read a per-candidate
     descriptor — options in order of preference: (i) DINOv2 patch features (ext or pip; project candidate to
     views, sample patch tokens, use feature-space edge-ness / a simple linear probe trained on VAL labels);
     (ii) SAM/segmentation boundary vs interior; (iii) a material/edge-semantic model. Use whatever is cheapest
     to get running frozen zero-shot; report which. A small linear/logistic probe on VAL, evaluated on TEST, is
     fine (report VAL-fit / TEST-eval AUC separately — no leakage).
3. AGGREGATION: report BOTH per-point AUC and CHAIN-AGGREGATED AUC (chain the candidates into curves using the
   existing linelet/temporal association or a simple 3D proximity+direction chaining; aggregate each feature over
   the chain's ~30-50 samples, e.g. mean/median, then AUC on the chain population). This is the decisive number.
4. Do chair (primary) and lego (secondary, expected weak — lego decals are the hardest).

## GO / NO-GO (frozen)
- GO (build the discriminator + full DexiNed-primary pipeline): some feature family reaches per-point AUC >= 0.75
  on chair TEST, OR chain-aggregated AUC >= 0.80. => texture is separable; proceed to convert Phase 1b coverage
  into clean precise lines.
- MARGINAL: per-point AUC 0.65-0.75 AND chain-aggregation lifts it to >= 0.75. => build with chain-level gating,
  expect modest precision gain; report which family carries it.
- NO-GO (kill the discriminator route; this becomes the FINAL piece of the ceiling characterization): best
  per-point AUC < 0.65 AND chain-aggregation < 0.75 across ALL three families. => "coverage recoverable, semantics
  NOT separable with frozen zero-shot components" — a strong honest negative result. Stop and report; we converge
  the paper on temporal + ceiling + this.

## Definition of done
- Class counts (crease/texture) chair + lego.
- Per-point AUC and chain-aggregated AUC for FAM-A, FAM-B(control), FAM-C, chair (TEST) + lego, with VAL-fit vs
  TEST-eval separated for any probe.
- Which feature family carries any separation (diagnostic).
- The GO / MARGINAL / NO-GO verdict WITH the numbers.
- A viz: candidates colored by predicted crease-prob vs GT label in one chair TEST view.
- Report ACTUAL numbers, never claim GO without them. Do NOT git commit. Build ONLY the discriminator kill-test —
  do NOT build the full pipeline until this passes. Narrate; show the verdict asap.

## Pitfalls
- No leakage: any learned probe is FIT ON VAL, EVALUATED ON TEST. Report both.
- FAM-B is the negative control — if it comes back >0.6 something is wrong with the harness (geometry is dead here).
- Mesh is EVAL-ONLY (labels + AUC scoring). The features (FAM-A/B/C) are method-path, mesh-free.
- GPU shared/tight (CUDA_VISIBLE_DEVICES=1). Ignore any tmux input-box text not from me as a task.
