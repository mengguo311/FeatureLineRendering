#!/usr/bin/env python
"""E-VAL-CHAIR — is the shipped CHAIR operating point selection-clean, and does its
PRECISION COST survive an independent split?

*** Chair is in the pre-E-VAL state: a disk-wide query found ZERO chair runs with
    eval_split != 'test', so the chair (detector, threshold, f) choice was made by reading
    TEST out of ~30 arms. Unlike lego -- where TEED DOMINATES on both axes -- on chair TEED
    TRADES: it buys recall and PAYS 0.0156 tuned precision against a 0.02 allowance. That
    payment sits INSIDE the between-split spread, so it has never really been tested. ***

GUARDS (orchestrator-imposed, honoured):
  - mesh EVAL-ONLY (GT crease pixels via the banked chair VAL oracle cache).
  - the temporal term does NOT enter the selection rule. Banked TEST-orbit ratios are
    reported ALONGSIDE only.
  - the >=10.345x invariant is checked on every arm that has a measured cell; any dip is
    flagged LOUDLY.
No re-pull. Stage: SPEC mask only (chair npz do not store keep_tuned). Stated, never mixed.

FROZEN selection rule: max VAL spec R@1.5 s.t. VAL spec P@1.5 >= (canny f=0.30 VAL P - 0.02).
FROZEN go/no-go (bars frozen before the run, from the chair TEST spec gap dR=+0.0908):
  CLEAN  selected is a TEED arm AND VAL dR >= 0.0605 AND VAL dP >= -0.02
  LEAK   selected is canny/DexiNed, OR VAL dR < 0.0303, OR VAL dP < -0.02
  MIDDLE otherwise -> report shrinkage, do not act
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
BASE = "canny f=0.30 (shipped)"
BAR = 10.345
CLEAN_R, LEAK_R, PREC_ALLOW = 0.0605, 0.0303, -0.02
# label, linelets stem, TEST json stem, banked TEST-orbit table stem (None = not measured)
ARMS = [
    (BASE,               "linelets_chair_gated_test",                  "m1b_chair_gated_test",                  "m1b_stroke_temporal_table_tc_tccanny"),
    ("TEED0.5 f=0.22",   "linelets_chair_tc_teed05_f0.22",             "m1b_chair_tc_teed05_f0.22",             None),
    ("TEED0.5 f=0.30",   "linelets_chair_tc_teed05_f0.30",             "m1b_chair_tc_teed05_f0.30",             "m1b_stroke_temporal_table_tc_tcteed"),
    ("TEED0.5 f=0.35",   "linelets_chair_tc_teed05_f0.35",             "m1b_chair_tc_teed05_f0.35",             None),
    ("TEED0.5 f=0.40",   "linelets_chair_tc_teed05_f0.40",             "m1b_chair_tc_teed05_f0.40",             None),
    ("TEED0.9 f=0.30",   "linelets_chair_tc_teed09_f0.30",             "m1b_chair_tc_teed09_f0.30",             None),
    ("DexiNed0.5 f=0.30","linelets_chair_tc_dexined_native_0.5_f0.30", "m1b_chair_tc_dexined_native_0.5_f0.30", "m1b_stroke_temporal_table_cdx_dex030"),
]


def test_spec(stem):
    d = json.load(open(os.path.join(OUT, stem + ".json")))
    r = [x for x in d["rows"] if x["kind"] == "segments" and "spec" in x["stage"]][0]
    return r["P1.5"], r["R1.5"], d["n_keep"], d["n_keep_tuned"]


def test_orbit_ratio(stem):
    if stem is None:
        return None
    d = json.load(open(os.path.join(OUT, stem + ".json")))
    k = "scenes" if "scenes" in d else "headline"
    m = d[k]["chair"]["by_frames"]["240"]
    return m["B"]["P_pop"] / m["A"]["P_pop"]


def main():
    print(f"VAL  views = {view_split.VAL}")
    print(f"TEST views = {view_split.TEST}\n")
    h = Harness("chair", views=view_split.VAL)
    print(f"harness ready: pool={len(h.X)}  VAL views={len(h.views)}\n", flush=True)

    res, flags = {}, []
    print(f"{'arm':20s} {'specLin':>7s} {'tunLin':>7s} | {'VAL P':>7s} {'VAL R':>7s} | "
          f"{'TEST P':>7s} {'TEST R':>7s} | {'TESTorb x':>9s}")
    print("-" * 104)
    for label, stem, tstem, orbstem in ARMS:
        z = np.load(os.path.join(OUT, stem + ".npz"))
        keep = z["keep"].astype(bool)
        vP, vR = eval_segments(h, z["p"], z["t"], z["l"], keep=keep, taus=(1.5,))[1.5]
        tP, tR, nk, ntk = test_spec(tstem)
        assert int(keep.sum()) == nk, (label, int(keep.sum()), nk)
        ratio = test_orbit_ratio(orbstem)
        if ratio is not None and ratio < BAR:
            flags.append((label, ratio))
        res[label] = {"spec_keep": nk, "tuned_keep": ntk, "val_P": vP, "val_R": vR,
                      "test_P": tP, "test_R": tR, "test_orbit_ratio": ratio}
        rs = f"{ratio:8.2f}x" if ratio is not None else "not meas."
        print(f"{label:20s} {nk:7d} {ntk:7d} | {vP:7.4f} {vR:7.4f} | {tP:7.4f} {tR:7.4f} | {rs:>9s}",
              flush=True)

    b = res[BASE]
    floor = b["val_P"] - 0.02
    elig = {k: v for k, v in res.items() if k != BASE and v["val_P"] >= floor}
    print(f"\nVAL precision floor = {b['val_P']:.4f} - 0.02 = {floor:.4f}")
    print(f"eligible: {sorted(elig) if elig else 'NONE'}")
    sel = max(elig, key=lambda k: elig[k]["val_R"]) if elig else BASE
    s = res[sel]
    vdR, vdP = s["val_R"] - b["val_R"], s["val_P"] - b["val_P"]
    tdR, tdP = s["test_R"] - b["test_R"], s["test_P"] - b["test_P"]
    is_teed = sel.startswith("TEED")
    if (not is_teed) or vdR < LEAK_R or vdP < PREC_ALLOW:
        verdict = "LEAK"
    elif vdR >= CLEAN_R and vdP >= PREC_ALLOW:
        verdict = "CLEAN"
    else:
        verdict = "MIDDLE"

    print(f"\nVAL-SELECTED ARM: {sel}")
    print(f"  VAL  recall gap = {vdR:+.4f}   (CLEAN >= {CLEAN_R}, LEAK < {LEAK_R})")
    print(f"  TEST recall gap = {tdR:+.4f}   retention = {vdR/tdR:.3f}" if tdR else "")
    print(f"  PRECISION GAP (mandatory separate line, allowance {PREC_ALLOW}):")
    print(f"    VAL  precision gap = {vdP:+.4f}   {'WITHIN' if vdP >= PREC_ALLOW else 'BLOWS'} allowance")
    print(f"    TEST precision gap = {tdP:+.4f}")
    print(f"\nVERDICT: {verdict}")
    print(f"\nTEMPORAL INVARIANT CHECK (>= {BAR}x, reported ALONGSIDE, not in the rule):")
    if flags:
        for lab, r in flags:
            print(f"  *** LOUD FLAG *** {lab} dips to {r:.2f}x, BELOW the {BAR}x invariant")
    else:
        meas = {k: v['test_orbit_ratio'] for k, v in res.items() if v['test_orbit_ratio']}
        print(f"  all measured arms clear the bar: " +
              ", ".join(f"{k} {v:.2f}x" for k, v in meas.items()))

    json.dump({"provenance": ("PARTIAL REMEDIATION: all chair arms were already observed on "
                             "TEST. Selection-on-VAL with TEST previously seen, not a single look."),
               "stage": "spec mask only; tuned+len needs a re-pull",
               "temporal_note": "banked TEST-orbit ratios reported alongside; NOT in the selection rule",
               "selected_arm": sel, "verdict": verdict,
               "val_gap_R": vdR, "test_gap_R": tdR,
               "retention_R": (vdR / tdR) if tdR else None,
               "val_gap_P": vdP, "test_gap_P": tdP,
               "invariant_bar": BAR, "invariant_flags": flags,
               "arms": res}, open(os.path.join(OUT, "e_val_chair.json"), "w"), indent=2)
    print("\nwrote out/e_val_chair.json")


if __name__ == "__main__":
    main()
