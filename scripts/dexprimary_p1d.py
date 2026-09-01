"""PHASE 1d — MESH-FREE SUPERVISION falsification (the path-B decider).

*** EVAL / ANALYSIS SCRIPT. ***
The Phase 1c GO fit its linear probe on MESH GT labels — an EVAL oracle. This phase asks the
one question that decides whether FAM-C is a deployable METHOD-PATH component: does the
DINOv2 discrimination survive when the probe is trained on MESH-FREE PSEUDO-LABELS only,
with the mesh reserved strictly for the held-out AUC?

SUPERVISION HYGIENE (the invariant this script exists to respect):
  - pseudo-labels come from src.edge_semantics.{pseudo_labels_votes,pseudo_labels_cluster},
    a METHOD-PATH module that sees only FAM-A/B features and DINO descriptors (AST-checked);
  - the mesh labels y enter ONLY at auc(y_eval, score) time, on the held-out x-halfspace;
  - probe training uses the FIT halfspace only, identical xsplit protocol to Phase 1c, so
    the numbers are directly comparable to the mesh-supervised 0.8401 (chair) / 0.9044 (lego).

FROZEN GATES (chair primary, per-point xsplit AUC vs held-out mesh GT):
  GO >= 0.78 AND clearly beats the FAM-A photometric baseline (~0.71)
  NO-GO <= 0.72        GRAY 0.72-0.78 (lean converge)

SECONDARY (demoted, NOT a gate): cross-scene transfer of the MESH-supervised probe
(chair->lego, lego->chair) — a category-transfer datapoint, not a path-B kill.
"""
import os
import sys
import json

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
OUT = os.path.join(TIER1, "out")

from src import edge_semantics as ES
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score

MESH_AUC_P1C = {"chair": 0.8401, "lego": 0.9044}   # Phase 1c mesh-supervised references
FAMA_AUC_P1C = {"chair": 0.7112, "lego": 0.6600}


def load(scene):
    z = np.load(os.path.join(OUT, f"dexp1d_feats_{scene}.npz"))
    return {k: z[k] for k in z.files}


def fit_eval(X, y_train, train_mask, y_gt, eval_mask, seed=0, max_fit=60000):
    """Probe on (X, y_train) over train_mask; AUC vs MESH GT y_gt over eval_mask."""
    ok_tr = train_mask & (y_train >= 0) & np.isfinite(X).all(1)
    ok_ev = eval_mask & (y_gt >= 0) & np.isfinite(X).all(1)
    if ok_tr.sum() < 500 or ok_ev.sum() < 500:
        return float("nan"), None, None
    sc = StandardScaler().fit(X[ok_tr])
    clf = LogisticRegression(max_iter=2000, C=1.0)
    sub = np.where(ok_tr)[0]
    if len(sub) > max_fit:
        sub = np.random.default_rng(seed).choice(sub, max_fit, replace=False)
    clf.fit(sc.transform(X[sub]), y_train[sub])
    s = np.full(len(X), np.nan)
    allok = np.isfinite(X).all(1)
    s[allok] = clf.predict_proba(sc.transform(X[allok]))[:, 1]
    a = roc_auc_score(y_gt[ok_ev], s[ok_ev])
    return float(a), s, (sc, clf)


def guarded_chain_auc(score, chain, y_gt, eval_mask):
    """Chain-AUC over chains fully inside the held-out halfspace (leakage-guarded)."""
    nch = chain.max() + 1 if chain.max() >= 0 else 0
    if nch == 0:
        return float("nan"), 0
    order = np.argsort(chain)
    b = np.searchsorted(chain[order], np.arange(nch))
    b = np.append(b, len(order))
    ys, ss = [], []
    for c in range(nch):
        idx = order[b[c]:b[c + 1]]
        if len(idx) < 10 or not eval_mask[idx].all():
            continue
        lm = y_gt[idx] >= 0
        if lm.sum() < 5:
            continue
        fr = (y_gt[idx][lm] == 1).mean()
        v = score[idx]
        v = v[np.isfinite(v)]
        if not len(v):
            continue
        ys.append(1 if fr >= 0.5 else 0)
        ss.append(np.median(v))
    ys, ss = np.array(ys), np.array(ss)
    if len(np.unique(ys)) < 2:
        return float("nan"), len(ys)
    return float(roc_auc_score(ys, ss)), len(ys)


