# -*- coding: utf-8 -*-
"""Generate a REAL 3DGS .ply of geometric primitives (cube + sphere + cylinder).

We place flat, surface-aligned Gaussians (2DGS-style disks: two large tangent
scales, one tiny scale along the surface normal) on each primitive's surface.
The result is a standard 3DGS .ply (same 17 fields as a trained model) so it
loads through render.load_ply / experiment.py unchanged — but unlike captured
scenes it has crisp creases (primitive edges) and corners, exactly what we want
to stress-test object-space feature-line extraction.
"""
import numpy as np
from plyfile import PlyData, PlyElement

SP = 0.014          # surface sample spacing
C0 = 0.28209479177387814


def frames_from_normals(N):
    """Orthonormal frames (N,3,3) with the 3rd column == surface normal."""
    N = N / (np.linalg.norm(N, axis=1, keepdims=True) + 1e-9)
    a = np.where((np.abs(N[:, 0]) < 0.9)[:, None],
                 np.array([1.0, 0, 0]), np.array([0, 1.0, 0]))
    t1 = np.cross(a, N); t1 /= (np.linalg.norm(t1, axis=1, keepdims=True) + 1e-9)
    t2 = np.cross(N, t1)
    return np.stack([t1, t2, N], axis=2)   # columns: t1, t2, normal


def quats_from_R(R):
    m = lambda i, j: R[:, i, j]
    tr = m(0, 0) + m(1, 1) + m(2, 2)
    sA = np.sqrt(np.maximum(tr + 1, 1e-12)) * 2
    qA = np.stack([0.25 * sA, (m(2, 1) - m(1, 2)) / sA, (m(0, 2) - m(2, 0)) / sA, (m(1, 0) - m(0, 1)) / sA], 1)
    sB = np.sqrt(np.maximum(1 + m(0, 0) - m(1, 1) - m(2, 2), 1e-12)) * 2
    qB = np.stack([(m(2, 1) - m(1, 2)) / sB, 0.25 * sB, (m(0, 1) + m(1, 0)) / sB, (m(0, 2) + m(2, 0)) / sB], 1)
    sC = np.sqrt(np.maximum(1 + m(1, 1) - m(0, 0) - m(2, 2), 1e-12)) * 2
    qC = np.stack([(m(0, 2) - m(2, 0)) / sC, (m(0, 1) + m(1, 0)) / sC, 0.25 * sC, (m(1, 2) + m(2, 1)) / sC], 1)
    sD = np.sqrt(np.maximum(1 + m(2, 2) - m(0, 0) - m(1, 1), 1e-12)) * 2
    qD = np.stack([(m(1, 0) - m(0, 1)) / sD, (m(0, 2) + m(2, 0)) / sD, (m(1, 2) + m(2, 1)) / sD, 0.25 * sD], 1)
    uA = tr > 0
    uB = (~uA) & (m(0, 0) >= m(1, 1)) & (m(0, 0) >= m(2, 2))
    uC = (~uA) & (~uB) & (m(1, 1) >= m(2, 2))
    q = np.where(uA[:, None], qA, np.where(uB[:, None], qB, np.where(uC[:, None], qC, qD)))
    return q / (np.linalg.norm(q, axis=1, keepdims=True) + 1e-12)


# ----------------------------- samplers -> (points, normals) -----------------
def cube(center, size, sp=SP):
    h = size / 2; n = max(2, int(size / sp)); lin = np.linspace(-h, h, n)
    g1, g2 = np.meshgrid(lin, lin); P, Nn = [], []
    for ax in range(3):
        other = [i for i in range(3) if i != ax]
        for sgn in (-1, 1):
            p = np.zeros((n * n, 3)); p[:, other[0]] = g1.ravel(); p[:, other[1]] = g2.ravel(); p[:, ax] = sgn * h
            nn = np.zeros((n * n, 3)); nn[:, ax] = sgn
            P.append(p); Nn.append(nn)
    return np.vstack(P) + center, np.vstack(Nn)


def sphere(center, r, count):
    i = np.arange(count); phi = np.arccos(1 - 2 * (i + 0.5) / count); g = np.pi * (1 + 5 ** 0.5)
    th = g * i
    N = np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)], 1)
    return N * r + center, N.copy()


