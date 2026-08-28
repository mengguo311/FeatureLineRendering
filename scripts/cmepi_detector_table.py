"""CMEPI — the 2D detector-level table: miss-set recovery and precision drop, per detector.

*** ANALYSIS ONLY — reads the jsons recall_trackC_detector.py already wrote. ***

Same script, same tau=2 (TAU_MAIN, the tau every chair go/no-go number was quoted at), same
mesh oracle, same GT crease set (chair 228,079 @30deg / lego 971,793 @30deg -- verified equal
to the published run), same NMS thinning so stroke width is not a confound.  The published
TEED and Canny rows are read out of the ORIGINAL out/trackC_detector_<scene>.json, not
recomputed, so the control is literally the published one.

`rec_miss` = fraction of the M1a-Canny miss-set (visible GT creases the blurred M1a Canny
does NOT cover) that this detector recovers.  The FP triage splits every non-crease edge
pixel into occluding-contour / sub-30deg fold / actual texture hallucination, because a
detector that draws a complete line drawing is otherwise punished for the occluding contours
it gets RIGHT.
"""
import os
import json
import argparse

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
OUT = os.path.join(TIER1, "out")
TAU = "tau2"

# (label, json file, arm key) -- the arm keys are role labels (raw / nms-thinned /
# union-with-canny); which DETECTOR they refer to is set by the json file.
ROWS = {
    "chair": [
        ("canny_m1a (defines the miss-set)", "trackC_detector_chair.json", "canny_m1a"),
        ("TEED nms@0.5  [published control]", "trackC_detector_chair.json", "nms_native_0.5"),
        ("TEED nms@0.9  [published]", "trackC_detector_chair.json", "nms_native_0.9"),
        ("PiDiNet nms@0.9  *CMEPI headline", "trackC_detector_chair_cmepi_pidinet.json", "nms_native_0.9"),
        ("PiDiNet nms@0.5  *CMEPI", "trackC_detector_chair_cmepi_pidinet.json", "nms_native_0.5"),
        ("DexiNed nms@0.7  *CMEPI headline", "trackC_detector_chair_cmepi_dexined.json", "nms_native_0.7"),
        ("DexiNed nms@0.5  *CMEPI", "trackC_detector_chair_cmepi_dexined.json", "nms_native_0.5"),
        ("cannysharplow (0,20,60)  [control]", "trackC_detector_chair.json", "cannysharplow"),
    ],
    "lego": [
        ("canny_m1a (defines the miss-set)", "trackC_detector_lego.json", "canny_m1a"),
        ("TEED nms@0.5  [published control]", "trackC_detector_lego.json", "nms_native_0.5"),
        ("TEED nms@0.9  [published]", "trackC_detector_lego.json", "nms_native_0.9"),
        ("PiDiNet nms@0.9  *CMEPI headline", "trackC_detector_lego_cmepi_pidinet.json", "nms_native_0.9"),
        ("PiDiNet nms@0.5  *CMEPI", "trackC_detector_lego_cmepi_pidinet.json", "nms_native_0.5"),
        ("DexiNed nms@0.7  *CMEPI headline", "trackC_detector_lego_cmepi_dexined.json", "nms_native_0.7"),
        ("DexiNed nms@0.5  *CMEPI", "trackC_detector_lego_cmepi_dexined.json", "nms_native_0.5"),
        ("cannysharplow (0,20,60)  [control]", "trackC_detector_lego.json", "cannysharplow"),
    ],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test", choices=["test", "val"])
    ap.add_argument("--out", default=os.path.join(OUT, "cmepi_detector_table.json"))
    args = ap.parse_args()

    doc = {"split": args.split, "tau": TAU, "scenes": {}}
    cache = {}
    for scene, rows in ROWS.items():
        print("=" * 122)
        print(f"CMEPI — 2D DETECTOR METRIC, {scene.upper()} held-out {args.split.upper()}, "
              f"{TAU} (script TAU_MAIN).  All arms NMS-thinned.")
        print("=" * 122)
        hdr = ("{:>36} {:>7} {:>8} {:>7} {:>8} {:>9} {:>9} {:>8} {:>8} {:>8} {:>8}".format(
            "arm", "R_GT", "dRecall", "P_GT", "Pdrop", "rec_miss", "px/view",
            "FP occ", "FP fold", "FP hall", "P_line"))
        print(hdr)
        base = None
        out_rows = {}
        for label, fn, key in rows:
            p = os.path.join(OUT, fn)
            if p not in cache:
                if not os.path.exists(p):
                    print(f"{label:>36}   MISSING {fn}")
                    continue
                cache[p] = json.load(open(p))
            t = cache[p]["per_split"][args.split]["table"][TAU]["arms"]
            if key not in t:
                print(f"{label:>36}   arm {key!r} absent in {fn}")
                continue
            r = t[key]
            if base is None:
                base = r
            dR = r["R_GT"] - base["R_GT"]
            pd = (base["P_GT"] - r["P_GT"]) / base["P_GT"]
            print("{:>36} {:7.3f} {:>8} {:7.3f} {:>8} {:9.3f} {:9.0f} {:8.3f} {:8.3f} "
                  "{:8.3f} {:8.3f}".format(
                      label, r["R_GT"], ("—" if r is base else f"{dR:+.3f}"), r["P_GT"],
                      ("—" if r is base else f"{pd:+.3f}"), r["rec_miss"],
                      r["px_per_view"], r["fp_frac_occluding"], r["fp_frac_shallow_fold"],
                      r["fp_frac_hallucination"], r["P_line"]))
            out_rows[label] = {
                "source_json": fn, "arm_key": key,
                "R_GT": r["R_GT"], "dRecall": (None if r is base else dR),
                "P_GT": r["P_GT"], "precision_drop_frac": (None if r is base else pd),
                "rec_miss": r["rec_miss"], "px_per_view": r["px_per_view"],
                "fp_frac_occluding": r["fp_frac_occluding"],
                "fp_frac_shallow_fold": r["fp_frac_shallow_fold"],
                "fp_frac_hallucination": r["fp_frac_hallucination"],
                "P_line": r["P_line"],
            }
        doc["scenes"][scene] = {
            "n_gt": cache[os.path.join(OUT, rows[0][1])]["per_split"][args.split]["table"][TAU]["n_gt"],
            "n_canny_miss": cache[os.path.join(OUT, rows[0][1])]["per_split"][args.split]["table"][TAU]["n_miss"],
            "rows": out_rows}
        print(f"   GT crease px {doc['scenes'][scene]['n_gt']}, "
              f"Canny miss-set {doc['scenes'][scene]['n_canny_miss']}\n")

    json.dump(doc, open(args.out, "w"), indent=2)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
