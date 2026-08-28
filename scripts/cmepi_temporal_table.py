"""CMEPI — the temporal no-regress table: do the new detectors' strokes hold up in motion?

*** ANALYSIS ONLY — reads the jsons m1b_stroke_temporal.py already wrote. ***

Same trajectory (TEST views 5->15, look-at-corrected orbit), same frame counts, same
forward-warp metric, same BASELINE (naive image-space Canny re-traced independently every
frame) for every row.  The published control rows are read from the PUBLISHED tables, not
recomputed.

WHY THIS TABLE DECIDES SOMETHING.  On lego the un-blurred permissive Canny WON the static
f-frontier and LOST temporal coherence (11.61x -> 9.67x at 240 frames); TEED was preferred
because it improved both.  So "detector X reproduces the static lift" is only half a result
until X's flicker ratio is on the same page as X's LIFT_P.
"""
import os
import json
import argparse

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
OUT = os.path.join(TIER1, "out")

ROWS = {
    "chair": [
        ("canny  f=0.30  [published control]", "m1b_stroke_temporal_table_tc_tccanny.json"),
        ("TEED   f=0.30  [published control]", "m1b_stroke_temporal_table_tc_tcteed.json"),
        ("PiDiNet@0.9 f=0.30  *CMEPI", "m1b_stroke_temporal_table_cmepi_pidinet.json"),
        ("DexiNed@0.7 f=0.30  *CMEPI", "m1b_stroke_temporal_table_cmepi_dexined.json"),
    ],
    "lego": [
        ("canny  f=0.40  [published control]", "m1b_stroke_temporal_table_tcL_tccanny040.json"),
        ("TEED   f=0.40  [published control]", "m1b_stroke_temporal_table_tcL_tcteed040.json"),
        ("cannysharplow f=0.40 [published]", "m1b_stroke_temporal_table_tcL_tcsharplow040.json"),
        ("PiDiNet@0.9 f=0.40  *CMEPI", "m1b_stroke_temporal_table_cmepiL_pidinet.json"),
        ("DexiNed@0.7 f=0.40  *CMEPI", "m1b_stroke_temporal_table_cmepiL_dexined.json"),
    ],
}
FRAMES = ["30", "60", "120", "240"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(OUT, "cmepi_temporal_table.json"))
    args = ap.parse_args()
    doc = {"frames": FRAMES, "scenes": {}}
    for scene, rows in ROWS.items():
        print("=" * 118)
        print(f"CMEPI — TEMPORAL NO-REGRESS, {scene.upper()}.  P_pop ratio = BASELINE/OURS "
              f"(higher = our strokes flicker less).  TEST views 5->15 orbit.")
        print("=" * 118)
        print("{:>36} {:>34} {:>34} {:>10}".format(
            "arm", "P_pop OURS  (30/60/120/240)", "P_pop ratio (30/60/120/240)",
            "strokes/f"))
        out_rows = {}
        for label, fn in rows:
            p = os.path.join(OUT, fn)
            if not os.path.exists(p):
                print(f"{label:>36}   MISSING {fn}")
                continue
            d = json.load(open(p))
            per = d.get("scenes", d).get(scene)
            if per is None:
                print(f"{label:>36}   (no {scene} in {fn})")
                continue
            bf = per["by_frames"]
            if not all(f in bf for f in FRAMES):
                print(f"{label:>36}   incomplete frames in {fn}: {sorted(bf)}")
                continue
            ours = [bf[f]["A"]["P_pop"] for f in FRAMES]
            base = [bf[f]["B"]["P_pop"] for f in FRAMES]
            ratio = [b / a if a > 0 else float("inf") for a, b in zip(ours, base)]
            fr_o = [bf[f]["A"]["frechet_median"] for f in FRAMES]
            fr_b = [bf[f]["B"]["frechet_median"] for f in FRAMES]
            fr_r = [b / a if a > 0 else float("inf") for a, b in zip(fr_o, fr_b)]
            spf = bf[FRAMES[-1]]["A"].get("n_strokes_mean", bf[FRAMES[-1]]["A"].get("strokes_per_frame"))
            print("{:>36} {:>34} {:>34} {:>10}".format(
                label,
                " ".join(f"{v:.3f}" for v in ours),
                " ".join(f"{v:.2f}x" for v in ratio),
                (f"{spf:.0f}" if isinstance(spf, (int, float)) else "-")))
            out_rows[label] = {"source_json": fn, "P_pop_ours": ours, "P_pop_base": base,
                               "P_pop_ratio": ratio, "frechet_med_ours": fr_o,
                               "frechet_med_base": fr_b, "frechet_med_ratio": fr_r,
                               "strokes_per_frame": spf}
        # Frechet block
        print("\n{:>36} {:>34} {:>34}".format(
            "arm", "Frechet med OURS (30/60/120/240)", "Frechet ratio (30/60/120/240)"))
        for label, r in out_rows.items():
            print("{:>36} {:>34} {:>34}".format(
                label,
                " ".join(f"{v:.3f}" for v in r["frechet_med_ours"]),
                " ".join(f"{v:.2f}x" for v in r["frechet_med_ratio"])))
        doc["scenes"][scene] = out_rows
        print()
    json.dump(doc, open(args.out, "w"), indent=2)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
