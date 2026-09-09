"""tier1/scripts/geoline_step2.py — GEOLINE STEP 2: the 2DGS reconstruction test.

*** EVAL / DIAGNOSTIC.  Reads the GT mesh (tune_lib.Harness -> mesh_oracle) for LABELS ONLY.
    Defines no method, adds no method-path file, modifies nothing committed. ***

WHAT STEP 1 ESTABLISHED (banked, out/GEOLINE_STEP1_RESULTS.md)
    On cadpartA the frozen dihedral gate is NO-GO on every cell.  Every sign flipped versus
    lego (3-D arm AUC 0.4110 -> 0.6336, gap -17.33 -> +16.67 deg), so lego's premise failure
    is scene-specific and does NOT transport -- but the cue never became discriminative, and
    the lift is ENTIRELY on easy negatives: against the off-crease loci that survive the
    consensus prune the vanilla 3-D arm reads AUC 0.3672 (TEST) / 0.3443 (VAL), BELOW chance
    with the gap sign reversed.  Diagnosis: the vanilla 3DGS normal field reads a median
    crease dihedral of 10.20 deg where the GT dihedral is 40.89-90 deg.  The signal is in the
    object and smoothed out of THAT reconstruction.

WHAT THIS STEP TESTS
    Substitute a 2DGS surfel reconstruction and rerun BOTH arms VERBATIM.  The estimators are
    IMPORTED from scripts/diag2dgs.py, never reimplemented, at the frozen lego constants
    rho=4.0, xi=0.25, n_min=5.  The CANDIDATE SET IS UNCHANGED: the same 9,743 vanilla-3DGS
    gated linelets, so the only thing that moves is the geometry used to SCORE them.

  arm 1  surfel3d_2dgs        diag2dgs.surfel3d_dihedral on the 2DGS SURFEL cloud
                              (diag2dgs.load_surfel_normals -> build_rotation(q)[:,:,2])
  arm 2  ribbon2dgs           diag2dgs.ribbon_dihedral on the 2DGS RENDERED NORMAL map
  controls (Step-1 arms, rerun here so every number is same-population comparable)
         surfel3d_vanilla3dgs, ribbon3dgs_vanilla
    Following diag2dgs verbatim, ONE foreground mask -- from the VANILLA render -- is used for
    BOTH ribbon arms, so the two differ only in the normal field (2DGS alpha is not an object
    mask; see the gate2dgs docstring).

PRE-REGISTERED FROZEN GATE (dispatch), committed here BEFORE any number was looked at
    GO iff  AUC(dihedral; TrueCrease vs off-crease PRUNE-SURVIVORS) >= 0.75 on TEST
            AND  |AUC_TEST - AUC_VAL| <= 0.03.
    The dispatch says "both arms" but names one gate.  To remove any post-hoc arm selection,
    the PERMISSIVE reading is fixed in advance: the overall verdict is GO if EITHER 2DGS arm
    clears both legs.  A NO-GO under the permissive rule is therefore unambiguous.
    Supporting, NOT gated: median crease dihedral recovery toward GT 40.89-90 deg (vanilla
    10.20), and AUC vs all-off-crease and vs DexiNed-hi off-crease for Step-1 comparability.
"""
import argparse
import json
import os
import sys

import numpy as np
from scipy.spatial import cKDTree

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))

from src import common, visibility, view_split, render2dgs                   # noqa: E402
import diag2dgs                                                             # noqa: E402
from geoline_step1 import dexined_frac, score                               # noqa: E402

OUT = os.path.join(TIER1, "out")
GATE_AUC = 0.75
GATE_VAL_TOL = 0.03


