"""Round 3: full AUC table + ORACLE-SUPERVISED ceiling (analysis only) + combo sweeps.
Loads the cached feature npz written by explore_geom2.py.
"""
import os
import sys
import time
import numpy as np

sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tune_lib import Harness, structure_tensor, nms_along_e1
from explore_geom import auc, sweep, FS, SCRATCH

Z = np.load(os.path.join(SCRATCH, "geom_all.npz"))
META = {"sel", "near", "visa", "ncnt", "vcnt"}
NAMES = [k for k in Z.files if k not in META]
near, visa = Z["near"], Z["visa"]
sel = Z["sel"]


def zr(x):
    """rank -> gaussian-ish z score"""
    o = np.argsort(np.argsort(x))
    return (o + 0.5) / len(x)


def main():
    print(f"pool={len(sel)} vis={visa.sum()} near={near.sum()} nfeat={len(NAMES)}")
    rows = [(n, auc(Z[n], near), auc(Z[n][visa], near[visa])) for n in NAMES]
    rows.sort(key=lambda r: -max(r[2], 1 - r[2]))
    print("\n=== FULL single-feature AUC table ===")
    for n, a, av in rows:
        print(f"{n:22s} all={a:6.3f} vis={av:6.3f}")

    # ---- TPR at f=0.3 for the best few (recall proxy) ----
    print("\n=== retained-positive fraction (TPR) at f, over ALL seeds ===")
    for n, a, av in rows[:6]:
        s = Z[n] if av >= 0.5 else -Z[n]
        o = np.argsort(-s)
        line = []
        for f in [0.5, 0.4, 0.3, 0.2]:
            k = o[:int(f * len(s))]
            line.append(f"{f:.1f}:TPR={near[k].sum()/near.sum():.3f}")
        print(f"{n:22s} " + " ".join(line))

    # ---- ORACLE-SUPERVISED ceiling for the family (ANALYSIS ONLY) ----
    print("\n=== supervised ceiling of the geom family (oracle-fit, NOT a usable score) ===")
    M = np.stack([zr(Z[n]) for n in NAMES], 1)
    Mv, yv = M[visa], near[visa]
    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.ensemble import HistGradientBoostingClassifier
        from sklearn.model_selection import cross_val_predict
        lr = LogisticRegression(max_iter=2000, C=1.0)
        pl = cross_val_predict(lr, Mv, yv, cv=5, method="predict_proba")[:, 1]
        print(f"  logreg  5-fold CV AUC = {auc(pl, yv):.3f}")
        gb = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.1)
        pg = cross_val_predict(gb, Mv, yv, cv=5, method="predict_proba")[:, 1]
        print(f"  GBDT    5-fold CV AUC = {auc(pg, yv):.3f}")
        # in-sample full-fit score for a Pareto upper bound
        gb.fit(Mv, yv)
        full = gb.predict_proba(M)[:, 1]
        np.save(os.path.join(SCRATCH, "gb_score.npy"), full)
        imp = np.argsort(-np.abs(lr.fit(Mv, yv).coef_[0]))[:15]
        print("  logreg top coefs:", ", ".join(f"{NAMES[i]}({lr.coef_[0][i]:+.2f})" for i in imp))
    except Exception as e:
        print("  sklearn unavailable:", e)

    # ---- Pareto of the supervised score (upper bound for the family) ----
    h = Harness("chair")
    st = structure_tensor(h.X, h.N, 8)
    P = h.X[sel]
    if os.path.exists(os.path.join(SCRATCH, "gb_score.npy")):
        s = np.load(os.path.join(SCRATCH, "gb_score.npy"))
        res = sweep(h, P, s)
        print("\nGBDT(in-sample, oracle-fit) Pareto: " +
              " ".join(f"{f:.1f}:{p:.3f}/{r:.3f}" for f, p, r, _ in res))

    # ---- unsupervised hand combos ----
    print("\n=== hand combos (mesh-free) ===")
    combos = {
        "opa*dens": zr(Z["nb_opa_mean"]) * zr(Z["dens"]),
        "opa*seedd24": zr(Z["nb_opa_mean"]) * zr(Z["seed_dens_k24"]),
        "opa*posthick": zr(Z["nb_opa_mean"]) * zr(Z["pos_thick"]),
        "opa*dens*posthick": zr(Z["nb_opa_mean"]) * zr(Z["dens"]) * zr(Z["pos_thick"]),
        "opa*scr": zr(Z["nb_opa_mean"]) * zr(Z["s_crease"]),
        "opa+dens+posthick": zr(Z["nb_opa_mean"]) + zr(Z["dens"]) + zr(Z["pos_thick"]),
        "opa*dens*scr24": zr(Z["nb_opa_mean"]) * zr(Z["dens"]) * zr(Z["s_crease_k24"]),
        "opa*posthick*scr24": (zr(Z["nb_opa_mean"]) * zr(Z["pos_thick"])
                               * zr(Z["s_crease_k24"])),
        "4way": (zr(Z["nb_opa_mean"]) * zr(Z["dens"]) * zr(Z["pos_thick"])
                 * zr(Z["s_crease_k24"])),
    }
    for n, s in combos.items():
        av = auc(s[visa], near[visa])
        res = sweep(h, P, s)
        print(f"{n:22s} AUCvis={av:.3f}  " +
              " ".join(f"{f:.1f}:{p:.3f}/{r:.3f}" for f, p, r, _ in res))


if __name__ == "__main__":
    main()
