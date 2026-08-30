"""STEP A.3 — THE GO/NO-GO DIAGNOSTIC for Plan #1.

*** EVAL-ONLY DIAGNOSTIC. NOT A METHOD MODULE. ***
The GT mesh is used HERE AND ONLY HERE, and only to (a) LABEL Canny-edge pixels as
fabric-print vs true-crease and (b) provide the ceiling control arm. The measurement applied
to those pixels is computed purely from a rendered G-buffer, i.e. exactly what
src/geom_gate.py would be allowed to see.

THE QUESTION
    Vanilla 3DGS bakes printed fabric texture into GEOMETRY: the bilateral-ribbon dihedral
    at a flat printed edge is as large as at a real crease (fabric theta_p95 79.3 deg vs
    crease theta_p05 4.9 deg -- the classes are inverted, AUC ~0.5). Plan #1 asserts that
    2DGS's surfels + depth-normal consistency keep flat printed surfaces FLAT in geometry so
    the same measurement separates the classes. This script tests that, and nothing else.

ARMS (identical pixels, identical labels, identical estimator -- only the geometry differs)
    vanilla   src/render.render_gbuffer on ~/cglib/outputs/<scene>_static/point_cloud.ply
    2dgs:<name>  src/render2dgs.render_gbuffer_2dgs on a trained 2DGS model
    mesh      MeshOracle.render_depth -- GT geometry. THE CEILING CONTROL, and the single
              most important column in the table: the ribbon estimator is itself imperfect,
              and geom_gate.py:28-30 records that on GT-mesh depth it reaches only
              AUC 0.72-0.77. A 2DGS AUC must be read against THAT, not against 1.0.

SCORES (all three are things a mesh-free gate could actually compute)
    theta_depth   bilateral-ribbon dihedral from robust inverse-depth plane fits (the exact
                  gate_falsify.py measurement -- GF.ribbon_measure is imported, not copied)
    dstep         |z_L - z_R| / z with both planes extrapolated to the edge pixel
    theta_normal  angle between the mean RENDERED normal of the two ribbon sides. Not
                  available for the mesh arm. This is the signal STEP B's G_v would use.

PIXEL SET
    Canny edges (dt_pull.EDGE_SHARP and EDGE_M1A) intersected with an INTERIOR mask built
    from the GROUND-TRUTH png alpha (>4px from the silhouette), so that every arm is scored
    on exactly the same pixels -- an arm cannot win by hallucinating or dropping coverage.
    Labels: FABRIC = no GT crease within 3px, CREASE = GT crease within 2px (the 2-3px band
    is discarded), identical to gate_falsify.py:205-207.
    A `legacy` replication using the vanilla arm's OWN alpha (exactly gate_falsify.py) is
    also run, to prove this harness reproduces the published 79.3/4.9 numbers.

THE REFINED CLASSES (added after the first run, and the ones that actually answer Plan #1)
    The first run showed the GT-MESH arm itself scoring fabric theta_p95 = 71.7 deg. The mesh
    has no texture at all, so that tail cannot be texture-baking: the FABRIC class ("Canny edge
    with no GT crease within 3px") is contaminated by pixels whose geometry is genuinely NOT
    flat -- chair legs, ornament silhouettes, self-occlusion boundaries in the interior, and
    folds shallower than the oracle's 30 deg crease criterion. So `fabric_p95` measures mostly
    real geometry, not contamination, and the spec's GO bar (fabric_p95 < 15 deg) is
    unreachable even with perfect geometry.
    To ask the real question -- "does a FLAT printed surface stay flat?" -- we subset using the
    mesh arm as a flatness oracle (EVAL ONLY, same as the labelling):
        FLAT-FABRIC   fabric pixels where the mesh arm's own ribbon theta < FLAT_DEG
                      => GT geometry is locally flat AND colour changes. A texture-blind
                         reconstruction MUST read ~0 here. This is the contamination number.
        SHARP-CREASE  crease pixels where the mesh arm's ribbon theta > SHARP_DEG
                      => GT geometry really is creased and visible from this view.
    Both arms are measured on the identical subsets, so the refined AUC is the clean
    separability of "flat but printed" from "actually creased".

AUC convention (gate_falsify_control.py:39): P(score[crease] > score[fabric]); 0.5 = chance.
"""
import os
import sys
import json
import argparse

