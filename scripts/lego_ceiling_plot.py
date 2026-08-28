#!/usr/bin/env python
"""LEGO CEILING AUTOPSY — render Figure A and Figure B from the autopsy json."""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
d = json.load(open(os.path.join(TIER1, "out/lego_ceiling_autopsy.json")))
A, B = d["figure_A"], d["figure_B"]
REF = d["carrier_auc_ref"]

# ------------------------------------------------------------------ FIGURE A
fig, ax = plt.subplots(1, 2, figsize=(12.5, 4.6))
taus = [1.0, 1.5, 2.5]
for i, sc in enumerate(("lego", "chair")):
    v = [A[sc][f"zpeel+interior|tau{t:g}"]["auc_raw"] for t in taus]
    ax[0].plot(taus, v, "o-", lw=2, ms=7, label=f"{sc} (full controls)")
ax[0].axhline(0.75, color="tab:green", ls="--", lw=1.2)
ax[0].axhline(0.55, color="tab:red", ls="--", lw=1.2)
ax[0].axhline(0.50, color="k", ls=":", lw=1)
ax[0].text(2.52, 0.755, "0.75 representation disconnect", fontsize=7.5, color="tab:green")
ax[0].text(2.52, 0.555, "0.55 photometric blur", fontsize=7.5, color="tab:red")
ax[0].text(2.52, 0.505, "chance", fontsize=7.5, color="k")
ax[0].set_xlabel("chamfer tolerance tau (px)"); ax[0].set_ylabel("TEED pixel ROC-AUC")
ax[0].set_title("A1. TEED sees lego creases only weakly\n(held-out TEST, z-peel + interior)")
ax[0].set_ylim(0.45, 0.85); ax[0].legend(fontsize=8); ax[0].grid(alpha=.3)

labels = ["full\ncontrols", "no\nz-peel", "no\ninterior", "NMS-thinned\n(sensitivity)",
          "CARRIER\nAUC"]
lego = [A["lego"]["zpeel+interior|tau1.5"]["auc_raw"], A["lego"]["no_zpeel|tau1.5"]["auc_raw"],
        A["lego"]["no_interior|tau1.5"]["auc_raw"],
        A["lego"]["zpeel+interior|tau1.5"]["auc_nms"], REF["lego"]]
chair = [A["chair"]["zpeel+interior|tau1.5"]["auc_raw"], A["chair"]["no_zpeel|tau1.5"]["auc_raw"],
         A["chair"]["no_interior|tau1.5"]["auc_raw"],
         A["chair"]["zpeel+interior|tau1.5"]["auc_nms"], REF["chair"]]
x = np.arange(len(labels)); w = 0.38
ax[1].bar(x - w/2, lego, w, label="lego", color="tab:red")
ax[1].bar(x + w/2, chair, w, label="chair", color="tab:blue")
for xi, (a_, b_) in enumerate(zip(lego, chair)):
    ax[1].text(xi - w/2, a_ + .01, f"{a_:.3f}", ha="center", fontsize=7)
    ax[1].text(xi + w/2, b_ + .01, f"{b_:.3f}", ha="center", fontsize=7)
ax[1].axhline(0.5, color="k", ls=":", lw=1)
ax[1].set_xticks(x); ax[1].set_xticklabels(labels, fontsize=8)
ax[1].set_ylabel("ROC-AUC"); ax[1].set_ylim(0, 1.0)
ax[1].set_title("A2. Confound controls MOVE the number\n(tau=1.5px; NMS destroys the ROC)")
ax[1].legend(fontsize=8); ax[1].grid(alpha=.3, axis="y")
plt.tight_layout()
pa = os.path.join(TIER1, "out/lego_ceiling_figA.png")
plt.savefig(pa, dpi=130); plt.close()
print(f"wrote {pa}")

# ------------------------------------------------------------------ FIGURE B
fig, ax = plt.subplots(1, 2, figsize=(12.5, 4.6))
u, r, c = B["UNCOVERED"], B["COVERED_and_ranked"], B["COVERED_but_culled"]
ax[0].bar([0], [r], 0.6, color="tab:green", label=f"COVERED & ranked  {r:.3f}")
ax[0].bar([0], [c], 0.6, bottom=[r], color="tab:orange",
          label=f"COVERED but culled  {c:.3f}")
ax[0].bar([0], [u], 0.6, bottom=[r + c], color="tab:red", label=f"UNCOVERED  {u:.3f}")
ax[0].axhline(0.408, color="k", ls="--", lw=1.6)
ax[0].text(0.34, 0.412, "measured R@1.5 = 0.408", fontsize=8)
ax[0].axhline(1 - 0.45, color="tab:purple", ls=":", lw=1.5)
ax[0].text(0.34, 0.558, "UNCOVERED >= 0.45 would start here", fontsize=7.5,
           color="tab:purple")
ax[0].set_xlim(-0.5, 1.25); ax[0].set_xticks([]); ax[0].set_ylim(0, 1.0)
ax[0].set_ylabel("fraction of visible GT crease points")
ax[0].set_title("B1. Recall-ceiling decomposition, lego TEST\n"
                "(tau=1.5px, same space as R@1.5)")
ax[0].legend(fontsize=8, loc="upper right")

pv = B["per_view"]
vs = [p["view"] for p in pv]
ax[1].plot(vs, [p["uncovered"] for p in pv], "o-", color="tab:red", label="UNCOVERED")
ax[1].plot(vs, [p["covered_ranked"] for p in pv], "s-", color="tab:green",
           label="COVERED & ranked")
ax[1].plot(vs, [p["covered_culled"] for p in pv], "^-", color="tab:orange",
           label="COVERED but culled")
ax[1].axhline(0.45, color="tab:purple", ls=":", lw=1.5)
ax[1].text(6, 0.462, "frozen GO threshold 0.45", fontsize=7.5, color="tab:purple")
ax[1].axhline(0.25, color="tab:brown", ls=":", lw=1.5)
ax[1].text(6, 0.262, "loud NO-GO below 0.25", fontsize=7.5, color="tab:brown")
ax[1].set_xlabel("held-out TEST view"); ax[1].set_ylabel("fraction")
ax[1].set_ylim(0, 0.62); ax[1].grid(alpha=.3)
ax[1].set_title("B2. Per-view stability — UNCOVERED never reaches 0.45\n"
                "(max 0.448 at view 65)")
ax[1].legend(fontsize=8)
plt.tight_layout()
pb = os.path.join(TIER1, "out/lego_ceiling_figB.png")
plt.savefig(pb, dpi=130); plt.close()
print(f"wrote {pb}")
