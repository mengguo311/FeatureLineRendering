"""RETRAIN-FALSIFY Experiment X — prize-pool sizing (spec: tier1/retrain_falsify_spec.md).

*** EVAL / ANALYSIS ONLY. Reads the GT mesh (permitted for diagnostics). No method file
    is added or modified; no pipeline is built. CPU-only; no GPU is touched. ***

Question: of the GT creases the FROZEN pipeline misses at 1.5px, what fraction g is
retrainable GEOMETRIC crease (real dihedral at scale) vs unrecoverable DECAL/flat
(dihedral ~0 at scale)?  Frozen rule: g<0.25 on lego => kill signal; g>0.40 => proceed Y.

FROZEN CONVENTIONS REUSED (nothing re-invented):
 - GT crease set: mesh adjacency edges with dihedral >= 30 deg, sampled at ds=0.0015
   (src/mesh_oracle.py); cached with per-TEST-view visibility in cache/dexp0_gt_<s>_a30.npz.
 - Frozen pipeline cloud: chair = out/dexprimary_p1b_cloud_chair_ref40.npz,
   lego = out/dexprimary_p1c_cloud_lego.npz, filtered support>=2 & surface_keep &
   resid<=1.0 (dexprimary_p1c.load_candidates). No discriminator gate exists in the
   frozen pipeline (Phase 1d/1e all NO-GO probes) -> the ungated cloud IS the pipeline.
 - Recovery test: 3D, GT crease point recovered iff nearest cloud point within
   TOL = px1.5_equiv = {chair: 0.00515, lego: 0.00508} (dexprimary_p1c.py TOL).
 - "seen" = visible in >=1 held-out TEST view {5,15,...,95}.

CLASSIFIER (frozen before running, stated in spec + here):
 - For each missed crease point's source mesh edge, measure the dihedral AT SCALE:
   faces with centroid within radius r of the edge midpoint, assigned to the two sides
   by normal affinity to the edge's two adjacent faces (orientation-corrected),
   area-weighted mean normal per side, angle between the oriented side means.
 - GEOMETRIC (retrainable) iff dihedral_at_scale >= 20 deg at r=0.01 (primary).
 - DECAL/flat iff dihedral_at_scale < 10 deg ("dihedral ~ 0").
 - band [10,20) and unmeasurable reported separately, EXCLUDED from g's numerator
   (conservative: favors the kill).
 - sensitivity: r in {0.005, 0.01, 0.02}; thresholds {5,10,15,20,30}.

Reproduction gates (hard): cloud filter counts must equal the banked 272,366 (chair) /
350,002 (lego); chair 3D recall must reproduce the banked 0.6753 within 5e-4.
"""
import json, os, sys, time
import numpy as np
import trimesh
from scipy.spatial import cKDTree

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
OUT = os.path.join(TIER1, "out"); CACHE = os.path.join(TIER1, "cache")
MESH_DIR = os.path.expanduser("~/3dgs_line/bcr/meshes/NeRF_Mesh")
TOL = {"chair": 0.00515, "lego": 0.00508}
CLOUD = {"chair": "dexprimary_p1b_cloud_chair_ref40.npz", "lego": "dexprimary_p1c_cloud_lego.npz"}
BANKED_KEEP = {"chair": 272366, "lego": 350002}
BANKED_RECALL = {"chair": 0.6753}     # lego: no banked tri-cloud 3D recall in P1b/P1C docs -> computed fresh, reported
TEST_VIEWS = [5, 15, 25, 35, 45, 55, 65, 75, 85, 95]
DS, ANGLE = 0.0015, 30.0
R_LIST = [0.005, 0.01, 0.02]
R_PRIMARY = 0.01
GEOM_MIN, FLAT_MAX = 20.0, 10.0
ANG_BANDS = [(30.0, 30.5), (30.5, 45.0), (45.0, 90.0), (90.0, 1e9)]


def sample_edges_with_ids(V, pairs, ds):
    """Exact vectorized replica of MeshOracle._sample_edges + per-point source edge id."""
    a = V[pairs[:, 0]]; b = V[pairs[:, 1]]
    seg = b - a
    L = np.linalg.norm(seg, axis=1)
    n = np.maximum(2, (L / ds).astype(np.int64) + 1)          # int() truncation, same as source
    eid = np.repeat(np.arange(len(a)), n)
    # ts = linspace(0,1,n_i) per edge: cumulative index within each edge
    start = np.concatenate([[0], np.cumsum(n)[:-1]])
    within = np.arange(n.sum()) - np.repeat(start, n)
    ts = within / np.repeat(n - 1, n).astype(np.float64)
    pts = a[eid] + ts[:, None] * seg[eid]
    return pts, eid


