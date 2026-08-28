"""ECO — the results table: the ABSOLUTE precision gate, LIFT_P, and dP at matched recall.

*** ANALYSIS ONLY — reads the jsons run_m1b.py already wrote. No mesh, no GPU. ***

THREE MEASUREMENTS, AND WHY ALL THREE ARE NEEDED
  1. THE ABSOLUTE GATE (the number eco_spec.md says now matters): P@1.5 and R@1.5 at each band
     f, and whether P>=0.85 AND R>=0.65 hold simultaneously.
  2. dP AT MATCHED RECALL vs the ECO arm's OWN BASE CARRIER.  This is the PARTIAL criterion:
     does spending consensus buy precision the base detector's keep-fraction dial cannot buy at
     that recall?  The base carrier's own f-frontier is the interpolant, NOT canny's -- the
     question is what CONSENSUS added, with the detector held fixed.
  3. LIFT_P against the PUBLISHED canny f-frontier, both estimators, so the ECO arms are on the
     same axis as every CMEPI/TEED number and "LIFT_P sign preserved" can be checked.

NAMESPACE DISCIPLINE
  ECO arms live under out/m1b_<scene>_ec_*.json, a PRIVATE prefix.  The canny frontier and the
  base carriers are read from the published _tc_ glob but never rewritten, and this script's
  --out defaults to out/eco_table.json, so the committed out/cmepi_table.json and the
  manifest-protected out/teedgen_verdict_*.json are never touched.
"""
import os
import sys
import json
import glob
import argparse

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from teedgen_verdict import analyse, SEG                                # noqa: E402

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
OUT = os.path.join(TIER1, "out")

BASE_OF = {"eco_dex_add_l0p25_K3": "dexined_native_0.7",
           "eco_dex_add_l0p25_K1": "dexined_native_0.7",
           "eco_dex_add_l0p25_K5": "dexined_native_0.7",
           "eco_dex_veto_c0p9_K3": "dexined_native_0.7",
           "eco_dex_vetoq0p2_K3": "dexined_native_0.7",
           "eco_teed_add_l0p25_K3": "teed_native_0.5"}
CHAIR_BASE_ALIAS = {"teed_native_0.5": "teed05"}     # chair's TEED arm is tagged teed05
BAND = {"chair": (0.30, 0.50), "lego": (0.15, 0.50)}


def row_of(d):
    for r in d["rows"]:
        if r["kind"] == "segments" and r["stage"] == SEG:
            return r
    return None


def load(prefix):
    arms = {}
    for p in sorted(glob.glob(os.path.join(OUT, prefix + "*.json"))):
        tag = os.path.basename(p)[len(prefix):-len(".json")]
        if "_f" not in tag:
            continue
        name, f = tag.rsplit("_f", 1)
        try:
            fv = float(f)
        except ValueError:
            continue
        arms.setdefault(name, {})[fv] = json.load(open(p))
    return arms


