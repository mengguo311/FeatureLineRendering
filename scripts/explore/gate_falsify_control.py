"""STEP 0 CONTROL — is the LEAKS verdict real, or an artefact of my ribbon estimator?

EVAL-ONLY DIAGNOSTIC (imports gate_falsify, which owns the mesh labelling).

The falsification returned a NEGATIVE separation: fabric-print pixels look MORE dihedral
than true creases. Before concluding "the geometry carries no signal", three controls:

  C1  DEPTH SOURCE.  Run the identical ribbon measurement on the GT MESH depth instead of
      the gaussian depth. If the mesh separates fabric from crease cleanly with the SAME
      code, the estimator is sound and the fault lies in the 3DGS geometry (albedo-driven
      splat ripple). If the mesh ALSO fails, my estimator or labelling is broken.
  C2  RIBBON SCALE. A 3px-wide ribbon determines its across-edge slope poorly, so the
      fitted normal may be dominated by that badly-conditioned direction. Sweep the ribbon
      offset/thickness/length.
  C3  NORMAL-MAP dihedral (what final_recipe's crease-ridge actually uses) as an
      independent estimator of the same quantity.

Reported per configuration: fabric theta_95, crease theta_05, separation, and the AUC of
theta for crease-vs-fabric (0.5 = no information, which is the number that actually
decides whether ANY threshold on this quantity can work).
"""
import os
import sys

import cv2
import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
sys.path.insert(0, os.path.join(TIER1, "scripts/explore"))
sys.path.insert(0, os.path.join(TIER1, "scripts/explore/syn"))

from src import common, render, dt_pull
from src.mesh_oracle import MeshOracle
import gate_falsify as GF


def auc(scores, labels):
    s = np.asarray(scores, float); y = np.asarray(labels, bool)
    ok = np.isfinite(s); s, y = s[ok], y[ok]
    n1 = int(y.sum()); n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return float("nan")
    r = np.empty(len(s)); r[np.argsort(s, kind="stable")] = np.arange(len(s))
    return float((r[y].sum() - n1 * (n1 - 1) / 2) / (n1 * n0))


def normal_dihedral(px, py, dirx, diry, normal, fg, off=3.0, half=4.5):
    """C3: dihedral straight from the rendered normal map, two ribbons, median normal."""
    H, W = fg.shape
    out = []
    for sgn in (-1.0, +1.0):
        acc = np.zeros((len(px), 3))
        cnt = np.zeros(len(px))
        for da in (off - 1, off, off + 1):
            for dl in np.arange(-half, half + 0.5, 1.0):
                qx = np.clip(px + sgn * da * dirx - dl * diry, 0, W - 1)
                qy = np.clip(py + sgn * da * diry + dl * dirx, 0, H - 1)
                xi = np.round(qx).astype(int); yi = np.round(qy).astype(int)
                m = fg[yi, xi]
                acc += normal[yi, xi] * m[:, None]
                cnt += m
        n = acc / np.maximum(cnt, 1)[:, None]
        out.append(n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12))
    c = np.clip(np.abs((out[0] * out[1]).sum(1)), -1, 1)
    return np.degrees(np.arccos(c))


