"""Fig 7 + Tab 1-4 renders. Values transcribed from the FROZEN ledger; json-backed values
drift-checked against their source files before rendering (same protocol as render_figs.py)."""
import os
import json
import sys

import numpy as np
import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.expanduser("~/3dgs_line/tier1/out")
GREEN, RED, BLUE, GRAY, ORANGE = "#1a7f37", "#c0392b", "#2456a4", "#8a8a8a", "#e69f00"
FAILS = []


def check(name, jv, lv, nd):
    if round(float(jv), nd) != lv:
        FAILS.append((name, jv, lv))
        print(f"  [MISMATCH] {name}: {jv} vs {lv}")
    return float(jv)


# ---- drift checks for Fig 7 (json-backed)
c = json.load(open(f"{OUT}/dexprimary_p1c_chair.json"))
l = json.load(open(f"{OUT}/dexprimary_p1c_lego.json"))
vals = {
    "chair": {"FAM-C (mesh)": check("c C", c["probes"]["FAM-C(dino)"]["xsplit"]["eval_auc"], 0.8401, 4),
              "FAM-C guarded chain": check("c Cg", c["chains_guarded"]["FAM-C(probe)"]["auc"], 0.8205, 4),
              "FAM-A photometric": check("c A", c["probes"]["FAM-A"]["xsplit"]["eval_auc"], 0.7112, 4),
              "FAM-B geometric": check("c B", c["probes"]["FAM-B"]["xsplit"]["eval_auc"], 0.6461, 4)},
    "lego": {"FAM-C (mesh)": check("l C", l["probes"]["FAM-C(dino)"]["xsplit"]["eval_auc"], 0.9044, 4),
             "FAM-C guarded chain": check("l Cg", l["chains_guarded"]["FAM-C(probe)"]["auc"], 0.8913, 4),
             "FAM-A photometric": check("l A", l["probes"]["FAM-A"]["xsplit"]["eval_auc"], 0.6600, 4),
             "FAM-B geometric": check("l B", l["probes"]["FAM-B"]["xsplit"]["eval_auc"], 0.7260, 4)},
}
d2 = json.load(open(f"{OUT}/pareto_verdict.json"))
check("tab2 worst", d2["chair"]["worst_conservative_advantage"], 2.42, 2)
if FAILS:
    print("DRIFT GATE FAILED", FAILS); sys.exit(1)
print("drift checks OK — rendering")

# ================================================================ Fig 7
panel = cv2.imread(f"{OUT}/dexprimary_p1c_chair.png")           # existing P1c viz (3 panels)
H, W = panel.shape[:2]
mid = panel[:, int(W * 0.315):int(W * 0.72)]                    # middle panel: DINO prob map
fig = plt.figure(figsize=(12.5, 5.0))
ax = fig.add_axes([0.02, 0.03, 0.46, 0.80])
ax.imshow(cv2.cvtColor(mid, cv2.COLOR_BGR2RGB))
ax.set_xticks([]); ax.set_yticks([])
ax.set_title("frozen DINOv2 probe: predicted crease-probability\n"
             "(fabric field suppressed, structural piping/frame kept)", fontsize=10)
ax2 = fig.add_axes([0.56, 0.12, 0.42, 0.70])
names = list(vals["chair"].keys())
x = np.arange(len(names))
w = 0.36
b1 = ax2.bar(x - w / 2, [vals["chair"][n] for n in names], w, color=BLUE, label="chair")
b2 = ax2.bar(x + w / 2, [vals["lego"][n] for n in names], w, color=ORANGE, label="lego")
for bs in (b1, b2):
    for b in bs:
        ax2.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.006,
                 f"{b.get_height():.3f}", ha="center", fontsize=8)
ax2.axhline(0.5, color=GRAY, ls=":", lw=0.8)
ax2.set_xticks(x)
ax2.set_xticklabels([n.replace(" ", "\n") for n in names], fontsize=8.5)
ax2.set_ylim(0.4, 1.0)
ax2.set_ylabel("crease-vs-texture AUC (held-out xsplit)")
ax2.legend(fontsize=9)
ax2.set_title("the separating signal EXISTS — and only the\nsemantic family carries it",
              fontsize=10)
plt.suptitle("Fig 7 — Act 3: the missing precision signal exists in frozen DINOv2 features",
             fontsize=11, y=0.975)
plt.savefig(f"{OUT}/fig7_semantic.png", dpi=160)
plt.close()
print("wrote fig7_semantic.png")


# ================================================================ table renderer
def render_table(fname, title, cols, rows, col_w=None, highlight=None, fs=9, figw=None, rs=1.35):
    fig, ax = plt.subplots(figsize=(figw or max(7.5, 1.9 * len(cols)), 0.42 * len(rows) + 1.4))
    ax.axis("off")
    t = ax.table(cellText=rows, colLabels=cols, loc="center", cellLoc="center",
                 colWidths=col_w)
    t.auto_set_font_size(False)
    t.set_fontsize(fs)
    t.scale(1, rs)
    for (r, cc), cell in t.get_celld().items():
        if r == 0:
            cell.set_facecolor("#e8e8e8"); cell.set_text_props(fontweight="bold")
        if highlight and (r, cc) in highlight:
            cell.set_facecolor("#fbe3e0")
    ax.set_title(title, fontsize=11, pad=14)
    plt.tight_layout()
    plt.savefig(f"{OUT}/{fname}", dpi=170)
    plt.close()
    print(f"wrote {fname}")