def main():
    res = {}
    data = {sc: load(sc) for sc in ("chair", "lego")}
    for scene in ("chair", "lego"):
        d = data[scene]
        FA, FB, DD = d["FA"], d["FB"], d["DD"].astype(np.float32)
        y_gt, ev = d["y"], d["x_eval_half"].astype(bool)
        fit = ~ev
        print(f"\n================ {scene.upper()} ================")
        print(f"n={len(y_gt)}  GT crease {(y_gt==1).sum()} / texture {(y_gt==0).sum()}  "
              f"fit-half {fit.sum()} / eval-half {ev.sum()}")

        # -------- mesh-free pseudo-label sources (METHOD path builds them) --------
        pl_v, V = ES.pseudo_labels_votes(FA, FB)
        pl_c, cl, cmean = ES.pseudo_labels_cluster(DD, FA, FB)
        r = {"n": int(len(y_gt))}

        # how noisy are the pseudo-labels themselves? (EVAL diagnostic, not supervision)
        for nm, pl in (("PL-VOTE", pl_v), ("PL-CLUSTER", pl_c)):
            m = (pl >= 0) & (y_gt >= 0)
            agree = float((pl[m] == y_gt[m]).mean())
            posrate = float((pl[pl >= 0] == 1).mean())
            print(f"  {nm}: labeled {int((pl>=0).sum())}  pos-rate {posrate:.3f}  "
                  f"agreement with mesh GT {agree:.3f}")
            r[f"{nm}_agreement"] = agree
            r[f"{nm}_posrate"] = posrate

        # -------- probes: pseudo-label-trained, mesh-GT-evaluated (xsplit) --------
        rows = {}
        for nm, pl in (("PL-VOTE", pl_v), ("PL-CLUSTER", pl_c)):
            aC, sC, _ = fit_eval(DD, pl, fit, y_gt, ev)
            aA, _, _ = fit_eval(FA, pl, fit, y_gt, ev)
            gch, ngc = guarded_chain_auc(sC, d["chain"], y_gt, ev)
            rows[nm] = {"FAM-C_auc": aC, "FAM-A_auc": aA,
                        "FAM-C_guarded_chain": gch, "n_guarded_chains": ngc}
            print(f"  probe[{nm:10s}] FAM-C xsplit AUC {aC:.4f}   (FAM-A {aA:.4f})   "
                  f"guarded chain {gch:.4f} ({ngc} chains)")
        # vote score alone (no probe) as the floor reference
        m_ev = ev & (y_gt >= 0) & np.isfinite(V)
        a_vote = float(roc_auc_score(y_gt[m_ev], V[m_ev]))
        print(f"  raw vote V alone (no probe, no DINO): {a_vote:.4f}")
        r["vote_alone_auc"] = a_vote

        # mesh-supervised ceiling, recomputed on this dump (sanity vs P1c)
        a_mesh, s_mesh, mdl = fit_eval(DD, y_gt, fit, y_gt, ev)
        print(f"  mesh-supervised ceiling (recomputed): {a_mesh:.4f}  "
              f"(P1c reported {MESH_AUC_P1C[scene]:.4f})")
        r["mesh_ceiling_recomputed"] = a_mesh
        r["rows"] = rows
        r["mesh_model"] = mdl
        res[scene] = r

    # -------- SECONDARY (demoted): cross-scene transfer of the MESH-supervised probe -----
    print(f"\n================ SECONDARY: cross-scene transfer (NOT a gate) ================")
    for src, dst in (("chair", "lego"), ("lego", "chair")):
        sc, clf = res[src]["mesh_model"]
        dd = data[dst]
        X = dd["DD"].astype(np.float32)
        y_gt = dd["y"]
        m = np.isfinite(X).all(1) & (y_gt >= 0)
        s = clf.predict_proba(sc.transform(X[m]))[:, 1]
        a = float(roc_auc_score(y_gt[m], s))
        res[f"transfer_{src}_to_{dst}"] = a
        print(f"  {src} -> {dst}: AUC {a:.4f}   (within-scene mesh ceilings: "
              f"{res[src]['mesh_ceiling_recomputed']:.4f} -> {res[dst]['mesh_ceiling_recomputed']:.4f})")

    for scene in ("chair", "lego"):
        res[scene].pop("mesh_model", None)
    jp = os.path.join(OUT, "dexprimary_p1d.json")
    json.dump(res, open(jp, "w"), indent=2)
    print(f"\nwrote {jp}")

    best = max(res["chair"]["rows"].values(), key=lambda v: v["FAM-C_auc"])
    a = best["FAM-C_auc"]
    v = "GO" if (a >= 0.78 and a > res["chair"]["rows"]["PL-VOTE"]["FAM-A_auc"] + 0.03) \
        else ("NO-GO" if a <= 0.72 else "GRAY")
    print(f"\nFROZEN GATE (chair, best mesh-free FAM-C xsplit AUC = {a:.4f}): {v}")


if __name__ == "__main__":
    main()
