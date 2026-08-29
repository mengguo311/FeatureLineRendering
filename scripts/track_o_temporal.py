#!/usr/bin/env python
"""TRACK O — temporal-coherence trajectory stress-test on chair. TEED + NG-MEC.

*** The MEASUREMENT is eval-only in the sense that matters here: no mesh is imported at all.
    Cameras come from the frozen held-out TEST views; the scene centre is the median gaussian
    position (mesh-free). Strokes come from linelet sets already produced by the method. ***

ALL prior temporal numbers were on ONE smooth circular orbit. Track O asks whether the win,
and whether NG-MEC culling, survives non-trivial camera motion. Three held-out 240-frame
trajectories, all look-at corrected so the object stays framed (identical construction to
temporal_m1b.orbit_cameras, so T1 reproduces the published motion exactly):

  T1  smooth orbit                      sanity anchor, the existing baseline motion
  T2  orbit + radial zoom               scale / parallax stress
  T3  multi-axis spline                 azimuth+elevation swing, NON-CONSTANT angular
                                        velocity -> crosses consensus-angle boundaries

THREE ARMS, one shared per-frame baseline:
  A  per-frame TEED on the rendered frame (2D, no object-space carrier)
  B  TEED + object-space linelets, NO cull
  C  TEED + NG-MEC consensus cull (the winner)
A is TEED, not Canny: the published table's baseline is Canny, but Track O's question is
whether the object-space carrier beats the SAME learned detector applied per frame.

METRIC. Identical operator to m1b_stroke_temporal_table_*: forward-warp every stroke of
frame t into t+1, match, accumulate P_pop and Frechet. m1b_stroke_temporal.sequence_metrics
is imported and called, not reimplemented; it is invoked twice per trajectory, once with
(ours=B, baseline=A) and once with (ours=C, baseline=A), so B and C are scored by the same
code against the same baseline frames.

  multiplier(X) = P_pop(A) / P_pop(X)          coherence gain over per-frame
  C/B           = multiplier(C) / multiplier(B) = P_pop(B) / P_pop(C)
"""
import argparse, json, os, sys, time

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
for p in (TIER1, os.path.join(TIER1, "scripts"), os.path.join(TIER1, "scripts/explore"),
          os.path.join(TIER1, "scripts/explore/syn")):
    if p not in sys.path:
        sys.path.insert(0, p)

import cv2                                                        # noqa: E402
import torch                                                      # noqa: E402
from src import common, render, view_split, strokes               # noqa: E402
import temporal_m1b as T                                          # noqa: E402
import m1b_stroke_temporal as MST                                 # noqa: E402

OUT = os.path.join(TIER1, "out")
EXT = os.path.expanduser("~/3dgs_line/ext")
TEED_DIR = os.path.join(EXT, "TEED")
TEED_CKPT = os.path.join(TEED_DIR, "checkpoints/BIPED/5/5_model.pth")
TEED_MEAN_BGR = np.array([103.939, 116.779, 123.68], np.float32)


# ------------------------------------------------------------------ trajectories
def _look_at(C, target, up_w, ref, name):
    f = target - C
    f /= max(np.linalg.norm(f), 1e-12)
    up = up_w if abs(f @ up_w) < 0.99 else np.array([0.0, 0.0, 1.0])
    r = np.cross(f, up); r /= max(np.linalg.norm(r), 1e-12)
    d = np.cross(f, r)
    c2w = np.eye(4)
    c2w[:3, 0], c2w[:3, 1], c2w[:3, 2] = r, d, f
    c2w[:3, 3] = C
    return common.Camera(ref.K, np.linalg.inv(c2w), ref.H, ref.W, name=name)


def _sphere(cam, target):
    c = np.linalg.inv(cam.w2c)[:3, 3] - target
    r = float(np.linalg.norm(c))
    return c / r, r


def _up(cams, target):
    u = -sum(np.linalg.inv(c.w2c)[:3, 1] for c in cams)
    return u / max(np.linalg.norm(u), 1e-12)


def _slerp(ua, ub, s):
    om = float(np.arccos(np.clip(ua @ ub, -1, 1)))
    if om < 1e-6:
        return ua
    return (np.sin((1 - s) * om) * ua + np.sin(s * om) * ub) / np.sin(om)


def traj_orbit(cams, target, nf, a=5, b=15):
    """T1 — exactly temporal_m1b.orbit_cameras, the published motion."""
    return T.orbit_cameras(cams[a], cams[b], nf, target)


