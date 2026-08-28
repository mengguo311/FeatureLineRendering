#!/usr/bin/env python
"""CONDLAW-3-PRE — rho_flat_mesh, TESSELLATION-DEBIASED.  Mesh-only, no training.

WHY v2 EXISTS (a real defect found in v1, recorded rather than hidden).
v1 measured local normal dispersion over the FACE CENTROIDS inside a ball and required
n_min=5 of them.  Triangle density is not uniform over these meshes: flat panels are
tessellated with FEW LARGE triangles, curved relief with MANY SMALL ones.  So the
validity test ">=5 centroids in the ball" preferentially DELETES FLAT SURFACE, and does
so by a different amount per scene (valid samples at R=0.01: chair 6461/20000 = 32%,
lego 16019 = 80%, materials 18478 = 92%, mic 13429 = 67%, ship 11562 = 58%).
That inverted the anchors: v1 made chair (0.0045) look FLATTER-LESS than lego (0.0123),
contradicting the CONDLAW ground truth that chair's flat class is large and lego's empty.

FIX: decouple the neighbourhood from the tessellation.  Resample the surface into an
AREA-UNIFORM point cloud at a FIXED density D points per unit area, each point carrying
its source face's normal EXACTLY (no smoothing).  Neighbour count in a ball is then
proportional to the ball's SURFACE AREA and is independent of how the mesh was triangulated.
Because the cloud is area-uniform, an UNWEIGHTED scatter over cloud points already IS the
area-weighted scatter, so `normal_spread` is applied with unit weights by construction.

rho_flat_mesh(scene, R) = fraction of GT-mesh surface AREA whose local undirected-normal
dispersion within radius R is < 5 deg.

Also computes the CONDITIONAL scalar that actually matches what CONDLAW measured:
rho_flat_far = the same fraction, restricted to surface FAR from any GT crease
(> d_far), i.e. the mesh-only analogue of CONDLAW's distractor class ("a confident
non-crease locus"), since CONDLAW's binding quantity was flat-class MEMBERSHIP among
non-crease loci, not raw global area.

MESH-ONLY: no images, no 3DGS/2DGS, no rendering, no training.  Mesh read through the
same trimesh path scripts/diag2dgs.py uses for its GT-mesh arm; EVAL/label use only.
"""
import argparse, json, os, sys

import numpy as np
import trimesh
from scipy.spatial import cKDTree

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
if TIER1 not in sys.path:
    sys.path.insert(0, TIER1)
from src.mesh_oracle import MESH_DIR                     # EVAL ONLY

CAP = 400
SCALES = (0.01, 0.02, 0.04)


def normal_spread(N, W):
    """VERBATIM from scripts/diag2dgs.py:normal_spread."""
    S = (N * W[:, None]).T @ N / max(W.sum(), 1e-12)
    lam = np.linalg.eigvalsh(S)[-1]
    return float(np.degrees(np.arccos(np.sqrt(np.clip(lam, 0.0, 1.0)))))


def load_mesh(scene):
    m = trimesh.load(f"{MESH_DIR}/{scene}_new.obj", process=True)
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate([g for g in m.geometry.values()])
    return m


def crease_pts(m, angle_deg=30.0, ds=0.0015):
    """IDENTICAL to src/mesh_oracle.MeshOracle: edges with dihedral >= angle_deg, resampled."""
    V = np.asarray(m.vertices, np.float64)
    sel = m.face_adjacency_edges[m.face_adjacency_angles >= np.deg2rad(angle_deg)]
    if not len(sel):
        return np.zeros((0, 3)), sel, 0.0
    a, b = V[sel[:, 0]], V[sel[:, 1]]
    L = np.linalg.norm(b - a, axis=1)
    pts = []
    for i in range(len(a)):
        n = max(2, int(L[i] / ds) + 1)
        pts.append(a[i][None] + np.linspace(0, 1, n)[:, None] * (b[i] - a[i])[None])
    return np.concatenate(pts, 0), sel, float(L.sum())


