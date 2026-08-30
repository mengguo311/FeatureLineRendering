"""STEP 1c — DOES THE 2DGS GATE ADD ANYTHING THAT A SMALLER f WOULD NOT?

*** EVAL-ONLY. Uses tune_lib.Harness (mesh) to score candidate seed sets on VAL. ***

THE TRAP THIS EXISTS TO AVOID
    A gate that removes seeds ALWAYS trades recall for precision. The M1a OVERALL score
    already offers that trade for free: just lower the keep-fraction f. out/m1b_stroke_
    temporal_table.md records the previous time this was not checked -- a rescue signal
    "worked" until it turned out to land exactly ON the ungated precision/recall frontier,
    i.e. it bought nothing the score itself did not already buy.

    So the honest question is NOT "does gating raise precision" (it must). It is:
        at MATCHED seed count / matched recall, does the gated set beat the point the M1a
        score reaches on its own?
    Only a gated point strictly ABOVE the f-frontier is evidence of ORTHOGONAL information
    -- which is the entire premise of the vanilla x 2DGS hybrid.

Scored with the literal M1a gate protocol (tune_lib.Harness.evaluate: precision = frac of
visible projected seeds within 2.5px of a visible GT crease pixel, recall = frac of visible
GT crease pixels within 3.0px of a seed), on the VAL views only.
"""
import json
import os
import sys

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))

from src import common, render, view_split, hybrid_gate

OUT, CACHE = os.path.join(TIER1, "out"), os.path.join(TIER1, "cache")
SYN = os.path.join(TIER1, "scripts/explore/syn")


