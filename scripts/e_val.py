#!/usr/bin/env python
"""E-VAL — clean re-selection of the lego operating point on the VAL split.

*** WHY: src/view_split.py freezes VAL as the split "used to pick gate thresholds" and TEST
    as "never used to choose a threshold". A disk-wide query found ZERO lego runs with
    eval_split != 'test'. So the standing (detector, threshold, f) choice was made by
    reading TEST out of 100+ arms. This re-selects on VAL. ***

PARTIAL REMEDIATION, stated up front: all eight arms have ALREADY been observed on TEST.
This converts "selected on TEST" into "selected on VAL, TEST previously seen". It is
materially better than the status quo and weaker than a true single look.

Stage: SPEC mask (z["keep"]) only. The TEED/DexiNed npz do not store keep_tuned, so the
tuned+len stage is not computable without a re-pull. Stated, never mixed.
No re-pull. Mesh EVAL-ONLY (GT crease pixels via the banked VAL oracle cache).

FROZEN selection rule: maximise VAL spec R@1.5 subject to VAL spec P@1.5 >= (canny f=0.30
VAL spec P - 0.02).
FROZEN go/no-go, against the TEST spec-stage recall gap:
  CLEAN  VAL picks a TEED arm AND VAL recall gap over canny f=0.30 >= 0.14
  LEAK   VAL picks canny or DexiNed, OR gap < 0.07
  MIDDLE gap in [0.07, 0.14) -> report shrinkage
Precision gap is reported on its own line regardless of the recall verdict.
"""
import json, os, sys

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
for p in (TIER1, os.path.join(TIER1, "scripts"), os.path.join(TIER1, "scripts/explore"),
          os.path.join(TIER1, "scripts/explore/syn")):
    if p not in sys.path:
        sys.path.insert(0, p)

from src import view_split                       # noqa: E402
from tune_lib import Harness                     # noqa: E402
from run_m1b import eval_segments                # EVAL harness  # noqa: E402

OUT = os.path.join(TIER1, "out")
BASELINE = "canny f=0.30 (shipped)"
# (label, linelets npz stem, banked TEST json stem)
ARMS = [
    (BASELINE,            "linelets_lego_gated_test",                  "m1b_lego_gated_test"),
    ("canny f=0.40",      "linelets_lego_tc_canny_f0.40",              "m1b_lego_tc_canny_f0.40"),
    ("TEED0.5 f=0.30",    "linelets_lego_tc_teed_native_0.5_f0.30",    "m1b_lego_tc_teed_native_0.5_f0.30"),
    ("TEED0.5 f=0.35",    "linelets_lego_tc_teed_native_0.5_f0.35",    "m1b_lego_tc_teed_native_0.5_f0.35"),
    ("TEED0.5 f=0.40",    "linelets_lego_tc_teed_native_0.5_f0.40",    "m1b_lego_tc_teed_native_0.5_f0.40"),
    ("TEED0.5 f=0.50",    "linelets_lego_tc_teed_native_0.5_f0.50",    "m1b_lego_tc_teed_native_0.5_f0.50"),
    ("TEED0.9 f=0.30",    "linelets_lego_tc_teed_native_0.9_f0.30",    "m1b_lego_tc_teed_native_0.9_f0.30"),
    ("DexiNed0.5 f=0.40", "linelets_lego_tc_dexined_native_0.5_f0.40", "m1b_lego_tc_dexined_native_0.5_f0.40"),
]


def test_spec(stem):
    """banked TEST spec-stage segment P/R -- read, never recomputed."""
    d = json.load(open(os.path.join(OUT, stem + ".json")))
    r = [x for x in d["rows"] if x["kind"] == "segments" and "spec" in x["stage"]][0]
    return r["P1.5"], r["R1.5"], d["n_keep"]


