#!/usr/bin/env python
"""LEGO CEILING AUTOPSY — Figure A (TEED pixel AUC) + Figure B (recall decomposition).

*** EVAL-ONLY. Reads the GT mesh via src/mesh_oracle, exactly as scripts/ngmec_v2_cuediag.py
    does. Nothing here is a method module; nothing in the method path imports it. ***

This is an AUTOPSY, not a gateway. It builds no aggregation heuristic and changes no scoring.

FIGURE A - does TEED see lego creases in 2D at all?
  ROC-AUC of the raw TEED sigmoid confidence at GT-crease pixels vs non-crease pixels, on
  held-out TEST views. Three confound controls, each MEASURED (reported with the control on
  and off) rather than asserted:
    C1 depth z-peel   GT creases are projected through MeshOracle.visible_crease_uv, which
                      culls with the GT mesh depth buffer (3x3 min |dz|, eps 0.015). Without
                      it, studs/cavities occluded from the camera would still be counted as
                      GT, inflating the negative class with unseeable creases.
    C2 interior only  pixels within 4px of the GT silhouette are dropped, so the number
                      measures CREASE alignment and not silhouette contrast (TEED fires hard
                      on any object boundary).
    C3 chamfer band   positive = within tau of a visible crease; negative = beyond 2*tau.
                      The band between is discarded, mirroring the 1.5/3.0 px convention the
                      published labels use. tau swept 1.0/1.5/2.5.
  RAW probability is scored, not the NMS-thinned map: NMS zeroes non-maximal pixels, which
  would turn the ROC into "is this a ridge peak" instead of "does TEED see a crease here".
  The thinned variant is reported as a sensitivity arm.

FIGURE B - why does lego recall max out at R = 0.408?
  Reranking moves along the ROC; it cannot manufacture proposals. So for every VISIBLE GT
  crease point on TEST views, classify by what exists near it in the FROZEN carrier:
    UNCOVERED         no visible carrier gaussian projects within tau -> no scoring function
                      of any kind could ever place a linelet here.
    COVERED-and-ranked a visible carrier gaussian within tau IS in the f=0.4 proposal set.
    COVERED-but-culled a visible carrier gaussian within tau exists but is NOT a proposal.
  Measured in the SAME 2D pixel space and at the SAME tau=1.5px as the R@1.5 metric, so the
  buckets decompose the actual recall gap. A 3D cross-check is also reported.
"""
import argparse, json, os, sys

import cv2
import numpy as np
from scipy.spatial import cKDTree

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
for p in (TIER1, os.path.join(TIER1, "scripts"), os.path.join(TIER1, "scripts/explore"),
          os.path.join(TIER1, "scripts/explore/syn")):
    if p not in sys.path:
        sys.path.insert(0, p)

from src import common, render, visibility, view_split           # noqa: E402
from src.mesh_oracle import MeshOracle                            # EVAL ONLY  # noqa: E402

SYN = os.path.join(TIER1, "scripts/explore/syn")