def traj_orbit_zoom(cams, target, nf, a=5, b=15, amp=0.35):
    """T2 — the same angular arc with a smooth in/out radial zoom (scale + parallax)."""
    ua, ra = _sphere(cams[a], target)
    ub, rb = _sphere(cams[b], target)
    up_w = _up([cams[a], cams[b]], target)
    out = []
    for s in np.linspace(0.0, 1.0, nf):
        u = _slerp(ua, ub, s)
        r = ((1 - s) * ra + s * rb) * (1.0 + amp * np.sin(2 * np.pi * s))
        out.append(_look_at(target + u * r, target, up_w, cams[a], f"zoom{s:.3f}"))
    return out


def traj_spline(cams, target, nf, ctrl=(5, 25, 45, 65, 85), warp=0.15, elev=0.30):
    """T3 — multi-axis: azimuth swing through several TEST cams, an elevation oscillation,
    and a NON-UNIFORM time warp so angular velocity is not constant."""
    us, rs = zip(*[_sphere(cams[c], target) for c in ctrl])
    up_w = _up([cams[c] for c in ctrl], target)
    out = []
    for s0 in np.linspace(0.0, 1.0, nf):
        s = np.clip(s0 + warp * np.sin(2 * np.pi * s0), 0.0, 1.0)   # non-constant velocity
        x = s * (len(ctrl) - 1)
        i = int(np.clip(np.floor(x), 0, len(ctrl) - 2))
        u = _slerp(us[i], us[i + 1], x - i)
        r = (1 - (x - i)) * rs[i] + (x - i) * rs[i + 1]
        ax = np.cross(u, up_w)                                       # elevation swing axis
        n = np.linalg.norm(ax)
        if n > 1e-9:
            ax /= n
            th = elev * np.sin(3 * np.pi * s0)
            u = (u * np.cos(th) + np.cross(ax, u) * np.sin(th)
                 + ax * (ax @ u) * (1 - np.cos(th)))
            u /= max(np.linalg.norm(u), 1e-12)
        out.append(_look_at(target + u * r, target, up_w, cams[ctrl[0]], f"spl{s0:.3f}"))
    return out


TRAJ = {"T1_orbit": traj_orbit, "T2_orbit_zoom": traj_orbit_zoom, "T3_spline": traj_spline}


# ------------------------------------------------------------------ arm A: per-frame TEED
class TEED:
    def __init__(self, device="cuda"):
        if TEED_DIR not in sys.path:
            sys.path.insert(0, TEED_DIR)
        from ted import TED
        self.m = TED().to(device).eval()
        self.m.load_state_dict(torch.load(TEED_CKPT, map_location=device))
        self.device = device

    @torch.no_grad()
    def prob(self, bgr):
        x = bgr.astype(np.float32) - TEED_MEAN_BGR
        x = torch.from_numpy(np.ascontiguousarray(x.transpose(2, 0, 1)))[None].to(self.device)
        return torch.sigmoid(self.m(x)[-1])[0, 0].float().cpu().numpy()


def teed_strokes(det, gray, thr, min_len, eps, fg=None):
    """Per-frame TEED edges -> NMS-thin -> threshold -> polyline trace.
    Mirrors final_recipe.teed_edge_map (nms then >= thr), then the same tracer arm B/C use."""
    import final_recipe as FR
    bgr = np.repeat(gray[:, :, None], 3, axis=2).astype(np.uint8)
    p = FR.nms_thin(det.prob(bgr))
    e = (p >= thr).astype(np.uint8) * 255
    if fg is not None:
        e = e * fg.astype(np.uint8)
    return strokes.trace_polylines(e > 0, min_len=min_len, approx_eps=eps)


