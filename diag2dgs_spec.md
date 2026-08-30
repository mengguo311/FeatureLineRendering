# DIAG-2DGS — 2DGS Dihedral Separability Diagnostic (lego)

## Motivation (from TGAP NO-GO)
TGAP proved the TEED image-prior gate is near-chance on lego (AUC 0.502-0.542; BELOW
chance conditional on multi-view inlier ratio, 0.42-0.47). Cause: on lego the strongest
multi-view-consistent image edges are decals/stud-fillets = exactly the wrong candidates.
Both image-prior and multi-view-consensus gates fail because distractors ARE strong
consistent image edges. The ONLY orthogonal signal left is 3D SURFACE GEOMETRY:
paint/decals are FLAT (low dihedral); true creases BEND (high dihedral). Vanilla 3DGS
bakes texture into geometry (K_geom~0) but 2DGS raised K_geom on chair fabric
(dihedral 79->10deg, AUC 0.958). Question: does that transfer to lego's sharp studs?

## This is a DIAGNOSTIC, not a pipeline. Cheap. Isolate the assumption before spending.

## Steps
1. Reconstruct lego in 2DGS (reuse existing 2DGS training recipe from the chair pivot;
   same hyperparams; frozen after training). If a lego 2DGS ckpt already exists, reuse it.
2. Take the SAME linelet candidate set already evaluated in TGAP (lego, held-out TEST
   views). For each linelet, label via mesh_oracle ONLY (eval-only, method never imports):
   - TrueCrease: mesh-crease distance <= 1.5 px equivalent (use existing crease-dist metric)
   - DecalDistractor: TEED-high-confidence AND mesh-crease distance > 3.0px (i.e. a strong
     image edge that is NOT a real crease)
3. For each linelet compute cross-linelet 2DGS surfel-normal dihedral:
   dtheta = arccos(n_left . n_right), where n_left/n_right are mean 2DGS surfel normals on
   the two sides of the linelet (small local neighborhood, project linelet to 3D, sample
   surfels within a fixed radius each side). Document the sampling recipe explicitly.

## FROZEN go/no-go (decide BEFORE reading TEST numbers)
- GO iff:  AUC(dtheta; TrueCrease vs DecalDistractor) >= 0.80
      AND  median(dtheta_crease) - median(dtheta_decal) >= 25 deg
- If GO: 2DGS-dihedral geometry gate is founded -> next fire builds the full gate targeting
  gate P@1.5>=0.85 AND R>=0.60 on held-out lego TEST, temporal no-regress (<2%, >=8x).
- If NO-GO: 2DGS raw surfel normals suffer edge-blur/discretization on lego's studs
  (cylinder tiling, sharp-step oversmoothing) -> report AUC + medians straight; next fire
  considers TSDF zero-crossing geometry instead of raw surfel normals.

## Invariants
- mesh_oracle.py touched only for LABELING/eval, never in method path.
- Held-out TEST views only for the reported AUC.
- Do NOT modify any published/committed temporal results.
- Write DIAG2DGS_RESULTS.md with: the AUC, both medians, the dtheta sampling recipe,
  n_crease / n_decal counts, and a histogram png. Report negative results straight.
- Nothing committed unless it PASSES and is a clean milestone.
