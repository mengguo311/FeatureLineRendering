#!/usr/bin/env python
"""B3 — SHIP the frozen feature-line pipeline: line-drawing figures + per-scene table.

*** Transcription + rendering of FROZEN artefacts.  No new method, no retraining.  The GT
    mesh is never touched here: every P/R number is read from the banked M1b eval jsons
    (which scored against the mesh, EVAL-ONLY, on held-out TEST views). ***

WHAT IS SHIPPED
    The M1b object-space line pipeline (scripts/run_m1b.py, frozen args f=0.30, edge=sharp,
    100 views, DT pull on the 80 TRAIN views, geometric gate theta=20/tau=0.015 for the
    'gated' variant): 3D linelets -> NMS -> chained into static 3D polylines
    (src/strokes.chain_linelets_3d) -> projected per view through the frozen 3DGS z-buffer
    with occlusion splitting (scripts/m1b_stroke_temporal.ours_strokes).  That is exactly the
    stroke set behind the banked 7-13x temporal result (out/m1b_stroke_temporal_table.md).

FIGURES (deliverable A)   out/ship/fig_lines_<scene>.{png,pdf}
    held-out TEST view: (i) 3DGS render = SH-degree-0 albedo composited over white (the
    view-independent colour the pipeline itself renders; the GT photo is NOT used),
    (ii) the shipped 3D feature lines projected and overlaid, (iii) the pure line drawing,
    (iv) per-frame Canny on the same render (the temporal baseline) for contrast.

TABLE (deliverable B)     out/ship/tab_ship_perscene.{json,md} + tab_ship.png
    per scene: held-out TEST P@1.5 / R@1.5 / F1 (points and segments, gated and ungated),
    DexiNed multi-view triangulation 3D recall vs single-view depth lift, discriminator AUC,
    temporal P_pop / Frechet ratios (OURS vs per-frame Canny) at 30/60/120/240 frames, and
    the caveats row (ficus foliage exclusion, train-fit vs test-eval, the line-buffer NO-GO).
"""
import argparse
import json
import os
import sys
import types

import cv2
import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
from src import common, render, strokes, view_split           # noqa: E402  METHOD PATH
import m1b_stroke_temporal as MT                                # noqa: E402  build_chains / ours_strokes

OUT = os.path.join(TIER1, "out")
SHIP = os.path.join(OUT, "ship")
SCENES = ["chair", "lego", "ficus"]
# validated dataviz palette slots (light mode)
C1, C2, C3, C_TXT, C_TXT2, C_GRID, SURF = "#2a78d6", "#eb6834", "#1baf7a", "#0b0b0b", "#52514e", "#e6e5e1", "#fcfcfb"

CHAIN_ARGS = types.SimpleNamespace(nms_mult=1.0, knn=10, cos_tan=0.60, cos_col=0.50, gap_mult=4.0,
                                   min_nodes=3, carrier_persistence=False, cp_ratio=0.8, cp_views=20)


def log(m):
    print(m, flush=True)


# ============================================================================ FIGURES
def albedo_render(g, keep_g, cam):
    gb = render.render_gbuffer(g, keep_g, cam, with_albedo=True)
    alb = gb["albedo"].detach().cpu().numpy()
    a = gb["alpha"].detach().cpu().numpy()[..., None]
    rgb = np.clip(alb * a + 1.0 * (1 - a), 0, 1)
    return rgb, gb["depth"], gb["alpha"].detach().cpu().numpy()


