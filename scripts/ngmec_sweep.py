#!/usr/bin/env python
"""NG-MEC — sweep (tau_n, c_thr) on CHAIR VAL only, then transfer to lego UNCHANGED.

Selection discipline identical to eco_score.py / CMEPI: every knob is chosen on chair VAL and
carried to the other scene without re-tuning. TEST is never used to choose anything.
The sweep maximises LIFT_P vs the teed_native_0.5 reference at matched f — i.e. does the cull
buy precision the f dial could not — with the recall change reported beside it so a
precision win bought by recall collapse is visible immediately.
"""
import argparse, json, os, subprocess, sys

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, os.path.join(TIER1, "scripts"))
from ngmec_build import build_score, tag_of                     # noqa: E402
import teedgen_verdict as TV                                    # noqa: E402

SYN = os.path.join(TIER1, "scripts/explore/syn")
BASE = ["--edge", "sharp", "--gate", "--gate_theta", "20.0", "--gate_tau", "0.015",
        "--gate_dilate", "2", "--pull_split", "train", "--views", "100",
        "--steps", "100", "--no_viz"]


def run(scene, score_path, split, tag, f):
    cmd = ([sys.executable, os.path.join(TIER1, "scripts/run_m1b.py"),
            "--scene", scene, "--score", score_path, "--eval_split", split,
            "--tag", tag, "--f", f"{f:g}"] + BASE)
    r = subprocess.run(cmd, cwd=TIER1, capture_output=True, text=True,
                       env={**os.environ, "CUDA_VISIBLE_DEVICES": "1",
                            "MESH_ORACLE_MAX_ELEMS": "2000000",
                            "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"})
    p = os.path.join(TIER1, "out", f"m1b_{scene}{tag}.json")
    if not os.path.exists(p):
        return None, (r.stdout[-1500:] + "\n" + r.stderr[-1500:])
    # confirm the intended score was actually loaded (run_m1b silently falls back otherwise)
    if "[seeds] reusing OVERALL score" not in r.stdout:
        return None, "SILENT FALLBACK: run_m1b did not load the score file"
    return json.load(open(p)), None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="chair")
    ap.add_argument("--split", default="val")
    ap.add_argument("--f", type=float, default=0.40)
    ap.add_argument("--taus", default="0.0,0.20,0.30,0.40")
    ap.add_argument("--cthrs", default="0.0,0.85,0.90,0.93")
    ap.add_argument("--out", default="out/ngmec_sweep_chair_val.json")
    a = ap.parse_args()

    # reference: the un-culled teed_native_0.5 arm at the same f and split
    refp = os.path.join(SYN, f"finalscore_overall_{a.scene}__teed_native_0.5.npy")
    ref, err = run(a.scene, refp, a.split, f"_ngmecref_f{a.f:.2f}", a.f)
    if ref is None:
        sys.exit(f"reference run failed: {err}")
    rp = TV.row(ref, "points", TV.PTS); rs = TV.row(ref, "segments", TV.SEG)
    print(f"REFERENCE teed_native_0.5  f={a.f:.2f} {a.scene} {a.split}: "
          f"pts P {rp['P1.5']:.4f} R {rp['R1.5']:.4f} | seg P {rs['P1.5']:.4f} R {rs['R1.5']:.4f}\n")

    rows = []
    hdr = (f"{'tau_n':>6s} {'c_thr':>6s} {'surv':>6s} | {'pts P':>7s} {'dP':>8s} "
           f"{'pts R':>7s} {'dR':>8s} | {'seg P':>7s} {'dP':>8s} {'seg R':>7s} {'dR':>8s}")
    print(hdr); print("-" * len(hdr))
    for tn in [float(x) for x in a.taus.split(",")]:
        for ct in [float(x) for x in a.cthrs.split(",")]:
            if tn == 0.0 and ct == 0.0:
                continue                                   # that is the reference itself
            S, diag = build_score(a.scene, tn, ct)
            if diag["surv_frac"] < a.f:
                print(f"{tn:6.2f} {ct:6.2f} {diag['surv_frac']:6.3f} | "
                      f"SKIP (survivors < f)"); continue
            nm = f"ngmec_{tag_of(tn, ct)}"
            sp = os.path.join(SYN, f"finalscore_overall_{a.scene}__{nm}.npy")
            np.save(sp, S)
            d, err = run(a.scene, sp, a.split, f"_ngmecsw_{tag_of(tn,ct)}_f{a.f:.2f}", a.f)
            if d is None:
                print(f"{tn:6.2f} {ct:6.2f} {diag['surv_frac']:6.3f} | FAILED: {err[:80]}")
                continue
            p = TV.row(d, "points", TV.PTS); s = TV.row(d, "segments", TV.SEG)
            row = {"tau_n": tn, "c_thr": ct, **diag,
                   "pts_P": p["P1.5"], "pts_R": p["R1.5"],
                   "seg_P": s["P1.5"], "seg_R": s["R1.5"],
                   "d_pts_P": p["P1.5"] - rp["P1.5"], "d_pts_R": p["R1.5"] - rp["R1.5"],
                   "d_seg_P": s["P1.5"] - rs["P1.5"], "d_seg_R": s["R1.5"] - rs["R1.5"]}
            rows.append(row)
            print(f"{tn:6.2f} {ct:6.2f} {diag['surv_frac']:6.3f} | "
                  f"{p['P1.5']:7.4f} {row['d_pts_P']:+8.4f} {p['R1.5']:7.4f} "
                  f"{row['d_pts_R']:+8.4f} | {s['P1.5']:7.4f} {row['d_seg_P']:+8.4f} "
                  f"{s['R1.5']:7.4f} {row['d_seg_R']:+8.4f}", flush=True)

    best = max(rows, key=lambda r: r["d_pts_P"]) if rows else None
    if best:
        print(f"\nSELECTED on {a.scene} {a.split} (max points dP): "
              f"tau_n={best['tau_n']:g} c_thr={best['c_thr']:g}  "
              f"dP {best['d_pts_P']:+.4f}  dR {best['d_pts_R']:+.4f}  "
              f"survivors {best['surv_frac']:.3f}")
    json.dump({"scene": a.scene, "split": a.split, "f": a.f,
               "reference": {"pts_P": rp["P1.5"], "pts_R": rp["R1.5"],
                             "seg_P": rs["P1.5"], "seg_R": rs["R1.5"]},
               "rows": rows, "selected": best}, open(a.out, "w"), indent=1, default=float)
    if best:
        json.dump(best, open("out/ngmec_selected.json", "w"), indent=1, default=float)
    print(f"\nwrote {a.out}")
