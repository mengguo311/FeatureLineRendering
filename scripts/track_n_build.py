#!/usr/bin/env python
"""TRACK N — consensus-only cull scores for PiDiNet / DexiNed. MESH-FREE.

Identical to NG-MEC's selected pipeline (tau_n = 0, i.e. NO normal gate, which NG-MEC
refuted), with only the edge proposer swapped. The carrier is not grown; proposals are only
removed, by pushing them below every real score so run_m1b's top-f can never seed them.

CULL-STRENGTH CALIBRATION — a decision made before any Track-N dP was computed.
A fixed c_thr = 0.93 does NOT mean the same thing across detectors, because each detector's
consensus C has its own distribution. Measured survivor fractions at 0.93:
    chair  teed 0.695 | pidinet 0.588 | dexined 0.708
    lego   teed 0.773 | pidinet 0.358 | dexined 0.580
lego/pidinet at 0.358 cannot even support f = 0.40 or 0.50 (top-f needs survivors >= f), so
the literal fixed threshold is both unfair and partly unexecutable: it would compare a 36%
cull against a 77% cull and call them "the same pipeline".

  PRIMARY   matched-strength: c_thr is set per (scene, detector) to the quantile of C that
            reproduces TEED's survivor fraction for that scene. Equal cull strength, full
            f-grid, and calibrated only on the score distribution - no TEST labels involved.
  SECONDARY fixed c_thr = 0.93, the literal NG-MEC value, reported wherever the f-grid is
            supported.
Both are emitted so the choice is auditable.
"""
import argparse, json, os, sys

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
for p in (TIER1, os.path.join(TIER1, "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

SYN = os.path.join(TIER1, "scripts/explore/syn")
OUT = os.path.join(TIER1, "out")
ECO = "K3_t2.5_r0_s16"
TEED_CTHR = 0.93


def teed_surv_frac(scene):
    C = np.load(os.path.join(OUT, f"eco_C_{scene}__teed0.5_{ECO}.npy"))
    return float((C >= TEED_CTHR).mean())


def build(scene, det, mode="matched"):
    base = np.load(os.path.join(SYN, f"finalscore_overall_{scene}__{det}_native_0.5.npy"))
    C = np.load(os.path.join(OUT, f"eco_C_{scene}__{det}0.5_{ECO}.npy"))
    assert len(base) == len(C), (len(base), len(C))
    if mode == "matched":
        target = teed_surv_frac(scene)
        c_thr = float(np.quantile(C, 1.0 - target))
    else:
        c_thr = TEED_CTHR
    surv = C >= c_thr
    S = base.astype(np.float64).copy()
    S[~surv] = base.min() - 1e6
    return S, {"scene": scene, "detector": det, "mode": mode, "c_thr": c_thr,
               "n": int(len(base)), "n_survivors": int(surv.sum()),
               "surv_frac": float(surv.mean()),
               "teed_surv_frac": teed_surv_frac(scene),
               "max_f_supported": float(surv.mean())}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", nargs="+", default=["chair", "lego"])
    ap.add_argument("--dets", nargs="+", default=["pidinet", "dexined"])
    ap.add_argument("--modes", nargs="+", default=["matched", "fixed"])
    a = ap.parse_args()
    alld = {}
    for scene in a.scenes:
        for det in a.dets:
            for mode in a.modes:
                S, d = build(scene, det, mode)
                nm = f"trackn_{det}" + ("" if mode == "matched" else "_fixed")
                np.save(os.path.join(SYN, f"finalscore_overall_{scene}__{nm}.npy"), S)
                alld[f"{scene}|{det}|{mode}"] = d
                print(f"[trackn] {scene:6s} {det:8s} {mode:8s} c_thr={d['c_thr']:.4f}  "
                      f"survivors {d['n_survivors']:6d}/{d['n']} ({d['surv_frac']:.3f})  "
                      f"teed_frac {d['teed_surv_frac']:.3f}  max_f {d['max_f_supported']:.3f}")
    json.dump(alld, open(os.path.join(OUT, "track_n_build.json"), "w"), indent=1, default=float)
    print("\nwrote out/track_n_build.json")
