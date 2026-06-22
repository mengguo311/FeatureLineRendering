# -*- coding: utf-8 -*-
"""Stack per-object comparison figures into one montage.
Usage:
  montage.py                                  -> captured trio (nike/plush/luigi)
  montage.py <out_stem> <scene1> <scene2> ... -> custom set
"""
import sys, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

args = sys.argv[1:]
if args:
    out_stem, objs = args[0], args[1:]
    title = "Image-space vs object-space line drawing on 3DGS"
else:
    out_stem = "all_objects"
    objs = ["nike", "plush", "luigi"]
    title = "Image-space vs object-space line drawing on 3 real 3DGS scenes  (CPU, no GPU)"

fig, ax = plt.subplots(len(objs), 1, figsize=(10.5, 5.0 * len(objs)))
if len(objs) == 1:
    ax = [ax]
for a, name in zip(ax, objs):
    a.imshow(mpimg.imread("outputs/comparison/%s_comparison.png" % name))
    a.axis("off")
    a.text(0.005, 0.5, name, transform=a.transAxes, rotation=90,
           va="center", ha="center", fontsize=11, fontweight="bold")
fig.suptitle(title, fontsize=12.5, y=0.997)
plt.tight_layout(rect=[0.01, 0, 1, 0.99])
plt.savefig("outputs/%s_comparison.png" % out_stem, dpi=150, bbox_inches="tight")
print("saved outputs/%s_comparison.png" % out_stem)
