# -*- coding: utf-8 -*-
"""
Schematic figures for 3DGS feature-line proposal (kaiti report).

Scene: a flat-shaded CUBE (gives creases + corners) and a smooth SPHERE
(gives a pure silhouette, no creases).

Figure A  - IMAGE-SPACE line drawing:
    Render a depth+normal G-buffer, add mild noise (mimicking a real 3DGS
    G-buffer), run Sobel on depth & normal -> threshold -> raster edge map.
    -> works for ANY representation (incl. 3DGS) but is noisy / flickers.

Figure B  - OBJECT-SPACE line drawing:
    Use mesh connectivity to extract silhouette / crease / corner lines,
    hidden-line removed against the depth buffer -> clean vector lines.
    -> precise & temporally stable, but needs explicit mesh topology
       which 3DGS does NOT have.
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from scipy.ndimage import gaussian_filter

np.random.seed(7)

# ----------------------------------------------------------------------
# Mesh builders  -> (V (n,3), F (m,3), flat_bool)
# ----------------------------------------------------------------------
def make_cube(center, size):
    c = np.asarray(center, float); s = size * 0.5
    V = np.array([[-1,-1,-1],[ 1,-1,-1],[ 1, 1,-1],[-1, 1,-1],
                  [-1,-1, 1],[ 1,-1, 1],[ 1, 1, 1],[-1, 1, 1]], float) * s + c
    F = np.array([[0,2,1],[0,3,2],   # -z
                  [4,5,6],[4,6,7],   # +z
                  [0,1,5],[0,5,4],   # -y
                  [2,3,7],[2,7,6],   # +y
                  [1,2,6],[1,6,5],   # +x
                  [0,4,7],[0,7,3]],  # -x
                 int)
    return V, F, True


def make_icosphere(center, radius, subdiv=3):
    c = np.asarray(center, float)
    t = (1.0 + 5 ** 0.5) / 2.0
    V = np.array([[-1, t, 0],[1, t, 0],[-1,-t, 0],[1,-t, 0],
                  [0,-1, t],[0, 1, t],[0,-1,-t],[0, 1,-t],
                  [t, 0,-1],[t, 0, 1],[-t, 0,-1],[-t, 0, 1]], float)
    F = np.array([[0,11,5],[0,5,1],[0,1,7],[0,7,10],[0,10,11],
                  [1,5,9],[5,11,4],[11,10,2],[10,7,6],[7,1,8],
                  [3,9,4],[3,4,2],[3,2,6],[3,6,8],[3,8,9],
                  [4,9,5],[2,4,11],[6,2,10],[8,6,7],[9,8,1]], int)
    V = list(map(np.array, V)); cache = {}
    def mid(a, b):
        key = (min(a, b), max(a, b))
        if key in cache: return cache[key]
        m = (V[a] + V[b]) / 2.0; V.append(m); cache[key] = len(V) - 1
        return cache[key]
    for _ in range(subdiv):
        nf = []
        for a, b, cc in F:
            ab, bc, ca = mid(a, b), mid(b, cc), mid(cc, a)
            nf += [[a, ab, ca],[b, bc, ab],[cc, ca, bc],[ab, bc, ca]]
        F = np.array(nf, int)
    V = np.array(V, float)
    V = V / np.linalg.norm(V, axis=1, keepdims=True) * radius + c
    return V, F, False


def merge(meshes):
    """Concatenate meshes; keep per-object id + flat/smooth flag per face."""
    Vs, Fs, fobj, fflat, voff = [], [], [], [], 0
    for oid, (V, F, flat) in enumerate(meshes):
        Vs.append(V); Fs.append(F + voff)
        fobj.append(np.full(len(F), oid)); fflat.append(np.full(len(F), flat))
        voff += len(V)
    return (np.vstack(Vs), np.vstack(Fs),
            np.concatenate(fobj), np.concatenate(fflat))


# ----------------------------------------------------------------------
# Camera
# ----------------------------------------------------------------------
def look_at(eye, target, up=(0, 1, 0)):
    eye, target, up = map(lambda x: np.asarray(x, float), (eye, target, up))
    f = target - eye; f /= np.linalg.norm(f)
    r = np.cross(f, up); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    M = np.eye(4)
    M[0, :3] = r; M[1, :3] = u; M[2, :3] = -f
    M[:3, 3] = -M[:3, :3] @ eye
    return M


def perspective(fov_deg, aspect, near, far):
    fy = 1.0 / np.tan(np.radians(fov_deg) / 2)
    P = np.zeros((4, 4))
    P[0, 0] = fy / aspect; P[1, 1] = fy
    P[2, 2] = (far + near) / (near - far)
    P[2, 3] = 2 * far * near / (near - far)
    P[3, 2] = -1
    return P


# ----------------------------------------------------------------------
# Software rasterizer -> G-buffers
# ----------------------------------------------------------------------
def rasterize(V, F, fflat, view, proj, W, H, light=(-0.4, 0.8, 0.6)):
    Vc = (view @ np.c_[V, np.ones(len(V))].T).T          # view space
    vz = Vc[:, 2]                                         # view-space z (neg fwd)
    clip = (proj @ Vc.T).T
    w = clip[:, 3].copy(); w[np.abs(w) < 1e-9] = 1e-9
    ndc = clip[:, :3] / w[:, None]
    sx = (ndc[:, 0] * 0.5 + 0.5) * W
    sy = (1 - (ndc[:, 1] * 0.5 + 0.5)) * H
    invw = 1.0 / w

    # per-vertex smooth normals (area-weighted) for smooth objects
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    fn /= (np.linalg.norm(fn, axis=1, keepdims=True) + 1e-12)
    vn = np.zeros_like(V)
    for i, f in enumerate(F):
        vn[f] += fn[i]
    vn /= (np.linalg.norm(vn, axis=1, keepdims=True) + 1e-12)

    INF = 1e9
    zbuf = np.full((H, W), INF)            # ndc depth
    depth = np.full((H, W), np.nan)        # linear view depth (positive)
    normal = np.zeros((H, W, 3))
    objfid = np.full((H, W), -1, int)
    shade = np.ones((H, W, 3))             # base shaded render (light grey bg)
    mask = np.zeros((H, W), bool)
    L = np.asarray(light, float); L /= np.linalg.norm(L)

    for fi, tri in enumerate(F):
        i0, i1, i2 = tri
        x0, y0 = sx[i0], sy[i0]; x1, y1 = sx[i1], sy[i1]; x2, y2 = sx[i2], sy[i2]
        minx = max(int(np.floor(min(x0, x1, x2))), 0)
        maxx = min(int(np.ceil(max(x0, x1, x2))), W - 1)
        miny = max(int(np.floor(min(y0, y1, y2))), 0)
        maxy = min(int(np.ceil(max(y0, y1, y2))), H - 1)
        if minx > maxx or miny > maxy:
            continue
        area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
        if abs(area) < 1e-7:
            continue
        ys, xs = np.mgrid[miny:maxy + 1, minx:maxx + 1]
        px, py = xs + 0.5, ys + 0.5
        w0 = ((x1 - px) * (y2 - py) - (x2 - px) * (y1 - py)) / area
        w1 = ((x2 - px) * (y0 - py) - (x0 - px) * (y2 - py)) / area
        w2 = 1 - w0 - w1
        inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        if not inside.any():
            continue
        # perspective-correct interpolation
        iw = w0 * invw[i0] + w1 * invw[i1] + w2 * invw[i2]
        ndcz = (w0 * (ndc[i0, 2] * invw[i0]) + w1 * (ndc[i1, 2] * invw[i1])
                + w2 * (ndc[i2, 2] * invw[i2])) / iw
        vzz = (w0 * (vz[i0] * invw[i0]) + w1 * (vz[i1] * invw[i1])
               + w2 * (vz[i2] * invw[i2])) / iw

        sub = inside
        gy, gx = ys[sub], xs[sub]
        cand = ndcz[sub]
        closer = cand < zbuf[gy, gx]
        sel = np.zeros_like(sub); sel[sub] = closer
        if not sel.any():
            continue
        gy, gx = ys[sel], xs[sel]
        zbuf[gy, gx] = ndcz[sel]
        depth[gy, gx] = -vzz[sel]                       # positive depth
        objfid[gy, gx] = fi
        mask[gy, gx] = True
        if fflat[fi]:
            n = np.broadcast_to(fn[fi], (sel.sum(), 3)).copy()
        else:
            ww0, ww1, ww2 = w0[sel], w1[sel], w2[sel]
            n = (ww0[:, None] * vn[i0] + ww1[:, None] * vn[i1]
                 + ww2[:, None] * vn[i2])
            n /= (np.linalg.norm(n, axis=1, keepdims=True) + 1e-12)
        normal[gy, gx] = n
        diff = np.clip(np.abs(n @ L), 0, 1)
        col = 0.32 + 0.6 * diff                          # grey lambert
        shade[gy, gx] = np.stack([col, col, col], axis=1)

    return dict(depth=depth, normal=normal, objfid=objfid, shade=shade,
                mask=mask, sx=sx, sy=sy, vz=vz, fn=fn)


# ----------------------------------------------------------------------
# IMAGE-SPACE edges  (Sobel on noisy G-buffer)
# ----------------------------------------------------------------------
def sobel_mag(img):
    if img.ndim == 2:
        img = img[..., None]
    Kx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], float)
    Ky = Kx.T
    from scipy.ndimage import convolve
    gx = sum(convolve(img[..., c], Kx, mode="nearest") for c in range(img.shape[2]))
    gy = sum(convolve(img[..., c], Ky, mode="nearest") for c in range(img.shape[2]))
    return np.hypot(gx, gy)


def image_space_edges(gb, noise=0.14, thr=0.10, seed=0):
    from scipy.ndimage import binary_dilation
    rng = np.random.default_rng(seed)
    H, W = gb["depth"].shape
    depth = gb["depth"].copy()
    bg = ~gb["mask"]
    depth[bg] = np.nanmax(depth[gb["mask"]]) + 0.5        # background plane
    dmin, dmax = np.nanmin(depth), np.nanmax(depth)
    dn0 = (depth - dmin) / (dmax - dmin + 1e-9)
    nrm0 = gb["normal"].copy()
    nrm0[bg] = np.array([0, 0, 1.0])

    # clean edges -> band around the *true* discontinuities
    clean = sobel_mag(dn0) * 3.5 + sobel_mag(nrm0) * 1.0
    band = binary_dilation((clean / (clean.max() + 1e-9)) > 0.18, iterations=6)

    # mimic an imperfect 3DGS G-buffer: small low-freq warp everywhere (edges
    # wiggle/break) + high-freq noise gated to the edge band (3DGS depth/normal
    # noise is worst at depth discontinuities) -> jagged, broken, spurious specks.
    bandf = band.astype(float)
    dn = (dn0
          + gaussian_filter(rng.standard_normal((H, W)), 2.5) * 0.03
          + gaussian_filter(rng.standard_normal((H, W)), 0.6) * noise * bandf)
    nrm = (nrm0
           + gaussian_filter(rng.standard_normal((H, W, 3)), (0.6, 0.6, 0))
           * noise * 1.4 * bandf[..., None])
    edge = sobel_mag(dn) * 3.5 + sobel_mag(nrm) * 1.0
    edge = edge / (edge.max() + 1e-9)
    near = binary_dilation(gb["mask"], iterations=4)
    binary = (edge > thr) & near
    binary = binary_dilation(binary, iterations=1) & near   # fatten -> fuzzy look
    return edge, binary


# ----------------------------------------------------------------------
# OBJECT-SPACE edges  (from mesh connectivity)
# ----------------------------------------------------------------------
def build_edge_faces(F):
    em = {}
    for fi, tri in enumerate(F):
        for a, b in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
            k = (min(a, b), max(a, b))
            em.setdefault(k, []).append(fi)
    return em


def object_space_lines(V, F, gb, view, eye, crease_deg=25.0):
    fn = gb["fn"]
    em = build_edge_faces(F)
    fcent = V[F].mean(axis=1)
    eye = np.asarray(eye, float)
    sil, crease, inc = [], [], {}
    for (a, b), faces in em.items():
        if len(faces) != 2:
            continue
        f0, f1 = faces
        # front/back facing wrt camera
        s0 = np.dot(fn[f0], eye - fcent[f0])
        s1 = np.dot(fn[f1], eye - fcent[f1])
        if s0 * s1 < 0:                                   # silhouette
            sil.append((a, b))
        dih = np.degrees(np.arccos(np.clip(np.dot(fn[f0], fn[f1]), -1, 1)))
        if dih > crease_deg:                              # crease (hidden-line removed later)
            crease.append((a, b))
            inc[a] = inc.get(a, 0) + 1
            inc[b] = inc.get(b, 0) + 1
    corners = [v for v, c in inc.items() if c >= 3]        # all corners; visibility tested at draw
    return sil, crease, corners


def visible_points(V, idx, view, proj, W, H, depthbuf, bias=0.06):
    if not len(idx):
        return np.empty((0, 2))
    scr, vd = project_pts(V[idx], view, proj, W, H)
    keep = []
    for i in range(len(idx)):
        x, y = int(round(scr[i, 0])), int(round(scr[i, 1]))
        if 0 <= x < W and 0 <= y < H:
            db = depthbuf[y, x]
            if np.isnan(db) or vd[i] <= db + bias:
                keep.append(scr[i])
    return np.array(keep) if keep else np.empty((0, 2))


def project_pts(P, view, proj, W, H):
    P = np.atleast_2d(P)
    Vc = (view @ np.c_[P, np.ones(len(P))].T).T
    clip = (proj @ Vc.T).T
    w = clip[:, 3].copy(); w[np.abs(w) < 1e-9] = 1e-9
    ndc = clip[:, :3] / w[:, None]
    sx = (ndc[:, 0] * 0.5 + 0.5) * W
    sy = (1 - (ndc[:, 1] * 0.5 + 0.5)) * H
    return np.column_stack([sx, sy]), -Vc[:, 2]           # screen + view depth


def visible_segments(V, edges, view, proj, W, H, depthbuf, samples=24, bias=0.06):
    """Split each 3D edge into visible sub-segments via depth-buffer test."""
    out = []
    for a, b in edges:
        ts = np.linspace(0, 1, samples)
        pts = V[a][None] * (1 - ts)[:, None] + V[b][None] * ts[:, None]
        scr, vd = project_pts(pts, view, proj, W, H)
        vis = np.zeros(samples, bool)
        for i in range(samples):
            x, y = int(round(scr[i, 0])), int(round(scr[i, 1]))
            if 0 <= x < W and 0 <= y < H:
                db = depthbuf[y, x]
                vis[i] = np.isnan(db) or (vd[i] <= db + bias)
        # group consecutive visible samples into polyline segments
        i = 0
        while i < samples:
            if vis[i]:
                j = i
                while j + 1 < samples and vis[j + 1]:
                    j += 1
                if j > i:
                    out.append(scr[i:j + 1])
                i = j + 1
            else:
                i += 1
    return out


# ----------------------------------------------------------------------
# Scene + render
# ----------------------------------------------------------------------
W, H = 900, 640
scene = [make_cube(center=(-1.05, 0, 0), size=1.55),
         make_icosphere(center=(1.15, -0.05, 0.15), radius=0.95, subdiv=3)]
V, F, fobj, fflat = merge(scene)

eye = (2.6, 2.2, 4.6)
target = (0, -0.1, 0)
view = look_at(eye, target)
proj = perspective(38, W / H, 0.1, 50)

gb = rasterize(V, F, fflat, view, proj, W, H)

# ---------------- Figure A : IMAGE-SPACE ----------------
edge, binary = image_space_edges(gb, seed=1)

fig, ax = plt.subplots(1, 2, figsize=(11, 4.1))
fig.patch.set_facecolor("white")
# left: the G-buffer input (normal map)
nm = (gb["normal"] * 0.5 + 0.5)
nm[~gb["mask"]] = 0.96
ax[0].imshow(nm)
ax[0].set_title("Input: depth + normal G-buffer\n(available for ANY representation, incl. 3DGS)",
                fontsize=11)
# right: image-space edges over faint render
base = gb["shade"].copy(); base[~gb["mask"]] = 1.0
canvas = base * 0.35 + 0.65
em = np.ma.masked_where(~binary, binary)
ax[1].imshow(canvas)
ax[1].imshow(em, cmap="gray_r", vmin=0, vmax=1, interpolation="nearest")
ax[1].set_title("Image-space lines: Sobel/Canny on G-buffer\n"
                "universal, but NOISY & temporally unstable (flicker)",
                fontsize=11, color="#b00000")
for a in ax:
    a.set_xticks([]); a.set_yticks([])
    for s in a.spines.values():
        s.set_visible(False)
# zoom inset auto-centred on a visible cube corner (vertex 6 = +x,+y,+z)
axins = ax[1].inset_axes([0.60, 0.04, 0.36, 0.40])
cx, cy = gb["sx"][6], gb["sy"][6]
x0 = int(np.clip(cx - 95, 0, W - 2)); x1 = int(np.clip(cx + 95, 1, W - 1))
y0 = int(np.clip(cy - 75, 0, H - 2)); y1 = int(np.clip(cy + 75, 1, H - 1))
axins.imshow(canvas[y0:y1, x0:x1])
axins.imshow(np.ma.masked_where(~binary, binary)[y0:y1, x0:x1],
             cmap="gray_r", vmin=0, vmax=1, interpolation="nearest")
axins.set_xticks([]); axins.set_yticks([])
for s in axins.spines.values():
    s.set_edgecolor("#b00000"); s.set_linewidth(1.5)
axins.set_title("jagged / broken", fontsize=8, color="#b00000", pad=2)
plt.tight_layout()
plt.savefig("fig_A_image_space.png", dpi=200, bbox_inches="tight")
plt.close()

# ---------------- Figure B : OBJECT-SPACE ----------------
sil, crease, corners = object_space_lines(V, F, gb, view, eye)
# silhouettes sit at grazing angles -> generous bias so self-occlusion rounding
# doesn't shred them, while a real occluder (cube over sphere) still culls them.
seg_sil = visible_segments(V, sil, view, proj, W, H, gb["depth"], bias=0.35)
seg_cre = visible_segments(V, crease, view, proj, W, H, gb["depth"], bias=0.06)
cpts = visible_points(V, corners, view, proj, W, H, gb["depth"], bias=0.08)

fig, ax = plt.subplots(figsize=(6.0, 4.4))
fig.patch.set_facecolor("white")
base = gb["shade"].copy(); base[~gb["mask"]] = 1.0
ax.imshow(base * 0.25 + 0.75)
ax.add_collection(LineCollection(seg_sil, colors="#1f5fd6", linewidths=2.4))
ax.add_collection(LineCollection(seg_cre, colors="#d6451f", linewidths=2.4))
if len(cpts):
    ax.scatter(cpts[:, 0], cpts[:, 1], s=42, facecolor="#15a015",
               edgecolor="white", linewidth=1.0, zorder=5)
ax.set_xlim(0, W); ax.set_ylim(H, 0)
ax.set_xticks([]); ax.set_yticks([])
for s in ax.spines.values():
    s.set_visible(False)
ax.set_title("Object-space lines from mesh connectivity\n"
             "precise & temporally STABLE — but needs explicit topology (3DGS has none)",
             fontsize=10.5, color="#0a6b0a")
from matplotlib.lines import Line2D
leg = [Line2D([0], [0], color="#1f5fd6", lw=2.4, label="silhouette"),
       Line2D([0], [0], color="#d6451f", lw=2.4, label="crease"),
       Line2D([0], [0], marker="o", color="w", markerfacecolor="#15a015",
              markeredgecolor="white", markersize=9, label="corner")]
ax.legend(handles=leg, loc="upper right", fontsize=9, framealpha=0.9)
plt.tight_layout()
plt.savefig("fig_B_object_space.png", dpi=200, bbox_inches="tight")
plt.close()

# ---------------- Figure C : side-by-side combined ----------------
fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.4))
fig.patch.set_facecolor("white")
canvas = (gb["shade"].copy()); canvas[~gb["mask"]] = 1.0
ax[0].imshow(canvas * 0.35 + 0.65)
ax[0].imshow(np.ma.masked_where(~binary, binary), cmap="gray_r",
             vmin=0, vmax=1, interpolation="nearest")
ax[0].set_title("(a) IMAGE-SPACE  —  works on 3DGS, but noisy + flickers",
                fontsize=11, color="#b00000")
ax[1].imshow(canvas * 0.25 + 0.75)
ax[1].add_collection(LineCollection(seg_sil, colors="#1f5fd6", linewidths=2.4))
ax[1].add_collection(LineCollection(seg_cre, colors="#d6451f", linewidths=2.4))
if len(cpts):
    ax[1].scatter(cpts[:, 0], cpts[:, 1], s=42, facecolor="#15a015",
                  edgecolor="white", linewidth=1.0, zorder=5)
ax[1].set_xlim(0, W); ax[1].set_ylim(H, 0)
ax[1].set_title("(b) OBJECT-SPACE  —  clean + stable, but needs a mesh (3DGS lacks one)",
                fontsize=11, color="#0a6b0a")
for a in ax:
    a.set_xticks([]); a.set_yticks([])
    for s in a.spines.values():
        s.set_visible(False)
ax[1].legend(handles=leg, loc="upper right", fontsize=8.5, framealpha=0.9)
plt.tight_layout()
plt.savefig("fig_C_comparison.png", dpi=200, bbox_inches="tight")
plt.close()

# ---------------- Figure D : temporal flicker (image-space) ----------------
def orbit(eye, target, deg):
    e = np.asarray(eye, float) - np.asarray(target, float)
    a = np.radians(deg)
    R = np.array([[np.cos(a), 0, np.sin(a)], [0, 1, 0], [-np.sin(a), 0, np.cos(a)]])
    return R @ e + np.asarray(target, float)

eye2 = orbit(eye, target, 2.5)
view2 = look_at(eye2, target)
gb2 = rasterize(V, F, fflat, view2, proj, W, H)
_, bin1 = image_space_edges(gb, seed=11)
_, bin2 = image_space_edges(gb2, seed=22)

fig, ax = plt.subplots(1, 3, figsize=(13.2, 3.5))
fig.patch.set_facecolor("white")
for a, b, ttl in [(ax[0], bin1, "frame t"), (ax[1], bin2, "frame t+1 (camera moved 2.5°)")]:
    a.imshow(np.ones((H, W, 3)))
    a.imshow(np.ma.masked_where(~b, b), cmap="gray_r", vmin=0, vmax=1, interpolation="nearest")
    a.set_title("Image-space lines, " + ttl, fontsize=10.5)
diff = bin1 ^ bin2
rgb = np.ones((H, W, 3))
rgb[bin1 & bin2] = [0.75, 0.75, 0.75]      # stable edges = grey
rgb[diff] = [0.85, 0.05, 0.05]             # changed pixels = red
ax[2].imshow(rgb, interpolation="nearest")
ax[2].set_title("Difference (red = flickering pixels)\nno 3D anchoring → edges are NOT temporally stable",
                fontsize=10.5, color="#b00000")
for a in ax:
    a.set_xticks([]); a.set_yticks([])
    for s in a.spines.values():
        s.set_visible(False)
plt.tight_layout()
plt.savefig("fig_D_flicker.png", dpi=200, bbox_inches="tight")
plt.close()

flick = diff.sum() / max((bin1 | bin2).sum(), 1)
print("counts: silhouette=%d crease=%d corner=%d" % (len(sil), len(crease), len(corners)))
print("flicker ratio (changed / union edge px) = %.1f%%" % (100 * flick))
print("saved: fig_A_image_space.png fig_B_object_space.png fig_C_comparison.png fig_D_flicker.png")
