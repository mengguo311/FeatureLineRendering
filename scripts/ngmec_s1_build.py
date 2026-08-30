"""NG-MEC Stage 1 — build the epipolar-consensus edge caches.

*** METHOD PATH DRIVER. MESH-FREE. *** It imports src.epipolar_consensus (mesh-free) and
writes binary edge caches; no mesh_oracle, no tune_lib, no GT anywhere.

Caches land in out/epi_edges_<scene>_t<tau>_r<rho>_m<m>/ with the TEED file layout, so
final_recipe's "teed_epi" source reads them through the existing cache path.
"""
import os
import sys
import json
import time
import argparse

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts/explore/syn"))

from src import common, view_split, epipolar_consensus as EC
import final_recipe as FR

OUT = os.path.join(TIER1, "out")


def tag(tau, rho, m):
    return f"t{tau:g}_r{rho:g}_m{m}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", required=True)
    ap.add_argument("--K", type=int, default=4)
    ap.add_argument("--taus", type=float, nargs="*", default=[1.5, 2.5])
    ap.add_argument("--rhos", type=float, nargs="*", default=[0.0, 0.2, 7.0])
    ap.add_argument("--ms", type=int, nargs="*", default=[2, 3, 4])
    ap.add_argument("--thr", type=float, default=0.5,
                    help="TEED threshold. CARRIED FROM CHAIR VAL, never retuned per scene.")
    ap.add_argument("--teed_cache", default=None)
    ap.add_argument("--extra_views", action="store_true",
                    help="also cover VAL+TEST views (for 2D diagnostics); the pipeline "
                         "itself only ever reads the 25 M1a evidence views")
    args = ap.parse_args()

    teed_cache = args.teed_cache or os.path.join(OUT, f"teed_edges_{args.scene}")
    cams, _ = common.load_cameras(args.scene)
    ev = np.unique(np.round(np.linspace(0, len(cams) - 1, FR.N_VIEWS)).astype(int)).tolist()
    views = sorted(set(ev) | (set(view_split.VAL) | set(view_split.TEST)
                              if args.extra_views else set()))
    configs = [(t, r) for t in args.taus for r in args.rhos]
    print(f"[build] scene={args.scene} K={args.K} thr={args.thr} "
          f"evidence views={len(ev)} total views={len(views)} configs={configs}", flush=True)

    t0 = time.time()
    counts = EC.support_counts(args.scene, views, teed_cache, configs,
                               K=args.K, thr=args.thr)
    print(f"[build] support counts in {time.time() - t0:.1f}s", flush=True)

    meta = {"scene": args.scene, "K": args.K, "thr": args.thr, "teed_cache": teed_cache,
            "evidence_views": ev, "views": views,
            "neighbour_pool": "TRAIN (80 views)", "arms": {}}
    for (tau, rho) in configs:
        c = counts[(tau, rho)]
        for m in args.ms:
            tg = tag(tau, rho, m)
            d = os.path.join(OUT, f"epi_edges_{args.scene}_{tg}")
            stats = EC.write_cache(c, d, m)
            ev_stats = [x for x in stats if x["view"] in ev]
            keep = float(np.mean([x["frac_kept"] for x in ev_stats]))
            npx = float(np.mean([x["n_keep"] for x in ev_stats]))
            meta["arms"][tg] = {"tau": tau, "rho": rho, "m": m, "cache": d,
                                "frac_teed_kept_evidence_views": keep,
                                "px_per_view_evidence": npx,
                                "px_per_view_teed": float(np.mean(
                                    [x["n_teed"] for x in ev_stats])),
                                "per_view": stats}
            print(f"  [arm] {tg:>16}: keeps {keep * 100:5.1f}% of TEED "
                  f"({npx:6.0f} px/view vs {np.mean([x['n_teed'] for x in ev_stats]):6.0f})",
                  flush=True)
    jp = os.path.join(OUT, f"ngmec_s1_build_{args.scene}.json")
    json.dump(meta, open(jp, "w"), indent=2)
    print(f"[build] wrote {jp}", flush=True)


if __name__ == "__main__":
    main()
