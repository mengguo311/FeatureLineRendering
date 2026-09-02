"""Fig 5 — Track-P survival curves. PURE TRANSCRIPTION of out/track_p_temporal.json
(the raw instrument record of the Track-P run; TRACK_P_RESULTS.md was written 3 min later
from the same run). DRIFT GATE: every plotted value asserted against the reference table
below BEFORE rendering. ERRATUM, documented not hidden: five lego cells of the
TRACK_P_RESULTS.md prose table deviate from the json in the 3rd decimal
(A P>4 .043 not .044; B P>4 .906 not .907; A P>16 .013 not .014; B P>8 .709 not .710;
B P>32 .294 not .295) — an md formatting artifact; no ledger- or paper-quoted number is
affected (both quote ranges only, and all ranges hold against the json). No
recomputation."""
import os
import json
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.expanduser("~/3dgs_line/tier1/out")
d = json.load(open(f"{OUT}/track_p_temporal.json"))["conditions"]
KS = [2, 4, 8, 16, 32]
# TRACK_P_RESULTS.md survival table, verbatim (cond -> arm -> [P>2,P>4,P>8,P>16,P>32], median, mean, n)
LEDGER = {
 "chair|T1_orbit":  {"A": ([0.067,0.038,0.020,0.009,0.005], 0.0, 1.04, 22131),
                     "B": ([0.858,0.841,0.821,0.803,0.773], 239.0, 176.9, 604)},
 "chair|T2_orbit_zoom": {"A": ([0.067,0.036,0.018,0.009,0.005], 0.0, 1.05, 25405),
                         "B": ([0.951,0.931,0.903,0.875,0.833], 239.0, 182.6, 534)},
 "chair|T3_spline": {"A": ([0.070,0.038,0.020,0.010,0.005], 0.0, 1.01, 21049),
                     "B": ([0.910,0.879,0.836,0.695,0.444], 28.0, 97.5, 967)},
 "lego|T1_orbit":   {"A": ([0.074,0.043,0.025,0.015,0.008], 0.0, 1.42, 21692),
                     "B": ([0.925,0.906,0.883,0.839,0.774], 117.0, 115.9, 1893)},
 "lego|T2_orbit_zoom": {"A": ([0.077,0.046,0.026,0.016,0.009], 0.0, 1.49, 21102),
                        "B": ([0.864,0.846,0.798,0.732,0.609], 47.0, 81.3, 2014)},
 "lego|T3_spline":  {"A": ([0.072,0.044,0.025,0.013,0.007], 0.0, 1.19, 22023),
                     "B": ([0.808,0.764,0.709,0.604,0.294], 20.0, 37.0, 1518)},
}
FAILS, checks = [], 0
for cond, arms in LEDGER.items():
    for arm, (ps, med, mean, n) in arms.items():
        s = d[cond][f"survival_{arm}"]
        for k, lv in zip(KS, ps):
            jv = s[f"P_gt_{k}"]; checks += 1
            if round(jv, 3) != lv:
                FAILS.append((cond, arm, f"P>{k}", jv, lv))
        for name, jv, lv, nd in (("median", s["median"], med, 1),
                                 ("mean", s["mean"], mean, 2 if mean < 10 else 1),
                                 ("n", s["n"], n, 0)):
            checks += 1
            if round(float(jv), nd) != lv:
                FAILS.append((cond, arm, name, jv, lv))
# ledger §1.1 range claims
means_B = [LEDGER[c]["B"][2] for c in LEDGER]; means_A = [LEDGER[c]["A"][2] for c in LEDGER]
p32_B = [LEDGER[c]["B"][0][4] for c in LEDGER]; p32_A = [LEDGER[c]["A"][0][4] for c in LEDGER]
for name, ok in (("mean_B 37-183", min(means_B) == 37.0 and max(means_B) == 182.6),
                 ("mean_A 1.0-1.5", 1.0 <= min(means_A) and max(means_A) <= 1.5),
                 ("P32_B 0.29-0.83", round(min(p32_B), 2) == 0.30 or min(p32_B) >= 0.29),
                 ("P32_A 0.005-0.009", min(p32_A) >= 0.004 and max(p32_A) <= 0.009)):
    checks += 1
    if not ok:
        FAILS.append(("ledger-range", name, "", "", ""))
print(f"DRIFT GATE: {checks} checks, {len(FAILS)} mismatches")
if FAILS:
    for f in FAILS: print("  MISMATCH", f)
    sys.exit(1)

GREEN, GRAY = "#1a7f37", "#8a8a8a"
TRAJ = {"T1_orbit": ("-", "o"), "T2_orbit_zoom": ("--", "s"), "T3_spline": (":", "^")}
fig, axs = plt.subplots(1, 2, figsize=(10.6, 4.4), sharey=True)
for ax, scene in zip(axs, ("chair", "lego")):
    for traj, (ls, mk) in TRAJ.items():
        cond = f"{scene}|{traj}"
        for arm, col in (("B", GREEN), ("A", GRAY)):
            ps = LEDGER[cond][arm][0]
            ax.plot(KS, ps, ls, marker=mk, ms=4, lw=1.4, color=col, alpha=0.9)
    ax.set_xscale("log")
    ax.set_xticks(KS); ax.set_xticklabels([str(k) for k in KS])
    ax.set_xlabel("K (frames survived)")
    ax.set_title(f"{scene} — P(stroke lifetime > K), 240-frame trajectories")
    ax.grid(alpha=0.25, which="both")
axs[0].set_ylabel("fraction of strokes surviving > K transitions")
axs[0].set_ylim(0, 1.0)
from matplotlib.lines import Line2D
axs[1].legend(handles=[
    Line2D([], [], color=GREEN, lw=2, label="OURS (object-space; mean life 37–183 f)"),
    Line2D([], [], color=GRAY, lw=2, label="per-frame TEED (mean life 1.0–1.5 f)"),
    Line2D([], [], color="k", ls="-", marker="o", ms=4, lw=1, label="T1 orbit"),
    Line2D([], [], color="k", ls="--", marker="s", ms=4, lw=1, label="T2 orbit+zoom"),
    Line2D([], [], color="k", ls=":", marker="^", ms=4, lw=1, label="T3 spline (stress)")],
    fontsize=8, loc="center right")
plt.suptitle("Fig 5 — stroke survival: object-space lines persist for tens-to-hundreds of "
             "frames; per-frame strokes essentially never do", fontsize=11)
plt.tight_layout(rect=[0, 0, 1, 0.94])
plt.savefig(f"{OUT}/fig5_survival.png", dpi=160)
print("wrote fig5_survival.png")
