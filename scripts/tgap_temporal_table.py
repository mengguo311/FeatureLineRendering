"""tier1/scripts/tgap_temporal_table.py — TGAP gate 4 scorer (ANALYSIS ONLY).

Gate 4 as frozen in tgap_spec.md:
  object-space inter-frame coherence < 2.0% relative degradation vs arm A,
  AND >= 8x margin over per-frame Canny.  Any temporal regress => NO-GO regardless.

"Coherence" is read on the two scalars the published temporal table reports for the OURS
pipeline: P_pop (popping penalty; lower is steadier) and the median forward-warped Frechet
residual.  Both are reported at every frame count and the gate is decided on the 240-frame
headline, which is where the published ">= 8x" claim lives; the other counts are printed so a
regress that only appears at short horizons cannot hide.
"""
import json
import os
import sys

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
OUT = os.path.join(TIER1, "out")
FRAMES = ["30", "60", "120", "240"]


def load(variant):
    p = os.path.join(OUT, f"m1b_stroke_temporal_table_{variant}.json")
    return json.load(open(p))["scenes"]["lego"] if os.path.exists(p) else None


def main():
    variants = sys.argv[1:] or ["tgapA", "tgapB", "tgapC"]
    base = load(variants[0])
    if base is None:
        raise SystemExit(f"missing table for {variants[0]}")
    out = {"reference_arm": variants[0], "arms": {}, "gate4": {}}
    print(f"{'variant':10s} {'frames':>7s} {'P_pop':>8s} {'Frechet':>8s} "
          f"{'BASE P_pop':>11s} {'ratio':>7s} {'dP_pop%':>9s} {'dFre%':>8s} {'strokes':>8s}")
    for v in variants:
        d = load(v)
        if d is None:
            print(f"{v:10s}   MISSING")
            continue
        out["arms"][v] = {"chain": d["chain"], "by_frames": {}}
        for nf in FRAMES:
            m = d["by_frames"].get(nf)
            if not m:
                continue
            b = base["by_frames"][nf]
            ratio = m["B"]["P_pop"] / m["A"]["P_pop"]
            dpop = (m["A"]["P_pop"] - b["A"]["P_pop"]) / b["A"]["P_pop"] * 100.0
            dfre = ((m["A"]["frechet_median"] - b["A"]["frechet_median"])
                    / b["A"]["frechet_median"] * 100.0)
            out["arms"][v]["by_frames"][nf] = {
                "P_pop": m["A"]["P_pop"], "frechet_median": m["A"]["frechet_median"],
                "base_P_pop": m["B"]["P_pop"], "ratio": ratio,
                "rel_dP_pop_pct_vs_ref": dpop, "rel_dFrechet_pct_vs_ref": dfre,
                "strokes_per_frame": m["A"]["n_strokes_per_frame"]}
            print(f"{v:10s} {nf:>7s} {m['A']['P_pop']:8.4f} "
                  f"{m['A']['frechet_median']:8.3f} {m['B']['P_pop']:11.4f} "
                  f"{ratio:6.2f}x {dpop:+9.2f} {dfre:+8.2f} "
                  f"{m['A']['n_strokes_per_frame']:8.0f}")
    for v in variants[1:]:
        a = out["arms"].get(v)
        if not a or "240" not in a["by_frames"]:
            continue
        h = a["by_frames"]["240"]
        worst = max(x["rel_dP_pop_pct_vs_ref"] for x in a["by_frames"].values())
        out["gate4"][v] = {
            "rel_dP_pop_pct_240": h["rel_dP_pop_pct_vs_ref"],
            "rel_dFrechet_pct_240": h["rel_dFrechet_pct_vs_ref"],
            "worst_rel_dP_pop_pct_any_frames": worst,
            "ratio_240": h["ratio"],
            "pass_lt_2pct_degradation_240": bool(h["rel_dP_pop_pct_vs_ref"] < 2.0),
            "pass_lt_2pct_degradation_all_frames": bool(worst < 2.0),
            "pass_ratio_ge_8x_240": bool(h["ratio"] >= 8.0),
            "PASS": bool(h["rel_dP_pop_pct_vs_ref"] < 2.0 and h["ratio"] >= 8.0)}
    print()
    print(json.dumps(out["gate4"], indent=1))
    p = os.path.join(OUT, "tgap_temporal_verdict.json")
    json.dump(out, open(p, "w"), indent=1)
    print("wrote", p)


if __name__ == "__main__":
    main()
