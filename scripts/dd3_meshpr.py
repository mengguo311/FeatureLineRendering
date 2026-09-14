"""tier1/scripts/dd3_meshpr.py — HYGIENE item 6: mesh P/R for the dd3 carrier of record.

*** EVAL ONLY. *** The GT mesh enters only through the two cached oracle label sets every
banked cadpartA P/R already used (tune_lib.Harness crease pixels; dexprimary_p0.gt_labels
crease samples). Nothing in the method path is touched and nothing is tuned.

The dd3 carrier (out/carrier_dd3_cadpartA.npz, 59 static 3-D polylines) is scored under BOTH
conventions that the DD3 write-up quotes side by side, so the numbers are comparable to the
right thing:

  (1) SEGMENT-RASTER P@tau / R@tau on the 10 held-out TEST views, tau = 1.5 px (and 2.5),
      macro-averaged over views — run_m1b.eval_segments, the deliverable metric behind the
      STEP3 zero-knob point P 0.8139 / R 0.4206. Each polyline edge becomes a linelet
      (midpoint, unit tangent, half-length); edges are subdivided to at most the STEP3
      carrier's median full length so no piece trips the 64 px degenerate-segment guard and
      the per-segment visibility test is as fine as the banked carrier's. Rasterisation is
      pixel-identical with or without subdivision.
  (2) 3-D POINT precision/recall at the px1.5-equivalent radius (1.5 * median crease depth /
      f), the dexprimary_p1b convention behind the DexiNed-cloud number P 0.7302 / R 0.8431.
      The polylines are sampled at radius/5 along their length.

Both harnesses are first re-run on the banked inputs (STEP3 zero-knob linelets; DexiNed
tri_sup1 cloud) and must reproduce the banked numbers before the dd3 numbers are reported.
"""
import json, os, sys, time
import numpy as np
from scipy.spatial import cKDTree

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1); sys.path.insert(0, os.path.join(TIER1, "scripts"))
from src import common, view_split                                          # noqa: E402
import run_m1b                                                              # noqa: E402
from tune_lib import Harness                                                # noqa: E402  EVAL
from dexprimary_p0 import gt_labels                                         # noqa: E402  EVAL

OUT = os.path.join(TIER1, "out")
SCENE = "cadpartA"
TEST = tuple(view_split.TEST)


def load_polylines():
    z = np.load(os.path.join(OUT, f"carrier_dd3_{SCENE}.npz"))
    pts, offs = z["pts"], z["offs"]
    polys = [pts[offs[i]:offs[i + 1]] for i in range(len(offs) - 1)]
    return [P for P in polys if len(P) >= 2], {k: list(z[k].shape) for k in z.files}


def edges(polys):
    A, B = [], []
    for P in polys:
        A.append(P[:-1]); B.append(P[1:])
    return np.concatenate(A), np.concatenate(B)


def to_linelets(A, B, max_len):
    """Edge (a,b) -> n = ceil(|b-a|/max_len) collinear linelets covering it exactly."""
    p, t, l = [], [], []
    for a, b in zip(A, B):
        d = b - a; L = float(np.linalg.norm(d))
        if L < 1e-9:
            continue
        n = max(1, int(np.ceil(L / max_len)))
        u = d / L
        for k in range(n):
            s0, s1 = a + u * (L * k / n), a + u * (L * (k + 1) / n)
            p.append((s0 + s1) / 2); t.append(u); l.append(L / n / 2)
    return np.asarray(p), np.asarray(t), np.asarray(l)


def sample_edges(A, B, spacing):
    S = []
    for a, b in zip(A, B):
        L = float(np.linalg.norm(b - a))
        n = max(2, int(np.ceil(L / spacing)) + 1)
        S.append(a[None] + (b - a)[None] * np.linspace(0, 1, n)[:, None])
    return np.concatenate(S)


def pr3(P, crease_pts, seen_idx, tree_gt3, rad):
    d3 = cKDTree(P).query(crease_pts[seen_idx], k=1)[0]
    dprec = tree_gt3.query(P, k=1)[0]
    return {"precision_3D": float((dprec <= rad).mean()), "recall_3D": float((d3 <= rad).mean()),
            "chamfer_median": float(np.median(d3)), "n_points": int(len(P))}


