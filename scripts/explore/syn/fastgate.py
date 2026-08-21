"""Fast EXACT-ish mirror of Harness.evaluate for mask-only sweeps.

Precision: identical (cdt lookup at the seed pixel, same cdt array).
Recall: for each GT crease pixel, precompute the set of SEED PIXELS within tau_r;
recall = frac of crease pixels with >=1 kept seed in that set.  This differs from
the harness only in that the harness uses cv2's approximate DIST_L2 mask-5 transform
on the seed mask; we use exact euclidean.  Validated against h.evaluate below.
"""
import numpy as np
from scipy.spatial import cKDTree
import sys, os
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
from src import visibility


class FastGate:
    def __init__(self, h, sel, tau_p=2.5, tau_r=3.0):
        self.views = h.views
        P = h.X[sel]
        self.M = len(sel)
        self.per = {}
        for v in h.views:
            vis, uv, _ = visibility.visible_mask(P, h.cams[v], h.gbufs[v]["depth"])
            u = np.round(uv[:, 0]).astype(int)
            w = np.round(uv[:, 1]).astype(int)
            inb = (u >= 0) & (u < 800) & (w >= 0) & (w < 800)
            vis = vis & inb
            u = np.clip(u, 0, 799); w = np.clip(w, 0, 799)
            cu, cvv, cdt = h.crease[v]
            hit = np.zeros(self.M, bool)
            hit[vis] = cdt[w[vis], u[vis]] <= tau_p
            # crease-pixel -> seeds within tau_r
            idx = np.where(vis)[0]
            tree = cKDTree(np.stack([u[idx], w[idx]], 1).astype(np.float64))
            lists = tree.query_ball_point(np.stack([cu, cvv], 1).astype(np.float64),
                                          r=tau_r + 1e-9)
            rows, cols = [], []
            for ci, L in enumerate(lists):
                for j in L:
                    rows.append(ci); cols.append(idx[j])
            self.per[v] = dict(vis=vis, hit=hit, ncre=len(cu),
                               rows=np.asarray(rows, np.int64),
                               cols=np.asarray(cols, np.int64))

    def __call__(self, keep, per_view=False):
        ps, rs, ns = [], [], []
        for v in self.views:
            d = self.per[v]
            k = d["vis"] & keep
            n = int(k.sum())
            ps.append(float(d["hit"][k].sum()) / max(n, 1))
            cov = np.zeros(d["ncre"], bool)
            m = k[d["cols"]]
            cov[d["rows"][m]] = True
            rs.append(float(cov.mean()))
            ns.append(n)
        if per_view:
            return ps, rs, ns
        return float(np.mean(ps)), float(np.mean(rs)), int(np.mean(ns))
