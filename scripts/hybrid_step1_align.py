"""STEP 1 — CROSS-REPRESENTATION ALIGNMENT PRE-TEST for the vanilla x 2DGS hybrid.

*** EVAL-ONLY DRIVER. The GT mesh appears HERE ONLY, to (a) LABEL vanilla M1a seeds as
GT-crease vs GT-fabric and (b) provide the CEILING CONTROL arm. The gate under test
(src/hybrid_gate.py) is mesh-free and never sees any of this. ***

THE QUESTION
    Vanilla 3DGS and 2DGS are two independent trainings whose surfaces diverge most exactly
    at creases. Gating a VANILLA seed by querying a 2DGS geometric-edge map at that seed's
    reprojection may sample the adjacent flat facet and veto a true crease. Does a DILATED
    region gate absorb that misalignment before printed texture leaks back in?

        G_r(u,v) = OR over ||delta||_2 <= r of [ C_2dgs(u+delta) >= tau ]

    R_crease(r)   = fraction of GT-CREASE vanilla seed observations that pass G_r
    FPR_fabric(r) = fraction of GT-FABRIC vanilla seed observations that pass G_r
  GO: exists r with R_crease >= 0.80 AND FPR_fabric <= 0.15  -> use the smallest such r.
  else -> STEP 1b, the projection-immune 3D nearest-surfel dihedral gate, measured here in
  the same units so the two are directly comparable.

WHY THERE IS A CEILING ARM, AND WHY IT IS THE MOST IMPORTANT COLUMN
    PLAN1_RESULTS.md records that STEP A's first, frozen GO rule was failed BY GROUND TRUTH
    ITSELF: the FABRIC class ("no GT crease within 3px") is contaminated by genuinely
    non-flat geometry -- chair legs, ornaments, interior self-occlusions, folds shallower
    than the oracle's 30 deg crease criterion -- so no reconstruction, however perfect, can
    read flat there. A NO-GO is only evidence about CO-REGISTRATION if a GT-mesh gate,
    measured on the identical seeds with the identical estimator, would have passed. Three
    control arms are therefore run alongside the 2DGS ones:
        mesh     -> the ceiling. GT geometry, normals derived from the GT depth buffer.
        vanilla  -> the floor. Gating the vanilla seeds on their OWN representation; this
                    has no cross-representation misalignment at all, so any gap between
                    `vanilla` and `2dgs` is the price of co-registration, and any gap
                    between `mesh` and both is the price of reconstruction.
        + the STEP-A refined subset (FLAT-fabric vs SHARP-crease, judged by the mesh arm),
          which is the subset on which 2DGS normals scored AUC 0.967.

LABELS (identical convention to scripts/explore/gate_falsify.py):
    CREASE  reprojection within 2.0 px of a visible GT crease pixel
    FABRIC  reprojection further than 3.0 px from every one (2-3 px band unlabelled)
    INTERIOR restricts to seeds >4 px from the silhouette, so an occluding contour cannot
    masquerade as either class.
    REFINED restricts FABRIC to seeds where the MESH arm's own dihedral is < 5 deg (the
    surface really is flat there and the edge really is printed) and CREASE to seeds where
    it is > 20 deg (the crease really is geometric and visible from this view) --
    FLAT_DEG / SHARP_DEG exactly as in scripts/explore/gate_falsify_2dgs.py.
"""
import argparse
import json
import os
import sys
import time

import cv2
import numpy as np
import torch

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
sys.path.insert(0, os.path.join(TIER1, "scripts/explore/syn"))

from src import common, render, visibility, view_split, render2dgs, hybrid_gate

OUT = os.path.join(TIER1, "out")
CACHE = os.path.join(TIER1, "cache")
SYN = os.path.join(TIER1, "scripts/explore/syn")

TAU_CREASE = 2.0          # <= px from a GT crease            -> CREASE
TAU_FABRIC = 3.0          # >  px from every GT crease        -> FABRIC
SIL_CLEAR = 4.0           # interior = > px from the silhouette
FLAT_DEG = 5.0            # mesh-arm dihedral below this => GT surface locally FLAT
SHARP_DEG = 20.0          # mesh-arm dihedral above this => GT surface genuinely CREASED

SUBSETS = ("all", "interior", "refined")


