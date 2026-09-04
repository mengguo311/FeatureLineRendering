"""EXPERIMENT X, step 1 — EVAL-ONLY mesh geometry characterisation of the GT crease set.

*** EVAL / ANALYSIS ONLY.  Reads the GT mesh.  Defines NO method, touches NO method path. ***

WHY
    tier1/src/mesh_oracle.py DEFINES the GT crease set as the mesh edges whose face-adjacency
    (dihedral) angle is >= 30 deg.  Experiment X asks us to split the pipeline's MISS-SET into
    (a) geometric creases (dihedral above threshold -> retrainable) and (b) decals (dihedral ~0
    on a flat region -> not retrainable).  Applied literally to THIS crease set that split is a
    TAUTOLOGY: every GT crease point sits on a >=30 deg edge by construction, so g == 1.000 for
    every scene, every miss-set, with no measurement performed.  That is reported, not hidden.

    The non-vacuous question is whether a >=30 deg *single-edge* dihedral is a real feature line
    AT THE SCALE THE CAMERA SEES.  It need not be: a smooth curved surface tessellated into
    facets has a real per-edge dihedral everywhere.  A 12-sided cylinder has EXACTLY 360/12 = 30
    deg between adjacent side facets, so the 30 deg oracle threshold admits every lego stud
    barrel as "crease".  This module measures, per crease edge, whether the normal discontinuity
    is SCALE-STABLE (two locally planar sheets meeting -> a real line) or whether the normals
    FAN CONTINUOUSLY (tessellated curvature -> no line exists in the rendered image at all).

MEASUREMENT (per crease edge, at two physical radii r_fine < r_coarse)
    Gather the K nearest face centroids; keep those within r.  Face normals are consistently
    wound, so no sign fixing is needed.  Seed a 2-means on the sphere with the edge's own two
    face normals, run 2 Lloyd iterations, then report
        theta_r   = angle between the two (area-weighted) cluster mean normals
        spread_r  = area-weighted RMS angle of each normal to its own cluster mean  (PLANARITY:
                    ~0 <=> two locally FLAT sheets; large <=> the "sheets" are themselves curved)
        ext_r     = max angle of any local normal to the edge's own first face normal
                    (total angular extent swept inside radius r)
    A real dihedral crease saturates: ext_r stops growing with r and spread_r stays ~0.
    Tessellated curvature does not: ext_r grows ~linearly in r and spread_r is large.

CALIBRATION (built in, not assumed)
    lego carries its own positive and negative controls: 38.5k edges at EXACTLY 90 deg (true box
    corners) and 214k at EXACTLY 30 deg (suspected 12-gon cylinder tessellation).  The separation
    of the two on spread_r / growth is reported so the operator is validated on the mesh itself
    before it is used to classify anything.
"""
import argparse
import json
import os
import time

import numpy as np
import trimesh
from scipy.spatial import cKDTree

MESH_DIR = os.path.expanduser("~/3dgs_line/bcr/meshes/NeRF_Mesh")
OUT = os.path.expanduser("~/3dgs_line/tier1/out/xy")

# NeRF-synthetic: 800px, camera_angle_x ~0.6911 rad, orbit radius ~4.03 -> 1 px ~ 0.0036 world.
# Fixed here, but recomputed from the real cameras by xy_missset.py and cross-checked.
PX_WORLD = 0.0036


def unit(a, axis=-1):
    return a / np.clip(np.linalg.norm(a, axis=axis, keepdims=True), 1e-12, None)


def ang(a, b):
    """angle in degrees between unit vectors, broadcasting."""
    return np.degrees(np.arccos(np.clip((a * b).sum(-1), -1.0, 1.0)))


