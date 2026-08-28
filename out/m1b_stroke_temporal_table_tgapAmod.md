# M1b STEP-06 — forward-warped STROKE temporal residual

Metric: forward-warped stroke temporal residual (discrete Frechet, px) + popping penalty P_pop.  Warp: identical depth-based forward warp for both pipelines.
Held-out: TEST views only; trajectory 5->15.  Stroke variant: `tgapA`.

- **A = OURS**: object-space carrier — DT-pulled linelets chained into static 3D polylines, projected into each frame.
- **B = BASELINE**: naive image-space Canny re-traced independently every frame.

| scene | frames | pipeline | Frechet med | Frechet p90 | Chamfer med | **P_pop** | unmatched | cuts | warp-dropped | strokes/frame | verts/stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|
| lego | 30 | OURS | 0.483 | 1.689 | 0.261 | **0.329** | 0.136 | 0.193 | 0.002 | 1773 | 4.74 |
| lego | 30 | BASE | 1.505 | 2.689 | 0.517 | **0.803** | 0.801 | 0.002 | 0.160 | 616 | 2.24 |
| lego | 60 | OURS | 0.252 | 1.279 | 0.156 | **0.271** | 0.070 | 0.200 | 0.002 | 1772 | 4.74 |
| lego | 60 | BASE | 1.393 | 2.631 | 0.481 | **0.764** | 0.762 | 0.002 | 0.160 | 616 | 2.24 |
| lego | 120 | OURS | 0.129 | 0.896 | 0.090 | **0.237** | 0.031 | 0.206 | 0.002 | 1772 | 4.74 |
| lego | 120 | BASE | 1.271 | 2.584 | 0.442 | **0.734** | 0.732 | 0.002 | 0.161 | 617 | 2.24 |
| lego | 240 | OURS | 0.065 | 0.532 | 0.048 | **0.219** | 0.012 | 0.208 | 0.002 | 1772 | 4.74 |
| lego | 240 | BASE | 1.202 | 2.553 | 0.420 | **0.719** | 0.717 | 0.002 | 0.161 | 615 | 2.24 |

## Headline ratios (BASELINE / OURS — higher means our strokes are steadier)

| scene | frames | Frechet med ratio | P_pop ratio |
|---|---|---|---|
| lego | 30 | 3.12x | 2.44x |
| lego | 60 | 5.54x | 2.82x |
| lego | 120 | 9.89x | 3.10x |
| lego | 240 | 18.52x | 3.28x |

## Stroke graphs

| scene | linelets | after 3D NMS | strokes | median vertices/stroke |
|---|---|---|---|---|
| lego | 31915 | 27669 | 2673 | 4 |
