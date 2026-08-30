"""Two-panel summary: the M1b P-R frontier per scene, with every edge-source arm on it.

*** ANALYSIS ONLY — reads the jsons run_m1b.py already wrote. ***

The point of the figure is the SIGN FLIP: the un-blurred Canny arm sits far BELOW chair's
frontier and ABOVE lego's, with nothing changed but the object.
"""
import os
import sys
import json
import glob

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
OUT = os.path.join(TIER1, "out")
SEG = "AFTER   pull+prune[tuned+len]"

STYLE = {
    "canny":            dict(c="#444444", m="o", label="Canny (M1a, published)"),
    "teed_native_0.5":  dict(c="#1f77b4", m="s", label="TEED @0.5 (learned, zero-shot)"),
    "teed05":           dict(c="#1f77b4", m="s", label="TEED @0.5 (learned, zero-shot)"),
    "teed_native_0.9":  dict(c="#7fb3d5", m="v", label="TEED @0.9"),
    "teed09":           dict(c="#7fb3d5", m="v", label="TEED @0.9"),
    "union_native_0.5": dict(c="#17becf", m="D", label="union(Canny, TEED)"),
    "union05":          dict(c="#17becf", m="D", label="union(Canny, TEED)"),
    "cannysharp":       dict(c="#ff7f0e", m="^", label="Canny un-blurred (0,50,150)"),
    "cannysharplow":    dict(c="#d62728", m="*", label="Canny un-blurred (0,20,60)"),
}


def load(prefix):
    arms = {}
    for p in sorted(glob.glob(os.path.join(OUT, prefix + "*.json"))):
        tag = os.path.basename(p)[len(prefix):-len(".json")]
        name, f = tag.rsplit("_f", 1)
        d = json.load(open(p))
        for r in d["rows"]:
            if r["kind"] == "segments" and r["stage"] == SEG:
                arms.setdefault(name, []).append((float(f), r["R1.5"], r["P1.5"]))
    return {k: sorted(v) for k, v in arms.items()}


def main():
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.6))
    for ax, (scene, prefix, note) in zip(axes, [
            ("chair", "m1b_chair_tc_", "Canny edge purity 0.53  (texture-contaminated)"),
            ("lego", "m1b_lego_tc_", "Canny edge purity 0.64  (mostly real geometry)")]):
        arms = load(prefix)
        for name in ("canny", "teed_native_0.5", "teed05", "teed_native_0.9", "teed09",
                     "union_native_0.5", "union05", "cannysharp", "cannysharplow"):
            if name not in arms:
                continue
            st = STYLE[name]
            xs = [r for _, r, _ in arms[name]]
            ys = [p for _, _, p in arms[name]]
            if name == "canny":
                ax.plot(xs, ys, "-", color=st["c"], lw=2.4, zorder=3)
                ax.plot(xs, ys, st["m"], color=st["c"], ms=6, zorder=4, label=st["label"])
                for f, r, p in arms[name]:
                    if f in (0.15, 0.30, 0.50, 1.00):
                        ax.annotate(f"f={f:g}", (r, p), textcoords="offset points",
                                    xytext=(3, -11), fontsize=7.5, color=st["c"])
            else:
                ax.plot(xs, ys, st["m"], color=st["c"], ms=8, alpha=0.9,
                        label=st["label"], zorder=5, ls="--", lw=1.0)
        ax.set_title(f"{scene}   —   {note}", fontsize=11)
        ax.set_xlabel("segment recall @1.5 px  (held-out TEST)")
        ax.set_ylabel("segment precision @1.5 px")
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8, loc="best", framealpha=0.92)
    axes[0].text(0.02, 0.03,
                 "un-blurred Canny lands FAR BELOW the frontier\nLIFT_P −0.21   (learned "
                 "selectivity REQUIRED)",
                 transform=axes[0].transAxes, fontsize=9, color="#d62728",
                 va="bottom", bbox=dict(fc="white", ec="#d62728", alpha=0.9))
    axes[1].text(0.02, 0.97,
                 "the SAME detector lands ABOVE the frontier\nLIFT_P +0.07, beating TEED "
                 "2.6×   (selectivity optional)",
                 transform=axes[1].transAxes, fontsize=9, color="#d62728",
                 va="top", bbox=dict(fc="white", ec="#d62728", alpha=0.9))
    fig.suptitle("M1b held-out TEST P–R frontier: what a 2D edge source buys is "
                 "CONDITIONAL on the scene's native edge purity", fontsize=12.5)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    p = os.path.join(OUT, "teedgen_frontier_chair_vs_lego.png")
    fig.savefig(p, dpi=150)
    print("wrote", p)


if __name__ == "__main__":
    main()
