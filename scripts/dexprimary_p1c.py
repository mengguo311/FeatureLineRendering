"""PHASE 1c — crease-vs-texture discriminator KILL-TEST.

*** EVAL / ANALYSIS SCRIPT.  Reads the GT mesh (via dexprimary_p0.gt_labels) for LABELS and
    AUC scoring only.  Features come from src/edge_semantics.py (METHOD PATH, mesh-free:
    photos + DexiNed maps + G-buffers + frozen DINOv2). ***

MEASUREMENT
  Candidates = the Phase 1b triangulated cloud (chair ref40 primary; lego secondary, built
  here with the same generator if missing).  Label CREASE if within tol=1.5px-equiv of the GT
  crease set, TEXTURE if beyond 2*tol (ambiguous band dropped).  Three feature families
  (A photometric / B geometric = the known-dead control on lego / C DINOv2 semantic),
  aggregated per candidate over the SAME 40 reference views with the SAME visibility.
  Report per-point AUC and CHAIN-AGGREGATED AUC.  Probes (logistic) are fit/eval on DISJOINT
  candidate splits: by reference view (even/odd) AND by 3D x-halfspace — both reported, so
  spatial leakage is visible if present.

FROZEN GATES (spec): GO  some family per-point AUC >= 0.75 (chair TEST-eval) or chain >= 0.80
                     MARGINAL  per-point 0.65-0.75 AND chain >= 0.75
                     NO-GO  all families < 0.65 per-point AND < 0.75 chain
"""
import os
import sys
import json
import time
import argparse

import numpy as np
import torch
from scipy.spatial import cKDTree

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
OUT = os.path.join(TIER1, "out")

from src import common, render, view_split, tri_edges as T, edge_semantics as ES
from dexprimary_p0 import gt_labels

TOL = {"chair": 0.00515, "lego": 0.00508}


def load_candidates(scene):
    """Chair: the Phase 1b ref40 cloud. Lego: same generator, built once here (METHOD path)."""
    if scene == "chair":
        z = np.load(os.path.join(OUT, "dexprimary_p1b_cloud_chair_ref40.npz"))
        cfg = json.load(open(os.path.join(OUT, "dexprimary_p1b_chair_ref40.json")))
        keep = (z["support"] >= 2) & z["surface_keep"] & (z["resid"] <= cfg["args"]["resid_max"])
        return z["P"][keep], z["ref"][keep], cfg["refs"], cfg["args"]
    p = os.path.join(OUT, "dexprimary_p1c_cloud_lego.npz")
    args = {"thr": 0.5, "key": "native", "halfpix": 0.5, "K": 6, "rho": 0.2,
            "resid_max": 1.0}
    TR = view_split.TRAIN
    refs = [TR[i] for i in np.linspace(0, len(TR) - 1, 40).astype(int)]
    if not os.path.exists(p):
        print("[p1c] building lego triangulated cloud (same generator as Phase 1b)...",
              flush=True)
        tri, st = T.build("lego", refs, TR, os.path.join(OUT, "dexined_edges_lego"),
                          thr=args["thr"], key=args["key"], K=args["K"], rho=args["rho"],
                          halfpix=args["halfpix"], verbose=False)
        print(f"[p1c] lego cloud: {st}", flush=True)
        np.savez(p, P=tri["P"], support=tri["support"], resid=tri["resid"],
                 ref=tri["ref"], surface_keep=tri["surface_keep"])
    z = np.load(p)
    keep = (z["support"] >= 2) & z["surface_keep"] & (z["resid"] <= args["resid_max"])
    return z["P"][keep], z["ref"][keep], [int(r) for r in refs], args


