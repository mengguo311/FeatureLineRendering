"""tier1/scripts/tgap_plot.py — TGAP per-arm f-frontier figure (ANALYSIS ONLY, no mesh/GPU).

Left  : every scored point of all three arms, with arm A's frontier, the VAL-frozen arm B,
        arm A's Pareto envelope and the gate-1 bar drawn on top of them.
Right : the SELECTIVITY test that gate 2 asks -- the upper envelope (best precision at or
        above each recall) of arm B against the upper envelope of the TEED-BLIND arms.  If
        the learned edge prior were selective the red curve would sit above the grey one.
"""
import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
OUT = os.path.join(TIER1, "out")


def upper_env(pts, grid):
    """best precision reached at or above each recall in `grid` (nan where unreachable)."""
    out = []
    for R in grid:
        ps = [p for r, p in pts if r >= R - 1e-12]
        out.append(max(ps) if ps else np.nan)
    return np.array(out)


def main():
    scene = sys.argv[1] if len(sys.argv) > 1 else "lego"
    T = json.load(open(os.path.join(OUT, f"tgap_arms_{scene}_test.json")))
    V = json.load(open(os.path.join(OUT, f"tgap_verdict_{scene}.json")))
    a, b = V["val_selection"]["alpha"], V["val_selection"]["beta"]
    rows = T["rows"]
    A = sorted([(r["R1.5"], r["P1.5"]) for r in rows if r["arm"] == "A"])
    B = sorted([(r["R1.5"], r["P1.5"]) for r in rows if r["arm"] == "B"
                and abs(r["k1"] - a) < 1e-9 and abs(r["k2"] - b) < 1e-9])
    Ball = [(r["R1.5"], r["P1.5"]) for r in rows if r["arm"] == "B"]
    Call = [(r["R1.5"], r["P1.5"]) for r in rows if r["arm"] == "C"]
    Pmax = max(p for _, p in A)
    Rmax = max(r for r, _ in A)

    fig, ax = plt.subplots(1, 2, figsize=(13.4, 5.3))
    ax[0].scatter(*zip(*Call), s=9, c="#c9c9c9", zorder=1,
                  label="arm C — TEED-blind global relaxation (77 x 9 pts)")
    ax[0].scatter(*zip(*Ball), s=9, c="#f6c08a", zorder=2,
                  label="arm B — TGAP, all 35 (alpha,beta) x 9 f")
    ax[0].axhline(Pmax, color="k", ls=":", lw=1.1,
                  label=f"arm A Pareto envelope  P = {Pmax:.4f}")
    ax[0].axhline(Pmax + 0.030, color="crimson", ls="--", lw=1.3,
                  label="gate-1 bar  (envelope + 0.030)")
    ax[0].axvline(Rmax, color="#555555", ls="-.", lw=1.0,
                  label=f"arm A max recall  {Rmax:.4f}  (f = 1.00)")
    ax[0].plot(*zip(*A), "-o", c="#1f77b4", ms=5, lw=1.9, zorder=4,
               label="arm A — committed tuned+len prune")
    if B:
        ax[0].plot(*zip(*B), "-s", c="#d62728", ms=5, lw=1.9, zorder=5,
                   label=f"arm B at the VAL-frozen (alpha={a}, beta={b})")
    ax[0].set_xlabel("segment recall @ 1.5 px   (held-out TEST)")
    ax[0].set_ylabel("segment precision @ 1.5 px")
    ax[0].set_title(f"{scene} — f-frontier, stage AFTER pull+prune[tuned+len]")
    ax[0].legend(fontsize=7.4, loc="lower left")
    ax[0].grid(alpha=0.25)

    grid = np.linspace(0.19, 0.84, 200)
    eB, eC = upper_env(Ball, grid), upper_env(Call + A, grid)
    ax[1].plot(grid, eC, "-", c="#666666", lw=2.2, label="arm C / A envelope (TEED-blind)")
    ax[1].plot(grid, eB, "--", c="#d62728", lw=2.0, label="arm B envelope (TEED-gated)")
    ax[1].axhline(Pmax, color="k", ls=":", lw=1.1, label=f"arm A envelope P = {Pmax:.4f}")
    ax[1].axhline(Pmax + 0.030, color="crimson", ls="--", lw=1.3, label="gate-1 bar")
    ax[1].axvline(Rmax, color="#555555", ls="-.", lw=1.0, label="arm A max recall")
    ax[1].axvspan(0.22, 0.50, color="#dbe9f6", alpha=0.0)
    ax[1].set_xlabel("segment recall @ 1.5 px   (held-out TEST)")
    ax[1].set_ylabel("best precision reachable at >= that recall")
    ax[1].set_title("gate-2 question: is the TEED gate selective?  (curves coincide => no)")
    ax[1].legend(fontsize=7.6, loc="lower left")
    ax[1].grid(alpha=0.25)

    fig.tight_layout()
    p = os.path.join(OUT, f"tgap_frontier_{scene}.png")
    fig.savefig(p, dpi=150)
    print("wrote", p)


if __name__ == "__main__":
    main()
