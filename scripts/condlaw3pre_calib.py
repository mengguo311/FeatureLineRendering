#!/usr/bin/env python
"""CONDLAW-3-PRE — two-point calibration, candidate selection, frozen pre-registration.

Anchors are the SOLID CONDLAW numbers (out/CONDLAW_RESULTS.md):
    chair DRR@80 = 0.986   (0.985772, 95% CI [0.9848, 0.9866])
    lego  DRR@80 = 0.512   (0.512323, 95% CI [0.4976, 0.5281])
Interpolant (frozen by condlaw3pre_spec.md item 3):
    D_hat = 0.512 + (rho_cand - rho_lego)/(rho_chair - rho_lego) * (0.986 - 0.512)
Let t = (rho_cand - rho_lego)/(rho_chair - rho_lego) be the normalised position.
"""
import json

D_LEGO, D_CHAIR = 0.512, 0.986
SPAN = D_CHAIR - D_LEGO
PRIMARY_R = "0.04"          # the FROZEN CONDLAW radius: rho=4.0 * linelet half-length
                            # 0.010007 = 0.04003 (scripts/diag2dgs.py mesh arm, R=0.04003)
CANDS = ["materials", "mic", "ship"]


def t_of(rho, rl, rc):
    return (rho - rl) / (rc - rl) if rc != rl else float("nan")


if __name__ == "__main__":
    S = json.load(open("out/condlaw3pre_rhoflat2.json"))["scenes"]
    variants = {}
    for R in ("0.01", "0.02", "0.04"):
        for stat in ("rho_flat", "rho_flat_far"):
            variants[f"{stat}@R={R}"] = {s: S[s]["by_R"][R][stat] for s in S}
    # proxy 2: flat-class AREA per crease locus  (spec item 2)
    variants["proxy2_flatarea_per_creasept@R=0.04"] = {
        s: S[s]["by_R"]["0.04"]["rho_flat"] * S[s]["surface_area"] / S[s]["n_crease_pts"]
        for s in S}

    out = {"anchors": {"chair": D_CHAIR, "lego": D_LEGO,
                       "chair_exact": 0.985772, "lego_exact": 0.512323,
                       "lego_ci_hi": 0.5281, "chair_ci": [0.9848, 0.9866]},
           "primary_variant": f"rho_flat@R={PRIMARY_R}", "variants": {}}

    print("t = normalised position in (lego, chair); interior <=> t near 0.5\n")
    hdr = f"{'variant':42s} " + " ".join(f"{c:>22s}" for c in CANDS)
    print(hdr); print("-" * len(hdr))
    for vn, vals in variants.items():
        rl, rc = vals["lego"], vals["chair"]
        row = {"rho_lego": rl, "rho_chair": rc, "cands": {}}
        cells = []
        for c in CANDS:
            t = t_of(vals[c], rl, rc)
            dh = D_LEGO + t * SPAN
            row["cands"][c] = {"rho": vals[c], "t": t, "D_hat": dh,
                               "interior_dist": abs(t - 0.5),
                               "outside": bool(t < 0.0 or t > 1.0)}
            flag = "*OUT*" if (t < 0 or t > 1) else ""
            cells.append(f"t={t:6.3f} D={dh:5.3f}{flag:>5s}")
        out["variants"][vn] = row
        print(f"{vn:42s} " + " ".join(f"{x:>22s}" for x in cells))

    # ---- selection: most interior under the PRIMARY variant, robustness across all ----
    pv = out["variants"][f"rho_flat@R={PRIMARY_R}"]
    sel = min(CANDS, key=lambda c: pv["cands"][c]["interior_dist"])
    wins = {c: 0 for c in CANDS}
    for vn, row in out["variants"].items():
        w = min(CANDS, key=lambda c: row["cands"][c]["interior_dist"])
        wins[w] += 1
    n_out = {c: sum(1 for r in out["variants"].values() if r["cands"][c]["outside"])
             for c in CANDS}
    dhats = {c: [r["cands"][c]["D_hat"] for r in out["variants"].values()] for c in CANDS}

    print(f"\n'most interior' wins across all {len(out['variants'])} variants: {wins}")
    print(f"variants where the candidate pins OUTSIDE (lego,chair): {n_out}")
    print(f"\nSELECTED (primary variant rho_flat@R={PRIMARY_R}): {sel.upper()}")
    p = pv["cands"][sel]
    lo, hi = p["D_hat"] - 0.08, p["D_hat"] + 0.08
    print(f"  rho_flat(ship) = {p['rho']:.6f}   t = {p['t']:.4f}")
    print(f"  D_hat = {p['D_hat']:.4f}   secondary band [{lo:.3f}, {hi:.3f}]")
    print(f"  D_hat across ALL variants: [{min(dhats[sel]):.3f}, {max(dhats[sel]):.3f}]")

    out["selection"] = {
        "scene": sel, "reason": "most interior under the primary variant and the only "
                                "candidate interior under every variant",
        "interior_wins": wins, "n_variants_outside": n_out,
        "rho": p["rho"], "t": p["t"], "D_hat": p["D_hat"],
        "band": [lo, hi],
        "D_hat_range_all_variants": [min(dhats[sel]), max(dhats[sel])],
        "D_hat_all_variants": {vn: r["cands"][sel]["D_hat"]
                               for vn, r in out["variants"].items()}}
    out["prereg"] = {
        "PRIMARY_monotonicity": f"0.5281 < DRR@80({sel}) < 0.9848  (strictly between the "
                                f"lego upper CI and the chair lower CI), and ordered "
                                f"consistently with rho_flat: lego < {sel} < chair",
        "SECONDARY_affine_band": [lo, hi],
        "HARD_GO_FLOOR": 0.5281,
        "falsified_if": f"DRR@80({sel}) <= 0.5281 or >= 0.9848 (monotonicity broken)",
        "nonlinearity_if": f"monotonicity holds but DRR@80({sel}) outside [{lo:.3f},{hi:.3f}]"}
    json.dump(out, open("out/condlaw3pre_prereg.json", "w"), indent=1, default=float)
    print("\nwrote out/condlaw3pre_prereg.json")
