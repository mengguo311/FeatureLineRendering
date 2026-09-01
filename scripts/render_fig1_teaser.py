"""Fig 1 teaser — assembled ONLY from the existing banked side-by-side temporal video
(out/m1b_temporal_sidebyside_chair.mp4; published M1b assets). No new analysis.
Layout: 2 rows (OURS / per-frame BASELINE) x [3 trajectory frames + 2-frame overlap] +
stat inset. The overlap column composites frame t (red) with t+1 (blue): stable lines
overlap to dark purple; popped/shifted lines show as isolated red/blue fringes."""
import os

import sys

import cv2
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
for q in (TIER1, os.path.join(TIER1, "scripts")):
    sys.path.insert(0, q)
OUT = os.path.join(TIER1, "out")
VID = f"{OUT}/m1b_temporal_sidebyside_chair.mp4"
FRAMES = [100, 150, 200]
Y0, Y1 = 48, 848
OX, BX = (0, 800), (802, 1602)


def grab(v, i):
    v.set(cv2.CAP_PROP_POS_FRAMES, i)
    ok, f = v.read()
    assert ok, i
    return f


def crop(f, side):
    x0, x1 = OX if side == "ours" else BX
    return f[Y0:Y1 - 45, x0:x1]          # crop the per-frame stroke-count footer


def lines(img):
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) < 128


def overlap_rgb(m0, m1):
    im = np.ones((*m0.shape, 3), np.float32)
    im[m0] = [0.85, 0.15, 0.15]                     # frame t = red
    im[m1] = np.where(m0[m1][:, None], [0.25, 0.05, 0.45], [0.15, 0.25, 0.85])  # t+1 blue; both purple
    return im


v = cv2.VideoCapture(VID)
frames = {i: grab(v, i) for i in set(FRAMES + [f + 1 for f in FRAMES[:1]])}
v.release()

# --- gray object underlay for the SAME trajectory cameras (visual context only; the
#     published video's trajectory is the 240-frame look-at orbit TEST 5->15)
from src import common, render                       # noqa: E402
import temporal_m1b as TM                            # noqa: E402
import torch                                         # noqa: E402
cams, _ = common.load_cameras("chair")
g = common.load_gaussians("chair")
keep_g = render.defloat_mask(g["mu"], g["opacity"])
target = np.median(g["mu"][keep_g], axis=0)
traj = TM.orbit_cameras(cams[5], cams[15], 240, target)
under = {}
for i in FRAMES:
    gb = render.render_gbuffer(g, keep_g, traj[i], with_albedo=True)
    alb = gb["albedo"].detach().cpu().numpy().mean(2)
    a = gb["alpha"].detach().cpu().numpy()
    shade = np.clip(a * (0.30 * (1.0 - alb) + 0.10), 0, 1)   # faint shaded silhouette
    under[i] = (1.0 - shade)[:Y1 - Y0 - 45, :]                # white bg, light-gray object
    del gb
    torch.cuda.empty_cache()


def with_underlay(img, i):
    """strokes (dark) over a faint gray render of the object."""
    m = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) < 128
    base = np.repeat(under[i][:, :, None], 3, 2)
    base[m] = [0.05, 0.05, 0.05]
    return base

fig, axs = plt.subplots(2, 5, figsize=(15.6, 6.6),
                        gridspec_kw={"width_ratios": [1, 1, 1, 1, 0.9]})
for r, side in enumerate(("ours", "base")):
    for c, fi in enumerate(FRAMES):
        ax = axs[r, c]
        ax.imshow(with_underlay(crop(frames[fi], side), fi))
        ax.set_xticks([]); ax.set_yticks([])
        if r == 0:
            ax.set_title(f"frame {fi}/240", fontsize=10)
    m0 = lines(crop(frames[FRAMES[0]], side))
    m1 = lines(crop(frames[FRAMES[0] + 1], side))
    ax = axs[r, 3]
    ax.imshow(overlap_rgb(m0, m1))
    ax.set_xticks([]); ax.set_yticks([])
    if r == 0:
        ax.set_title(f"frames {FRAMES[0]}+{FRAMES[0]+1} overlaid\n(red=t, blue=t+1)",
                     fontsize=9)
axs[0, 0].set_ylabel("OURS — static 3D lines,\nprojected per frame", fontsize=10)
axs[1, 0].set_ylabel("per-frame image-space\ndetection (Canny)", fontsize=10)

ax = axs[0, 4]
ax.axis("off")
ax.text(0.02, 0.95, "interior temporal stability\nat MATCHED precision\nAND density",
        fontsize=11.5, fontweight="bold", va="top", transform=ax.transAxes)
ax.text(0.02, 0.56,
        "1.72–8.35×\nfewer popped line-pixels than an\nORACLE-FLOW accumulated\n"
        "2D baseline (≥5.19× in 3 of 4\nconditions)",
        fontsize=10.5, va="top", transform=ax.transAxes, color="#1a7f37")
ax.text(0.02, 0.13, "worst adversarial cell:\n1.72× = the frozen floor",
        fontsize=10, va="top", transform=ax.transAxes, color="#c0392b")
ax2 = axs[1, 4]
ax2.axis("off")
ax2.text(0.02, 0.9, "≥9.8× vs memoryless\nper-frame detectors\n(every shared point)",
         fontsize=10.5, va="top", transform=ax2.transAxes)
ax2.text(0.02, 0.42, "stability is threshold-\ninvariant: it comes from the\n"
         "object-space parameterization,\nnot from drawing fewer lines",
         fontsize=9.5, va="top", transform=ax2.transAxes, color="#444444")
plt.suptitle("Fig 1 — object-space feature lines from a frozen 3DGS: stable where "
             "per-frame detection flickers", fontsize=12, y=0.99)
plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig(f"{OUT}/fig1_teaser.png", dpi=150)
print("wrote out/fig1_teaser.png")
