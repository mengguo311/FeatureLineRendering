"""EVAL-ONLY tuning harness for M1a gate exploration (imports mesh_oracle; NOT a method module).

Caches the expensive parts (gaussian G-buffers, GT crease distance transforms) so that
sweeps over seed parameters are cheap. evaluate() implements exactly the verify_m1a gate:
  precision = frac of visible projected seeds within 2.5px of a visible GT crease pixel
  recall    = frac of visible GT crease pixels within 3.0px of a projected seed
"""
import os
import sys
import numpy as np
import cv2
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
from src import common, render, visibility
from src.mesh_oracle import MeshOracle

CACHE = os.path.expanduser("~/3dgs_line/tier1/cache")
H = Wd = 800


class Harness:
    def __init__(self, scene, views=(0, 25), angle_deg=30.0, defloat=True):
        self.scene, self.views = scene, list(views)
        self.cams, self.rgb_paths = common.load_cameras(scene)
        self.g = common.load_gaussians(scene)
        self.keep = (render.defloat_mask(self.g["mu"], self.g["opacity"]) if defloat
                     else self.g["opacity"] > 0.1)
        self.X = self.g["mu"][self.keep]
        self.N = self.g["normal"][self.keep]
        self.opa = self.g["opacity"][self.keep]
        self.scale = self.g["scale"][self.keep]
        self.gbufs = {v: render.render_gbuffer(self.g, self.keep, self.cams[v])
                      for v in self.views}
        self.depth_np = {v: self.gbufs[v]["depth"].cpu().numpy() for v in self.views}
        self._load_oracle(angle_deg)

    def _load_oracle(self, angle_deg):
        os.makedirs(CACHE, exist_ok=True)
        tag = f"{self.scene}_a{int(angle_deg)}_v{'-'.join(map(str,self.views))}"
        p = os.path.join(CACHE, f"oracle_{tag}.npz")
        if os.path.exists(p):
            z = np.load(p)
            self.crease = {v: (z[f"cu{v}"], z[f"cv{v}"], z[f"cdt{v}"]) for v in self.views}
            return
        o = MeshOracle(self.scene, angle_deg=angle_deg)
        out, self.crease = {}, {}
        for v in self.views:
            uvq = o.visible_crease_uv(self.cams[v], view_key=v)
            cu = np.clip(np.round(uvq[:, 0]).astype(int), 0, Wd - 1)
            cv_ = np.clip(np.round(uvq[:, 1]).astype(int), 0, H - 1)
            m = np.zeros((H, Wd), bool)
            m[cv_, cu] = True
            # dedupe to unique crease PIXELS (recall over pixels, not over duplicated samples)
            cv_u, cu_u = np.nonzero(m)
            cdt = cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5)
            self.crease[v] = (cu_u, cv_u, cdt)
            out[f"cu{v}"], out[f"cv{v}"], out[f"cdt{v}"] = cu_u, cv_u, cdt
        np.savez(p, **out)

    def evaluate(self, pos, extra_mask=None, tau_p=2.5, tau_r=3.0, per_view=False):
        """pos[M,3] seed positions. extra_mask[M] bool = additional method-side keep."""
        ps, rs, ns = [], [], []
        for v in self.views:
            vis, uv, _ = visibility.visible_mask(pos, self.cams[v], self.gbufs[v]["depth"])
            if extra_mask is not None:
                vis = vis & extra_mask
            suv = uv[vis]
            inb = (suv[:, 0] >= 0) & (suv[:, 0] < Wd) & (suv[:, 1] >= 0) & (suv[:, 1] < H)
            suv = suv[inb]
            su = np.round(suv[:, 0]).astype(int)
            sv = np.round(suv[:, 1]).astype(int)
            cu, cv_, cdt = self.crease[v]
            ps.append(float((cdt[sv, su] <= tau_p).mean()) if len(suv) else 0.0)
            sm = np.zeros((H, Wd), bool)
            sm[sv, su] = True
            sdt = cv2.distanceTransform((~sm).astype(np.uint8), cv2.DIST_L2, 5)
            rs.append(float((sdt[cv_, cu] <= tau_r).mean()))
            ns.append(int(len(suv)))
        if per_view:
            return ps, rs, ns
        return float(np.mean(ps)), float(np.mean(rs)), int(np.mean(ns))


def structure_tensor(X, n, k, knn=None, tree=None):
    """C_N eigendecomposition. Returns dict(s_crease, s_corner, e1, e3, knn, l1,l2,l3)."""
    if knn is None:
        tree = tree or cKDTree(X)
        _, knn = tree.query(X, k=k + 1)
        knn = knn[:, 1:]
    nj = n[knn]
    sign = np.sign(np.einsum("nkc,nc->nk", nj, n))
    sign[sign == 0] = 1.0
    nj = nj * sign[..., None]
    nbar = nj.mean(1, keepdims=True)
    dnj = nj - nbar
    C = np.einsum("nkc,nkd->ncd", dnj, dnj) / knn.shape[1]
    w, V = np.linalg.eigh(C)
    return {"s_crease": w[:, 2] - w[:, 1], "s_corner": w[:, 1] - w[:, 0],
            "e1": V[:, :, 2], "e3": V[:, :, 0], "knn": knn,
            "l1": w[:, 2], "l2": w[:, 1], "l3": w[:, 0]}


def nms_along_e1(X, cand, s, e1, knn, cos_thr=0.7):
    is_c = np.zeros(len(X), bool)
    is_c[cand] = True
    nb = knn[cand]
    d = X[nb] - X[cand][:, None]
    dn = np.linalg.norm(d, axis=2) + 1e-12
    along = np.abs(np.einsum("mkc,mc->mk", d, e1[cand])) / dn > cos_thr
    rival = is_c[nb] & along & (s[nb] > s[cand][:, None])
    return cand[~rival.any(1)]