def main():
    t0 = time.time()
    rep = {"scene": SCENE, "carrier": f"out/carrier_dd3_{SCENE}.npz", "test_views": list(TEST),
           "mesh_eval_only": "GT mesh read only via cached oracle labels (tune_lib.Harness, "
                             "dexprimary_p0.gt_labels); method path untouched; nothing tuned"}
    polys, fields = load_polylines()
    rep["carrier_fields"] = fields
    rep["n_strokes"] = len(polys)
    A, B = edges(polys)
    rep["n_edges"] = int(len(A))
    print(f"[dd3 carrier] fields {fields}  strokes {len(polys)}  edges {len(A)}", flush=True)

    # ---------------- (1) segment-raster metric, TEST views, tau 1.5 / 2.5 -----------------
    h = Harness(SCENE, views=TEST)
    z = np.load(os.path.join(OUT, f"linelets_{SCENE}_step3spec_test.npz"))
    keep = z["keep"].astype(bool)
    e_ref = run_m1b.eval_segments(h, z["p"], z["t"], z["l"], keep=keep, taus=(1.5, 2.5))
    rep["harness_check_step3_zero_knob"] = {"P@1.5": e_ref[1.5][0], "R@1.5": e_ref[1.5][1],
                                            "P@2.5": e_ref[2.5][0], "R@2.5": e_ref[2.5][1],
                                            "banked": "P 0.8139 / R 0.4206"}
    print(f"[check] STEP3 zero-knob via eval_segments: P@1.5 {e_ref[1.5][0]:.4f} "
          f"R@1.5 {e_ref[1.5][1]:.4f}  (banked 0.8139 / 0.4206)", flush=True)
    Lmed = float(2 * np.median(z["l"][keep]))
    rep["subdivision_max_len_world"] = Lmed
    p, t, l = to_linelets(A, B, Lmed)
    rep["n_linelets_after_subdivision"] = int(len(p))
    # how many raw edges would the 64 px guard drop, per view, if NOT subdivided
    p0, t0_, l0 = to_linelets(A, B, 1e9)
    drop = []
    for v in TEST:
        _, n_sub = run_m1b.raster_segments(h, v, p, t, l)
        _, n_raw = run_m1b.raster_segments(h, v, p0, t0_, l0)
        drop.append({"view": v, "drawn_subdivided": n_sub, "drawn_raw_edges": n_raw,
                     "raw_edges_total": int(len(p0))})
    rep["visibility_and_guard_per_view"] = drop
    e = run_m1b.eval_segments(h, p, t, l, keep=None, taus=(1.5, 2.5))
    e_pv = run_m1b.eval_segments(h, p, t, l, keep=None, taus=(1.5,), per_view=True)
    e_raw = run_m1b.eval_segments(h, p0, t0_, l0, keep=None, taus=(1.5,))
    rep["dd3_segment_raster"] = {
        "P@1.5": e[1.5][0], "R@1.5": e[1.5][1], "P@2.5": e[2.5][0], "R@2.5": e[2.5][1],
        "n_px_per_view_mean": e["n_px"],
        "per_view_P@1.5": e_pv[1.5][0], "per_view_R@1.5": e_pv[1.5][1],
        "sensitivity_no_subdivision_P@1.5": e_raw[1.5][0],
        "sensitivity_no_subdivision_R@1.5": e_raw[1.5][1]}
    print(f"[dd3] segment-raster TEST macro: P@1.5 {e[1.5][0]:.4f}  R@1.5 {e[1.5][1]:.4f}  "
          f"P@2.5 {e[2.5][0]:.4f}  R@2.5 {e[2.5][1]:.4f}   (no-subdivision sensitivity "
          f"P {e_raw[1.5][0]:.4f} R {e_raw[1.5][1]:.4f})", flush=True)
    print("[dd3] per view P@1.5: " + " ".join(f"{x:.3f}" for x in e_pv[1.5][0]), flush=True)
    print("[dd3] per view R@1.5: " + " ".join(f"{x:.3f}" for x in e_pv[1.5][1]), flush=True)

    # ---------------- (2) 3-D point metric, p1b convention ---------------------------------
    crease_pts, gt, bbox = gt_labels(SCENE, list(TEST))
    cams, _ = common.load_cameras(SCENE)
    seen = np.zeros(len(crease_pts), bool)
    for v in TEST:
        seen[gt[v][0]] = True
    seen_idx = np.where(seen)[0]
    zmed = float(np.median(np.concatenate(
        [((cams[v].w2c[:3, :3] @ crease_pts[gt[v][0]].T).T + cams[v].w2c[:3, 3])[:, 2]
         for v in TEST])))
    rad = 1.5 * zmed / cams[TEST[0]].f
    tree_gt3 = cKDTree(crease_pts)
    rep["radius_px1.5_equiv"] = rad
    rep["n_seen_gt_crease_samples"] = int(len(seen_idx))
    zc = np.load(os.path.join(OUT, f"dexprimary_p1b_cloud_{SCENE}_ref40.npz"))
    Pc = zc["P"][(zc["support"] >= 1) & zc["surface_keep"] & (zc["resid"] <= 1.0)]
    c_ref = pr3(Pc, crease_pts, seen_idx, tree_gt3, rad)
    c_ref["banked"] = "tri_sup1: P 0.7302 / R 0.8431 (n 220,255)"
    rep["harness_check_dexined_cloud_tri_sup1"] = c_ref
    print(f"[check] DexiNed tri_sup1 cloud 3-D: P {c_ref['precision_3D']:.4f} "
          f"R {c_ref['recall_3D']:.4f} n {c_ref['n_points']}  (banked 0.7302 / 0.8431, "
          f"radius {rad:.6f} vs banked 0.004860)", flush=True)
    S = sample_edges(A, B, rad / 5)
    c_dd3 = pr3(S, crease_pts, seen_idx, tree_gt3, rad)
    c_dd3["sample_spacing_world"] = rad / 5
    rep["dd3_point3D"] = c_dd3
    # STEP3 zero-knob segments sampled the same way, for a like-for-like 3-D row
    a3, b3 = z["p"][keep] - z["t"][keep] * z["l"][keep][:, None], \
        z["p"][keep] + z["t"][keep] * z["l"][keep][:, None]
    S3 = sample_edges(a3, b3, rad / 5)
    rep["step3_zero_knob_point3D_sampled"] = pr3(S3, crease_pts, seen_idx, tree_gt3, rad)
    print(f"[dd3] 3-D point metric @ px1.5-equiv: P {c_dd3['precision_3D']:.4f}  "
          f"R {c_dd3['recall_3D']:.4f}  (n samples {c_dd3['n_points']})", flush=True)
    print(f"[ref] STEP3 zero-knob sampled 3-D: P {rep['step3_zero_knob_point3D_sampled']['precision_3D']:.4f} "
          f"R {rep['step3_zero_knob_point3D_sampled']['recall_3D']:.4f}", flush=True)
    rep["elapsed_s"] = time.time() - t0
    pth = os.path.join(OUT, "dd3_meshpr.json")
    json.dump(rep, open(pth, "w"), indent=1)
    print(f"wrote {pth}  ({rep['elapsed_s']:.0f}s)")


if __name__ == "__main__":
    main()