def dihedral_at_scale(mesh, e_verts, e_faces, r, cap=400):
    """Two-sided at-scale dihedral (deg) per edge; NaN if a side has no faces in the ball.
    Side split = normal affinity to the two adjacent faces; members orientation-corrected
    to their side's reference normal; area-weighted mean normals; oriented angle."""
    C = np.asarray(mesh.triangles_center); N = np.asarray(mesh.face_normals)
    W = np.asarray(mesh.area_faces)
    tree = cKDTree(C)
    mids = 0.5 * (mesh.vertices[e_verts[:, 0]] + mesh.vertices[e_verts[:, 1]])
    balls = tree.query_ball_point(mids, r, workers=-1)
    out = np.full(len(mids), np.nan)
    nsides = np.zeros((len(mids), 2), np.int32)
    for i, b in enumerate(balls):
        b = np.asarray(b, dtype=np.int64)
        if len(b) > cap:
            dd = np.linalg.norm(C[b] - mids[i], axis=1)
            b = b[np.argsort(dd, kind="stable")[:cap]]
        n1, n2 = N[e_faces[i, 0]], N[e_faces[i, 1]]
        nb = N[b]; wb = W[b]
        s1 = np.abs(nb @ n1) >= np.abs(nb @ n2)
        got = [None, None]
        for side, (mask, ref) in enumerate(((s1, n1), (~s1, n2))):
            idx = np.where(mask)[0]
            if len(idx) == 0:
                got[side] = None; continue
            nn = nb[idx].copy()
            flip = (nn @ ref) < 0
            nn[flip] *= -1.0
            m = (nn * wb[idx, None]).sum(0)
            nrm = np.linalg.norm(m)
            got[side] = m / nrm if nrm > 1e-12 else None
            nsides[i, side] = len(idx)
        if got[0] is not None and got[1] is not None:
            out[i] = np.degrees(np.arccos(np.clip(got[0] @ got[1], -1.0, 1.0)))
    return out, nsides


