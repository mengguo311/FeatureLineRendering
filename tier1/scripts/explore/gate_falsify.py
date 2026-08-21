"""STEP 0 — FALSIFICATION EXPERIMENT for the geometry-gated DT (M1b-fix).

*** EVAL-ONLY DIAGNOSTIC. NOT A METHOD MODULE. ***
The GT mesh is used HERE AND ONLY HERE, and only to LABEL Canny-edge pixels as
fabric-print vs true-crease so the two populations can be compared. The measurement
applied to those pixels — the bilateral ribbon — is computed purely from the rendered
G-buffer (depth + normal), i.e. exactly what src/geom_gate.py would be allowed to see.
If this file's numbers say the gate is clean, geom_gate.py can reproduce the measurement
with no mesh at all.

THE CLAIM UNDER TEST
    At a flat fabric print the surface geometry is FLAT (dihedral ~0, depth-step ~0) even
    though the colour changes; at a true crease it is not. If that fails, gating the
    RGB-Canny DT by G-buffer geometry cannot separate print from crease and the whole
    approach is dead (-> Plan B).

THE MEASUREMENT (bilateral ribbon, method-side)
    At each Canny-edge pixel, the local edge direction comes from the image gradient
    (across-edge = grad direction). Two ribbons Omega_L / Omega_R are sampled at +-3px
    across the edge, each 3px across x 10px along. Every ribbon sample is back-projected
    with the rendered depth and a plane is fitted ROBUSTLY to each side, then:
        theta   = angle between the two fitted plane normals (the dihedral)
        dd/d    = |z_L(edge) - z_R(edge)| / z, both planes EXTRAPOLATED to the edge pixel
                  (extrapolating is what makes this a depth STEP rather than a measure of
                  surface slant, which would fire on every slanted flat surface)
    The plane fit is done in inverse-depth: for a plane, 1/z is EXACTLY affine in (u,v),
    so the fit is linear (3x3 normal equations, batched) and the plane normal is recovered
    in closed form. Three IRLS passes with a Tukey redescending weight keep a couple of
    floater pixels in a ribbon from swinging the dihedral.
"""
import os
import sys

import cv2
import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
sys.path.insert(0, os.path.join(TIER1, "scripts/explore/syn"))

from src import common, render, dt_pull
from src.mesh_oracle import MeshOracle          # EVAL ONLY — labelling only
import final_recipe as FR

OUT = os.path.join(TIER1, "out")

# ribbon geometry (px)
OFF_ACROSS = (2.0, 3.0, 4.0)                     # ribbon centre +-3px, 3px thick
OFF_ALONG = np.arange(-4.5, 5.0, 1.0)            # 10px long
MIN_VALID = 8                                    # samples needed per ribbon side


def robust_plane_invz(u, v, invz, w0, iters=3, tukey_c=4.685):
    """Weighted robust fit invz ~ a + b*u + c*v, batched over N ribbons.
    u,v,invz,w0: [N,P]. Returns (abc[N,3], ok[N])."""
    N, P = u.shape
    w = w0.copy()
    abc = np.zeros((N, 3))
    ok = w0.sum(1) >= MIN_VALID
    for _ in range(iters):
        A = np.stack([np.ones_like(u), u, v], -1)              # [N,P,3]
        Aw = A * w[..., None]
        M = np.einsum("npi,npj->nij", Aw, A)                   # [N,3,3]
        b = np.einsum("npi,np->ni", Aw, invz)                  # [N,3]
        M[:, 0, 0] += 1e-12
        M[:, 1, 1] += 1e-12
        M[:, 2, 2] += 1e-12
        try:
            abc = np.linalg.solve(M, b)
        except np.linalg.LinAlgError:
            sol = np.zeros((N, 3))
            for i in range(N):
                try:
                    sol[i] = np.linalg.solve(M[i], b[i])
                except np.linalg.LinAlgError:
                    ok[i] = False
            abc = sol
        r = invz - np.einsum("npi,ni->np", A, abc)
        s = 1.4826 * np.median(np.abs(r) * (w0 > 0) + 1e12 * (w0 == 0), axis=1, keepdims=True)
        s = np.maximum(s, 1e-9)
        t = np.clip(r / (tukey_c * s), -1, 1)
        w = w0 * (1 - t ** 2) ** 2                             # Tukey biweight
    return abc, ok