def main():
    print(f"VAL views = {view_split.VAL}")
    print(f"TEST views = {view_split.TEST}\n")
    h = Harness("lego", views=view_split.VAL)
    print(f"harness ready: pool={len(h.X)}  VAL views={len(h.views)}\n", flush=True)

    res = {}
    print(f"{'arm':20s} {'keep':>6s} | {'VAL P@1.5':>9s} {'VAL R@1.5':>9s} | "
          f"{'TEST P':>7s} {'TEST R':>7s} | {'dP':>7s} {'dR':>7s}")
    print("-" * 96)
    for label, stem, tstem in ARMS:
        z = np.load(os.path.join(OUT, stem + ".npz"))
        keep = z["keep"].astype(bool)
        out = eval_segments(h, z["p"], z["t"], z["l"], keep=keep, taus=(1.5,))
        vP, vR = out[1.5]
        tP, tR, nk = test_spec(tstem)
        assert int(keep.sum()) == nk, (label, int(keep.sum()), nk)
        res[label] = {"keep": nk, "val_P": vP, "val_R": vR, "test_P": tP, "test_R": tR}
        print(f"{label:20s} {nk:6d} | {vP:9.4f} {vR:9.4f} | {tP:7.4f} {tR:7.4f} | "
              f"{vP-tP:+7.4f} {vR-tR:+7.4f}", flush=True)

    b = res[BASELINE]
    pfloor = b["val_P"] - 0.02
    elig = {k: v for k, v in res.items() if v["val_P"] >= pfloor and k != BASELINE}
    print(f"\nVAL precision floor = baseline VAL P {b['val_P']:.4f} - 0.02 = {pfloor:.4f}")
    print(f"eligible arms: {sorted(elig)}")
    if not elig:
        sel, selv = BASELINE, b
    else:
        sel = max(elig, key=lambda k: elig[k]["val_R"])
        selv = elig[sel]
    val_gapR = selv["val_R"] - b["val_R"]
    val_gapP = selv["val_P"] - b["val_P"]
    test_gapR = selv["test_R"] - b["test_R"]
    test_gapP = selv["test_P"] - b["test_P"]
    is_teed = sel.startswith("TEED")
    if (not is_teed) or val_gapR < 0.07:
        verdict = "LEAK"
    elif val_gapR >= 0.14:
        verdict = "CLEAN"
    else:
        verdict = "MIDDLE"

    print(f"\nVAL-SELECTED ARM: {sel}")
    print(f"  VAL  recall gap over baseline = {val_gapR:+.4f}   (CLEAN >= 0.14, LEAK < 0.07)")
    print(f"  TEST recall gap over baseline = {test_gapR:+.4f}")
    print(f"  shrinkage VAL/TEST recall gap = {val_gapR/test_gapR:.4f}" if test_gapR else "")
    print(f"  PRECISION GAP (separate line, mandatory):")
    print(f"    VAL  precision gap = {val_gapP:+.4f}")
    print(f"    TEST precision gap = {test_gapP:+.4f}")
    print(f"\nVERDICT: {verdict}")

    res_out = {
        "provenance": ("PARTIAL REMEDIATION: all 8 arms were already observed on TEST. "
                       "This is selection-on-VAL with TEST previously seen, not a single look."),
        "stage": "spec mask only (keep); tuned+len not computable without a re-pull",
        "val_views": list(map(int, view_split.VAL)),
        "test_views": list(map(int, view_split.TEST)),
        "baseline": BASELINE, "val_precision_floor": pfloor,
        "selected_arm": sel, "verdict": verdict,
        "val_gap_R": val_gapR, "test_gap_R": test_gapR,
        "shrinkage_R": (val_gapR / test_gapR) if test_gapR else None,
        "val_gap_P": val_gapP, "test_gap_P": test_gapP,
        "arms": res}
    json.dump(res_out, open(os.path.join(OUT, "e_val_lego.json"), "w"), indent=2)
    print("\nwrote out/e_val_lego.json")


if __name__ == "__main__":
    main()
