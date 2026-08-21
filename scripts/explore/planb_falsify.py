"""STEP 2 — PLAN B FALSIFICATION. Which multi-view signal separates fabric print from
true crease, given that single-view G-buffer geometry does NOT (STEP 0: AUC 0.42-0.51)?

*** EVAL-ONLY DIAGNOSTIC *** (mesh used only to LABEL; every candidate signal is
computed from gaussians + training RGB + cameras, i.e. is implementable mesh-free.)

CANDIDATES
  B1  rank-1 as written in the spec: VARIANCE ACROSS VIEWS of the world-space ribbon
      dihedral. Premise: "real crease -> view-invariant world normals; albedo splat
      ripple -> camera-relative, varies with view". NOTE the premise is suspect: the
      ripple is baked into fixed 3D gaussian POSITIONS, so it should be view-invariant
      too. Testing it is the point.
  B2  multi-view MEDIAN of the world dihedral (pure averaging: if the single-view failure
      were rendering noise, averaging ~16 views would rescue it).
  B3  world-normal CONSENSUS: mean resultant length of the two ribbon normals across
      views (how stable is the fitted normal as a world quantity).
  B4  rank-3: multi-view median depth step.
  B5  NEW, physics rather than geometry: a crease is a SHADING edge — its two sides have
      different normals, so the intensity ratio across it CHANGES as the camera orbits a
      fixed light. A print is an ALBEDO edge — the ratio is the albedo ratio and is
      view-INVARIANT. So std_views( log(I_L/I_R) ) should be large for creases and small
      for prints. This never touches the contaminated 3DGS geometry; it only needs the
      gaussian depth for CORRESPONDENCE (which is accurate at the few-px scale even when
      its fine ripple is wrong).
  B6  control: median |log(I_L/I_R)| (contrast MAGNITUDE). Should NOT discriminate; if it
      does, B5 is confounded by contrast rather than measuring view-dependence.

Orientation is made consistent in 3D: the across-edge direction is fixed once in the
reference view, back-projected to a world direction, and re-projected into every probe
view, so "L" and "R" mean the same physical side everywhere (otherwise the log-ratio sign
would flip at random and B5 would be meaningless).
"""
import os
import sys

import cv2
import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
sys.path.insert(0, os.path.join(TIER1, "scripts/explore"))

from src import common, render, dt_pull
from src.mesh_oracle import MeshOracle
import gate_falsify as GF

OUT = os.path.join(TIER1, "out")
ACROSS = (2.0, 3.0, 4.0)
ALONG = np.arange(-4.5, 5.0, 1.0)


def auc(s, y):
    s = np.asarray(s, float); y = np.asarray(y, bool)
    ok = np.isfinite(s); s, y = s[ok], y[ok]
    n1 = int(y.sum()); n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return float("nan")
    r = np.empty(len(s)); r[np.argsort(s, kind="stable")] = np.arange(len(s))
    return float((r[y].sum() - n1 * (n1 - 1) / 2) / (n1 * n0))


def gray_of(path):
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    a = im[:, :, 3:4].astype(np.float32) / 255.0
    bgr = (im[:, :, :3].astype(np.float32) * a + 255.0 * (1 - a))
    return cv2.cvtColor(bgr.astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float64)


def unproject(u, v, z, cam):
    f, cx, cy = cam.f, cam.K[0, 2], cam.K[1, 2]
    Xc = np.stack([(u - cx) * z / f, (v - cy) * z / f, z], -1)
    R, t = cam.w2c[:3, :3], cam.w2c[:3, 3]
    return (R.T @ (Xc - t).T).T