def auc_mw(score, pos):
    s = np.asarray(score, np.float64); y = np.asarray(pos, bool)
    n1, n0 = int(y.sum()), int((~y).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    order = np.argsort(s, kind="stable"); sv = s[order]
    rank = np.empty(len(s)); i = 0
    while i < len(sv):
        j = i
        while j + 1 < len(sv) and sv[j + 1] == sv[i]:
            j += 1
        rank[order[i:j + 1]] = 0.5 * (i + j) + 1.0
        i = j + 1
    return float((rank[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def teed_prob(scene, v):
    z = np.load(os.path.join(TIER1, f"out/teed_edges_{scene}", f"v{v:03d}.npz"))
    return z["native"].astype(np.float32)


def nms_thin(p):
    from final_recipe import nms_thin as _n
    return _n(p)


def gt_masks(oracle, cam, v, rgb_path, use_zpeel=True):
    """(cdt, interior) — distance to visible GT crease px, and the interior mask."""
    im = cv2.imread(rgb_path, cv2.IMREAD_UNCHANGED)
    a4 = im[:, :, 3:4].astype(np.float32) / 255.0
    gt_fg = a4[:, :, 0] > 0.5
    if use_zpeel:
        uvq = oracle.visible_crease_uv(cam, view_key=("autopsy", v))   # C1 depth z-peel
    else:
        q = oracle.crease_pts                                           # control: no cull
        c = (cam.w2c[:3, :3] @ q.T).T + cam.w2c[:3, 3]
        uv = (cam.K @ c.T).T
        uv = uv[:, :2] / np.clip(uv[:, 2:3], 1e-9, None)
        uvq = uv[c[:, 2] > 0]
    cm = np.zeros((cam.H, cam.W), bool)
    cu = np.clip(np.round(uvq[:, 0]).astype(int), 0, cam.W - 1)
    cv_ = np.clip(np.round(uvq[:, 1]).astype(int), 0, cam.H - 1)
    cm[cv_, cu] = True
    cdt = cv2.distanceTransform((~cm).astype(np.uint8), cv2.DIST_L2, 5)
    sil = gt_fg ^ (cv2.erode(gt_fg.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)
    sdt = cv2.distanceTransform((~sil).astype(np.uint8), cv2.DIST_L2, 5)
    return cdt, (gt_fg & (sdt > 4)), gt_fg, uvq


# ------------------------------------------------------------------ FIGURE A
def figure_a(scene, taus=(1.0, 1.5, 2.5)):
    cams, rgb_paths = common.load_cameras(scene)
    oracle = MeshOracle(scene)
    out = {}
    variants = [("zpeel+interior", True, True), ("no_zpeel", False, True),
                ("no_interior", True, False)]
    for vname, zp, interior_only in variants:
        for tau in (taus if vname == "zpeel+interior" else (1.5,)):
            pos_s, neg_s, pos_n, neg_n = [], [], [], []
            for v in view_split.TEST:
                cdt, interior, gt_fg, _ = gt_masks(oracle, cams[v], v, rgb_paths[v], zp)
                p = teed_prob(scene, v)
                pn = nms_thin(p)
                dom = interior if interior_only else gt_fg
                pm = dom & (cdt <= tau)
                nm = dom & (cdt > 2 * tau)
                pos_s.append(p[pm]); neg_s.append(p[nm])
                pos_n.append(pn[pm]); neg_n.append(pn[nm])
            ps, ns = np.concatenate(pos_s), np.concatenate(neg_s)
            pnn, nnn = np.concatenate(pos_n), np.concatenate(neg_n)
            key = f"{vname}|tau{tau:g}"
            out[key] = {
                "n_pos": int(len(ps)), "n_neg": int(len(ns)),
                "auc_raw": auc_mw(np.r_[ps, ns],
                                  np.r_[np.ones(len(ps), bool), np.zeros(len(ns), bool)]),
                "auc_nms": auc_mw(np.r_[pnn, nnn],
                                  np.r_[np.ones(len(pnn), bool), np.zeros(len(nnn), bool)]),
                "median_pos": float(np.median(ps)), "median_neg": float(np.median(ns))}
            r = out[key]
            print(f"    [A:{scene}] {key:26s} AUC_raw={r['auc_raw']:.4f} "
                  f"AUC_nms={r['auc_nms']:.4f}  med +{r['median_pos']:.4f}/"
                  f"-{r['median_neg']:.4f}  n={r['n_pos']}/{r['n_neg']}", flush=True)
    del oracle
    return out


# ------------------------------------------------------------------ FIGURE B
def figure_b(scene, score_npy, f_keep, tau_px=1.5):
    cams, rgb_paths = common.load_cameras(scene)
    oracle = MeshOracle(scene)
    g = common.load_gaussians(scene)
    keep = render.defloat_mask(g["mu"], g["opacity"])
    X = g["mu"][keep]
    s = np.load(score_npy)
    assert len(s) == len(X), (len(s), len(X))
    o = np.argsort(-s, kind="stable")
    seed_idx = np.sort(o[:int(round(f_keep * len(X)))])           # EXACT run_m1b:63-64
    is_seed = np.zeros(len(X), bool); is_seed[seed_idx] = True

    tot = dict(n=0, unc=0, cov_rank=0, cov_cull=0)
    per_view = []
    for v in view_split.TEST:
        cam = cams[v]
        _, _, _, uvq = gt_masks(oracle, cam, v, rgb_paths[v], True)
        if not len(uvq):
            continue
        gb = render.render_gbuffer(g, keep, cam)
        vis, uv, _ = visibility.visible_mask(X, cam, gb["depth"])
        del gb
        try:
            import torch; torch.cuda.empty_cache()
        except Exception:
            pass
        car = uv[vis]
        sed = uv[vis & is_seed]
        d_car = cKDTree(car).query(uvq, workers=-1)[0] if len(car) else np.full(len(uvq), 1e9)
        d_sed = cKDTree(sed).query(uvq, workers=-1)[0] if len(sed) else np.full(len(uvq), 1e9)
        unc = d_car > tau_px
        rank = (~unc) & (d_sed <= tau_px)
        cull = (~unc) & (d_sed > tau_px)
        per_view.append({"view": int(v), "n": int(len(uvq)),
                         "uncovered": float(unc.mean()),
                         "covered_ranked": float(rank.mean()),
                         "covered_culled": float(cull.mean())})
        tot["n"] += len(uvq); tot["unc"] += int(unc.sum())
        tot["cov_rank"] += int(rank.sum()); tot["cov_cull"] += int(cull.sum())
        print(f"    [B:{scene}] view {v:3d}  n={len(uvq):6d}  UNCOV={unc.mean():.4f}  "
              f"cov_ranked={rank.mean():.4f}  cov_culled={cull.mean():.4f}", flush=True)

    N = max(tot["n"], 1)
    res = {"tau_px": tau_px, "n_gt_crease_pts": tot["n"],
           "UNCOVERED": tot["unc"] / N,
           "COVERED_and_ranked": tot["cov_rank"] / N,
           "COVERED_but_culled": tot["cov_cull"] / N,
           "per_view": per_view, "score": score_npy, "f_keep": f_keep,
           "n_carrier": int(len(X)), "n_seeds": int(len(seed_idx))}

    # ---- 3D cross-check (tau = carrier NN spacing), independent of projection ----
    sp = float(np.median(cKDTree(X).query(X, k=2, workers=-1)[0][:, 1]))
    q = oracle.crease_pts
    d3c = cKDTree(X).query(q, workers=-1)[0]
    d3s = cKDTree(X[is_seed]).query(q, workers=-1)[0]
    u3 = d3c > sp
    res["cross_check_3d"] = {"spacing": sp, "n_crease_pts": int(len(q)),
                             "UNCOVERED": float(u3.mean()),
                             "COVERED_and_ranked": float(((~u3) & (d3s <= sp)).mean()),
                             "COVERED_but_culled": float(((~u3) & (d3s > sp)).mean())}
    del oracle
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes_a", nargs="+", default=["lego", "chair"])
    ap.add_argument("--scene_b", default="lego")
    ap.add_argument("--score", default=os.path.join(
        SYN, "finalscore_overall_lego__ngmecv2_g0_e0p25.npy"))
    ap.add_argument("--f", type=float, default=0.4)
    ap.add_argument("--tau_px", type=float, default=1.5)
    ap.add_argument("--out", default="out/lego_ceiling_autopsy.json")
    a = ap.parse_args()

    print("=== FIGURE A — TEED pixel-level ROC-AUC (held-out TEST) ===", flush=True)
    A = {s: figure_a(s) for s in a.scenes_a}
    print("\n=== FIGURE B — recall-ceiling decomposition ===", flush=True)
    B = figure_b(a.scene_b, a.score, a.f, a.tau_px)
    print(f"\n  UNCOVERED          {B['UNCOVERED']:.4f}")
    print(f"  COVERED_and_ranked {B['COVERED_and_ranked']:.4f}")
    print(f"  COVERED_but_culled {B['COVERED_but_culled']:.4f}")
    print(f"  3D cross-check UNCOVERED {B['cross_check_3d']['UNCOVERED']:.4f}")
    json.dump({"figure_A": A, "figure_B": B,
               "carrier_auc_ref": {"lego": 0.5503, "chair": 0.8542,
                                   "source": "out/ngmec_v2_cuediag.json"}},
              open(a.out, "w"), indent=1, default=float)
    print(f"\nwrote {a.out}")
