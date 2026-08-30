"""STEP B.1 — pick tau_geom for the 2DGS gate on the VAL split.

*** EVAL-ONLY DRIVER. The mesh is used to SCORE candidate thresholds, never to build the
gate. The gate itself (src/gate2dgs.py) is mesh-free, and the chosen tau is a single scalar
picked on VAL views {0,10,...,90} -- TEST views {5,15,...,95} are never touched here. ***

WHAT IS MEASURED, per candidate tau_geom, over the VAL views:
    survive     surviving Canny pixels / all on-object Canny pixels
    purity      fraction of SURVIVING edge pixels that are within 2px of a GT crease
                (this is the number the whole plan is about: on vanilla 3DGS the gate could
                not raise it, because the geometric channel was texture-contaminated)
    crease_keep fraction of GT crease pixels that still have a surviving edge pixel within
                2px -- the recall side. A gate that kills fabric AND creases is worthless.
    f1          harmonic mean of purity and crease_keep, used to rank.

The baseline row `tau=0` is the ungated Canny field, i.e. exactly what M1b used, so the
table shows the gate's contribution directly.
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

from src import common, dt_pull, geom_gate, render2dgs, view_split
from src import gate2dgs
from src.gate2dgs import geom_support_2dgs
from src.mesh_oracle import MeshOracle          # EVAL ONLY — scoring the candidates

OUT = os.path.join(TIER1, "out")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="chair")
    ap.add_argument("--model", default=os.path.join(OUT, "2dgs_chair"))
    ap.add_argument("--edge", default="sharp", choices=sorted(dt_pull.EDGE_SETS))
    ap.add_argument("--taus", type=float, nargs="*",
                    default=[0, 4, 6, 8, 10, 12, 15, 20, 25, 30])
    ap.add_argument("--dilate", type=int, default=2)
    ap.add_argument("--use_depth", action="store_true")
    ap.add_argument("--tau_crease", type=float, default=2.0)
    ap.add_argument("--mode", default="ribbon", choices=["ribbon", "patch"],
                    help="ribbon = the STEP-A-validated bilateral ribbon on normals, "
                         "evaluated at each Canny pixel; patch = geom_gate.dihedral_map "
                         "on an 81px grid patch + dilation (the vanilla-3DGS gate shape)")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    cams, rgb_paths = common.load_cameras(args.scene)
    views = list(view_split.VAL)
    g2, pipe, meta = render2dgs.load_2dgs(args.model)
    oracle = MeshOracle(args.scene)               # EVAL ONLY
    cfgs = dt_pull.EDGE_SETS[args.edge]
    print(f"[tau sweep] {args.scene} model={meta['model_path']} it={meta['iteration']} "
          f"VAL views {views}", flush=True)

    acc = {t: {"surv": 0, "tot": 0, "pure": 0, "cre_hit": 0, "cre_tot": 0}
           for t in args.taus}
    for v in views:
        cam = cams[v]
        gb2 = render2dgs.render_gbuffer_2dgs(g2, pipe, cam,
                                             bg_white=meta.get("white_background", True))
        # G_v once per candidate tau (dihedral map itself is tau-independent, so compute
        # the raw angle map once and threshold it repeatedly)
        dep = gb2["depth"].detach().cpu().numpy().astype(np.float32)
        nrm = gb2["normal"].detach().cpu().numpy()
        alp = gb2["alpha"].detach().cpu().numpy()
        e = dt_pull.edge_map(rgb_paths[v], cfgs)
        if args.mode == "ribbon":
            fgm = (alp > 0.5) & np.isfinite(dep)
            dirx, diry = gate2dgs.edge_normals_dir(rgb_paths[v])
            eys, exs = np.nonzero(e)
            th_e, ok_e = gate2dgs.ribbon_normal_theta(
                exs.astype(np.float64), eys.astype(np.float64),
                dirx[eys, exs], diry[eys, exs], nrm, fgm)
            A = D = None
        else:
            A = geom_gate.dihedral_map(nrm, dep, alp)
            D = geom_gate.depth_step_map(dep, alp) if args.use_depth else None
        del gb2
        torch.cuda.empty_cache()
        # GT crease pixels for this view (EVAL ONLY)
        uvq = oracle.visible_crease_uv(cam, view_key=int(v))
        cm = np.zeros((cam.H, cam.W), bool)
        cu = np.clip(np.round(uvq[:, 0]).astype(int), 0, cam.W - 1)
        cv_ = np.clip(np.round(uvq[:, 1]).astype(int), 0, cam.H - 1)
        cm[cv_, cu] = True
        cdt = cv2.distanceTransform((~cm).astype(np.uint8), cv2.DIST_L2, 5)
        cvu, cuu = np.nonzero(cm)

        for t in args.taus:
            if t <= 0:
                ge = e.copy()
            elif args.mode == "ribbon":
                ge = np.zeros_like(e)
                sel = (th_e >= t) & ok_e
                ge[eys[sel], exs[sel]] = True
            else:
                sup = A >= t
                if D is not None:
                    sup = sup | (D >= 0.015)
                ge = geom_gate.gate_edges(e, sup, dilate_px=args.dilate)
            ys, xs = np.nonzero(ge)
            acc[t]["surv"] += len(ys)
            acc[t]["tot"] += int(e.sum())
            acc[t]["pure"] += int((cdt[ys, xs] <= args.tau_crease).sum())
            if len(ys):
                sdt = cv2.distanceTransform((~ge).astype(np.uint8), cv2.DIST_L2, 5)
                acc[t]["cre_hit"] += int((sdt[cvu, cuu] <= args.tau_crease).sum())
            acc[t]["cre_tot"] += len(cvu)
        print(f"  view {v} done", flush=True)

    rows = []
    print("\n" + "=" * 82)
    print(f"tau_geom sweep — {args.scene}, VAL views {views}, edge='{args.edge}', "
          f"mode={args.mode}, dilate={args.dilate}px")
    print(f"{'tau_geom':>9} {'survive':>9} {'purity':>9} {'crease_keep':>12} {'f1':>8}")
    print("-" * 82)
    for t in args.taus:
        a = acc[t]
        surv = a["surv"] / max(a["tot"], 1)
        pur = a["pure"] / max(a["surv"], 1)
        ck = a["cre_hit"] / max(a["cre_tot"], 1)
        f1 = 2 * pur * ck / max(pur + ck, 1e-9)
        rows.append({"tau_geom": t, "survive": surv, "purity": pur,
                     "crease_keep": ck, "f1": f1,
                     "n_edge": a["tot"], "n_surv": a["surv"]})
        lab = " (ungated M1b baseline)" if t <= 0 else ""
        print(f"{t:>9.1f} {surv:>9.3f} {pur:>9.3f} {ck:>12.3f} {f1:>8.3f}{lab}")
    print("-" * 82)
    best = max(rows, key=lambda r: r["f1"])
    base = rows[0]
    print(f"  best f1 at tau_geom = {best['tau_geom']:g}  "
          f"(purity {base['purity']:.3f} -> {best['purity']:.3f}, "
          f"crease_keep {base['crease_keep']:.3f} -> {best['crease_keep']:.3f})")
    print("=" * 82, flush=True)

    tag = f"_{args.tag}" if args.tag else ""
    p = os.path.join(OUT, f"plan1_tau_sweep_{args.scene}{tag}.json")
    json.dump({"scene": args.scene, "model": meta, "val_views": views,
               "edge": args.edge, "mode": args.mode, "dilate": args.dilate,
               "use_depth": bool(args.use_depth), "rows": rows,
               "best_tau": best["tau_geom"]}, open(p, "w"), indent=1, default=float)
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
