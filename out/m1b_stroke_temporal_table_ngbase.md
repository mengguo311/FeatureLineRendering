# M1b STEP-06 — forward-warped STROKE temporal residual

Metric: forward-warped stroke temporal residual (discrete Frechet, px) + popping penalty P_pop.  Warp: identical depth-based forward warp for both pipelines.
Held-out: TEST views only; trajectory 5->15.  Stroke variant: `tcteed`.

- **A = OURS**: object-space carrier — DT-pulled linelets chained into static 3D polylines, projected into each frame.
- **B = BASELINE**: naive image-space Canny re-traced independently every frame.

| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** | unmatched | cuts | warp-dropped | strokes/frame | verts/stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|
| chair | 30 | OURS | 0.347 | 0.727 | 0.184 | **0.093** | 0.065 | 0.027 | 0.001 | 727 | 5.06 |
| chair | 30 | BASE | 1.376 | 2.638 | 0.468 | **0.788** | 0.786 | 0.003 | 0.151 | 576 | 2.25 |
| chair | 60 | OURS | 0.174 | 0.359 | 0.098 | **0.068** | 0.041 | 0.027 | 0.001 | 725 | 5.05 |
| chair | 60 | BASE | 1.291 | 2.614 | 0.434 | **0.770** | 0.768 | 0.003 | 0.148 | 577 | 2.25 |
| chair | 120 | OURS | 0.087 | 0.178 | 0.050 | **0.059** | 0.031 | 0.027 | 0.001 | 723 | 5.06 |
| chair | 120 | BASE | 1.253 | 2.611 | 0.421 | **0.756** | 0.753 | 0.003 | 0.148 | 575 | 2.25 |
| chair | 240 | OURS | 0.043 | 0.089 | 0.025 | **0.058** | 0.030 | 0.027 | 0.001 | 723 | 5.05 |
| chair | 240 | BASE | 1.225 | 2.616 | 0.414 | **0.755** | 0.752 | 0.003 | 0.148 | 578 | 2.25 |

## Headline ratios (BASELINE / OURS — higher means our strokes are steadier)

| scene | frames | Frechet med ratio | P_pop ratio |
|---|---|---|---|
| chair | 30 | 3.97x | 8.50x |
| chair | 60 | 7.43x | 11.35x |
| chair | 120 | 14.48x | 12.86x |
| chair | 240 | 28.36x | 13.13x |

## Stroke graphs

| scene | linelets | after 3D NMS | strokes | median vertices/stroke |
|---|---|---|---|---|
| chair | 15971 | 8640 | 1137 | 4 |
