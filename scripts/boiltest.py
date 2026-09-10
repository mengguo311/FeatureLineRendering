"""tier1/scripts/boiltest.py — does per-frame Canny VISIBLY boil on cadpartA?

The linchpin test.  8 CONSECUTIVE orbit frames (adjacent, not every-20th), ours vs Canny,
side by side, plus a red/blue overlay of adjacent frames for each pipeline so "does the ink
jump" is answerable rather than eyeballed.

*** MESH EVAL-ONLY: reads no mesh at all. ***

It also reports an INK-STABILITY measure, which is the complement of P_pop and the whole point
of the finding that prompted this test:
    ink_churn(k) = fraction of ink pixels in frame k with NO ink pixel within 1.5 px in
                   frame k+1, symmetrised over both directions.
P_pop asks "did the stroke keep its identity".  ink_churn asks "did the drawn pixels move",
which is what a viewer actually sees.  gcube is rendered too as a calibration point, since it
is the solid where Canny was already verified steady.
"""
import argparse, json, os, sys
import cv2, numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1); sys.path.insert(0, os.path.join(TIER1, "scripts"))
from src import common, render                                            # noqa: E402
import temporal_m1b as T                                                  # noqa: E402
import m1b_stroke_temporal as M                                           # noqa: E402
from strokeviz import chain_args, VIZ
from dd3 import project_runs, draw_runs

OUT = os.path.join(TIER1, "out")
N_ORBIT, F0, NF, TOL = 240, 100, 8, 1.5
POOLS = {"cadpartA": "_step3pool", "gcube": "_step4",
         "lego": "_gated_test", "chair": "_gated_test"}   # the banked SHIPPED
# carriers for the textured scenes: exactly what --variant gated loads, so this
# reproduces the setup behind the banked lego 11.49x / chair temporal cells.


def ink(img):
    return img.min(2) < 0.6


def churn(a, b):
    """Symmetric fraction of ink pixels with no counterpart within TOL px."""
    out = []
    for x, y in ((a, b), (b, a)):
        if not x.any():
            out.append(0.0); continue
        dt = (cv2.distanceTransform((~y).astype(np.uint8), cv2.DIST_L2, 5)
              if y.any() else np.full(y.shape, 1e9, np.float32))
        out.append(float((dt[x] > TOL).mean()))
    return float(np.mean(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--solids", nargs="+", default=["cadpartA", "gcube"])
    args = ap.parse_args()
    ca = chain_args()
    rep = {"frames": list(range(F0, F0 + NF)), "tol_px": TOL,
           "note": "ink_churn is an INK-level measure; P_pop is a STROKE-IDENTITY measure",
           "solids": {}}
    for S in args.solids:
        z = np.load(os.path.join(OUT, f"linelets_{S}{POOLS[S]}.npz"))
        tp = os.path.join(OUT, f"linelets_{S}_gal_test.npz")
        np.savez(tp, p=z["p"], t=z["t"], l=z["l"], keep=z["keep"],
                 inlier_ratio=z["inlier_ratio"], n_vis=z["n_vis"])
        ch3, ci = M.build_chains(S, "gal", ca, verbose=False)
        oe = [(True, True)] * len(ch3)
        cams, _ = common.load_cameras(S)
        g = common.load_gaussians(S)
        kg = render.defloat_mask(g["mu"], g["opacity"])
        path = T.orbit_cameras(cams[5], cams[15], N_ORBIT,
                               np.median(g["mu"][kg], axis=0))
        O, C = [], []
        for k in range(F0, F0 + NF):
            cam = path[k]
            gb = render.render_gbuffer(g, kg, cam, with_albedo=True)
            O.append(draw_runs(project_runs(ch3, oe, cam, gb["depth"]), cam))
            gray = np.clip(gb["albedo"].detach().cpu().numpy().mean(2) * 255,
                           0, 255).astype(np.uint8)
            bp = M.baseline_strokes(gray, ca.canny_lo, ca.canny_hi, ca.min_len, ca.approx_eps)
            C.append(draw_runs([(np.asarray(q, np.float64), True, True)
                                for q in bp if len(q) > 1], cam))
            del gb
        co = [churn(ink(O[i]), ink(O[i + 1])) for i in range(NF - 1)]
        cc = [churn(ink(C[i]), ink(C[i + 1])) for i in range(NF - 1)]
        rep["solids"][S] = {"n_strokes": ci["n_strokes"],
                            "ink_churn_ours_mean": float(np.mean(co)),
                            "ink_churn_canny_mean": float(np.mean(cc)),
                            "ink_churn_ours_max": float(np.max(co)),
                            "ink_churn_canny_max": float(np.max(cc)),
                            "ratio_canny_over_ours": float(np.mean(cc) / max(np.mean(co), 1e-9))}
        print(f"  [{S}] ink_churn per consecutive pair: OURS {np.mean(co):.4f} "
              f"(max {np.max(co):.4f})   CANNY {np.mean(cc):.4f} (max {np.max(cc):.4f})   "
              f"canny/ours {np.mean(cc)/max(np.mean(co),1e-9):.2f}x", flush=True)
        # strip: 8 consecutive frames, ours top / canny bottom
        h = 600
        ro = np.concatenate([cv2.resize((np.clip(x, 0, 1) * 255).astype(np.uint8), (h, h))
                             for x in O], 1)
        rc = np.concatenate([cv2.resize((np.clip(x, 0, 1) * 255).astype(np.uint8), (h, h))
                             for x in C], 1)
        hdr = np.full((44, ro.shape[1], 3), 255, np.uint8)
        cv2.putText(hdr, f"{S}  CONSECUTIVE frames {F0}-{F0+NF-1}/{N_ORBIT}   TOP=OURS "
                         f"({ci['n_strokes']} strokes, ink_churn {np.mean(co):.3f})   "
                         f"BOTTOM=per-frame Canny (ink_churn {np.mean(cc):.3f})",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (0, 0, 0), 2, cv2.LINE_AA)
        p = os.path.join(VIZ, f"boiltest_{S}_consecutive_strip.png")
        cv2.imwrite(p, np.concatenate([hdr, ro, rc], 0)[:, :, ::-1])
        # red/blue overlay of adjacent frames, ours | canny
        def ov(a, b):
            ia, ib = ink(a), ink(b)
            d = np.ones(a.shape, np.float32)
            d[ia] = (0.85, 0.15, 0.15); d[ib] = (0.15, 0.25, 0.85); d[ia & ib] = (0.12,) * 3
            return (np.clip(cv2.resize(d, (900, 900)), 0, 1) * 255).astype(np.uint8)
        oo, oc = ov(O[0], O[1]), ov(C[0], C[1])
        for im, t in ((oo, f"OURS  f{F0} red / f{F0+1} blue"),
                      (oc, f"CANNY f{F0} red / f{F0+1} blue")):
            cv2.putText(im, t, (12, 880), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2,
                        cv2.LINE_AA)
        p2 = os.path.join(VIZ, f"boiltest_{S}_adjacent_overlay.png")
        cv2.imwrite(p2, np.concatenate([oo, oc], 1)[:, :, ::-1])
        print(f"  wrote {p}\n  wrote {p2}", flush=True)
        del g
    json.dump(rep, open(os.path.join(OUT, "boiltest.json"), "w"), indent=1)
    print(f"  -> {os.path.join(OUT,'boiltest.json')}", flush=True)


if __name__ == "__main__":
    main()
