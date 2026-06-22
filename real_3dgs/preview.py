# -*- coding: utf-8 -*-
"""Render 3 PCA candidate views of a .splat scene so we can pick a camera.
Usage: preview.py <scene.splat> [opacity_cut=0.2] [max_splats=200000]
"""
import sys, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from render import load_scene, build_geometry, render

scene = sys.argv[1]
opacity_cut = float(sys.argv[2]) if len(sys.argv) > 2 else 0.2
max_splats = int(sys.argv[3]) if len(sys.argv) > 3 else 200000

pos, scl, quat, rgb, opa = load_scene(scene)
keep = opa > opacity_cut
pos, scl, quat, rgb, opa = [a[keep] for a in (pos, scl, quat, rgb, opa)]
if len(pos) > max_splats:
    idx = np.argsort(opa)[-max_splats:]
    pos, scl, quat, rgb, opa = [a[idx] for a in (pos, scl, quat, rgb, opa)]
print("scene %s: %d splats used" % (scene, len(pos)))
cov3d, normal = build_geometry(pos, scl, quat)

center = np.median(pos, axis=0)
C = np.cov((pos - center).T)
ev, evec = np.linalg.eigh(C)
thin, mid, long = evec[:, 0], evec[:, 1], evec[:, 2]
scale = np.linalg.norm(np.percentile(pos, 95, 0) - np.percentile(pos, 5, 0))

views = {"thin": (thin, mid), "mid": (mid, thin), "long": (long, mid)}
fig, ax = plt.subplots(1, 3, figsize=(13, 4.6))
for j, (nm, (d, u)) in enumerate(views.items()):
    out = render(pos, cov3d, normal, rgb, opa, center + d * scale * 1.4, center, u,
                 W=440, H=440, fov=45, verbose=False)
    img = out["color"].copy(); img[~out["mask"]] = 1.0
    ax[j].imshow(img); ax[j].set_title("%s  cov=%.0f%%" % (nm, 100 * out["mask"].mean()))
    ax[j].set_xticks([]); ax[j].set_yticks([])
stem = os.path.splitext(os.path.basename(scene))[0]
os.makedirs("outputs/preview", exist_ok=True)
plt.tight_layout(); plt.savefig("outputs/preview/preview_%s.png" % stem, dpi=130, bbox_inches="tight")
print("saved outputs/preview/preview_%s.png" % stem)
