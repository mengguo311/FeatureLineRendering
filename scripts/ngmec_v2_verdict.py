#!/usr/bin/env python
"""NG-MEC-v2 — FROZEN GO/NO-GO. Written and committed BEFORE any final number was read.

Thresholds are verbatim from tier1/ngmec_v2_spec.md and are NOT to be moved after the
numbers are seen:

  GO:
    min(P_chair@1.5, P_lego@1.5) >= 0.85
    AND min(R_chair@1.5, R_lego@1.5) >= 0.65
    AND temporal speedup >= 7.0x preserved

  EARLY ABORT (reported during tuning, not after):
    if consensus culling drops recall below R = 0.60 before P@1.5 reaches 0.80 on either
    scene, halt and report WHICH CUE is over-penalising.

Operating point: for each scene the frontier is swept and the reported point is the one
that MAXIMISES P@1.5 subject to R@1.5 >= 0.65 (the gate's recall floor). If no frontier
point reaches R >= 0.65 the scene cannot satisfy the gate at any operating point, and that
is reported as such rather than by quietly relaxing the recall floor.
"""
import argparse, json, os

P_MIN, R_MIN, SPEEDUP_MIN = 0.85, 0.65, 7.0
ABORT_R, ABORT_P = 0.60, 0.80


def op_point(frontier, r_min=R_MIN, key_p="P1.5", key_r="R1.5"):
    """Max precision subject to recall >= r_min. None if the floor is unreachable."""
    ok = [p for p in frontier if p.get(key_r) is not None and p[key_r] >= r_min]
    if not ok:
        return None
    return max(ok, key=lambda p: p[key_p])


def best_p_anywhere(frontier, key_p="P1.5", key_r="R1.5"):
    return max(frontier, key=lambda p: p[key_p]) if frontier else None


def max_r_anywhere(frontier, key_r="R1.5"):
    return max(frontier, key=lambda p: p[key_r]) if frontier else None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--chair", required=True, help="m1b json for the chair NG-MEC-v2 run")
    ap.add_argument("--lego", required=True, help="m1b json for the lego NG-MEC-v2 run")
    ap.add_argument("--temporal", default="out/m1b_stroke_temporal_table_tc_tcteed.json")
    ap.add_argument("--weights", default="out/ngmec_v2_weights.json")
    ap.add_argument("--out", default="out/ngmec_v2_verdict.json")
    a = ap.parse_args()

    res, rows = {}, {}
    for scene, path in (("chair", a.chair), ("lego", a.lego)):
        d = json.load(open(path))
        fr = d.get("frontier") or []
        op = op_point(fr)
        bp, mr = best_p_anywhere(fr), max_r_anywhere(fr)
        rows[scene] = {
            "source": path, "n_frontier": len(fr),
            "operating_point": op,
            "best_P_anywhere": {"P": bp["P1.5"], "R": bp["R1.5"]} if bp else None,
            "max_R_anywhere": {"P": mr["P1.5"], "R": mr["R1.5"]} if mr else None,
            "recall_floor_reachable": op is not None,
        }
        res[scene] = op

    # ---- temporal: the protected win must not regress below 7.0x -------------------
    td = json.load(open(a.temporal))
    bf = td["scenes"]["chair"]["by_frames"]
    ratios = {k: bf[k]["B"]["P_pop"] / bf[k]["A"]["P_pop"] for k in sorted(bf, key=int)}
    speedup = max(ratios.values())
    speedup_min_obs = min(ratios.values())

    P = {s: (res[s]["P1.5"] if res[s] else None) for s in res}
    R = {s: (res[s]["R1.5"] if res[s] else None) for s in res}
    have = all(v is not None for v in P.values())

    gate_p = have and min(P.values()) >= P_MIN
    gate_r = have and min(R.values()) >= R_MIN
    gate_t = speedup >= SPEEDUP_MIN
    GO = bool(gate_p and gate_r and gate_t)

    # ---- early-abort diagnostic ----------------------------------------------------
    abort = {}
    for s in rows:
        mr = rows[s]["max_R_anywhere"]; bp = rows[s]["best_P_anywhere"]
        abort[s] = bool(mr and bp and mr["R"] < ABORT_R and bp["P"] < ABORT_P)

    print("=" * 74)
    print("NG-MEC-v2 — FROZEN GO/NO-GO")
    print("=" * 74)
    print(f"{'scene':7s} {'P@1.5':>8s} {'R@1.5':>8s}  {'bestP anywhere':>22s}  {'maxR anywhere':>20s}")
    for s in ("chair", "lego"):
        r = rows[s]
        op = r["operating_point"]
        ps = f"{op['P1.5']:8.4f}" if op else "     n/a"
        rs = f"{op['R1.5']:8.4f}" if op else "     n/a"
        bp, mr = r["best_P_anywhere"], r["max_R_anywhere"]
        bps = f"P={bp['P']:.4f} @R={bp['R']:.4f}" if bp else "n/a"
        mrs = f"R={mr['R']:.4f} @P={mr['P']:.4f}" if mr else "n/a"
        print(f"{s:7s} {ps} {rs}  {bps:>22s}  {mrs:>20s}")
        if not r["recall_floor_reachable"]:
            print(f"        ^ no frontier point reaches R >= {R_MIN}")
    print()
    print(f"  gate P >= {P_MIN}      -> {'PASS' if gate_p else 'FAIL'}")
    print(f"  gate R >= {R_MIN}      -> {'PASS' if gate_r else 'FAIL'}")
    print(f"  temporal >= {SPEEDUP_MIN}x   -> {'PASS' if gate_t else 'FAIL'}  "
          f"(P_pop ratios {min(ratios.values()):.2f}-{max(ratios.values()):.2f}x)")
    print(f"\n  VERDICT: {'GO' if GO else 'NO-GO'}")
    for s, v in abort.items():
        if v:
            print(f"  EARLY-ABORT condition met on {s}: max R {rows[s]['max_R_anywhere']['R']:.4f}"
                  f" < {ABORT_R} while best P {rows[s]['best_P_anywhere']['P']:.4f} < {ABORT_P}")

    w = json.load(open(a.weights)) if os.path.exists(a.weights) else None
    json.dump({"thresholds": {"P_min": P_MIN, "R_min": R_MIN,
                              "speedup_min": SPEEDUP_MIN,
                              "abort_R": ABORT_R, "abort_P": ABORT_P},
               "scenes": rows, "P": P, "R": R,
               "temporal_ratios": ratios, "temporal_speedup_max": speedup,
               "temporal_speedup_min": speedup_min_obs,
               "gate_P": gate_p, "gate_R": gate_r, "gate_temporal": gate_t,
               "GO": GO, "early_abort": abort, "weights": w},
              open(a.out, "w"), indent=1, default=float)
    print(f"\nwrote {a.out}")
