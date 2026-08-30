# M1b STEP-06 — forward-warped STROKE temporal residual

Metric: forward-warped stroke temporal residual (discrete Frechet, px) + popping penalty P_pop.  Warp: identical depth-based forward warp for both pipelines.
Held-out: TEST views only; trajectory 5->15.  Stroke variant: `plan1`.

- **A = OURS**: object-space carrier — DT-pulled linelets chained into static 3D polylines, projected into each frame.
- **B = BASELINE**: naive image-space Canny re-traced independently every frame.

| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** | unmatched | cuts | warp-dropped | strokes/frame | verts/stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|
| chair | 30 | OURS | 0.323 | 0.908 | 0.185 | **0.178** | 0.143 | 0.034 | 0.001 | 642 | 5.79 |
| chair | 30 | BASE | 1.382 | 2.640 | 0.469 | **0.789** | 0.786 | 0.003 | 0.150 | 578 | 2.25 |
| chair | 60 | OURS | 0.163 | 0.551 | 0.099 | **0.145** | 0.110 | 0.035 | 0.001 | 638 | 5.80 |
| chair | 60 | BASE | 1.295 | 2.616 | 0.434 | **0.770** | 0.768 | 0.003 | 0.148 | 577 | 2.25 |
| chair | 120 | OURS | 0.082 | 0.292 | 0.051 | **0.136** | 0.101 | 0.035 | 0.001 | 638 | 5.79 |
| chair | 120 | BASE | 1.252 | 2.611 | 0.421 | **0.756** | 0.753 | 0.003 | 0.148 | 575 | 2.25 |
| chair | 240 | OURS | 0.041 | 0.147 | 0.025 | **0.128** | 0.093 | 0.035 | 0.001 | 637 | 5.80 |
| chair | 240 | BASE | 1.225 | 2.616 | 0.414 | **0.755** | 0.752 | 0.003 | 0.148 | 578 | 2.25 |

## Headline ratios (BASELINE / OURS — higher means our strokes are steadier)

| scene | frames | Frechet med ratio | P_pop ratio |
|---|---|---|---|
| chair | 30 | 4.28x | 4.44x |
| chair | 60 | 7.95x | 5.32x |
| chair | 120 | 15.35x | 5.55x |
| chair | 240 | 30.14x | 5.90x |

## Stroke graphs

| scene | linelets | after 3D NMS | strokes | median vertices/stroke |
|---|---|---|---|---|
| chair | 14410 | 8045 | 953 | 5 |
