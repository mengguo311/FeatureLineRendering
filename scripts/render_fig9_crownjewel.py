"""Fig 9 + Tab 5 — the CROWN JEWEL: object-space lines vs per-frame Canny temporal coherence.

Pure transcription of FROZEN result jsons, in the style and with the discipline of
scripts/render_figs.py: every plotted value is asserted against the banked ledger
(`out/m1b_stroke_temporal_table.md` ratio tables and `out/RESULTS_MASTER.md` §1.1) to its
stated precision BEFORE anything is written. A mismatch aborts loudly. No new analysis, no
new experiment, no mesh anywhere in this file.

WHY THIS FIGURE DID NOT ALREADY EXIST
    Fig 3/4 compare against the *strongest possible accumulated* 2D baseline (oracle rigid
    flow + occlusion-aware EMA), Fig 2 is the PARETO-1 precision/density frontier and Fig 5
    is stroke survival. Tab 1 quotes the Canny ratios only at 30f and 240f, mixed in with
    E_warp. The headline claim the paper actually leads with -- "7-13x fewer popped strokes
    than per-frame Canny" -- had no figure of its own, and its two confound controls
    (sparsity, silhouette warp-drop) were prose only.  Slots 1-8 are taken, so this is Fig 9.

SCENES
    chair + lego. **ficus is NOT included and cannot be**: it has no banked temporal or P/R
    result of any kind, and `out/m1b_headline_table.md` records it as deliberately EXCLUDED
    ("thin/foliage: only 33% of object pixels are >4px from a silhouette, so 'crease vs flat
    surface' is not well posed"). The paper is scoped n=2 throughout. Adding ficus would
    require new experiments, which this figure set is forbidden to run. It is shown as an
    explicit excluded row in Tab 5 rather than silently dropped.
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = os.path.expanduser("~/3dgs_line/tier1/out")
GREEN, RED, BLUE, GRAY, ORANGE = "#1a7f37", "#c0392b", "#2456a4", "#8a8a8a", "#e69f00"
FRAMES = [30, 60, 120, 240]
FAILS = []


def check(name, val, ledger, nd):
    ok = round(float(val), nd) == ledger
    print(f"  [{'OK ' if ok else 'MISMATCH'}] {name}: {float(val):.6f} -> "
          f"round({nd}) {round(float(val), nd)} vs ledger {ledger}")
    if not ok:
        FAILS.append(name)
    return float(val)


print("=== DRIFT GATE: frozen json vs banked ledger ===")
T = json.load(open(f"{OUT}/m1b_stroke_temporal_table.json"))
H, C = T["headline"], T["control_fg_only"]

# ---- banked ratio tables (out/m1b_stroke_temporal_table.md §1 and §2b) -------------------
LEDGER_POP = {("lego", 30): 3.44, ("lego", 60): 5.30, ("lego", 120): 8.10,
              ("lego", 240): 11.49, ("chair", 30): 8.52, ("chair", 60): 10.17,
              ("chair", 120): 11.11, ("chair", 240): 11.35}
LEDGER_FRE = {("lego", 30): 2.43, ("lego", 60): 4.24, ("lego", 120): 7.49,
              ("lego", 240): 14.03, ("chair", 30): 4.19, ("chair", 60): 7.87,
              ("chair", 120): 15.22, ("chair", 240): 29.92}
LEDGER_POP_CTRL = {("lego", 120): 5.29, ("lego", 240): 6.49,
                   ("chair", 120): 6.85, ("chair", 240): 7.01}
LEDGER_FRE_CTRL = {("lego", 120): 7.15, ("lego", 240): 13.44,
                   ("chair", 120): 14.83, ("chair", 240): 28.79}

pop, fre, ratio_pop, ratio_fre = {}, {}, {}, {}
for sc in ("lego", "chair"):
    for nf in FRAMES:
        e = H[sc]["by_frames"][str(nf)]
        pop[(sc, nf, "A")], pop[(sc, nf, "B")] = e["A"]["P_pop"], e["B"]["P_pop"]
        fre[(sc, nf, "A")] = e["A"]["frechet_median"]
        fre[(sc, nf, "B")] = e["B"]["frechet_median"]
        ratio_pop[(sc, nf)] = check(f"P_pop ratio {sc} {nf}f",
                                    e["B"]["P_pop"] / e["A"]["P_pop"], LEDGER_POP[(sc, nf)], 2)
        ratio_fre[(sc, nf)] = check(f"Frechet ratio {sc} {nf}f",
                                    e["B"]["frechet_median"] / e["A"]["frechet_median"],
                                    LEDGER_FRE[(sc, nf)], 2)
ctrl_pop, ctrl_fre = {}, {}
for sc in ("lego", "chair"):
    for nf in (120, 240):
        e = C[sc]["by_frames"][str(nf)]
        ctrl_pop[(sc, nf)] = check(f"CTRL P_pop ratio {sc} {nf}f",
                                   e["B"]["P_pop"] / e["A"]["P_pop"],
                                   LEDGER_POP_CTRL[(sc, nf)], 2)
        ctrl_fre[(sc, nf)] = check(f"CTRL Frechet ratio {sc} {nf}f",
                                   e["B"]["frechet_median"] / e["A"]["frechet_median"],
                                   LEDGER_FRE_CTRL[(sc, nf)], 2)

# ---- RESULTS_MASTER.md 1.1 endpoints ----------------------------------------------------
check("ledger endpoint P_pop min (lego 30f)", ratio_pop[("lego", 30)], 3.44, 2)
check("ledger endpoint P_pop max (lego 240f)", ratio_pop[("lego", 240)], 11.49, 2)
check("ledger endpoint Frechet min (lego 30f)", ratio_fre[("lego", 30)], 2.43, 2)
check("ledger endpoint Frechet max (chair 240f)", ratio_fre[("chair", 240)], 29.92, 2)

# ---- confound controls ------------------------------------------------------------------
cf = T["confound_warp_dropped_frac"]
for k, led in (("BASE_lego", 0.198), ("BASE_chair", 0.182),
               ("OURS_lego", 0.002), ("OURS_chair", 0.0)):
    check(f"warp-drop {k}", cf[k], led, 3)
spf = {}
for sc in ("lego", "chair"):
    for nf in (240,):
        spf[(sc, "A")] = H[sc]["by_frames"][str(nf)]["A"]["n_strokes_per_frame"]
        spf[(sc, "B")] = H[sc]["by_frames"][str(nf)]["B"]["n_strokes_per_frame"]
check("sparsity OURS lego strokes/frame", spf[("lego", "A")], 1122, 0)
check("sparsity BASE lego strokes/frame", spf[("lego", "B")], 615, 0)
check("sparsity OURS chair strokes/frame", spf[("chair", "A")], 751, 0)
check("sparsity BASE chair strokes/frame", spf[("chair", "B")], 578, 0)

# ---- per-scene P/R at the banked M1b headline stage --------------------------------------
STAGE = "AFTER   pull+prune[tuned+len]"
PR = {}
for sc in ("chair", "lego"):
    d = json.load(open(f"{OUT}/m1b_{sc}_gated_test.json"))
    row = [r for r in d["rows"] if r["stage"] == STAGE and r["kind"] == "segments"][0]
    PR[sc] = (row["P1.5"], row["R1.5"], row["n"])
# chair is the ledger-quoted Appendix-A baseline; lego is the same stage/convention
check("PR chair P@1.5", PR["chair"][0], 0.6573, 4)
check("PR chair R@1.5", PR["chair"][1], 0.5959, 4)
print(f"  [note] lego P@1.5 {PR['lego'][0]:.4f} / R@1.5 {PR['lego'][1]:.4f} — same stage "
      f"and convention, surfaced from the banked m1b_lego_gated_test.json (no prior ledger "
      f"constant to assert against)")

if FAILS:
    print(f"\n*** DRIFT GATE FAILED: {FAILS} — NOTHING WRITTEN. ***")
    sys.exit(1)
print("\n=== DRIFT GATE PASSED — rendering ===")

plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False})

# ================================================================ Fig 2
fig, axs = plt.subplots(1, 3, figsize=(13.6, 4.5),
                        gridspec_kw={"width_ratios": [1.15, 1.5, 1.0]})

# -- (a) the mechanism: the baseline floor is motion-independent
ax = axs[0]
for sc, col in (("chair", BLUE), ("lego", GREEN)):
    ax.plot(FRAMES, [pop[(sc, f, "A")] for f in FRAMES], "-o", color=col, lw=2, ms=5,
            label=f"OURS · {sc}")
    ax.plot(FRAMES, [pop[(sc, f, "B")] for f in FRAMES], "--s", color=col, lw=1.6, ms=4,
            alpha=0.65, label=f"Canny · {sc}")
ax.set_xscale("log", base=2)
ax.set_xticks(FRAMES); ax.set_xticklabels(FRAMES)
ax.set_xlabel("frames on the held-out orbit\n(denser = smaller motion per frame)", labelpad=2)
ax.set_ylabel("$P_{pop}$  (popped-stroke rate, lower = steadier)", labelpad=4)
ax.set_ylim(0, 1.02)
ax.legend(fontsize=7.8, ncol=2, loc="lower left", framealpha=0.95)
ax.set_title("(a) per-frame detection saturates at a\nmotion-independent popping floor",
             fontsize=9.5)
ax.annotate("Canny floor: strokes are\nre-derived every frame", xy=(120, 0.742),
            xytext=(31, 0.93), fontsize=7.8, color=RED, ha="left",
            arrowprops=dict(arrowstyle="->", color=RED, lw=1))

# -- (b) the headline ratios + the silhouette-controlled bound
ax = axs[1]
x = np.arange(len(FRAMES))
w = 0.36
for i, (sc, col) in enumerate((("chair", BLUE), ("lego", GREEN))):
    vals = [ratio_pop[(sc, f)] for f in FRAMES]
    b = ax.bar(x + (i - 0.5) * w, vals, w, color=col, label=f"{sc}", zorder=3)
    for bb, v in zip(b, vals):
        ax.text(bb.get_x() + bb.get_width() / 2, v + 0.25, f"{v:.2f}",
                ha="center", fontsize=7.8, fontweight="bold")
    for j, f in enumerate(FRAMES):
        if (sc, f) in ctrl_pop:
            xc = x[j] + (i - 0.5) * w
            ax.plot([xc - w / 2, xc + w / 2], [ctrl_pop[(sc, f)]] * 2, color=RED, lw=2.4,
                    solid_capstyle="butt", zorder=6,
                    label="silhouette-controlled bound" if (i == 0 and j == 2) else None)
            ax.annotate("", xy=(xc, ctrl_pop[(sc, f)] + 0.10),
                        xytext=(xc, vals[j] - 0.10), zorder=6,
                        arrowprops=dict(arrowstyle="-|>", color=RED, lw=1.1))
ax.axhspan(7, 13, color=ORANGE, alpha=0.13, zorder=0)
ax.text(1.02, 7.35, "banked 7–13× band", fontsize=8, color="#7a5200", ha="left")
ax.set_xticks(x); ax.set_xticklabels([f"{f}f" for f in FRAMES])
ax.set_xlabel("frames on the held-out orbit", labelpad=2)
ax.set_ylabel("$P_{pop}$ ratio  (Canny / OURS, higher = better)", labelpad=4)
ax.set_ylim(0, 14.6)
ax.legend(fontsize=8, loc="upper left", ncol=1, framealpha=0.95)
ax.set_title("(b) 3.44× → 11.49× as motion refines;\nred line = silhouette-controlled bound",
             fontsize=9.5)

# -- (c) both confounds, controlled
ax = axs[2]
lbl = ["OURS\nchair", "Canny\nchair", "OURS\nlego", "Canny\nlego"]
sp = [spf[("chair", "A")], spf[("chair", "B")], spf[("lego", "A")], spf[("lego", "B")]]
cols = [BLUE, GRAY, GREEN, GRAY]
b = ax.bar(lbl, sp, color=cols, width=0.66)
for bb, v in zip(b, sp):
    ax.text(bb.get_x() + bb.get_width() / 2, v + 18, f"{v:.0f}", ha="center", fontsize=8.2,
            fontweight="bold")
ax.set_ylabel("strokes drawn per frame (240f)", labelpad=4)
ax.set_ylim(0, 1560)
ax.set_title("(c) not a sparsity artefact — OURS draws\nMORE strokes, and drops far fewer",
             fontsize=9.5)
for sc, xi in (("chair", 1), ("lego", 3)):
    ax.text(xi, sp[xi] + 95, f"warp-drop\n{cf['BASE_' + sc]*100:.1f}%", ha="center",
            fontsize=7.6, color=RED)
    ax.text(xi - 1, sp[xi - 1] + 95, f"warp-drop\n{cf['OURS_' + sc]*100:.1f}%", ha="center",
            fontsize=7.6, color=GREEN)

plt.suptitle("Fig 9 — the crown jewel: object-space feature lines vs per-frame Canny, "
             "held-out orbit, identical warp operator for both", fontsize=11, y=0.985)
plt.tight_layout(rect=[0, 0, 1, 0.92])
plt.savefig(f"{OUT}/fig9_crownjewel.png", dpi=170)
plt.close()
print("wrote fig9_crownjewel.png")

# ================================================================ Tab 5
def render_table(fname, title, cols, rows, col_w=None, fs=9, figw=None, rs=1.35,
                 grey_rows=(), footnote=None):
    fig, ax = plt.subplots(figsize=(figw or 11.0, 0.40 * len(rows) + 1.25))
    ax.axis("off")
    t = ax.table(cellText=rows, colLabels=cols, loc="center", cellLoc="center",
                 colWidths=col_w)
    t.auto_set_font_size(False); t.set_fontsize(fs); t.scale(1, rs)
    for (r, cc), cell in t.get_celld().items():
        if r == 0:
            cell.set_facecolor("#e8e8e8"); cell.set_text_props(fontweight="bold")
        elif r in grey_rows:
            cell.set_facecolor("#f2f2f2"); cell.set_text_props(color="#666666")
    ax.set_title(title, fontsize=11, pad=12)
    if footnote:
        ax.text(0.5, -0.06, footnote, transform=ax.transAxes, ha="center", va="top",
                fontsize=7.8, color="#555555")
    plt.tight_layout(); plt.savefig(f"{OUT}/{fname}", dpi=170, bbox_inches="tight")
    plt.close()
    print(f"wrote {fname}")


rows = []
for sc in ("chair", "lego"):
    rows.append([sc,
                 f"{PR[sc][0]:.4f}", f"{PR[sc][1]:.4f}",
                 f"{pop[(sc, 240, 'A')]:.3f}", f"{pop[(sc, 240, 'B')]:.3f}",
                 f"{ratio_pop[(sc, 240)]:.2f}×", f"{ctrl_pop[(sc, 240)]:.2f}×",
                 f"{ratio_fre[(sc, 240)]:.2f}×"])
rows.append(["ficus", "—", "—", "—", "—", "—", "—", "—"])
render_table(
    "tab5_per_scene.png",
    "Tab 5 — per-scene held-out TEST summary: accuracy and temporal coherence (all values banked)",
    ["scene", "P@1.5", "R@1.5", "$P_{pop}$ OURS", "$P_{pop}$ Canny",
     "$P_{pop}$ ratio", "ratio (silhouette-ctrl)", "Fréchet ratio"],
    rows, col_w=[0.08, 0.09, 0.09, 0.11, 0.11, 0.11, 0.22, 0.12], figw=11.9,
    grey_rows=(3,),
    footnote="P@1.5 / R@1.5: segment-raster, held-out TEST views, stage AFTER pull+prune"
             "[tuned+len] (m1b_{scene}_gated_test.json).  $P_{pop}$ columns: 240-frame "
             "held-out orbit, identical warp operator for both pipelines.\n"
             "ficus is EXCLUDED by scene scoping, not missing by omission: only 33% of its "
             "object pixels lie >4 px from a silhouette, so 'crease vs flat surface' is not "
             "well posed (m1b_headline_table.md). No ficus result was ever run.")
print("\nficus row is intentionally empty: no banked temporal or P/R result exists, and "
      "out/m1b_headline_table.md records it as EXCLUDED (thin/foliage; only 33% of object "
      "pixels are >4px from a silhouette).")
print("ALL RENDERED")
