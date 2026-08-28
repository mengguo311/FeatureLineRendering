# CONDLAW-3-PRE — a-priori rho_flat survey + pre-registration (mesh-only, NO training this stage)

## Why
CONDLAW confirmed the Conditional Law as a 2-point dichotomy: chair DRR@80=0.986 (flat printed-fabric class of 134805 loci EXISTS), lego DRR@80=0.512 (flat class provably EMPTY, 0/3814). To promote this from a 2-point anecdote to a FALSIFIABLE PREDICTIVE LAW we need a 3rd, INTERMEDIATE scene and a PRE-REGISTERED prediction made BEFORE seeing its rankability number.

CONSTRAINT (verified): the intended `hotdog` scene has NO GT mesh in ~/3dgs_line/bcr/meshes/NeRF_Mesh/ (only chair, ficus, lego, materials, mic, ship). mesh_oracle REQUIRES a mesh. So the 3rd scene must be chosen from {materials, mic, ship}. Only chair+lego have trained 2DGS/3DGS today; the new scene's expensive render+TEED+DRR@80 run is a LATER stage. This stage is CHEAP and mesh-only.

## Invariants (SACRED — do not violate)
- mesh-never-in-method-path: mesh read ONLY via src/mesh_oracle.py, EVAL/label use only. No method-path file changes.
- Held-out TEST split only for any eval; VAL for any fitting. Use frozen src/view_split.py.
- Protect the temporal-coherence win: do NOT touch any file under out/CMEPI_protected_manifest.sha256; re-verify 332/332 OK at the end.
- Never fabricate numbers; every value traces to a written JSON.

## Task (do all, write CONDLAW3PRE_RESULTS.md)
1. Define an a-priori, IMAGE-FREE scalar rho_flat_mesh(scene) = fraction of GT-mesh surface area with local dihedral/normal-variation below 5 degrees at the measurable scale CONDLAW used (reuse diag2dgs surface_flatness machinery; chair/lego already have out/diag2dgs_lego_surface_flatness.json as reference — lego=0.69%). Compute it for chair, lego (ANCHORS) and materials, mic, ship (CANDIDATES). Pure mesh_oracle load + geometry; no 3DGS, no training.
2. Also report, per scene, the ratio (mesh-flat-class area) / (mesh-crease-locus count) as a second a-priori proxy, since the binding CONDLAW quantity was flat-class MEMBERSHIP relative to creases, not raw area.
3. Two-point calibration from the SOLID CONDLAW numbers: chair(rho_flat_chair -> 0.986), lego(rho_flat_lego -> 0.512). For EACH candidate compute D_hat = 0.512 + (rho_cand - rho_lego)/(rho_chair - rho_lego) * (0.986 - 0.512).
4. SELECT the candidate whose rho_flat_mesh is most INTERIOR to (rho_lego, rho_chair) — i.e. the genuinely intermediate scene (avoid ones that pin to either anchor; that gives no discriminating power). State the choice and why.
5. PRE-REGISTER, frozen, for the selected scene BEFORE any rankability run:
   - PRIMARY (falsifiable, functional-form-free): strict MONOTONICITY — measured DRR@80(scene) must lie strictly between lego (0.528 upper CI) and chair, ordered consistently with rho_flat_mesh ordering. This is the real law claim; 2 points cannot fix a curve shape, so monotonicity is the load-bearing test.
   - SECONDARY (affine heuristic): DRR@80(scene) in [D_hat - 0.08, D_hat + 0.08]. If it misses the band but keeps monotonicity, report as evidence of nonlinearity / possible sigmoidal phase-transition in flat-mass, NOT as a law failure.
   - Hard GO floor: DRR@80(scene) > 0.528 (strictly exceeds lego ceiling upper CI) confirms the flat class is non-vacuous there.
   Write all of this + the numeric D_hat and rho values into CONDLAW3PRE_RESULTS.md so the prediction is timestamped and auditable BEFORE Stage 2.
6. Re-verify the protected manifest 332/332 OK. Report only real numbers with source JSON paths.

Do NOT train any 2DGS/3DGS in this stage. Keep it fast (mesh-side only). Stage 2 (train 2DGS on the selected scene + TEED-rankability DRR@80 on held-out TEST) will be dispatched in a later fire against this frozen pre-registration.
