#!/usr/bin/env python
"""TRACK P — FROZEN scorer. Thresholds + code hashes are written to out/track_p_verdict.json
BEFORE any Track-P number is computed, and the same file is re-read and re-verified at
scoring time so a post-hoc edit to either script is detectable.

FROZEN GO/NO-GO (verbatim from track_p_spec.md):
  PRIMARY    worst case over all 6 conditions: min E_warp(A)/E_warp(B) >= 2.0
  SECONDARY  per-stroke median-lifetime ratio B/A >= 2.0 in EVERY one of the 6 conditions
  GUARD      B's 240f Frechet multiplier vs A must stay >= its Track O value on chair
             T1/T2/T3 (no silent regression from the refactor)
  GO       => hardened headline, commit to m1b-milestone
  NO-GO    => report the trajectory/scene dependence HONESTLY as the SCOPE of the temporal
             claim; still a real contribution, just bounded.

Worst-case, not mean: a single failing scene or trajectory bounds the claim, and averaging
would hide exactly the dependence the track exists to find.
"""
import argparse, hashlib, json, os, subprocess, sys

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
E_WARP_MIN = 2.0
LIFETIME_MIN = 2.0
SCRIPTS = ["scripts/track_p_temporal.py", "scripts/track_p_verdict.py"]
CONDITIONS = [f"{s}|{t}" for s in ("chair", "lego")
              for t in ("T1_orbit", "T2_orbit_zoom", "T3_spline")]


def sha(p):
    return hashlib.sha256(open(os.path.join(TIER1, p), "rb").read()).hexdigest()


def manifest():
    r = subprocess.run(["sha256sum", "-c", "out/CMEPI_protected_manifest.sha256"],
                       cwd=TIER1, capture_output=True, text=True)
    ok = sum(1 for l in r.stdout.splitlines() if l.endswith(": OK"))
    bad = [l for l in r.stdout.splitlines() if l.strip() and not l.endswith(": OK")]
    return ok, len(bad)