def cylinder(center, r, height, sp=SP):
    nh = max(2, int(height / sp)); nc = max(8, int(2 * np.pi * r / sp))
    ys = np.linspace(-height / 2, height / 2, nh); th = np.linspace(0, 2 * np.pi, nc, endpoint=False)
    TH, Y = np.meshgrid(th, ys)
    P = [np.stack([np.cos(TH).ravel() * r, Y.ravel(), np.sin(TH).ravel() * r], 1)]
    N = [np.stack([np.cos(TH).ravel(), np.zeros(TH.size), np.sin(TH).ravel()], 1)]
    for sgn in (-1, 1):                                   # caps
        cp = []
        for rad in np.arange(sp, r, sp):
            na = max(6, int(2 * np.pi * rad / sp)); a = np.linspace(0, 2 * np.pi, na, endpoint=False)
            cp.append(np.stack([np.cos(a) * rad, np.full(na, sgn * height / 2), np.sin(a) * rad], 1))
        cp = np.vstack(cp); cn = np.zeros_like(cp); cn[:, 1] = sgn
        P.append(cp); N.append(cn)
    return np.vstack(P) + center, np.vstack(N)


# ----------------------------- build scene -----------------------------------
parts = [
    (cube(np.array([-1.75, 0.0, 0.0]), 1.45), (0.86, 0.30, 0.25)),     # red cube
    (sphere(np.array([0.05, 0.0, 0.0]), 0.82, 60000), (0.28, 0.45, 0.86)),  # blue sphere
    (cylinder(np.array([1.75, 0.0, 0.0]), 0.62, 1.5), (0.34, 0.70, 0.42)),  # green cylinder
]
P, N, COL = [], [], []
for (pts, nrm), col in parts:
    P.append(pts); N.append(nrm); COL.append(np.tile(col, (len(pts), 1)))
P = np.vstack(P); N = np.vstack(N); COL = np.vstack(COL)
M = len(P)

R = frames_from_normals(N)
quat = quats_from_R(R)                                    # (M,4) w,x,y,z
st = SP * 0.6                                             # tangent scale (disk radius)
tn = SP * 0.12                                            # thin scale (along normal)
scale_log = np.tile(np.log([st, st, tn]), (M, 1))        # thin axis = index 2 = normal
opacity_logit = np.full(M, 6.0)                           # ~0.9975
f_dc = (COL - 0.5) / C0

dt = [('x', 'f4'), ('y', 'f4'), ('z', 'f4'), ('nx', 'f4'), ('ny', 'f4'), ('nz', 'f4'),
      ('f_dc_0', 'f4'), ('f_dc_1', 'f4'), ('f_dc_2', 'f4'), ('opacity', 'f4'),
      ('scale_0', 'f4'), ('scale_1', 'f4'), ('scale_2', 'f4'),
      ('rot_0', 'f4'), ('rot_1', 'f4'), ('rot_2', 'f4'), ('rot_3', 'f4')]
arr = np.empty(M, dtype=dt)
arr['x'], arr['y'], arr['z'] = P[:, 0], P[:, 1], P[:, 2]
arr['nx'], arr['ny'], arr['nz'] = N[:, 0], N[:, 1], N[:, 2]
arr['f_dc_0'], arr['f_dc_1'], arr['f_dc_2'] = f_dc[:, 0], f_dc[:, 1], f_dc[:, 2]
arr['opacity'] = opacity_logit
arr['scale_0'], arr['scale_1'], arr['scale_2'] = scale_log[:, 0], scale_log[:, 1], scale_log[:, 2]
arr['rot_0'], arr['rot_1'], arr['rot_2'], arr['rot_3'] = quat[:, 0], quat[:, 1], quat[:, 2], quat[:, 3]
PlyData([PlyElement.describe(arr, 'vertex')]).write('primitives.ply')
print("wrote primitives.ply with %d gaussians" % M)

# sanity: reconstruct normal from quat (as load_ply does) and compare
from render import quats_to_R
Rr = quats_to_R(quat); n_rec = Rr[np.arange(M), :, 2]
agree = np.abs(np.einsum('ij,ij->i', n_rec, N)).mean()
print("normal round-trip agreement (should be ~1.0): %.4f" % agree)
