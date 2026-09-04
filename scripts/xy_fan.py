"""EXPERIMENT X mechanism — EVAL-ONLY: is each GT "crease" an isolated feature line, or one
facet boundary of a TESSELLATED CURVED SURFACE?

*** EVAL / ANALYSIS ONLY.  Reads the GT mesh.  No method path touched. ***

THE PROBLEM
    src/mesh_oracle.py calls every mesh edge with dihedral >= 30 deg a GT crease.  A smooth
    curved surface approximated by flat facets has a real dihedral at EVERY facet boundary.
    A cylinder tessellated into 12 sides has exactly 360/12 = 30.0 deg between adjacent side
    facets -- landing precisely on the oracle's threshold.  lego is built from such cylinders
    (every stud, pin and axle barrel), and 43% of its visible GT crease set sits in a spike at
    exactly 30.0 deg.  Those are not feature lines: the surface they lie on is round, and a
    line renderer should draw its silhouette, not 12 longitudinal stripes down every stud.

THE TEST — "does the turning continue about the same axis?"
    Decompose the mesh into maximal LOCALLY-PLANAR PATCHES (connected components of faces
    joined across sub-3-deg edges; this absorbs the arbitrary quad-diagonal triangulation).
    Every GT crease edge separates two patches P1, P2 with unit normals n1, n2.  Write the
    turn from Pa to Pb as its rotation axis  cross(n_a, n_b) normalised.

    Walk one patch further out.  If P1 has ANOTHER neighbour P0 such that
        (i)  the turn P0->P1 has the SAME magnitude as the turn P1->P2  (within tol), and
        (ii) the two turn axes are PARALLEL and same-sense,
    then P0, P1, P2 are consecutive facets of one surface rotating steadily about a fixed
    axis -- i.e. a tessellated cylinder/cone, not a crease.  An isolated crease fails (ii):
    a box corner's other edges turn about different axes entirely.

    A crease is called FAN if the turn continues on either side, ISOLATED otherwise.

WHAT THIS BUYS
    It is a statement about the GEOMETRY ALONE, derived from the same mesh the oracle uses.
    It needs no lighting model, no threshold on an image, and no assumption about how the
    asset was shaded -- all of which we tried first and had to discard (an earlier attempt to
    read Blender's smoothing groups out of the .obj failed because lego_new.obj was re-exported
    with fully averaged vertex normals, which report every 90-deg box corner as "smooth").
"""
import argparse
import json
import os
import time

import numpy as np
import trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