def main():
    scene = sys.argv[1] if len(sys.argv) > 1 else "chair"
    z = np.load(os.path.join(CACHE, f"hybrid_step1_{scene}.npz"))
    seed_idx = z["seed_idx"]
    VIS = z["vis"]                                              # [V,S]
    keys = [k for k in z.files if k.startswith("pass_")]

    g = common.load_gaussians(scene)
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    X = g["mu"][keep_g]
    s = np.load(os.path.join(SYN, f"finalscore_overall_{scene}.npy"))
    order = np.argsort(-s, kind="stable")

    from tune_lib import Harness                                # EVAL ONLY
    h = Harness(scene, views=tuple(view_split.VAL))
    assert len(h.X) == len(X)

    # ---------------- the ungated M1a f-frontier -------------------------------
    front = []
    for f in (0.50, 0.45, 0.40, 0.35, 0.30, 0.26, 0.22, 0.18, 0.15, 0.12, 0.10,
              0.08, 0.06, 0.04):
        k = np.zeros(len(X), bool)
        k[order[:int(round(f * len(X)))]] = True
        p, r, n = h.evaluate(X, extra_mask=k)
        front.append({"f": f, "P": p, "R": r, "n": n})
        print(f"  [frontier] f={f:<5} P={p:.4f} R={r:.4f} n={n}", flush=True)

    def interp_P_at_R(R):
        """Precision the ungated M1a score reaches at this recall (linear interp)."""
        a = sorted(front, key=lambda x: x["R"])
        rs = [x["R"] for x in a]; ps = [x["P"] for x in a]
        if R <= rs[0] or R >= rs[-1]:
            return float("nan")
        return float(np.interp(R, rs, ps))

    # ---------------- gated points at f = 0.30 --------------------------------
    base = np.zeros(len(X), bool)
    base[seed_idx] = True
    pb, rb, nb = h.evaluate(X, extra_mask=base)
    print(f"\n  [base] f=0.30 ungated  P={pb:.4f} R={rb:.4f} n={nb}\n", flush=True)

    rows = []
    for key in sorted(keys):
        P = z[key]                                              # [V,S]
        name = key[len("pass_"):]
        for vf in (0.01, 0.25, 0.5, 0.75, 1.0):
            keep_s, fr, nv = hybrid_gate.vote_keep(P, VIS, frac=vf)
            m = np.zeros(len(X), bool)
            m[seed_idx[keep_s]] = True
            if m.sum() < 200:
                continue
            p, r, n = h.evaluate(X, extra_mask=m)
            pf = interp_P_at_R(r)
            rows.append({"gate": name, "vote_frac": vf, "n_seeds": int(m.sum()),
                         "P": p, "R": r, "n": n, "P_frontier_at_same_R": pf,
                         "lift": (p - pf) if np.isfinite(pf) else float("nan")})
    rows.sort(key=lambda x: -(x["lift"] if np.isfinite(x["lift"]) else -9))

    print("=" * 108)
    print(f"STEP 1c — gated seed sets vs the ungated M1a f-frontier   ({scene}, VAL views "
          f"{view_split.VAL})")
    print("  LIFT = gated precision MINUS the precision the M1a score alone reaches at the "
          "SAME recall.")
    print("  lift <= 0  =>  the gate lands on/under the frontier and adds NOTHING.")
    print("=" * 108)
    print(f"{'gate':46s} {'vote':>5} {'n_seed':>7} {'P':>7} {'R':>7} {'P_front':>8} "
          f"{'LIFT':>8}")
    for x in rows[:40]:
        print(f"{x['gate']:46s} {x['vote_frac']:>5.2f} {x['n_seeds']:>7d} {x['P']:>7.4f} "
              f"{x['R']:>7.4f} {x['P_frontier_at_same_R']:>8.4f} {x['lift']:>+8.4f}")
    pos = [x for x in rows if np.isfinite(x["lift"]) and x["lift"] > 0]
    print("-" * 108)
    print(f"  gated points strictly ABOVE the frontier: {len(pos)} / {len(rows)}")
    if pos:
        b = pos[0]
        print(f"  best: {b['gate']} vote={b['vote_frac']}  P={b['P']:.4f} R={b['R']:.4f} "
              f"(frontier P={b['P_frontier_at_same_R']:.4f})  LIFT={b['lift']:+.4f}")
    print("=" * 108, flush=True)

    p = os.path.join(OUT, f"hybrid_step1c_frontier_{scene}.json")
    json.dump({"scene": scene, "val_views": list(view_split.VAL), "frontier": front,
               "base": {"f": 0.30, "P": pb, "R": rb, "n": nb}, "rows": rows},
              open(p, "w"), indent=1, default=float)
    print(f"wrote {p}")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.figure(figsize=(7.5, 6))
    a = sorted(front, key=lambda x: x["R"])
    plt.plot([x["R"] for x in a], [x["P"] for x in a], "-k", lw=2,
             label="ungated M1a f-frontier")
    for x in front:
        plt.annotate(f"{x['f']:g}", (x["R"], x["P"]), fontsize=6)
    cols = {"2dgs_chair": "tab:blue", "2dgs_chair_dist": "tab:orange",
            "vanilla": "tab:green", "mesh": "tab:red"}
    seen = set()
    for x in rows:
        arm = next((k for k in cols if x["gate"].startswith(k)), None)
        if arm is None:
            continue
        lab = arm if arm not in seen else None
        seen.add(arm)
        plt.scatter(x["R"], x["P"], s=12, alpha=0.6, c=cols[arm], label=lab)
    plt.scatter([rb], [pb], marker="*", s=220, c="k", zorder=5, label="f=0.30 ungated")
    plt.xlabel("seed recall (VAL)"); plt.ylabel("seed precision (VAL)")
    plt.title(f"{scene}: does the 2DGS gate beat simply lowering f?")
    plt.legend(fontsize=8); plt.grid(alpha=0.3)
    pp = os.path.join(OUT, f"hybrid_step1c_frontier_{scene}.png")
    plt.tight_layout(); plt.savefig(pp, dpi=120)
    print(f"wrote {pp}")


if __name__ == "__main__":
    main()
