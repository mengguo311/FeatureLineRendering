"""tier1/scripts/diag2dgs_plot.py — DIAG-2DGS figure (ANALYSIS ONLY, no mesh, no GPU)."""
import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
OUT = os.path.join(TIER1, "out")


def main():
    split = sys.argv[1] if len(sys.argv) > 1 else "test"
    z = np.load(os.path.join(OUT, f"diag2dgs_lego_{split}.npz"))
    j = json.load(open(os.path.join(OUT, f"diag2dgs_lego_{split}.json")))
    crease, decal = z["crease"], z["decal"]
    panels = [("surfel3d_rho4_xi0.25_nmin5",
               "(1) 2DGS surfel dihedral\nTHE GATED ARM", 90),
              ("mesh3d_rho4_xi0.25_nmin5",
               "(4) GT-MESH dihedral\nsame estimator, perfect geometry", 90),
              ("ribbon2dgs", "(2) 2DGS rendered-normal ribbon\nthe chair-winning estimator", 90),
              ("spreadmesh_rho4_xi0.25_nmin5",
               "GT-MESH normal dispersion\nno side split, no tangent", 60)]
    fig, ax = plt.subplots(1, 4, figsize=(17.5, 4.3))
    for k, (key, title, xmax) in enumerate(panels):
        if key not in z.files:
            ax[k].set_visible(False)
            continue
        th = z[key]
        ok = z["ok_" + key] if "ok_" + key in z.files else np.isfinite(th)
        c, d = crease & ok, decal & ok
        bins = np.linspace(0, xmax, 61)
        ax[k].hist(th[c], bins=bins, density=True, alpha=0.55, color="#1f77b4",
                   label=f"TrueCrease  n={int(c.sum())}")
        ax[k].hist(th[d], bins=bins, density=True, alpha=0.55, color="#d62728",
                   label=f"DecalDistractor  n={int(d.sum())}")
        ax[k].axvline(np.median(th[c]), color="#1f77b4", lw=2, ls="--")
        ax[k].axvline(np.median(th[d]), color="#d62728", lw=2, ls="--")
        r = j["signals"].get(f"{key}|own", {})
        a = r.get("AUC", float("nan"))
        ax[k].set_title(f"{title}\nAUC {a:.3f}   medians {np.median(th[c]):.1f} vs "
                        f"{np.median(th[d]):.1f} deg", fontsize=9.5)
        ax[k].set_xlabel("degrees")
        ax[k].legend(fontsize=8)
        ax[k].grid(alpha=0.25)
    ax[0].set_ylabel("density")
    fig.suptitle("DIAG-2DGS (lego, held-out TEST) — the gate needs AUC >= 0.80 and a "
                 ">= +25 deg median gap.  Every arm is BELOW chance, and so is perfect "
                 "geometry.", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    p = os.path.join(OUT, f"diag2dgs_lego_{split}.png")
    fig.savefig(p, dpi=150)
    print("wrote", p)


if __name__ == "__main__":
    main()
