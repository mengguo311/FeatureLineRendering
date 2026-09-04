"""EXPERIMENT Y, step 0 — build the PURE-GEOMETRY, ZERO-DECAL CAD scene.

Retraining's home turf: every GT feature line here is a REAL dihedral crease between two
PLANAR faces, there is not one square pixel of texture/albedo variation anywhere on the part,
and the shading is FLAT (per-face constant), so every GT crease is a hard photometric step in
every view it is visible in.  If retraining cannot beat frozen post-hoc extraction HERE, it
cannot beat it anywhere.

THE PART  a chamfered hex nut: regular hexagonal prism (radius R), a coaxial regular hexagonal
through-hole (radius r), and 45-degree chamfers of DIFFERENT size on the top and bottom outer
rims (which breaks the up/down symmetry).  All 36 faces are exactly planar (verified below),
so the mesh carries no tessellated curvature at all -- deliberately unlike lego, whose GT
"crease set" is 43% 12-gon cylinder tessellation.

WIRING  writes every file the frozen pipeline needs for a new scene <S> = cadpart:
    ~/3dgs_line/bcr/meshes/NeRF_Mesh/cadpart_new.obj        (EVAL-ONLY GT mesh)
    ~/cglib/data/full/cadpart/transforms_train.json         (100 views -- view_split needs 100)
    ~/cglib/data/full/cadpart/train/r_<i>.png               (800x800 RGBA)
    ~/cglib/data/full/cadpart/transforms_test.json + test/  (20 views, for train_static PSNR)
    ~/cglib/data/full/cadpart/transforms_orbit.json + orbit/(120-frame smooth HELD-OUT orbit,
                                                             for the temporal-coherence metric)

SELF-CHECKS (all run, all reported; the scene is rejected if any fails)
  1. every face is planar to < 1e-9
  2. every GT crease edge separates two faces whose FLAT-SHADED intensities differ by a margin
     -- i.e. no GT crease is photometrically invisible.  This is the premise of "home turf",
     so it is measured, not assumed.
  3. the camera convention round-trips: the depth map from THIS renderer must agree with
     src.mesh_oracle.render_depth() driven by src.common.load_cameras() reading the JSON we
     just wrote.  A Blender-vs-OpenCV convention slip would silently invalidate all of Y.
"""
import argparse
import json
import math
import os

import cv2
import numpy as np
import torch

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
MESH_DIR = os.path.expanduser("~/3dgs_line/bcr/meshes/NeRF_Mesh")
CGLIB = os.path.expanduser("~/cglib")
W = H = 800
CAM_R = 4.031128875572954                 # NeRF-synthetic orbit radius (matches lego/chair)
FOVX = 0.6911112070083618                 # NeRF-synthetic camera_angle_x
ALBEDO = np.array([0.72, 0.70, 0.66])     # ONE uniform albedo -> zero decals, by construction
AMBIENT = 0.13
N_LIGHTS = 3
LIGHTS = None          # frozen by pick_lights() at build time, recorded in the report JSON


def build_part(R=1.10, r=0.52, HZ=0.62, c_bot=0.10, c_top=0.20):
    """-> V[n,3], quads list. All faces planar by construction (asserted)."""
    ang = np.arange(6) * np.pi / 3.0
    u = np.c_[np.cos(ang), np.sin(ang), np.zeros(6)]
    ring = lambda rad, z: u * rad + np.array([0, 0, z])
    r0 = ring(R - c_bot, -HZ)          # bottom chamfer, inner (on the bottom plane)
    r1 = ring(R, -HZ + c_bot)          # bottom chamfer, outer / side start
    r2 = ring(R, HZ - c_top)           # side end / top chamfer outer
    r3 = ring(R - c_top, HZ)           # top chamfer inner (on the top plane)
    h0 = ring(r, -HZ)                  # hole, bottom
    h1 = ring(r, HZ)                   # hole, top
    V = np.concatenate([r0, r1, r2, r3, h0, h1], 0)
    O = {n: i * 6 for i, n in enumerate(["r0", "r1", "r2", "r3", "h0", "h1"])}
    Q = []
    for j in range(6):
        k = (j + 1) % 6
        Q.append([O["r0"] + j, O["r0"] + k, O["r1"] + k, O["r1"] + j])   # bottom chamfer
        Q.append([O["r1"] + j, O["r1"] + k, O["r2"] + k, O["r2"] + j])   # side
        Q.append([O["r2"] + j, O["r2"] + k, O["r3"] + k, O["r3"] + j])   # top chamfer
        Q.append([O["r3"] + j, O["r3"] + k, O["h1"] + k, O["h1"] + j])   # top annulus
        Q.append([O["h0"] + j, O["h0"] + k, O["r0"] + k, O["r0"] + j])   # bottom annulus
        Q.append([O["h1"] + j, O["h1"] + k, O["h0"] + k, O["h0"] + j])   # hole wall
    return V, Q