# ===================================================================== METHOD PATH
def m1a_overall_seeds(scene, f, X, verbose=True):
    """The tuned vanilla M1a OVERALL seeds: top-f of the cached per-gaussian score."""
    p = os.path.join(SYN, f"finalscore_overall_{scene}.npy")
    if not os.path.exists(p):
        raise RuntimeError(f"missing cached M1a OVERALL score {p}")
    s = np.load(p)
    if len(s) != len(X):
        raise RuntimeError(f"score/gaussian mismatch {len(s)} vs {len(X)}")
    idx = np.sort(np.argsort(-s, kind="stable")[:int(round(f * len(X)))])
    if verbose:
        print(f"  [seeds] M1a OVERALL f={f} -> {len(idx)} of {len(X)} gaussians "
              f"({os.path.relpath(p, TIER1)})", flush=True)
    return idx


# ================================================================== EVAL ONLY ====
_ORACLE = None


def oracle(scene, angle_deg=30.0):
    global _ORACLE
    if _ORACLE is None:
        from src.mesh_oracle import MeshOracle
        _ORACLE = MeshOracle(scene, angle_deg=angle_deg)
    return _ORACLE


def gt_crease_dt(scene, cam, v, angle_deg=30.0):
    """GT crease distance transform for one view. EVAL ONLY. Cached on disk."""
    p = os.path.join(CACHE, f"creasedt_{scene}_a{int(angle_deg)}_v{v}.npz")
    if os.path.exists(p):
        return np.load(p)["cdt"]
    uvq = oracle(scene, angle_deg).visible_crease_uv(cam, view_key=int(v))
    m = np.zeros((cam.H, cam.W), bool)
    m[np.clip(np.round(uvq[:, 1]).astype(int), 0, cam.H - 1),
      np.clip(np.round(uvq[:, 0]).astype(int), 0, cam.W - 1)] = True
    cdt = cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5)
    np.savez_compressed(p, cdt=cdt)
    return cdt


def normals_from_depth(depth, fg, cam):
    """Camera-space normals from a z-buffer (used for the GT-mesh ceiling arm, which has
    no normal buffer of its own). tier1 convention: u = f*X/Z + W/2, depth = camera-axis z.
    The dihedral and ||grad N||_F estimators are both invariant to a global rotation, so
    camera-space normals are directly comparable to the world-space normals the gaussian
    arms render."""
    H, W = depth.shape
    z = np.where(fg, depth, np.nan).astype(np.float64)
    uu, vv = np.meshgrid(np.arange(W), np.arange(H))
    Xc = (uu - cam.K[0, 2]) * z / cam.f
    Yc = (vv - cam.K[1, 2]) * z / cam.f
    P = np.stack([Xc, Yc, z], -1)
    du = np.zeros_like(P); dv = np.zeros_like(P)
    du[:, 1:-1] = P[:, 2:] - P[:, :-2]
    dv[1:-1] = P[2:] - P[:-2]
    n = np.cross(du, dv)
    nn = np.linalg.norm(n, axis=-1, keepdims=True)
    n = np.where(nn > 1e-12, n / np.maximum(nn, 1e-30), 0.0)
    n = np.where((n[..., 2:3] > 0), -n, n)          # orient toward the camera, as render.py
    return np.nan_to_num(n, nan=0.0).astype(np.float32)


class GaussArm:
    """Any splat representation that renders a normal buffer (vanilla 3DGS or 2DGS)."""

    def __init__(self, name, kind, **kw):
        self.name, self.kind, self.kw = name, kind, kw

    def gbuffer(self, cam, v):
        if self.kind == "vanilla":
            gb = render.render_gbuffer(self.kw["g"], self.kw["keep"], cam)
            d = gb["depth"].cpu().numpy().astype(np.float32)
            a = gb["alpha"].cpu().numpy()
            n = gb["normal"].cpu().numpy()
        else:
            gb = render2dgs.render_gbuffer_2dgs(
                self.kw["g2"], self.kw["pipe"], cam,
                bg_white=self.kw["meta"].get("white_background", True),
                half_pixel=self.kw.get("half_pixel", True))
            d = gb["depth"].cpu().numpy().astype(np.float32)
            a = gb["alpha"].cpu().numpy()
            n = gb["normal"].cpu().numpy()
        del gb
        torch.cuda.empty_cache()
        return d, a, n


