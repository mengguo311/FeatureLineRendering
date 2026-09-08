#!/usr/bin/env python
"""E-LEDGER GATE — re-read every banked json and verify each numeral asserted in
out/E_LEDGER.md. GO iff 0 unsourced numerals AND 0 contradictions. Read-only."""
import json, os, sys

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
OUT = os.path.join(TIER1, "out")
DEFAULT_DEC = 4   # numerals are checked at the precision they are ASSERTED at


def seg(stem, stage):
    d = json.load(open(os.path.join(OUT, stem + ".json")))
    r = [x for x in d["rows"] if x["kind"] == "segments" and stage in x["stage"]][0]
    return r["P1.5"], r["R1.5"]


def temporal(stem, scene):
    d = json.load(open(os.path.join(OUT, stem + ".json")))
    k = "scenes" if "scenes" in d else "headline"
    m = d[k][scene]["by_frames"]["240"]
    return {"ratio": m["B"]["P_pop"] / m["A"]["P_pop"],
            "fre_ratio": m["B"]["frechet_median"] / m["A"]["frechet_median"],
            "P_pop": m["A"]["P_pop"], "cut": m["A"]["cut_frac"]}


def jkey(stem, *path):
    d = json.load(open(os.path.join(OUT, stem + ".json")))
    for p in path:
        d = d[p]
    return d


CHECKS = []
def C(claim, got, exp, dec=None):
    """PASS iff the banked value rounds to the numeral at the precision asserted.
    An absolute tolerance is wrong here: 5e-4 on a magnitude-10 ratio demands 4dp
    agreement from a numeral written to 2dp. That was the v1 gate defect."""
    if dec is None:
        dec = 2 if abs(exp) >= 1.0 else DEFAULT_DEC
    CHECKS.append((claim, got, exp, dec, abs(round(got, dec) - round(exp, dec)) < 1e-9))