def run_split(args, split):
    from tune_lib import Harness                                            # EVAL ONLY (mesh)
    views = {"val": view_split.VAL, "test": view_split.TEST}[split]
    h = Harness(args.scene, views=tuple(views))

    lp = os.path.join(OUT, f"linelets_{args.scene}_gated_test.npz")
    z = np.load(lp)
    P, T, L, KEEP = z["p"], z["t"], z["l"], z["keep"]
    print(f"[{args.scene}/{split}] {len(P)} linelets ({int(KEEP.sum())} prune survivors), "
          f"{len(views)} views", flush=True)

    # ---- labels (mesh, EVAL-ONLY) -- identical rule to Step 1 --------------------------
    dists = [[] for _ in range(len(P))]
    nvis = np.zeros(len(P), np.int64)
    for v in views:
        vis, uv, _ = visibility.visible_mask(P, h.cams[v], h.gbufs[v]["depth"])
        _, _, cdt = h.crease[v]
        u = np.clip(np.round(uv[:, 0]).astype(int), 0, cdt.shape[1] - 1)
        w = np.clip(np.round(uv[:, 1]).astype(int), 0, cdt.shape[0] - 1)
        d = cdt[w, u]
        nvis += vis
        for i in np.where(vis)[0]:
            dists[i].append(d[i])
    dmed = np.array([np.median(x) if x else np.inf for x in dists])
    seen = nvis > 0
    dexfrac, _ = dexined_frac(P, h, views, args.dexined)
    crease = seen & (dmed <= 1.5)
    offcrease = seen & (dmed > 3.0)
    offcrease_dexhi = offcrease & (dexfrac >= 0.5)
    print(f"  [labels] seen {int(seen.sum())} | crease {int(crease.sum())} | offcrease "
          f"{int(offcrease.sum())} | dexhi {int(offcrease_dexhi.sum())} | "
          f"offcrease&keep {int((offcrease & KEEP).sum())}", flush=True)

    sig = {}
    # ---- arm 1: 3-D estimator on the 2DGS surfel cloud ---------------------------------
    S, _ = diag2dgs.load_surfel_normals(args.model2dgs)
    print(f"  [2dgs] {len(S['mu'])} surfels, {int(S['keep'].sum())} above opacity 0.1 "
          f"(it={S['meta'].get('iteration')})", flush=True)
    k = S["keep"]
    cloud2 = {"mu": S["mu"][k], "n": S["n"][k], "w": S["opacity"][k]}
    th, sp, ok = diag2dgs.surfel3d_dihedral(P, T, L, cloud2, rho=args.rho, xi=args.xi,
                                            n_min=args.n_min, tree=cKDTree(cloud2["mu"]),
                                            name="surfel3d_2dgs")
    sig["surfel3d_2dgs"] = (th, ok)
    sig["spread2dgs"] = (sp, ok)

    # ---- control: the same estimator on the VANILLA cloud (Step-1 arm) -----------------
    cloudv = {"mu": h.X, "n": h.N, "w": h.opa}
    thv, spv, okv = diag2dgs.surfel3d_dihedral(P, T, L, cloudv, rho=args.rho, xi=args.xi,
                                               n_min=args.n_min, tree=cKDTree(h.X),
                                               name="surfel3d_vanilla3dgs")
    sig["surfel3d_vanilla3dgs"] = (thv, okv)

    # ---- arms 2/3: image-space ribbon on the 2DGS vs the VANILLA normal map ------------
    import torch
    g2, pipe2, meta2 = render2dgs.load_2dgs(args.model2dgs)
    n2, n1, fg = {}, {}, {}
    for v in views:
        gb2 = render2dgs.render_gbuffer_2dgs(g2, pipe2, h.cams[v],
                                             bg_white=meta2.get("white_background", True))
        n2[v] = gb2["normal"].detach().cpu().numpy().astype(np.float32)
        gb1 = h.gbufs[v]
        n1[v] = gb1["normal"].detach().cpu().numpy().astype(np.float32)
        fg[v] = (gb1["alpha"].detach().cpu().numpy() > 0.5)     # ONE mask, vanilla, both arms
        del gb2
    del g2
    torch.cuda.empty_cache()
    thr2, nok2 = diag2dgs.ribbon_dihedral(P, T, h, views, n2, fg)
    sig["ribbon2dgs"] = (thr2, nok2 > 0)
    thr1, nok1 = diag2dgs.ribbon_dihedral(P, T, h, views, n1, fg)
    sig["ribbon3dgs_vanilla"] = (thr1, nok1 > 0)

    rows = {}
    for kk, (s, okm) in sig.items():
        for negname, neg in (("keep_only", offcrease & KEEP),      # THE GATED CLASS
                             ("offcrease", offcrease),
                             ("offcrease_dexhi", offcrease_dexhi)):
            r = score(s, okm, crease, neg, kk)
            # score() stamps the STEP-1 bars (AUC 0.80 AND gap +25 deg). Step 2 is gated
            # ONLY on AUC >= 0.75 vs prune survivors, so rename to prevent misreading.
            r["step1_bar_gate"] = r.pop("gate")
            rows[f"{kk}|{negname}"] = r
    return {"split": split, "views": list(views), "n_linelets": int(len(P)),
            "n_keep": int(KEEP.sum()), "n_surfels_kept": int(k.sum()),
            "labels": {"n_seen": int(seen.sum()), "n_crease": int(crease.sum()),
                       "n_offcrease": int(offcrease.sum()),
                       "n_offcrease_keep": int((offcrease & KEEP).sum()),
                       "n_offcrease_dexhi": int(offcrease_dexhi.sum())},
            "signals": rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="cadpartA")
    ap.add_argument("--model2dgs", default=os.path.join(OUT, "2dgs_cadpartA"))
    ap.add_argument("--rho", type=float, default=4.0)      # lego-frozen
    ap.add_argument("--xi", type=float, default=0.25)      # lego-frozen
    ap.add_argument("--n_min", type=int, default=5)        # lego-frozen
    ap.add_argument("--dexined", default=os.path.join(OUT, "dexined_edges_cadpart"))
    args = ap.parse_args()

    res = {"scene": args.scene, "model2dgs": args.model2dgs,
           "frozen": {"rho": args.rho, "xi": args.xi, "n_min": args.n_min,
                      "source": "lego headline out/diag2dgs_lego_test.json, no retuning"},
           "gate": {"class": "off-crease PRUNE-SURVIVORS", "AUC_min": GATE_AUC,
                    "val_tol": GATE_VAL_TOL,
                    "rule": "permissive: GO if EITHER 2DGS arm clears both legs"},
           "mesh_eval_only": "GT mesh -> LABELS ONLY; no mesh quantity enters any signal.",
           "step1_reference": {"surfel3d_vanilla3dgs|keep_only": {"TEST": 0.3672,
                                                                  "VAL": 0.3443},
                               "ribbon3dgs_vanilla|keep_only": {"TEST": 0.6120,
                                                                "VAL": 0.5779},
                               "vanilla_median_crease_ribbon_deg": 10.20}}
    for sp in ("test", "val"):
        res[sp] = run_split(args, sp)

    verdict = {}
    for arm in ("surfel3d_2dgs", "ribbon2dgs", "surfel3d_vanilla3dgs", "ribbon3dgs_vanilla"):
        t = res["test"]["signals"][f"{arm}|keep_only"]
        v = res["val"]["signals"][f"{arm}|keep_only"]
        okt = t["AUC"] == t["AUC"] and t["AUC"] >= GATE_AUC
        okv = (t["AUC"] == t["AUC"] and v["AUC"] == v["AUC"]
               and abs(t["AUC"] - v["AUC"]) <= GATE_VAL_TOL)
        verdict[arm] = {"AUC_test": t["AUC"], "AUC_val": v["AUC"],
                        "n_neg_test": t["n_neg"], "n_neg_val": v["n_neg"],
                        "leg_auc": bool(okt), "leg_val_agree": bool(okv),
                        "gate": "GO" if (okt and okv) else "NO-GO"}
    res["verdict_per_arm"] = verdict
    res["VERDICT"] = ("GO" if any(verdict[a]["gate"] == "GO"
                                  for a in ("surfel3d_2dgs", "ribbon2dgs")) else "NO-GO")

    p = os.path.join(OUT, f"geoline_step2_{args.scene}.json")
    json.dump(res, open(p, "w"), indent=1)
    print(f"\n  FROZEN GATE: AUC vs off-crease PRUNE-SURVIVORS >= {GATE_AUC} on TEST, "
          f"VAL within {GATE_VAL_TOL}")
    for a, r in verdict.items():
        print(f"    {a:24s} TEST {r['AUC_test']:.4f}  VAL {r['AUC_val']:.4f}  "
              f"(n_neg {r['n_neg_test']}/{r['n_neg_val']})  {r['gate']}")
    print(f"\n  === STEP 2 VERDICT: {res['VERDICT']} ===")
    print(f"  -> {p}", flush=True)


if __name__ == "__main__":
    main()
