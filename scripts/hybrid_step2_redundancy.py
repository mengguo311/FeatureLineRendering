"""STEP 2 diagnostic — WHY does a seed gate with real seed-level lift vanish end-to-end?

*** EVAL-ONLY. Reads the baseline run's linelets and the (mesh-free) 2DGS seed gate, and
scores both with tune_lib.Harness on the TEST views. Adds no new method component. ***

STEP 1c measured, on VAL, that the 2DGS gate buys +0.043 seed precision ABOVE what the
M1a score reaches on its own at the same recall -- i.e. the 2DGS channel really does carry
information the vanilla score does not. STEP 2 then measured that the same gate lands ON or
UNDER the ungated f-frontier end-to-end. Both cannot be dismissed; something between the
seed set and the drawn segment absorbs the gain. The candidates are:

  (a) REDUNDANCY WITH THE PRUNE. The multi-view consensus prune already deletes linelets
      that cannot be reconciled across views -- which is close to what a texture edge is.
      Test: how much of the gate's veto set had the prune already vetoed?
  (b) THE PULL RESCUES THE SEED. A fabric seed does not stay on the fabric: the DT pull
      moves it up to delta_max=5px onto the nearest gated-Canny valley, which may be a real
      crease. A seed the gate would delete can therefore end up drawing a CORRECT segment.
      Test: segment precision of the linelets the gate would have deleted.
  (c) THE GATE DELETES GOOD LINE. Test: how much TEST recall the vetoed set carries.

The three are separated by scoring the IDENTICAL baseline linelets split by the gate's
verdict, so no re-pull, no re-prune, no confound.
"""
import json
import os
import sys

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
sys.path.insert(0, os.path.join(TIER1, "scripts/explore/syn"))

from src import common, render, view_split, hybrid_gate

OUT, CACHE = os.path.join(TIER1, "out"), os.path.join(TIER1, "cache")
SYN = os.path.join(TIER1, "scripts/explore/syn")