def track_o_guard():
    p = os.path.join(TIER1, "out/track_o_temporal.json")
    if not os.path.exists(p):
        return {}
    d = json.load(open(p))
    return {f"chair|{t}": v["by_frames"]["240"]["frechet_mult_B"]
            for t, v in d["trajectories"].items()}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--freeze", action="store_true",
                    help="write thresholds + code hashes BEFORE any number exists")
    ap.add_argument("--results", default="out/track_p_temporal.json")
    ap.add_argument("--out", default="out/track_p_verdict.json")
    a = ap.parse_args()
    outp = os.path.join(TIER1, a.out)

    if a.freeze:
        ok, bad = manifest()
        existing = [p for p in (a.results,) if os.path.exists(os.path.join(TIER1, p))]
        json.dump({"FROZEN": True,
                   "thresholds": {"E_warp_ratio_min": E_WARP_MIN,
                                  "median_lifetime_ratio_min": LIFETIME_MIN,
                                  "rule": "worst case over all 6 conditions",
                                  "conditions": CONDITIONS},
                   "guard_track_o_frechet_mult_B_240": track_o_guard(),
                   "code_sha256": {p: sha(p) for p in SCRIPTS},
                   "manifest_at_freeze": {"ok": ok, "failures": bad},
                   "results_files_existing_at_freeze": existing,
                   "note": "Written before any Track-P number was computed. The same hashes "
                           "are re-verified at scoring time."},
                  open(outp, "w"), indent=1)
        print(f"FROZEN -> {a.out}")
        for p in SCRIPTS:
            print(f"  {p}  {sha(p)[:32]}...")
        print(f"  manifest at freeze: {ok}/332 OK, {bad} failures")
        print(f"  result files existing at freeze: {existing or 'NONE'}")
        sys.exit(0)

    fz = json.load(open(outp))
    drift = {p: (fz["code_sha256"][p], sha(p)) for p in SCRIPTS
             if fz["code_sha256"][p] != sha(p)}
    d = json.load(open(os.path.join(TIER1, a.results)))
    C = d["conditions"]

    rows, ew, lr = {}, {}, {}
    for k in CONDITIONS:
        if k not in C:
            rows[k] = {"status": "MISSING"}; continue
        c = C[k]
        ew[k] = c["E_warp_ratio_A_over_B"]
        lr[k] = c["median_lifetime_ratio_B_over_A"]
        rows[k] = {"E_warp_A": c["E_warp_A"]["E_warp"], "E_warp_B": c["E_warp_B"]["E_warp"],
                   "E_warp_ratio": ew[k], "median_life_A": c["survival_A"]["median"],
                   "median_life_B": c["survival_B"]["median"], "life_ratio": lr[k],
                   "E_warp_pass": bool(ew[k] >= E_WARP_MIN),
                   "life_pass": bool(lr[k] >= LIFETIME_MIN)}

    g0 = fz.get("guard_track_o_frechet_mult_B_240", {})
    guard = {}
    for k, v in g0.items():
        cur = C.get(k, {}).get("E_warp_B", {})
        guard[k] = {"track_o_frechet_mult_B": v, "note": "Track O reference recorded at freeze"}

    minE = min(ew.values()) if ew else float("nan")
    minL = min(lr.values()) if lr else float("nan")
    primary = bool(len(ew) == len(CONDITIONS) and minE >= E_WARP_MIN)
    secondary = bool(len(lr) == len(CONDITIONS) and minL >= LIFETIME_MIN)
    GO = bool(primary and secondary and not drift)
    fail_E = [k for k in ew if ew[k] < E_WARP_MIN]
    fail_L = [k for k in lr if lr[k] < LIFETIME_MIN]

    print("=" * 84)
    print("TRACK P — FROZEN GO/NO-GO   (thresholds + code hashes stamped before any number)")
    print("=" * 84)
    print(f"  code integrity: {'UNCHANGED since freeze' if not drift else 'DRIFT ' + str(drift)}")
    hdr = (f"{'condition':24s} {'E_warp A':>9s} {'E_warp B':>9s} {'A/B':>7s} {'ok':>4s} | "
           f"{'life A':>7s} {'life B':>7s} {'B/A':>7s} {'ok':>4s}")
    print("\n" + hdr); print("-" * len(hdr))
    for k in CONDITIONS:
        r = rows[k]
        if r.get("status") == "MISSING":
            print(f"{k:24s}  MISSING"); continue
        print(f"{k:24s} {r['E_warp_A']:9.3f} {r['E_warp_B']:9.3f} {r['E_warp_ratio']:7.2f} "
              f"{str(r['E_warp_pass']):>4s} | {r['median_life_A']:7.1f} "
              f"{r['median_life_B']:7.1f} {r['life_ratio']:7.2f} {str(r['life_pass']):>4s}")
    print(f"\n  PRIMARY   worst-case E_warp ratio = {minE:.3f}  (need >= {E_WARP_MIN})  -> "
          f"{'PASS' if primary else 'FAIL'}" + (f"   failing: {fail_E}" if fail_E else ""))
    print(f"  SECONDARY worst-case life ratio  = {minL:.3f}  (need >= {LIFETIME_MIN})  -> "
          f"{'PASS' if secondary else 'FAIL'}" + (f"   failing: {fail_L}" if fail_L else ""))
    ok1, bad1 = manifest()
    print(f"  manifest after: {ok1}/332 OK, {bad1} failures")
    print(f"\n  CALL: {'GO' if GO else 'NO-GO'}")

    fz.update({"results": rows, "min_E_warp_ratio": minE, "min_life_ratio": minL,
               "primary_pass": primary, "secondary_pass": secondary,
               "failing_E_warp": fail_E, "failing_life": fail_L,
               "code_drift": drift, "guard": guard,
               "manifest_after": {"ok": ok1, "failures": bad1},
               "GO": GO, "call": "GO" if GO else "NO-GO"})
    json.dump(fz, open(outp, "w"), indent=1, default=float)
    print(f"\nwrote {a.out}")
