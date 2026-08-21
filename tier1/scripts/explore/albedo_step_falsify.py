"""STEP 0.5 — ALBEDO(SH-DC)-STEP FALSIFICATION. Diagnostic only; builds no gate.

*** EVAL-ONLY *** The GT mesh appears here solely to LABEL Canny-edge pixels as
fabric-print vs true-crease, exactly as scripts/explore/gate_falsify.py does. The
measured quantity is computed only from the frozen gaussians + cameras.

WHY THIS INVERTS THE STEP 0 GATE
    STEP 0 killed the geometry gate: the fabric print is baked into vanilla 3DGS as real
    tilted splats, so fabric bilateral dihedral p95 = 79 deg overlaps true-crease
    p05 = 5 deg, and EVERY normal/coplanarity feature inherits that same poisoning.
    So stop asking geometry to CONFIRM creases and ask ALBEDO to REJECT prints:

        a printed line   = a discontinuity in view-independent diffuse base colour,
                           over a continuous surface           -> LARGE SH-DC step
        a true crease    = the same material on both sides,
                           shaded differently                  -> SMALL SH-DC step

MEASURED SCALAR
    s = || c_L - c_R ||_2 , where c_L / c_R are the mean SH DEGREE-0 albedo
    (RGB = clip(0.5 + SH_C0 * f_dc, 0, 1), NO view-direction evaluation of the 45 f_rest
    coefficients) over the two sides of the SAME +-3px bilateral ribbon geometry as
    gate_falsify (3px thick x 10px long, foreground samples only).

FROZEN VERDICT (from M1b_step05_spec.md, not rationalised after the fact)
    CLEAN : fabric s_p05 >= 1.6 * crease s_p95
    LEAKS : fabric s_p05 <= crease s_p95   OR   ratio < 1.2
"""
import json
import os
import sys

import cv2
import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
sys.path.insert(0, os.path.join(TIER1, "scripts/explore"))

from src import common, render, dt_pull, view_split
from src.mesh_oracle import MeshOracle          # EVAL ONLY — labelling only
import gate_falsify as GF                        # reuse ribbon geometry + pct()

OUT = os.path.join(TIER1, "out")
ACROSS = GF.OFF_ACROSS                            # (2,3,4) px -> ribbon centred at +-3px
ALONG = GF.OFF_ALONG                              # 10px long
MIN_VALID = GF.MIN_VALID


def auc(s, y):
    s = np.asarray(s, float); y = np.asarray(y, bool)
    ok = np.isfinite(s); s, y = s[ok], y[ok]
    n1 = int(y.sum()); n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return float("nan")
    r = np.empty(len(s)); r[np.argsort(s, kind="stable")] = np.arange(len(s))
    return float((r[y].sum() - n1 * (n1 - 1) / 2) / (n1 * n0))


def albedo_step(px, py, dirx, diry, albedo, fg, W, H):
    """Bilateral SH-DC albedo step s = ||c_L - c_R|| at pixels (px,py). Vectorised."""
    ax, ay = dirx, diry                           # across-edge (image gradient)
    lx, ly = -diry, dirx                          # along-edge
    sides = []
    for sgn in (-1.0, +1.0):
        acc = np.zeros((len(px), 3))
        cnt = np.zeros(len(px))
        for da in ACROSS:
            for dl in ALONG:
                qx = np.clip(np.round(px + sgn * da * ax + dl * lx).astype(np.int64), 0, W - 1)
                qy = np.clip(np.round(py + sgn * da * ay + dl * ly).astype(np.int64), 0, H - 1)
                m = fg[qy, qx]
                acc += albedo[qy, qx] * m[:, None]
                cnt += m
        sides.append((acc / np.maximum(cnt, 1)[:, None], cnt))
    (cL, nL), (cR, nR) = sides
    s = np.linalg.norm(cL - cR, axis=1)
    ok = (nL >= MIN_VALID) & (nR >= MIN_VALID)
    return s, ok


