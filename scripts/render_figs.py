"""Path-C figures 3/4/6/8 — pure transcription of FROZEN result jsons.

DRIFT GATE: every plotted value is asserted against the RESULTS_MASTER.md ledger constant
to its stated precision BEFORE any figure is written. A mismatch aborts loudly — it is the
number-drift catch, never silently reconciled. No new analysis.
"""
import os
import json
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.expanduser("~/3dgs_line/tier1/out")
GREEN, RED, BLUE, GRAY, ORANGE = "#1a7f37", "#c0392b", "#2456a4", "#8a8a8a", "#e69f00"
FAILS = []


def check(name, json_val, ledger_val, nd):
    ok = round(float(json_val), nd) == ledger_val
    tag = "OK " if ok else "MISMATCH"
    print(f"  [{tag}] {name}: json {json_val:.6f} -> round({nd}) "
          f"{round(float(json_val), nd)} vs ledger {ledger_val}")
    if not ok:
        FAILS.append(name)
    return float(json_val)


print("=== DRIFT GATE: json vs RESULTS_MASTER.md ===")
# ---- Fig 3 sources
v2 = json.load(open(f"{OUT}/pareto2_verdict.json"))
adv = {}
for cond, ledger in (("chair_T1_orbit", 5.19), ("chair_T3_spline", 5.49),
                     ("lego_T1_orbit", 8.35), ("lego_T3_spline", 1.72)):
    adv[cond] = check(f"fig3 {cond} worst_pop_adv", v2[cond]["worst_pop_adv"], ledger, 2)

# ---- Fig 4 sources
p3 = json.load(open(f"{OUT}/pareto3_lego_T3_disocc.json"))
ri_o = check("fig4 ours interior rate", p3["ours"]["pop_RATE_interior"], 0.0214, 4)
ri_b = check("fig4 base interior rate", p3["baseline"]["pop_RATE_interior"], 0.0425, 4)
rd_b = check("fig4 base disocc rate", p3["baseline"]["pop_RATE_disocc"], 0.300, 3)
rd_o = check("fig4 ours disocc rate", p3["ours"]["pop_RATE_disocc"], 0.407, 3)
gate3 = check("fig4 gate frac", p3["gate"]["frac_baseline_pop_in_disocc"], 0.333, 3)
check("fig4 interior ratio 1.98x", ri_b / ri_o, 1.98, 2)

# ---- Fig 6 sources
ceil = {}
for sc, ledger in (("chair", 0.7908), ("lego", 0.5572)):
    c = json.load(open(f"{OUT}/cap_miss_attribution_{sc}.json"))
    ceil[sc] = check(f"fig6 {sc} R@1.5 ceiling", c["recall_at_1.5_recomputed"], ledger, 4)
pool = {}
for sc, ledger in (("chair", 0.7382), ("lego", 0.6337)):
    d = json.load(open(f"{OUT}/dexprimary_p0_{sc}_native.json"))
    pool[sc] = check(f"fig6 {sc} pool cover",
                     d["missset_2d_tau1.5"]["cover_fraction_pool"], ledger, 4)
    if sc == "lego":
        unc = check("fig6 lego UNCOVERED",
                    d["missset_2d_tau1.5"]["miss_fraction"], 0.3663, 4)
p0 = json.load(open(f"{OUT}/dexprimary_p0_lego_ms_thr005.json"))
p0_r = check("fig6b P0 R_miss (median arm)",
             p0["recovery"]["median"]["R_miss_3D_px1.5_equiv"], 0.0952, 4)
p0_c = check("fig6b P0 chance",
             p0["recovery"]["ctrl_randfg"]["R_miss_3D_px1.5_equiv"], 0.0940, 4)
p1b = json.load(open(f"{OUT}/dexprimary_p1b_chair_ref40.json"))
b_rec = check("fig6b P1b recall", p1b["clouds"]["tri_sup2"]["recall_3D_px1.5_equiv"],
              0.6753, 4)
b_rm = check("fig6b P1b R_miss", p1b["clouds"]["tri_sup2"]["R_miss_3D_px1.5_equiv"],
             0.6914, 4)

# ---- Fig 8 sources
p1d = json.load(open(f"{OUT}/dexprimary_p1d.json"))
ch_m = check("fig8 chair mesh ceiling", p1d["chair"]["mesh_ceiling_recomputed"], 0.8395, 4)
ch_f = check("fig8 chair best mesh-free",
             max(r["FAM-C_auc"] for r in p1d["chair"]["rows"].values()), 0.6371, 4)
lg_m = check("fig8 lego mesh ceiling", p1d["lego"]["mesh_ceiling_recomputed"], 0.9046, 4)
lg_f = check("fig8 lego best mesh-free",
             max(r["FAM-C_auc"] for r in p1d["lego"]["rows"].values()), 0.6569, 4)
