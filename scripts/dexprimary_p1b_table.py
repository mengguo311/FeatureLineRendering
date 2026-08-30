"""Phase 1b — collate every arm. Reads out/dexprimary_p1b_chair*.json."""
import os, json

OUT = os.path.expanduser("~/3dgs_line/tier1/out")
NICE = [("", "MAIN  20 refs, K=6, rho=0.20"),
        ("_cap", "budget-matched to 85,325 (Phase 0's chair cap)"),
        ("_rho002", "rho=0.02  (search bracket 15x the tolerance -- near-local)"),
        ("_rho050", "rho=0.50  (wide epipolar search)"),
        ("_K2", "K=2 neighbour views"),
        ("_K12", "K=12 neighbour views"),
        ("_ref40", "40 reference views")]
ROWS = ["tri_sup1", "tri_sup2", "tri_sup3", "tri_sup2_nocull", "p0_singleview",
        "ctrl_tri_randpix", "ctrl_randfg", "gauss_pool"]


def main():
    print("=" * 116)
    print("PHASE 1b — CHAIR. Multi-view epipolar triangulation vs single-view 3DGS depth.")
    print("Scored on held-out TEST {5,15,..,95}; every cloud triangulated/lifted from TRAIN views only.")
    print("=" * 116)
    base = None
    for tag, lab in NICE:
        p = os.path.join(OUT, f"dexprimary_p1b_chair{tag}.json")
        if not os.path.exists(p):
            continue
        d = json.load(open(p))
        if base is None:
            base = d
            print(f"\nmiss-set {d['n_miss']}/{d['n_gt_pairs']} = {d['miss_fraction']:.4f}"
                  f"   fixed-pool 2D cover {d['pool_cover_2D']:.4f}"
                  f"   radii " + " ".join(f"{k}={v:.5f}" for k, v in d["radii"].items()))
        t = d["tri_stats"]
        print(f"\n-- {lab}   [sup>=2 {t['frac_sup_ge2']:.3f}  surface_keep "
              f"{t['frac_surface_keep']:.3f}  median|dz| {t['median_moved']:.4f}  "
              f"moved>tol {t['frac_moved_gt_tol']:.3f}]")
        print(f"   {'cloud':18s} {'n':>8s} | {'rec2D':>7s} {'covfg':>6s} {'lift':>5s} |"
              f" {'rec3D':>7s} {'Rm3D':>7s} {'pr3D':>7s} | {'rec3D@0.5%':>10s} {'pr3D@0.5%':>9s}")
        for k in ROWS:
            v = d["clouds"].get(k)
            if not v or "recall_2D" not in v:
                continue
            print(f"   {k:18s} {v['n_total']:8d} | {v['recall_2D']:7.4f} {v['cover_fg']:6.3f} "
                  f"{v['lift']:5.2f} | {v['recall_3D_px1.5_equiv']:7.4f} "
                  f"{v['R_miss_3D_px1.5_equiv']:7.4f} {v['precision_3D_px1.5_equiv']:7.4f} | "
                  f"{v['recall_3D_chamfer_0.5pct_bbox']:10.4f} "
                  f"{v['precision_3D_chamfer_0.5pct_bbox']:9.4f}")


if __name__ == "__main__":
    main()