def fig_scene(scene, view, variant, dpi):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    cams, _ = common.load_cameras(scene)
    g = common.load_gaussians(scene)
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    chain3d, cinfo = MT.build_chains(scene, variant, CHAIN_ARGS)
    cam = cams[view]
    rgb, depth_t, alpha = albedo_render(g, keep_g, cam)
    ours = MT.ours_strokes(chain3d, cam, depth_t)
    gray = np.clip(rgb.mean(2) * 255, 0, 255).astype(np.uint8)
    canny = MT.baseline_strokes(gray, 50, 150, 4, 1.0)
    H, W = gray.shape
    m_ours = strokes.raster_polylines(ours, H, W)
    info = {"scene": scene, "view": int(view), "variant": variant, "n_strokes_3d": cinfo["n_strokes"],
            "n_linelets": cinfo["n_linelets"], "n_strokes_projected": len(ours),
            "n_canny_strokes": len(canny), "line_px_ours": int(m_ours.sum())}
    fig, ax = plt.subplots(1, 4, figsize=(20, 5.6), facecolor=SURF)
    titles = [f"{scene}: 3DGS render (SH-0 albedo), held-out TEST view {view}",
              f"shipped 3D feature lines overlaid ({len(ours)} strokes)",
              "pure line drawing (object-space lines, projected)",
              f"temporal baseline: per-frame Canny ({len(canny)} strokes)"]
    ax[0].imshow(rgb)
    ax[1].imshow(rgb)
    ax[1].add_collection(LineCollection([p for p in ours], colors=C1, linewidths=1.4))
    ax[2].imshow(np.ones_like(rgb))
    ax[2].add_collection(LineCollection([p for p in ours], colors=C_TXT, linewidths=0.9))
    ax[3].imshow(np.ones_like(rgb))
    ax[3].add_collection(LineCollection([p for p in canny], colors=C2, linewidths=0.9))
    for a, t in zip(ax, titles):
        a.set_xlim(0, W - 1)
        a.set_ylim(H - 1, 0)
        a.set_title(t, color=C_TXT, fontsize=9.5, loc="left")
        a.axis("off")
    fig.tight_layout()
    os.makedirs(SHIP, exist_ok=True)
    p = os.path.join(SHIP, f"fig_lines_{scene}.png")
    fig.savefig(p, dpi=dpi, facecolor=SURF)
    fig.savefig(p.replace(".png", ".pdf"), facecolor=SURF)
    plt.close(fig)
    # standalone pure line drawing at full resolution (black on white), for the paper
    img = np.full((H, W, 3), 255, np.uint8)
    img[m_ours] = (20, 20, 20)
    cv2.imwrite(os.path.join(SHIP, f"lines_{scene}_v{view}_{variant}.png"), img)
    strokes.write_svg(os.path.join(SHIP, f"lines_{scene}_v{view}_{variant}.svg"), ours, W, H, width=1.2)
    log(f"[figs] {scene}: {info} -> {p}")
    return info


# ============================================================================ TABLE
def m1b_rows(scene, variant):
    p = os.path.join(OUT, f"m1b_{scene}_{variant}_test.json")
    if not os.path.exists(p):
        return None
    j = json.load(open(p))
    rows = {(r["stage"].strip(), r["kind"]): r for r in j["rows"]}
    pts = rows[("AFTER   pull+prune[tuned]", "points")]
    seg = rows[("AFTER   pull+prune[tuned+len]", "segments")]
    pts0 = rows[("BEFORE  seeds (M1a)", "points")]

    def f1(P, R):
        return 0.0 if P + R == 0 else 2 * P * R / (P + R)

    return {"variant": variant, "args": {k: j["args"][k] for k in ("f", "edge", "views", "gate", "pull_split", "eval_split")},
            "n_lines": int(seg["n"]), "n_seeds": int(j["n_seeds"]), "eval_views": j["eval_views"],
            "points": {"P@1.5": pts["P1.5"], "R@1.5": pts["R1.5"], "F1@1.5": f1(pts["P1.5"], pts["R1.5"]),
                       "P@2.5": pts["P2.5"], "R@2.5": pts["R2.5"], "F1@2.5": f1(pts["P2.5"], pts["R2.5"])},
            "segments": {"P@1.5": seg["P1.5"], "R@1.5": seg["R1.5"], "F1@1.5": f1(seg["P1.5"], seg["R1.5"]),
                         "P@2.5": seg["P2.5"], "R@2.5": seg["R2.5"], "F1@2.5": f1(seg["P2.5"], seg["R2.5"])},
            "seeds_before_pull_points": {"P@1.5": pts0["P1.5"], "R@1.5": pts0["R1.5"]},
            "source": os.path.basename(p)}


