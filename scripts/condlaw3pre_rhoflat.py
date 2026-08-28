#!/usr/bin/env python
"""CONDLAW-3-PRE — a-priori, IMAGE-FREE rho_flat_mesh survey over the GT meshes.

MESH-ONLY.  No 2DGS, no 3DGS, no training, no rendering, no images.  The mesh is read
through the same path scripts/diag2dgs.py uses for its GT-mesh arm (trimesh load of
MESH_DIR/<scene>_new.obj), i.e. EVAL/label use only.  Nothing here enters a method path.

rho_flat_mesh(scene, R) = fraction of GT-mesh SURFACE AREA whose local undirected-normal
dispersion within a ball of radius R is < 5 degrees.

  - area fraction is realised by AREA-UNIFORM surface sampling (trimesh.sample.sample_surface),
    so a plain count fraction over the samples IS an area fraction.
  - the dispersion statistic is `normal_spread` COPIED VERBATIM from scripts/diag2dgs.py:
    arccos(sqrt(lambda_1)) of the area-weighted scatter sum_j w_j n_j n_j^T, in degrees.
    Flat patch -> 0.  This is diag2dgs's side-split-free `spread`, the statistic whose
    lego value CONDLAW reported as the 0.32 deg crease-vs-decal gap.
  - the same cap=400 nearest-in-ball truncation diag2dgs uses on the 2.03M-face mesh arm.

VALIDATION.  out/diag2dgs_lego_surface_flatness.json is the pre-existing reference
(lego: n 18572 / median 38.384 / frac<5 0.0068921 at R=0.01).  --validate reproduces it
before any new scene is trusted, exactly as CONDLAW re-proved its chair harness first.
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


def flatness(m, R_list, n_samp=20000, n_min=5, seed=0):
    """Per-radius dispersion stats over area-uniform surface samples.

    Reported under BOTH normal weightings, because the archived reference
    out/diag2dgs_lego_surface_flatness.json was written by a script that is no longer in
    the repo and is not byte-reproducible from it:
      area  - weight each face normal by its area.  PRIMARY: the spec asks for a fraction
              of surface AREA, and this is diag2dgs.normal_spread's own convention.
      unit  - weight every face normal equally.  Reported because it reproduces the
              reference's frac<20 (0.0358 vs 0.0365) and its tight frac<5/frac<10 shape,
              so it is the likelier archived convention.
    The SELECTION and the pre-registered MONOTONICITY claim are only trusted if the scene
    ranking is identical under both, which is checked in the results table."""
    mu = np.asarray(m.triangles_center, np.float64)
    nn = np.asarray(m.face_normals, np.float64)
    w = np.asarray(m.area_faces, np.float64)
    rs = np.random.RandomState(seed)
    P, _ = trimesh.sample.sample_surface(m, n_samp, seed=seed) \
        if "seed" in trimesh.sample.sample_surface.__code__.co_varnames \
        else trimesh.sample.sample_surface(m, n_samp)
    P = np.asarray(P, np.float64)
    tree = cKDTree(mu)
    out = {}
    for R in R_list:
        balls = tree.query_ball_point(P, R, workers=-1)
        vals = {"area": np.full(len(P), np.nan), "unit": np.full(len(P), np.nan)}
        for i, b in enumerate(balls):
            if len(b) < n_min:
                continue
            b = np.asarray(b)
            if len(b) > CAP:
                dd = np.linalg.norm(mu[b] - P[i], axis=1)
                b = b[np.argsort(dd, kind="stable")[:CAP]]
            vals["area"][i] = normal_spread(nn[b], w[b])
            vals["unit"][i] = normal_spread(nn[b], np.ones(len(b)))
        rec = {"R": float(R), "n_samp": int(len(P))}
        for wname in ("area", "unit"):
            v = vals[wname][np.isfinite(vals[wname])]
            rec[wname] = {
                "n": int(len(v)),
                "median": float(np.median(v)) if len(v) else float("nan"),
                "frac<5": float((v < 5.0).mean()) if len(v) else float("nan"),
                "frac<10": float((v < 10.0).mean()) if len(v) else float("nan"),
                "frac<20": float((v < 20.0).mean()) if len(v) else float("nan"),
            }
        out[f"{R:g}"] = rec
        for wname in ("area", "unit"):
            r = rec[wname]
            print(f"    R={R:<9g} [{wname:4s}] n={r['n']:6d}  median={r['median']:7.3f}  "
                  f"frac<5={r['frac<5']:.6f}  frac<10={r['frac<10']:.6f}  "
                  f"frac<20={r['frac<20']:.6f}", flush=True)
    return out


def crease_stats(m, angle_deg=30.0, ds=0.0015):
    """GT crease loci, IDENTICAL definition to src/mesh_oracle.MeshOracle.__init__:
    mesh edges whose face-adjacency dihedral >= angle_deg, resampled at spacing ds."""
    V = np.asarray(m.vertices, np.float64)
    sel = m.face_adjacency_edges[m.face_adjacency_angles >= np.deg2rad(angle_deg)]
    a, b = V[sel[:, 0]], V[sel[:, 1]]
    L = np.linalg.norm(b - a, axis=1)
    n_pts = int(np.sum(np.maximum(2, (L / ds).astype(int) + 1)))
    return {"n_crease_edges": int(len(sel)), "crease_len_total": float(L.sum()),
            "n_crease_pts": n_pts, "angle_deg": angle_deg, "ds": ds}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", nargs="+",
                    default=["chair", "lego", "materials", "mic", "ship"])
    ap.add_argument("--n_samp", type=int, default=20000)
    ap.add_argument("--n_min", type=int, default=5)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--norm_frac", type=float, default=0.0035,
                    help="scale-normalised radius as a fraction of the bbox diagonal "
                         "(0.0035 * lego diag 2.944 = 0.0103 ~ the absolute 0.01)")
    ap.add_argument("--out", default="out/condlaw3pre_rhoflat.json")
    a = ap.parse_args()

    res = {}
    for s in a.scenes:
        print(f"\n[{s}] loading mesh ...", flush=True)
        m = load_mesh(s)
        ex = m.bounds[1] - m.bounds[0]
        diag = float(np.linalg.norm(ex))
        area = float(np.asarray(m.area_faces).sum())
        Rn = a.norm_frac * diag
        print(f"  faces={len(m.faces)}  diag={diag:.4f}  area={area:.3f}  "
              f"median_edge_scale={np.sqrt(np.median(m.area_faces)):.5f}  R_norm={Rn:.5f}",
              flush=True)
        print("  absolute radii:", flush=True)
        fl = flatness(m, SCALES, a.n_samp, a.n_min, a.seed)
        print("  scale-normalised radius:", flush=True)
        fln = flatness(m, [Rn], a.n_samp, a.n_min, a.seed)
        cs = crease_stats(m)
        res[s] = {"n_faces": int(len(m.faces)), "bbox_extent": ex.tolist(),
                  "bbox_diag": diag, "surface_area": area,
                  "median_edge_scale": float(np.sqrt(np.median(m.area_faces))),
                  "flatness_absR": fl, "flatness_normR": fln,
                  "R_norm": float(Rn), "norm_frac": a.norm_frac,
                  "crease": cs}
        print(f"  crease: {cs['n_crease_edges']} edges, total len {cs['crease_len_total']:.3f}, "
              f"{cs['n_crease_pts']} sampled pts", flush=True)
        del m

    json.dump({"meta": {"n_samp": a.n_samp, "n_min": a.n_min, "seed": a.seed,
                        "cap": CAP, "scales_abs": list(SCALES),
                        "norm_frac": a.norm_frac, "mesh_dir": MESH_DIR,
                        "spread_def": "arccos(sqrt(lambda1)) of area-weighted normal "
                                      "scatter, deg; verbatim diag2dgs.normal_spread"},
               "scenes": res}, open(a.out, "w"), indent=1, default=float)
    print(f"\nwrote {a.out}")
