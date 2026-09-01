"""PARETO-2 verdict — frozen gate vs the accumulated baselines (pareto2_flowbaseline_spec.md).

GATE (frozen): GO iff OURS pop>2px advantage >= 3x at EVERY shared matched-P-and-density
point vs the best (accumulated or memoryless) baseline, on BOTH scenes (both trajectories).
NO-GO iff advantage < 2x at ANY shared point, OR an accumulated point matches our precision
at matched density (formalized: an alpha>0 point that no OURS point dominates on (P, density)
AND that itself dominates at least one OURS point). Else GRAY (bounded claim).
"""
import os
import json

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.expanduser("~/3dgs_line/tier1/out")
CONDS = [("chair", "T1_orbit"), ("chair", "T3_spline"),
         ("lego", "T1_orbit"), ("lego", "T3_spline")]
COL = {"ours": "#1a7f37", "canny": "#e69f00", "canny_acc": "#c0392b",
       "pidinet": "#7fb3d5", "pidinet_acc": "#2456a4"}


def gate_cond(d):
    ours = [r for r in d["rows"] if r["kind"] == "ours"]
    base = [r for r in d["rows"] if r["kind"] != "ours"]
    table, worst = [], np.inf
    prec_breach = []
    for b in base:
        dom = [o for o in ours if o["P15_traj"] >= b["P15_traj"]
               and o["px_per_frame"] >= b["px_per_frame"]]
        if not dom:
            table.append({"baseline": b["name"], "shared": False, "P": b["P15_traj"],
                          "px": b["px_per_frame"], "pop2": b.get("pop_gt2px")})
            if b.get("alpha", 0) and any(b["P15_traj"] >= o["P15_traj"]
                                         and b["px_per_frame"] >= o["px_per_frame"]
                                         for o in ours):
                prec_breach.append(b["name"])
            continue
        adv = min(b.get("pop_gt2px", np.inf) / max(o.get("pop_gt2px", 1e-9), 1e-9)
                  for o in dom)
        worst = min(worst, adv)
        table.append({"baseline": b["name"], "shared": True, "P": b["P15_traj"],
                      "px": b["px_per_frame"], "pop2": b.get("pop_gt2px"),
                      "alpha": b.get("alpha", 0.0), "adv_pop2": float(adv)})
    return table, (None if not np.isfinite(worst) else float(worst)), prec_breach


def plot_cond(scene, tname, d):
    fig, ax = plt.subplots(figsize=(8.2, 6))
    for kind in COL:
        rr = sorted([r for r in d["rows"] if r["kind"] == kind],
                    key=lambda r: r["P15_traj"])
        if not rr:
            continue
        x = [r["P15_traj"] for r in rr]
        y = [max(r.get("pop_gt2px", np.nan), 1e-4) for r in rr]
        sz = [22 + r["px_per_frame"] / 150 for r in rr]
        ax.scatter(x, y, s=sz, c=COL[kind], label=kind, zorder=3,
                   edgecolors="white", linewidths=0.4)
        if kind == "ours":
            ax.plot(x, y, "-", c=COL[kind], lw=1.0, alpha=0.5)
    ax.set_yscale("log")
    ax.set_xlabel("precision P@1.5 (trajectory frames, GT mesh, interior)")
    ax.set_ylabel("pooled pop-rate P(warped px > 2 px from next-frame line)")
    ax.set_title(f"{scene} · {tname} — ours vs ORACLE-FLOW accumulated 2D baselines\n"
                 f"(marker size = px/frame; _acc = EMA over exact rigid flow, "
                 f"occlusion-aware)")
    ax.grid(alpha=0.25, which="both")
    ax.legend(fontsize=8)
    p = os.path.join(OUT, f"pareto2_{scene}_{tname}.png")
    plt.tight_layout()
    plt.savefig(p, dpi=140)
    plt.close()
    print(f"wrote {p}")


def main():
    res, worst_all, any_lt2, breaches = {}, np.inf, [], []
    for scene, tname in CONDS:
        d = json.load(open(os.path.join(OUT, f"pareto2_{scene}_{tname}.json")))
        plot_cond(scene, tname, d)
        table, worst, breach = gate_cond(d)
        res[f"{scene}_{tname}"] = {"table": table, "worst_adv_pop2": worst,
                                   "precision_breach_acc": breach}
        print(f"\n===== {scene} {tname} =====")
        for t in table:
            if t["shared"]:
                flag = " <2x!" if t["adv_pop2"] < 2 else (" <3x" if t["adv_pop2"] < 3 else "")
                print(f"  {t['baseline']:26s} P {t['P']:.3f} px {t['px']:7.0f} "
                      f"pop2 {t['pop2']:.4f}  adv {t['adv_pop2']:6.2f}x{flag}")
        ns = sum(1 for t in table if t["shared"])
        print(f"  shared {ns}/{len(table)}  worst {worst}  acc-precision-breach {breach}")
        if worst is not None:
            worst_all = min(worst_all, worst)
            if worst < 2:
                any_lt2.append(f"{scene}_{tname}")
        breaches += [f"{scene}_{tname}:{b}" for b in breach]
    verdict = ("NO-GO" if (any_lt2 or breaches)
               else ("GO" if worst_all >= 3 else "GRAY"))
    res["worst_overall"] = None if not np.isfinite(worst_all) else float(worst_all)
    res["conditions_lt2x"] = any_lt2
    res["precision_breaches"] = breaches
    res["verdict"] = verdict
    json.dump(res, open(os.path.join(OUT, "pareto2_verdict.json"), "w"), indent=2,
              default=float)
    print(f"\nFROZEN GATE: worst shared pop>2px advantage {res['worst_overall']}, "
          f"<2x conditions {any_lt2}, precision breaches {breaches}")
    print(f"VERDICT: {verdict}")
    print("wrote out/pareto2_verdict.json")


if __name__ == "__main__":
    main()