def temporal_rows(scene):
    if scene in ("chair", "lego"):
        t = json.load(open(os.path.join(OUT, "m1b_stroke_temporal_table.json")))
        r = t["headline"][scene]
        src = "m1b_stroke_temporal_table.json[headline]"
    else:
        p = os.path.join(OUT, f"m1b_stroke_temporal_table_ship_{scene}.json")
        if not os.path.exists(p):
            return None
        t = json.load(open(p))
        r = t["scenes"][scene] if "scenes" in t else t["headline"][scene]
        src = os.path.basename(p)
    out = {"trajectory": r.get("trajectory"), "variant": r.get("variant"), "chain": r.get("chain"), "by_frames": {}, "source": src}
    for nf, b in r["by_frames"].items():
        A, B = b["A"], b["B"]
        out["by_frames"][nf] = {"P_pop_ours": A["P_pop"], "P_pop_canny": B["P_pop"],
                                "P_pop_ratio": B["P_pop"] / max(A["P_pop"], 1e-9),
                                "frechet_med_ours": A["frechet_median"], "frechet_med_canny": B["frechet_median"],
                                "frechet_ratio": B["frechet_median"] / max(A["frechet_median"], 1e-9),
                                "strokes_per_frame_ours": A.get("n_strokes_per_frame"),
                                "strokes_per_frame_canny": B.get("n_strokes_per_frame")}
    return out


def triangulation_rows(scene):
    out = {}
    if scene == "chair":
        j = json.load(open(os.path.join(OUT, "dexprimary_p1b_chair_ref40.json")))
        c = j["clouds"]
        out = {"tri_sup2_recall_3D": c["tri_sup2"]["recall_3D_px1.5_equiv"], "tri_sup2_precision_3D": c["tri_sup2"]["precision_3D_px1.5_equiv"],
               "singleview_recall_3D": c["p0_singleview"]["recall_3D_px1.5_equiv"], "miss_set_recovery": c["tri_sup2"]["R_miss_3D_px1.5_equiv"],
               "source": "dexprimary_p1b_chair_ref40.json"}
    elif scene == "ficus":
        p = os.path.join(OUT, "dexprimary_p1b_ficus_ref40.json")
        if os.path.exists(p):
            j = json.load(open(p))
            c = j["clouds"]
            out = {"tri_sup2_recall_3D": c["tri_sup2"]["recall_3D_px1.5_equiv"], "tri_sup2_precision_3D": c["tri_sup2"]["precision_3D_px1.5_equiv"],
                   "singleview_recall_3D": c["p0_singleview"]["recall_3D_px1.5_equiv"], "miss_set_recovery": c["tri_sup2"]["R_miss_3D_px1.5_equiv"],
                   "source": "dexprimary_p1b_ficus_ref40.json"}
    elif scene == "lego":
        p = os.path.join(OUT, "xy", "xy_expX_lego_p1c.json")
        j = json.load(open(p))
        out = {"tri_sup2_recall_3D": j["recall_3D"], "tri_sup2_precision_3D": None, "singleview_recall_3D": None,
               "miss_set_recovery": None, "source": "xy/xy_expX_lego_p1c.json (p1c cloud, same generator; no p1b json for lego)"}
    return out


DISC_AUC = {"chair": (0.8401, "RESULTS_MASTER.md (DINOv2 semantic family, held-out, P1c/P1d)"),
            "lego": (0.9044, "RESULTS_MASTER.md (DINOv2 semantic family, held-out, P1c/P1d)"),
            "ficus": (None, "not run (P1c is scoped to chair/lego)")}


