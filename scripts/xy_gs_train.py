"""EXPERIMENT Y — one 3DGS trainer, three conditions, matched in everything else.

  A  vanilla        the FROZEN baseline: stock 3DGS, no line awareness whatsoever.
  B  oracle    ***  SIMULATED IDEAL RETRAIN -- AN ORACLE UPPER BOUND, NOT A METHOD.  ***
                    It reads the GROUND-TRUTH MESH CREASES and seeds/densifies carriers
                    directly on them.  It is deliberately best-case: it is handed the answer
                    the pipeline is supposed to find.  No proposed method may do this.  It
                    exists only to put a CEILING on what any line-favourable retraining could
                    ever achieve.  Every artefact it produces is labelled ORACLE.
  B' honest         a legal, mesh-free line-aware retrain: an edge-weighted photometric loss
                    plus edge-boosted densification, driven ONLY by Sobel edges of the
                    training images.  Expected to land between A and B.

Everything else -- seed, iterations, lr schedule, SH schedule, densify interval/window,
opacity reset, loss, camera order -- is byte-identical across conditions, so any difference
in the extracted lines is attributable to the intervention alone.
"""
import argparse
import json
import os
import sys
import time

import numpy as np
import torch
import torch.nn.functional as Fn

sys.path.insert(0, os.path.expanduser("~/cglib"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
from vfsdgs.gs_io import GaussianSet, inverse_sigmoid, load_ply, render, rgb2sh, save_ply
from vfsdgs.train_static import (Densifier, _cat_optimizer, evaluate, expon_lr,
                                 init_gaussians, load_blender, scene_extent_of, ssim)
from scipy.spatial import cKDTree

MESH_DIR = os.path.expanduser("~/3dgs_line/bcr/meshes/NeRF_Mesh")
ANGLE, DS = 30.0, 0.0015


def mat2quat_batch(R):
    """R[N,3,3] with columns = axes -> wxyz quaternions."""
    m = R
    tr = m[:, 0, 0] + m[:, 1, 1] + m[:, 2, 2]
    q = np.zeros((len(R), 4))
    s = tr > 0
    if s.any():
        S = np.sqrt(tr[s] + 1.0) * 2
        q[s] = np.stack([0.25 * S, (m[s, 2, 1] - m[s, 1, 2]) / S,
                         (m[s, 0, 2] - m[s, 2, 0]) / S, (m[s, 1, 0] - m[s, 0, 1]) / S], 1)
    r = ~s
    if r.any():
        # fall back to the largest-diagonal branch
        idx = np.argmax(np.stack([m[r, 0, 0], m[r, 1, 1], m[r, 2, 2]], 1), 1)
        mm = m[r]
        out = np.zeros((len(mm), 4))
        for k in range(3):
            sel = idx == k
            if not sel.any():
                continue
            a, b, c = k, (k + 1) % 3, (k + 2) % 3
            S = np.sqrt(1.0 + mm[sel, a, a] - mm[sel, b, b] - mm[sel, c, c]) * 2
            out[sel, 0] = (mm[sel, c, b] - mm[sel, b, c]) / S
            out[sel, 1 + a] = 0.25 * S
            out[sel, 1 + b] = (mm[sel, b, a] + mm[sel, a, b]) / S
            out[sel, 1 + c] = (mm[sel, a, c] + mm[sel, c, a]) / S
        q[r] = out
    return q / np.clip(np.linalg.norm(q, axis=1, keepdims=True), 1e-12, None)


def gt_crease_with_tangent(scene):
    """*** ORACLE INPUT -- GROUND-TRUTH MESH.  Condition B only. ***"""
    import trimesh
    m = trimesh.load(f"{MESH_DIR}/{scene}_new.obj", process=True)
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate([g for g in m.geometry.values()])
    V = np.asarray(m.vertices, np.float64)
    sel = m.face_adjacency_edges[m.face_adjacency_angles >= np.deg2rad(ANGLE)]
    A, B = V[sel[:, 0]], V[sel[:, 1]]
    L = np.linalg.norm(B - A, axis=1)
    P, T = [], []
    for i in range(len(A)):
        n = max(2, int(L[i] / DS) + 1)
        ts = np.linspace(0, 1, n)
        P.append(A[i][None] + ts[:, None] * (B[i] - A[i])[None])
        T.append(np.repeat(((B[i] - A[i]) / L[i])[None], n, 0))
    return np.concatenate(P, 0), np.concatenate(T, 0)


def make_line_gaussians(P, T, rgb_mean, s_long, s_thin, dev, rng):
    """anisotropic gaussians aligned WITH the crease tangent: long along it, thin across.
    Maximally favourable initialisation -- exactly what a sharp 1D carrier wants to be."""
    n = len(P)
    t = T / np.clip(np.linalg.norm(T, axis=1, keepdims=True), 1e-12, None)
    a = np.tile(np.array([0.0, 0.0, 1.0]), (n, 1))
    bad = np.abs((t * a).sum(1)) > 0.9
    a[bad] = np.array([1.0, 0.0, 0.0])
    b = np.cross(t, a)
    b /= np.clip(np.linalg.norm(b, axis=1, keepdims=True), 1e-12, None)
    c = np.cross(t, b)
    R = np.stack([t, b, c], axis=2)                        # columns = principal axes
    q = mat2quat_batch(R)
    T_ = lambda x, d=torch.float32: torch.tensor(x, dtype=d, device=dev)
    return {
        "means": T_(P + rng.normal(scale=s_thin * 0.25, size=P.shape)),
        "quats": T_(q),
        "log_scales": T_(np.log(np.tile([s_long, s_thin, s_thin], (n, 1)))),
        "logit_opacities": inverse_sigmoid(torch.full((n, 1), 0.5, device=dev)),
        "sh_dc": rgb2sh(T_(rgb_mean))[None, None, :].expand(n, 1, 3).clone(),
        "sh_rest": torch.zeros(n, 15, 3, device=dev),
    }


def edge_maps(cams, dev):
    """Sobel |grad| of each training image, normalised to [0,1]. LEGAL (image-only)."""
    E = []
    for c in cams:
        g = c.image.mean(0, keepdim=True)[None].to(dev)
        kx = torch.tensor([[[[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]]]], dtype=torch.float32,
                          device=dev)
        gx = Fn.conv2d(g, kx, padding=1)
        gy = Fn.conv2d(g, kx.transpose(2, 3), padding=1)
        e = (gx ** 2 + gy ** 2).sqrt()[0, 0]
        E.append((e / e.max().clamp(min=1e-8)).cpu())
    return E


def project_px(means, cam, W, H):
    ph = torch.cat([means, torch.ones_like(means[:, :1])], 1) @ cam.full_proj_transform
    w = ph[:, 3:4].clamp(min=1e-6)
    ndc = ph[:, :3] / w
    x = ((ndc[:, 0] + 1.0) * W - 1.0) * 0.5
    y = ((ndc[:, 1] + 1.0) * H - 1.0) * 0.5
    return x, y, ph[:, 3]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="cadpart")
    ap.add_argument("--mode", required=True, choices=["vanilla", "oracle", "honest"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--iters", type=int, default=10000)
    ap.add_argument("--n_init", type=int, default=30000)
    ap.add_argument("--max_gauss", type=int, default=200000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--densify_from", type=int, default=500)
    ap.add_argument("--inject_n", type=int, default=20000, help="ORACLE: carriers per injection")
    ap.add_argument("--inject_at", default="500,2000,3500", help="ORACLE: injection iterations")
    ap.add_argument("--s_long", type=float, default=0.010)
    ap.add_argument("--s_thin", type=float, default=0.0025)
    ap.add_argument("--crease_r_px", type=float, default=2.0, help="ORACLE densify-boost radius")
    ap.add_argument("--boost", type=float, default=0.25, help="grad-thresh multiplier near lines")
    ap.add_argument("--lam_edge", type=float, default=0.5, help="HONEST edge-weighted loss")
    args = ap.parse_args()
    data = os.path.expanduser(f"~/cglib/data/full/{args.scene}")
    densify_until = args.iters // 2
    torch.manual_seed(args.seed)
    dev = torch.device("cuda:0")
    torch.cuda.set_device(dev)
    rng = np.random.default_rng(args.seed)
    t0 = time.time()

    train_cams = load_blender(data, "train", 1, True)
    test_cams = load_blender(data, "test", 1, True)
    extent = scene_extent_of(train_cams)
    Him, Wim = train_cams[0].image_height, train_cams[0].image_width
    print(f"[{args.mode}] train={len(train_cams)} test={len(test_cams)} {Wim}x{Him} "
          f"extent={extent:.3f}", flush=True)

    gs = init_gaussians(min(args.n_init, args.max_gauss), train_cams, dev, seed=args.seed)
    bg = torch.ones(3, device=dev)
    rgb_mean = torch.stack([c.image.mean(dim=(1, 2)) for c in train_cams]).mean(0).numpy()
    mlr0, mlr1 = 1.6e-4 * extent, 1.6e-6 * extent
    groups = [{"name": "means", "params": [gs.means], "lr": mlr0},
              {"name": "quats", "params": [gs.quats], "lr": 1e-3},
              {"name": "log_scales", "params": [gs.log_scales], "lr": 5e-3},
              {"name": "logit_opacities", "params": [gs.logit_opacities], "lr": 5e-2},
              {"name": "sh_dc", "params": [gs.sh_dc], "lr": 2.5e-3},
              {"name": "sh_rest", "params": [gs.sh_rest], "lr": 2.5e-3 / 20}]
    opt = torch.optim.Adam(groups, lr=0.0, eps=1e-15)
    dens = Densifier(gs, opt, extent, max_gauss=args.max_gauss)

    px_world = 4.031128875572954 / (0.5 * 800 / np.tan(0.5 * 0.6911112070083618))
    crease_R = args.crease_r_px * px_world
    tree = Pg = Tg = None
    if args.mode == "oracle":
        Pg, Tg = gt_crease_with_tangent(args.scene)
        tree = cKDTree(Pg)
        print(f"[ORACLE] *** GT-MESH CREASES USED AS TRAINING SUPERVISION -- UPPER BOUND, "
              f"NOT A METHOD *** {len(Pg)} crease points, boost radius {crease_R:.5f}",
              flush=True)
    Emaps = edge_maps(train_cams, dev) if args.mode == "honest" else None
    inject_at = set(int(x) for x in args.inject_at.split(",") if x)

    os.makedirs(args.out, exist_ok=True)
    curve = {"iter": [], "loss": [], "n_gauss": [], "test": [], "injected": []}
    sh_deg, ema = 0, None
    for it in range(1, args.iters + 1):
        if it >= 500 and (it - 500) % 1000 == 0 and sh_deg < 3:
            sh_deg += 1
        for g in opt.param_groups:
            if g["name"] == "means":
                g["lr"] = expon_lr(it, mlr0, mlr1, args.iters)
        vi = int(torch.randint(len(train_cams), (1,)))
        cam = train_cams[vi].to(dev)
        gt = cam.gt_image(dev)
        out = render(gs, cam, bg, active_sh_degree=sh_deg)
        img = out["render"]
        loss = 0.8 * (img - gt).abs().mean() + 0.2 * (1 - ssim(img, gt))
        if args.mode == "honest":
            e = Emaps[vi].to(dev)
            loss = loss + args.lam_edge * (e[None] * (img - gt).abs()).mean()
        loss.backward()
        with torch.no_grad():
            if it <= densify_until:
                dens.add_stats(out["viewspace_points"], out["visibility_filter"])
        opt.step()
        opt.zero_grad(set_to_none=True)

        with torch.no_grad():
            # ---- ORACLE: inject sharp carriers exactly ON the GT crease curves -----------
            if args.mode == "oracle" and it in inject_at and gs.n + args.inject_n <= args.max_gauss:
                pick = rng.choice(len(Pg), size=min(args.inject_n, len(Pg)), replace=False)
                ext = make_line_gaussians(Pg[pick], Tg[pick], rgb_mean,
                                          args.s_long, args.s_thin, dev, rng)
                _cat_optimizer(opt, gs, ext)
                dens.reset_stats()
                curve["injected"].append({"iter": it, "n": int(len(pick)), "total": gs.n})
                print(f"[ORACLE] iter {it}: injected {len(pick)} GT-crease carriers "
                      f"-> n_gauss={gs.n}", flush=True)
            if args.densify_from <= it <= densify_until and it % 100 == 0:
                # line-favourable densification: lower the split/clone bar near lines
                base = dens.grad_thresh
                near = None
                if args.mode == "oracle":
                    d = tree.query(gs.means.data.cpu().numpy(), k=1, workers=-1)[0]
                    near = torch.tensor(d <= crease_R, device=dev)
                elif args.mode == "honest":
                    x, y, w = project_px(gs.means.data, cam, Wim, Him)
                    xi = x.round().long().clamp(0, Wim - 1)
                    yi = y.round().long().clamp(0, Him - 1)
                    ev = Emaps[vi].to(dev)[yi, xi]
                    near = (w > 0) & (ev > 0.15)
                if near is not None and near.any():
                    g_ = (dens.grad_accum / dens.denom.clamp_min(1)).squeeze(-1)
                    dens.grad_accum[near] = (g_[near] / args.boost).unsqueeze(-1) * \
                        dens.denom[near].clamp_min(1)
                dens.densify_and_prune()
                dens.grad_thresh = base
            if it % 3000 == 0 and it <= densify_until:
                dens.reset_opacity()

        ema = float(loss) if ema is None else 0.99 * ema + 0.01 * float(loss)
        if it % 100 == 0 or it == 1:
            curve["iter"].append(it); curve["loss"].append(round(ema, 6))
            curve["n_gauss"].append(gs.n)
        if it % 1000 == 0 or it == args.iters:
            print(f"[{args.mode} {it:6d}] loss={ema:.5f} n={gs.n} sh={sh_deg} "
                  f"({time.time()-t0:.0f}s)", flush=True)
        if it % 5000 == 0 or it == args.iters:
            p = evaluate(gs, test_cams, bg, sh_deg, dev)
            curve["test"].append({"iter": it, "psnr": round(p, 3)})
            print(f"[{args.mode} test {it}] PSNR={p:.2f} dB", flush=True)

    save_ply(gs, os.path.join(args.out, "point_cloud.ply"))
    op = gs.opacities().data.squeeze(-1).cpu().numpy()
    sc = gs.scales().data.cpu().numpy()
    summary = {"mode": args.mode, "scene": args.scene, "args": vars(args),
               "n_gauss": int(gs.n), "final_loss_ema": round(ema, 6),
               "test_psnr": curve["test"][-1]["psnr"],
               "opacity": {f"p{q}": round(float(np.percentile(op, q)), 4)
                           for q in (5, 25, 50, 75, 95)},
               "scale_min_axis": {f"p{q}": round(float(np.percentile(sc.min(1), q)), 6)
                                  for q in (5, 50, 95)},
               "aniso_ratio_med": round(float(np.median(sc.max(1) / np.clip(sc.min(1), 1e-9, None))), 3),
               "minutes": round((time.time() - t0) / 60, 2)}
    if args.mode == "oracle":
        summary["ORACLE_WARNING"] = ("Condition B used GROUND-TRUTH MESH CREASES during "
                                     "training. It is a SIMULATED IDEAL UPPER BOUND, NOT a "
                                     "proposed method, and must never be reported as one.")
    json.dump({**summary, "curve": curve}, open(os.path.join(args.out, "train_curve.json"), "w"),
              indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
