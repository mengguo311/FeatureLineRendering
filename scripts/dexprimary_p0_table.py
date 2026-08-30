"""Phase 0 — collate every arm into the report tables. Reads out/dexprimary_p0_*.json."""
import os, sys, json, glob

OUT = os.path.expanduser("~/3dgs_line/tier1/out")
ARMS = ["naive", "naive_fill", "fgmin", "median", "medmin", "ctrl_randfg", "ctrl_shufz",
        "gauss_pool"]
NICE = {"": "base (native, thr0.5, hp0, src=test 9-view LOO)",
        "_hp05": "A  + half-pixel grid correction (+0.5)",
        "_ms": "B  + multi-scale detector (ms = max over scales 1.0/0.64)",
        "_srctrain": "C  src=TRAIN 20 views (URS-legal, zero TEST contact)",
        "_best": "D  BEST CASE: ms + hp0.5 + TRAIN20",
        "_thr020": "E  D at thr 0.20 (buy recall with precision)",
        "_thr005": "F  D at thr 0.05 (buy recall with precision)",
        "_urscap": "G  budget-matched to URS's cap, voxel-dedup, ALL clouds"}
TAGS = ["", "_hp05", "_ms", "_srctrain", "_best", "_thr020", "_thr005", "_urscap"]


def load(scene, tag):
    for key in ("native", "ms"):
        p = os.path.join(OUT, f"dexprimary_p0_{scene}_{key}{tag}.json")
        if os.path.exists(p):
            return json.load(open(p))
    return None


def main():
    for scene, ceil_prune, ceil_pool in (("lego", 0.5572, 0.6337), ("chair", 0.7908, 0.7382)):
        print(f"\n{'='*118}\n### {scene.upper()}\n{'='*118}")
        d0 = load(scene, "")
        if d0:
            print("STEP 1 — GAUSSIAN MISS-SET (visible GT crease POINTS, pooled over the 10 TEST views)")
            print(f"{'tau':>5} {'|miss|/|GT| 2D-pt':>18} {'2D pixel-dedup':>16} {'3D any-view':>13}"
                  f" {'pool cover 2D':>14} {'raw cover 2D':>13}")
            for t in ("1.5", "2.5"):
                a = d0[f"missset_2d_tau{t}"]; b = d0[f"missset_3d_tau{t}"]
                c = d0["missset_2d_pixeldedup"][t]
                print(f"{t:>5} {a['miss_fraction']:18.4f} {c['miss_fraction']:16.4f} "
                      f"{b['miss_fraction']:13.4f} {a['cover_fraction_pool']:14.4f} "
                      f"{a['cover_fraction_raw']:13.4f}")
            print(f"      n_GT_pairs={d0['missset_2d_tau1.5']['n_gt_pairs']}  "
                  f"n_miss@1.5={d0['missset_2d_tau1.5']['n_miss']}  "
                  f"gauss pool={d0['n_gauss_pool']} raw={d0['n_gauss_raw']}  "
                  f"bbox_diag={d0['bbox_diag']:.4f}")
            print(f"      radii: " + "  ".join(f"{k}={v:.5f}" for k, v in d0["chamfer_radii"].items()))
            print(f"      REFERENCE CEILINGS: pipeline R@1.5 f=1.00 (prune) = {ceil_prune:.4f}"
                  f" ; all-gaussian-centre coverage (this metric) = {ceil_pool:.4f}")

        for tag in TAGS:
            d = load(scene, tag)
            if d is None:
                continue
            print(f"\n-- ARM {NICE[tag]}   (key={d['key']} thr={d['thr']}"
                  f" halfpix={d.get('halfpix', 0.0)} src={d.get('src', 'test')}"
                  f" n_lift_views={len(d.get('lift_views', d['views']))}"
                  f" budget={d.get('budget', 0)})")
            print(f"   {'cloud':12s} {'n':>7s} | {'Rmiss2D_own':>11s} {'Rmiss2D_loo':>11s}"
                  f" {'cov_fg':>7s} {'lift':>5s} | {'rec2D_own':>9s} {'rec2D_loo':>9s} |"
                  f" {'Rmiss3D':>8s} {'rec3D':>7s} {'prec3D':>7s} | {'Rm3D@1.5%':>9s}")
            for a in ARMS:
                v = d["recovery"].get(a)
                if not v:
                    continue
                print(f"   {a:12s} {v['n_total']:7d} | {v['R_miss_2D_own']:11.4f} "
                      f"{v['R_miss_2D_loo']:11.4f} {v['cover_fg_loo']:7.3f} "
                      f"{v['lift_loo']:5.2f} | {v['recall_2D_own']:9.4f} "
                      f"{v['recall_2D_loo']:9.4f} | {v.get('R_miss_3D_px1.5_equiv',0):8.4f} "
                      f"{v.get('recall_3D_px1.5_equiv',0):7.4f} "
                      f"{v.get('precision_3D_px1.5_equiv',0):7.4f} | "
                      f"{v.get('R_miss_3D_chamfer_1.5pct_bbox',0):9.4f}")


if __name__ == "__main__":
    main()
