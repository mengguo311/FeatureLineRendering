"""tier1/scripts/comparison_fig.py — VISUALISATION ONLY.

Assembles out/featviz/COMPARISON_ours_vs_poster.png from images that already exist on disk.
No metrics are computed here and no pipeline is run: every number printed on the figure is
quoted from a banked json (out/boiltest.json, out/poster_repro_lego.json) and every picture is
a crop or a paste of a file rendered earlier.  Mesh is not touched.
"""
import os
import cv2
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
VIZ = os.path.join(TIER1, "out", "featviz")
OUTP = os.path.join(VIZ, "COMPARISON_ours_vs_poster.png")


def rd(name):
    im = cv2.imread(os.path.join(VIZ, name))
    if im is None:
        raise SystemExit(f"missing {name}")
    return im[:, :, ::-1]


# the three field tiles are cropped out of the 11-tile panel (image area only, headers dropped)
PANEL = rd("poster_repro_lego_fields.png")
CROPS = {"opacity": (160, 780, 620, 1240),
         "normal": (160, 780, 1860, 2480),
         "topk8": (858, 1478, 0, 620)}

poster_still = rd("poster_repro_lego_composite_still.png")
ours_still = rd("stroke_cadpartA_dd3_still.png")
ours_strip = rd("stroke_cadpartA_dd3_strip.png")

# ink_churn, all three measured on LEGO over the SAME 8 consecutive orbit frames (100-107).
# quoted from out/boiltest.json and out/poster_repro_lego.json -- nothing recomputed here.
BARS = [("per-frame Canny\n(image-space baseline)", 0.536, "1.0x", "#c0392b"),
        ("poster fused composite\n(image-space, per-frame)", 0.178, "3.0x steadier", "#e08e0b"),
        ("ours: object-space linelets\n(persistent 3D)", 0.058, "9.2x steadier", "#1f7a4d")]

CAPTION = (
    "Both methods extract feature lines from a FROZEN vanilla 3DGS. Neither uses a mesh at any point in the "
    "method path.\n"
    "The poster method is IMAGE-SPACE and recomputed independently every frame, so its lines flicker as the "
    "camera moves. Ours lifts lines to PERSISTENT 3D loci that are\n"
    "drawn from every view, so they do not. The poster is the baseline our object-space work extends -- "
    "view-stable 3D feature lines are its own stated future work.\n\n"
    "DISCLOSURE -- the two rows use DIFFERENT ASSETS and this is NOT a same-asset head-to-head. The poster row "
    "is the lego bulldozer (the poster asset); our row is cadpartA\n"
    "(our clean-solid headline) because our lego stroke result is coverage-limited. The figure therefore "
    "contrasts METHOD CHARACTER, not two methods on one object.\n"
    "The stability bars are the one same-asset comparison in this figure: all three ink_churn values are measured "
    "on LEGO over the same 8 consecutive orbit frames, so the\n"
    "bar labelled \"ours\" is our lego number, not the cadpartA still shown above it. "
    "Reproduction caveat: we have not seen the poster or its Figure 3, so the top row is our\n"
    "reconstruction from a description of the method and its fidelity to the source is NOT verified."
)

fig = plt.figure(figsize=(24, 21.0), dpi=100)
fig.patch.set_facecolor("white")
gs = GridSpec(6, 4, figure=fig, height_ratios=[0.42, 5.6, 0.42, 4.7, 2.7, 3.9],
              hspace=0.26, wspace=0.05,
              left=0.022, right=0.978, top=0.955, bottom=0.015)

fig.suptitle("Feature lines from a frozen 3DGS: image-space per-frame fields  vs  "
             "object-space persistent strokes", fontsize=30, fontweight="bold", y=0.988)


def band(row, text, fc):
    ax = fig.add_subplot(gs[row, :])
    ax.set_axis_off()
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes, facecolor=fc,
                               edgecolor="none"))
    ax.text(0.008, 0.5, text, transform=ax.transAxes, va="center", ha="left",
            fontsize=19, fontweight="bold", color="white")


def show(row, col, img, title, span=None, fs=15):
    ax = fig.add_subplot(gs[row, col] if span is None else gs[row, col:span])
    ax.imshow(img)
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_color("#999999")
    ax.set_title(title, fontsize=fs, pad=7)
    return ax


# ---------------- ROW 1: the poster method ----------------
band(0, "ROW 1  -  IMAGE-SPACE rasterization-state fields, PER-FRAME   "
        "(Hao and Mukai, SIGGRAPH Asia 2025 poster -- OUR REPRODUCTION)", "#8a5a00")
show(1, 0, poster_still,
     "fused composite (feature line rendering)\nlego bulldozer, held-out view cams[5]")
for i, (k, (y0, y1, x0, x1)) in enumerate(CROPS.items()):
    lbl = {"opacity": "1. OPACITY discontinuity\n(pure silhouette detector)",
           "normal": "2. NORMAL discontinuity\n(4-neighbour max angle)",
           "topk8": "3. TOP-K GAUSSIAN field, k=8\n(weighted-overlap dissimilarity)"}[k]
    show(1, i + 1, PANEL[y0:y1, x0:x1], lbl)

# ---------------- ROW 2: our method ----------------
band(2, "ROW 2  -  OBJECT-SPACE persistent 3D linelets, TEMPORALLY STABLE   (ours)", "#14543a")
show(3, 0, ours_still, "dd3 stroke rendering -- cadpartA\nBLACK = our strokes\n"
                       "faint PINK = GT-mesh crease overlay, EVAL-ONLY", fs=13.5)
ax = show(3, 1, ours_strip, "the SAME strokes over consecutive orbit frames "
                            "-- the ink does not reorganise", span=4)

# ---------------- stability axis ----------------
axb = fig.add_subplot(gs[4, :])
_p = axb.get_position()
axb.set_position([0.175, _p.y0, 0.978 - 0.175, _p.height])   # room for the category labels
ypos = np.arange(len(BARS))[::-1]
for (lbl, v, mult, c), y in zip(BARS, ypos):
    axb.barh(y, v, height=0.55, color=c, edgecolor="none")
    axb.text(v + 0.008, y, f"{v:.3f}   ({mult})", va="center", ha="left",
             fontsize=17, fontweight="bold", color=c)
axb.set_yticks(ypos)
axb.set_yticklabels([b[0] for b in BARS], fontsize=15)
axb.set_xlim(0, 0.70)
axb.set_xlabel("ink_churn  -  fraction of drawn pixels with no counterpart within 1.5 px in the "
               "adjacent frame   (LOWER = STEADIER)", fontsize=16, labelpad=12)
axb.set_title("STABILITY AXIS  -  all three measured on LEGO, same 8 consecutive orbit frames "
              "(quoted from banked json, nothing recomputed for this figure)",
              fontsize=17, fontweight="bold", pad=10)
axb.tick_params(axis="x", labelsize=13)
for sp in ("top", "right", "left"):
    axb.spines[sp].set_visible(False)
axb.grid(axis="x", alpha=0.25, linestyle=":")
axb.set_axisbelow(True)

# ---------------- caption ----------------
axc = fig.add_subplot(gs[5, :])
axc.set_axis_off()
axc.text(0.0, 0.90, CAPTION, transform=axc.transAxes, va="top", ha="left",
         fontsize=15.5, linespacing=1.5, color="#1a1a1a", family="DejaVu Sans")

fig.savefig(OUTP, dpi=100, facecolor="white")
im = cv2.imread(OUTP)
print(f"wrote {OUTP}  {im.shape[1]}x{im.shape[0]}")