def run_scene(scene):
    t0 = time.time()
    res = {"scene": scene, "tol": TOL[scene], "frozen_rule": "g<0.25 kill / g>0.40 proceed (lego)",
           "classifier": {"r_primary": R_PRIMARY, "geom_min_deg": GEOM_MIN, "flat_max_deg": FLAT_MAX}}
    print(f"\n=== {scene} ===")
    gt = np.load(os.path.join(CACHE, f"dexp0_gt_{scene}_a30.npz"))
    crease_pts = gt["crease_pts"]
    seen_idx = np.unique(np.concatenate([gt[f"idx{v}"] for v in TEST_VIEWS]))
    res["n_crease_pts"] = int(len(crease_pts)); res["n_seen3d"] = int(len(seen_idx))
    print(f"crease_pts {len(crease_pts)}  seen3d {len(seen_idx)}")

    z = np.load(os.path.join(OUT, CLOUD[scene]))
    keep = (z["support"] >= 2) & z["surface_keep"] & (z["resid"] <= 1.0)
    P = z["P"][keep]
    res["n_cloud_keep"] = int(keep.sum())
    assert keep.sum() == BANKED_KEEP[scene], f"GATE FAIL cloud keep {keep.sum()} != {BANKED_KEEP[scene]}"
    print(f"pipeline cloud keep {keep.sum()} == banked {BANKED_KEEP[scene]}  OK")

    d3, _ = cKDTree(P).query(crease_pts[seen_idx], k=1, workers=-1)
    rec = d3 <= TOL[scene]
    recall = float(rec.mean())
    res["recall_3D"] = recall
    print(f"3D recall @ {TOL[scene]} = {recall:.4f}")
    if scene in BANKED_RECALL:
        assert abs(recall - BANKED_RECALL[scene]) < 5e-4, f"GATE FAIL recall {recall:.4f} != banked {BANKED_RECALL[scene]}"
        print(f"reproduces banked {BANKED_RECALL[scene]}  OK")
    miss_idx = seen_idx[~rec]
    res["n_miss3d"] = int(len(miss_idx)); res["miss_frac_of_seen"] = float(len(miss_idx) / len(seen_idx))
    print(f"miss-set: {len(miss_idx)} pts ({res['miss_frac_of_seen']:.4f} of seen)")

    # --- map cached crease points back to source mesh edges (exact reconstruction) ---
    m = trimesh.load(os.path.join(MESH_DIR, f"{scene}_new.obj"), process=True)
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate([g for g in m.geometry.values()])
    V = np.asarray(m.vertices, np.float64)
    ang = np.degrees(m.face_adjacency_angles)
    sel_mask = ang >= ANGLE
    sel_pairs = m.face_adjacency_edges[sel_mask]
    sel_faces = m.face_adjacency[sel_mask]
    sel_ang = ang[sel_mask]
    pts2, eid = sample_edges_with_ids(V, sel_pairs, DS)
    assert pts2.shape == crease_pts.shape and np.allclose(pts2, crease_pts, atol=1e-9), \
        "GATE FAIL: crease_pts reconstruction does not match frozen cache"
    print(f"crease_pts reconstruction matches cache exactly ({len(sel_pairs)} crease edges)  OK")

    miss_eid = eid[miss_idx]
    uniq_e, uniq_counts = np.unique(miss_eid, return_counts=True)
    res["n_miss_edges"] = int(len(uniq_e))
    print(f"missed points map to {len(uniq_e)} unique crease edges")

    # exact adjacency dihedral of the miss-set (banding, incl. lego tessellation band)
    miss_ang_pts = sel_ang[miss_eid]
    res["miss_exact_dihedral_bands_pts"] = {
        f"[{lo},{hi})": float(((miss_ang_pts >= lo) & (miss_ang_pts < hi)).mean()) for lo, hi in ANG_BANDS}
    res["miss_exact_dihedral_pcts"] = {p: float(np.percentile(miss_ang_pts, p)) for p in (5, 25, 50, 75, 95)}

    # --- at-scale dihedral per unique missed edge, all radii ---
    scale = {}
    for r in R_LIST:
        ds_deg, nsides = dihedral_at_scale(m, sel_pairs[uniq_e], sel_faces[uniq_e], r)
        scale[r] = ds_deg
        meas = np.isfinite(ds_deg)
        print(f"r={r}: measurable {meas.mean():.4f}  median at-scale dihedral {np.nanmedian(ds_deg):.2f} deg  ({time.time()-t0:.0f}s)")
    ds_p = scale[R_PRIMARY]

    # propagate per-edge class to missed points
    e2pos = {e: i for i, e in enumerate(uniq_e)}
    pt_ds = ds_p[np.searchsorted(uniq_e, miss_eid)]   # uniq_e sorted by np.unique
    cls_geom = pt_ds >= GEOM_MIN
    cls_flat = pt_ds < FLAT_MAX
    cls_band = np.isfinite(pt_ds) & ~cls_geom & ~cls_flat
    cls_unm = ~np.isfinite(pt_ds)
    n = len(miss_idx)
    g_pts = float(cls_geom.sum() / n)
    res["split_points"] = {"geometric": int(cls_geom.sum()), "decal_flat": int(cls_flat.sum()),
                           "band_10_20": int(cls_band.sum()), "unmeasurable": int(cls_unm.sum()), "total": n}
    eg = ds_p >= GEOM_MIN
    res["split_edges"] = {"geometric": int(eg.sum()), "decal_flat": int((ds_p < FLAT_MAX).sum()),
                          "band_10_20": int((np.isfinite(ds_p) & ~eg & ~(ds_p < FLAT_MAX)).sum()),
                          "unmeasurable": int((~np.isfinite(ds_p)).sum()), "total": len(uniq_e)}
    res["g_points"] = g_pts
    res["g_edges"] = float(eg.sum() / len(uniq_e))
    # sensitivity: g over radii x thresholds (flat bucket = <10 always reported alongside)
    res["sensitivity_g_points"] = {}
    for r in R_LIST:
        d = scale[r][np.searchsorted(uniq_e, miss_eid)]
        res["sensitivity_g_points"][str(r)] = {
            f">={thr}": float((d >= thr).sum() / n) for thr in (5, 10, 15, 20, 30)}
        res["sensitivity_g_points"][str(r)]["decal_flat<10"] = float((d < 10.0).sum() / n)
        res["sensitivity_g_points"][str(r)]["unmeasurable"] = float((~np.isfinite(d)).sum() / n)
    print(f"g (points, primary r={R_PRIMARY}, >= {GEOM_MIN} deg) = {g_pts:.4f}")
    print(f"decal/flat (<{FLAT_MAX} deg) = {res['split_points']['decal_flat']/n:.4f}   "
          f"band = {res['split_points']['band_10_20']/n:.4f}   unmeasurable = {res['split_points']['unmeasurable']/n:.4f}")

    # --- viz: missed creases colored geometric-vs-decal, on the TEST view with most misses ---
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        best_v, best_ct = None, -1
        miss_set = set(miss_idx.tolist())
        for v in TEST_VIEWS:
            ct = np.isin(gt[f"idx{v}"], miss_idx).sum()
            if ct > best_ct: best_v, best_ct = v, ct
        vi = gt[f"idx{best_v}"]; uv = gt[f"uv{best_v}"]
        inmiss = np.isin(vi, miss_idx)
        # class per visible point
        pos = np.searchsorted(miss_idx, vi[inmiss])  # miss_idx sorted? np unique -> seen_idx sorted, miss subset keeps order
        pt_class = np.full(len(vi), -1, np.int8)
        lookup = np.zeros(len(crease_pts), np.int8)  # 0 unknown; on miss pts: 1 geom 2 flat 3 band 4 unm
        lookup[miss_idx[cls_geom]] = 1; lookup[miss_idx[cls_flat]] = 2
        lookup[miss_idx[cls_band]] = 3; lookup[miss_idx[cls_unm]] = 4
        cls_v = lookup[vi]
        fig, ax = plt.subplots(figsize=(8, 8), dpi=110)
        ax.scatter(uv[cls_v == 0, 0], uv[cls_v == 0, 1], s=0.05, c="0.85", label="recovered/other")
        ax.scatter(uv[cls_v == 1, 0], uv[cls_v == 1, 1], s=0.3, c="tab:blue", label=f"missed GEOMETRIC (>={GEOM_MIN} at scale)")
        ax.scatter(uv[cls_v == 3, 0], uv[cls_v == 3, 1], s=0.3, c="tab:orange", label="missed band 10-20")
        ax.scatter(uv[cls_v == 2, 0], uv[cls_v == 2, 1], s=0.6, c="tab:red", label=f"missed DECAL/flat (<{FLAT_MAX})")
        ax.scatter(uv[cls_v == 4, 0], uv[cls_v == 4, 1], s=0.6, c="tab:purple", label="missed unmeasurable")
        ax.set_xlim(0, 800); ax.set_ylim(800, 0); ax.set_aspect("equal")
        ax.set_title(f"Experiment X {scene}: frozen-pipeline miss-set, TEST view {best_v}\n"
                     f"g={g_pts:.3f} (points, at-scale dihedral r={R_PRIMARY})")
        ax.legend(loc="lower right", fontsize=7, markerscale=8)
        fig.tight_layout()
        fig.savefig(os.path.join(OUT, f"retrainx_{scene}_missmap.png"))
        plt.close(fig)
        res["viz"] = f"out/retrainx_{scene}_missmap.png (view {best_v})"
        print(f"viz -> out/retrainx_{scene}_missmap.png (view {best_v}, {best_ct} missed pts visible)")
    except Exception as ex:
        res["viz_error"] = str(ex); print("viz failed:", ex)

    res["runtime_s"] = round(time.time() - t0, 1)
    with open(os.path.join(OUT, f"retrainx_{scene}.json"), "w") as f:
        json.dump(res, f, indent=1)
    return res


if __name__ == "__main__":
    scenes = sys.argv[1:] or ["lego", "chair"]
    allres = {s: run_scene(s) for s in scenes}
    print("\n=== X-DECISION (frozen rule, lego primary) ===")
    for s, r in allres.items():
        g = r["g_points"]
        verdict = "KILL-SIGNAL (g<0.25)" if g < 0.25 else ("PROCEED-TO-Y (g>0.40)" if g > 0.40 else "GRAY (0.25<=g<=0.40)")
        print(f"{s}: g={g:.4f} -> {verdict}")