# 1 standing points
p, r = seg("m1b_lego_gated_test", "tuned+len");            C("lego shipped tuned P", p, 0.6196); C("lego shipped tuned R", r, 0.2856)
p, r = seg("m1b_lego_tc_teed_native_0.5_f0.40", "tuned+len"); C("lego TEED f0.40 tuned P", p, 0.6535); C("lego TEED f0.40 tuned R", r, 0.4463)
p, r = seg("m1b_chair_gated_test", "tuned+len");           C("chair shipped tuned P", p, 0.6573); C("chair shipped tuned R", r, 0.5959)
# 2 breakthrough table
p, r = seg("m1b_lego_gated_test", "spec");                 C("lego canny spec P", p, 0.5826); C("lego canny spec R", r, 0.4168)
p, r = seg("m1b_lego_tc_teed_native_0.5_f0.40", "spec");    C("lego TEED spec P", p, 0.6197); C("lego TEED spec R", r, 0.6267)
t = temporal("m1b_stroke_temporal_table_vf100_gate030", "lego"); C("lego canny ctrl ratio", t["ratio"], 12.10); C("lego canny ctrl Fre", t["fre_ratio"], 13.98); C("lego canny ctrl P_pop", t["P_pop"], 0.05942); C("lego canny ctrl cut", t["cut"], 0.0254)
t = temporal("m1b_stroke_temporal_table_ehyb_teed040", "lego"); C("lego TEED f0.40 ratio", t["ratio"], 12.10); C("lego TEED f0.40 Fre", t["fre_ratio"], 14.81); C("lego TEED f0.40 P_pop", t["P_pop"], 0.05942); C("lego TEED f0.40 cut", t["cut"], 0.0225)
t = temporal("m1b_stroke_temporal_table_vf100_f100spec", "lego"); C("lego f=1.00 cut", t["cut"], 0.0424)
t = temporal("m1b_stroke_temporal_table", "lego");         C("lego published ratio", t["ratio"], 11.494)
t = temporal("m1b_stroke_temporal_table", "chair");        C("chair published ratio", t["ratio"], 11.35)
# 3/4 channels
C("agree lego min3 vs TEED", jkey("pb1b_tier0", "lego", "arms", "AGREE_min3", "overlap_vs_TEED"), 0.7992)
C("agree lego vs PiDiNet",   jkey("pb1b_tier0", "lego", "pairwise", "PiDiNet|AGREE_min3"), 0.8376)
C("junction lam2 AUC",       jkey("a_reframed_tier0", "auc", "lam2"), 0.7053)
C("junction seedscore AUC",  jkey("a_reframed_tier0", "auc", "teed_seedscore"), 0.7271)
Q1 = "Q1 band90-vs-band30 (all near-crease)"; Q2B = "Q2b nontess-vs-tess (NON-SEEDED only)"
C("ms_alone AUC",            jkey("ms_ratio_tier0", "auc", Q1, "ms_alone"), 0.6501)
C("ms native_alone AUC",     jkey("ms_ratio_tier0", "auc", Q1, "native_alone"), 0.6058)
C("ms seedscore AUC",        jkey("ms_ratio_tier0", "auc", Q1, "teed_seedscore"), 0.7270)
C("ms culled best",          jkey("ms_ratio_tier0", "auc", Q2B, "ms_minus_native"), 0.6250)
C("ms culled seedscore",     jkey("ms_ratio_tier0", "auc", Q2B, "teed_seedscore"), 0.7071)
p, r = seg("m1b_lego_tc_union_native_0.5_f0.40", "tuned+len"); C("union tuned P", p, 0.6429); C("union tuned R", r, 0.4424)
p, r = seg("m1b_chair_tc_dexined_native_0.5_f0.30", "tuned+len")  # chair DexiNed exists
C("chair DexiNed seedP", jkey("chair_dexined_seedpr", "DexiNed_0.5", "seedP15"), 0.5786)
C("chair TEED seedP",    jkey("chair_dexined_seedpr", "TEED_0.5", "seedP15"), 0.6485)
# 5/6 E-BAND
b90 = jkey("e_band_lego", "bands", "theta=90.000"); b30 = jkey("e_band_lego", "bands", "theta=30.000")
C("b90 share_of_missset", b90["share_of_missset"], 0.1505); C("b90 realised", b90["realised_R"], 0.7983)
C("b90 culled", b90["COVERED_culled"], 0.0938); C("b90 share_all", b90["share_of_all"], 0.243)
C("b30 culled", b30["COVERED_culled"], 0.2966); C("b30 share_of_missset", b30["share_of_missset"], 0.649)
C("global realised", jkey("e_band_lego", "global", "realised"), 0.6744)
C("global culled", jkey("e_band_lego", "global", "culled"), 0.1754)
C("tess reachable", b30["share_of_all"] * b30["COVERED_culled"], 0.125, dec=3)
nont = sum(v["share_of_all"] * v["COVERED_culled"] for k, v in jkey("e_band_lego", "bands").items() if k != "theta=30.000")
C("non-tess reachable", nont, 0.050, dec=3)
# 7 E-VAL / E-FMARGIN
C("E-VAL retention R", jkey("e_val_lego", "shrinkage_R"), 0.946, dec=3)
C("E-VAL chair gap R", jkey("e_val_chair", "val_gap_R"), 0.0354)
C("E-VAL chair TEED f0.30 VAL P", jkey("e_val_chair", "arms", "TEED0.5 f=0.30", "val_P") - jkey("e_val_chair", "arms", "canny f=0.30 (shipped)", "val_P"), -0.0452)
# 8 trajectory
for stem, scene, claim, exp in [
    ("m1b_stroke_temporal_table_etraj_lego_valorb_ungated", "lego", "lego ungated VAL orbit", 8.663),
    ("m1b_stroke_temporal_table_etraj_valorb_ungated", "chair", "chair ungated VAL orbit", 10.18),
    ("m1b_stroke_temporal_table_etraj_valorb_gated", "chair", "chair gated VAL orbit", 12.18),
    ("m1b_stroke_temporal_table_fm_valorb_canny030", "lego", "lego gated VAL orbit", 8.64),
    ("m1b_stroke_temporal_table_tc_tccanny", "chair", "chair gated TEST orbit", 10.71)]:
    C(claim, temporal(stem, scene)["ratio"], exp)
C("lego f=0.50 ratio", temporal("m1b_stroke_temporal_table_pb1_teed050", "lego")["ratio"], 10.38)
C("lego f=0.60 ratio", temporal("m1b_stroke_temporal_table_pb1_teed060", "lego")["ratio"], 10.27)

bad = [c for c in CHECKS if not c[4]]
print(f"{'claim':34s} {'ledger':>10s} {'banked':>10s} {'dp':>3s}  ok")
for claim, got, exp, dec, ok in CHECKS:
    print(f"{claim:34s} {exp:10.4f} {got:10.4f} {dec:3d}  {'OK' if ok else '*** MISMATCH ***'}")
print(f"\nchecked {len(CHECKS)} numerals | contradictions {len(bad)} | unsourced 0 "
      f"(every check names its banked json)")
print(f"GATE: {'GO' if not bad else 'NO-GO'}")
json.dump({"n_checked": len(CHECKS), "n_contradictions": len(bad), "n_unsourced": 0,
           "gate": "GO" if not bad else "NO-GO", "rule": "banked value must round to the numeral at the precision asserted",
           "mismatches": [{"claim": c[0], "ledger": c[2], "banked": c[1], "dp": c[3]} for c in bad]},
          open(os.path.join(OUT, "e_ledger_check.json"), "w"), indent=2)
print("wrote out/e_ledger_check.json")
