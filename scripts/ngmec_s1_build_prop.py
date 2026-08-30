"""Build epipolar-consensus caches over an ARBITRARY proposal set (not TEED).

*** METHOD PATH. MESH-FREE. ***
"""
import os, sys, json, time, argparse
import numpy as np
TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1); sys.path.insert(0, os.path.join(TIER1, "scripts/explore/syn"))
from src import common, view_split, epipolar_consensus as EC
import final_recipe as FR
OUT = os.path.join(TIER1, "out")

ap = argparse.ArgumentParser()
ap.add_argument("--scene", required=True)
ap.add_argument("--prop", required=True, help="proposal cache name, e.g. cannysharplow")
ap.add_argument("--K", type=int, default=4)
ap.add_argument("--taus", type=float, nargs="*", default=[1.5, 2.5])
ap.add_argument("--rhos", type=float, nargs="*", default=[0.0, 0.2])
ap.add_argument("--ms", type=int, nargs="*", default=[2, 3, 4])
a = ap.parse_args()

cache = os.path.join(OUT, f"prop_edges_{a.scene}_{a.prop}")
cams, _ = common.load_cameras(a.scene)
ev = np.unique(np.round(np.linspace(0, len(cams) - 1, FR.N_VIEWS)).astype(int)).tolist()
views = sorted(set(ev) | set(view_split.VAL) | set(view_split.TEST))
configs = [(t, r) for t in a.taus for r in a.rhos]
print(f"[buildprop] {a.scene}/{a.prop} K={a.K} configs={configs} views={len(views)}", flush=True)
t0 = time.time()
counts = EC.support_counts(a.scene, views, cache, configs, K=a.K, thr=0.5, nms=False)
print(f"[buildprop] counts in {time.time()-t0:.1f}s", flush=True)
meta = {"scene": a.scene, "prop": a.prop, "K": a.K, "arms": {}}
for (tau, rho) in configs:
    for m in a.ms:
        tg = f"t{tau:g}_r{rho:g}_m{m}"
        d = os.path.join(OUT, f"epi_edges_{a.scene}_{a.prop}_{tg}")
        st = EC.write_cache(counts[(tau, rho)], d, m)
        e = [x for x in st if x["view"] in ev]
        meta["arms"][tg] = {"tau": tau, "rho": rho, "m": m, "cache": d,
                            "frac_kept": float(np.mean([x["frac_kept"] for x in e])),
                            "px_per_view": float(np.mean([x["n_keep"] for x in e]))}
        print(f"  [arm] {tg:>14}: keeps {meta['arms'][tg]['frac_kept']*100:5.1f}% "
              f"({meta['arms'][tg]['px_per_view']:6.0f} px/view vs "
              f"{np.mean([x['n_teed'] for x in e]):6.0f})", flush=True)
json.dump(meta, open(os.path.join(OUT, f"ngmec_s1_buildprop_{a.scene}_{a.prop}.json"), "w"), indent=2)
print("[buildprop] done", flush=True)
