# -*- coding: utf-8 -*-
"""Stack the per-object comparison figures into one montage for a slide."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

import os
objs = ["nike", "plush", "luigi"]
labels = ["nike.splat (270k)", "plush.splat (281k)", "luigi.ply (15k)"]
fig, ax = plt.subplots(len(objs), 1, figsize=(10.5, 5.0 * len(objs)))
for a, name, lab in zip(ax, objs, labels):
    a.imshow(mpimg.imread("outputs/comparison/%s_comparison.png" % name))
    a.axis("off")
    a.text(0.005, 0.5, lab, transform=a.transAxes, rotation=90,
            va="center", ha="center", fontsize=11, fontweight="bold")
fig.suptitle("Image-space vs object-space line drawing on 3 real 3DGS scenes  (CPU, no GPU)",
             fontsize=12.5, y=0.997)
plt.tight_layout(rect=[0.01, 0, 1, 0.99])
plt.savefig("outputs/all_objects_comparison.png", dpi=150, bbox_inches="tight")
print("saved outputs/all_objects_comparison.png")