def survey(scene, density, n_query, n_min, d_far_mult, seed=0):
    m = load_mesh(scene)
    area = float(np.asarray(m.area_faces).sum())
    ex = m.bounds[1] - m.bounds[0]
    diag = float(np.linalg.norm(ex))
    n_cloud = int(round(density * area))
    print(f"[{scene}] faces={len(m.faces)} area={area:.3f} diag={diag:.4f} "
          f"-> cloud {n_cloud} pts (density {density:g}/unit area)", flush=True)

    # area-uniform cloud; each point inherits its source face normal exactly (no smoothing)
    Pc, fid = trimesh.sample.sample_surface(m, n_cloud, seed=seed)
    Pc = np.asarray(Pc, np.float64)
    Nc = np.asarray(m.face_normals, np.float64)[fid]
    Pq, _ = trimesh.sample.sample_surface(m, n_query, seed=seed + 1)
    Pq = np.asarray(Pq, np.float64)

    tree = cKDTree(Pc)
    cp, _, clen = crease_pts(m)
    ctree = cKDTree(cp) if len(cp) else None
    dcre = ctree.query(Pq, workers=-1)[0] if ctree is not None else np.full(len(Pq), np.inf)

    out = {}
    for R in SCALES:
        exp_n = density * np.pi * R * R
        balls = tree.query_ball_point(Pq, R, workers=-1)
        v = np.full(len(Pq), np.nan)
        for i, b in enumerate(balls):
            if len(b) < n_min:
                continue
            b = np.asarray(b)
            if len(b) > CAP:
                rs = np.random.RandomState(seed + i)     # unbiased subsample of an
                b = b[rs.choice(len(b), CAP, replace=False)]   # area-uniform cloud
            v[i] = normal_spread(Nc[b], np.ones(len(b)))
        ok = np.isfinite(v)
        d_far = d_far_mult * R
        far = ok & (dcre > d_far)
        rec = {"R": float(R), "expected_neighbours": float(exp_n),
               "n_valid": int(ok.sum()), "n_query": int(len(Pq)),
               "valid_frac": float(ok.mean()),
               "median": float(np.median(v[ok])) if ok.any() else float("nan"),
               "rho_flat": float((v[ok] < 5.0).mean()) if ok.any() else float("nan"),
               "frac<10": float((v[ok] < 10.0).mean()) if ok.any() else float("nan"),
               "frac<20": float((v[ok] < 20.0).mean()) if ok.any() else float("nan"),
               "d_far": float(d_far), "n_far": int(far.sum()),
               "far_frac_of_surface": float(far.sum() / max(ok.sum(), 1)),
               "rho_flat_far": float((v[far] < 5.0).mean()) if far.any() else float("nan"),
               "far_frac<10": float((v[far] < 10.0).mean()) if far.any() else float("nan")}
        out[f"{R:g}"] = rec
        print(f"    R={R:<5g} exp_nbr={exp_n:6.1f} valid={rec['valid_frac']:.3f} "
              f"med={rec['median']:7.3f}  rho_flat={rec['rho_flat']:.6f}  "
              f"| far(d>{d_far:.3f}) n={rec['n_far']:5d} "
              f"rho_flat_far={rec['rho_flat_far']:.6f}", flush=True)
    res = {"n_faces": int(len(m.faces)), "surface_area": area, "bbox_diag": diag,
           "n_cloud": n_cloud, "density": density,
           "n_crease_pts": int(len(cp)), "crease_len_total": clen,
           "median_edge_scale": float(np.sqrt(np.median(m.area_faces))),
           "by_R": out}
    del m, Pc, Nc, tree
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", nargs="+",
                    default=["chair", "lego", "materials", "mic", "ship"])
    ap.add_argument("--density", type=float, default=63662.0,
                    help="cloud points per unit surface area; 63662 => ~20 expected "
                         "neighbours in a ball of R=0.01, identically for every scene")
    ap.add_argument("--n_query", type=int, default=20000)
    ap.add_argument("--n_min", type=int, default=5)
    ap.add_argument("--d_far_mult", type=float, default=1.5,
                    help="'far from crease' threshold as a multiple of R")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="out/condlaw3pre_rhoflat2.json")
    a = ap.parse_args()

    res = {s: survey(s, a.density, a.n_query, a.n_min, a.d_far_mult, a.seed)
           for s in a.scenes}
    json.dump({"meta": {"density": a.density, "n_query": a.n_query, "n_min": a.n_min,
                        "d_far_mult": a.d_far_mult, "seed": a.seed, "cap": CAP,
                        "scales": list(SCALES), "mesh_dir": MESH_DIR,
                        "note": "tessellation-debiased: neighbourhoods are drawn from an "
                                "AREA-UNIFORM resampling of the surface, not from face "
                                "centroids, so validity does not correlate with flatness"},
               "scenes": res}, open(a.out, "w"), indent=1, default=float)
    print(f"\nwrote {a.out}")