def run_scene(scene, fields):
    cams, rgb_paths = common.load_cameras(scene)
    g = common.load_gaussians(scene)
    keep = render.defloat_mask(g["mu"], g["opacity"])
    oracle = MeshOracle(scene)
    views = list(view_split.TEST)
    print(f"[{scene}] SH-DC albedo-step falsification, TEST views {views}", flush=True)
    acc = {k: {"fab": [], "cre": [], "fab_all": [], "cre_all": []} for k in fields}

    for v in views:
        cam = cams[v]
        gb = render.render_gbuffer(g, keep, cam, with_albedo=True)
        alb = gb["albedo"].cpu().numpy().astype(np.float64)
        alpha = gb["alpha"].cpu().numpy()
        depth = gb["depth"].cpu().numpy()
        del gb
        fg = (alpha > 0.5) & np.isfinite(depth)

        uvq = oracle.visible_crease_uv(cam, view_key=int(v))
        cm = np.zeros((cam.H, cam.W), bool)
        cm[np.clip(np.round(uvq[:, 1]).astype(int), 0, cam.H - 1),
           np.clip(np.round(uvq[:, 0]).astype(int), 0, cam.W - 1)] = True
        cdt = cv2.distanceTransform((~cm).astype(np.uint8), cv2.DIST_L2, 5)
        sil = fg ^ (cv2.erode(fg.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)
        sdt = cv2.distanceTransform((~sil).astype(np.uint8), cv2.DIST_L2, 5)
        interior = fg & (sdt > 4)

        im = cv2.imread(rgb_paths[v], cv2.IMREAD_UNCHANGED)
        a4 = im[:, :, 3:4].astype(np.float32) / 255.0
        bgr = (im[:, :, :3].astype(np.float32) * a4 + 255.0 * (1 - a4)).astype(np.uint8)
        gray = cv2.GaussianBlur(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), (0, 0), 1.0)
        gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gm = np.maximum(np.sqrt(gx * gx + gy * gy), 1e-9)
        dirx, diry = gx / gm, gy / gm

        for name, cfg in fields.items():
            edge = dt_pull.edge_map(rgb_paths[v], cfg)
            for tag, sel in (("", interior), ("_all", fg)):
                fab = edge & sel & (cdt > 3.0)
                cre = edge & sel & (cdt <= 2.0)
                for cls, m in (("fab", fab), ("cre", cre)):
                    ys, xs = np.nonzero(m)
                    if not len(ys):
                        continue
                    if len(ys) > 20000:
                        idx = np.random.RandomState(0).choice(len(ys), 20000, False)
                        ys, xs = ys[idx], xs[idx]
                    s, ok = albedo_step(xs.astype(np.float64), ys.astype(np.float64),
                                        dirx[ys, xs], diry[ys, xs], alb, fg,
                                        cam.W, cam.H)
                    acc[name][cls + tag].append(s[ok])
        print(f"  view {v} done", flush=True)
    return acc


def summarise(scene, acc, fields):
    out = {"scene": scene, "views": list(view_split.TEST),
           "measure": "s = ||c_L - c_R||, mean SH degree-0 albedo, +-3px bilateral ribbon",
           "fields": {}}
    for name in fields:
        A = acc[name]
        rec = {}
        for tag, lab in (("", "interior"), ("_all", "all_on_object")):
            f = np.concatenate(A["fab" + tag]) if A["fab" + tag] else np.array([])
            c = np.concatenate(A["cre" + tag]) if A["cre" + tag] else np.array([])
            if not len(f) or not len(c):
                continue
            y = np.concatenate([np.zeros(len(f), bool), np.ones(len(c), bool)])
            rec[lab] = {
                "n_fabric": int(len(f)), "n_crease": int(len(c)),
                "fabric_p05": GF.pct(f, 5), "fabric_p50": GF.pct(f, 50),
                "fabric_p95": GF.pct(f, 95),
                "crease_p05": GF.pct(c, 5), "crease_p50": GF.pct(c, 50),
                "crease_p95": GF.pct(c, 95),
                "ratio_fabp05_over_crep95": GF.pct(f, 5) / max(GF.pct(c, 95), 1e-12),
                "auc_fabric_is_higher": auc(np.concatenate([f, c]), ~y),
                "_f": f, "_c": c,
            }
        out["fields"][name] = rec
    return out


