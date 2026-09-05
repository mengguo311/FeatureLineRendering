# M1b STEP-06 — forward-warped STROKE temporal residual

Metric: forward-warped stroke temporal residual (discrete Frechet, px) + popping penalty P_pop.  Warp: identical depth-based forward warp for both pipelines.
Held-out: TEST views only; trajectory 5->15.  Stroke variant: `ungated`.

- **A = OURS**: object-space carrier — DT-pulled linelets chained into static 3D polylines, projected into each frame.
- **B = BASELINE**: naive image-space Canny re-traced independently every frame.

| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** | unmatched | cuts | warp-dropped | strokes/frame | verts/stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ficus | 30 | OURS | 0.589 | 2.121 | 0.300 | **0.417** | 0.404 | 0.013 | 0.002 | 421 | 4.12 |
| ficus | 30 | BASE | 1.692 | 2.741 | 0.565 | **0.876** | 0.875 | 0.001 | 0.314 | 573 | 2.22 |
| ficus | 60 | OURS | 0.361 | 1.965 | 0.190 | **0.275** | 0.260 | 0.015 | 0.002 | 422 | 4.12 |
| ficus | 60 | BASE | 1.439 | 2.701 | 0.487 | **0.854** | 0.852 | 0.002 | 0.319 | 569 | 2.22 |
| ficus | 120 | OURS | 0.199 | 1.428 | 0.109 | **0.164** | 0.147 | 0.017 | 0.002 | 421 | 4.12 |
| ficus | 120 | BASE | 1.328 | 2.638 | 0.449 | **0.820** | 0.817 | 0.003 | 0.316 | 571 | 2.22 |
| ficus | 240 | OURS | 0.101 | 0.811 | 0.057 | **0.103** | 0.085 | 0.018 | 0.002 | 421 | 4.12 |
| ficus | 240 | BASE | 1.148 | 2.512 | 0.385 | **0.786** | 0.782 | 0.003 | 0.316 | 571 | 2.22 |

## Headline ratios (BASELINE / OURS — higher means our strokes are steadier)

| scene | frames | Frechet med ratio | P_pop ratio |
|---|---|---|---|
| ficus | 30 | 2.88x | 2.10x |
| ficus | 60 | 3.99x | 3.11x |
| ficus | 120 | 6.69x | 5.01x |
| ficus | 240 | 11.36x | 7.64x |

## Stroke graphs

| scene | linelets | after 3D NMS | strokes | median vertices/stroke |
|---|---|---|---|---|
| ficus | 7172 | 4872 | 612 | 4 |