class MeshArm:
    """GT geometry. EVAL ONLY — the ceiling control, never a method input."""
    kind = "mesh"

    def __init__(self, scene):
        self.name, self.scene = "mesh", scene

    def gbuffer(self, cam, v):
        z = oracle(self.scene).render_depth(cam, view_key=int(v))
        z = (z.cpu().numpy() if torch.is_tensor(z) else np.asarray(z)).astype(np.float32)
        fg = z < 1e8
        d = np.where(fg, z, np.inf).astype(np.float32)
        return d, fg.astype(np.float32), normals_from_depth(d, fg, cam)


def rates(pas, lab, sel):
    c = sel & (lab == 1)
    f = sel & (lab == 2)
    nc, nf = int(c.sum()), int(f.sum())
    return (float(pas[c].mean()) if nc else float("nan"),
            float(pas[f].mean()) if nf else float("nan"), nc, nf)


def auc_from_scores(s, lab, sel):
    """P(score[crease] > score[fabric]); 0.5 = chance. Ties averaged."""
    c, f = s[sel & (lab == 1)], s[sel & (lab == 2)]
    if not len(c) or not len(f):
        return float("nan")
    a = np.concatenate([c, f])
    r = np.empty(len(a))
    r[np.argsort(a, kind="stable")] = np.arange(1, len(a) + 1)
    _, inv, cnt = np.unique(a, return_inverse=True, return_counts=True)
    ssum = np.zeros(len(cnt))
    np.add.at(ssum, inv, r)
    r = (ssum / cnt)[inv]
    return float((r[:len(c)].sum() - len(c) * (len(c) + 1) / 2.0) / (len(c) * len(f)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="chair")
    ap.add_argument("--models", nargs="*",
                    default=[os.path.join(OUT, "2dgs_chair_dist"),
                             os.path.join(OUT, "2dgs_chair")])
    ap.add_argument("--f", type=float, default=0.30)
    ap.add_argument("--radii", type=int, nargs="*", default=[0, 1, 2, 3, 5, 8])
    ap.add_argument("--taus_dihedral", type=float, nargs="*",
                    default=[8.0, 10.0, 12.0, 15.0, 20.0])
    ap.add_argument("--gradn_q", type=float, nargs="*",
                    default=[50.0, 70.0, 80.0, 90.0, 95.0])
    ap.add_argument("--surfel_k", type=int, nargs="*", default=[4, 8, 16])
    ap.add_argument("--surfel_theta", type=float, nargs="*",
                    default=[5, 8, 10, 12, 15, 20, 25, 30, 40, 50, 60])
    ap.add_argument("--vote_fracs", type=float, nargs="*",
                    default=[0.01, 0.25, 0.5, 0.75, 1.0])
    ap.add_argument("--no_half_pixel_control", action="store_true")
    ap.add_argument("--nviews", type=int, default=0)
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    t0 = time.time()

    # ------------------------------------------------------------ METHOD PATH
    cams, rgb_paths = common.load_cameras(args.scene)
    g = common.load_gaussians(args.scene)
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    X = g["mu"][keep_g]
    idx = m1a_overall_seeds(args.scene, args.f, X)
    seeds = X[idx]
    S = len(seeds)
    views = list(view_split.VAL)
    if args.nviews:
        views = views[:args.nviews]
    print(f"[STEP 1] {args.scene}: {S} vanilla M1a OVERALL seeds, VAL views {views}",
          flush=True)

    arms = []
    for m in args.models:
        name = os.path.basename(os.path.normpath(m))
        g2, pipe, meta = render2dgs.load_2dgs(m)
        arms.append(GaussArm(name, "2dgs", g2=g2, pipe=pipe, meta=meta))
        print(f"  [arm 2dgs] {name}: {meta['n_gauss']} surfels it={meta['iteration']} "
              f"depth_ratio={meta['depth_ratio']}", flush=True)
    arms.append(GaussArm("vanilla", "vanilla", g=g, keep=keep_g))
    arms.append(MeshArm(args.scene))
    print(f"  [arm control] vanilla (floor: no cross-representation misalignment)")
    print(f"  [arm control] mesh    (ceiling: GT geometry)  EVAL ONLY", flush=True)
    names = [a.name for a in arms]

    LAB, VIS, INT, MESHTH = [], [], [], []
    PASS, RAW, HPCTL, gradn_tau = {}, {}, {}, {}

    for v in views:
        cam = cams[v]
        gbv = render.render_gbuffer(g, keep_g, cam)
        vis, uv, _ = visibility.visible_mask(seeds, cam, gbv["depth"])
        alp = gbv["alpha"].cpu().numpy()
        del gbv
        torch.cuda.empty_cache()
        fg = alp > 0.5
        u = np.clip(np.round(uv[:, 0]).astype(np.int64), 0, cam.W - 1)
        w = np.clip(np.round(uv[:, 1]).astype(np.int64), 0, cam.H - 1)
        vis = vis & (uv[:, 0] >= 0) & (uv[:, 0] < cam.W) & \
                    (uv[:, 1] >= 0) & (uv[:, 1] < cam.H)

        cdt = gt_crease_dt(args.scene, cam, v)                       # EVAL ONLY
        sil = fg ^ (cv2.erode(fg.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)
        sdt = cv2.distanceTransform((~sil).astype(np.uint8), cv2.DIST_L2, 5)
        d = cdt[w, u]
        LAB.append(np.where(d <= TAU_CREASE, 1,
                            np.where(d > TAU_FABRIC, 2, 0)).astype(np.uint8))
        VIS.append(vis)
        INT.append(fg[w, u] & (sdt[w, u] > SIL_CLEAR))

        for arm in arms:
            dep, alpa, nrm = arm.gbuffer(cam, v)
            fga = (alpa > 0.5) & np.isfinite(dep)
            A = hybrid_gate.dihedral_deg(nrm, dep, alpa)
            G = hybrid_gate.normal_grad_mag(nrm, dep, alpa)
            if arm.name == "mesh":
                MESHTH.append(A[w, u].copy())
            for signal, sig in (("dihedral", A), ("gradn", G)):
                RAW.setdefault((arm.name, signal), []).append(sig[w, u].copy())
                if signal == "dihedral":
                    taus = [(f"{t:g}", t) for t in args.taus_dihedral]
                else:
                    on = sig[fga & (sig > 0)]
                    taus = []
                    for q in args.gradn_q:
                        t = float(np.percentile(on, q)) if len(on) else 0.0
                        gradn_tau.setdefault((arm.name, q), []).append(t)
                        taus.append((f"q{q:g}", t))
                for tkey, t in taus:
                    hard = sig >= t
                    for r in args.radii:
                        PASS.setdefault((arm.name, signal, tkey, r), []).append(
                            hybrid_gate.dilate_disk(hard, r)[w, u])
            if arm.kind == "2dgs" and not args.no_half_pixel_control:
                gb2n = render2dgs.render_gbuffer_2dgs(
                    arm.kw["g2"], arm.kw["pipe"], cam,
                    bg_white=arm.kw["meta"].get("white_background", True),
                    half_pixel=False)
                sig, _ = hybrid_gate.signal_map(gb2n, "dihedral")
                hard = sig >= hybrid_gate.TAU_GEOM
                for r in args.radii:
                    HPCTL.setdefault((arm.name, r), []).append(
                        hybrid_gate.dilate_disk(hard, r)[w, u])
                del gb2n
                torch.cuda.empty_cache()
        print(f"  view {v} done ({time.time() - t0:.0f}s)", flush=True)

    V = len(views)
    LAB = np.concatenate(LAB); VIS = np.concatenate(VIS); INT = np.concatenate(INT)
    MESHTH = np.concatenate(MESHTH)
    LABv = LAB.reshape(V, S); VISv = VIS.reshape(V, S)
    sel = {"all": VIS,
           "interior": VIS & INT,
           "refined": VIS & INT & (((LAB == 2) & (MESHTH < FLAT_DEG)) |
                                   ((LAB == 1) & (MESHTH > SHARP_DEG)))}
    for k in SUBSETS:
        print(f"  [{k:8s}] crease {int((sel[k] & (LAB==1)).sum()):6d}  "
              f"fabric {int((sel[k] & (LAB==2)).sum()):6d}", flush=True)

    # --------------------------------------------------------------- 3D surfel gate
    surfel_rows, surfel_theta = [], {}
    from scipy.spatial import cKDTree
    for m in args.models:
        name = os.path.basename(os.path.normpath(m))
        sf = hybrid_gate.load_surfel_frames(m)
        print(f"  [3d] {name}: {sf['n_keep']}/{sf['n_all']} surfels after de-floater",
              flush=True)
        tree = cKDTree(sf["mu"])
        for k in args.surfel_k:
            th, nnb, d1 = hybrid_gate.surfel_dihedral(seeds, sf["mu"], sf["normal"],
                                                      k=k, tree=tree)
            surfel_theta[(name, k)] = th
            ths = np.tile(th, V)
            for tag in SUBSETS:
                a = auc_from_scores(ths, LAB, sel[tag])
                for t in args.surfel_theta:
                    rc, ff, nc, nf = rates(ths >= t, LAB, sel[tag])
                    surfel_rows.append({"model": name, "k": k, "theta": t, "subset": tag,
                                        "R_crease": rc, "FPR_fabric": ff,
                                        "n_crease": nc, "n_fabric": nf, "auc": a})
        del tree, sf

    # ------------------------------------------------------------------- 2D tables
    rows, vote_rows = [], []
    seedlab = np.where((LABv == 1).sum(0) >= (LABv == 2).sum(0),
                       np.where((LABv == 1).sum(0) > 0, 1, 0),
                       2).astype(np.uint8)
    for (name, signal, tkey, r), lst in PASS.items():
        P = np.stack(lst)                                   # [V,S]
        pas = P.reshape(-1)
        for tag in SUBSETS:
            rc, ff, nc, nf = rates(pas, LAB, sel[tag])
            rows.append({"arm": name, "signal": signal, "tau": tkey, "r": r,
                         "subset": tag, "R_crease": rc, "FPR_fabric": ff,
                         "n_crease": nc, "n_fabric": nf,
                         "pass_rate": float(pas[sel[tag]].mean())})
        for vf in args.vote_fracs:
            k, fr, nv = hybrid_gate.vote_keep(P, VISv, frac=vf)
            c, f_ = seedlab == 1, seedlab == 2
            vote_rows.append({"arm": name, "signal": signal, "tau": tkey, "r": r,
                              "vote_frac": vf, "keep": int(k.sum()),
                              "R_crease": float(k[c].mean()) if c.any() else float("nan"),
                              "FPR_fabric": float(k[f_].mean()) if f_.any() else float("nan")})
    auc2d = {}
    for (name, signal), lst in RAW.items():
        s = np.concatenate(lst)
        for tag in SUBSETS:
            auc2d[f"{name}|{signal}|{tag}"] = auc_from_scores(s, LAB, sel[tag])
    hp_rows = []
    for (name, r), lst in HPCTL.items():
        pas = np.concatenate(lst)
        for tag in SUBSETS:
            rc, ff, nc, nf = rates(pas, LAB, sel[tag])
            hp_rows.append({"arm": name, "r": r, "subset": tag, "half_pixel": False,
                            "R_crease": rc, "FPR_fabric": ff})

    # --------------------------------------------------------------- print + verdict
    for sub in SUBSETS:
        print("\n" + "=" * 106)
        print(f"STEP 1 ALIGNMENT TABLE — {args.scene}, VAL views {views}, subset = {sub}"
              f"   (crease n={int((sel[sub] & (LAB==1)).sum())}, "
              f"fabric n={int((sel[sub] & (LAB==2)).sum())})")
        print("=" * 106)
        hdr = "  ".join(f"r={r:<3d}" for r in args.radii)
        for name in names:
            for signal in ("dihedral", "gradn"):
                keys = sorted({k[2] for k in PASS if k[0] == name and k[1] == signal},
                              key=lambda s: float(s.lstrip("q")))
                print(f"\n-- {name} / {signal}   (raw-signal AUC = "
                      f"{auc2d[f'{name}|{signal}|{sub}']:.3f})")
                print(f"{'tau':>7} {'metric':>12}   {hdr}")
                for tkey in keys:
                    for metric in ("R_crease", "FPR_fabric"):
                        vals = []
                        for r in args.radii:
                            rr = [x for x in rows if x["arm"] == name and
                                  x["signal"] == signal and x["tau"] == tkey and
                                  x["r"] == r and x["subset"] == sub][0]
                            vals.append(f"{rr[metric]:.3f}")
                        print(f"{tkey:>7} {metric:>12}   " +
                              "  ".join(f"{v:<5}" for v in vals))

    print("\n" + "=" * 106)
    print("STEP 1b — 3D NEAREST-SURFEL DIHEDRAL GATE (projection-immune)")
    print("=" * 106)
    for m in args.models:
        name = os.path.basename(os.path.normpath(m))
        for k in args.surfel_k:
            for sub in SUBSETS:
                rr = [x for x in surfel_rows if x["model"] == name and x["k"] == k
                      and x["subset"] == sub]
                print(f"\n-- {name} / k={k} / {sub}   (theta_max AUC = {rr[0]['auc']:.3f})")
                print("  " + " ".join(f"th={x['theta']:<5g}" for x in rr))
                print("  " + " ".join(f"R={x['R_crease']:<6.3f}" for x in rr))
                print("  " + " ".join(f"F={x['FPR_fabric']:<6.3f}" for x in rr))

    verdict = {}
    for sub in SUBSETS:
        r2 = [x for x in rows if x["subset"] == sub]
        r3 = [x for x in surfel_rows if x["subset"] == sub]
        meth2 = [x for x in r2 if x["arm"] not in ("mesh",)]
        ok2 = [x for x in meth2 if x["R_crease"] >= 0.80 and x["FPR_fabric"] <= 0.15]
        ok3 = [x for x in r3 if x["R_crease"] >= 0.80 and x["FPR_fabric"] <= 0.15]
        okm = [x for x in r2 if x["arm"] == "mesh" and
               x["R_crease"] >= 0.80 and x["FPR_fabric"] <= 0.15]
        verdict[sub] = {
            "go_2d": min(ok2, key=lambda x: (x["r"], -x["R_crease"])) if ok2 else None,
            "go_3d": max(ok3, key=lambda x: x["R_crease"] - x["FPR_fabric"]) if ok3 else None,
            "ceiling_go": min(okm, key=lambda x: (x["r"], -x["R_crease"])) if okm else None,
            "best_sep_2d": max(meth2, key=lambda x: x["R_crease"] - x["FPR_fabric"]),
            "best_sep_3d": max(r3, key=lambda x: x["R_crease"] - x["FPR_fabric"]),
            "best_sep_mesh": max([x for x in r2 if x["arm"] == "mesh"],
                                 key=lambda x: x["R_crease"] - x["FPR_fabric"]),
        }

    print("\n" + "#" * 106)
    print("# GO rule: exists a gate with R_crease >= 0.80 AND FPR_fabric <= 0.15")
    for sub in SUBSETS:
        vd = verdict[sub]
        print(f"#\n# [{sub}]")
        for key, lab in (("go_2d", "2D dilated gate (2DGS/vanilla)"),
                         ("go_3d", "3D surfel gate"),
                         ("ceiling_go", "GT-MESH CEILING")):
            x = vd[key]
            s = "GO  " if x else "NO-GO"
            det = ""
            if x:
                det = ("  -> " + (f"{x['model']} k={x['k']} theta={x['theta']}"
                                  if key == "go_3d" else
                                  f"{x['arm']}/{x['signal']} tau={x['tau']} r={x['r']}px") +
                       f"  R={x['R_crease']:.3f} FPR={x['FPR_fabric']:.3f}")
            print(f"#   {lab:32s}: {s}{det}")
        for key, lab in (("best_sep_2d", "best 2D separation "),
                         ("best_sep_3d", "best 3D separation "),
                         ("best_sep_mesh", "best MESH separation")):
            x = vd[key]
            who = (f"{x['model']} k={x['k']} th={x['theta']}" if key == "best_sep_3d"
                   else f"{x['arm']}/{x['signal']} tau={x['tau']} r={x['r']}")
            print(f"#     {lab}: {who:38s} R={x['R_crease']:.3f} "
                  f"FPR={x['FPR_fabric']:.3f}  (R-FPR={x['R_crease']-x['FPR_fabric']:+.3f})")
    print("#" * 106, flush=True)

    tag = f"_{args.tag}" if args.tag else ""
    js = {"scene": args.scene, "val_views": views, "f": args.f, "n_seeds": S,
          "arms": names, "models": args.models,
          "label_rule": {"tau_crease": TAU_CREASE, "tau_fabric": TAU_FABRIC,
                         "sil_clear": SIL_CLEAR, "flat_deg": FLAT_DEG,
                         "sharp_deg": SHARP_DEG},
          "n_obs": {k: {"crease": int((sel[k] & (LAB == 1)).sum()),
                        "fabric": int((sel[k] & (LAB == 2)).sum())} for k in SUBSETS},
          "rows_2d": rows, "auc_2d": auc2d, "rows_3d": surfel_rows,
          "vote_rows": vote_rows, "half_pixel_control": hp_rows,
          "gradn_tau": {f"{k[0]}|q{k[1]:g}": float(np.mean(v))
                        for k, v in gradn_tau.items()},
          "verdict": verdict, "runtime_s": time.time() - t0}
    p = os.path.join(OUT, f"hybrid_step1_align_{args.scene}{tag}.json")
    json.dump(js, open(p, "w"), indent=1, default=float)
    np.savez_compressed(
        os.path.join(CACHE, f"hybrid_step1_{args.scene}{tag}.npz"),
        lab=LABv, vis=VISv, seed_idx=idx, views=np.array(views),
        mesh_theta=MESHTH.reshape(V, S), seedlab=seedlab,
        **{f"th3d_{n}_k{k}": t for (n, k), t in surfel_theta.items()},
        **{f"pass_{n}_{s}_{tk}_r{r}".replace(".", "p"): np.stack(l)
           for (n, s, tk, r), l in PASS.items()})
    print(f"wrote {p}")

    # ------------------------------------------------------------------- plot
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(len(SUBSETS), len(names) + 1,
                             figsize=(5.2 * (len(names) + 1), 4.2 * len(SUBSETS)),
                             squeeze=False)
    for i, sub in enumerate(SUBSETS):
        for j, name in enumerate(names):
            ax = axes[i][j]
            for tkey in sorted({k[2] for k in PASS if k[0] == name and
                                k[1] == "dihedral"}, key=float):
                rr = sorted([x for x in rows if x["arm"] == name and
                             x["signal"] == "dihedral" and x["tau"] == tkey and
                             x["subset"] == sub], key=lambda z: z["r"])
                ax.plot([x["r"] for x in rr], [x["R_crease"] for x in rr], "-o", ms=3,
                        label=f"R tau={tkey}")
                ax.plot([x["r"] for x in rr], [x["FPR_fabric"] for x in rr], "--s", ms=3,
                        label=f"FPR tau={tkey}")
            ax.axhline(0.80, color="k", ls=":", lw=1)
            ax.axhline(0.15, color="k", ls=":", lw=1)
            ax.set_xlabel("dilation radius r (px)"); ax.set_ylim(0, 1)
            ax.set_title(f"{name} / dihedral / {sub}", fontsize=9)
            ax.legend(fontsize=5, ncol=2)
        ax = axes[i][len(names)]
        for name in names:
            rr = [x for x in rows if x["arm"] == name and x["subset"] == sub]
            ax.scatter([x["FPR_fabric"] for x in rr], [x["R_crease"] for x in rr],
                       s=9, alpha=0.55, label=f"2D {name}")
        for m in args.models:
            n0 = os.path.basename(os.path.normpath(m))
            for k in args.surfel_k:
                rr = sorted([x for x in surfel_rows if x["model"] == n0 and x["k"] == k
                             and x["subset"] == sub], key=lambda z: z["FPR_fabric"])
                ax.plot([x["FPR_fabric"] for x in rr], [x["R_crease"] for x in rr],
                        "-", lw=1, label=f"3D {n0} k={k}")
        ax.add_patch(plt.Rectangle((0, 0.8), 0.15, 0.2, color="tab:green", alpha=0.18))
        ax.set_xlabel("FPR_fabric"); ax.set_ylabel("R_crease")
        ax.set_xlim(0, 1); ax.set_ylim(0, 1)
        ax.set_title(f"operating points — {sub}  (green = GO box)", fontsize=9)
        ax.legend(fontsize=5)
    plt.tight_layout()
    pp = os.path.join(OUT, f"hybrid_step1_align_{args.scene}{tag}.png")
    plt.savefig(pp, dpi=110)
    print(f"wrote {pp}\ntotal {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
