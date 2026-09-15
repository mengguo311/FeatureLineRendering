"""Confound-isolation ablation: does chair's crown ink_churn advantage (28x, PERFECT
poses) survive COLMAP-magnitude pose error?  (driver-side; agent login-expired.)

WHY. Exp B on real-capture Truck came back NO-GO (ink_churn 1.10x, need >=8x). Two
unseparated confounds: (1) ESTIMATED poses jitter object-space strokes on reprojection;
(2) Truck is larger/specular/less-uniformly-textured than chair. This isolates (1) on the
scene where the crown is strongest: inject pose noise into the chair EVAL cameras ONLY
(method/carrier/gaussians UNTOUCHED), reuse the EXACT boiltest churn protocol, and sweep.

DEFENSIVE DESIGN (pre-empts "you guessed the magnitude"):
  - A SWEEP over pose-noise sigma, not a single number.
  - Each level's x-axis is the EMPIRICALLY MEASURED induced mean on-screen displacement in
    px (project gaussian centres clean-vs-noisy), so it is directly comparable to Truck's
    measured COLMAP residual (~0.38 px @ half-res / 0.76 px @ full-res).
  - Noise is INDEPENDENT per frame (COLMAP estimates each cam independently) — the honest,
    slightly conservative model of estimated-pose temporal instability.
  - SELF-VALIDATION GATE: sigma=0 MUST reproduce the banked chair ~28x (boiltest.json chair
    28.16x). If it doesn't, the harness is wrong and the sweep is void — printed loudly.
MESH EVAL-ONLY: reads no mesh. No per-scene tuning. Frozen shipped carrier + operators.

PRE-REGISTERED READING (frozen before running):
  - If chair ratio COLLAPSES toward ~1x at/below Truck's induced px (~0.4 px) -> the crown
    advantage is largely a PERFECT-POSE ARTIFACT; thesis re-scoped to perfect-pose synthetic
    as a HARD limitation. (Would corroborate the Truck NO-GO as pose-driven.)
  - If chair ratio STAYS HIGH (say >=8x) at Truck's induced px -> the Truck NO-GO is a
    TEXTURE/scene confound, not pose error; a chair-like real capture is the honest retry.
Report the curve straight either way; do not root for a direction.
"""
import json, os, sys, time
import numpy as np, cv2
from scipy.spatial.transform import Rotation

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1); sys.path.insert(0, os.path.join(TIER1, "scripts"))
from src import common, render
import temporal_m1b as T
import m1b_stroke_temporal as M
from strokeviz import chain_args, VIZ
from dd3 import project_runs, draw_runs
from boiltest import ink, churn, POOLS, N_ORBIT, F0, NF

OUT = os.path.join(TIER1, "out")
SCENE = "chair"
# sweep: (sigma_rot_deg, sigma_trans_frac_of_orbit_radius). L0 is the validation control.
LEVELS = [
    (0.00, 0.0000),   # L0 control: MUST reproduce ~28x
    (0.02, 0.0005),
    (0.05, 0.0010),
    (0.10, 0.0020),
    (0.20, 0.0050),
    (0.50, 0.0100),
]
SEED = 20260915


def perturb(cam, srot_deg, strans, rng):
    """Independent small rigid jitter on c2w (rotation about random axis + translation)."""
    c2w = np.linalg.inv(cam.w2c)
    R, C = c2w[:3, :3].copy(), c2w[:3, 3].copy()
    if srot_deg > 0:
        ax = rng.normal(size=3); ax /= max(np.linalg.norm(ax), 1e-12)
        ang = np.deg2rad(rng.normal(0.0, srot_deg))
        R = Rotation.from_rotvec(ax * ang).as_matrix() @ R
    if strans > 0:
        C = C + rng.normal(0.0, strans, 3)
    c2wn = np.eye(4); c2wn[:3, :3] = R; c2wn[:3, 3] = C
    return common.Camera(cam.K, np.linalg.inv(c2wn), cam.H, cam.W, name=cam.name + "_n")


def induced_px(pts, cam_clean, cam_noisy):
    """Mean on-screen displacement (px) of visible object points, clean vs noisy cam."""
    uv0, z0 = common.project(pts, cam_clean)
    uv1, z1 = common.project(pts, cam_noisy)
    ok = (z0 > 1e-6) & (z1 > 1e-6) & \
         (uv0[:, 0] > 0) & (uv0[:, 0] < cam_clean.W) & \
         (uv0[:, 1] > 0) & (uv0[:, 1] < cam_clean.H)
    if ok.sum() < 10:
        return float("nan")
    return float(np.linalg.norm(uv1[ok] - uv0[ok], axis=1).mean())