def main():
    scene = sys.argv[1] if len(sys.argv) > 1 else "chair"
    n_ref = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    n_probe = int(sys.argv[3]) if len(sys.argv) > 3 else 16
    cams, rgb_paths = common.load_cameras(scene)
    g = common.load_gaussians(scene)
    keep = render.defloat_mask(g["mu"], g["opacity"])
    oracle = MeshOracle(scene)
    refs = np.unique(np.round(np.linspace(0, len(cams) - 1, n_ref + 2)).astype(int))[1:-1]
    probes = np.unique(np.round(np.linspace(0, len(cams) - 1, n_probe)).astype(int))
    print(f"[PLAN B] {scene}: ref views {list(refs)}, {len(probes)} probe views", flush=True)

    # cache probe-view geometry + images once
    P_depth, P_gray = {}, {}
    for k in probes:
        gb = render.render_gbuffer(g, keep, cams[k])
        P_depth[k] = gb["depth"].cpu().numpy().astype(np.float64)
        del gb
        P_gray[k] = gray_of(rgb_paths[k])
    print("  probe cache ready", flush=True)

    FEAT = {n: [] for n in ("B1_var_dihedral", "B2_med_dihedral", "B3_normal_consensus",
                            "B4_med_depthstep", "B5_std_logratio", "B6_med_abs_logratio",
                            "n_seen")}
    LAB = []

    for v0 in refs:
        cam0 = cams[v0]
        gb = render.render_gbuffer(g, keep, cam0)
        d0 = gb["depth"].cpu().numpy().astype(np.float64)
        a0 = gb["alpha"].cpu().numpy()
        del gb
        fg0 = a0 > 0.5
        uvq = oracle.visible_crease_uv(cam0, view_key=int(v0))
        cm = np.zeros((cam0.H, cam0.W), bool)
        cm[np.clip(np.round(uvq[:, 1]).astype(int), 0, cam0.H - 1),
           np.clip(np.round(uvq[:, 0]).astype(int), 0, cam0.W - 1)] = True
        cdt = cv2.distanceTransform((~cm).astype(np.uint8), cv2.DIST_L2, 5)
        sil = fg0 ^ (cv2.erode(fg0.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)
        sdt = cv2.distanceTransform((~sil).astype(np.uint8), cv2.DIST_L2, 5)
        interior = fg0 & (sdt > 4) & np.isfinite(d0)

        gy0 = gray_of(rgb_paths[v0])
        gb1 = cv2.GaussianBlur(gy0.astype(np.float32), (0, 0), 1.0)
        gx = cv2.Sobel(gb1, cv2.CV_64F, 1, 0, ksize=3)
        gyy = cv2.Sobel(gb1, cv2.CV_64F, 0, 1, ksize=3)
        gm = np.maximum(np.sqrt(gx * gx + gyy * gyy), 1e-9)
        dx0, dy0 = gx / gm, gyy / gm

        edge = dt_pull.edge_map(rgb_paths[v0], dt_pull.EDGE_SHARP)
        fab = edge & interior & (cdt > 3.0)
        cre = edge & interior & (cdt <= 2.0)
        ys = np.concatenate([np.nonzero(fab)[0], np.nonzero(cre)[0]])
        xs = np.concatenate([np.nonzero(fab)[1], np.nonzero(cre)[1]])
        y = np.concatenate([np.zeros(int(fab.sum()), bool), np.ones(int(cre.sum()), bool)])
        if len(ys) > 6000:
            sel = np.random.RandomState(0).choice(len(ys), 6000, False)
            ys, xs, y = ys[sel], xs[sel], y[sel]
        px, py = xs.astype(np.float64), ys.astype(np.float64)
        z0 = d0[ys, xs]
        Pw = unproject(px, py, z0, cam0)
        # world across-direction, fixed ONCE so L/R means the same side in every view
        Aw = unproject(px + dx0[ys, xs], py + dy0[ys, xs], z0, cam0) - Pw
        Aw /= np.maximum(np.linalg.norm(Aw, axis=1, keepdims=True), 1e-12)

        N = len(px)
        th = np.full((len(probes), N), np.nan)
        ds = np.full((len(probes), N), np.nan)
        lr = np.full((len(probes), N), np.nan)
        nLw = np.zeros((len(probes), N, 3))
        seen = np.zeros((len(probes), N), bool)

        for ki, k in enumerate(probes):
            cam = cams[k]
            dep = P_depth[k]
            fgk = np.isfinite(dep) & (dep < 1e8)
            uv, zc = common.project(Pw, cam)
            u, w_ = uv[:, 0], uv[:, 1]
            ui = np.clip(np.round(u).astype(int), 0, cam.W - 1)
            wi = np.clip(np.round(w_).astype(int), 0, cam.H - 1)
            inb = (zc > 0) & (u >= 3) & (u < cam.W - 3) & (w_ >= 3) & (w_ < cam.H - 3)
            zb = dep[wi, ui]
            vis = inb & np.isfinite(zb) & (np.abs(zb - zc) < 0.02 * np.maximum(zc, 1e-9))
            if not vis.any():
                continue
            # consistent 2D across-direction = projection of the FIXED world direction
            uv2, _ = common.project(Pw + 1e-3 * Aw, cam)
            a2 = uv2 - uv
            n2 = np.maximum(np.linalg.norm(a2, axis=1, keepdims=True), 1e-12)
            a2 = a2 / n2
            GF.OFF_ACROSS, GF.OFF_ALONG = ACROSS, ALONG
            r = GF.ribbon_measure(u, w_, a2[:, 0], a2[:, 1], dep, fgk, cam)
            ok = r["ok"] & vis
            th[ki][ok] = r["theta"][ok]
            ds[ki][ok] = r["dstep"][ok]
            seen[ki] = ok
            # world normal of the LEFT ribbon, oriented toward the camera
            nl = r.get("nL")
            if nl is not None:
                nc = nl.copy()
                nc[nc[:, 2] > 0] *= -1
                nLw[ki] = (cam.w2c[:3, :3].T @ nc.T).T
            # photometric ribbon means with the consistent orientation
            IL = np.zeros(N); IR = np.zeros(N); cL = np.zeros(N); cR = np.zeros(N)
            for sgn, (I, C) in ((-1.0, (IL, cL)), (+1.0, (IR, cR))):
                for da in ACROSS:
                    for dl in ALONG:
                        qx = np.clip(u + sgn * da * a2[:, 0] - dl * a2[:, 1], 0, cam.W - 1)
                        qy = np.clip(w_ + sgn * da * a2[:, 1] + dl * a2[:, 0], 0, cam.H - 1)
                        xi = np.round(qx).astype(int); yi = np.round(qy).astype(int)
                        m = fgk[yi, xi]
                        I += P_gray[k][yi, xi] * m
                        C += m
            IL /= np.maximum(cL, 1); IR /= np.maximum(cR, 1)
            good = ok & (cL > 8) & (cR > 8) & (IL > 1) & (IR > 1)
            lr[ki][good] = np.log((IL[good] + 1.0) / (IR[good] + 1.0))

        nseen = seen.sum(0)
        enough = nseen >= 6
        with np.errstate(all="ignore"):
            FEAT["B1_var_dihedral"].append(np.nanstd(th, axis=0))
            FEAT["B2_med_dihedral"].append(np.nanmedian(th, axis=0))
            FEAT["B4_med_depthstep"].append(np.nanmedian(ds, axis=0))
            FEAT["B5_std_logratio"].append(np.nanstd(lr, axis=0))
            FEAT["B6_med_abs_logratio"].append(np.nanmedian(np.abs(lr), axis=0))
            nn = np.linalg.norm(nLw.sum(0), axis=1) / np.maximum(nseen, 1)
            FEAT["B3_normal_consensus"].append(nn)
        FEAT["n_seen"].append(nseen.astype(float))
        LAB.append(y & enough | (y & False))
        LAB[-1] = y
        FEAT["_enough"] = FEAT.get("_enough", [])
        FEAT["_enough"].append(enough)
        print(f"  ref view {v0}: {N} labelled px, median views seen {np.median(nseen):.0f}",
              flush=True)

    y = np.concatenate(LAB)
    en = np.concatenate(FEAT.pop("_enough"))
    print("\n" + "=" * 88)
    print(f"PLAN B CANDIDATES — {scene}   n={int(en.sum())} px "
          f"(crease {int((y & en).sum())} / fabric {int((~y & en).sum())})")
    print("AUC = separability of CREASE vs FABRIC. 0.5 = no information.")
    print("=" * 88)
    print(f"{'candidate':26s} {'AUC':>7s}  {'direction':>28s}")
    for name, vals in FEAT.items():
        if name == "n_seen":
            continue
        s = np.concatenate(vals)[en]
        a = auc(s, y[en])
        d = "crease HIGHER" if a > 0.5 else "crease LOWER"
        print(f"{name:26s} {a:7.3f}  {d:>28s}   (|AUC-0.5| = {abs(a-0.5):.3f})")
    print("\nBaseline for reference: single-view gaussian ribbon dihedral AUC 0.42-0.51;")
    print("the same ribbon on GT-mesh depth reaches 0.72-0.77.")


if __name__ == "__main__":
    main()
