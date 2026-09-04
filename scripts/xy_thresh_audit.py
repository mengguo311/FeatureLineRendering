"""SHIP-PREP MILESTONE 1 — lego threshold-robustness audit.

*** EVAL / ANALYSIS ONLY.  Reads the GT mesh for LABELS.  No method path touched. ***

WHY
    src/mesh_oracle.py DEFINES the GT crease set as `face_adjacency_angles >= deg2rad(30)`.
    lego's mesh carries ONE family of ~213,711 edges at exactly 30.000 deg, which that
    threshold splits ~52/48 (110,655 just below, 103,056 just above) purely through the .obj's
    6-decimal vertex quantisation.  So the target set the pipeline is scored against is, for
    almost half of lego, decided by coordinate rounding.  Before any paper figure is cut we
    check whether the committed lego conclusions survive moving that threshold.

STAGES (cheap first; NEITHER stage needs a GPU)
  1  FREE      recall vs threshold, straight from the banked per-point arrays in
               out/xy/xy_expX_{lego,chair}*.npz (keys theta0_pt / rec3 / rec2 / seen_idx).
               Raising the oracle threshold only REMOVES crease points -- it never moves the
               ones that remain, and per-point visibility is a depth test independent of which
               edges are in the set -- so the recall of the frozen cloud at threshold t is
               exactly rec[theta0_pt >= t].mean().  No re-render, no mesh, no GPU.
  2  CPU       precision and F1 vs threshold.  These need the FULL crease point set (not just
               the TEST-visible subset), so the mesh is loaded once to rebuild the
               point -> source-edge dihedral map (byte-verified against mesh_oracle's own
               sampler, as in scripts/xy_expX.py).  Still no GPU.

The radius is HELD FIXED at the frozen a30 value across all thresholds.  Recomputing it per
threshold would change two things at once and confound the audit; the drift is reported
separately so the choice is visible rather than assumed.
"""
import argparse
import json
import os
import sys
import time

import numpy as np
from scipy.spatial import cKDTree

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
OUT = os.path.join(TIER1, "out", "xy")
CACHE = os.path.join(TIER1, "cache")
MESH_DIR = os.path.expanduser("~/3dgs_line/bcr/meshes/NeRF_Mesh")
DS, ANGLE0 = 0.0015, 30.0
THRESHOLDS = [30.00, 30.05, 31.0, 45.0]
SCENES = {"lego": ("_p1c", "dexprimary_p1c_cloud_lego.npz"),
          "chair": ("_ref40", "dexprimary_p1b_cloud_chair_ref40.npz")}
VIEWS_TEST = [5, 15, 25, 35, 45, 55, 65, 75, 85, 95]


def theta_per_point(scene, n_expect):
    """Rebuild the crease-point -> source-edge dihedral map, exactly as mesh_oracle samples."""
    import trimesh
    m = trimesh.load(f"{MESH_DIR}/{scene}_new.obj", process=True)
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate([g for g in m.geometry.values()])
    V = np.asarray(m.vertices, np.float64)
    adjE = np.asarray(m.face_adjacency_edges)
    deg = np.degrees(np.asarray(m.face_adjacency_angles))
    sel = np.where(deg >= ANGLE0)[0]
    A, B = V[adjE[sel, 0]], V[adjE[sel, 1]]
    L = np.linalg.norm(B - A, axis=1)
    npt = np.maximum(2, (L / DS).astype(int) + 1)
    assert npt.sum() == n_expect, (npt.sum(), n_expect)
    return np.repeat(deg[sel], npt).astype(np.float32)