# ------------------------------------------------------------------ main
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="chair")
    ap.add_argument("--variant_B", default="tc_teed05_f0.30", help="unculled linelets")
    ap.add_argument("--variant_C", default="ngmec_ngmec_f0.30", help="NG-MEC culled linelets")
    ap.add_argument("--frames", type=int, nargs="+", default=[30, 60, 120, 240])
    ap.add_argument("--trajectories", nargs="+", default=list(TRAJ))
    ap.add_argument("--teed_thr", type=float, default=0.5)
    ap.add_argument("--out", default="out/track_o_temporal.json")
    # metric knobs, identical defaults to m1b_stroke_temporal
    ap.add_argument("--nms_mult", type=float, default=1.0)
    ap.add_argument("--knn", type=int, default=10)
    ap.add_argument("--cos_tan", type=float, default=0.60)
    ap.add_argument("--cos_col", type=float, default=0.50)
    ap.add_argument("--gap_mult", type=float, default=4.0)
    ap.add_argument("--min_nodes", type=int, default=3)
    ap.add_argument("--min_len", type=int, default=4)
    ap.add_argument("--approx_eps", type=float, default=1.0)
    ap.add_argument("--n_resample", type=int, default=16)
    ap.add_argument("--max_cand", type=int, default=6)
    ap.add_argument("--cand_radius", type=float, default=40.0)
    ap.add_argument("--match_thresh", type=float, default=3.0)
    ap.add_argument("--carrier_persistence", action="store_true")
    ap.add_argument("--cp_ratio", type=float, default=0.8)
    ap.add_argument("--cp_views", type=int, default=20)
    ap.add_argument("--fg_only", action="store_true")
    ap.add_argument("--fg_erode", type=int, default=2)
    a = ap.parse_args()

    cams, _ = common.load_cameras(a.scene)
    g = common.load_gaussians(a.scene)
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    target = np.median(g["mu"][keep_g], axis=0)              # mesh-free scene centre
    TEST = set(view_split.TEST)

    chB, iB = MST.build_chains(a.scene, a.variant_B, a)
    chC, iC = MST.build_chains(a.scene, a.variant_C, a)
    det = TEED()
    print(f"[track-o] B unculled {iB['n_strokes']} strokes | C culled {iC['n_strokes']} "
          f"strokes | per-frame TEED thr {a.teed_thr}", flush=True)

    res = {"scene": a.scene, "arms": {"A": "per-frame TEED", "B": f"linelets {a.variant_B}",
                                      "C": f"NG-MEC cull {a.variant_C}"},
           "chain_B": iB, "chain_C": iC, "teed_thr": a.teed_thr,
           "held_out": "TEST cams only", "target": [float(x) for x in target],
           "trajectories": {}}

    for tname in a.trajectories:
        fn = TRAJ[tname]
        res["trajectories"][tname] = {"by_frames": {}}
        for nf in a.frames:
            path = fn(cams, target, nf)
            t0 = time.time()
            frames = []
            for c in path:
                gb = render.render_gbuffer(g, keep_g, c, with_albedo=True)
                depth = gb["depth"].detach().cpu().numpy()
                alb = gb["albedo"].detach().cpu().numpy()
                gray = np.clip(alb.mean(2) * 255.0, 0, 255).astype(np.uint8)
                fg = None
                if a.fg_only:
                    al = (gb["alpha"].detach().cpu().numpy() > 0.5).astype(np.uint8)
                    fg = cv2.erode(al, np.ones((2 * a.fg_erode + 1,) * 2, np.uint8)) > 0
                sB = MST.ours_strokes(chB, c, gb["depth"], fg=fg)
                sC = MST.ours_strokes(chC, c, gb["depth"], fg=fg)
                sA = teed_strokes(det, gray, a.teed_thr, a.min_len, a.approx_eps, fg=fg)
                del gb
                torch.cuda.empty_cache()
                frames.append({"depth": depth, "gray": gray, "cam": c,
                               "sA": sA, "sB": sB, "sC": sC})
            # same operator, twice: (ours=B, base=A) and (ours=C, base=A)
            fB = [{**f, "A": f["sB"], "B": f["sA"]} for f in frames]
            fC = [{**f, "A": f["sC"], "B": f["sA"]} for f in frames]
            mB = MST.sequence_metrics(fB, a)
            mC = MST.sequence_metrics(fC, a)
            popA, popB, popC = mB["B"]["P_pop"], mB["A"]["P_pop"], mC["A"]["P_pop"]
            row = {"A_perframe_TEED": mB["B"], "B_unculled": mB["A"], "C_ngmec": mC["A"],
                   "mult_B": popA / popB if popB > 0 else float("inf"),
                   "mult_C": popA / popC if popC > 0 else float("inf"),
                   "frechet_mult_B": (mB["B"]["frechet_median"]
                                      / max(mB["A"]["frechet_median"], 1e-12)),
                   "frechet_mult_C": (mC["B"]["frechet_median"]
                                      / max(mC["A"]["frechet_median"], 1e-12)),
                   "_seconds": time.time() - t0}
            row["C_over_B"] = (row["mult_C"] / row["mult_B"]
                               if np.isfinite(row["mult_B"]) and row["mult_B"] > 0
                               else float("nan"))
            res["trajectories"][tname]["by_frames"][str(nf)] = row
            print(f"  [{tname}] {nf:4d}f | A P_pop {popA:.4f} | B {popB:.4f} "
                  f"({row['mult_B']:6.2f}x) | C {popC:.4f} ({row['mult_C']:6.2f}x) | "
                  f"C/B {row['C_over_B']:.4f}  ({row['_seconds']:.0f}s)", flush=True)
            json.dump(res, open(os.path.join(TIER1, a.out), "w"), indent=1, default=float)

    json.dump(res, open(os.path.join(TIER1, a.out), "w"), indent=1, default=float)
    print(f"\nwrote {a.out}")
