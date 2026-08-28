#!/usr/bin/env python
"""LEGO-GEN — does the chair frontier-outward LIFT_P generalize to lego? FROZEN scorer.

Committed BEFORE any lego lift number is read. Thresholds and metric are fixed here and are
not to be adjusted once the answer is known.

DECOUPLED FROM THE ABSOLUTE GATE. This does NOT chase P>=0.85 & R>=0.65 on lego; the lego
ceiling autopsy already showed 36.6% of visible GT creases have no frozen-3DGS carrier within
tau, so that gate is unreachable in principle. The question here is only whether the RANKABLE
SEED LIFT (learned prior vs re-tuned Canny) reproduces on a hard-surface scene.

METRIC — the EXACT chair XMEP primary metric, unchanged, no lego-specific renormalisation:
    segments / pull+prune[tuned+len]
    INTERPOLATED canny P at the same recall (not the Pareto envelope)
    rows beyond canny's reach EXCLUDED
    canny frontier restricted to f in {0.15,0.22,0.30,0.35,0.40,0.45,0.50}
teedgen_verdict.analyse() is imported and called, so the lego and chair numbers cannot drift.
Deliberately NO recall-band renormalisation: re-banding to lego's favourable slice would be
cherry-picking.

FROZEN GO / NO-GO (verbatim from tier1/lego_gen_spec.md):
    GO       mean LIFT_P over f in [0.22, 0.50] >= +0.030
             AND dP > 0 (TEED beats Canny at matched f) on >= 80% of held-out TEST views
    NO-GO    mean LIFT_P < +0.010  OR  view-consistency < 80%
    PARTIAL  anything between, reported straight

MEAN, not best: the spec asks for the mean over the f-band, so a single lucky f cannot carry
the verdict. Best LIFT_P (with its f, P, R) is reported for context only.

PER-VIEW dP is computed at the MATCHED f for which both a Canny and a TEED linelet dump exist
on disk (f = 0.40, out/linelets_lego_tc{canny,teed}040_test.npz), using
run_m1b.eval_segments(..., per_view=True) — the harness's own scorer, not a reimplementation.

Mesh is EVAL-ONLY throughout (tune_lib.Harness -> mesh_oracle). Held-out TEST views only.
Nothing is tuned on TEST.
"""
import argparse, json, os, sys

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, os.path.join(TIER1, "scripts"))
import teedgen_verdict as TV
from xmep_verdict import load_arms

FMIN, FMAX = 0.22, 0.50
KIND, STAGE = "segments", TV.SEG
PUB_CANNY_F = [0.15, 0.22, 0.30, 0.35, 0.40, 0.45, 0.50]
GO_MEAN, NOGO_MEAN = 0.030, 0.010
VIEW_CONSISTENCY = 0.80
MATCHED_F = 0.40
DUMP_CANNY = "out/linelets_lego_tccanny040_test.npz"
DUMP_TEED = "out/linelets_lego_tcteed040_test.npz"


def band_rows(res, arm):
    return [r for r in res[arm]["rows"]
            if FMIN - 1e-9 <= r["f"] <= FMAX + 1e-9
            and np.isfinite(r["LIFT_P"]) and not r["beyond_canny_Rmax"]]


