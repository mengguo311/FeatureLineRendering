# 3DGS Feature-Line Rendering — Research Proposal Workspace

Hybrid **object-space + image-space feature-line (NPR) rendering** for **3D Gaussian Splatting (3DGS)**: extract 3D edge candidates (silhouette / crease / corner) directly from the Gaussian covariance field (no mesh), fuse them with image-space G-buffer edges, for temporally stable, real-time line drawing — no retraining of the 3DGS model.

M1 research proposal · Umetani Lab, The University of Tokyo.

## Layout
```
.
├── slides_outline.md          # English proposal-defense slide outline (~16 slides)
├── novelty_survey.md          # prior-art / novelty survey (cited)
├── figures/                   # schematic figures for the slides (synthetic)
│   ├── make_figures.py        #   fig_A..D: image-space vs object-space, flicker
│   ├── make_pipeline.py       #   fig_E: hybrid pipeline architecture
│   └── fig_*.png
└── real_3dgs/                 # experiments on REAL 3DGS scenes (CPU, no GPU)
    ├── render.py              #   CPU EWA splatter (.splat / .ply -> G-buffer)
    ├── preview.py             #   pick a camera (3 PCA views)
    ├── experiment.py          #   image-space vs object-space line drawing
    ├── montage.py             #   combine into one overview
    └── outputs/{comparison,gbuffer,preview}/   # result images
```

## Reproduce
```bash
# python env for figures + experiments (numpy / matplotlib / scipy / plyfile)
python3.11 -m venv figures/.venv
figures/.venv/bin/pip install numpy matplotlib scipy plyfile

# schematic slide figures
cd figures && .venv/bin/python make_figures.py && .venv/bin/python make_pipeline.py && cd ..

# real-scene experiments (scene data download URLs in real_3dgs/README.md)
cd real_3dgs && ../figures/.venv/bin/python experiment.py nike.splat mid 1.35 && ../figures/.venv/bin/python montage.py
```

Scene data (`*.splat`, `*.ply`) and the virtualenv are git-ignored; see `real_3dgs/README.md` for the download commands.
