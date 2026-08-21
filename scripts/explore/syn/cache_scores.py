"""Cache every family's compute() (+ key variants) on a scene, plus oracle labels.
EVAL-SIDE script (imports harness which imports the oracle) -- for analysis only.
"""
import os, sys, time, argparse
import numpy as np

sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts/explore"))
from tune_lib import Harness, structure_tensor, nms_along_e1
from src import visibility

OUT = os.path.expanduser("~/3dgs_line/tier1/scripts/explore/syn")


def build(scene):
    h = Harness(scene)
    st = structure_tensor(h.X, h.N, 8)
    cand = np.where(st["s_crease"] > 0.05)[0]
    sel = nms_along_e1(h.X, cand, st["s_crease"], st["e1"], st["knn"])
    return h, st, sel


def labels(h, sel):
    """EVAL ONLY: per-seed 'within 2.5px of GT crease in >=1 view' + visible-in>=1."""
    P = h.X[sel]
    pos = np.zeros(len(sel), bool)
    visany = np.zeros(len(sel), bool)
    dmin = np.full(len(sel), np.inf)
    for v in h.views:
        vis, uv, _ = visibility.visible_mask(P, h.cams[v], h.gbufs[v]["depth"])
        u = np.clip(np.round(uv[:, 0]).astype(int), 0, 799)
        vv = np.clip(np.round(uv[:, 1]).astype(int), 0, 799)
        _, _, cdt = h.crease[v]
        d = cdt[vv, u]
        visany |= vis
        pos |= vis & (d <= 2.5)
        dmin = np.where(vis, np.minimum(dmin, d), dmin)
    return pos, visany, dmin


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="chair")
    ap.add_argument("--fams", default="pool,geom,neigh,gline,dt,view")
    a = ap.parse_args()
    t0 = time.time()
    h, st, sel = build(a.scene)
    print(f"[{a.scene}] pool {len(sel)} seeds, build {time.time()-t0:.1f}s", flush=True)
    P = h.X[sel]
    print("baseline", h.evaluate(P), flush=True)

    d = {}
    pos, visany, dmin = labels(h, sel)
    d["lab_pos"] = pos; d["lab_vis"] = visany; d["lab_dmin"] = dmin
    d["sel"] = sel

    fams = a.fams.split(",")
    jobs = {
        "pool":  [("pool", "compute"), ("pool_dens", "compute_density"),
                  ("pool_l1", "compute_l1_pca"), ("pool_densl1", "compute_dens_l1")],
        "geom":  [("geom", "compute"), ("geom_dih", "compute_dihedral"),
                  ("geom_aucbest", "compute_auc_best"), ("geom_nbopa", "compute_nb_opacity"),
                  ("geom_seeddens", "compute_seed_density")],
        "neigh": [("neigh", "compute"), ("neigh_smdih", "compute_smooth_dihedral")],
        "gline": [("gline", "compute"), ("gline_crease", "compute_crease"),
                  ("gline_dihed", "compute_dihed"), ("gline_nogmag", "compute_nogmag")],
        "dt":    [("dt", "compute")],
        "view":  [("view", "compute"), ("view_negmed", "compute_negmed")],
    }
    for f in fams:
        try:
            mod = __import__(f"score_{f}")
        except Exception as e:
            print(f"FAMILY {f} IMPORT FAILED: {e}", flush=True); continue
        for name, fn in jobs[f]:
            if not hasattr(mod, fn):
                print(f"  {name}: missing {fn}", flush=True); continue
            t = time.time()
            try:
                s = np.asarray(getattr(mod, fn)(h, sel, st), dtype=np.float64)
                assert s.shape == (len(sel),), s.shape
                d[name] = s
                print(f"  {name}: ok {time.time()-t:.1f}s", flush=True)
            except Exception as e:
                import traceback; traceback.print_exc()
                print(f"  {name}: FAILED {e}", flush=True)
    np.savez(os.path.join(OUT, f"scores_{a.scene}.npz"), **d)
    print("saved", time.time() - t0, flush=True)


if __name__ == "__main__":
    main()