def stage1():
    print("=" * 78)
    print("STAGE 1 — FREE PRE-CHECK (no GPU, no mesh): recall vs oracle threshold")
    print("=" * 78)
    res = {}
    for sc, (tag, _) in SCENES.items():
        z = np.load(os.path.join(OUT, f"xy_expX_{sc}{tag}.npz"))
        th, r3, r2 = z["theta0_pt"], z["rec3"], z["rec2"]
        base_n = int(len(th))
        rows = []
        print(f"\n[{sc}]  radius(frozen a30) = {float(z['radius']):.6f} world  "
              f"| TEST-visible crease pts @30 = {base_n}")
        print(f"  {'thresh':>7} {'n_target':>10} {'frac_kept':>10} "
              f"{'recall_3D':>10} {'recall_2D':>10} {'n_miss_3D':>10}")
        for t in THRESHOLDS:
            k = th >= t
            row = {"threshold_deg": t, "n_target_TESTvisible": int(k.sum()),
                   "frac_of_a30_target": round(float(k.mean()), 4),
                   "recall_3D": round(float(r3[k].mean()), 4),
                   "recall_2D_anyview": round(float(r2[k].mean()), 4),
                   "n_miss_3D": int((~r3[k]).sum())}
            rows.append(row)
            print(f"  {t:7.2f} {row['n_target_TESTvisible']:10d} "
                  f"{row['frac_of_a30_target']:10.4f} {row['recall_3D']:10.4f} "
                  f"{row['recall_2D_anyview']:10.4f} {row['n_miss_3D']:10d}")
        res[sc] = {"radius_world_frozen_a30": float(z["radius"]),
                   "n_TESTvisible_at_a30": base_n, "rows": rows}
    return res


def stage2(res):
    print("\n" + "=" * 78)
    print("STAGE 2 — CPU: precision / F1 vs threshold (mesh loaded for labels only)")
    print("=" * 78)
    for sc, (tag, cloudf) in SCENES.items():
        t0 = time.time()
        gt = np.load(os.path.join(CACHE, f"dexp0_gt_{sc}_a{int(ANGLE0)}.npz"))
        cp = gt["crease_pts"]
        thf = theta_per_point(sc, len(cp))
        seen = np.zeros(len(cp), bool)
        for v in VIEWS_TEST:
            seen[gt[f"idx{v}"]] = True
        z = np.load(os.path.join(OUT, f"xy_expX_{sc}{tag}.npz"))
        rad = float(z["radius"])
        zc = np.load(os.path.join(TIER1, "out", cloudf))
        keep = (zc["support"] >= 2) & zc["surface_keep"] & (zc["resid"] <= 1.0)
        P = zc["P"][keep]
        print(f"\n[{sc}] cloud {cloudf}: kept {len(P)}  (mesh map rebuilt in "
              f"{time.time()-t0:.0f}s)")
        print(f"  {'thresh':>7} {'n_full':>10} {'recall_3D':>10} {'prec_3D':>9} "
              f"{'F1':>8} {'zmed_drift':>11}")
        cams = None
        for row in res[sc]["rows"]:
            t = row["threshold_deg"]
            m_full = thf >= t
            m_seen = m_full & seen
            tg = cKDTree(cp[m_full])
            pr = float((tg.query(P, k=1, workers=-1)[0] <= rad).mean())
            rc = row["recall_3D"]
            row["n_target_full"] = int(m_full.sum())
            row["precision_3D"] = round(pr, 4)
            row["F1_3D"] = round(0.0 if (rc + pr) == 0 else 2 * rc * pr / (rc + pr), 4)
            if cams is None:
                from src import common
                cams, _ = common.load_cameras(sc)
            zs = []
            for v in VIEWS_TEST:
                idx = gt[f"idx{v}"]
                q = cp[idx[thf[idx] >= t]]
                if len(q):
                    zs.append((cams[v].w2c[:3, :3] @ q.T).T[:, 2] + cams[v].w2c[2, 3])
            zmed = float(np.median(np.concatenate(zs))) if zs else float("nan")
            row["radius_if_recomputed"] = round(1.5 * zmed / cams[VIEWS_TEST[0]].f, 6)
            drift = row["radius_if_recomputed"] / rad - 1.0
            row["radius_drift_frac"] = round(float(drift), 5)
            print(f"  {t:7.2f} {row['n_target_full']:10d} {rc:10.4f} {pr:9.4f} "
                  f"{row['F1_3D']:8.4f} {drift:+10.3%}")
    return res