MESH_DIR = os.path.expanduser("~/3dgs_line/bcr/meshes/NeRF_Mesh")
OUT = os.path.expanduser("~/3dgs_line/tier1/out/xy")
ANGLE, FLAT_DEG = 30.0, 3.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", required=True)
    ap.add_argument("--tol_deg", type=float, default=6.0, help="turn-magnitude match tolerance")
    ap.add_argument("--cos_thr", type=float, default=0.95, help="axis-parallel threshold")
    ap.add_argument("--max_deg", type=int, default=256, help="cap on patch boundary degree")
    args = ap.parse_args()
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    m = trimesh.load(f"{MESH_DIR}/{args.scene}_new.obj", process=True)
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate([g for g in m.geometry.values()])
    FN = np.asarray(m.face_normals, np.float64)
    FA = np.asarray(m.area_faces, np.float64)
    adj = np.asarray(m.face_adjacency)
    deg = np.degrees(np.asarray(m.face_adjacency_angles))
    F = len(FN)

    flat = deg < FLAT_DEG
    G = coo_matrix((np.ones(int(flat.sum()), np.int8), (adj[flat, 0], adj[flat, 1])),
                   shape=(F, F))
    npatch, lab = connected_components(G, directed=False)
    PN = np.zeros((npatch, 3))
    np.add.at(PN, lab, FN * FA[:, None])
    PN /= np.clip(np.linalg.norm(PN, axis=1, keepdims=True), 1e-12, None)
    parea = np.bincount(lab, weights=FA, minlength=npatch)
    print(f"[{args.scene}] F={F} patches={npatch} ({time.time()-t0:.0f}s)", flush=True)

    # patch-boundary edges (both directions), carrying the crease-edge id where applicable
    b = ~flat
    pa, pb = lab[adj[b, 0]], lab[adj[b, 1]]
    keep = pa != pb
    pa, pb = pa[keep], pb[keep]
    bdeg = deg[b][keep]
    src = np.where(b)[0][keep]                                  # adjacency index
    C = np.concatenate([np.stack([pa, pb], 1), np.stack([pb, pa], 1)], 0)
    Cd = np.concatenate([bdeg, bdeg])
    Cs = np.concatenate([src, src])
    o = np.argsort(C[:, 0], kind="stable")
    C, Cd, Cs = C[o], Cd[o], Cs[o]
    cnt = np.bincount(C[:, 0], minlength=npatch)
    ptr = np.concatenate([[0], np.cumsum(cnt)])
    print(f"[{args.scene}] patch-boundary half-edges={len(C)}  "
          f"max patch degree={cnt.max()} median={np.median(cnt[cnt>0]):.0f}", flush=True)

    sel = np.where(deg >= ANGLE)[0]
    adj_pos = -np.ones(len(deg), np.int64)                       # adjacency id -> crease id
    adj_pos[sel] = np.arange(len(sel))
    fan = np.zeros(len(sel), bool)
    both = np.zeros(len(sel), bool)
    nfan_side = np.zeros(len(sel), np.int8)
    rng = np.random.default_rng(0)

    for p in range(npatch):
        s, e = ptr[p], ptr[p + 1]
        if e - s < 2:
            continue
        nb = C[s:e, 1]
        dd = Cd[s:e]
        ss = Cs[s:e]
        if e - s > args.max_deg:
            pick = rng.choice(e - s, size=args.max_deg, replace=False)
            nb, dd, ss = nb[pick], dd[pick], ss[pick]
        ax = np.cross(PN[p][None, :], PN[nb])                    # cross_out(p, nb)
        nrm = np.linalg.norm(ax, axis=1, keepdims=True)
        ax = ax / np.clip(nrm, 1e-12, None)
        ok = nrm[:, 0] > 1e-9
        # pairwise: neighbour j continues the fan through neighbour i
        dot = ax @ ax.T
        dmatch = np.abs(dd[:, None] - dd[None, :]) <= args.tol_deg
        cont = dmatch & (dot <= -args.cos_thr) & ok[:, None] & ok[None, :]
        np.fill_diagonal(cont, False)
        has = cont.any(1)
        cid = adj_pos[ss]
        good = (cid >= 0) & has
        if good.any():
            g = cid[good]
            nfan_side[g] += 1

    fan = nfan_side >= 1
    both = nfan_side >= 2
    theta0 = deg[sel]
    a1 = parea[lab[adj[sel, 0]]]
    a2 = parea[lab[adj[sel, 1]]]
    np.savez_compressed(os.path.join(OUT, f"xy_fan_{args.scene}.npz"),
                        sel=sel, fan=fan, both=both, nfan_side=nfan_side,
                        theta0=theta0.astype(np.float32),
                        min_patch_area=np.minimum(a1, a2).astype(np.float32))

    def band(lo, hi, nm):
        bb = (theta0 >= lo) & (theta0 < hi)
        return {"band": nm, "n": int(bb.sum()),
                "frac_of_crease_edges": round(float(bb.mean()), 4),
                "FAN_frac": round(float(fan[bb].mean()), 4) if bb.sum() else None,
                "FAN_both_sides_frac": round(float(both[bb].mean()), 4) if bb.sum() else None}

    rep = {"scene": args.scene, "n_faces": F, "n_patches": int(npatch),
           "n_crease_edges": int(len(sel)),
           "tol_deg": args.tol_deg, "cos_thr": args.cos_thr,
           "FAN_frac_all_creases": round(float(fan.mean()), 4),
           "FAN_both_sides_frac_all": round(float(both.mean()), 4),
           "ISOLATED_frac_all_creases": round(float(1 - fan.mean()), 4),
           "by_band": [band(29.9, 30.1, "EXACTLY 30 deg"), band(30.1, 44.0, "30-44"),
                       band(44.0, 60.0, "44-60"), band(60.0, 89.9, "60-90"),
                       band(89.9, 90.1, "EXACTLY 90 deg (box corner)"),
                       band(90.1, 181.0, ">90")]}
    jp = os.path.join(OUT, f"xy_fan_{args.scene}.json")
    json.dump(rep, open(jp, "w"), indent=1)
    print(json.dumps(rep, indent=1))
    print(f"[done] {jp} ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
