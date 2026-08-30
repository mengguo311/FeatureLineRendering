"""tier1/scripts/diag2dgs.py — DIAG-2DGS: does 2DGS surface geometry separate lego's decal
distractors from true creases, where the TEED image prior could not?

*** EVAL / DIAGNOSTIC.  It reads the GT mesh (tune_lib.Harness -> mesh_oracle) for LABELS
    ONLY, exactly as diag2dgs_spec.md permits.  It defines no method, adds no method-path
    file, and modifies nothing that is committed. ***

WHY THIS EXISTS
    TGAP established that the frozen TEED image prior is at chance on lego (AUC 0.502-0.542)
    and BELOW chance conditional on the multi-view inlier ratio the prune already uses
    (within-decile AUC 0.42-0.47).  The cause it measured: lego's strongest MULTI-VIEW-
    CONSISTENT image edges are printed decals and stud fillets, i.e. the distractors are
    exactly the candidates both an image prior and a multi-view-consensus statistic reward.
    The one signal orthogonal to both is 3-D SURFACE SHAPE: paint is flat, creases bend.
    Vanilla 3DGS cannot supply it (its geometry is texture-baked); 2DGS could, on chair
    (PLAN1_RESULTS.md STEP A: on GT-flat printed fabric the 2DGS rendered-normal ribbon
    dihedral reads p50 1.80 / p95 7.29 deg against crease p50 24.5, AUC 0.967, vs vanilla
    3DGS 11.9 / 38.5, AUC 0.696).  Does that transfer to lego's studs?

THREE SIGNALS, BECAUSE ONE CANNOT ANSWER THE QUESTION ASKED
  (1) surfel3d   the spec's estimator: cross-linelet dihedral between the mean 2DGS SURFEL
                 normals on the two sides of the linelet, sampled in 3-D.  This is the arm
                 the frozen gate is read on.
  (2) ribbon2dgs the image-space bilateral-ribbon dihedral on the 2DGS RENDERED NORMAL map,
                 i.e. gate2dgs.ribbon_normal_theta, reused unchanged.  This is the estimator
                 the chair result was measured with.  It is included because
                 HYBRID_RESULTS.md already measured that on chair the 3-D nearest-surfel
                 variant is much WEAKER than the rendered-buffer one (theta_max AUC 0.51-0.55
                 on all/interior, 0.63 refined, versus 0.856/0.967).  Without arm (2) a
                 NO-GO on arm (1) could not be attributed to lego's geometry rather than to
                 a known-weaker estimator.
  (3) ribbon3dgs the SAME image-space ribbon on the VANILLA 3DGS normal map -- the control
                 that says whether 2DGS bought anything at all on lego, parallel to the
                 chair table above.

  (4) mesh       the SAME 3-D estimator with the 2DGS surfel cloud replaced by the GT mesh's
                 face centroids / face normals / face areas.  It is PARTIALLY CIRCULAR --
                 mesh_oracle defines a crease as a mesh edge of dihedral >= 30 deg, so the
                 labels derive from the same geometry -- and PLAN1_RESULTS.md flagged exactly
                 that when it ran a mesh arm.  It is run anyway because it is the only thing
                 that can separate "2DGS geometry is too blurred" from "these two label
                 classes are not separable by ANY geometry", and a below-chance result cannot
                 be read without knowing which.  It is never quoted as a ceiling.

  Each of (1) and (4) is ALSO reported as a SIDE-SPLIT-FREE statistic, `spread`: the angular
  dispersion of the undirected normals in the ball, degrees(arccos(sqrt(lambda_1))) of the
  weighted scatter sum_j w_j n_j n_j^T.  Flat patch -> 0; two faces meeting at theta ->
  ~theta/2; curved patch -> the curvature times the ball radius.  It needs no tangent and no
  side split, so it cannot be blamed on either.

THE surfel3d SAMPLING RECIPE, STATED IN FULL (the spec asks for it explicitly)
    For linelet i with centre p, unit tangent t and half-length l:
      radius        R = rho * median(l) over the candidate set -- a FIXED radius, as the spec
                    says; the per-linelet variant R_i = rho * l_i is reported as a sensitivity
      candidates    2DGS surfels with ||x - p|| <= R, opacity > 0.1
      exclusion     drop surfels whose perpendicular distance to the linelet's infinite line
                    is <= xi * R, so surfels straddling the crease cannot pollute both sides
      in-plane      d_j = (x_j - p) - ((x_j - p).t) t, then centred by their mean
      SIDE SPLIT    e = first principal component of the centred in-plane offsets; side =
                    sign(d_j . e).  This is view-independent and needs no surface: on a
                    crease the two sheets leave the line in two different directions, so the
                    offset cloud is an L and its first PC separates them; on a flat patch the
                    offsets fill the tangent plane and any split gives two halves of the same
                    plane, i.e. dtheta ~ 0, which is the correct answer.
      side normal   surfel normals are UNDIRECTED (2DGS flips them toward the camera at
                    render time), so a plain mean is ill-defined.  Each side's normal is the
                    leading eigenvector of the opacity-weighted scatter sum_j w_j n_j n_j^T,
                    which is the standard mean of undirected directions.
      dtheta        degrees(arccos(|n_L . n_R|)) in [0,90], the same |.| convention
                    gate2dgs._ribbon_normal_theta uses
      validity      at least n_min surfels on EACH side, else the linelet is unmeasurable and
                    is excluded from every arm's AUC so all arms score the same population.
      VISIBILITY    --visible_only restricts the cloud to elements that are the FRONT surface
                    in at least one TRAIN view.  This is not decoration.  A ball of radius R
                    around a point on a lego tile reaches THROUGH the tile: lego's walls are
                    ~0.01-0.02 world thick, so the unfiltered ball mixes the outer surface
                    with the inner one and with interior tube geometry, whose normals are
                    opposed or perpendicular.  Under the |.| convention that reads as a 90 deg
                    "dihedral" with no visible crease anywhere near, which is exactly the
                    artefact the unfiltered numbers show.  TRAIN views are used so the
                    reported split never enters the signal.
    rho, xi and n_min are chosen on VAL views only and frozen; the full TEST sweep is printed
    beside the frozen value so it is visible whether the verdict depends on the choice.

    2DGS surfel normal = third column of build_rotation(q).  2DGS discs carry two scales and
    lie in their local xy-plane, and the rasteriser takes exactly this vector
    (forward.cu:113, `normal = transformVec4x3({L[2].x, L[2].y, L[2].z}, viewmatrix)` with
    L = R diag(s0,s1,1)).  The derivation is not assumed: --selfcheck measures the angle
    between it and the RENDERED normal buffer at each surfel's own projection.

LABELS (mesh, eval-only).  Per linelet, over the views of the reported split in which it is
visible (vanilla z-buffer, the same visibility TGAP used), d = median distance from its
projected centre to the nearest GT crease pixel, read off the SAME cdt the published
recall is computed from.
    TrueCrease       d <= 1.5 px
    DecalDistractor  d >  3.0 px AND TEED-high-confidence
"TEED-high-confidence" is anchored on TEED's PUBLISHED threshold in this repo rather than on
a new tuned number: the linelet's TEED probability exceeds 0.5 in at least half of the views
where it is visible (the E_frac_0p5 field TGAP already computed).  Quantile-based variants
are reported as a sensitivity.
"""
import argparse
import json
import os
import sys