def main():
    t0 = time.time()
    ca = chain_args()
    # rebuild the SHIPPED chair carrier exactly as boiltest does (--variant gated equiv)
    z = np.load(os.path.join(OUT, f"linelets_{SCENE}{POOLS[SCENE]}.npz"))
    tp = os.path.join(OUT, f"linelets_{SCENE}_gal_test.npz")
    np.savez(tp, p=z["p"], t=z["t"], l=z["l"], keep=z["keep"],
             inlier_ratio=z["inlier_ratio"], n_vis=z["n_vis"])
    ch3, ci = M.build_chains(SCENE, "gal", ca, verbose=False)
    oe = [(True, True)] * len(ch3)
    cams, _ = common.load_cameras(SCENE)
    g = common.load_gaussians(SCENE)
    kg = render.defloat_mask(g["mu"], g["opacity"])
    target = np.median(g["mu"][kg], axis=0)
    path = T.orbit_cameras(cams[5], cams[15], N_ORBIT, target)   # SAME orbit as boiltest
    base = path[F0:F0 + NF]                                       # 8 consecutive frames
    mu = g["mu"][kg]
    sub = mu[np.random.default_rng(0).choice(len(mu), min(20000, len(mu)), replace=False)]
    print(f"[{SCENE}] carrier {ci['n_strokes']} strokes; orbit {N_ORBIT}, frames {F0}-{F0+NF-1}",
          flush=True)

    rows = []
    for li, (srot, strans) in enumerate(LEVELS):
        rng = np.random.default_rng(SEED + li)
        strans_abs = strans * float(np.linalg.norm(cams[5].center - target))
        # perturb each of the 8 eval cams independently (both pipelines see identical cams)
        ncams = [perturb(c, srot, strans_abs, rng) for c in base]
        ipx = float(np.nanmean([induced_px(sub, base[k], ncams[k]) for k in range(NF)]))
        O, C = [], []
        for k in range(NF):
            cam = ncams[k]
            gb = render.render_gbuffer(g, kg, cam, with_albedo=True)
            O.append(draw_runs(project_runs(ch3, oe, cam, gb["depth"]), cam))
            gray = np.clip(gb["albedo"].detach().cpu().numpy().mean(2) * 255, 0, 255).astype(np.uint8)
            bp = M.baseline_strokes(gray, ca.canny_lo, ca.canny_hi, ca.min_len, ca.approx_eps)
            C.append(draw_runs([(np.asarray(q, np.float64), True, True) for q in bp if len(q) > 1], cam))
            del gb
        co = [churn(ink(O[i]), ink(O[i + 1])) for i in range(NF - 1)]
        cc = [churn(ink(C[i]), ink(C[i + 1])) for i in range(NF - 1)]
        ico, icc = float(np.mean(co)), float(np.mean(cc))
        ratio = icc / max(ico, 1e-9)
        rows.append({"level": li, "sigma_rot_deg": srot, "sigma_trans_frac": strans,
                     "induced_px_mean": ipx, "ink_churn_ours": ico, "ink_churn_canny": icc,
                     "ratio_canny_over_ours": ratio})
        print(f"  L{li} rot{srot}deg trans{strans}r  induced {ipx:.3f}px  "
              f"OURS {ico:.4f}  CANNY {icc:.4f}  ratio {ratio:.2f}x", flush=True)

    # self-validation gate: L0 must reproduce banked chair ~28x
    l0 = rows[0]["ratio_canny_over_ours"]
    banked = 28.16
    valid = abs(l0 - banked) / banked < 0.15
    rep = {
        "experiment": "confound-isolation: chair crown ink_churn under COLMAP-magnitude pose noise",
        "scene": SCENE, "carrier_strokes": ci["n_strokes"],
        "protocol": "boiltest churn, 8 consecutive orbit frames, per-frame INDEPENDENT rigid "
                    "jitter on eval cams only; method/carrier/gaussians untouched; mesh-free",
        "seed": SEED, "sweep": rows,
        "truck_reference_induced_px": {"half_res": 0.38, "full_res": 0.76,
                                       "note": "COLMAP BA reproj residual, NOT proven == pose error"},
        "self_validation": {"L0_ratio": l0, "banked_chair": banked, "PASS": bool(valid),
                            "note": "L0 (sigma=0) must reproduce banked boiltest chair 28.16x"},
    }
    json.dump(rep, open(os.path.join(OUT, "posenoise_chair.json"), "w"), indent=1)
    print(f"\n=== SELF-VALIDATION: L0 {l0:.2f}x vs banked {banked}x -> "
          f"{'PASS' if valid else 'FAIL (harness suspect, sweep VOID)'} ===")
    print(f"wrote out/posenoise_chair.json  ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