import cv2
import numpy as np
import torch

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts"))
sys.path.insert(0, os.path.join(TIER1, "scripts/explore"))

from src import common, render, dt_pull, render2dgs
from src.mesh_oracle import MeshOracle          # EVAL ONLY — labelling + ceiling control
import gate_falsify as GF                       # reuse the estimator verbatim

OUT = os.path.join(TIER1, "out")
MAX_PX_PER_VIEW = 20000
FLAT_DEG = 5.0      # mesh ribbon theta below this => GT surface is locally FLAT
SHARP_DEG = 20.0    # mesh ribbon theta above this => GT surface is genuinely CREASED


# ----------------------------------------------------------------------------- AUC
def auc(scores, labels):
    """P(score[positive] > score[negative]); 0.5 = no information.
    Verbatim from scripts/explore/gate_falsify_control.py:39-46 (tie handling included)."""
    s = np.asarray(scores, float)
    y = np.asarray(labels, bool)
    ok = np.isfinite(s)
    s, y = s[ok], y[ok]
    n1 = int(y.sum())
    n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return float("nan")
    r = np.empty(len(s))
    r[np.argsort(s, kind="stable")] = np.arange(len(s))
    return float((r[y].sum() - n1 * (n1 - 1) / 2) / (n1 * n0))


# ------------------------------------------------------- ribbon dihedral on a NORMAL map
def ribbon_normal_measure(px, py, dirx, diry, normal, fg):
    """Angle between the mean rendered normal of the two ribbon sides.

    Same ribbon geometry as GF.ribbon_measure (GF.OFF_ACROSS / GF.OFF_ALONG), so the two
    dihedrals are directly comparable; only the estimator of each side's orientation differs
    (mean of the composited normal map vs a robust plane fit to inverse depth).
    """
    H, W = fg.shape
    ax, ay = dirx, diry
    lx, ly = -diry, dirx
    nrm = normal.astype(np.float32)
    val = fg.astype(np.float32)

    sides = {}
    for sgn, key in ((-1.0, "L"), (+1.0, "R")):
        acc = np.zeros((len(px), 3), np.float64)
        wsum = np.zeros(len(px), np.float64)
        for da in GF.OFF_ACROSS:
            for dl in GF.OFF_ALONG:
                qx = np.clip(px + sgn * da * ax + dl * lx, 0, W - 1).astype(np.float32)
                qy = np.clip(py + sgn * da * ay + dl * ly, 0, H - 1).astype(np.float32)
                w = cv2.remap(val, qx, qy, cv2.INTER_NEAREST).ravel()
                for c in range(3):
                    acc[:, c] += w * cv2.remap(nrm[:, :, c], qx, qy, cv2.INTER_LINEAR).ravel()
                wsum += w
        m = np.maximum(wsum, 1e-9)[:, None]
        n = acc / m
        nn = np.linalg.norm(n, axis=1, keepdims=True)
        sides[key] = (n / np.maximum(nn, 1e-30), wsum >= GF.MIN_VALID, nn[:, 0])

    nL, okL, mL = sides["L"]
    nR, okR, mR = sides["R"]
    cosang = np.clip(np.abs((nL * nR).sum(1)), -1, 1)
    theta = np.degrees(np.arccos(cosang))
    # a side whose averaged normal nearly cancels (mag << 1) has no consistent orientation
    ok = okL & okR & np.isfinite(theta) & (mL > 0.2) & (mR > 0.2)
    return {"theta": theta, "ok": ok}


# ----------------------------------------------------------------------------- geometry arms
class VanillaArm:
    name = "vanilla-3DGS"

    def __init__(self, scene):
        self.g = common.load_gaussians(scene)
        self.keep = render.defloat_mask(self.g["mu"], self.g["opacity"])
        self.meta = {"kind": "vanilla", "n_gauss": int(self.keep.sum()),
                     "ply": f"~/cglib/outputs/{scene}_static/point_cloud.ply"}

    def gbuffer(self, cam, view_key):
        gb = render.render_gbuffer(self.g, self.keep, cam)
        d = gb["depth"].cpu().numpy().astype(np.float64)
        a = gb["alpha"].cpu().numpy()
        n = gb["normal"].cpu().numpy()
        del gb
        torch.cuda.empty_cache()
        return d, a > 0.5, n