import cv2
import numpy as np
from scipy.spatial import cKDTree

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))

from src import common, render, visibility, view_split, gate2dgs, render2dgs   # noqa: E402

OUT = os.path.join(TIER1, "out")


# ------------------------------------------------------------------------ small utilities
def auc(score, label):
    """Mann-Whitney AUC with ties averaged; nan if a class is empty."""
    s = np.asarray(score, np.float64)
    y = np.asarray(label, bool)
    n1, n0 = int(y.sum()), int((~y).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    order = np.argsort(s, kind="stable")
    sv = s[order]
    rank = np.empty(len(s))
    i = 0
    while i < len(sv):
        j = i
        while j + 1 < len(sv) and sv[j + 1] == sv[i]:
            j += 1
        rank[order[i:j + 1]] = 0.5 * (i + j) + 1.0
        i = j + 1
    return float((rank[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def load_surfel_normals(model_path, opa_min=0.1):
    """2DGS surfel centres, UNDIRECTED world normals, opacity. Mesh-free."""
    import torch
    render2dgs._ensure_path()
    from utils.general_utils import build_rotation
    g2, pipe, meta = render2dgs.load_2dgs(model_path)
    with torch.no_grad():
        mu = g2.get_xyz.detach().float()
        q = g2.get_rotation.detach().float()
        n = build_rotation(q)[:, :, 2]                       # disc normal, world space
        n = n / n.norm(dim=-1, keepdim=True).clamp_min(1e-12)
        op = g2.get_opacity.detach().float().ravel()
        sc = g2.get_scaling.detach().float()
        out = {"mu": mu.cpu().numpy().astype(np.float64),
               "n": n.cpu().numpy().astype(np.float64),
               "opacity": op.cpu().numpy().astype(np.float64),
               "scale": sc.cpu().numpy().astype(np.float64), "meta": meta}
    keep = out["opacity"] > opa_min
    out["keep"] = keep
    del g2
    torch.cuda.empty_cache()
    return out, pipe


def visible_mask_cloud(X, cams, views, depth_of_view, rel_tol=0.02, chunk=200000):
    """True for cloud elements that are the FRONT surface in at least one of `views`."""
    vis = np.zeros(len(X), bool)
    for v in views:
        cam = cams[v]
        d = depth_of_view(v)
        for a in range(0, len(X), chunk):
            b = min(a + chunk, len(X))
            uv, z = common.project(X[a:b], cam)
            u = np.round(uv[:, 0]).astype(int)
            w = np.round(uv[:, 1]).astype(int)
            inb = (u >= 0) & (u < cam.W) & (w >= 0) & (w < cam.H) & (z > 1e-6)
            uu = np.clip(u, 0, cam.W - 1)
            ww = np.clip(w, 0, cam.H - 1)
            zb = d[ww, uu]
            ok = inb & np.isfinite(zb) & (np.abs(zb - z) < rel_tol * z)
            vis[a:b] |= ok
    return vis


def normal_spread(N, W):
    """Angular dispersion (deg) of UNDIRECTED unit normals: arccos(sqrt(lambda_1)) of the
    weighted scatter, in [0,~55]. 0 = perfectly flat."""
    S = (N * W[:, None]).T @ N / max(W.sum(), 1e-12)
    lam = np.linalg.eigvalsh(S)[-1]
    return float(np.degrees(np.arccos(np.sqrt(np.clip(lam, 0.0, 1.0)))))


def leading_dir(N, W):
    """Mean of UNDIRECTED unit vectors N[k,3] with weights W[k]: leading eigenvector of
    sum_k w_k n_k n_k^T."""
    S = (N * W[:, None]).T @ N
    w, V = np.linalg.eigh(S)
    return V[:, 2]


# ------------------------------------------------------------------- signal 1: surfel3d
def surfel3d_dihedral(P, T, L, cloud, rho=3.0, xi=0.25, n_min=5, per_linelet=False,
                      tree=None, verbose=True, name="surfel3d", cap=400):
    """(dtheta[M], spread[M], ok[M]). cloud = dict(mu[N,3], n[N,3], w[N]).
    See the module docstring for the full recipe."""
    mu, nn, op = cloud["mu"], cloud["n"], cloud["w"]
    tree = tree if tree is not None else cKDTree(mu)
    Rg = rho * float(np.median(L))
    M = len(P)
    th = np.full(M, np.nan)
    sp = np.full(M, np.nan)
    ok = np.zeros(M, bool)
    nca = np.zeros(M, np.int8)
    radii = (rho * np.asarray(L, np.float64)) if per_linelet else np.full(M, Rg)
    # one ball query per distinct radius keeps this a few seconds even at M ~ 1e5
    balls = tree.query_ball_point(P, radii, workers=-1)
    for i, b in enumerate(balls):
        if len(b) < 2 * n_min:
            continue
        b = np.asarray(b)
        if len(b) > cap:
            # bounded work per linelet: keep the `cap` nearest elements inside the ball.
            # Deterministic, and it only binds for the 2.03M-face GT mesh arm (2DGS balls
            # hold ~1e2 surfels); the truncation radius is reported as `cap_binding_frac`.
            dd = np.linalg.norm(mu[b] - P[i], axis=1)
            b = b[np.argsort(dd, kind="stable")[:cap]]
            nca[i] = 1
        off = mu[b] - P[i]
        al = off @ T[i]
        d = off - al[:, None] * T[i]                        # in-plane offsets
        perp = np.linalg.norm(d, axis=1)
        m = perp > xi * radii[i]
        if m.sum() < 2 * n_min:
            continue
        b, d = b[m], d[m]
        sp[i] = normal_spread(nn[b], op[b])
        dc = d - d.mean(0)
        # first PC of the centred in-plane offsets, restricted to the plane perp to t
        _, _, Vt = np.linalg.svd(dc, full_matrices=False)
        e = Vt[0] - (Vt[0] @ T[i]) * T[i]
        ne = np.linalg.norm(e)
        if ne < 1e-12:
            continue
        e /= ne
        side = (dc @ e) > 0
        if side.sum() < n_min or (~side).sum() < n_min:
            continue
        nL = leading_dir(nn[b[side]], op[b[side]])
        nR = leading_dir(nn[b[~side]], op[b[~side]])
        th[i] = np.degrees(np.arccos(np.clip(abs(float(nL @ nR)), 0.0, 1.0)))
        ok[i] = True
    if verbose:
        print(f"    [{name}] rho={rho} xi={xi} n_min={n_min} "
              f"{'per-linelet' if per_linelet else f'R={Rg:.5f}'}  "
              f"measurable {ok.mean():.4f}  cap-binding {nca.mean():.3f}", flush=True)
    return th, sp, ok


# --------------------------------------------------- signal 2/3: image-space ribbon arms
def ribbon_dihedral(P, T, h, views, normal_of_view, fg_of_view):
    """Median over the split's visible views of gate2dgs.ribbon_normal_theta at the
    linelet's projected centre, with the across-direction perpendicular to the PROJECTED
    tangent. Returns (theta[M], n_ok[M])."""
    M = len(P)
    acc = [[] for _ in range(M)]
    for v in views:
        cam = h.cams[v]
        vis, uv, _ = visibility.visible_mask(P, cam, h.gbufs[v]["depth"])
        if not vis.any():
            continue
        a = P + 1e-3 * T
        uva, _ = common.project(a, cam)
        du = uva - uv
        nrm = np.linalg.norm(du, axis=1)
        good = vis & (nrm > 1e-9)
        idx = np.where(good)[0]
        tx, ty = du[idx, 0] / nrm[idx], du[idx, 1] / nrm[idx]      # projected tangent
        dirx, diry = -ty, tx                                        # across the linelet
        th, okv = gate2dgs.ribbon_normal_theta(
            uv[idx, 0].astype(np.float32), uv[idx, 1].astype(np.float32),
            dirx, diry, normal_of_view[v], fg_of_view[v])
        for k, i in enumerate(idx):
            if okv[k] and np.isfinite(th[k]):
                acc[i].append(th[k])
    out = np.full(M, np.nan)
    nok = np.zeros(M, np.int64)
    for i, a in enumerate(acc):
        nok[i] = len(a)
        if a:
            out[i] = float(np.median(a))
    return out, nok


# --------------------------------------------------------------------------- the driver
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="lego")
    ap.add_argument("--f", type=float, default=0.50)
    ap.add_argument("--model2dgs", default=os.path.join(OUT, "2dgs_lego"))
    ap.add_argument("--split", default="test", choices=["test", "val"])
    ap.add_argument("--rho", type=float, default=3.0)
    ap.add_argument("--xi", type=float, default=0.25)
    ap.add_argument("--n_min", type=int, default=5)
    ap.add_argument("--sweep", action="store_true",
                    help="score a (rho, xi, n_min) grid instead of one point")
    ap.add_argument("--rho_list", type=float, nargs="*",
                    default=[0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0])
    ap.add_argument("--xi_list", type=float, nargs="*", default=[0.25])
    ap.add_argument("--nmin_list", type=int, nargs="*", default=[5])
    ap.add_argument("--selfcheck", action="store_true",
                    help="validate the surfel-normal derivation against the rendered "
                         "normal buffer before anything else")
    ap.add_argument("--no_ribbon", action="store_true")
    ap.add_argument("--visible_only", action="store_true",
                    help="restrict both clouds to elements that are the front surface in at "
                         "least one TRAIN view (see the module docstring: lego's thin walls "
                         "make the unfiltered ball reach through the object)")
    ap.add_argument("--vis_views_mesh", type=int, default=20,
                    help="how many evenly spaced TRAIN views the (expensive) GT-mesh "
                         "visibility pass uses")
    ap.add_argument("--mesh_arm", action="store_true",
                    help="add the partially-circular GT-mesh arm (same 3-D estimator, mesh "
                         "faces as the cloud). Needed to tell a blurred reconstruction "
                         "apart from inseparable labels.")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    from tune_lib import Harness                                     # EVAL ONLY (mesh)
    views = {"val": view_split.VAL, "test": view_split.TEST}[args.split]
    h = Harness(args.scene, views=tuple(views))

    z = np.load(os.path.join(OUT, f"tgap_pull_{args.scene}_f{args.f:.2f}.npz"))
    P, T, L = z["p"], z["t"], z["l"]
    Efrac = z["E_frac_0p5"] if "E_frac_0p5" in z.files else None
    E = z["E"]
    print(f"[{args.scene}] {len(P)} TGAP linelets at f={args.f}, split={args.split} "
          f"({len(views)} views)", flush=True)

    S, pipe = load_surfel_normals(args.model2dgs)
    print(f"  [2dgs] {len(S['mu'])} surfels, {int(S['keep'].sum())} above opacity 0.1  "
          f"({S['meta']['model_path']} it={S['meta']['iteration']})", flush=True)

    res = {"scene": args.scene, "f": args.f, "split": args.split, "views": list(views),
           "n_linelets": int(len(P)), "model2dgs": S["meta"],
           "surfel_median_scale_max": float(np.median(S["scale"][S["keep"]].max(1))),
           "linelet_median_half_length": float(np.median(L))}

    # ---- 0. self-check: is the surfel normal the vector the renderer uses? --------------
    # The absolute agreement is capped by alpha compositing (a pixel blends many surfels), so
    # the check is made DISCRIMINATIVE: the same measurement is run for all three columns of
    # build_rotation(q). Only the true normal should agree at all.
    if args.selfcheck:
        import torch
        g2, pipe2, meta2 = render2dgs.load_2dgs(args.model2dgs)
        from utils.general_utils import build_rotation
        with torch.no_grad():
            Rq = build_rotation(g2.get_rotation.detach().float()).cpu().numpy()
        cols = {f"col{c}": Rq[:, :, c][S["keep"]] for c in range(3)}
        angs = []
        for v in views[:3]:
            gb2 = render2dgs.render_gbuffer_2dgs(g2, pipe2, h.cams[v],
                                                 bg_white=meta2.get("white_background", True))
            nb = gb2["normal"].detach().cpu().numpy()
            dep = gb2["depth"].detach().cpu().numpy()
            mu = S["mu"][S["keep"]]
            uv, zc = common.project(mu, h.cams[v])
            u = np.round(uv[:, 0]).astype(int)
            w = np.round(uv[:, 1]).astype(int)
            inb = (u >= 0) & (u < h.cams[v].W) & (w >= 0) & (w < h.cams[v].H) & (zc > 1e-6)
            uu, ww = u[inb], w[inb]
            front = np.abs(dep[ww, uu] - zc[inb]) < 0.02 * zc[inb]   # surfel is the visible one
            nb_s = nb[ww[front], uu[front]]
            row = {}
            for k, C in cols.items():
                ns = C[inb][front]
                c = np.abs((nb_s * ns).sum(1)) / (np.linalg.norm(nb_s, axis=1) *
                                                  np.linalg.norm(ns, axis=1) + 1e-12)
                row[k] = np.degrees(np.arccos(np.clip(c, 0, 1)))
            angs.append(row)
        sc = {}
        for k in cols:
            a = np.concatenate([r[k] for r in angs])
            sc[k] = {"n": int(len(a)), "median": float(np.median(a)),
                     "p90": float(np.percentile(a, 90)),
                     "frac_under_10deg": float((a < 10).mean())}
            print(f"  [selfcheck] build_rotation(q)[:,:,{k[-1]}] vs RENDERED normal: "
                  f"median {sc[k]['median']:6.2f} deg  p90 {sc[k]['p90']:6.2f}  "
                  f"{100*sc[k]['frac_under_10deg']:5.1f}% under 10 deg  (n={len(a)})",
                  flush=True)
        res["selfcheck_surfel_vs_rendered_normal_deg"] = sc
        res["selfcheck_note"] = ("absolute agreement is capped by alpha compositing; the "
                                 "column-2 arm must be far better than columns 0/1 or the "
                                 "derivation is wrong")
        del g2
        torch.cuda.empty_cache()

    # ---- 1. labels (mesh, eval-only) ---------------------------------------------------
    dists = [[] for _ in range(len(P))]
    nvis = np.zeros(len(P), np.int64)
    for v in views:
        vis, uv, _ = visibility.visible_mask(P, h.cams[v], h.gbufs[v]["depth"])
        cu, cv_, cdt = h.crease[v]
        u = np.clip(np.round(uv[:, 0]).astype(int), 0, cdt.shape[1] - 1)
        w = np.clip(np.round(uv[:, 1]).astype(int), 0, cdt.shape[0] - 1)
        d = cdt[w, u]
        nvis += vis
        for i in np.where(vis)[0]:
            dists[i].append(d[i])
    dmed = np.array([np.median(x) if x else np.inf for x in dists])
    seen = nvis > 0
    teed_hi = (Efrac >= 0.5) if Efrac is not None else (E >= np.quantile(E, 0.75))
    crease = seen & (dmed <= 1.5)
    decal = seen & (dmed > 3.0) & teed_hi
    res["labels"] = {
        "rule": "TrueCrease: median over visible split views of GT-crease distance <= 1.5 px; "
                "DecalDistractor: median > 3.0 px AND TEED prob > 0.5 in >= half the views "
                "it is visible in",
        "n_seen": int(seen.sum()), "n_crease": int(crease.sum()), "n_decal": int(decal.sum()),
        "n_teed_high": int((seen & teed_hi).sum()),
        "n_far_not_teed_high": int((seen & (dmed > 3.0) & ~teed_hi).sum())}
    print(f"  [labels] seen {int(seen.sum())} | TrueCrease {int(crease.sum())} | "
          f"DecalDistractor {int(decal.sum())} "
          f"(TEED-high {int((seen & teed_hi).sum())})", flush=True)

    # ---- 2. signals --------------------------------------------------------------------
    keep2 = S["keep"].copy()
    if args.visible_only:
        import torch
        g2v, pipev, metav = render2dgs.load_2dgs(args.model2dgs)
        cams_all, _ = common.load_cameras(args.scene)
        tv = list(view_split.TRAIN)
        dcache = {}

        def dep2(v):
            if v not in dcache:
                gb = render2dgs.render_gbuffer_2dgs(
                    g2v, pipev, cams_all[v], bg_white=metav.get("white_background", True))
                dcache[v] = gb["depth"].detach().cpu().numpy()
                del gb
            return dcache[v]

        vis2 = visible_mask_cloud(S["mu"][keep2], cams_all, tv, dep2)
        idx2 = np.where(keep2)[0]
        keep2 = np.zeros(len(keep2), bool)
        keep2[idx2[vis2]] = True
        print(f"  [visible_only] 2DGS surfels {len(idx2)} -> {int(keep2.sum())} "
              f"front-surface in >=1 of {len(tv)} TRAIN views", flush=True)
        res["visible_only_2dgs"] = {"before": int(len(idx2)), "after": int(keep2.sum()),
                                    "n_train_views": len(tv)}
        del g2v, dcache
        torch.cuda.empty_cache()
    cloud2 = {"mu": S["mu"][keep2], "n": S["n"][keep2], "w": S["opacity"][keep2]}
    tree = cKDTree(cloud2["mu"])
    sig = {}
    grid = ([(r, x, n) for r in args.rho_list for x in args.xi_list
             for n in args.nmin_list] if args.sweep else [(args.rho, args.xi, args.n_min)])
    for (r, x, n) in grid:
        th, sp, okm = surfel3d_dihedral(P, T, L, cloud2, rho=r, xi=x, n_min=n, tree=tree)
        sig[f"surfel3d_rho{r:g}_xi{x:g}_nmin{n}"] = (th, okm)
        sig[f"spread2dgs_rho{r:g}_xi{x:g}_nmin{n}"] = (sp, okm)
    if not args.sweep:
        th, sp, okm = surfel3d_dihedral(P, T, L, cloud2, rho=args.rho, xi=args.xi,
                                        n_min=args.n_min, per_linelet=True, tree=tree)
        sig["surfel3d_perlinelet"] = (th, okm)

    # ---- GT-mesh arm: SAME estimator, mesh face centroids/normals/areas as the cloud.
    #      PARTIALLY CIRCULAR (see the module docstring); never quoted as a ceiling.
    if args.mesh_arm:
        from src.mesh_oracle import MESH_DIR                          # EVAL ONLY
        import trimesh
        m = trimesh.load(f"{MESH_DIR}/{args.scene}_new.obj", process=True)
        if isinstance(m, trimesh.Scene):
            m = trimesh.util.concatenate([g for g in m.geometry.values()])
        cloudm = {"mu": np.asarray(m.triangles_center, np.float64),
                  "n": np.asarray(m.face_normals, np.float64),
                  "w": np.asarray(m.area_faces, np.float64)}
        print(f"  [mesh] {len(cloudm['mu'])} faces, median edge-scale "
              f"{np.sqrt(np.median(cloudm['w'])):.5f}", flush=True)
        if args.visible_only:
            from src.mesh_oracle import MeshOracle                    # EVAL ONLY
            o = MeshOracle(args.scene)
            cams_all, _ = common.load_cameras(args.scene)
            tv = list(view_split.TRAIN)
            step = max(1, len(tv) // args.vis_views_mesh)
            tvm = tv[::step][:args.vis_views_mesh]
            mcache = {}

            def depm(v):
                if v not in mcache:
                    dd = o.render_depth(cams_all[v], view_key=("diagvis", v))
                    mcache[v] = (dd.detach().cpu().numpy()
                                 if hasattr(dd, "detach") else np.asarray(dd))
                return mcache[v]

            vm = visible_mask_cloud(cloudm["mu"], cams_all, tvm, depm)
            print(f"  [visible_only] mesh faces {len(vm)} -> {int(vm.sum())} "
                  f"front-surface in >=1 of {len(tvm)} TRAIN views", flush=True)
            res["visible_only_mesh"] = {"before": int(len(vm)), "after": int(vm.sum()),
                                        "n_train_views": len(tvm)}
            cloudm = {k: v[vm] for k, v in cloudm.items()}
            del o, mcache
        treem = cKDTree(cloudm["mu"])
        for (r, x, n) in grid:
            th, sp, okm = surfel3d_dihedral(P, T, L, cloudm, rho=r, xi=x, n_min=n,
                                            tree=treem, name="mesh3d")
            sig[f"mesh3d_rho{r:g}_xi{x:g}_nmin{n}"] = (th, okm)
            sig[f"spreadmesh_rho{r:g}_xi{x:g}_nmin{n}"] = (sp, okm)

    if not args.no_ribbon:
        import torch
        g2, pipe2, meta2 = render2dgs.load_2dgs(args.model2dgs)
        n2, n1, fg = {}, {}, {}
        for v in views:
            gb2 = render2dgs.render_gbuffer_2dgs(g2, pipe2, h.cams[v],
                                                 bg_white=meta2.get("white_background", True))
            n2[v] = gb2["normal"].detach().cpu().numpy().astype(np.float32)
            gb1 = h.gbufs[v]
            n1[v] = gb1["normal"].detach().cpu().numpy().astype(np.float32)
            # ONE foreground mask, from the VANILLA render, for BOTH ribbon arms, so the two
            # differ only in the normal field. 2DGS alpha is not an object mask (white-bg
            # splat canvas, gate2dgs docstring).
            fg[v] = (gb1["alpha"].detach().cpu().numpy() > 0.5)
            del gb2
        del g2
        torch.cuda.empty_cache()
        th, nok = ribbon_dihedral(P, T, h, views, n2, fg)
        sig["ribbon2dgs"] = (th, nok > 0)
        th, nok = ribbon_dihedral(P, T, h, views, n1, fg)
        sig["ribbon3dgs_vanilla"] = (th, nok > 0)

    # ---- 3. score ----------------------------------------------------------------------
    common_ok = np.ones(len(P), bool)
    for k, (th, okm) in sig.items():
        common_ok &= okm
    res["n_common_measurable"] = int(common_ok.sum())
    rows = {}
    for k, (th, okm) in sig.items():
        for scope, m in (("own", okm), ("common", common_ok)):
            c = crease & m
            d = decal & m
            if c.sum() < 10 or d.sum() < 10:
                rows[f"{k}|{scope}"] = {"n_crease": int(c.sum()), "n_decal": int(d.sum()),
                                        "AUC": float("nan")}
                continue
            lab = np.concatenate([np.ones(int(c.sum()), bool), np.zeros(int(d.sum()), bool)])
            sc = np.concatenate([th[c], th[d]])
            rows[f"{k}|{scope}"] = {
                "n_crease": int(c.sum()), "n_decal": int(d.sum()),
                "measurable_frac": float(m.mean()),
                "AUC": auc(sc, lab),
                "median_crease": float(np.median(th[c])),
                "median_decal": float(np.median(th[d])),
                "median_gap": float(np.median(th[c]) - np.median(th[d])),
                "p05_crease": float(np.percentile(th[c], 5)),
                "p95_decal": float(np.percentile(th[d], 95))}
    res["signals"] = rows

    # ---- the premise itself: are the DecalDistractors actually FLAT? -------------------
    prem = {}
    for k, (th, okm) in sig.items():
        if not k.startswith("spreadmesh") and not k.startswith("spread2dgs"):
            continue
        m = okm & decal
        mc = okm & crease
        if m.sum() < 10:
            continue
        prem[k] = {"n_decal": int(m.sum()),
                   "decal_frac_spread_under_5deg": float((th[m] < 5.0).mean()),
                   "decal_frac_spread_under_10deg": float((th[m] < 10.0).mean()),
                   "decal_median_spread": float(np.median(th[m])),
                   "crease_frac_spread_under_5deg": float((th[mc] < 5.0).mean()),
                   "crease_median_spread": float(np.median(th[mc]))}
    res["flatness_premise"] = prem

    # ---- sensitivity of the verdict to how "TEED-high-confidence" is defined -----------
    tv = {"frac@0.5>=0.5 (FROZEN)": teed_hi}
    if Efrac is not None:
        tv["frac@0.5>=0.75"] = Efrac >= 0.75
        tv["frac@0.5>=0.90"] = Efrac >= 0.90
    tv["E>=q50"] = E >= np.quantile(E, 0.50)
    tv["E>=q75"] = E >= np.quantile(E, 0.75)
    tv["E>=q90"] = E >= np.quantile(E, 0.90)
    key = f"surfel3d_rho{args.rho:g}_xi{args.xi:g}_nmin{args.n_min}"
    tvres = {}
    for kname, hi in tv.items():
        dd = seen & (dmed > 3.0) & hi
        for sname in [k for k in sig if k.startswith(("surfel3d_rho", "spreadmesh_rho",
                                                      "mesh3d_rho", "ribbon"))]:
            th, okm = sig[sname]
            c, d2 = crease & okm, dd & okm
            if c.sum() < 10 or d2.sum() < 10:
                continue
            lab = np.concatenate([np.ones(int(c.sum()), bool),
                                  np.zeros(int(d2.sum()), bool)])
            tvres.setdefault(kname, {})[sname] = {
                "n_decal": int(d2.sum()),
                "AUC": auc(np.concatenate([th[c], th[d2]]), lab),
                "median_gap": float(np.median(th[c]) - np.median(th[d2]))}
    res["teed_threshold_sensitivity"] = tvres
    print(f"\n{'TEED-high definition':26s} {'n_decal':>8s}  AUC / median gap per signal")
    for kname, r in tvres.items():
        first = list(r.items())[0]
        print(f"{kname:26s} {first[1]['n_decal']:8d}  " +
              "  ".join(f"{k.split('_rho')[0]}:{v['AUC']:.3f}/{v['median_gap']:+.1f}"
                        for k, v in r.items()))
    if prem:
        print(f"\n{'PREMISE: are DecalDistractors flat?':44s} "
              f"{'%<5deg':>8s} {'%<10deg':>8s} {'med':>7s} | crease %<5deg / med")
        for k, r in prem.items():
            print(f"{k:44s} {100*r['decal_frac_spread_under_5deg']:8.2f} "
                  f"{100*r['decal_frac_spread_under_10deg']:8.2f} "
                  f"{r['decal_median_spread']:7.2f} | "
                  f"{100*r['crease_frac_spread_under_5deg']:.2f} / "
                  f"{r['crease_median_spread']:.2f}")

    print(f"\n{'signal|scope':44s} {'n_cre':>7s} {'n_dec':>7s} {'AUC':>7s} "
          f"{'med_cre':>8s} {'med_dec':>8s} {'gap':>8s}")
    for k, r in rows.items():
        if not np.isfinite(r["AUC"]):
            print(f"{k:44s} {r['n_crease']:7d} {r['n_decal']:7d}   too few")
            continue
        print(f"{k:44s} {r['n_crease']:7d} {r['n_decal']:7d} {r['AUC']:7.4f} "
              f"{r['median_crease']:8.2f} {r['median_decal']:8.2f} {r['median_gap']:+8.2f}")

    p = os.path.join(OUT, f"diag2dgs_{args.scene}_{args.split}{args.tag}.json")
    json.dump(res, open(p, "w"), indent=1, default=float)
    np.savez(os.path.join(OUT, f"diag2dgs_{args.scene}_{args.split}{args.tag}.npz"),
             crease=crease, decal=decal, seen=seen, dmed=dmed, teed_hi=teed_hi,
             common_ok=common_ok,
             **{k: v[0] for k, v in sig.items()},
             **{"ok_" + k: v[1] for k, v in sig.items()})
    print(f"\nwrote {p}")


if __name__ == "__main__":
    main()
