# M1b — carrier-persistence Pareto sweep (chair, held-out TEST views)

Cheap axes only. cp_views fixed at 20; only cp_ratio is swept. Flat regions are GT-verified (mesh EVAL-ONLY): on the mesh, >c px from any visible GT crease and >4 px from the silhouette. Recall is the fraction of visible GT crease pixels within 1.5 px of a drawn linelet.

| cp_ratio | n_keep | FP px/kpx @5 | FP px/kpx @8 | FP linelets/kpx @5 | crease R@1.5 | recall delta vs base | % of base recall |
|---|---|---|---|---|---|---|---|
| base (cp=0) | 16208 | 22.12 | 12.11 | 4.30 | 0.7136 | +0.0000 | 100.0% |
| 0.50 | 15543 | 21.33 | 11.62 | 4.22 | 0.7041 | -0.0095 | 98.7% |
| 0.55 | 15327 | 20.30 | 11.16 | 4.05 | 0.6983 | -0.0153 | 97.9% |
| 0.60 | 15023 | 19.23 | 10.66 | 3.87 | 0.6867 | -0.0269 | 96.2% |
| 0.65  **<-- KNEE** | 14615 | 17.63 | 9.84 | 3.64 | 0.6675 | -0.0460 | 93.6% |
| 0.70 | 14222 | 16.08 | 8.97 | 3.36 | 0.6393 | -0.0743 | 89.6% |
| 0.75 | 13767 | 14.72 | 8.32 | 3.15 | 0.6175 | -0.0960 | 86.5% |
| 0.80 | 13124 | 13.00 | 7.42 | 2.86 | 0.5917 | -0.1218 | 82.9% |
| 0.85 | 12150 | 11.18 | 6.52 | 2.43 | 0.5504 | -0.1631 | 77.1% |
| 0.90 | 10662 | 9.23 | 5.52 | 2.02 | 0.5145 | -0.1990 | 72.1% |
| 0.95 | 7774 | 6.01 | 3.72 | 1.27 | 0.4505 | -0.2631 | 63.1% |

**KNEE = cp_ratio 0.65**: FP density 22.12 -> 17.63 px/kpx at crease-clear 5px (-20.3%), keeping 93.6% of base true-crease recall (0.7136 -> 0.6675).

## Knee temporal confirmation (run exactly once, chair @120 frames, corrected orbit)

| config | OURS Frechet med | OURS P_pop | cut_frac | strokes/frame | BASE Frechet / P_pop | Frechet ratio | P_pop ratio |
|---|---|---|---|---|---|---|---|
| base (cp=0) | 0.082 | 0.068 | 0.043 | 752 | 1.252 / 0.756 | 15.2x | 11.1x |
| **knee cp=0.65** | 0.077 | 0.078 | 0.057 | 718 | 1.252 / 0.756 | 16.2x | 9.7x |

Temporal win **not regressed**: Frechet improves (0.082 -> 0.077 px) and the
BASELINE/OURS advantage stays the same order (15.2x -> 16.2x Frechet,
11.1x -> 9.7x P_pop). P_pop rises slightly
(0.068 -> 0.078) because pruning shortens some stroke chains, which is the
expected cost of removing carriers rather than a loss of coherence.