def build_table(fig_info):
    tab = {"deliverable": "B3 per-scene table", "held_out": "TEST views [5,15,...,95]; DT pull on TRAIN views only",
           "definitions": {"P/R@1.5": "pixel precision/recall at 1.5 px vs GT-mesh crease pixels (mesh EVAL-ONLY), mean over the 10 TEST views; points = linelet centres, segments = rasterised linelets",
                           "temporal": "forward-warped stroke residual on the 240-frame look-at orbit between TEST views 5 and 15; P_pop = popped-stroke fraction, ratio = Canny/OURS (higher = OURS steadier)",
                           "triangulation": "DexiNed multi-view triangulation (Phase 1b) 3D recall @1.5px-equiv of TEST-visible GT crease points vs single-view depth lift"},
           "scenes": {}}
    for sc in SCENES:
        tab["scenes"][sc] = {"m1b_gated": m1b_rows(sc, "gated"), "m1b_ungated": m1b_rows(sc, "ungated"),
                             "temporal": temporal_rows(sc), "triangulation": triangulation_rows(sc),
                             "discriminator_auc": {"value": DISC_AUC[sc][0], "source": DISC_AUC[sc][1]},
                             "figure": fig_info.get(sc)}
    tab["caveats"] = [
        "ficus: the banked headline table (out/m1b_headline_table.md) EXCLUDES ficus by design ('thin/foliage: only 33% of object pixels are >4px from a silhouette, so crease vs flat surface is not well posed'); it is run here for completeness with the identical frozen recipe and reported straight. Its GT crease set (mesh_oracle, split-vertex face adjacency) covers only ~31% of the geometric >=30deg edges and none of the 31,390 open-boundary leaf-rim edges, so P/R vs 'GT creases' understates what the lines capture on a plant.",
        "train-fit vs test-eval: the DT pull (the only fitted step) consumed the 80 TRAIN views; every P/R and temporal number is on the 10 held-out TEST views / the TEST-to-TEST orbit. The prune/length thresholds ('tuned') were selected on VAL views per the M1b protocol; no number here is in-sample.",
        "line-buffer pivot NO-GO (motivation for shipping the frozen design): pre-registered EPIPOLAR ACCUMULATION TEST, corrected labels (out/EPIPOLAR_ACCUM_RESULTS.md): lego S_bar AUC 0.698 / Recall@85%P 0.000 (NO-GO, structural), chair 0.859 / 0.000 (NO-GO, knife-edge). Multi-view accumulation of raw DexiNed does not separate missed creases from flat surface at 85% precision; the mechanism is DexiNed's ~5 px spatial response tail on edge-dense surfaces, not dead zeros. (The B3 spec's 0.572/0.733 figures are from the superseded first run with a label bug.)",
        "GT crease topology (inherited, all scenes): src/mesh_oracle.py builds GT creases from split-vertex face adjacency; the banked crease set covers 37% (lego) / 43% (chair) / ~31% (ficus) of the geometric >=30deg edges. All P/R here are against that banked definition, as in every prior result.",
    ]
    os.makedirs(SHIP, exist_ok=True)
    json.dump(tab, open(os.path.join(SHIP, "tab_ship_perscene.json"), "w"), indent=1, default=float)
    write_md(tab)
    render_png(tab)
    return tab


def _f(x, nd=3):
    return "—" if x is None else f"{x:.{nd}f}"