def normal_from_invz(abc, f, cx, cy):
    """Camera-space plane normal from invz = a + b*u + c*v (see module docstring)."""
    a, b, c = abc[:, 0], abc[:, 1], abc[:, 2]
    n = np.stack([f * b, f * c, a + b * cx + c * cy], -1)
    nn = np.linalg.norm(n, axis=1, keepdims=True)
    return n / np.maximum(nn, 1e-30)


def ribbon_measure(px, py, dirx, diry, depth, fg, cam):
    """Bilateral ribbon dihedral + depth step at pixels (px,py). All numpy, vectorised.
    Returns dict(theta_deg[N], dstep[N], ok[N])."""
    H, W = depth.shape
    f, cx, cy = cam.f, cam.K[0, 2], cam.K[1, 2]
    # across = gradient direction; along = perpendicular
    ax, ay = dirx, diry
    lx, ly = -diry, dirx
    invd = np.where(fg & np.isfinite(depth) & (depth > 1e-6), 1.0 / np.maximum(depth, 1e-9), 0.0)
    valid = (fg & np.isfinite(depth) & (depth > 1e-6)).astype(np.float64)

    sides = {}
    for sgn, key in ((-1.0, "L"), (+1.0, "R")):
        us, vs, iz, wv = [], [], [], []
        for da in OFF_ACROSS:
            for dl in OFF_ALONG:
                qx = px + sgn * da * ax + dl * lx
                qy = py + sgn * da * ay + dl * ly
                qxc = np.clip(qx, 0, W - 1)
                qyc = np.clip(qy, 0, H - 1)
                iz.append(cv2.remap(invd.astype(np.float32), qxc.astype(np.float32),
                                    qyc.astype(np.float32), cv2.INTER_LINEAR).ravel())
                wv.append(cv2.remap(valid.astype(np.float32), qxc.astype(np.float32),
                                    qyc.astype(np.float32), cv2.INTER_NEAREST).ravel())
                us.append(qx)
                vs.append(qy)
        U = np.stack(us, -1)
        V = np.stack(vs, -1)
        IZ = np.stack(iz, -1).astype(np.float64)
        WV = np.stack(wv, -1).astype(np.float64)
        WV = WV * (IZ > 1e-9)
        abc, ok = robust_plane_invz(U, V, IZ, WV)
        sides[key] = (abc, ok)

    abcL, okL = sides["L"]
    abcR, okR = sides["R"]
    nL = normal_from_invz(abcL, f, cx, cy)
    nR = normal_from_invz(abcR, f, cx, cy)
    cosang = np.clip(np.abs((nL * nR).sum(1)), -1, 1)          # sign-agnostic
    theta = np.degrees(np.arccos(cosang))
    # both planes extrapolated TO THE EDGE PIXEL -> depth step
    izL = abcL[:, 0] + abcL[:, 1] * px + abcL[:, 2] * py
    izR = abcR[:, 0] + abcR[:, 1] * px + abcR[:, 2] * py
    zL = 1.0 / np.where(np.abs(izL) < 1e-9, np.nan, izL)
    zR = 1.0 / np.where(np.abs(izR) < 1e-9, np.nan, izR)
    zm = 0.5 * (np.abs(zL) + np.abs(zR))
    with np.errstate(all="ignore"):
        dstep = np.abs(zL - zR) / np.maximum(zm, 1e-9)
    ok = okL & okR & np.isfinite(theta) & np.isfinite(dstep)
    return {"theta": theta, "dstep": dstep, "ok": ok, "nL": nL, "nR": nR}


def pct(a, q):
    a = np.asarray(a)
    a = a[np.isfinite(a)]
    return float(np.percentile(a, q)) if len(a) else float("nan")