tr_cl = check("fig8 transfer chair->lego", p1d["transfer_chair_to_lego"], 0.8245, 4)
tr_lc = check("fig8 transfer lego->chair", p1d["transfer_lego_to_chair"], 0.5626, 4)
# Act-3 existence-proof numbers quoted in captions
p1c_c = json.load(open(f"{OUT}/dexprimary_p1c_chair.json"))
p1c_l = json.load(open(f"{OUT}/dexprimary_p1c_lego.json"))
check("caption P1c chair xsplit", p1c_c["probes"]["FAM-C(dino)"]["xsplit"]["eval_auc"],
      0.8401, 4)
check("caption P1c lego xsplit", p1c_l["probes"]["FAM-C(dino)"]["xsplit"]["eval_auc"],
      0.9044, 4)

if FAILS:
    print(f"\n*** DRIFT GATE FAILED: {FAILS} — NO FIGURES WRITTEN. ***")
    sys.exit(1)
print("\n=== DRIFT GATE PASSED (all values match the ledger) — rendering ===")

plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False})

# ================================================================ Fig 3
fig, ax = plt.subplots(figsize=(6.6, 4.2))
conds = ["chair_T1_orbit", "chair_T3_spline", "lego_T1_orbit", "lego_T3_spline"]
labels = ["chair\nT1 orbit", "chair\nT3 spline", "lego\nT1 orbit", "lego\nT3 spline"]
vals = [adv[c] for c in conds]
cols = [GREEN, GREEN, GREEN, RED]
bars = ax.bar(labels, vals, color=cols, width=0.62)
ax.axhline(3.0, color=GRAY, ls="--", lw=1)
ax.axhline(2.0, color=RED, ls=":", lw=1)
ax.text(-0.42, 3.06, "GO gate 3x", color=GRAY, fontsize=8, ha="left")
ax.text(-0.42, 2.06, "NO-GO floor 2x", color=RED, fontsize=8, ha="left")
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.12, f"{v:.2f}x",
            ha="center", fontweight="bold")
ax.annotate("frozen conservative\nlower bound", xy=(3.05, 1.9), xytext=(2.45, 4.9),
            arrowprops=dict(arrowstyle="->", color=RED), color=RED, fontsize=9,
            ha="center")
ax.set_ylabel("OURS pop>2px advantage vs oracle-flow EMA\n(worst shared matched-P-and-density point)")
ax.set_title("Fig 3 — vs the strongest possible accumulated 2D baseline\n"
             "(exact rigid flow + occlusion-aware EMA; stronger than any RAFT variant)",
             fontsize=10)
ax.set_ylim(0, 9.6)
plt.tight_layout(); plt.savefig(f"{OUT}/fig3_pareto2.png", dpi=170); plt.close()
print("wrote fig3_pareto2.png")

# ================================================================ Fig 4
fig, axs = plt.subplots(1, 2, figsize=(8.6, 4.0), gridspec_kw={"width_ratios": [3, 1.15]})
ax = axs[0]
x = np.arange(2)
w = 0.34
b1 = ax.bar(x - w / 2, [ri_b, rd_b], w, color=ORANGE, label="oracle-flow EMA baseline")
b2 = ax.bar(x + w / 2, [ri_o, rd_o], w, color=GREEN, label="OURS")
ax.set_xticks(x)
ax.set_xticklabels(["INTERIOR\n(93–97% of pixels)", "DISOCCLUSION\n(3–7% of pixels)"])
for bs in (b1, b2):
    for b in bs:
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.006,
                f"{b.get_height():.3f}", ha="center", fontsize=8.5)
ax.annotate("1.98x better", xy=(0.17, 0.085), ha="center", color=GREEN,
            fontweight="bold")
ax.annotate("OURS WORSE\n(disclosed)", xy=(0.83, 0.43), ha="center", color=RED,
            fontweight="bold", fontsize=9)
ax.set_ylabel("pop>2px RATE (pooled, per region)")
ax.set_ylim(0, 0.48)
ax.legend(fontsize=8, loc="upper left")
ax.set_title("Fig 4 — where the 1.72x advantage lives (lego x T3, the hardest cell)",
             fontsize=10)
ax2 = axs[1]
ax2.bar(["baseline pop\nin disocclusion"], [gate3], color=BLUE, width=0.45)
ax2.axhline(0.60, color=GRAY, ls="--", lw=1)
ax2.axhline(0.40, color=GRAY, ls=":", lw=1)
ax2.text(0.02, 0.605, "GO 60%", fontsize=7.5, color=GRAY)
ax2.text(0.02, 0.405, "NO-GO 40%", fontsize=7.5, color=GRAY)
ax2.text(0, gate3 + 0.015, f"{gate3:.1%}", ha="center", fontweight="bold")
ax2.set_ylim(0, 0.72)
ax2.set_title("mechanism gate:\nNO-GO (diffuse\ninterior drift)", fontsize=9)
plt.tight_layout(); plt.savefig(f"{OUT}/fig4_pareto3.png", dpi=170); plt.close()
print("wrote fig4_pareto3.png")