def stage3(scenes=("lego", "chair"), thresholds=None):
    """MINIMAL RE-SCORE of the COMMITTED 2D pixel recall R@1.5 (out/CAP_RESULTS.md: lego
    0.5572, chair 0.7908) at each audited threshold.

    The committed number is NOT the 3D recall of stage 1.  It is the image-space pixel recall
    of the M1b headline stage at f=1.00 -- rasterise the kept linelet segments, distance-
    transform, and ask what fraction of GT crease PIXELS lie within 1.5 px.  That is the number
    behind the claim in scripts/cap_miss_attribution.py:10-11 that "on lego that bound is
    R@1.5 = 0.5572, i.e. R >= 0.65 is unreachable by ANY ranking method".

    KEY ECONOMY: the rasterised segment mask depends only on the linelets and the gaussian
    G-buffers -- NOT on the oracle threshold.  So the expensive part is computed ONCE per view
    and re-scored against each threshold's crease-pixel set, which is a strict subset of the
    a30 set.  One GPU pass over 10 TEST views per scene, then pure CPU.

    Also recomputes the frozen CAP gate rho_B2 = |B2| / (|B1| + |B2|) at each threshold, since
    that (< 0.30) is the actual committed decision gate in out/CAP_RESULTS.md.
    """
    import cv2
    from src import common, render, view_split, visibility  # noqa: F401
    from run_m1b import raster_segments
    from tune_lib import Harness
    TAU, B1_HI = 1.5, 3.0
    LINELETS = {"lego": "linelets_lego_cap_f1.00.npz",
                "chair": "linelets_chair_cap_f1.00.npz"}
    TH = thresholds or THRESHOLDS
    print("\n" + "=" * 78)
    print("STAGE 3 — MINIMAL RE-SCORE of the COMMITTED 2D pixel recall R@1.5 + rho_B2")
    print("  the frozen operating gate is JOINT: P@1.5 >= 0.85 AND R@1.5 >= 0.65")
    print("=" * 78)
    out = {}
    for sc in scenes:
        lp = os.path.join(TIER1, "out", LINELETS[sc])
        if not os.path.exists(lp):
            print(f"[{sc}] SKIP — no {LINELETS[sc]}")
            continue
        t0 = time.time()
        z = np.load(lp)
        P1, t1 = z["p"], z["t"]
        keep_t, l_mod_t = z["keep_tuned"], z["l_mod_tuned"]
        h = Harness(sc, views=tuple(view_split.TEST))
        g = common.load_gaussians(sc)
        kmask = render.defloat_mask(g["mu"], g["opacity"])
        X_pool, X_raw = g["mu"][kmask], g["mu"]
        gt = np.load(os.path.join(CACHE, f"dexp0_gt_{sc}_a{int(ANGLE0)}.npz"))
        cp = gt["crease_pts"]
        thf = theta_per_point(sc, len(cp))
        print(f"[{sc}] linelets {len(P1)} kept {int(keep_t.sum())}; pool {len(X_pool)} "
              f"raw {len(X_raw)} ({time.time()-t0:.0f}s)", flush=True)
        per_t = {t: {"rec": [], "prec": [], "n": [], "A": 0, "B0": 0, "B1": 0, "B2": 0,
                     "miss": 0, "vA": 0, "vB0": 0, "vB1": 0, "vB2": 0} for t in TH}
        for v in h.views:
            cam = h.cams[v]
            mask, _ = raster_segments(h, v, P1, t1, l_mod_t, keep=keep_t)
            sdt = (cv2.distanceTransform((~mask).astype(np.uint8), cv2.DIST_L2, 5)
                   if mask.any() else np.full(mask.shape, 1e9, np.float32))
            idx, uv = gt[f"idx{v}"], gt[f"uv{v}"]
            uvp = project_uv(X_pool, cam)
            uvr = project_uv(X_raw, cam)
            tp = cKDTree(uvp) if len(uvp) else None
            tr = cKDTree(uvr) if len(uvr) else None
            # CAP's most adverse reading: restrict both reference sets to gaussians VISIBLE in
            # this view, so an occluded back-surface gaussian cannot "cover" a front crease.
            # On lego this is the arm that comes closest to the 0.30 gate (0.2934), and on
            # chair it is ALREADY above it (0.3311) -- so it is the one worth sweeping.
            vp, _, _ = visibility.visible_mask(X_pool, cam, h.gbufs[v]["depth"])
            vr, _, _ = visibility.visible_mask(X_raw, cam, h.gbufs[v]["depth"])
            uvpv, uvrv = project_uv(X_pool[vp], cam), project_uv(X_raw[vr], cam)
            tpv = cKDTree(uvpv) if len(uvpv) else None
            trv = cKDTree(uvrv) if len(uvrv) else None
            for t in TH:
                sel = thf[idx] >= t
                if not sel.any():
                    continue
                u = np.clip(np.round(uv[sel, 0]).astype(int), 0, cam.W - 1)
                w = np.clip(np.round(uv[sel, 1]).astype(int), 0, cam.H - 1)
                m = np.zeros((cam.H, cam.W), bool)
                m[w, u] = True
                cvv, cuu = np.nonzero(m)                       # unique crease PIXELS
                d = sdt[cvv, cuu]
                per_t[t]["rec"].append(float((d <= TAU).mean()))
                per_t[t]["n"].append(int(len(cuu)))
                # PRECISION at the same tau: what fraction of the rasterised segment pixels
                # land on a GT crease.  The frozen operating gate is JOINT (P>=0.85 & R>=0.65),
                # so recall alone cannot decide it.
                cdt = cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5)
                sv, su = np.nonzero(mask)
                per_t[t]["prec"].append(float((cdt[sv, su] <= TAU).mean())
                                        if len(sv) else 0.0)
                ms = d > TAU
                per_t[t]["miss"] += int(ms.sum())
                if ms.any():
                    q = np.stack([cuu[ms], cvv[ms]], 1).astype(np.float64)
                    dp = tp.query(q, k=1)[0] if tp else np.full(len(q), 1e9)
                    dr = tr.query(q, k=1)[0] if tr else np.full(len(q), 1e9)
                    A = dp <= TAU
                    per_t[t]["A"] += int(A.sum())
                    per_t[t]["B0"] += int(((~A) & (dr <= TAU)).sum())
                    per_t[t]["B1"] += int(((~A) & (dr > TAU) & (dr <= B1_HI)).sum())
                    per_t[t]["B2"] += int(((~A) & (dr > B1_HI)).sum())
                    dpv = tpv.query(q, k=1)[0] if tpv else np.full(len(q), 1e9)
                    drv = trv.query(q, k=1)[0] if trv else np.full(len(q), 1e9)
                    Av = dpv <= TAU
                    per_t[t]["vA"] += int(Av.sum())
                    per_t[t]["vB0"] += int(((~Av) & (drv <= TAU)).sum())
                    per_t[t]["vB1"] += int(((~Av) & (drv > TAU) & (drv <= B1_HI)).sum())
                    per_t[t]["vB2"] += int(((~Av) & (drv > B1_HI)).sum())
        rows = []
        print(f"  {'thresh':>7} {'n_crease_px':>12} {'R@1.5(mean)':>12} {'P@1.5':>8} "
              f"{'rho_B2':>8} {'rhoB2_vis':>10} {'vis>=0.30':>10} {'joint gate':>11}")
        for t in TH:
            d = per_t[t]
            ntot = int(sum(d["n"]))
            rmean = float(np.mean(d["rec"])) if d["rec"] else float("nan")
            rpool = 1.0 - d["miss"] / max(ntot, 1)
            den = d["B1"] + d["B2"]
            den2 = d["B0"] + d["B1"] + d["B2"]
            vden = d["vB1"] + d["vB2"]
            vden2 = d["vB0"] + d["vB1"] + d["vB2"]
            pmean = float(np.mean(d["prec"])) if d["prec"] else float("nan")
            rows.append({"threshold_deg": t, "n_crease_pixels": ntot,
                         "P_at_1.5_mean_over_views": round(pmean, 4),
                         "joint_gate_P085_R065_met": bool(pmean >= 0.85 and rmean >= 0.65),
                         "R_gate_0.65_margin": round(0.65 - rmean, 4),
                         "R_at_1.5_mean_over_views": round(rmean, 4),
                         "R_at_1.5_pooled": round(rpool, 4),
                         "counts": {k: int(d[k]) for k in ("A", "B0", "B1", "B2")},
                         "n_miss_px": int(d["miss"]),
                         "rho_B2_spec_literal": round(d["B2"] / max(den, 1), 4),
                         "rho_B2_with_B0": round(d["B2"] / max(den2, 1), 4),
                         "rho_B2_visible_only": round(d["vB2"] / max(vden, 1), 4),
                         "rho_B2_visible_only_with_B0": round(d["vB2"] / max(vden2, 1), 4),
                         "rho_B2_visible_only_CROSSES_0.30":
                             bool(d["vB2"] / max(vden, 1) >= 0.30)})
            print(f"  {t:7.2f} {ntot:12d} {rmean:12.4f} {pmean:8.4f} "
                  f"{rows[-1]['rho_B2_spec_literal']:8.4f} "
                  f"{rows[-1]['rho_B2_visible_only']:10.4f} "
                  f"{str(rows[-1]['rho_B2_visible_only_CROSSES_0.30']):>10} "
                  f"{str(rows[-1]['joint_gate_P085_R065_met']):>11}")
        out[sc] = {"linelets": LINELETS[sc], "rows": rows,
                   "seconds": round(time.time() - t0, 1)}
    return out


