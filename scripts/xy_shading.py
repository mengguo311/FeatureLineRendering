"""EXPERIMENT X, decisive step — EVAL-ONLY: is each GT crease SHADING-DISCONTINUOUS?

*** EVAL / ANALYSIS ONLY.  Reads the GT .obj.  No method path touched. ***

WHY THIS IS THE RIGHT TEST
    3DGS is fit by a purely PHOTOMETRIC loss against the training renders.  A GT crease is
    reachable by ANY photometric method - the frozen post-hoc pipeline, or any retraining
    scheme whatsoever - only if it actually produces a discontinuity in those renders.
    Whether it does is not a matter of opinion or of thresholding a gradient: it is written
    into the asset.  The NeRF-synthetic images were rendered in Blender from these very .obj
    files, and the .obj records, per face corner, WHICH VERTEX NORMAL the renderer used.

    - If the two faces meeting at a crease edge reference the SAME vertex normal at both
      shared vertices, the shading normal is CONTINUOUS across that edge (Blender smooth
      shading, `s 1`).  The rendered image is C1 there.  There is NO edge in ANY view, in
      any lighting, at any resolution.  A 12-sided cylinder tessellating a lego stud is the
      canonical case: real 30 deg dihedral per facet, zero visible line.
    - If they reference DIFFERENT vertex normals, the shading normal STEPS across the edge
      (flat shading / split normals / sharp edge).  That is a visible line.

    So SMOOTH = information-theoretically unrecoverable, SPLIT = genuinely retrainable.
    This measures the renderer's own contract, not a proxy for it.

METHOD
    Parse the .obj at the polygon level (before triangulation), keeping per-corner (v, vn)
    indices and the active smoothing group.  Build the polygon edge -> faces map on raw v
    indices.  For each manifold edge classify SMOOTH vs SPLIT, and compute the true dihedral
    from the polygon face normals.  Then transfer the labels onto the mesh_oracle crease set
    by exact edge-midpoint KD match (mesh_oracle loads the same file with process=True, which
    merges coincident vertices but never moves them, so midpoints coincide to ~1e-12).
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
ANGLE = 30.0


def parse_obj(path):
    """-> V[nv,3], VN[nvn,3], faces list of (v_idx array, vn_idx array, smooth_group)."""
    V, VN = [], []
    fv, fvn, fs = [], [], []
    s = 0
    t0 = time.time()
    with open(path, "r") as fp:
        for line in fp:
            if line.startswith("v "):
                V.append(line[2:].split())
            elif line.startswith("vn "):
                VN.append(line[3:].split())
            elif line.startswith("f "):
                toks = line[2:].split()
                a, b = [], []
                for t in toks:
                    p = t.split("/")
                    a.append(int(p[0]))
                    b.append(int(p[2]) if len(p) > 2 and p[2] else 0)
                fv.append(a)
                fvn.append(b)
                fs.append(s)
            elif line.startswith("s "):
                w = line[2:].strip()
                s = 0 if w in ("off", "0") else int(w) if w.isdigit() else 1
    V = np.array(V, np.float64)
    VN = np.array(VN, np.float64) if VN else np.zeros((0, 3))
    print(f"  parsed {path}: v={len(V)} vn={len(VN)} f={len(fv)} ({time.time()-t0:.0f}s)",
          flush=True)
    return V, VN, fv, fvn, np.array(fs, np.int32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", required=True)
    args = ap.parse_args()
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    path = f"{MESH_DIR}/{args.scene}_new.obj"
    V, VN, fv, fvn, fs = parse_obj(path)

    # ---- polygon edge -> (face, corner-pair) map on RAW v indices -----------------------
    rows_e, rows_f, rows_vn0, rows_vn1 = [], [], [], []
    for fi, (a, b) in enumerate(zip(fv, fvn)):
        n = len(a)
        for i in range(n):
            j = (i + 1) % n
            u, w = a[i], a[j]
            rows_e.append((u, w) if u < w else (w, u))
            rows_f.append(fi)
            # vn indices at the two ENDPOINTS of this edge, ordered by (min v, max v)
            if u < w:
                rows_vn0.append(b[i]); rows_vn1.append(b[j])
            else:
                rows_vn0.append(b[j]); rows_vn1.append(b[i])
    E = np.array(rows_e, np.int64)
    FI = np.array(rows_f, np.int64)
    N0 = np.array(rows_vn0, np.int64)
    N1 = np.array(rows_vn1, np.int64)
    print(f"  half-edges: {len(E)} ({time.time()-t0:.0f}s)", flush=True)

    order = np.lexsort((E[:, 1], E[:, 0]))
    E, FI, N0, N1 = E[order], FI[order], N0[order], N1[order]
    same = (E[1:, 0] == E[:-1, 0]) & (E[1:, 1] == E[:-1, 1])
    # manifold edges = exactly 2 half-edges; take pairs where i and i+1 match and neither
    # extends to a third
    pair = np.where(same)[0]
    prev_ok = np.ones(len(pair), bool)
    prev_ok[1:] = pair[1:] != pair[:-1] + 1
    nxt_ok = np.ones(len(pair), bool)
    nxt_ok[:-1] = pair[:-1] + 1 != pair[1:]
    pair = pair[prev_ok & nxt_ok]
    i0, i1 = pair, pair + 1
    print(f"  manifold polygon edges: {len(pair)} ({time.time()-t0:.0f}s)", flush=True)

    # polygon face normals (Newell, robust for quads)
    fn = np.zeros((len(fv), 3))
    for fi, a in enumerate(fv):
        p = V[np.array(a) - 1]
        q = np.roll(p, -1, axis=0)
        fn[fi] = np.cross(p, q).sum(0)
    fn /= np.clip(np.linalg.norm(fn, axis=1, keepdims=True), 1e-15, None)

    n1, n2 = fn[FI[i0]], fn[FI[i1]]
    dih = np.degrees(np.arccos(np.clip((n1 * n2).sum(1), -1, 1)))
    a_v, b_v = E[i0, 0], E[i0, 1]
    mid = 0.5 * (V[a_v - 1] + V[b_v - 1])

    # ---- SMOOTH vs SPLIT: same vertex normal referenced on both sides, at BOTH endpoints --
    same_vn_idx = (N0[i0] == N0[i1]) & (N1[i0] == N1[i1])
    if len(VN):
        eq0 = np.all(np.isclose(VN[N0[i0] - 1], VN[N0[i1] - 1], atol=1e-6), axis=1)
        eq1 = np.all(np.isclose(VN[N1[i0] - 1], VN[N1[i1] - 1], atol=1e-6), axis=1)
        same_vn_val = eq0 & eq1
    else:
        same_vn_val = same_vn_idx
    smooth = same_vn_idx | same_vn_val          # shading normal continuous across the edge
    sgrp_same = fs[FI[i0]] == fs[FI[i1]]

    # ---- transfer onto the mesh_oracle crease set (process=True, merged verts) ------------
    m = trimesh.load(path, process=True)
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate([g for g in m.geometry.values()])
    MV = np.asarray(m.vertices, np.float64)
    adjE = np.asarray(m.face_adjacency_edges)
    tdeg = np.degrees(np.asarray(m.face_adjacency_angles))
    sel = np.where(tdeg >= ANGLE)[0]
    tmid = 0.5 * (MV[adjE[sel, 0]] + MV[adjE[sel, 1]])
    d, j = cKDTree(mid).query(tmid, k=1, workers=-1)
    matched = d < 1e-9
    print(f"  crease edges {len(sel)}: matched to a polygon edge {matched.mean()*100:.2f}% "
          f"(median match dist {np.median(d):.2e})", flush=True)

    lab = np.full(len(sel), -1, np.int8)         # -1 unmatched, 0 SPLIT(visible), 1 SMOOTH
    lab[matched] = smooth[j[matched]].astype(np.int8)
    np.savez_compressed(os.path.join(OUT, f"xy_shading_{args.scene}.npz"),
                        sel=sel.astype(np.int64), smooth=lab,
                        theta0=tdeg[sel].astype(np.float32),
                        matched=matched, match_dist=d.astype(np.float32))

    def band(lo, hi):
        b = matched & (tdeg[sel] >= lo) & (tdeg[sel] < hi)
        return {"n": int(b.sum()),
                "smooth_frac": round(float(lab[b].mean()), 4) if b.sum() else None}

    rep = {"scene": args.scene, "obj": path,
           "n_polygon_faces": len(fv), "n_vertex_normals": len(VN),
           "n_manifold_polygon_edges": int(len(pair)),
           "n_crease_edges_at_30deg": int(len(sel)),
           "matched_frac": round(float(matched.mean()), 4),
           "SMOOTH_frac_of_crease_edges": round(float(lab[matched].mean()), 4),
           "SPLIT_frac_of_crease_edges": round(float(1 - lab[matched].mean()), 4),
           "smoothing_group_agreement": round(float(sgrp_same.mean()), 4),
           "by_dihedral_band": {
               "exactly_30deg": band(29.9, 30.1), "30_44": band(30.1, 44.0),
               "44_60": band(44.0, 60.0), "60_90": band(60.0, 89.9),
               "exactly_90deg": band(89.9, 90.1), "gt_90": band(90.1, 181.0)},
           "all_polygon_edges_smooth_frac": round(float(smooth.mean()), 4),
           "polygon_edges_dihedral_ge30_smooth_frac":
               round(float(smooth[dih >= ANGLE].mean()), 4)}
    jp = os.path.join(OUT, f"xy_shading_{args.scene}.json")
    json.dump(rep, open(jp, "w"), indent=1)
    print(json.dumps(rep, indent=1))
    print(f"[done] {jp} ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