def write_md(tab):
    L = ["# B3 — per-scene table (held-out TEST; mesh EVAL-ONLY)\n",
         f"{tab['held_out']}. Definitions: {tab['definitions']['P/R@1.5']}. Temporal: {tab['definitions']['temporal']}.\n",
         "## Shipped lines (M1b gated variant): precision / recall / F1 vs GT-mesh creases\n",
         "| scene | n lines | points P@1.5 | R@1.5 | F1 | segments P@1.5 | R@1.5 | F1 | segments P@2.5 | R@2.5 | ungated seg P/R@1.5 |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for sc, d in tab["scenes"].items():
        g_, u_ = d["m1b_gated"], d["m1b_ungated"]
        if g_ is None:
            L.append(f"| {sc} | — | not run | | | | | | | | |")
            continue
        p, s = g_["points"], g_["segments"]
        us = u_["segments"] if u_ else None
        L.append(f"| {sc} | {g_['n_lines']:,} | {_f(p['P@1.5'])} | {_f(p['R@1.5'])} | {_f(p['F1@1.5'])} | {_f(s['P@1.5'])} | {_f(s['R@1.5'])} | {_f(s['F1@1.5'])} | "
                 f"{_f(s['P@2.5'])} | {_f(s['R@2.5'])} | {_f(us['P@1.5']) if us else '—'} / {_f(us['R@1.5']) if us else '—'} |")
    L += ["\n## Temporal coherence: object-space lines vs per-frame Canny (P_pop ratio = Canny/OURS; the 7-13x crown jewel = 120-240 f band)\n",
          "| scene | 30 f P_pop OURS / Canny (ratio) | 60 f | 120 f | 240 f | Frechet ratio 240 f | strokes/frame OURS / Canny |",
          "|---|---|---|---|---|---|---|"]
    for sc, d in tab["scenes"].items():
        t = d["temporal"]
        if t is None:
            L.append(f"| {sc} | not run | | | | | |")
            continue
        cells = []
        for nf in ("30", "60", "120", "240"):
            b = t["by_frames"].get(nf)
            cells.append(f"{b['P_pop_ours']:.3f} / {b['P_pop_canny']:.3f} (**{b['P_pop_ratio']:.2f}x**)" if b else "—")
        b240 = t["by_frames"].get("240", {})
        L.append(f"| {sc} | " + " | ".join(cells) + f" | {b240.get('frechet_ratio', float('nan')):.2f}x | "
                 f"{_f(b240.get('strokes_per_frame_ours'), 0)} / {_f(b240.get('strokes_per_frame_canny'), 0)} |")
    L += ["\n## Coverage-ceiling breaker and discriminator (context rows)\n",
          "| scene | DexiNed triangulation 3D recall @1.5px-equiv | single-view depth lift | miss-set recovery | triangulation precision | DINOv2 crease-vs-texture AUC (held-out) |",
          "|---|---|---|---|---|---|"]
    for sc, d in tab["scenes"].items():
        tr, da = d["triangulation"], d["discriminator_auc"]
        L.append(f"| {sc} | {_f(tr.get('tri_sup2_recall_3D'), 4)} | {_f(tr.get('singleview_recall_3D'), 4)} | {_f(tr.get('miss_set_recovery'), 4)} | "
                 f"{_f(tr.get('tri_sup2_precision_3D'), 4)} | {_f(da['value'], 4)} ({da['source']}) |")
    L.append("\n## Caveats\n")
    for c in tab["caveats"]:
        L.append(f"- {c}")
    L.append("\nSources per cell are in `out/ship/tab_ship_perscene.json` (`source` fields).")
    open(os.path.join(SHIP, "tab_ship_perscene.md"), "w").write("\n".join(L))
    log(f"[table] -> {os.path.join(SHIP, 'tab_ship_perscene.md')}")


def render_png(tab):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows, cols = [], ["scene", "lines", "pts P@1.5", "pts R@1.5", "pts F1", "seg P@1.5", "seg R@1.5", "seg F1",
                      "P_pop 120f (x)", "P_pop 240f (x)", "Frechet 240f (x)", "tri. 3D recall", "disc. AUC"]
    for sc, d in tab["scenes"].items():
        g_, t, tr, da = d["m1b_gated"], d["temporal"], d["triangulation"], d["discriminator_auc"]
        if g_ is None:
            rows.append([sc] + ["—"] * (len(cols) - 1))
            continue
        p, s = g_["points"], g_["segments"]
        b120 = t["by_frames"].get("120") if t else None
        b240 = t["by_frames"].get("240") if t else None
        rows.append([sc, f"{g_['n_lines']:,}", _f(p["P@1.5"]), _f(p["R@1.5"]), _f(p["F1@1.5"]), _f(s["P@1.5"]), _f(s["R@1.5"]), _f(s["F1@1.5"]),
                     f"{b120['P_pop_ratio']:.1f}" if b120 else "—", f"{b240['P_pop_ratio']:.1f}" if b240 else "—",
                     f"{b240['frechet_ratio']:.1f}" if b240 else "—", _f(tr.get("tri_sup2_recall_3D")), _f(da["value"])])
    fig, ax = plt.subplots(figsize=(15, 1.1 + 0.42 * len(rows)), facecolor=SURF)
    ax.axis("off")
    tb = ax.table(cellText=rows, colLabels=cols, loc="center", cellLoc="center")
    tb.auto_set_font_size(False)
    tb.set_fontsize(9)
    tb.scale(1.0, 1.5)
    for (r, c), cell in tb.get_celld().items():
        cell.set_edgecolor(C_GRID)
        cell.set_text_props(color=C_TXT)
        if r == 0:
            cell.set_facecolor("#efeeea")
            cell.set_text_props(weight="bold", color=C_TXT)
        else:
            cell.set_facecolor(SURF)
    ax.set_title("B3 ship table — held-out TEST, mesh EVAL-ONLY; temporal ratios = per-frame Canny / object-space lines (higher = steadier)",
                 color=C_TXT, fontsize=10, loc="left")
    fig.text(0.01, 0.01, "ficus is the banked-excluded foliage scene (crease-vs-flat ill-posed; GT crease set covers ~31% of geometric edges and no leaf rims) — reported straight, see caveats.",
             color=C_TXT2, fontsize=8)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(os.path.join(SHIP, "tab_ship.png"), dpi=170, facecolor=SURF)
    plt.close(fig)
    log(f"[table] -> {os.path.join(SHIP, 'tab_ship.png')}")


def build_master(tab):
    """ONE combined per-scene master table: shipped-line P/R/F1 + temporal ratios at 240 frames
    (P_pop and Frechet), with the Contribution-B diagnostic rows kept as CONTEXT columns."""
    rows = []
    for sc, d in tab["scenes"].items():
        g_, u_, t, tr, da = d["m1b_gated"], d["m1b_ungated"], d["temporal"], d["triangulation"], d["discriminator_auc"]
        b = t["by_frames"].get("240") if t else None
        rows.append({"scene": sc, "shipped_lines_n": g_["n_lines"] if g_ else None,
                     "points_P@1.5": g_["points"]["P@1.5"] if g_ else None, "points_R@1.5": g_["points"]["R@1.5"] if g_ else None,
                     "points_F1@1.5": g_["points"]["F1@1.5"] if g_ else None,
                     "segments_P@1.5": g_["segments"]["P@1.5"] if g_ else None, "segments_R@1.5": g_["segments"]["R@1.5"] if g_ else None,
                     "segments_F1@1.5": g_["segments"]["F1@1.5"] if g_ else None,
                     "ungated_segments_P@1.5": u_["segments"]["P@1.5"] if u_ else None, "ungated_segments_R@1.5": u_["segments"]["R@1.5"] if u_ else None,
                     "P_pop_ours_240f": b["P_pop_ours"] if b else None, "P_pop_canny_240f": b["P_pop_canny"] if b else None,
                     "P_pop_ratio_240f": b["P_pop_ratio"] if b else None,
                     "frechet_ours_240f": b["frechet_med_ours"] if b else None, "frechet_canny_240f": b["frechet_med_canny"] if b else None,
                     "frechet_ratio_240f": b["frechet_ratio"] if b else None,
                     "strokes_per_frame_ours": b["strokes_per_frame_ours"] if b else None, "strokes_per_frame_canny": b["strokes_per_frame_canny"] if b else None,
                     "CONTEXT_triangulation_3D_recall": tr.get("tri_sup2_recall_3D"), "CONTEXT_dinov2_auc": da["value"],
                     "sources": {"m1b": g_["source"] if g_ else None, "temporal": t["source"] if t else None,
                                 "triangulation": tr.get("source"), "discriminator": da["source"]}})
    master = {"title": "B3 master per-scene table — shipped M1b object-space lines (gated variant), held-out TEST, mesh EVAL-ONLY",
              "shipped_generator": "M1b: frozen-3DGS carrier seeds -> linelets -> multi-view DT pull (TRAIN views) -> consensus prune -> 3D NMS + chaining -> per-frame projection through the 3DGS z-buffer",
              "context_columns_note": "triangulation recall and DINOv2 AUC are Contribution B DIAGNOSTIC precision-boundary rows; they are NOT stages of the shipped generator",
              "temporal_definition": tab["definitions"]["temporal"] + "; ratios at 240 frames (the finest-motion end of the banked 7-13x band)",
              "rows": rows, "caveats": tab["caveats"]}
    json.dump(master, open(os.path.join(SHIP, "tab_master_perscene.json"), "w"), indent=1, default=float)
    L = [f"# {master['title']}\n", f"Shipped generator: {master['shipped_generator']}.  {master['context_columns_note']}.\n",
         "| scene | shipped lines | points P / R / F1 @1.5 | segments P / R / F1 @1.5 | P_pop 240 f ours / Canny | **P_pop ratio** | Frechet med 240 f ours / Canny (px) | **Frechet ratio** | strokes/frame ours / Canny | ctx: triangulation 3D recall | ctx: DINOv2 AUC |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['scene']} | {r['shipped_lines_n']:,} | {_f(r['points_P@1.5'])} / {_f(r['points_R@1.5'])} / {_f(r['points_F1@1.5'])} | "
                 f"{_f(r['segments_P@1.5'])} / {_f(r['segments_R@1.5'])} / {_f(r['segments_F1@1.5'])} | "
                 f"{_f(r['P_pop_ours_240f'])} / {_f(r['P_pop_canny_240f'])} | **{_f(r['P_pop_ratio_240f'], 2)}x** | "
                 f"{_f(r['frechet_ours_240f'])} / {_f(r['frechet_canny_240f'])} | **{_f(r['frechet_ratio_240f'], 2)}x** | "
                 f"{_f(r['strokes_per_frame_ours'], 0)} / {_f(r['strokes_per_frame_canny'], 0)} | {_f(r['CONTEXT_triangulation_3D_recall'])} | {_f(r['CONTEXT_dinov2_auc'])} |")
    L.append(f"\n{master['temporal_definition']}.\n\n## Caveats\n")
    for c in master["caveats"]:
        L.append(f"- {c}")
    open(os.path.join(SHIP, "tab_master_perscene.md"), "w").write("\n".join(L))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cols = ["scene", "lines", "pts P/R/F1@1.5", "seg P/R/F1@1.5", "P_pop 240f ours/Canny", "P_pop ratio", "Frechet 240f ours/Canny", "Frechet ratio", "strokes/f ours/Canny", "ctx tri. recall", "ctx DINOv2 AUC"]
    cells = [[r["scene"], f"{r['shipped_lines_n']:,}", f"{_f(r['points_P@1.5'])}/{_f(r['points_R@1.5'])}/{_f(r['points_F1@1.5'])}",
              f"{_f(r['segments_P@1.5'])}/{_f(r['segments_R@1.5'])}/{_f(r['segments_F1@1.5'])}", f"{_f(r['P_pop_ours_240f'])}/{_f(r['P_pop_canny_240f'])}",
              f"{_f(r['P_pop_ratio_240f'], 1)}x", f"{_f(r['frechet_ours_240f'])}/{_f(r['frechet_canny_240f'])}", f"{_f(r['frechet_ratio_240f'], 1)}x",
              f"{_f(r['strokes_per_frame_ours'], 0)}/{_f(r['strokes_per_frame_canny'], 0)}", _f(r["CONTEXT_triangulation_3D_recall"]), _f(r["CONTEXT_dinov2_auc"])] for r in rows]
    fig, ax = plt.subplots(figsize=(17, 1.1 + 0.42 * len(rows)), facecolor=SURF)
    ax.axis("off")
    tb = ax.table(cellText=cells, colLabels=cols, loc="center", cellLoc="center")
    tb.auto_set_font_size(False)
    tb.set_fontsize(8.5)
    tb.scale(1.0, 1.5)
    for (rr, cc), cell in tb.get_celld().items():
        cell.set_edgecolor(C_GRID)
        cell.set_text_props(color=C_TXT, weight="bold" if rr == 0 else "normal")
        cell.set_facecolor("#efeeea" if rr == 0 else SURF)
    ax.set_title("B3 master table — shipped M1b lines (gated), held-out TEST, mesh EVAL-ONLY; ratios = per-frame Canny / ours at 240 frames (higher = steadier); ctx = Contribution B diagnostic rows, not shipped stages",
                 color=C_TXT, fontsize=9, loc="left")
    fig.text(0.01, 0.01, "ficus: banked-excluded foliage scene run with the identical frozen recipe; its GT crease set covers ~31% of geometric creases and no leaf rims (see caveats).",
             color=C_TXT2, fontsize=8)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(os.path.join(SHIP, "tab_master_perscene.png"), dpi=170, facecolor=SURF)
    plt.close(fig)
    log(f"[master] -> {os.path.join(SHIP, 'tab_master_perscene.{json,md,png}')}")
    return master


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all", choices=["figs", "table", "master", "all"])
    ap.add_argument("--scenes", nargs="+", default=SCENES)
    ap.add_argument("--view", type=int, default=25, help="held-out TEST view for the figures")
    ap.add_argument("--variant", default="gated", help="linelet variant to draw (gated = shipped lines)")
    ap.add_argument("--dpi", type=int, default=150)
    args = ap.parse_args()
    assert args.view in view_split.TEST, "figure view must be a held-out TEST view"
    info = {}
    if args.stage in ("figs", "all"):
        for sc in args.scenes:
            if os.path.exists(os.path.join(OUT, f"linelets_{sc}_{args.variant}_test.npz")):
                info[sc] = fig_scene(sc, args.view, args.variant, args.dpi)
            else:
                log(f"[figs] {sc}: linelets_{sc}_{args.variant}_test.npz missing — skipped")
    tab = None
    if args.stage in ("table", "all"):
        if not info:
            p = os.path.join(SHIP, "tab_ship_perscene.json")
            if os.path.exists(p):
                info = {k: v.get("figure") for k, v in json.load(open(p))["scenes"].items()}
        tab = build_table(info)
    if args.stage in ("master", "all"):
        if tab is None:
            tab = json.load(open(os.path.join(SHIP, "tab_ship_perscene.json")))
        build_master(tab)


if __name__ == "__main__":
    main()
