#!/usr/bin/env python
"""NG-MEC-v2 — weight tuning. CHAIR ONLY, NON-TEST SPLIT.

SPLIT NOTE (deviation from the spec's wording, stated rather than hidden). The spec says
"tune weights on chair TRAIN views only". scripts/run_m1b.py's --eval_split accepts only
{test, val, legacy} - there is no train-eval mode, because P/R needs the mesh oracle and the
harness only scores VAL/TEST. Tuning therefore runs on chair VAL. The invariant that matters
- NEVER tune on TEST - is preserved, and VAL is this repo's established selection split
(eco_score.py: "Every knob is chosen on CHAIR VAL only, then transferred to lego UNCHANGED").
The pull itself still consumes TRAIN views only (--pull_split train).

Weights are transferred to lego UNCHANGED and TEST is read once, at the end, by
scripts/ngmec_v2_verdict.py (frozen at commit 076a6aa).
"""
import argparse, json, os, subprocess, sys

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
SYN = os.path.join(TIER1, "scripts/explore/syn")
sys.path.insert(0, os.path.join(TIER1, "scripts"))
from ngmec_v2_combine import write as write_score, wtag          # noqa: E402
from ngmec_v2_verdict import op_point, best_p_anywhere, max_r_anywhere   # noqa: E402

BASE_ARGS = ["--f", "0.4", "--edge", "sharp", "--gate", "--gate_theta", "20.0",
             "--gate_tau", "0.015", "--gate_dilate", "2", "--pull_split", "train",
             "--views", "100", "--steps", "100", "--no_viz"]


def run(scene, score_path, split, tag):
    cmd = ([sys.executable, os.path.join(TIER1, "scripts/run_m1b.py"),
            "--scene", scene, "--score", score_path, "--eval_split", split,
            "--tag", tag] + BASE_ARGS)
    r = subprocess.run(cmd, cwd=TIER1, capture_output=True, text=True,
                       env={**os.environ, "CUDA_VISIBLE_DEVICES": "1",
                            "MESH_ORACLE_MAX_ELEMS": "2000000",
                            "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"})
    p = os.path.join(TIER1, "out", f"m1b_{scene}{tag}.json")
    if not os.path.exists(p):
        return None, r.stdout[-2500:] + "\n" + r.stderr[-2500:]
    return json.load(open(p)), None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="chair")
    ap.add_argument("--split", default="val")
    ap.add_argument("--grid", default="0,0.25,0.5,1.0")
    ap.add_argument("--out", default="out/ngmec_v2_sweep_chair_val.json")
    a = ap.parse_args()
    grid = [float(x) for x in a.grid.split(",")]

    rows = []
    print(f"NG-MEC-v2 weight sweep — scene={a.scene} split={a.split} "
          f"(w_teed fixed at 1.0)\n")
    hdr = (f"{'w_2dgs':>7s} {'w_epi':>7s} | {'P@R>=.65':>9s} {'R':>7s} | "
           f"{'bestP':>7s} {'@R':>7s} | {'maxR':>7s} {'@P':>7s}")
    print(hdr); print("-" * len(hdr))
    for wg in grid:
        for we in grid:
            sp, _, _ = write_score(a.scene, 1.0, wg, we)
            tag = f"_ngmecv2_{wtag(wg, we)}_{a.split}"
            d, err = run(a.scene, sp, a.split, tag)
            if d is None:
                print(f"{wg:7g} {we:7g} |  RUN FAILED"); print(err[:1200]); continue
            fr = d["frontier"]
            op, bp, mr = op_point(fr), best_p_anywhere(fr), max_r_anywhere(fr)
            rows.append({"w_2dgs": wg, "w_epi": we, "score": os.path.basename(sp),
                         "json": f"out/m1b_{a.scene}{tag}.json",
                         "op": op, "bestP": {"P": bp["P1.5"], "R": bp["R1.5"]},
                         "maxR": {"P": mr["P1.5"], "R": mr["R1.5"]},
                         "frontier": fr})
            ops = f"{op['P1.5']:9.4f} {op['R1.5']:7.4f}" if op else f"{'n/a':>9s} {'n/a':>7s}"
            print(f"{wg:7g} {we:7g} | {ops} | {bp['P1.5']:7.4f} {bp['R1.5']:7.4f} | "
                  f"{mr['R1.5']:7.4f} {mr['P1.5']:7.4f}", flush=True)

    cand = [r for r in rows if r["op"]]
    best = max(cand, key=lambda r: r["op"]["P1.5"]) if cand else \
        (max(rows, key=lambda r: r["bestP"]["P"]) if rows else None)
    sel = {"w_teed": 1.0, "w_2dgs": best["w_2dgs"], "w_epi": best["w_epi"],
           "selected_on": f"{a.scene} {a.split}", "criterion":
           "max P@1.5 subject to R@1.5 >= 0.65; if unreachable, max P anywhere",
           "op": best["op"], "bestP": best["bestP"], "maxR": best["maxR"]} if best else None
    if sel:
        print(f"\nSELECTED on {a.scene} {a.split}: "
              f"w_teed=1.0  w_2dgs={sel['w_2dgs']:g}  w_epi={sel['w_epi']:g}")
        if sel["op"]:
            print(f"  operating point P={sel['op']['P1.5']:.4f} R={sel['op']['R1.5']:.4f}")
        else:
            print(f"  recall floor R>=0.65 UNREACHABLE on {a.split}; "
                  f"best P anywhere {sel['bestP']['P']:.4f} @ R={sel['bestP']['R']:.4f}")
    json.dump({"scene": a.scene, "split": a.split, "grid": grid,
               "base_args": BASE_ARGS, "rows": rows, "selected": sel},
              open(a.out, "w"), indent=1, default=float)
    if sel:
        json.dump(sel, open("out/ngmec_v2_weights.json", "w"), indent=1, default=float)
    print(f"\nwrote {a.out} and out/ngmec_v2_weights.json")