def main():
    fields = {"sharp(pull field)": dt_pull.EDGE_SHARP, "m1a(seed field)": dt_pull.EDGE_M1A}
    results = {}
    for scene in (sys.argv[1:] or ["chair", "lego"]):
        acc = run_scene(scene, fields)
        results[scene] = summarise(scene, acc, fields)

    print("\n" + "=" * 100)
    print("STEP 0.5 RESULT — bilateral SH-DC ALBEDO STEP  s = ||c_L - c_R||   (TEST views only)")
    print("hypothesis: fabric print => LARGE s ; true crease => SMALL s")
    print("=" * 100)
    verdicts = {}
    for scene, res in results.items():
        for name, rec in res["fields"].items():
            for lab, r in rec.items():
                mark = "  <== VERDICT ROW" if (name.startswith("sharp") and
                                               lab == "interior") else ""
                print(f"\n[{scene}] {name} / {lab}  n_fabric={r['n_fabric']} "
                      f"n_crease={r['n_crease']}{mark}")
                print(f"    FABRIC s: p05 {r['fabric_p05']:.4f}  p50 {r['fabric_p50']:.4f}  "
                      f"p95 {r['fabric_p95']:.4f}")
                print(f"    CREASE s: p05 {r['crease_p05']:.4f}  p50 {r['crease_p50']:.4f}  "
                      f"p95 {r['crease_p95']:.4f}")
                print(f"    ratio fabric_p05 / crease_p95 = {r['ratio_fabp05_over_crep95']:.3f}"
                      f"   (AUC fabric>crease = {r['auc_fabric_is_higher']:.3f})")
        r = res["fields"]["sharp(pull field)"]["interior"]
        ratio = r["ratio_fabp05_over_crep95"]
        clean = r["fabric_p05"] >= 1.6 * r["crease_p95"]
        leaks = (r["fabric_p05"] <= r["crease_p95"]) or (ratio < 1.2)
        verdicts[scene] = ("GATE CLEAN" if clean else ("GATE LEAKS" if leaks else "IN BETWEEN"))
        res["verdict"] = verdicts[scene]
        res["verdict_ratio"] = ratio

    print("\n" + "#" * 100)
    for scene, v in verdicts.items():
        r = results[scene]["fields"]["sharp(pull field)"]["interior"]
        print(f"# {scene:6s}  fabric s_p05 = {r['fabric_p05']:.4f}   "
              f"crease s_p95 = {r['crease_p95']:.4f}   ratio = "
              f"{r['ratio_fabp05_over_crep95']:.3f}   ==> {v}")
    print("#   CLEAN needs ratio >= 1.6 ; LEAKS if fabric_p05 <= crease_p95 or ratio < 1.2")
    print("#" * 100, flush=True)

    # ---- json + histogram
    for scene, res in results.items():
        j = json.loads(json.dumps(res, default=lambda o: None))
        for name in j["fields"]:
            for lab in j["fields"][name]:
                j["fields"][name][lab].pop("_f", None)
                j["fields"][name][lab].pop("_c", None)
        p = os.path.join(OUT, f"m1b_albedo_step_falsify_{scene}.json")
        json.dump(j, open(p, "w"), indent=2)
        print(f"wrote {p}")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    scenes = list(results)
    fig, axes = plt.subplots(1, len(scenes), figsize=(7 * len(scenes), 5), squeeze=False)
    for j, scene in enumerate(scenes):
        r = results[scene]["fields"]["sharp(pull field)"]["interior"]
        ax = axes[0][j]
        bins = np.linspace(0, 0.6, 90)
        ax.hist(r["_f"], bins=bins, alpha=0.6, density=True, color="tab:red",
                label=f"FABRIC print (n={r['n_fabric']})")
        ax.hist(r["_c"], bins=bins, alpha=0.6, density=True, color="tab:blue",
                label=f"TRUE crease (n={r['n_crease']})")
        ax.axvline(r["fabric_p05"], color="tab:red", ls="--",
                   label=f"fabric p05 = {r['fabric_p05']:.3f}")
        ax.axvline(r["crease_p95"], color="tab:blue", ls="--",
                   label=f"crease p95 = {r['crease_p95']:.3f}")
        ax.set_title(f"{scene} — bilateral SH-DC albedo step (TEST views)\n"
                     f"ratio {r['ratio_fabp05_over_crep95']:.2f} "
                     f"(CLEAN needs >= 1.6)  ==> {results[scene]['verdict']}")
        ax.set_xlabel("s = ||c_L - c_R||   (SH degree-0 RGB)")
        ax.legend(fontsize=8)
    plt.tight_layout()
    p = os.path.join(OUT, "m1b_albedo_step_falsify.png")
    plt.savefig(p, dpi=110)
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
