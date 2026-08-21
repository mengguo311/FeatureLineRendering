"""Round 8: fast exact gate evaluator + subset search maximizing
   precision subject to recall >= 0.70.  EVAL-SIDE (oracle used for scoring only)."""
import os
import sys
import time
import itertools
import numpy as np
import cv2

sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tune_lib import Harness, structure_tensor, nms_along_e1
from src import visibility
from explore_geom import auc, sweep, SCRATCH

Z1 = np.load(os.path.join(SCRATCH, "geom_all.npz"))
Z2 = np.load(os.path.join(SCRATCH, "geom_denoise.npz"))
META = {"sel", "near", "visa", "ncnt", "vcnt"}
near, visa, sel = Z1["near"], Z1["visa"], Z1["sel"]
F = {k: Z1[k] for k in Z1.files if k not in META}
F.update({k: Z2[k] for k in Z2.files})
H = Wd = 800


def zr(x):
    return (np.argsort(np.argsort(x)) + 0.5) / len(x)


class Fast:
    """Exact reimplementation of Harness.evaluate with visibility precomputed."""

    def __init__(self, h, pos):
        self.h, self.pv = h, []
        for v in h.views:
            vis, uv, _ = visibility.visible_mask(pos, h.cams[v], h.gbufs[v]["depth"])
            inb = (uv[:, 0] >= 0) & (uv[:, 0] < Wd) & (uv[:, 1] >= 0) & (uv[:, 1] < H)
            ok = vis & inb
            su = np.round(uv[:, 0]).astype(int)
            sv = np.round(uv[:, 1]).astype(int)
            cu, cv_, cdt = h.crease[v]
            self.pv.append((ok, su, sv, cu, cv_, cdt))

    def __call__(self, keep):
        ps, rs = [], []
        for ok, su, sv, cu, cv_, cdt in self.pv:
            m = ok & keep
            u, w = su[m], sv[m]
            ps.append(float((cdt[w, u] <= 2.5).mean()) if len(u) else 0.0)
            sm = np.zeros((H, Wd), np.uint8)
            sm[w, u] = 1
            sdt = cv2.distanceTransform(1 - sm, cv2.DIST_L2, 5)
            rs.append(float((sdt[cv_, cu] <= 3.0).mean()))
        return float(np.mean(ps)), float(np.mean(rs))


def gate_curve(fast, score, fs):
    o = np.argsort(-score, kind="mergesort")
    out = []
    for f in fs:
        keep = np.zeros(len(score), bool)
        keep[o[:int(round(f * len(score)))]] = True
        p, r = fast(keep)
        out.append((f, p, r))
    return out


def main():
    t0 = time.time()
    h = Harness("chair")
    st = structure_tensor(h.X, h.N, 8)
    P = h.X[sel]
    fast = Fast(h, P)

    # --- verify the fast evaluator matches the harness exactly ---
    rng = np.random.default_rng(1)
    for _ in range(2):
        k = rng.random(len(P)) < 0.4
        a = h.evaluate(P, extra_mask=k)[:2]
        b = fast(k)
        assert abs(a[0] - b[0]) < 1e-9 and abs(a[1] - b[1]) < 1e-9, (a, b)
    print(f"fast evaluator verified vs harness ({time.time()-t0:.1f}s)")

    POOL = ["seed_dens_k24", "nb_opa_mean", "p90ang_pca_k20", "dens", "curv_k20",
            "nb_flat_mean", "opa", "pos_thick", "dih_pca_p32c24", "edge_thick"
            if "edge_thick" in F else "s_crease", "rel_scale_min", "seed_dens_k12"]
    POOL = [p for p in POOL if p in F]
    SG = {n: (1.0 if auc(F[n][visa], near[visa]) >= 0.5 else -1.0) for n in POOL}
    RK = {n: zr(SG[n] * F[n]) for n in POOL}
    FS = [0.70, 0.65, 0.60, 0.55, 0.50, 0.45]

    best = []
    t = time.time()
    for r in range(1, 6):
        for sub in itertools.combinations(POOL, r):
            s = sum(RK[n] for n in sub)
            cur = gate_curve(fast, s, FS)
            ok = [(p, f, rr) for f, p, rr in cur if rr >= 0.70]
            if ok:
                p, f, rr = max(ok)
                best.append((p, rr, f, sub))
        print(f"  size {r} done, {time.time()-t:.0f}s, best so far "
              f"{max(best)[0]:.3f}" if best else "")
        if time.time() - t > 180:
            print("  (time budget hit)")
            break
    best.sort(reverse=True)
    print("\n=== top subsets by precision @ recall>=0.70 ===")
    for p, rr, f, sub in best[:15]:
        s = sum(RK[n] for n in sub)
        print(f"  prec={p:.3f} rec={rr:.3f} f={f:.2f} AUC={auc(s[visa],near[visa]):.3f} "
              f"{'+'.join(sub)}")
    np.save(os.path.join(SCRATCH, "best_subset.npy"),
            np.array(best[0][3], dtype=object), allow_pickle=True)
    print(f"total {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
