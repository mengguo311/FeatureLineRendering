# -*- coding: utf-8 -*-
"""Synthesize an ANGULAR object (hexagonal prism, nut-like) as a 3DGS-style .splat:
flat Gaussians tile each face (thin axis = face normal). Faces meet at REAL creases,
vertices are REAL corners. Mild per-Gaussian jitter mimics real 3DGS normal noise.
Used to test whether object-space anchoring stabilizes creases when they actually exist.
"""
import numpy as np
np.random.seed(3)

R, HZ = 1.0, 0.62          # hexagon radius, half-height (flat-ish prism)
CELL = 0.045               # tiling cell -> ~12k gaussians
THIN = 0.18                # thin-axis scale (disk thickness) relative to CELL
JIT_DEG = 4.0              # normal jitter (deg) ~ real 3DGS imperfection
L = np.array([0.3, 0.5, 0.8]); L = L / np.linalg.norm(L)

ang = np.arange(6) * np.pi / 3
htop = np.c_[R * np.cos(ang), R * np.sin(ang), np.full(6, HZ)]
hbot = np.c_[R * np.cos(ang), R * np.sin(ang), np.full(6, -HZ)]

P, U, V, N, C = [], [], [], [], []


def tile_face(o, udir, vdir):
    """tile a parallelogram face (origin o, edges udir,vdir) with flat gaussians."""
    ul = np.linalg.norm(udir); vl = np.linalg.norm(vdir)
    u = udir / ul; v = vdir / vl
    n = np.cross(u, v); n = n / np.linalg.norm(n)        # right-handed [u,v,n]
    nu, nv = max(int(ul / CELL), 1), max(int(vl / CELL), 1)
    shade = 0.32 + 0.55 * abs(n @ L)                     # bake simple lambert into albedo
    for iu in range(nu):
        for iv in range(nv):
            s, t = (iu + 0.5) / nu, (iv + 0.5) / nv
            p = o + s * udir + t * vdir
            P.append(p); U.append(u); V.append(v); N.append(n); C.append(shade)


# 6 side faces
for j in range(6):
    a, b = htop[j], htop[(j + 1) % 6]
    tile_face(a, b - a, hbot[j] - a)
# 2 hexagonal caps -> fan into 6 triangles, tile each (as degenerate-safe parallelograms)
for corners, z in [(htop, HZ), (hbot, -HZ)]:
    ctr = np.array([0, 0, z], float)
    for j in range(6):
        a, b = corners[j], corners[(j + 1) % 6]
        # tile triangle (ctr,a,b) via barycentric grid
        m = max(int(R / CELL), 1)
        for ia in range(m):
            for ib in range(m - ia):
                s, t = (ia + 0.33) / m, (ib + 0.33) / m
                p = ctr + s * (a - ctr) + t * (b - ctr)
                u = (a - ctr) / np.linalg.norm(a - ctr)
                n = np.array([0, 0, 1.0]) if z > 0 else np.array([0, 0, -1.0])
                v = np.cross(n, u)
                P.append(p); U.append(u); V.append(v); N.append(n)
                C.append(0.32 + 0.55 * abs(n @ L))

P = np.array(P); U = np.array(U); V = np.array(V); N = np.array(N); C = np.array(C)
n_g = len(P)

# per-gaussian jitter: rotate the frame by a small random rotation (noisy normals)
def small_rot(deg):
    ax = np.random.randn(3); ax /= np.linalg.norm(ax)
    th = np.radians(np.random.randn() * deg)
    K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
    return np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * (K @ K)


def mat2quat(R3):
    m = R3; tr = m[0, 0] + m[1, 1] + m[2, 2]
    if tr > 0:
        S = np.sqrt(tr + 1.0) * 2
        q = [0.25 * S, (m[2, 1] - m[1, 2]) / S, (m[0, 2] - m[2, 0]) / S, (m[1, 0] - m[0, 1]) / S]
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        S = np.sqrt(1 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        q = [(m[2, 1] - m[1, 2]) / S, 0.25 * S, (m[0, 1] + m[1, 0]) / S, (m[0, 2] + m[2, 0]) / S]
    elif m[1, 1] > m[2, 2]:
        S = np.sqrt(1 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        q = [(m[0, 2] - m[2, 0]) / S, (m[0, 1] + m[1, 0]) / S, 0.25 * S, (m[1, 2] + m[2, 1]) / S]
    else:
        S = np.sqrt(1 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
        q = [(m[1, 0] - m[0, 1]) / S, (m[0, 2] + m[2, 0]) / S, (m[1, 2] + m[2, 1]) / S, 0.25 * S]
    return np.array(q)


pos = np.zeros((n_g, 3)); scl = np.zeros((n_g, 3)); quat = np.zeros((n_g, 4))
for i in range(n_g):
    Rf = small_rot(JIT_DEG) @ np.column_stack([U[i], V[i], N[i]])
    pos[i] = P[i] + N[i] * np.random.randn() * 0.01            # tiny position jitter
    scl[i] = [CELL * 0.75 * (1 + 0.2 * np.random.randn()),
              CELL * 0.75 * (1 + 0.2 * np.random.randn()), CELL * THIN]
    quat[i] = mat2quat(Rf)

# write .splat (32B/gaussian: pos f32*3, scale f32*3, rgba u8*4, quat u8*4 [w,x,y,z])
arr = np.zeros((n_g, 32), np.uint8)
arr[:, 0:12] = pos.astype('<f4').view(np.uint8).reshape(n_g, 12)
arr[:, 12:24] = scl.astype('<f4').view(np.uint8).reshape(n_g, 12)
g = np.clip(C * 255, 0, 255).astype(np.uint8)
arr[:, 24] = g; arr[:, 25] = g; arr[:, 26] = g; arr[:, 27] = 235        # grey, opaque
arr[:, 28:32] = np.clip(np.round(quat * 128 + 128), 0, 255).astype(np.uint8)
arr.tofile("cad.splat")
print("wrote cad.splat with %d gaussians (hex prism, %d sides+2 caps)" % (n_g, 6))
