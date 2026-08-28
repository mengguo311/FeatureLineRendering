# M1b STEP-06 — forward-warped STROKE temporal residual

Metric: forward-warped stroke temporal residual (discrete Frechet, px) + popping penalty P_pop.  Warp: identical depth-based forward warp for both pipelines.
Held-out: TEST views only; trajectory 5->15.  Stroke variant: `tgapA`.

- **A = OURS**: object-space carrier — DT-pulled linelets chained into static 3D polylines, projected into each frame.
- **B = BASELINE**: naive image-space Canny re-traced independently every frame.

| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** | unmatched | cuts | warp-dropped | strokes/frame | verts/stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|
| lego | 30 | OURS | 0.569 | 1.767 | 0.301 | **0.236** | 0.207 | 0.029 | 0.000 | 1319 | 4.97 |
| lego | 30 | BASE | 1.510 | 2.686 | 0.518 | **0.803** | 0.801 | 0.002 | 0.160 | 616 | 2.24 |
| lego | 60 | OURS | 0.301 | 1.349 | 0.178 | **0.150** | 0.118 | 0.032 | 0.000 | 1320 | 4.97 |
| lego | 60 | BASE | 1.397 | 2.636 | 0.481 | **0.764** | 0.762 | 0.002 | 0.160 | 616 | 2.24 |
| lego | 120 | OURS | 0.155 | 0.927 | 0.096 | **0.095** | 0.061 | 0.034 | 0.000 | 1321 | 4.97 |
| lego | 120 | BASE | 1.275 | 2.584 | 0.442 | **0.734** | 0.732 | 0.002 | 0.161 | 617 | 2.24 |
| lego | 240 | OURS | 0.078 | 0.534 | 0.049 | **0.067** | 0.032 | 0.035 | 0.000 | 1322 | 4.97 |
| lego | 240 | BASE | 1.203 | 2.555 | 0.421 | **0.719** | 0.717 | 0.002 | 0.161 | 615 | 2.24 |

## Headline ratios (BASELINE / OURS — higher means our strokes are steadier)

| scene | frames | Frechet med ratio | P_pop ratio |
|---|---|---|---|
| lego | 30 | 2.65x | 3.40x |
| lego | 60 | 4.65x | 5.08x |
| lego | 120 | 8.24x | 7.75x |
| lego | 240 | 15.41x | 10.70x |

## Stroke graphs

| scene | linelets | after 3D NMS | strokes | median vertices/stroke |
|---|---|---|---|---|
| lego | 31915 | 17244 | 2304 | 4 |