def project_uv(P, cam, margin=64.0):
    """same projection+frustum filter cap_miss_attribution.py uses."""
    from src import common
    uv, _ = common.project(P, cam)
    z = (cam.w2c[:3, :3] @ P.T).T[:, 2] + cam.w2c[2, 3]
    ok = (z > 1e-6) & np.isfinite(uv).all(1) & (uv[:, 0] > -margin) \
        & (uv[:, 0] < cam.W + margin) & (uv[:, 1] > -margin) & (uv[:, 1] < cam.H + margin)
    return uv[ok]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="both", choices=["1", "2", "3", "both", "all"])
    ap.add_argument("--thresholds", default="", help="override sweep (out-of-spec extension)")
    ap.add_argument("--out_name", default="xy_thresh_audit.json")
    args = ap.parse_args()
    res = stage1() if args.stage != "3" else {}
    if args.stage in ("2", "both", "all"):
        res = stage2(res)
    TH = [float(x) for x in args.thresholds.split(",")] if args.thresholds else None
    s3 = stage3(thresholds=TH) if args.stage in ("3", "all") else None
    out = {"thresholds_deg": THRESHOLDS, "angle_deg_frozen": ANGLE0,
           "radius_policy": "held fixed at the frozen a30 value; drift reported separately",
           "scenes": res}
    if s3 is not None:
        out["stage3_committed_2D_pixel_recall"] = s3
    if TH:
        out["EXTENSION_out_of_frozen_sweep"] = True
        out["thresholds_deg"] = TH
    p = os.path.join(OUT, args.out_name)
    json.dump(out, open(p, "w"), indent=1)
    print(f"\n[audit] wrote {p}")


if __name__ == "__main__":
    main()