class TwoDGSArm:
    """Arm spec: label=path[,dr=<depth_ratio>][,hp=0|1]

    dr overrides the depth flavour AT RENDER TIME (1.0 = median depth, 0.0 = expected/mean).
    This costs nothing and matters: median depth is quantised to the ray-splat intersection of
    whichever surfel carries the 0.5 alpha crossing, so it can FACET -- manufacturing dihedral
    at splat boundaries. Mean depth is smooth but blurs across true depth steps. Measuring both
    separates "2DGS geometry is contaminated" from "median depth is faceted".
    hp toggles the half-pixel resample (see render2dgs) purely as a robustness check.
    """

    def __init__(self, label, model_path, half_pixel=True, depth_ratio=None):
        self.name = f"2DGS[{label}]"
        self.g, self.pipe, self.meta = render2dgs.load_2dgs(model_path)
        if depth_ratio is not None:
            self.pipe.depth_ratio = float(depth_ratio)
            self.meta["depth_ratio"] = float(depth_ratio)
        self.meta["kind"] = "2dgs"
        self.meta["half_pixel"] = bool(half_pixel)
        self.half_pixel = half_pixel

    def gbuffer(self, cam, view_key):
        gb = render2dgs.render_gbuffer_2dgs(self.g, self.pipe, cam,
                                            bg_white=self.meta.get("white_background", True),
                                            half_pixel=self.half_pixel)
        d = gb["depth"].cpu().numpy().astype(np.float64)
        a = gb["alpha"].cpu().numpy()
        n = gb["normal"].cpu().numpy()
        del gb
        torch.cuda.empty_cache()
        return d, a > 0.5, n


