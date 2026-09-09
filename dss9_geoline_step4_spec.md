# STEP 4 — GENERALITY ON SOLIDS (frozen spec, converged from design argue)

GOAL: verify ONE frozen zero-knob param set transports across multiple clean solids.
Direct run, NO heavy multi-agent workflow. Mesh EVAL-ONLY (labels/oracle arm only).
Report negatives straight. Nothing per-scene tuned.

## ACCEPTED from your proposal
- Frozen zero-knob rule: f=1.00, shipped spec consensus prune, rho=4.0 xi=0.25 n_min=5 verbatim, NO keep-fraction anywhere.
- Drop arm B (2DGS verifier lost to the prune everywhere above P0.65).
- Three declarations in write-up: (1) f=1.00 framed as M1a seed-selection DELETED not tuned; (2) R0.6250 retired from any generality claim, survives only as upper reference; (3) half-length stays at published behaviour, 3.2x mismatch DECLARED not fixed.
- Dissociation oracle ceiling arm per solid (eval-only, reported not gated): solid misses bar but oracle clears R0.60 => ranker failure; oracle also misses => pool failure.
- Temporal reported ungated, trip-wire: surface any solid below 3x (cadpart zero-knob is 10.50x).

## TWO AMENDMENTS I AM LOCKING (converged, not optional)
1. GENERALITY REFERENCE is the ZERO-KNOB operating point R@1.5=0.4206 / P@1.5=0.8139 on cadpartA. NOT the keep-frac-0.35 point 0.6250/0.7486. Every regression comparison uses 0.4206/0.8139.
2. CUBE-FIRST as a real falsification tripwire (cheapest-falsification-first). Build+evaluate the CUBE before spending GPU on the other two solids, and PRINT the cube P/R checkpoint to the log before continuing. Cube is ungated and strictly simpler than cadpart; if it does not clear R@1.5>=0.35 at P@1.5>=0.70 the method is broken and you STOP and report — do not waste GPU on icosahedron / shallow-prism.

## SOLIDS (existing generator only, identical 3DGS recipe + pipeline)
- Cube (90deg): ungated control / tripwire. Build+eval FIRST.
- Icosahedron (interior dihedral 138.19 => oracle-labelled 41.81deg): gated. Moves face count + valence-5 vertices.
- Shallow-chamfer prism in the 30-40deg band (small change to chamfered-prism builder, inherits its planarity + photometric-step + camera round-trip self-checks): gated. The genuinely new dihedral stress just above the 30deg oracle threshold.
- Report each builder self-check (planarity, photometric step, camera round-trip).

## FROZEN GO/NO-GO (pre-registered)
- GENERAL iff every GATED solid (icosa, shallow-prism) reaches R@1.5>=0.35 at P@1.5>=0.70 at the zero-knob point AND regresses from cadpartA zero-knob ref (0.4206/0.8139) by <=0.10 recall and <=0.12 precision.
- NOT-GENERAL otherwise, reported per solid, straight.
- Write to out/GEOLINE_STEP4_RESULTS.md with the MESH EVAL-ONLY attestation, per-solid P/R frontier, oracle dissociation, temporal, and builder self-checks.

Persist plan here so nothing is lost at auto-compact. When done, leave the verdict at top of the .md.