def two_means(nrm, w, seed1, seed2, n_iter=2):
    """Spherical 2-means over local normals.
    nrm[E,K,3] normals, w[E,K] area weights (0 for masked-out), seeds [E,3]."""
    m1, m2 = seed1.copy(), seed2.copy()
    for _ in range(n_iter):
        d1 = ang(nrm, m1[:, None, :])
        d2 = ang(nrm, m2[:, None, :])
        c = (d2 < d1)                                  # True -> cluster 2
        for lab, out in ((False, "m1"), (True, "m2")):
            ww = (w * (c == lab)).astype(np.float64)
            s = (nrm * ww[..., None]).sum(1)
            n = np.linalg.norm(s, axis=-1, keepdims=True)
            good = n[:, 0] > 1e-9
            newm = np.where(good[:, None], s / np.clip(n, 1e-12, None),
                            m1 if out == "m1" else m2)
            if out == "m1":
                m1 = newm
            else:
                m2 = newm
    d1 = ang(nrm, m1[:, None, :])
    d2 = ang(nrm, m2[:, None, :])
    c = (d2 < d1)
    dmin = np.minimum(d1, d2)
    wsum = np.clip(w.sum(1), 1e-12, None)
    spread = np.sqrt((w * dmin ** 2).sum(1) / wsum)     # area-weighted RMS residual
    theta = ang(m1, m2)
    return theta, spread, c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", required=True)
    ap.add_argument("--angle_deg", type=float, default=30.0)
    ap.add_argument("--r_fine_px", type=float, default=2.0)
    ap.add_argument("--r_coarse_px", type=float, default=6.0)
    ap.add_argument("--px_world", type=float, default=PX_WORLD)
    ap.add_argument("--K", type=int, default=192)
    ap.add_argument("--chunk", type=int, default=20000)
    ap.add_argument("--mesh_dir", default=MESH_DIR)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    r_f = args.r_fine_px * args.px_world
    r_c = args.r_coarse_px * args.px_world
    t0 = time.time()
    m = trimesh.load(f"{args.mesh_dir}/{args.scene}_new.obj", process=True)
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate([g for g in m.geometry.values()])
    V = np.asarray(m.vertices, np.float64)
    FN = np.asarray(m.face_normals, np.float64)
    FA = np.asarray(m.area_faces, np.float64)
    FC = np.asarray(m.triangles_center, np.float64)
    adj = np.asarray(m.face_adjacency)                       # [P,2] face pairs
    adjE = np.asarray(m.face_adjacency_edges)                # [P,2] vertex pairs
    deg = np.degrees(np.asarray(m.face_adjacency_angles))
    print(f"[{args.scene}] V={len(V)} F={len(FN)} adj={len(deg)} load={time.time()-t0:.0f}s "
          f"r_fine={r_f:.5f} r_coarse={r_c:.5f} (px={args.px_world})", flush=True)

    sel = np.where(deg >= args.angle_deg)[0]
    A = V[adjE[sel, 0]]
    B = V[adjE[sel, 1]]
    mid = 0.5 * (A + B)
    elen = np.linalg.norm(B - A, axis=1)
    theta0 = deg[sel]
    f1, f2 = adj[sel, 0], adj[sel, 1]
    print(f"[{args.scene}] crease edges@{args.angle_deg:.0f} = {len(sel)}  "
          f"edge_len med={np.median(elen):.5f} p95={np.percentile(elen,95):.5f}", flush=True)

    tree = cKDTree(FC)
    E = len(sel)
    res = {k: np.zeros(E, np.float32) for k in
           ("theta_f", "spread_f", "ext_f", "theta_c", "spread_c", "ext_c",
            "rK", "nf", "nc")}
    for s in range(0, E, args.chunk):
        e = slice(s, min(s + args.chunk, E))
        d, idx = tree.query(mid[e], k=args.K, workers=-1)
        nrm = FN[idx]                                        # [c,K,3]
        area = FA[idx]
        n_ref = FN[f1[e]]
        seed2 = FN[f2[e]]
        res["rK"][e] = d[:, -1]
        for tag, r in (("f", r_f), ("c", r_c)):
            msk = (d <= r)
            msk[:, 0] = True                                 # always keep nearest
            w = area * msk
            th, sp, _ = two_means(nrm, w, n_ref.copy(), seed2.copy())
            a_ref = ang(nrm, n_ref[:, None, :])
            ext = np.where(msk, a_ref, -1.0).max(1)
            res[f"theta_{tag}"][e] = th
            res[f"spread_{tag}"][e] = sp
            res[f"ext_{tag}"][e] = ext
            res[("nf" if tag == "f" else "nc")][e] = msk.sum(1)
        if s % (args.chunk * 5) == 0:
            print(f"  ...{s}/{E} ({time.time()-t0:.0f}s)", flush=True)

    growth = res["ext_c"] - res["ext_f"]
    out = dict(theta0=theta0.astype(np.float32), elen=elen.astype(np.float32),
               mid=mid.astype(np.float32), edge_idx=sel.astype(np.int64),
               growth=growth.astype(np.float32),
               **{k: v for k, v in res.items()})
    op = args.out or os.path.join(OUT, f"xy_meshgeom_{args.scene}.npz")
    os.makedirs(os.path.dirname(op), exist_ok=True)
    np.savez_compressed(op, **out)

    # ---- CALIBRATION on the mesh's own controls -------------------------------------
    def stats(mask, name):
        if mask.sum() == 0:
            return {"name": name, "n": 0}
        q = lambda a: [round(float(np.percentile(a[mask], p)), 3) for p in (25, 50, 75, 90)]
        return {"name": name, "n": int(mask.sum()),
                "spread_fine_p25_50_75_90": q(res["spread_f"]),
                "spread_coarse_p25_50_75_90": q(res["spread_c"]),
                "ext_fine_p25_50_75_90": q(res["ext_f"]),
                "ext_coarse_p25_50_75_90": q(res["ext_c"]),
                "growth_p25_50_75_90": q(growth),
                "n_faces_fine_median": float(np.median(res["nf"][mask])),
                "n_faces_coarse_median": float(np.median(res["nc"][mask])),
                "rK_median": float(np.median(res["rK"][mask]))}

    ctrl = [stats((theta0 >= 89.9) & (theta0 < 90.1), "CONTROL+ exactly 90deg (box corner)"),
            stats((theta0 >= 29.9) & (theta0 < 30.1), "CONTROL? exactly 30deg (susp. 12-gon cyl)"),
            stats((theta0 >= 44.0) & (theta0 < 89.9), "mid-band 44-90deg"),
            stats(np.ones(E, bool), "ALL crease edges")]
    rep = {"scene": args.scene, "angle_deg": args.angle_deg,
           "r_fine_world": r_f, "r_coarse_world": r_c, "px_world": args.px_world,
           "K": args.K, "n_crease_edges": int(E),
           "truncation_frac_rK_lt_r_coarse": float((res["rK"] < r_c).mean()),
           "controls": ctrl, "npz": op}
    rp = op.replace(".npz", "_calib.json")
    json.dump(rep, open(rp, "w"), indent=1)
    print(json.dumps(rep, indent=1))
    print(f"[done] {op}  ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