def auc(y, s):
    """ROC-AUC with orientation folded in (max of s and -s); returns (auc, sign)."""
    from sklearn.metrics import roc_auc_score
    m = np.isfinite(s)
    if m.sum() < 100 or len(np.unique(y[m])) < 2:
        return float("nan"), 0
    a = roc_auc_score(y[m], s[m])
    return (a, +1) if a >= 0.5 else (1 - a, -1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="chair", choices=["chair", "lego"])
    ap.add_argument("--no_dino", action="store_true")
    args = ap.parse_args()
    scene = args.scene
    t00 = time.time()

    P, refv, refs, A = load_candidates(scene)
    N = len(P)
    print(f"[p1c] {scene}: {N} candidates from {len(refs)} reference views", flush=True)

    # ---------------- LABELS (EVAL-ONLY: the one place the mesh is read) ----------------
    crease_pts, _, _ = gt_labels(scene, view_split.TEST)
    d3 = cKDTree(crease_pts).query(P, k=1)[0]
    tol = TOL[scene]
    y = np.full(N, -1, np.int8)                    # -1 = ambiguous band, dropped
    y[d3 <= tol] = 1                               # CREASE
    y[d3 >= 2 * tol] = 0                           # TEXTURE
    lab = y >= 0
    print(f"[p1c] labels: crease {int((y==1).sum())}  texture {int((y==0).sum())}  "
          f"band-dropped {int((y==-1).sum())}  (tol {tol})", flush=True)

    # ---------------- FEATURES (METHOD path; identical view set + visibility) -----------
    cams, rgb_paths = common.load_cameras(scene)
    g = common.load_gaussians(scene)
    kg = render.defloat_mask(g["mu"], g["opacity"])
    dex = os.path.join(OUT, f"dexined_edges_{scene}")

    dino = None
    if not args.no_dino:
        dino = torch.hub.load("facebookresearch/dinov2", "dinov2_vits14",
                              skip_validation=True).eval().cuda()

    nv = len(refs)
    fa = np.full((N, nv, len(ES.A_NAMES)), np.nan, np.float16)
    fb = np.full((N, nv, len(ES.B_NAMES)), np.nan, np.float16)
    fc = np.full((N, nv, 2), np.nan, np.float16)
    dsum = np.zeros((N, 384), np.float32)
    dcnt = np.zeros(N, np.int32)
    for i, v in enumerate(refs):
        t0 = time.time()
        cam = cams[v]
        gb = render.render_gbuffer(g, kg, cam, with_median_depth=True)
        rgb = ES.composite_white(rgb_paths[v])
        prob = np.load(os.path.join(dex, f"v{v:03d}.npz"))[A["key"]].astype(np.float32)
        inb, Af, Bf, en = ES.fam_ab_view(P, cam, rgb, prob, gb, halfpix=A["halfpix"])
        fa[:, i] = Af
        fb[:, i] = Bf
        if dino is not None:
            tok, grid = ES.dino_tokens(dino, rgb)
            gb["edge_nx"], gb["edge_ny"] = en[:, 0], en[:, 1]
            inc, desc, scal = ES.fam_c_view(P, cam, tok, grid, gb, halfpix=A["halfpix"])
            fc[:, i] = scal
            ok = inc & np.isfinite(desc[:, 0])
            dsum[ok] += desc[ok]
            dcnt[ok] += 1
        del gb
        torch.cuda.empty_cache()
        if i % 8 == 0:
            print(f"  view {i+1}/{nv} (v{v}) {time.time()-t0:.1f}s  inb {int(inb.sum())}",
                  flush=True)
    if dino is not None:
        del dino
        torch.cuda.empty_cache()

    FA = np.nanmedian(fa.astype(np.float32), axis=1)
    FB = np.nanmedian(fb.astype(np.float32), axis=1)
    FC = np.nanmedian(fc.astype(np.float32), axis=1)
    DD = dsum / np.maximum(dcnt, 1)[:, None]
    DD[dcnt == 0] = np.nan
    print(f"[p1c] features done {time.time()-t00:.0f}s  "
          f"dino views/candidate median {np.median(dcnt)}", flush=True)

    # ---------------- CHAINS (METHOD path) ----------------
    chain = ES.chain_candidates(P)
    nch = chain.max() + 1 if chain.max() >= 0 else 0
    in_ch = chain >= 0
    print(f"[p1c] chains: {nch} chains cover {in_ch.mean():.3f} of candidates; "
          f"median size {np.median(np.bincount(chain[in_ch])):.0f}", flush=True)

    # ---------------- SPLITS ----------------
    ref_idx = {r: i for i, r in enumerate(refs)}
    even = np.array([ref_idx[r] % 2 == 0 for r in refv])
    splits = {"refsplit": (even, ~even),
              "xsplit": (P[:, 0] < np.median(P[:, 0]), P[:, 0] >= np.median(P[:, 0]))}

    # ---------------- AUC ----------------
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    res = {"scene": scene, "n": N, "tol": tol,
           "n_crease": int((y == 1).sum()), "n_texture": int((y == 0).sum()),
           "n_band": int((y == -1).sum()), "n_chains": int(nch),
           "chain_cover": float(in_ch.mean()), "features": {}, "probes": {}, "chains": {}}

    feats = {}
    for i, n in enumerate(ES.A_NAMES):
        feats[f"A:{n}"] = FA[:, i]
    for i, n in enumerate(ES.B_NAMES):
        feats[f"B:{n}"] = FB[:, i]
    for i, n in enumerate(ES.C_SCALAR_NAMES):
        feats[f"C:{n}"] = FC[:, i]

    print(f"\n===== PER-POINT AUC, single features ({scene}) =====")
    for k, s in feats.items():
        a, sgn = auc(y[lab], s[lab])
        res["features"][k] = {"auc": a, "sign": sgn}
        print(f"  {k:22s} AUC {a:.4f}  (sign {sgn:+d})", flush=True)

    def fit_probe(X, name):
        out = {}
        sc_by_split = {}
        for sp, (mf, me) in splits.items():
            ok = np.isfinite(X).all(1) & lab
            f_m, e_m = ok & mf, ok & me
            if f_m.sum() < 500 or e_m.sum() < 500:
                continue
            sc = StandardScaler().fit(X[f_m])
            clf = LogisticRegression(max_iter=2000, C=1.0)
            sub = np.where(f_m)[0]
            if len(sub) > 60000:
                sub = np.random.default_rng(0).choice(sub, 60000, replace=False)
            clf.fit(sc.transform(X[sub]), y[sub])
            pf = clf.predict_proba(sc.transform(X[f_m]))[:, 1]
            pe = clf.predict_proba(sc.transform(X[e_m]))[:, 1]
            af, _ = auc(y[f_m], pf)
            ae, _ = auc(y[e_m], pe)
            out[sp] = {"fit_auc": af, "eval_auc": ae,
                       "n_fit": int(f_m.sum()), "n_eval": int(e_m.sum())}
            allok = np.isfinite(X).all(1)          # score EVERY candidate for chains/viz
            sf = np.full(N, np.nan)
            sf[allok] = clf.predict_proba(sc.transform(X[allok]))[:, 1]
            sc_by_split[sp] = sf
            print(f"  probe {name:12s} [{sp:8s}] fit {af:.4f}  EVAL {ae:.4f}  "
                  f"(n {int(f_m.sum())}/{int(e_m.sum())})", flush=True)
        res["probes"][name] = out
        return sc_by_split.get("refsplit", np.full(N, np.nan)), \
            sc_by_split.get("xsplit", np.full(N, np.nan))

    print(f"\n===== PROBES (logistic; fit/eval on disjoint splits) =====")
    sA, sAx = fit_probe(FA, "FAM-A")
    sB, sBx = fit_probe(FB, "FAM-B")
    scores = {"FAM-A(probe)": sA, "FAM-B(probe)": sB}
    xscores = {"FAM-A(probe)": sAx, "FAM-B(probe)": sBx}
    if not args.no_dino:
        sC, sCx = fit_probe(DD, "FAM-C(dino)")
        sABC, sABCx = fit_probe(np.concatenate([FA, FB, FC, DD], 1), "A+B+C")
        scores["FAM-C(probe)"] = sC
        scores["A+B+C(probe)"] = sABC
        xscores["FAM-C(probe)"] = sCx
        xscores["A+B+C(probe)"] = sABCx
    for k, s in feats.items():
        scores[k] = s * res["features"][k]["sign"]

    # ---------------- CHAIN AGGREGATION ----------------
    print(f"\n===== CHAIN-AGGREGATED AUC (median score over chain; majority label) =====")
    if nch > 0:
        ch_y = np.full(nch, -1, np.int8)
        pur = np.zeros(nch)
        for c in range(nch):
            m = (chain == c) & lab
            if m.sum() >= 5:
                fr = (y[m] == 1).mean()
                ch_y[c] = 1 if fr >= 0.5 else 0
                pur[c] = max(fr, 1 - fr)
        chl = ch_y >= 0
        res["chain_stats"] = {"n_scored": int(chl.sum()),
                              "purity_mean": float(pur[chl].mean()),
                              "crease_chains": int((ch_y == 1).sum()),
                              "texture_chains": int((ch_y == 0).sum())}
        print(f"  {int(chl.sum())} scorable chains  (crease {int((ch_y==1).sum())} / "
              f"texture {int((ch_y==0).sum())})  label purity {pur[chl].mean():.3f}")
        order = np.argsort(chain)
        bounds = np.searchsorted(chain[order], np.arange(nch))
        bounds = np.append(bounds, len(order))

        def chain_median(s):
            ch_s = np.full(nch, np.nan)
            for c in np.where(chl)[0]:
                v_ = s[order[bounds[c]:bounds[c + 1]]]
                v_ = v_[np.isfinite(v_)]
                if len(v_):
                    ch_s[c] = np.median(v_)
            return ch_s

        for k, s in scores.items():
            a, sgn = auc(ch_y[chl], chain_median(s)[chl])
            res["chains"][k] = {"auc": a, "sign": sgn}
            print(f"  {k:22s} chain-AUC {a:.4f}", flush=True)

        # LEAKAGE-GUARDED chain-AUC: the xsplit-fitted probe, scored only on chains that lie
        # ENTIRELY in the x-EVAL halfspace (the fit model never saw that half of the object).
        me_x = splits["xsplit"][1]
        ch_eval = np.zeros(nch, bool)
        for c in np.where(chl)[0]:
            ch_eval[c] = bool(me_x[order[bounds[c]:bounds[c + 1]]].all())
        sel = chl & ch_eval
        print(f"  -- leakage-guarded (xsplit model, {int(sel.sum())} chains fully in the "
              f"held-out halfspace; crease {int((ch_y[sel]==1).sum())} / texture "
              f"{int((ch_y[sel]==0).sum())}) --", flush=True)
        res["chains_guarded"] = {}
        for k, s in xscores.items():
            a, sgn = auc(ch_y[sel], chain_median(s)[sel])
            res["chains_guarded"][k] = {"auc": a, "sign": sgn}
            print(f"  {k:22s} GUARDED chain-AUC {a:.4f}", flush=True)

    def _san(k):
        return k.replace(":", "_").replace("(", "_").replace(")", "")
    np.savez(os.path.join(OUT, f"dexp1c_scores_{scene}.npz"),
             P=P, y=y, chain=chain, d3=d3, x_eval_half=splits["xsplit"][1],
             **{_san(k): v for k, v in scores.items()},
             **{"X_" + _san(k): v for k, v in xscores.items()})
    jp = os.path.join(OUT, f"dexprimary_p1c_{scene}.json")
    json.dump(res, open(jp, "w"), indent=2)
    print(f"\nwrote {jp}  ({time.time()-t00:.0f}s total)")


if __name__ == "__main__":
    main()