def interp_P_at_R(front, R):
    a = sorted(front)
    rs, ps = [x[0] for x in a], [x[1] for x in a]
    return float(np.interp(R, rs, ps)) if rs[0] < R < rs[-1] else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", nargs="+", default=["chair", "lego"])
    ap.add_argument("--out", default=os.path.join(OUT, "eco_table.json"))
    args = ap.parse_args()

    doc = {"gate": {"P1.5": 0.85, "R1.5": 0.65}, "band": BAND, "scenes": {}}
    for scene in args.scenes:
        tc = load(f"m1b_{scene}_tc_")
        ec = load(f"m1b_{scene}_ec_")
        if not ec:
            print(f"[eco-table] no ECO arms for {scene} yet")
            continue
        fmin, fmax = BAND[scene]

        # the PUBLISHED canny frontier + the base carriers, merged with the ECO arms so
        # teedgen_verdict.analyse can score every arm against the same interpolant
        merged = {"canny": tc["canny"]}
        for nm in set(BASE_OF.values()):
            key = CHAIR_BASE_ALIAS.get(nm, nm) if scene == "chair" else nm
            if key in tc:
                merged[key] = tc[key]
        merged.update(ec)
        front, res = analyse(merged, "segments", SEG, fmin, fmax)

        FS = sorted({f for v in res.values() for f in
                     {r["f"] for r in v["rows"]}}, reverse=True)
        print("=" * 128)
        print(f"ECO — {scene.upper()}, held-out TEST, segments stage '{SEG.strip()}', tau=1.5. "
              f"Band f in [{fmin},{fmax}]. Canny frontier {len(front)} pts.")
        print("=" * 128)

        # ---- 1. THE ABSOLUTE GATE
        print(f"\n--- 1. ABSOLUTE GATE  (need P@1.5 >= 0.85 AND R@1.5 >= 0.65 at the SAME f) ---")
        print(f"{'arm':>26} " + "".join(f"{'f=%.2f' % f:>17}" for f in FS) + "  gate?")
        gate_hits = {}
        for nm in sorted(res):
            cells, hit = "", False
            m = {r["f"]: (r["P"], r["R"]) for r in res[nm]["rows"]}
            for f in FS:
                if f in m:
                    P, R = m[f]
                    cells += f"{P:7.4f}/{R:<9.4f}"
                    if fmin - 1e-9 <= f <= fmax + 1e-9 and P >= 0.85 and R >= 0.65:
                        hit = True
                else:
                    cells += " " * 17
            gate_hits[nm] = hit
            print(f"{nm:>26} {cells}  {'PASS' if hit else 'fail'}")

        # ---- 2. dP at matched recall vs the arm's OWN base carrier
        print(f"\n--- 2. dP AT MATCHED RECALL vs the arm's OWN base carrier "
              f"(the PARTIAL criterion) ---")
        print(f"{'arm':>26} {'base':>22} " + "".join(f"{'f=%.2f' % f:>10}" for f in FS)
              + f"{'best':>10}{'n>0':>8}")
        dp_out = {}
        for nm in sorted(ec):
            b = BASE_OF.get(nm)
            bkey = CHAIR_BASE_ALIAS.get(b, b) if scene == "chair" else b
            if bkey not in res:
                print(f"{nm:>26} {str(bkey):>22}   base arm absent")
                continue
            bfront = [(r["R"], r["P"]) for r in res[bkey]["rows"]]
            m = {r["f"]: (r["P"], r["R"]) for r in res[nm]["rows"]}
            cells, vals = "", []
            for f in FS:
                if f not in m:
                    cells += " " * 10
                    continue
                P, R = m[f]
                d = P - interp_P_at_R(bfront, R)
                cells += (f"{d:+10.4f}" if np.isfinite(d) else f"{'—':>10}")
                if np.isfinite(d) and fmin - 1e-9 <= f <= fmax + 1e-9:
                    vals.append((d, f))
            best = max(vals)[0] if vals else float("nan")
            npos = sum(1 for d, _ in vals if d > 0)
            print(f"{nm:>26} {str(bkey):>22} {cells}{best:+10.4f}{npos:>5}/{len(vals):<3}")
            dp_out[nm] = {"base": bkey, "best_dP_in_band": best,
                          "n_pos": npos, "n_band": len(vals),
                          "dP_by_f": {f"{f:.2f}": d for d, f in vals}}

        # ---- 3. LIFT_P vs the published canny frontier
        print(f"\n--- 3. LIFT_P vs the PUBLISHED canny f-frontier (interp / envelope) ---")
        print(f"{'arm':>26} {'best interp':>13} {'n>0':>7} {'best env':>11} {'n>0':>7}")
        for nm in sorted(res):
            band = [r for r in res[nm]["rows"]
                    if fmin - 1e-9 <= r["f"] <= fmax + 1e-9]
            fi = [r["LIFT_P"] for r in band if np.isfinite(r["LIFT_P"])]
            fe = [r["LIFT_P_lb"] for r in band if np.isfinite(r["LIFT_P_lb"])]
            print(f"{nm:>26} {(max(fi) if fi else float('nan')):+13.4f} "
                  f"{sum(1 for x in fi if x > 0):>4}/{len(fi):<2} "
                  f"{(max(fe) if fe else float('nan')):+11.4f} "
                  f"{sum(1 for x in fe if x > 0):>4}/{len(fe):<2}")

        doc["scenes"][scene] = {
            "frontier": front, "gate_hits": gate_hits, "dP_vs_base": dp_out,
            "arms": {nm: {"rows": res[nm]["rows"],
                          "band_best_LIFT_P": max(
                              [r["LIFT_P"] for r in res[nm]["rows"]
                               if fmin - 1e-9 <= r["f"] <= fmax + 1e-9
                               and np.isfinite(r["LIFT_P"])] or [float("nan")]),
                          "band_best_LIFT_P_lb": max(
                              [r["LIFT_P_lb"] for r in res[nm]["rows"]
                               if fmin - 1e-9 <= r["f"] <= fmax + 1e-9
                               and np.isfinite(r["LIFT_P_lb"])] or [float("nan")])}
                     for nm in res},
        }
        print()

    json.dump(doc, open(args.out, "w"), indent=2, default=float)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
