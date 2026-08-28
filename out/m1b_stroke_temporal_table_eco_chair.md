# M1b STEP-06 — forward-warped STROKE temporal residual

Metric: forward-warped stroke temporal residual (discrete Frechet, px) + popping penalty P_pop.  Warp: identical depth-based forward warp for both pipelines.
Held-out: TEST views only; trajectory 5->15.  Stroke variant: `eco_chair`.

- **A = OURS**: object-space carrier — DT-pulled linelets chained into static 3D polylines, projected into each frame.
- **B = BASELINE**: naive image-space Canny re-traced independently every frame.

| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** | unmatched | cuts | warp-dropped | strokes/frame | verts/stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|
| chair | 30 | OURS | 0.358 | 0.738 | 0.196 | **0.100** | 0.076 | 0.024 | 0.000 | 676 | 4.98 |
| chair | 30 | BASE | 1.378 | 2.637 | 0.468 | **0.788** | 0.786 | 0.003 | 0.150 | 577 | 2.25 |
| chair | 60 | OURS | 0.180 | 0.366 | 0.104 | **0.073** | 0.048 | 0.025 | 0.000 | 674 | 4.97 |
| chair | 60 | BASE | 1.294 | 2.618 | 0.435 | **0.770** | 0.767 | 0.003 | 0.148 | 577 | 2.25 |
| chair | 120 | OURS | 0.090 | 0.183 | 0.053 | **0.064** | 0.039 | 0.024 | 0.000 | 673 | 4.96 |
| chair | 120 | BASE | 1.255 | 2.612 | 0.421 | **0.756** | 0.753 | 0.003 | 0.148 | 575 | 2.25 |
| chair | 240 | OURS | 0.045 | 0.091 | 0.027 | **0.061** | 0.036 | 0.025 | 0.000 | 672 | 4.96 |
| chair | 240 | BASE | 1.225 | 2.615 | 0.414 | **0.755** | 0.752 | 0.003 | 0.148 | 578 | 2.25 |

## Headline ratios (BASELINE / OURS — higher means our strokes are steadier)

| scene | frames | Frechet med ratio | P_pop ratio |
|---|---|---|---|
| chair | 30 | 3.84x | 7.89x |
| chair | 60 | 7.19x | 10.55x |
| chair | 120 | 13.94x | 11.88x |
| chair | 240 | 27.30x | 12.42x |

## Stroke graphs

| scene | linelets | after 3D NMS | strokes | median vertices/stroke |
|---|---|---|---|---|
| chair | 15420 | 7949 | 1059 | 4 |