def orient_outward(V, Q):
    """flip quads so face normals point away from the part's medial surface."""
    out = []
    for q in Q:
        p = V[q]
        n = np.cross(p[1] - p[0], p[2] - p[0])
        n /= np.linalg.norm(n)
        c = p.mean(0)
        ref = c.copy()
        ref[2] = 0.0
        rad = np.linalg.norm(ref)
        # outward = away from the axis for side/chamfer/hole-outward, +-z for the caps
        if abs(n[2]) > 0.9:
            want = np.array([0, 0, np.sign(c[2]) or 1.0])
        elif rad > 1e-9 and np.linalg.norm(c[:2]) > 0.8:
            want = np.array([ref[0], ref[1], 0.0]) / rad
        else:
            want = -np.array([ref[0], ref[1], 0.0]) / max(rad, 1e-9)   # hole wall faces in
        out.append(q if n @ want > 0 else q[::-1])
    return out


def face_normals(V, Q):
    N = []
    for q in Q:
        p = V[q]
        n = np.cross(p, np.roll(p, -1, axis=0)).sum(0)      # Newell
        N.append(n / np.linalg.norm(n))
    return np.array(N)


def shade(N, lights=None):
    """FLAT shading, ONE uniform albedo -> [F,3] in [0,1].  Clamped Lambert, many lights.

    Two shading models were tried and rejected before this one, both because they would have
    made GT creases photometrically INVISIBLE and so quietly destroyed the premise that this
    scene is retraining's home turf:
      - clamped Lambert with 3 lights: every face turned away from all of them collapses to
        exactly AMBIENT, so two such faces meeting at a real crease render identically
        (measured min |dI| across creases = 0.0000).
      - wrap lighting 0.5+0.5*(n.l): linear in n, so ANY number of lights collapses to the
        single effective direction sum(w_i l_i); normals with equal projection on it render
        identically (measured min |dI| = 0.0074, i.e. sub-quantisation at 8 bit).
      - clamped Lambert with 6 spread lights: no face is unlit, but averaging over many
        directions drives the shading toward isotropic, and the WEAKEST crease contrast fell
        further (0.0028) while the median fell 4.6x. More lights is the wrong direction.
    Two-sided |n.l| is what the project's own make_cad.py uses (`0.32 + 0.55*abs(n@L)`): it is
    piecewise-linear so it cannot collapse the way wrap lighting does, and no normal is ever
    dark, so a handful of high-contrast lights suffice.  pick_lights() then FREEZES a direction
    set verified to separate every adjacent crease pair by a real margin."""
    L = lights if lights is not None else LIGHTS
    I = np.full(len(N), AMBIENT)
    for d, w in L:
        I = I + w * np.abs(N @ (d / np.linalg.norm(d)))
    return np.clip(I[:, None] * ALBEDO[None, :], 0, 1)