def main():
    scene = sys.argv[1] if len(sys.argv) > 1 else "chair"
    nviews = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    cams, rgb_paths = common.load_cameras(scene)
    g = common.load_gaussians(scene)
    keep = render.defloat_mask(g["mu"], g["opacity"])
    oracle = MeshOracle(scene)                                  # EVAL ONLY (labelling)
    views = np.unique(np.round(np.linspace(0, len(cams) - 1, nviews)).astype(int))
    print(f"[STEP 0] {scene}: bilateral-ribbon falsification over {len(views)} views "
          f"{list(views)}", flush=True)

    fields = {"sharp(pull field)": dt_pull.EDGE_SHARP, "m1a(seed field)": dt_pull.EDGE_M1A}
    acc = {k: {"fab": {"theta": [], "dstep": []}, "cre": {"theta": [], "dstep": []},
               "fab_i": {"theta": [], "dstep": []}, "cre_i": {"theta": [], "dstep": []},
               "n_edge": 0, "n_fab": 0, "n_cre": 0} for k in fields}

    for v in views:
        cam = cams[v]
        gb = render.render_gbuffer(g, keep, cam)
        depth = gb["depth"].cpu().numpy().astype(np.float64)
        alpha = gb["alpha"].cpu().numpy()
        del gb
        fg = alpha > 0.5

        # GT crease distance transform for this view (EVAL ONLY, labelling)
        uvq = oracle.visible_crease_uv(cam, view_key=int(v))
        cm = np.zeros((cam.H, cam.W), bool)
        cu = np.clip(np.round(uvq[:, 0]).astype(int), 0, cam.W - 1)
        cv_ = np.clip(np.round(uvq[:, 1]).astype(int), 0, cam.H - 1)
        cm[cv_, cu] = True
        cdt = cv2.distanceTransform((~cm).astype(np.uint8), cv2.DIST_L2, 5)

        # interior mask: drop pixels near the silhouette so occluding contours cannot
        # masquerade as either class (a silhouette has a huge depth step by definition)
        sil = fg ^ (cv2.erode(fg.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)
        sdt = cv2.distanceTransform((~sil).astype(np.uint8), cv2.DIST_L2, 5)
        interior = fg & (sdt > 4)

        im = cv2.imread(rgb_paths[v], cv2.IMREAD_UNCHANGED)
        a4 = im[:, :, 3:4].astype(np.float32) / 255.0
        bgr = (im[:, :, :3].astype(np.float32) * a4 + 255.0 * (1 - a4)).astype(np.uint8)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        gb1 = cv2.GaussianBlur(gray, (0, 0), 1.0)
        gx = cv2.Sobel(gb1, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(gb1, cv2.CV_64F, 0, 1, ksize=3)
        gm = np.sqrt(gx * gx + gy * gy)
        dirx = np.where(gm > 1e-9, gx / np.maximum(gm, 1e-9), 1.0)
        diry = np.where(gm > 1e-9, gy / np.maximum(gm, 1e-9), 0.0)

        for name, cfg in fields.items():
            edge = dt_pull.edge_map(rgb_paths[v], cfg)
            acc[name]["n_edge"] += int((edge & fg).sum())
            for tag, sel in (("", fg), ("_i", interior)):
                fab = edge & sel & (cdt > 3.0)
                cre = edge & sel & (cdt <= 2.0)
                for cls, m in (("fab", fab), ("cre", cre)):
                    ys, xs = np.nonzero(m)
                    if not len(ys):
                        continue
                    if len(ys) > 20000:                     # cap per view for speed
                        idx = np.random.RandomState(0).choice(len(ys), 20000, False)
                        ys, xs = ys[idx], xs[idx]
                    r = ribbon_measure(xs.astype(np.float64), ys.astype(np.float64),
                                       dirx[ys, xs], diry[ys, xs], depth, fg, cam)
                    ok = r["ok"]
                    acc[name][cls + tag]["theta"].append(r["theta"][ok])
                    acc[name][cls + tag]["dstep"].append(r["dstep"][ok])
                    if tag == "":
                        acc[name]["n_" + cls] += int(ok.sum())
        print(f"  view {v} done", flush=True)

    # ------------------------------------------------------------------ verdict
    results = {}
    for name in fields:
        A = acc[name]
        print("\n" + "=" * 92)
        print(f"STEP 0 RESULT — {scene}, edge field = {name}")
        print(f"  on-object Canny edge px {A['n_edge']}   labelled: FABRIC(no GT crease "
              f"within 3px) {A['n_fab']}   CREASE(GT crease within 2px) {A['n_cre']}")
        print("=" * 92)
        for tag, lab in (("", "all on-object"), ("_i", "INTERIOR only (>4px from silhouette)")):
            fth = np.concatenate(A["fab" + tag]["theta"]) if A["fab" + tag]["theta"] else np.array([])
            fds = np.concatenate(A["fab" + tag]["dstep"]) if A["fab" + tag]["dstep"] else np.array([])
            cth = np.concatenate(A["cre" + tag]["theta"]) if A["cre" + tag]["theta"] else np.array([])
            cds = np.concatenate(A["cre" + tag]["dstep"]) if A["cre" + tag]["dstep"] else np.array([])
            if not len(fth) or not len(cth):
                print(f"  [{lab}] insufficient samples")
                continue
            print(f"  [{lab}]  n_fabric={len(fth)}  n_crease={len(cth)}")
            print(f"    FABRIC theta  deg: p50 {pct(fth,50):6.2f}  p90 {pct(fth,90):6.2f}  "
                  f"p95 {pct(fth,95):6.2f}  p99 {pct(fth,99):6.2f}")
            print(f"    CREASE theta  deg: p05 {pct(cth,5):6.2f}  p10 {pct(cth,10):6.2f}  "
                  f"p25 {pct(cth,25):6.2f}  p50 {pct(cth,50):6.2f}")
            print(f"    FABRIC dd/d     %: p50 {100*pct(fds,50):6.3f}  p90 {100*pct(fds,90):6.3f}  "
                  f"p95 {100*pct(fds,95):6.3f}")
            print(f"    CREASE dd/d     %: p05 {100*pct(cds,5):6.3f}  p50 {100*pct(cds,50):6.3f}")
            if tag == "_i":
                results[name] = (pct(fth, 95), pct(cth, 5), pct(fds, 95), pct(cds, 5),
                                 fth, cth, fds, cds)

    print("\n" + "#" * 92)
    for name, (f95, c05, fd95, cd05, *_ ) in results.items():
        clean = (f95 <= 8.0 and fd95 <= 0.005 and (c05 >= 18.0 or cd05 >= 0.02))
        leaks = (f95 >= 12.0) or ((c05 - f95) < 6.0)
        verdict = "GATE CLEAN" if clean else ("GATE LEAKS" if leaks else "IN BETWEEN")
        print(f"# {name:20s} fabric theta_95={f95:6.2f}deg  crease theta_05={c05:6.2f}deg  "
              f"separation={c05-f95:+6.2f}deg")
        print(f"#   {'':18s} fabric (dd/d)_95={100*fd95:.3f}%  crease (dd/d)_05={100*cd05:.3f}%")
        print(f"#   ==> VERDICT: {verdict}")
        print(f"#       (clean needs fabric_th95<=8 AND fabric_dd95<=0.5% AND "
              f"(crease_th05>=18 OR crease_dd05>=2%); leaks if fabric_th95>=12 OR sep<6)")
    print("#" * 92, flush=True)

    # ------------------------------------------------------------------ histograms
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    n = len(results)
    fig, axes = plt.subplots(2, max(n, 1), figsize=(7 * max(n, 1), 8), squeeze=False)
    for j, (name, (f95, c05, fd95, cd05, fth, cth, fds, cds)) in enumerate(results.items()):
        ax = axes[0][j]
        bins = np.linspace(0, 90, 91)
        ax.hist(fth, bins=bins, alpha=0.6, density=True, label=f"FABRIC print (n={len(fth)})",
                color="tab:red")
        ax.hist(cth, bins=bins, alpha=0.6, density=True, label=f"TRUE crease (n={len(cth)})",
                color="tab:blue")
        ax.axvline(f95, color="tab:red", ls="--", label=f"fabric p95 = {f95:.1f}deg")
        ax.axvline(c05, color="tab:blue", ls="--", label=f"crease p05 = {c05:.1f}deg")
        ax.axvline(8, color="k", ls=":", lw=1)
        ax.axvline(18, color="k", ls=":", lw=1)
        ax.set_title(f"{scene} — bilateral ribbon DIHEDRAL\n{name} (interior only)")
        ax.set_xlabel("theta (deg)")
        ax.legend(fontsize=8)
        ax = axes[1][j]
        bins = np.linspace(0, 8, 81)
        ax.hist(100 * fds, bins=bins, alpha=0.6, density=True, color="tab:red", label="FABRIC print")
        ax.hist(100 * cds, bins=bins, alpha=0.6, density=True, color="tab:blue", label="TRUE crease")
        ax.axvline(100 * fd95, color="tab:red", ls="--", label=f"fabric p95 = {100*fd95:.2f}%")
        ax.axvline(0.5, color="k", ls=":", lw=1)
        ax.set_title("depth STEP (both planes extrapolated to the edge)")
        ax.set_xlabel("dd/d (%)")
        ax.legend(fontsize=8)
    plt.tight_layout()
    p = os.path.join(OUT, f"gate_falsify_{scene}.png")
    plt.savefig(p, dpi=110)
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