def main():
    scene = "chair"
    model = os.path.join(OUT, "2dgs_chair")
    lin = np.load(os.path.join(OUT, f"linelets_{scene}_base_test.npz"))
    p, t, l, keep = lin["p"], lin["t"], lin["l"], lin["keep"]
    seed_idx = lin["seed_idx"]
    print(f"[redundancy] baseline linelets {len(p)}, prune keeps {int(keep.sum())}")

    g = common.load_gaussians(scene)
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    X = g["mu"][keep_g]
    cams, rgb_paths = common.load_cameras(scene)
    views = list(view_split.TRAIN)
    from src import dt_pull
    depthmin, _ = dt_pull.build_geom_cache(scene, g, keep_g, cams, views)
    gate_pass, info = hybrid_gate.build_seed_gate(
        scene, model, X[seed_idx], cams, views, depthmin,
        signal="gradn", tau_q=90.0, r=0, vote_frac=0.75)
    print(f"[redundancy] gate keeps {int(gate_pass.sum())}/{len(gate_pass)}")

    # ---- (a) redundancy with the prune -------------------------------------
    pr_drop = ~keep
    g_drop = ~gate_pass
    inter = int((pr_drop & g_drop).sum())
    print("\n(a) REDUNDANCY WITH THE CONSENSUS PRUNE")
    print(f"    prune drops              {int(pr_drop.sum()):6d} / {len(keep)} "
          f"({100*pr_drop.mean():.1f}%)")
    print(f"    gate  drops              {int(g_drop.sum()):6d} ({100*g_drop.mean():.1f}%)")
    print(f"    both drop                {inter:6d}")
    print(f"    P(prune drops)           {pr_drop.mean():.4f}")
    print(f"    P(prune drops | gate drops) {(inter / max(int(g_drop.sum()), 1)):.4f}"
          "   <- if ~= the row above, the two vetoes are INDEPENDENT, not redundant")

    # ---- relation to the M1a score itself ----------------------------------
    s = np.load(os.path.join(SYN, f"finalscore_overall_{scene}.npy"))[seed_idx]
    q = (np.argsort(np.argsort(s)) + 1) / len(s)
    print("\n(a2) IS THE GATE JUST A PROXY FOR THE M1a SCORE?")
    print(f"    mean M1a score percentile, gate KEEPS {q[gate_pass].mean():.4f}   "
          f"gate DROPS {q[g_drop].mean():.4f}")
    c, f_ = q[gate_pass], q[g_drop]
    a = np.concatenate([c, f_])
    r = np.empty(len(a)); r[np.argsort(a, kind="stable")] = np.arange(1, len(a) + 1)
    auc = (r[:len(c)].sum() - len(c) * (len(c) + 1) / 2.0) / (len(c) * len(f_))
    print(f"    AUC(M1a score predicts gate verdict) = {auc:.4f}   "
          "(0.5 = fully orthogonal, 1.0 = the gate IS the score)")

    # ---- (b)/(c) segment quality of the vetoed vs surviving linelets --------
    from tune_lib import Harness                                  # EVAL ONLY
    import run_m1b as M
    h = Harness(scene, views=tuple(view_split.TEST))
    combos = {
        "baseline  (prune keep)": keep,
        "gate KEEPS (prune keep & gate pass)": keep & gate_pass,
        "gate VETOES (prune keep & gate drop)": keep & g_drop,
    }
    print("\n(b)/(c) TEST-view segment quality of each group "
          "(identical linelets, only the split differs)")
    print(f"{'group':40s} {'n':>7} {'segP@1.5':>9} {'segR@1.5':>9} {'segP@2.5':>9} "
          f"{'px/view':>8}")
    res = {}
    for name, m in combos.items():
        e = M.eval_segments(h, p, t, l, keep=m)
        res[name] = {"n": int(m.sum()), "P1.5": e[1.5][0], "R1.5": e[1.5][1],
                     "P2.5": e[2.5][0], "R2.5": e[2.5][1], "n_px": e["n_px"]}
        print(f"{name:40s} {int(m.sum()):>7} {e[1.5][0]:>9.4f} {e[1.5][1]:>9.4f} "
              f"{e[2.5][0]:>9.4f} {e['n_px']:>8}")

    b = res["baseline  (prune keep)"]
    kp = res["gate KEEPS (prune keep & gate pass)"]
    vt = res["gate VETOES (prune keep & gate drop)"]
    print("\n  READING:")
    print(f"   - the vetoed group draws at precision {vt['P1.5']:.4f} vs the kept group's "
          f"{kp['P1.5']:.4f} (baseline {b['P1.5']:.4f})")
    if vt["P1.5"] >= b["P1.5"] - 0.02:
        print("     => the gate is NOT removing false positives at the SEGMENT level: what "
              "it deletes draws about as well as what it keeps.")
        print("     => hypothesis (b) — the DT pull rescues fabric seeds onto real crease "
              "valleys before they are ever drawn.")
    else:
        print("     => the gate IS removing lower-precision line; the end-to-end null must "
              "come from the recall it costs.")
    print(f"   - it costs {vt['R1.5']:.4f} of the {b['R1.5']:.4f} total TEST recall "
          f"({100 * vt['R1.5'] / max(b['R1.5'], 1e-9):.1f}% of the drawn recall).")

    js = {"scene": scene, "gate": info, "groups": res,
          "prune_drop_rate": float(pr_drop.mean()),
          "prune_drop_given_gate_drop": float(inter / max(int(g_drop.sum()), 1)),
          "auc_m1a_predicts_gate": float(auc),
          "mean_pct_gate_keep": float(q[gate_pass].mean()),
          "mean_pct_gate_drop": float(q[g_drop].mean())}
    pth = os.path.join(OUT, "hybrid_step2_redundancy.json")
    json.dump(js, open(pth, "w"), indent=1, default=float)
    print(f"\nwrote {pth}")


if __name__ == "__main__":
    main()