# Tab 1 — stroke-level banked ratios (transcribed from ledger §1.1 / TRACK_P / m1b tables)
render_table("tab1_stroke_ratios.png",
    "Tab 1 — stroke-level temporal ratios (banked; baseline / OURS, higher = steadier)",
    ["condition", "E_warp ratio (vs per-frame TEED)", "condition", "Fréchet ratio (vs per-frame Canny)", "P_pop ratio"],
    [["chair · T1 orbit", "20.44×", "chair · 30f", "4.19×", "8.52×"],
     ["chair · T2 orbit+zoom", "21.62×", "chair · 240f", "29.92×", "11.35×"],
     ["chair · T3 spline", "6.49×", "lego · 30f", "2.43×", "3.44×"],
     ["lego · T1 orbit", "10.38×", "lego · 240f", "14.03×", "11.49×"],
     ["lego · T2 orbit+zoom", "10.61×", "", "", ""],
     ["lego · T3 spline (worst)", "3.38×", "", "", ""]],
    col_w=[0.20, 0.25, 0.13, 0.27, 0.15], figw=11.5)

# Tab 2 — PARETO-1 failing-point anatomy (chair CANNY 150/300; ledger §1.3)
render_table("tab2_floor_anatomy.png",
    "Tab 2 — the PARETO-1 mean-statistic FAIL, dissected (chair, Canny 150/300 vs OURS f=0.15)",
    ["statistic (pooled over all warped line px)", "advantage", "frozen gate", "reading"],
    [["pooled-MEAN E_warp", "2.42×", "≥3× — FAIL", "floor-compressed: OURS sits at the\n~0.28 px raster/warp floor (p95 = 1.00 px)"],
     ["pop-rate P(d>2 px)", "12.8×", "—", "floor-free"],
     ["pop-rate P(d>3 px)", "15.4×", "—", "floor-free"],
     ["pixel flicker (1 px tol)", "12.2×", "—", "floor-free"]],
    col_w=[0.35, 0.10, 0.15, 0.40], figw=9.8, rs=1.6,
    highlight={(1, 1): True, (1, 2): True})

# Tab 3 — K_geom ~= 0 (ledger §2 Act 2)
render_table("tab3_kgeom.png",
    "Tab 3 — no geometric or low-level cue separates crease from texture on the miss-set (lego decals)",
    ["cue", "AUC / statistic", "verdict"],
    [["2DGS surfel dihedral (3D)", "0.4110", "≤ chance"],
     ["2DGS rendered-normal ribbon", "0.3307", "≤ chance"],
     ["vanilla-3DGS normal ribbon", "0.3875", "≤ chance"],
     ["GT-MESH dihedral (perfect geometry)", "0.3964", "≤ chance"],
     ["GT-mesh normal dispersion", "0.4675 (medians 44.52° vs 44.84°)", "0.32° apart"],
     ["SH-DC albedo step", "fabric p50 0.1235 vs crease 0.1211", "gate LEAKS"],
     ["multi-view consistency", "texture 0.870 vs crease 0.937", "non-separating"]],
    col_w=[0.42, 0.38, 0.20], figw=10.8)

# Tab 4 — the frozen-gate ledger (ledger §3, verbatim values)
render_table("tab4_gate_ledger.png",
    "Tab 4 — every pre-registered gate, evaluated on its letter (none re-tuned)",
    ["gate", "bar", "measured", "disposition"],
    [["PARETO-1 pooled-mean ≥3× everywhere", "3×", "2.42×", "FAIL; floor mechanism measured, claim carried by pop/flicker"],
     ["PARETO-2 vs oracle-flow EMA", "2× floor", "1.72×", "NO-GO on the letter; frozen conservative lower bound"],
     ["PARETO-3 residual in disocclusion ≥60 %", "60/40 %", "33.3 %", "NO-GO; no mechanism sentence"],
     ["Phase 0 single-view coverage R_miss", "0.50/0.35", "0.095 (≈chance)", "NO-GO; direction killed"],
     ["Phase 1b triangulation recall > ceiling", "0.79", "0.6753", "MARGINAL; localization fix banked"],
     ["Phase 1d mesh-free discriminator", "0.78/0.72", "0.6371", "NO-GO; supervision-bound"],
     ["DIAG2DGS dihedral gate", "0.80", "0.4110", "FAIL; K_geom≈0 established"]],
    col_w=[0.32, 0.09, 0.13, 0.46], fs=8.5, figw=11.0)
print("ALL RENDERED")