# ================================================================ Fig 6
fig, axs = plt.subplots(1, 2, figsize=(9.2, 4.0), gridspec_kw={"width_ratios": [1.5, 1]})
ax = axs[0]
x = np.arange(2)
w = 0.34
b1 = ax.bar(x - w / 2, [ceil["chair"], ceil["lego"]], w, color=BLUE,
            label="pipeline R@1.5 ceiling (f=1.00, keep all)")
b2 = ax.bar(x + w / 2, [pool["chair"], pool["lego"]], w, color=GRAY,
            label="gaussian-pool 2D coverage")
for bs in (b1, b2):
    for b in bs:
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.012,
                f"{b.get_height():.4f}", ha="center", fontsize=8.5)
ax.annotate(f"lego UNCOVERED\n= {unc:.4f}", xy=(1.17, pool["lego"]),
            xytext=(1.05, 0.90), arrowprops=dict(arrowstyle="->", color=RED),
            color=RED, fontsize=8.5, ha="center")
ax.set_xticks(x); ax.set_xticklabels(["chair", "lego"])
ax.set_ylabel("recall / coverage")
ax.set_ylim(0, 1.02)
ax.legend(fontsize=8, loc="lower left")
ax.set_title("Fig 6 — Act 1: the coverage ceiling of the frozen carrier", fontsize=10)
ax2 = axs[1]
names = ["P0 single-view\nlift (lego)", "P0 chance\ncloud", "P1b triangulation\nrecall (chair)",
         "P1b miss-set\nrecovery"]
vals6 = [p0_r, p0_c, b_rec, b_rm]
cols6 = [ORANGE, GRAY, BLUE, BLUE]
bars = ax2.bar(names, vals6, color=cols6, width=0.6)
for b, v in zip(bars, vals6):
    ax2.text(b.get_x() + b.get_width() / 2, v + 0.012, f"{v:.4f}", ha="center", fontsize=8)
ax2.axhline(0.79, color=GRAY, ls="--", lw=1)
ax2.text(3.4, 0.80, "chair ceiling", fontsize=7.5, color=GRAY, ha="right")
ax2.tick_params(axis="x", labelsize=7)
ax2.set_ylim(0, 1.0)
ax2.set_title("Fig 6b — recovery attempts:\nchance-equal, then MARGINAL", fontsize=9)
plt.tight_layout(); plt.savefig(f"{OUT}/fig6_ceiling.png", dpi=170); plt.close()
print("wrote fig6_ceiling.png")

# ================================================================ Fig 8
fig, axs = plt.subplots(1, 2, figsize=(8.8, 4.0), gridspec_kw={"width_ratios": [1.6, 1]})
ax = axs[0]
x = np.arange(2)
w = 0.34
b1 = ax.bar(x - w / 2, [ch_m, lg_m], w, color=GREEN,
            label="mesh-supervised (the signal EXISTS)")
b2 = ax.bar(x + w / 2, [ch_f, lg_f], w, color=RED,
            label="best mesh-free supervision (collapse)")
for bs in (b1, b2):
    for b in bs:
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.008,
                f"{b.get_height():.4f}", ha="center", fontsize=8.5)
ax.axhline(0.72, color=GRAY, ls="--", lw=1)
ax.text(1.45, 0.725, "frozen NO-GO bar 0.72", fontsize=8, color=GRAY, ha="right")
ax.axhline(0.5, color=GRAY, ls=":", lw=0.8)
ax.text(1.45, 0.505, "chance", fontsize=7.5, color=GRAY, ha="right")
ax.set_xticks(x); ax.set_xticklabels(["chair", "lego"])
ax.set_ylabel("crease-vs-texture AUC (held-out xsplit)")
ax.set_ylim(0.4, 1.0)
ax.legend(fontsize=8, loc="lower right")
ax.set_title("Fig 8 — Act 4: the semantic signal is supervision-bound", fontsize=10)
ax2 = axs[1]
bars = ax2.bar(["chair→lego", "lego→chair"], [tr_cl, tr_lc],
               color=[GREEN, ORANGE], width=0.5)
for b, v in zip(bars, [tr_cl, tr_lc]):
    ax2.text(b.get_x() + b.get_width() / 2, v + 0.008, f"{v:.4f}", ha="center", fontsize=8.5)
ax2.axhline(0.5, color=GRAY, ls=":", lw=0.8)
ax2.set_ylim(0.4, 1.0)
ax2.set_title("cross-scene transfer of the\nmesh-supervised probe\n(asymmetric — one direction)",
              fontsize=9)
plt.tight_layout(); plt.savefig(f"{OUT}/fig8_supervision.png", dpi=170); plt.close()
print("wrote fig8_supervision.png")
print("\nALL FOUR FIGURES WRITTEN.")
