# Phase 1f — chain-level gating diagnostic on CACHED Phase-1e oracle (appendix immunizer)

STATUS: path B is a PERMANENT NO-GO (Phase 1e: method-legal lego->chair transfer AUC 0.5626 = chance; you cannot vote away zero mutual information). Path-C camera-ready ships unchanged. This is a CHEAP (CPU, ~30min, ZERO GPU) appendix-hardening diagnostic ONLY — do NOT restart any pipeline, do NOT touch banked paper numbers, do NOT re-run eval on the mesh-free arms.

## Why (three-way consensus: dss9-synthesis + agy)
A hostile reviewer will ask: "per-point gating obviously severs 1D chains; why not simple chain-level pooling before thresholding?" Phase 1e only showed POINT-level oracle topology collapse (guard 0.6372). We must diagnose whether that severing is STRUCTURAL (post-hoc thresholding fundamentally cannot preserve 1D manifold continuity) or merely an artifact of point-level thresholding that chain pooling fixes. This isolates the failure cleanly for the appendix.

## Task (reuse cached Phase-1e artifacts; NO new scoring, NO new GPU)
1. Load the CACHED oracle per-point scores from Phase 1e (out/phase1e_scores_*.npz / meta + the linelets_chair_p1e_valref.npz chain structure). Use the SAME 272,366-pt chair ref40 cloud and the SAME oracle predictions already computed — do not refit anything.
2. Build triangulated connected-component chains (the linelet/chain topology already used by run_m1b). For each chain compute a POOLED score = mean oracle probability over its member points (also log median as a robustness check).
3. Threshold at CHAIN level: keep whole chains whose pooled score >= tau. Select tau on VAL views {0,10,..,90} by the SAME protocol as Phase 1e (argmax VAL P@1.5 s.t. VAL R@1.5 >= baseline 0.6307), freeze, then evaluate ONCE on TEST {5,15,..,95}. Use the LITERAL run_m1b segment-raster P@1.5 path (same as Phase 1e), and the SAME topology_guard definition (fraction of baseline-covered GT crease segments retaining >=1 surviving point).
4. Report a small table: chain-oracle vs the Phase-1e point-oracle (P@1.5, R@1.5, topology_guard) on TEST, tau frozen on VAL.

## Frozen go/no-go (DIAGNOSTIC fork — neither branch reopens path B)
- If chain-oracle topology_guard < 0.90  => STRUCTURAL impossibility: post-hoc thresholding cannot preserve 1D crease continuity even with a perfect ranking. Appendix conclusion: full builds need topology-aware (not threshold) construction.
- If chain-oracle topology_guard >= 0.90 => REPRESENTATION bottleneck: chain aggregation preserves topology, so the barrier is purely the mesh-free supervision gap (DINOv2 zero-shot gives no legal signal, AUC 0.5626). Appendix conclusion: future work = mesh-free edge self-supervision, chain-level deployment.
Either way: write out/PHASE1F_CHAIN_GATE.md, do NOT alter path-C banked numbers, and this stays an ADDITIVE appendix. Every number from a named result file.
