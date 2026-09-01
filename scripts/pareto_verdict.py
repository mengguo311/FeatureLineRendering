"""Pareto verdict — frontier plots + matched-P/matched-density gate (pareto_spec.md)."""
import os
import json

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.expanduser("~/3dgs_line/tier1/out")
GATE_MULT = 3.0
COL = {"ours": "#1a7f37", "canny": "#c0392b", "pidinet": "#2456a4"}


def load(scene):
    return json.load(open(os.path.join(OUT, f"pareto_{scene}.json")))


def gate(scene, d):
    """A baseline point is SHARED iff some OURS point matches-or-beats it on BOTH control
    axes (P@1.5 and px/frame density). For each shared point the CONSERVATIVE advantage is
    the MINIMUM E-ratio over all dominating OURS points, on the more conservative of the
    two pooled statistics (mean, and median where defined)."""
    ours = [r for r in d["rows"] if r["kind"] == "ours"]
    base = [r for r in d["rows"] if r["kind"] != "ours"]
    table, worst = [], np.inf
    for b in base:
        dom = [o for o in ours
               if o["P15_macro"] >= b["P15_macro"] and o["px_per_frame"] >= b["px_per_frame"]]
        if not dom:
            table.append({"baseline": b["name"], "shared": False,
                          "P": b["P15_macro"], "px": b["px_per_frame"],
                          "E_mean": b["E_pool_mean"], "note": "no OURS point dominates"})
            continue
        ratios = []
        for o in dom:
            rm = b["E_pool_mean"] / max(o["E_pool_mean"], 1e-9)
            rmed = (b["E_pool_median"] / max(o["E_pool_median"], 1e-9)
                    if o["E_pool_median"] > 0 else np.inf)
            rfl = b["flicker"] / max(o["flicker"], 1e-9)
            ratios.append({"ours": o["name"], "adv_mean": rm, "adv_median": rmed,
                           "adv_flicker": rfl,
                           "adv_conservative": min(rm, rmed, rfl)})
        best = min(ratios, key=lambda r: r["adv_conservative"])
        worst = min(worst, best["adv_conservative"])
        table.append({"baseline": b["name"], "shared": True,
                      "P": b["P15_macro"], "px": b["px_per_frame"],
                      "E_mean": b["E_pool_mean"],
                      "n_dominating": len(dom), "worst_pair": best})
    n_shared = sum(1 for t in table if t["shared"])
    verdict = ("PASS" if (n_shared and worst >= GATE_MULT)
               else ("NO-SHARED-POINTS" if not n_shared else "FAIL"))
    return {"scene": scene, "table": table, "n_shared": n_shared,
            "worst_conservative_advantage": None if not n_shared else float(worst),
            "verdict": verdict}


def plot(scene, d):
    fig, axs = plt.subplots(1, 2, figsize=(13, 5.4))
    for ax, ykey, ylab in ((axs[0], "E_pool_mean", "pooled E_warp (mean, px, cap 20)"),
                           (axs[1], "flicker", "pixel flicker (1px-tol XOR/union)")):
        for kind in ("ours", "canny", "pidinet"):
            rr = [r for r in d["rows"] if r["kind"] == kind]
            rr.sort(key=lambda r: r["P15_macro"])
            x = [r["P15_macro"] for r in rr]
            y = [r[ykey] for r in rr]
            sz = [24 + r["px_per_frame"] / 150 for r in rr]
            ax.plot(x, y, "-", c=COL[kind], lw=1.2, alpha=0.6)
            ax.scatter(x, y, s=sz, c=COL[kind], label=kind.upper(), zorder=3,
                       edgecolors="white", linewidths=0.5)
            for r in rr:
                ax.annotate(str(r["param"]), (r["P15_macro"], r[ykey]), fontsize=6,
                            xytext=(3, 3), textcoords="offset points", c=COL[kind])
        ax.set_yscale("log")
        ax.set_xlabel("precision P@1.5 (held-out TEST, interior)")
        ax.set_ylabel(ylab)
        ax.grid(alpha=0.25, which="both")
        ax.legend()
    axs[0].set_title(f"{scene} — coherence vs precision (marker size = px/frame density)\n"
                     f"240-frame T1 orbit, all methods interior-restricted, pooled metric")
    p = os.path.join(OUT, f"pareto_{scene}.png")
    plt.tight_layout()
    plt.savefig(p, dpi=140)
    plt.close()
    print(f"wrote {p}")


def main():
    res = {}
    for scene in ("chair", "lego"):
        d = load(scene)
        plot(scene, d)
        gv = gate(scene, d)
        res[scene] = gv
        print(f"\n===== {scene.upper()} gate =====")
        for t in gv["table"]:
            if not t["shared"]:
                print(f"  {t['baseline']:18s} P {t['P']:.3f} px {t['px']:7.0f}  NOT SHARED "
                      f"({t['note']})")
            else:
                w = t["worst_pair"]
                print(f"  {t['baseline']:18s} P {t['P']:.3f} px {t['px']:7.0f}  "
                      f"E_mean {t['E_mean']:.3f}  vs {w['ours']:12s} adv mean "
                      f"{w['adv_mean']:.2f}x med {w['adv_median']:.2f}x flick "
                      f"{w['adv_flicker']:.2f}x  -> conservative {w['adv_conservative']:.2f}x")
        print(f"  n_shared {gv['n_shared']}  worst conservative advantage "
              f"{gv['worst_conservative_advantage']}  VERDICT {gv['verdict']}")
    overall = "PASS" if all(res[s]["verdict"] == "PASS" for s in res) else \
        ("FAIL" if any(res[s]["verdict"] == "FAIL" for s in res) else "DEGENERATE")
    res["overall"] = overall
    json.dump(res, open(os.path.join(OUT, "pareto_verdict.json"), "w"), indent=2,
              default=float)
    print(f"\nOVERALL (frozen gate, >= {GATE_MULT}x at every shared point, both scenes): "
          f"{overall}")
    print("wrote out/pareto_verdict.json")


if __name__ == "__main__":
    main()
