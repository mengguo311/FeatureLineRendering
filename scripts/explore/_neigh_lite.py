"""EVAL-SIDE CPU-only mirror of tune_lib.Harness.evaluate (identical logic), backed by a
one-off cache of the gaussian depth buffers so sweeps do not contend for the GPU."""
import os
import sys
import numpy as np
import cv2
import torch

sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
from src import common, render, visibility

SCRATCH = "/tmp/claude-1026/-home-u00134-3dgs-line/4ee6144a-2815-4286-bec9-0a63623a57f6/scratchpad"
CACHE = os.path.expanduser("~/3dgs_line/tier1/cache")
H = Wd = 800


class LiteHarness:
    def __init__(self, scene="chair", views=(0, 25)):
        self.scene, self.views = scene, list(views)
        self.cams, self.rgb_paths = common.load_cameras(scene)
        self.g = common.load_gaussians(scene)
        self.keep = render.defloat_mask(self.g["mu"], self.g["opacity"])
        self.X = self.g["mu"][self.keep]
        self.N = self.g["normal"][self.keep]
        self.opa = self.g["opacity"][self.keep]
        self.scale = self.g["scale"][self.keep]
        dp = os.path.join(SCRATCH, f"depth_{scene}.npz")
        if os.path.exists(dp):
            z = np.load(dp)
            self.gbufs = {v: {"depth": torch.from_numpy(z[f"d{v}"].astype(np.float32))}
                          for v in self.views}
        else:
            dev = "cuda" if torch.cuda.is_available() else "cpu"
            try:
                gb = {v: render.render_gbuffer(self.g, self.keep, self.cams[v], device=dev)
                      for v in self.views}
            except torch.cuda.OutOfMemoryError:
                torch.cuda.empty_cache()
                gb = {v: render.render_gbuffer(self.g, self.keep, self.cams[v], device="cpu")
                      for v in self.views}
            np.savez(dp, **{f"d{v}": gb[v]["depth"].cpu().numpy() for v in self.views})
            self.gbufs = {v: {"depth": gb[v]["depth"].cpu()} for v in self.views}
        z = np.load(os.path.join(CACHE, f"oracle_{scene}_a30_v0-25.npz"))
        self.crease = {v: (z[f"cu{v}"], z[f"cv{v}"], z[f"cdt{v}"]) for v in self.views}

    def evaluate(self, pos, extra_mask=None, tau_p=2.5, tau_r=3.0, per_view=False):
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