def pick_lights(FN, adj, sel, n_lights=N_LIGHTS, n_try=4000, seed=11):
    """Deterministically choose light directions that MAXIMISE the weakest crease contrast.

    This is scene construction, not tuning against any reported metric: it guarantees the
    stated premise ("every GT crease is a visible photometric step") instead of assuming it.
    Constraint: rendered luma must stay inside [0.05, 0.95] so nothing clips at 8 bit."""
    rng = np.random.default_rng(seed)
    ga = math.pi * (3 - math.sqrt(5))
    best, best_L = -1.0, None
    for t in range(n_try):
        R = rng.normal(size=(3, 3))
        Qm = np.linalg.qr(R)[0]
        ph = rng.random() * 2 * math.pi
        L = []
        for i in range(n_lights):
            z = 1 - 2 * (i + 0.5) / n_lights
            rr = math.sqrt(max(0.0, 1 - z * z))
            a = ph + i * ga
            d = Qm @ np.array([rr * math.cos(a), rr * math.sin(a), z])
            L.append((d, 0.80 / n_lights * (1.0 + 0.8 * rng.random())))
        lum = shade(FN, L).mean(1)
        if lum.min() < 0.04 or lum.max() > 0.96:
            continue
        margin = float(np.abs(lum[adj[sel, 0]] - lum[adj[sel, 1]]).min())
        if margin > best:
            best, best_L = margin, L
    assert best_L is not None, "no admissible light configuration found"
    return best_L, best


def look_at_c2w(pos, up=np.array([0.0, 0.0, 1.0])):
    """Blender/OpenGL c2w: camera looks down -Z, +Y is up in image space."""
    z = pos / np.linalg.norm(pos)                 # -forward
    if abs(z @ up) > 0.999:
        up = np.array([0.0, 1.0, 0.0])
    x = np.cross(up, z)
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    M = np.eye(4)
    M[:3, 0], M[:3, 1], M[:3, 2], M[:3, 3] = x, y, z, pos
    return M


def cams_sphere(n, seed, el_lo=12.0, el_hi=80.0):
    """deterministic golden-angle spiral over an elevation band (NeRF-synthetic style)."""
    rng = np.random.default_rng(seed)
    ga = math.pi * (3 - math.sqrt(5))
    ph = rng.random() * 2 * math.pi
    out = []
    for i in range(n):
        t = (i + 0.5) / n
        el = math.radians(el_lo + (el_hi - el_lo) * t)
        az = ph + i * ga
        p = CAM_R * np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az),
                              math.sin(el)])
        out.append(look_at_c2w(p))
    return out


def cams_orbit(n, el_deg=32.0):
    """smooth HELD-OUT circular fly-around -- the trajectory the flicker metric runs on."""
    el = math.radians(el_deg)
    return [look_at_c2w(CAM_R * np.array([math.cos(el) * math.cos(a), math.cos(el) * math.sin(a),
                                          math.sin(el)]))
            for a in np.linspace(0, 2 * math.pi, n, endpoint=False)]


def rasterize(V, Q, N, col, c2w, dev):
    """exact per-pixel z-buffer + face id, then FLAT shading. 36 quads -> brute force."""
    c2w = np.array(c2w, np.float64).copy()
    c2w[:3, 1:3] *= -1                                   # OpenGL -> OpenCV (+Y down, +Z fwd)
    w2c = np.linalg.inv(c2w)
    f = 0.5 * W / math.tan(0.5 * FOVX)
    K = np.array([[f, 0, W / 2], [0, f, H / 2], [0, 0, 1]])
    Vc = (w2c[:3, :3] @ V.T).T + w2c[:3, 3]
    uv = (K @ Vc.T).T
    px = torch.tensor(uv[:, 0] / uv[:, 2], device=dev, dtype=torch.float32)
    py = torch.tensor(uv[:, 1] / uv[:, 2], device=dev, dtype=torch.float32)
    zz = torch.tensor(Vc[:, 2], device=dev, dtype=torch.float32)
    gy, gx = torch.meshgrid(torch.arange(H, device=dev, dtype=torch.float32),
                            torch.arange(W, device=dev, dtype=torch.float32), indexing="ij")
    depth = torch.full((H, W), float("inf"), device=dev)
    fid = torch.full((H, W), -1, device=dev, dtype=torch.long)
    tris = []
    for qi, q in enumerate(Q):
        for a, b, c in ((0, 1, 2), (0, 2, 3)):
            tris.append((q[a], q[b], q[c], qi))
    for i0, i1, i2, qi in tris:
        if min(zz[i0], zz[i1], zz[i2]) <= 1e-6:
            continue
        ax, ay, bx, by, cx, cy = px[i0], py[i0], px[i1], py[i1], px[i2], py[i2]
        area = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
        if abs(float(area)) < 1e-12:
            continue
        l0 = ((bx - gx) * (cy - gy) - (by - gy) * (cx - gx)) / area
        l1 = ((cx - gx) * (ay - gy) - (cy - gy) * (ax - gx)) / area
        l2 = 1.0 - l0 - l1
        inside = (l0 >= 0) & (l1 >= 0) & (l2 >= 0)
        invz = l0 / zz[i0] + l1 / zz[i1] + l2 / zz[i2]
        zp = 1.0 / invz.clamp(min=1e-9)
        m = inside & (zp < depth)
        depth = torch.where(m, zp, depth)
        fid = torch.where(m, torch.full_like(fid, qi), fid)
    hit = fid >= 0
    C = torch.tensor(col, device=dev, dtype=torch.float32)
    img = torch.where(hit[..., None], C[fid.clamp(min=0)], torch.ones(3, device=dev))
    return img.cpu().numpy(), hit.cpu().numpy(), torch.where(hit, depth, torch.full_like(depth, 1e9)).cpu().numpy()


