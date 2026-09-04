"""EXPERIMENT Y, §Y.8 — did retraining improve the geometry the extractor actually consumes?

*** EVAL ONLY.  Distance to the GT mesh surface is a SCORE, not a method input. ***

The 3DGS reaches the frozen extractor as the depth prior for its per-ray depth search
(tri_edges.build brackets +-log1p(rho) around the 3DGS median depth).  So the quantity that a
line-favourable retrain would have to improve is how close the resulting triangulated
candidates land to the true surface.  This measures exactly that, with exact point-to-triangle
distance (the CAD part has 72 triangles, so brute force is exact and fast; trimesh's
proximity path needs rtree, which is not installed in this env).
"""
import json
import os

import numpy as np
import trimesh

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
MESH = os.path.expanduser("~/3dgs_line/bcr/meshes/NeRF_Mesh/cadpart_new.obj")
CONDS = [("cadpartA", "A_vanilla"), ("cadpartB", "B_ORACLE"), ("cadpartH", "Bp_honest")]


def pt_tri_dist(P, tri):
    best = np.full(len(P), np.inf)
    for a, b, c in tri:
        ab, ac, ap = b - a, c - a, P - a
        d1, d2 = ap @ ab, ap @ ac
        bp = P - b
        d3, d4 = bp @ ab, bp @ ac
        cp = P - c
        d5, d6 = cp @ ab, cp @ ac
        va, vb, vc = d3 * d6 - d5 * d4, d5 * d2 - d1 * d6, d1 * d4 - d3 * d2
        den = va + vb + vc
        inside = (va >= 0) & (vb >= 0) & (vc >= 0) & (np.abs(den) > 1e-20)
        w = np.zeros((len(P), 3))
        w[inside, 0] = va[inside] / den[inside]
        w[inside, 1] = vb[inside] / den[inside]
        w[inside, 2] = vc[inside] / den[inside]
        q = np.where(inside[:, None], w @ np.stack([a, b, c]), 0.0)
        d = np.where(inside, np.linalg.norm(P - q, axis=1), np.inf)
        for p0, p1 in ((a, b), (b, c), (c, a)):
            e = p1 - p0
            L = max(float(e @ e), 1e-20)
            t = np.clip(((P - p0) @ e) / L, 0, 1)
            d = np.minimum(d, np.linalg.norm(P - (p0 + t[:, None] * e[None, :]), axis=1))
        best = np.minimum(best, d)
    return best


def main():
    m = trimesh.load(MESH, process=True)
    tri = np.asarray(m.vertices)[np.asarray(m.faces)]
    px = 4.031128875572954 / (0.5 * 800 / np.tan(0.5 * 0.6911112070083618))
    res = {"px_world": px, "n_faces": int(len(tri)),
           "note": ("exact distance from every RAW triangulated candidate to the GT mesh "
                    "SURFACE: the quantity a better depth prior would have to improve")}
    for scene, lab in CONDS:
        P = np.load(os.path.join(TIER1, "out",
                                 f"dexprimary_p1b_cloud_{scene}_ref40.npz"))["P"]
        d = pt_tri_dist(P, tri)
        res[lab] = {"n": int(len(P)),
                    "surface_dist_p50": round(float(np.median(d)), 6),
                    "surface_dist_p90": round(float(np.percentile(d, 90)), 6),
                    "frac_within_1px": round(float((d < px).mean()), 4),
                    "frac_within_0.5px": round(float((d < 0.5 * px).mean()), 4)}
        print(lab, res[lab], flush=True)
    json.dump(res, open(os.path.join(TIER1, "out", "xy", "xy_depthquality.json"), "w"),
              indent=1)
    print("wrote out/xy/xy_depthquality.json")


if __name__ == "__main__":
    main()