class MeshArm:
    name = "GT-mesh (ceiling control)"

    def __init__(self, oracle):
        self.oracle = oracle
        self.meta = {"kind": "mesh"}

    def gbuffer(self, cam, view_key):
        z = self.oracle.render_depth(cam, view_key=view_key)
        z = z.cpu().numpy() if torch.is_tensor(z) else np.asarray(z)
        z = z.astype(np.float64)
        fg = z < 1e8
        d = np.where(fg, z, np.inf)
        return d, fg, None            # no normal map for the mesh arm


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="chair")
    ap.add_argument("--nviews", type=int, default=8)
    ap.add_argument("--models", nargs="*", default=[],
                    help="2DGS arms: label=path[,dr=<depth_ratio>][,hp=0|1]  "
                         "e.g. default=out/2dgs_chair  meandepth=out/2dgs_chair,dr=0.0")
    ap.add_argument("--no_mesh_arm", action="store_true")
    ap.add_argument("--no_legacy", action="store_true")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    scene = args.scene

    cams, rgb_paths = common.load_cameras(scene)
    oracle = MeshOracle(scene)                                   # EVAL ONLY
    views = np.unique(np.round(np.linspace(0, len(cams) - 1, args.nviews)).astype(int))

    arms = [VanillaArm(scene)]
    for spec in args.models:
        label, rest = spec.split("=", 1)
        parts = rest.split(",")
        path = parts[0]
        kw = {}
        for opt_ in parts[1:]:
            k, val = opt_.split("=", 1)
            if k == "dr":
                kw["depth_ratio"] = float(val)
            elif k == "hp":
                kw["half_pixel"] = bool(int(val))
        arms.append(TwoDGSArm(label, os.path.expanduser(path), **kw))
    if not args.no_mesh_arm:
        arms.append(MeshArm(oracle))

    fields = {"sharp": dt_pull.EDGE_SHARP, "m1a": dt_pull.EDGE_M1A}
    scores = ("theta_depth", "dstep", "theta_normal")
    # acc[arm][field][score] -> {"fab": [...], "cre": [...]}
    # store RAW values + ok masks (not ok-filtered) so every arm stays index-aligned with
    # every other arm on the same pixel list -- required to subset by the mesh flatness oracle
    acc = {a.name: {f: {s: {"fab": [], "cre": []} for s in scores} for f in fields} for a in arms}
    legacy = {f: {s: {"fab": [], "cre": []} for s in ("theta_depth", "dstep")} for f in fields}
    counts = {f: {"fab": 0, "cre": 0, "edge": 0} for f in fields}

    print(f"[STEP A.3] {scene}: GO/NO-GO over {len(views)} views {list(views)}")
    print(f"           arms: {[a.name for a in arms]}", flush=True)

    for v in views:
        cam = cams[v]

        # ---- labels + common pixel set, from GT only (identical for every arm) ----
        im = cv2.imread(rgb_paths[v], cv2.IMREAD_UNCHANGED)
        a4 = im[:, :, 3:4].astype(np.float32) / 255.0
        gt_fg = a4[:, :, 0] > 0.5
        bgr = (im[:, :, :3].astype(np.float32) * a4 + 255.0 * (1 - a4)).astype(np.uint8)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        gb1 = cv2.GaussianBlur(gray, (0, 0), 1.0)
        gx = cv2.Sobel(gb1, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(gb1, cv2.CV_64F, 0, 1, ksize=3)
        gm = np.sqrt(gx * gx + gy * gy)
        dirx = np.where(gm > 1e-9, gx / np.maximum(gm, 1e-9), 1.0)
        diry = np.where(gm > 1e-9, gy / np.maximum(gm, 1e-9), 0.0)

        uvq = oracle.visible_crease_uv(cam, view_key=int(v))     # EVAL ONLY (labelling)
        cm = np.zeros((cam.H, cam.W), bool)
        cu = np.clip(np.round(uvq[:, 0]).astype(int), 0, cam.W - 1)
        cv_ = np.clip(np.round(uvq[:, 1]).astype(int), 0, cam.H - 1)
        cm[cv_, cu] = True
        cdt = cv2.distanceTransform((~cm).astype(np.uint8), cv2.DIST_L2, 5)

        sil = gt_fg ^ (cv2.erode(gt_fg.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)
        sdt = cv2.distanceTransform((~sil).astype(np.uint8), cv2.DIST_L2, 5)
        interior = gt_fg & (sdt > 4)

        # ---- one G-buffer per arm for this view ----
        gbufs = {}
        for a in arms:
            gbufs[a.name] = a.gbuffer(cam, int(v))

        for fname, cfg in fields.items():
            edge = dt_pull.edge_map(rgb_paths[v], cfg)
            counts[fname]["edge"] += int((edge & gt_fg).sum())
            for cls, sel in (("fab", edge & interior & (cdt > 3.0)),
                             ("cre", edge & interior & (cdt <= 2.0))):
                ys, xs = np.nonzero(sel)
                if not len(ys):
                    continue
                if len(ys) > MAX_PX_PER_VIEW:
                    idx = np.random.RandomState(0).choice(len(ys), MAX_PX_PER_VIEW, False)
                    ys, xs = ys[idx], xs[idx]
                counts[fname][cls] += len(ys)
                pxf, pyf = xs.astype(np.float64), ys.astype(np.float64)
                dx_, dy_ = dirx[ys, xs], diry[ys, xs]
                for a in arms:
                    d, fg, nrm = gbufs[a.name]
                    r = GF.ribbon_measure(pxf, pyf, dx_, dy_, d, fg, cam)
                    acc[a.name][fname]["theta_depth"][cls].append((r["theta"], r["ok"]))
                    acc[a.name][fname]["dstep"][cls].append((r["dstep"], r["ok"]))
                    if nrm is not None:
                        rn = ribbon_normal_measure(pxf, pyf, dx_, dy_, nrm, fg)
                        acc[a.name][fname]["theta_normal"][cls].append((rn["theta"], rn["ok"]))
                    else:
                        nz = len(pxf)
                        acc[a.name][fname]["theta_normal"][cls].append(
                            (np.full(nz, np.nan), np.zeros(nz, bool)))

            # ---- legacy replication: vanilla arm, its OWN alpha, exactly gate_falsify.py ----
            if not args.no_legacy:
                d, fg, _ = gbufs["vanilla-3DGS"]
                sil2 = fg ^ (cv2.erode(fg.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)
                sdt2 = cv2.distanceTransform((~sil2).astype(np.uint8), cv2.DIST_L2, 5)
                int2 = fg & (sdt2 > 4)
                for cls, sel in (("fab", edge & int2 & (cdt > 3.0)),
                                 ("cre", edge & int2 & (cdt <= 2.0))):
                    ys, xs = np.nonzero(sel)
                    if not len(ys):
                        continue
                    if len(ys) > MAX_PX_PER_VIEW:
                        idx = np.random.RandomState(0).choice(len(ys), MAX_PX_PER_VIEW, False)
                        ys, xs = ys[idx], xs[idx]
                    r = GF.ribbon_measure(xs.astype(np.float64), ys.astype(np.float64),
                                          dirx[ys, xs], diry[ys, xs], d, fg, cam)
                    ok = r["ok"]
                    legacy[fname]["theta_depth"][cls].append(r["theta"][ok])
                    legacy[fname]["dstep"][cls].append(r["dstep"][ok])

        del gbufs
        torch.cuda.empty_cache()
        print(f"  view {v} done", flush=True)

    # ----------------------------------------------------------------- summarise
    def catpair(lst):
        if not lst:
            return np.array([]), np.zeros(0, bool)
        return (np.concatenate([x[0] for x in lst]),
                np.concatenate([x[1] for x in lst]))

    def cat(lst):
        return np.concatenate(lst) if lst else np.array([])

    def summarise(vf, of, vc, oc):
        """Percentiles + AUC over the ok-and-selected pixels of each class."""
        if of.sum() < 20 or oc.sum() < 20:
            return None
        fab, cre = vf[of], vc[oc]
        y = np.concatenate([np.zeros(len(fab), bool), np.ones(len(cre), bool)])
        sc = np.concatenate([fab, cre])
        return {"n_fab": int(len(fab)), "n_cre": int(len(cre)),
                "fab_p50": GF.pct(fab, 50), "fab_p90": GF.pct(fab, 90),
                "fab_p95": GF.pct(fab, 95), "fab_p99": GF.pct(fab, 99),
                "cre_p05": GF.pct(cre, 5), "cre_p10": GF.pct(cre, 10),
                "cre_p25": GF.pct(cre, 25), "cre_p50": GF.pct(cre, 50),
                "separation": GF.pct(cre, 5) - GF.pct(fab, 95),
                "auc": auc(sc, y)}

    raw = {a.name: {f: {sc: {cls: catpair(acc[a.name][f][sc][cls]) for cls in ("fab", "cre")}
                        for sc in scores} for f in fields} for a in arms}

    # ---- mesh flatness oracle -> refined subsets (EVAL ONLY, same status as the labelling)
    mesh_name = next((a.name for a in arms if isinstance(a, MeshArm)), None)
    sub = {}
    for f in fields:
        if mesh_name is None:
            sub[f] = None
            continue
        mtf, mof = raw[mesh_name][f]["theta_depth"]["fab"]
        mtc, moc = raw[mesh_name][f]["theta_depth"]["cre"]
        sub[f] = {"flat_fab": mof & (mtf < FLAT_DEG),
                  "sharp_cre": moc & (mtc > SHARP_DEG)}

    results = {"scene": scene, "views": [int(x) for x in views], "counts": counts,
               "flat_deg": FLAT_DEG, "sharp_deg": SHARP_DEG,
               "headline": {}, "refined": {}, "legacy": {},
               "arm_meta": {a.name: a.meta for a in arms}}
    for a in arms:
        results["headline"][a.name] = {}
        results["refined"][a.name] = {}
        for f in fields:
            results["headline"][a.name][f] = {}
            results["refined"][a.name][f] = {}
            for sc in scores:
                vf, of = raw[a.name][f][sc]["fab"]
                vc, oc = raw[a.name][f][sc]["cre"]
                results["headline"][a.name][f][sc] = summarise(vf, of, vc, oc)
                if sub[f] is not None:
                    results["refined"][a.name][f][sc] = summarise(
                        vf, of & sub[f]["flat_fab"], vc, oc & sub[f]["sharp_cre"])
                else:
                    results["refined"][a.name][f][sc] = None
    if not args.no_legacy:
        for f in fields:
            results["legacy"][f] = {sc: summarise(cat(legacy[f][sc]["fab"]),
                                                  np.ones(len(cat(legacy[f][sc]["fab"])), bool),
                                                  cat(legacy[f][sc]["cre"]),
                                                  np.ones(len(cat(legacy[f][sc]["cre"])), bool))
                                    for sc in ("theta_depth", "dstep")}

    # ----------------------------------------------------------------- print
    def fmt(x, w=6, p=2):
        return "   n/a" if x is None or not np.isfinite(x) else f"{x:>{w}.{p}f}"

    def table(block, fname, title):
        print("\n" + "-" * 110)
        print(title)
        print("-" * 110)
        print(f"{'arm':<28} {'score':<13} {'fab p50':>8} {'fab p95':>8} {'cre p05':>8} "
              f"{'cre p50':>8} {'sep':>8} {'AUC':>7}  {'n_fab':>7} {'n_cre':>7}")
        for a in arms:
            for sc in scores:
                r = block[a.name][fname][sc]
                if r is None:
                    continue
                print(f"{a.name:<28} {sc:<13} {fmt(r['fab_p50'],8)} {fmt(r['fab_p95'],8)} "
                      f"{fmt(r['cre_p05'],8)} {fmt(r['cre_p50'],8)} "
                      f"{fmt(r['separation'],8)} {fmt(r['auc'],7,3)}  "
                      f"{r['n_fab']:>7} {r['n_cre']:>7}")

    print("\n" + "=" * 110)
    print(f"STEP A GO/NO-GO — {scene}, {len(views)} views, bilateral-ribbon dihedral")
    print("  labels: FABRIC = no GT crease within 3px | CREASE = GT crease within 2px | "
          "interior = >4px from GT silhouette")
    print("=" * 110)
    if not args.no_legacy and results["legacy"].get("sharp", {}).get("theta_depth"):
        L = results["legacy"]["sharp"]["theta_depth"]
        print(f"HARNESS CHECK (vanilla arm, gate_falsify.py replication, own alpha, sharp): "
              f"fabric p95 {L['fab_p95']:.1f}deg  crease p05 {L['cre_p05']:.1f}deg   "
              f"[published: 79.3 / 4.9]")
    for fname in fields:
        table(results["headline"], fname,
              f"[HEADLINE]  EDGE FIELD = {fname}   all labelled pixels "
              f"(n_fab {counts[fname]['fab']}  n_cre {counts[fname]['cre']})")
        if sub[fname] is not None:
            table(results["refined"], fname,
                  f"[REFINED]   EDGE FIELD = {fname}   FLAT-fabric (mesh theta < {FLAT_DEG} deg) "
                  f"vs SHARP-crease (mesh theta > {SHARP_DEG} deg)")

    # ----------------------------------------------------------------- verdict
    def verdict_of(r):
        if r is None:
            return "n/a", None, None, None
        f95, c05, A = r["fab_p95"], r["cre_p05"], r["auc"]
        if f95 > 35.0 or A < 0.80:
            vd = "NO-GO"
        elif f95 < 15.0 and c05 > 25.0 and A >= 0.90:
            vd = "GO"
        else:
            vd = "MARGINAL"
        return vd, f95, c05, A

    print("\n" + "#" * 110)
    print("# FROZEN DECISION (plan1_spec.md:38-45) — GO: fab_p95<15 AND cre_p05>25 AND AUC>=0.90 |"
          " MARGINAL: 0.80<=AUC<0.90 or fab_p95 in [15,35] | NO-GO: fab_p95>35 or AUC<0.80")
    results["verdicts"] = {}
    for block_name in ("headline", "refined"):
        if block_name == "refined" and sub["sharp"] is None:
            continue
        print(f"#\n# --- applied to theta_depth, 'sharp' field, {block_name.upper()} pixels ---")
        results["verdicts"][block_name] = {}
        for a in arms:
            vd, f95, c05, A = verdict_of(results[block_name][a.name]["sharp"]["theta_depth"])
            if f95 is None:
                continue
            results["verdicts"][block_name][a.name] = {
                "verdict": vd, "fab_p95": f95, "cre_p05": c05, "auc": A}
            print(f"#   {a.name:<28} fab_p95 {f95:6.2f}deg  cre_p05 {c05:6.2f}deg  "
                  f"AUC {A:5.3f}   ==> {vd}")
        # the normal-map score is what STEP B's G_v would actually use
        print(f"#   -- same, but theta_normal (the signal STEP B's G_v would use) --")
        for a in arms:
            vd, f95, c05, A = verdict_of(results[block_name][a.name]["sharp"]["theta_normal"])
            if f95 is None:
                continue
            print(f"#   {a.name:<28} fab_p95 {f95:6.2f}deg  cre_p05 {c05:6.2f}deg  "
                  f"AUC {A:5.3f}   ==> {vd}")
    print("#")
    print("# READ THE MESH ARM FIRST. It is GT geometry through the identical estimator, i.e. the")
    print("# CEILING. If the mesh arm does not itself reach the GO thresholds, those thresholds")
    print("# are unreachable by ANY reconstruction and a 2DGS 'NO-GO' says nothing about 2DGS --")
    print("# judge 2DGS by how much of the vanilla->mesh gap it closes instead.")
    for fname in ("sharp",):
        for block_name in ("headline", "refined"):
            if sub[fname] is None:
                continue
            for sc in ("theta_depth", "theta_normal", "dstep"):
                rv = results[block_name][arms[0].name][fname][sc]
                rm = results[block_name][mesh_name][fname][sc] if mesh_name else None
                tw = [a for a in arms if a.meta.get("kind") == "2dgs"]
                for a in tw:
                    r2 = results[block_name][a.name][fname][sc]
                    if not (rv and r2 and rm) or not np.isfinite(rm["auc"]):
                        continue
                    denom = rm["auc"] - rv["auc"]
                    frac = (r2["auc"] - rv["auc"]) / denom if abs(denom) > 1e-9 else float("nan")
                    print(f"#   [{block_name:<8} {sc:<12}] {a.name}: AUC vanilla {rv['auc']:.3f} "
                          f"-> 2DGS {r2['auc']:.3f} -> mesh {rm['auc']:.3f}   "
                          f"gap closed {100*frac:5.1f}%")
    print("#" * 110, flush=True)

    tag = f"_{args.tag}" if args.tag else ""
    pj = os.path.join(OUT, f"2dgs_falsify_{scene}{tag}.json")
    json.dump(results, open(pj, "w"), indent=1, default=float)
    print(f"wrote {pj}")

    # ----------------------------------------------------------------- histograms
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows = [("headline", "theta_depth", "ALL labelled px — dihedral on DEPTH"),
            ("refined", "theta_depth", f"FLAT-fabric vs SHARP-crease — dihedral on DEPTH"),
            ("refined", "theta_normal", f"FLAT-fabric vs SHARP-crease — dihedral on NORMAL")]
    fig, axes = plt.subplots(len(rows), len(arms),
                             figsize=(5.4 * len(arms), 3.6 * len(rows)), squeeze=False)
    bins = np.linspace(0, 90, 91)
    for i, (block_name, sc, rowtitle) in enumerate(rows):
        for j, a in enumerate(arms):
            ax = axes[i][j]
            vf, of = raw[a.name]["sharp"][sc]["fab"]
            vc, oc = raw[a.name]["sharp"][sc]["cre"]
            if block_name == "refined" and sub["sharp"] is not None:
                of = of & sub["sharp"]["flat_fab"]
                oc = oc & sub["sharp"]["sharp_cre"]
            r = results[block_name][a.name]["sharp"][sc]
            if r is None:
                ax.set_title(f"{a.name}\n(no data: {sc})", fontsize=9)
                ax.set_xlim(0, 90)
                continue
            ax.hist(vf[of], bins=bins, alpha=0.6, density=True, color="tab:red",
                    label=f"fabric (n={int(of.sum())})")
            ax.hist(vc[oc], bins=bins, alpha=0.6, density=True, color="tab:blue",
                    label=f"crease (n={int(oc.sum())})")
            ax.axvline(r["fab_p95"], color="tab:red", ls="--",
                       label=f"fab p95 ={r['fab_p95']:.1f}")
            ax.axvline(r["cre_p05"], color="tab:blue", ls="--",
                       label=f"cre p05 ={r['cre_p05']:.1f}")
            ax.axvline(15, color="k", ls=":", lw=1)
            ax.set_title(f"{a.name} — AUC {r['auc']:.3f}\n{rowtitle}", fontsize=8)
            ax.set_xlabel("theta (deg)")
            ax.legend(fontsize=6)
    plt.suptitle(f"STEP A GO/NO-GO — {scene}: fabric-print vs true-crease geometry "
                 f"(identical pixels, labels and estimator across arms)", fontsize=11)
    plt.tight_layout(rect=(0, 0, 1, 0.965))
    pp = os.path.join(OUT, f"2dgs_falsify_{scene}{tag}.png")
    plt.savefig(pp, dpi=110)
    print(f"wrote {pp}")


if __name__ == "__main__":
    main()