def main():
    scene = sys.argv[1] if len(sys.argv) > 1 else "chair"
    nv = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    cams, rgb_paths = common.load_cameras(scene)
    g = common.load_gaussians(scene)
    keep = render.defloat_mask(g["mu"], g["opacity"])
    oracle = MeshOracle(scene)
    views = np.unique(np.round(np.linspace(0, len(cams) - 1, nv)).astype(int))
    print(f"[CONTROL] {scene}, views {list(views)}", flush=True)

    CFGS = [("gauss  off3 thick3 len10", "gauss", (2.0, 3.0, 4.0), 4.5),
            ("gauss  off5 thick5 len16", "gauss", (3.0, 4.0, 5.0, 6.0, 7.0), 7.5),
            ("gauss  off8 thick5 len20", "gauss", (6.0, 7.0, 8.0, 9.0, 10.0), 9.5),
            ("MESH   off3 thick3 len10", "mesh", (2.0, 3.0, 4.0), 4.5),
            ("MESH   off5 thick5 len16", "mesh", (3.0, 4.0, 5.0, 6.0, 7.0), 7.5)]
    acc = {c[0]: {"th": [], "ds": [], "y": []} for c in CFGS}
    accN = {"th": [], "y": []}

    for v in views:
        cam = cams[v]
        gb = render.render_gbuffer(g, keep, cam)
        gdepth = gb["depth"].cpu().numpy().astype(np.float64)
        gnormal = gb["normal"].cpu().numpy().astype(np.float64)
        alpha = gb["alpha"].cpu().numpy()
        del gb
        fg = alpha > 0.5
        mdepth = oracle.render_depth(cam, view_key=int(v)).cpu().numpy().astype(np.float64)
        mfg = mdepth < 1e8
        mdepth = np.where(mfg, mdepth, np.inf)

        uvq = oracle.visible_crease_uv(cam, view_key=int(v))
        cm = np.zeros((cam.H, cam.W), bool)
        cm[np.clip(np.round(uvq[:, 1]).astype(int), 0, cam.H - 1),
           np.clip(np.round(uvq[:, 0]).astype(int), 0, cam.W - 1)] = True
        cdt = cv2.distanceTransform((~cm).astype(np.uint8), cv2.DIST_L2, 5)
        sil = fg ^ (cv2.erode(fg.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)
        sdt = cv2.distanceTransform((~sil).astype(np.uint8), cv2.DIST_L2, 5)
        interior = fg & mfg & (sdt > 4)

        im = cv2.imread(rgb_paths[v], cv2.IMREAD_UNCHANGED)
        a4 = im[:, :, 3:4].astype(np.float32) / 255.0
        bgr = (im[:, :, :3].astype(np.float32) * a4 + 255.0 * (1 - a4)).astype(np.uint8)
        gray = cv2.GaussianBlur(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), (0, 0), 1.0)
        gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gm = np.maximum(np.sqrt(gx * gx + gy * gy), 1e-9)
        dirx, diry = gx / gm, gy / gm

        edge = dt_pull.edge_map(rgb_paths[v], dt_pull.EDGE_SHARP)
        fab = edge & interior & (cdt > 3.0)
        cre = edge & interior & (cdt <= 2.0)
        ys = np.concatenate([np.nonzero(fab)[0], np.nonzero(cre)[0]])
        xs = np.concatenate([np.nonzero(fab)[1], np.nonzero(cre)[1]])
        y = np.concatenate([np.zeros(int(fab.sum()), bool), np.ones(int(cre.sum()), bool)])
        if len(ys) > 24000:
            idx = np.random.RandomState(0).choice(len(ys), 24000, False)
            ys, xs, y = ys[idx], xs[idx], y[idx]
        pxf, pyf = xs.astype(np.float64), ys.astype(np.float64)

        for name, src, offs, half in CFGS:
            GF.OFF_ACROSS = offs
            GF.OFF_ALONG = np.arange(-half, half + 0.5, 1.0)
            dep = gdepth if src == "gauss" else mdepth
            msk = fg if src == "gauss" else mfg
            r = GF.ribbon_measure(pxf, pyf, dirx[ys, xs], diry[ys, xs], dep, msk, cam)
            ok = r["ok"]
            acc[name]["th"].append(r["theta"][ok])
            acc[name]["ds"].append(r["dstep"][ok])
            acc[name]["y"].append(y[ok])
        tn = normal_dihedral(pxf, pyf, dirx[ys, xs], diry[ys, xs], gnormal, fg)
        accN["th"].append(tn); accN["y"].append(y)
        print(f"  view {v} done ({len(ys)} labelled px)", flush=True)

    print("\n" + "=" * 100)
    print(f"CONTROL RESULTS — {scene}. AUC = separability of theta for CREASE vs FABRIC "
          f"(0.5 = no information)")
    print("=" * 100)
    print(f"{'configuration':26s} {'n':>7s} {'fab th95':>9s} {'cre th05':>9s} {'sep':>8s} "
          f"{'AUC th':>7s} {'AUC dd':>7s}")
    for name, _, _, _ in CFGS:
        th = np.concatenate(acc[name]["th"]); ds = np.concatenate(acc[name]["ds"])
        y = np.concatenate(acc[name]["y"])
        f95 = GF.pct(th[~y], 95); c05 = GF.pct(th[y], 5)
        print(f"{name:26s} {len(y):7d} {f95:9.2f} {c05:9.2f} {c05-f95:8.2f} "
              f"{auc(th, y):7.3f} {auc(ds, y):7.3f}")
    thn = np.concatenate(accN["th"]); yn = np.concatenate(accN["y"])
    print(f"{'C3 normal-map dihedral':26s} {len(yn):7d} {GF.pct(thn[~yn],95):9.2f} "
          f"{GF.pct(thn[yn],5):9.2f} {GF.pct(thn[yn],5)-GF.pct(thn[~yn],95):8.2f} "
          f"{auc(thn, yn):7.3f} {'-':>7s}")
    print("\nREAD: if the MESH rows separate (AUC >> 0.5) but the gauss rows do not, the")
    print("ribbon estimator is SOUND and the 3DGS geometry itself carries the contamination.")


if __name__ == "__main__":
    main()
