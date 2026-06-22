# -*- coding: utf-8 -*-
"""Hybrid pipeline architecture diagram for the proposal method slide."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OBJ = "#1f5fd6"; IMG = "#c43a2b"; FUSE = "#7a3fb5"; OUT = "#0a8a3a"
OBJ_F = "#eaf1fc"; IMG_F = "#fdecea"; FUSE_F = "#f1eafa"; OUT_F = "#e7f7ee"
GREY = "#444444"


def box(ax, x, y, w, h, text, ec, fc, fs=10.5, bold=False):
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.10",
                       fc=fc, ec=ec, lw=2.0)
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color="#1a1a1a",
            fontweight="bold" if bold else "normal")
    return (x, y, w, h)


def arrow(ax, p0, p1, color=GREY, lw=2.0):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=18,
                                 lw=lw, color=color,
                                 connectionstyle="arc3,rad=0.0"))


fig, ax = plt.subplots(figsize=(16.5, 7.6))
fig.patch.set_facecolor("white")
ax.set_xlim(0, 17); ax.set_ylim(0, 8); ax.axis("off")

# Input
inp = box(ax, 0.3, 3.2, 2.4, 1.5,
          "Pretrained\n3DGS scene\n(μ, Σ, α, SH)", "#333333", "#f0f0f0",
          fs=11, bold=True)

# ---- Top lane : OBJECT-SPACE (offline) ----
ax.text(8.6, 7.35, "OBJECT-SPACE   —   precompute, once per scene",
        ha="center", fontsize=12.5, color=OBJ, fontweight="bold")
a1 = box(ax, 3.3, 5.55, 3.1, 1.35,
         "KNN graph over centers\n+ per-Gaussian normal\nfrom covariance Σ", OBJ, OBJ_F)
a2 = box(ax, 6.8, 5.55, 3.1, 1.35,
         "Local normal-structure\ntensor  T = Σ wⱼ nⱼ nⱼᵀ\n→ eigenvalues λ₁≥λ₂≥λ₃", OBJ, OBJ_F)
a3 = box(ax, 10.3, 5.55, 3.4, 1.35,
         "3D edge candidates\nsilhouette / crease / corner\n(+ strength)", OBJ, OBJ_F, bold=True)

# ---- Bottom lane : IMAGE-SPACE (per frame) ----
ax.text(7.0, 0.5, "IMAGE-SPACE   —   per frame, GPU",
        ha="center", fontsize=12.5, color=IMG, fontweight="bold")
b1 = box(ax, 3.3, 1.15, 3.4, 1.35,
         "Splat render →\ndepth + normal\nG-buffer", IMG, IMG_F)
b2 = box(ax, 7.1, 1.15, 3.4, 1.35,
         "Sobel / Canny →\nraw image-space\nedges", IMG, IMG_F)

# ---- Fusion ----
fu = box(ax, 10.95, 3.05, 3.5, 1.8,
         "FUSION\nproject 3D candidates\n· signal-specific gate\n· temporal anchoring", FUSE, FUSE_F,
         fs=10.5, bold=True)

# ---- Output ----
ou = box(ax, 14.75, 3.15, 2.0, 1.6,
         "Clean +\ntemporally\nSTABLE\nfeature lines", OUT, OUT_F, fs=10.5, bold=True)

# ---- arrows ----
# input -> both lanes
arrow(ax, (2.7, 4.3), (3.3, 6.2), OBJ)
arrow(ax, (2.7, 3.6), (3.3, 1.85), IMG)
# object lane chain
arrow(ax, (6.4, 6.22), (6.8, 6.22), OBJ)
arrow(ax, (9.9, 6.22), (10.3, 6.22), OBJ)
# image lane chain
arrow(ax, (6.7, 1.82), (7.1, 1.82), IMG)
# lanes -> fusion
arrow(ax, (12.0, 5.55), (12.5, 4.85), OBJ)     # candidates down into fusion
arrow(ax, (10.5, 2.5), (12.0, 3.05), IMG)      # raw edges up into fusion
# fusion -> output
arrow(ax, (14.45, 3.95), (14.75, 3.95), FUSE)

# footer constraints
ax.text(8.6, -0.25,
        "No mesh reconstruction      ·      No retraining      ·      "
        "Real-time, compatible with any pretrained 3DGS scene",
        ha="center", fontsize=11.5, color="#222222", style="italic")

plt.tight_layout()
plt.savefig("fig_E_pipeline.png", dpi=200, bbox_inches="tight")
plt.close()
print("saved: fig_E_pipeline.png")
