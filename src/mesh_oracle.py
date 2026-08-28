"""tier1/src/mesh_oracle.py — EVAL ONLY. The ONLY module allowed to touch the GT mesh.
Method modules (render/lines_image/seeds/dt_field/visibility) must NEVER import this.

Provides GT crease points (dihedral >= angle_deg), a GT-mesh depth rasterizer
(centroid z-buffer, reused from bcr/bcr_v1.py), and mesh-depth-culled 2D crease
projections for precision/recall scoring.
"""
import os
import numpy as np
import torch
import trimesh

MESH_DIR = os.path.expanduser("~/3dgs_line/bcr/meshes/NeRF_Mesh")


class MeshOracle:
    def __init__(self, scene, angle_deg=30.0, ds=0.0015, device="cuda"):
        self.device = device
        m = trimesh.load(f"{MESH_DIR}/{scene}_new.obj", process=True)
        if isinstance(m, trimesh.Scene):
            m = trimesh.util.concatenate([g for g in m.geometry.values()])
        self.V = np.asarray(m.vertices, np.float64)
        self.F = np.asarray(m.faces)
        sel = m.face_adjacency_edges[m.face_adjacency_angles >= np.deg2rad(angle_deg)]
        self.crease_pts = self._sample_edges(sel, ds)
        self._Vt = torch.tensor(self.V, dtype=torch.float32, device=device)
        self._Ft = torch.tensor(self.F, dtype=torch.long, device=device)
        self._depth_cache = {}

    def _sample_edges(self, vidx_pairs, ds):
        a = self.V[vidx_pairs[:, 0]]
        b = self.V[vidx_pairs[:, 1]]
        seg = b - a
        L = np.linalg.norm(seg, axis=1)
        pts = []
        for i in range(len(a)):
            n = max(2, int(L[i] / ds) + 1)
            ts = np.linspace(0, 1, n)
            pts.append(a[i][None] + ts[:, None] * seg[i][None])
        return np.concatenate(pts, 0) if pts else np.zeros((0, 3))

    def render_depth(self, cam, view_key=None, max_elems=None):
        """GT mesh depth via EXACT barycentric triangle rasterization (z-min buffer).

        NOTE: bcr/bcr_v1.py used a centroid splat, which is only valid when every
        triangle is sub-pixel. That holds for lego (2.03M faces) but NOT for chair
        (258k faces): the centroid splat covered only IoU 0.37 of the true silhouette
        and left 64% of the object interior as holes, which corrupts both the GT
        footprint and the crease occlusion cull. This does real coverage instead.
        Depth is perspective-correct (barycentric interpolation of 1/z).
        """
        # Chunk size only -- scatter_reduce "amin" is order-independent, so the depth
        # buffer is bit-identical for any chunking.  GPU 1 is shared (~4 GB free) and the
        # 2.03M-face lego mesh OOM'd at the 8M default, so this is env-overridable and
        # halves itself on OutOfMemoryError instead of aborting the run.
        if max_elems is None:
            max_elems = int(os.environ.get("MESH_ORACLE_MAX_ELEMS", 8_000_000))
        if view_key is not None and view_key in self._depth_cache:
            return self._depth_cache[view_key]
        H, Wd = cam.H, cam.W
        dev = self.device
        w2c = torch.tensor(cam.w2c, dtype=torch.float32, device=dev)
        K = torch.tensor(cam.K, dtype=torch.float32, device=dev)
        campts = self._Vt @ w2c[:3, :3].T + w2c[:3, 3]
        z = campts[:, 2]
        uv = campts @ K.T
        px = uv[:, 0] / uv[:, 2].clamp(min=1e-6)
        py = uv[:, 1] / uv[:, 2].clamp(min=1e-6)

        tri = self._Ft
        zc = z[tri]                                        # [F,3]
        keep = (zc > 1e-6).all(1)                          # fully in front of camera
        tri, zc = tri[keep], zc[keep]
        X = px[tri]                                        # [F,3]
        Y = py[tri]
        x0 = torch.floor(X.min(1).values)
        x1 = torch.ceil(X.max(1).values)
        y0 = torch.floor(Y.min(1).values)
        y1 = torch.ceil(Y.max(1).values)
        onscreen = (x1 >= 0) & (x0 <= Wd - 1) & (y1 >= 0) & (y0 <= H - 1)
        tri, zc, X, Y = tri[onscreen], zc[onscreen], X[onscreen], Y[onscreen]
        x0, y0 = x0[onscreen], y0[onscreen]
        span = torch.maximum(x1[onscreen] - x0, y1[onscreen] - y0)

        dbuf = torch.full((H * Wd,), float("inf"), device=dev)
        if len(tri) == 0:
            depth = dbuf.view(H, Wd).clone()
            depth[~torch.isfinite(depth)] = 1e9
            if view_key is not None:
                self._depth_cache[view_key] = depth
            return depth

        # bucket triangles by screen-space bbox span -> shared sample grid per bucket
        nb = torch.clamp(2 ** torch.ceil(torch.log2(span.clamp(min=1.0))).long(), 1, 1024)
        for n in torch.unique(nb).tolist():
            sel = nb == n
            g = n + 2                                       # grid side (pad 1px)
            off = torch.arange(g, device=dev, dtype=torch.float32)
            gx, gy = torch.meshgrid(off, off, indexing="xy")
            gx, gy = gx.reshape(-1), gy.reshape(-1)         # [P]
            idx_all = torch.nonzero(sel, as_tuple=True)[0]
            chunk = max(1, int(max_elems // (g * g)))
            s = 0
            while s < len(idx_all):
                ii = idx_all[s:s + chunk]
                try:
                    sx = x0[ii][:, None] + gx[None]         # [m,P] pixel x (integer)
                    sy = y0[ii][:, None] + gy[None]
                    Xi, Yi, Zi = X[ii], Y[ii], zc[ii]       # [m,3]
                    ax, ay = Xi[:, 0:1], Yi[:, 0:1]
                    bx, by = Xi[:, 1:2], Yi[:, 1:2]
                    cx_, cy_ = Xi[:, 2:3], Yi[:, 2:3]
                    area = (bx - ax) * (cy_ - ay) - (by - ay) * (cx_ - ax)
                    good = area.abs() > 1e-12
                    area = torch.where(good, area, torch.ones_like(area))
                    l0 = ((bx - sx) * (cy_ - sy) - (by - sy) * (cx_ - sx)) / area
                    l1 = ((cx_ - sx) * (ay - sy) - (cy_ - sy) * (ax - sx)) / area
                    l2 = 1.0 - l0 - l1
                    inside = (l0 >= 0) & (l1 >= 0) & (l2 >= 0) & good & \
                             (sx >= 0) & (sx <= Wd - 1) & (sy >= 0) & (sy <= H - 1)
                    if inside.any():
                        invz = l0 / Zi[:, 0:1] + l1 / Zi[:, 1:2] + l2 / Zi[:, 2:3]
                        zpix = 1.0 / invz.clamp(min=1e-9)   # perspective-correct depth
                        m = inside & torch.isfinite(zpix)
                        flat = (sy.long() * Wd + sx.long())[m]
                        dbuf.scatter_reduce_(0, flat, zpix[m], reduce="amin",
                                             include_self=True)
                except torch.cuda.OutOfMemoryError:
                    if chunk <= 1:
                        raise
                    torch.cuda.empty_cache()
                    chunk = max(1, chunk // 2)
                    continue
                s += chunk

        depth = dbuf.view(H, Wd).clone()
        depth[~torch.isfinite(depth)] = 1e9
        if view_key is not None:
            self._depth_cache[view_key] = depth
        return depth

    def visible_crease_uv(self, cam, eps_vis=0.015, view_key=None):
        """Project GT crease points, cull with GT mesh depth (3x3 min |dz| window).
        Returns uv[Mvis,2] float pixel coords of visible crease points."""
        H, Wd = cam.H, cam.W
        depth = self.render_depth(cam, view_key=view_key).detach().cpu().numpy()
        q = self.crease_pts
        campts = (cam.w2c[:3, :3] @ q.T).T + cam.w2c[:3, 3]
        z = campts[:, 2]
        uv = (cam.K @ campts.T).T
        uv = uv[:, :2] / np.clip(uv[:, 2:3], 1e-9, None)
        u = np.round(uv[:, 0]).astype(np.int64)
        v = np.round(uv[:, 1]).astype(np.int64)
        inb = (z > 0) & (u >= 0) & (u < Wd) & (v >= 0) & (v < H)
        idx = np.where(inb)[0]
        best = np.full(len(idx), 1e9)
        for du in (-1, 0, 1):
            for dv in (-1, 0, 1):
                uu = np.clip(u[idx] + du, 0, Wd - 1)
                vv = np.clip(v[idx] + dv, 0, H - 1)
                best = np.minimum(best, np.abs(z[idx] - depth[vv, uu]))
        ok = idx[best < eps_vis]
        return uv[ok]
