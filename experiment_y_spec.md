# EXPERIMENT Y — retrain ideal-ceiling falsification (FROZEN before running)

## Status of Experiment X (DONE, gates passed)
X ran CPU-only, all hard reproduction gates passed:
- lego: cloud keep 350002==banked OK; 3D geometric-crease recall @0.00508 = 0.2112 (misses 79%, 437132 pts / 98241 edges); crease reconstruction == cache exact.
- chair: cloud keep 272366==banked OK; 3D recall 0.6749 reproduces banked 0.6753 OK.
- g (retrainable-geometric fraction of miss-set, at-scale dihedral>=20 r=0.01): lego 0.9484, chair 0.9813.
- decal/flat (<10deg) = 0.0000 both scenes; band 0.1% lego; unmeasurable 5.0% lego / 1.9% chair.
- X-DECISION vs frozen rule (g<0.25 kill / g>0.40 proceed): BOTH PROCEED-TO-Y.
- Non-trivial payload: 0.0% decal/flat REFUTES the pre-registered "decal-wall" kill hypothesis — lego's 79% miss is structurally-real geometry that survives spatial smoothing, NOT flat painted decals. Prize is not blocked by the decal wall.

## Three-way conference reconciliation (this fire)
- dss9 m1b agent: ABSENT — out of usage credits, could not give a no-code synthesis this fire.
- agy (2 adversarial rounds): conceded X is a valid falsification not a tautology; residual risk = geometric-but-photometrically/multi-view-degenerate creases (sub-pixel aliasing, specular, grazing self-occlusion).
- FROZEN Y CONTROL (agreed): the simulated ideal retrain (Condition B) may ONLY densify at a GT crease point if BOTH hold:
  (a) evaluability gate: |grad I| >= tau in the TEST view where it is scored;
  (b) supervision gate: train co-visibility — >=2 training views observe it with |grad I| >= tau.
  Densifying where RGB gradient is ~0 = cheating oracle (impossible multi-view supervision) and is FORBIDDEN. tau uses the SAME gradient convention as the frozen DexiNed/Sobel pipeline (state it in the result).

## Y PROTOCOL (small GPU, CUDA_VISIBLE_DEVICES=1, only u00134 procs, ~3.5GB free)
1. Synthesize pure-geometry zero-decal CAD part via make_cad.py (~/3dgs_line/FeatureLineRendering/real_3dgs/), ~12k gaussians, REAL creases/corners.
2. Condition A: frozen DexiNed multi-view triangulation (existing pipeline, no changes).
3. Condition B: SIMULATED IDEAL RETRAIN = GT-guided edge densification, ORACLE UPPER BOUND, explicitly labeled. Mesh EVAL-ONLY, never enters method path. Apply the FROZEN photometric double-gate above.
4. Metrics on held-out TEST trajectory: recall / precision / F1 / Chamfer on geometric creases + the temporal-coherence flicker metric.
5. Inspect renders for the FLOATER-HALO failure mode (jittery 2D edge loss -> low-opacity halo, not a sharp 1D curve).

## FROZEN Y DECISION RULE
- If Condition B fails to beat A by >= +0.15 F1 on geometric creases, OR B worsens temporal coherence (protect the banked 7-13x win) => KILL retraining pivot PERMANENTLY -> ship the frozen thesis.
- Else (B beats A by >=+0.15 F1 AND does not hurt temporal) => the prize is real -> dispatch ONE scoped S2 line-aware training component targeting the geometric hard-tail + temporal (silhouette-flow reg), scoped away from EdgeGaussians, with its own kill-test.

Report ACTUAL numbers, A-vs-B table, floater-halo render, X+Y verdicts vs frozen rules. Do NOT build a retraining framework unless Y passes. Do NOT git commit (orchestrator handles retrain-falsify).