def per_view_dP(scene="lego", tau=1.5):
    """Per-view segment precision for the matched-f Canny and TEED dumps. Mesh EVAL-ONLY."""
    import run_m1b as RM
    import tune_lib
    from src import view_split
    # run_m1b.py:313 builds the harness as Harness(scene, views=tuple(eval_views));
    # the frozen TEST split is the eval split here, so pass it explicitly.
    h = tune_lib.Harness(scene, views=tuple(view_split.TEST))   # mesh_oracle lives here
    out = {}
    for name, path in (("canny", DUMP_CANNY), ("teed", DUMP_TEED)):
        z = np.load(os.path.join(TIER1, path), allow_pickle=True)
        keep = z["keep"].astype(bool) if "keep" in z.files else None
        r = RM.eval_segments(h, z["p"], z["t"], z["l"], keep=keep,
                             taus=(tau,), per_view=True)
        out[name] = {"P": list(r[tau][0]), "R": list(r[tau][1]), "n_px": list(r["n_px"])}
    views = list(h.views)
    dP = np.array(out["teed"]["P"]) - np.array(out["canny"]["P"])
    dR = np.array(out["teed"]["R"]) - np.array(out["canny"]["R"])
    return {"views": [int(v) for v in views],
            "canny_P": out["canny"]["P"], "teed_P": out["teed"]["P"],
            "canny_R": out["canny"]["R"], "teed_R": out["teed"]["R"],
            "dP": dP.tolist(), "dR": dR.tolist(),
            "dP_median": float(np.median(dP)), "dP_mean": float(dP.mean()),
            "frac_dP_positive": float((dP > 0).mean()),
            "dR_median": float(np.median(dR)),
            "matched_f": MATCHED_F, "tau": tau, "n_views": len(views)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="m1b_lego_tc_")
    ap.add_argument("--arm", default="teed_native_0.5")
    ap.add_argument("--skip_per_view", action="store_true")
    ap.add_argument("--out", default="out/lego_gen_verdict.json")
    a = ap.parse_args()

    full = load_arms(a.prefix)
    pub = dict(full)
    pub["canny"] = {f: d for f, d in full["canny"].items() if f in PUB_CANNY_F}
    _, res = TV.analyse(pub, KIND, STAGE, FMIN, FMAX)
    rows = band_rows(res, a.arm)
    if not rows:
        sys.exit(f"no in-band, in-reach rows for {a.arm}")
    lifts = [r["LIFT_P"] for r in rows]
    mean_lift = float(np.mean(lifts))
    best = max(rows, key=lambda r: r["LIFT_P"])

    pv = None if a.skip_per_view else per_view_dP()
    cons = pv["frac_dP_positive"] if pv else float("nan")

    go = bool(mean_lift >= GO_MEAN and pv is not None and cons >= VIEW_CONSISTENCY)
    nogo = bool(mean_lift < NOGO_MEAN or (pv is not None and cons < VIEW_CONSISTENCY))
    call = "GO" if go else ("NO-GO" if nogo else "PARTIAL")

    print("=" * 76)
    print("LEGO-GEN — FROZEN GO/NO-GO (scorer committed before any lego number was read)")
    print("=" * 76)
    print(f"  arm {a.arm}   metric {KIND}/{STAGE} (chair XMEP primary, unchanged)")
    print(f"  f-band [{FMIN}, {FMAX}]  ->  {len(rows)} in-reach rows: "
          + ", ".join(f"f{r['f']:.2f}:{r['LIFT_P']:+.4f}" for r in rows))
    print(f"\n  MEAN LIFT_P = {mean_lift:+.4f}   (GO >= {GO_MEAN:+.3f}, "
          f"NO-GO < {NOGO_MEAN:+.3f})")
    print(f"  best LIFT_P = {best['LIFT_P']:+.4f} at f={best['f']:.2f}  "
          f"(segP {best['P']:.4f}, segR {best['R']:.4f})")
    if pv:
        print(f"\n  per-view dP at matched f={MATCHED_F} (n={pv['n_views']} TEST views):")
        print(f"    median dP {pv['dP_median']:+.4f}   mean {pv['dP_mean']:+.4f}   "
              f"frac(dP>0) = {pv['frac_dP_positive']:.3f}  "
              f"(need >= {VIEW_CONSISTENCY:.2f})")
        print("    " + "  ".join(f"v{v}:{d:+.3f}" for v, d in zip(pv["views"], pv["dP"])))
    print(f"\n  CALL: {call}")

    json.dump({"thresholds": {"GO_mean_LIFT_P": GO_MEAN, "NOGO_mean_LIFT_P": NOGO_MEAN,
                              "view_consistency": VIEW_CONSISTENCY,
                              "fband": [FMIN, FMAX], "kind": KIND, "stage": STAGE,
                              "canny_frontier_f": PUB_CANNY_F, "matched_f": MATCHED_F},
               "arm": a.arm, "prefix": a.prefix,
               "band_rows": rows, "mean_LIFT_P": mean_lift,
               "best": {"LIFT_P": best["LIFT_P"], "f": best["f"],
                        "P": best["P"], "R": best["R"],
                        "matched_f_dP": best["matched_f_dP"],
                        "matched_f_dR": best["matched_f_dR"]},
               "per_view": pv, "view_consistency": cons,
               "call": call, "GO": go},
              open(a.out, "w"), indent=1, default=float)
    print(f"\nwrote {a.out}")