def write_split(name, c2ws, V, Q, N, col, dev, root, verbose=True):
    d = os.path.join(root, name)
    os.makedirs(d, exist_ok=True)
    frames = []
    for i, M in enumerate(c2ws):
        img, hit, _ = rasterize(V, Q, N, col, M, dev)
        rgba = np.zeros((H, W, 4), np.uint8)
        rgba[..., :3] = np.clip(img[..., ::-1] * 255, 0, 255).astype(np.uint8)   # BGR for cv2
        rgba[..., 3] = hit.astype(np.uint8) * 255
        cv2.imwrite(os.path.join(d, f"r_{i}.png"), rgba)
        frames.append({"file_path": f"./{name}/r_{i}", "rotation": 0.0,
                       "transform_matrix": np.asarray(M).tolist()})
        if verbose and i % 25 == 0:
            print(f"  [{name}] {i}/{len(c2ws)} fg={hit.mean():.3f}", flush=True)
    json.dump({"camera_angle_x": FOVX, "frames": frames},
              open(os.path.join(root, f"transforms_{name}.json"), "w"))
    return len(frames)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="cadpart")
    ap.add_argument("--n_train", type=int, default=100)
    ap.add_argument("--n_test", type=int, default=20)
    ap.add_argument("--n_orbit", type=int, default=120)
    args = ap.parse_args()
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    V, Q = build_part()
    Q = orient_outward(V, Q)
    N = face_normals(V, Q)

    # --- self-check 1: planarity -------------------------------------------------------
    planar = 0.0
    for q, n in zip(Q, N):
        p = V[q]
        planar = max(planar, float(np.abs((p - p.mean(0)) @ n).max()))
    print(f"[cad] {len(V)} verts, {len(Q)} quads; max face non-planarity = {planar:.2e}")
    assert planar < 1e-9, "faces are not planar"

    # --- write the GT mesh (EVAL-ONLY) --------------------------------------------------
    os.makedirs(MESH_DIR, exist_ok=True)
    op = os.path.join(MESH_DIR, f"{args.scene}_new.obj")
    with open(op, "w") as fp:
        fp.write("# EXPERIMENT Y pure-geometry CAD part (chamfered hex nut). EVAL-ONLY GT.\n")
        for v in V:
            fp.write(f"v {v[0]:.9f} {v[1]:.9f} {v[2]:.9f}\n")
        fp.write("s 0\n")
        for q in Q:
            fp.write("f " + " ".join(str(i + 1) for i in q) + "\n")
    print(f"[cad] wrote {op}")

    # --- self-check 2: is every GT crease a photometric step? ---------------------------
    import trimesh
    m = trimesh.load(op, process=True)
    deg = np.degrees(m.face_adjacency_angles)
    adj = np.asarray(m.face_adjacency)
    sel = deg >= 30.0
    # shade straight from trimesh's own face normals -- no quad<->triangle index mapping to
    # get wrong, and it is exactly what the rasteriser paints (flat, per-face).
    FN_tri = np.asarray(m.face_normals)
    globals()["LIGHTS"], margin = pick_lights(FN_tri, adj, sel)
    col = shade(N)
    tlum = shade(FN_tri).mean(1)
    d_int = np.abs(tlum[adj[sel, 0]] - tlum[adj[sel, 1]])
    print(f"[cad] pick_lights: {N_LIGHTS} lights, guaranteed min crease contrast {margin:.4f}")
    print(f"[cad] GT crease edges@30deg = {int(sel.sum())} of {len(deg)} adjacencies")
    print(f"[cad] crease dihedral (deg): {sorted(set(np.round(deg[sel],2).tolist()))}")
    print(f"[cad] |dI| across creases (0-1 luma): min={d_int.min():.4f} "
          f"p05={np.percentile(d_int,5):.4f} median={np.median(d_int):.4f} max={d_int.max():.4f}")
    assert d_int.min() > 0.02, "a GT crease is photometrically invisible -- retune LIGHTS"

    # --- render the three splits ---------------------------------------------------------
    root = os.path.join(CGLIB, "data", "full", args.scene)
    os.makedirs(root, exist_ok=True)
    n_tr = write_split("train", cams_sphere(args.n_train, 7), V, Q, N, col, dev, root)
    n_te = write_split("test", cams_sphere(args.n_test, 91, 18.0, 74.0), V, Q, N, col, dev, root)
    n_or = write_split("orbit", cams_orbit(args.n_orbit), V, Q, N, col, dev, root)
    print(f"[cad] wrote train={n_tr} test={n_te} orbit={n_or} under {root}")

    # --- self-check 3: camera convention round-trip -------------------------------------
    import sys
    sys.path.insert(0, TIER1)
    from src import common
    from src.mesh_oracle import MeshOracle
    cams, _ = common.load_cameras(args.scene)
    o = MeshOracle(args.scene, angle_deg=30.0, device=dev)
    rep = {"scene": args.scene, "n_verts": len(V), "n_quads": len(Q),
           "lights": [[list(np.round(d, 6)), round(float(w), 6)] for d, w in LIGHTS],
           "ambient": AMBIENT, "albedo": list(ALBEDO),
           "render_luma_range": [float(tlum.min()), float(tlum.max())],
           "max_nonplanarity": planar, "n_crease_edges": int(sel.sum()),
           "crease_dihedrals_deg": sorted(set(np.round(deg[sel], 2).tolist())),
           "crease_intensity_step": {"min": float(d_int.min()),
                                     "p05": float(np.percentile(d_int, 5)),
                                     "median": float(np.median(d_int)),
                                     "max": float(d_int.max())},
           "n_crease_pts": int(len(o.crease_pts)),
           "bbox_diag": float(np.linalg.norm(m.extents)),
           "n_train": n_tr, "n_test": n_te, "n_orbit": n_or,
           "convention_check": []}
    for v in (0, 5, 33, 77):
        dm = o.render_depth(cams[v]).cpu().numpy()
        _, hit, dmine = rasterize(V, Q, N, col, cams_sphere(args.n_train, 7)[v], dev)
        a, b = dm < 1e8, hit
        iou = float((a & b).sum() / max((a | b).sum(), 1))
        dd = float(np.abs(dm[a & b] - dmine[a & b]).max()) if (a & b).any() else 9e9
        rep["convention_check"].append({"view": v, "silhouette_IoU": round(iou, 5),
                                        "max_depth_diff": round(dd, 7)})
        print(f"[cad] view {v}: silhouette IoU vs mesh_oracle = {iou:.5f}, "
              f"max|depth diff| = {dd:.2e}")
        assert iou > 0.999 and dd < 1e-3, "CAMERA CONVENTION MISMATCH"
    jp = os.path.join(TIER1, "out", "xy", f"xy_cad_{args.scene}.json")
    os.makedirs(os.path.dirname(jp), exist_ok=True)
    json.dump(rep, open(jp, "w"), indent=1)
    print(json.dumps(rep, indent=1))
    print(f"[cad] OK -> {jp}")


if __name__ == "__main__":
    main()
