"""tier1/scripts/turntable_gallery.py — 5-solid turntable gallery, ours vs per-frame Canny.

*** MESH EVAL-ONLY in the strictest sense: this script reads NO MESH AT ALL. ***

CARRIER-GEOMETRY IDENTITY, the guarantee this whole deliverable rests on.
Each solid uses its LOCKED FALLBACK carrier: the Step-4 zero-knob set (f=1.00, shipped spec
consensus prune, no keep-fraction), chained by the frozen
`m1b_stroke_temporal.build_chains` at the carrier's OWN half-length from its own npz -- the
identical call the banked Step-4 temporal run made.  Part B polish is RENDERING-ONLY: it sets
stroke width and taper and touches no 3-D point.

**No endpoint snap is applied.**  dd3 snapped endpoints, but snapping MOVES 3-D points and
would change the metric.  Omitting it is the price of the identity guarantee, so every banked
Step-4 P_pop / cut / ratio carries to these clips unchanged.  With no snap there are no joins,
so every stroke end is a true open endpoint and tapers.

Orbit is the metric's own path: look-at-corrected arc cam5 -> cam15, 240 frames, the same
`--view_a 5 --view_b 15 --frames 240` the banked runs used.
"""
import argparse, json, os, sys
import cv2, numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1); sys.path.insert(0, os.path.join(TIER1, "scripts"))
from src import common, render                                            # noqa: E402
import temporal_m1b as T                                                  # noqa: E402
import m1b_stroke_temporal as M                                           # noqa: E402
from strokeviz import chain_args, VIZ
from dd3 import project_runs, draw_runs

OUT = os.path.join(TIER1, "out")
N_FRAMES, FPS, TILE = 240, 24, 700
STRIP0, STRIP_N, STRIP_H = 100, 7, 430
POOLS = {"cadpartA": "_step3pool", "gcube": "_step4", "gprism": "_step4",
         "gicosa": "_step4", "gstep": "_step4"}
ORDER = ["cadpartA", "gcube", "gprism", "gicosa", "gstep"]
# banked Step-4 / Step-3 / Step-8 temporal, quoted not recomputed
BANKED = {"cadpartA": dict(src="Step 3 step3spec", P_pop=0.0771, unmatched=0.0770,
                           cut=0.0002, base=0.8097, ratio=10.50),
          "gcube": dict(src="Step 4", P_pop=0.0381, unmatched=0.0381, cut=0.0000,
                        base=0.7907, ratio=20.77),
          "gprism": dict(src="Step 4", P_pop=0.0459, unmatched=0.0458, cut=0.0001,
                         base=0.8702, ratio=18.97),
          "gicosa": dict(src="Step 4", P_pop=0.0636, unmatched=0.0636, cut=0.0000,
                         base=0.8842, ratio=13.90),
          "gstep": dict(src="Step 8 ship", P_pop=0.0676, unmatched=None, cut=None,
                        base=0.7601, ratio=11.24)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--solids", nargs="+", default=ORDER)
    ap.add_argument("--frames", type=int, default=N_FRAMES)
    args = ap.parse_args()
    ca = chain_args()
    rep = {"orbit": "look-at-corrected cam5->cam15, 240 frames (the metric's own path)",
           "carrier": "Step-4 zero-knob (f=1.00, shipped spec prune, no keep-fraction)",
           "identity": "Part B is rendering-only; NO endpoint snap, so no 3-D point moves "
                       "and every banked temporal number carries unchanged",
           "mesh_eval_only": "this script reads no mesh at all", "solids": {}}

    for S in args.solids:
        print(f"\n===== {S}", flush=True)
        z = np.load(os.path.join(OUT, f"linelets_{S}{POOLS[S]}.npz"))
        tp = os.path.join(OUT, f"linelets_{S}_gal_test.npz")
        np.savez(tp, p=z["p"], t=z["t"], l=z["l"], keep=z["keep"],
                 inlier_ratio=z["inlier_ratio"], n_vis=z["n_vis"])
        chain3d, cinfo = M.build_chains(S, "gal", ca)
        open_end = [(True, True)] * len(chain3d)          # no snap -> every end is open
        arc = float(sum(np.sum(np.linalg.norm(np.diff(V, axis=0), axis=1))
                        for V in chain3d))
        cams, _ = common.load_cameras(S)
        g = common.load_gaussians(S)
        keep_g = render.defloat_mask(g["mu"], g["opacity"])
        ctr = np.median(g["mu"][keep_g], axis=0)
        path = T.orbit_cameras(cams[5], cams[15], args.frames, ctr)

        po = os.path.join(VIZ, f"turntable_{S}_ours.mp4")
        pc = os.path.join(VIZ, f"turntable_{S}_canny.mp4")
        vo = cv2.VideoWriter(po, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (TILE, TILE))
        vc = cv2.VideoWriter(pc, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (TILE, TILE))
        so, sc, nA, nB = [], [], [], []
        for i, cam in enumerate(path):
            gb = render.render_gbuffer(g, keep_g, cam, with_albedo=True)
            runs = project_runs(chain3d, open_end, cam, gb["depth"])
            ours = draw_runs(runs, cam)
            gray = np.clip(gb["albedo"].detach().cpu().numpy().mean(2) * 255,
                           0, 255).astype(np.uint8)
            bp = M.baseline_strokes(gray, ca.canny_lo, ca.canny_hi, ca.min_len, ca.approx_eps)
            can = draw_runs([(np.asarray(q, np.float64), True, True) for q in bp if len(q) > 1],
                            cam)
            del gb
            nA.append(len(runs)); nB.append(len(bp))
            L = cv2.resize((np.clip(ours, 0, 1) * 255).astype(np.uint8), (TILE, TILE))
            R = cv2.resize((np.clip(can, 0, 1) * 255).astype(np.uint8), (TILE, TILE))
            cv2.putText(L, f"{S} OURS  {len(chain3d)} object-space strokes", (12, 26),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 0, 0), 2, cv2.LINE_AA)
            cv2.putText(R, f"{S} BASELINE per-frame Canny", (12, 26),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 0, 0), 2, cv2.LINE_AA)
            vo.write(L[:, :, ::-1]); vc.write(R[:, :, ::-1])
            if STRIP0 <= i < STRIP0 + STRIP_N:
                so.append(cv2.resize(L, (STRIP_H, STRIP_H)))
                sc.append(cv2.resize(R, (STRIP_H, STRIP_H)))
            if (i + 1) % 80 == 0:
                print(f"    {i+1}/{len(path)}", flush=True)
        vo.release(); vc.release()
        rowo = np.concatenate(so, 1); rowc = np.concatenate(sc, 1)
        hdr = np.full((40, rowo.shape[1], 3), 255, np.uint8)
        cv2.putText(hdr, f"{S}  consecutive orbit frames {STRIP0}-{STRIP0+STRIP_N-1}/"
                         f"{args.frames}   TOP = OURS ({len(chain3d)} strokes)   "
                         f"BOTTOM = per-frame Canny   banked cut "
                         f"{BANKED[S]['cut']}  ratio {BANKED[S]['ratio']}x",
                    (10, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 0, 0), 2, cv2.LINE_AA)
        strip = np.concatenate([hdr, rowo, rowc], 0)
        ps = os.path.join(VIZ, f"turntable_{S}_strip.png")
        cv2.imwrite(ps, strip[:, :, ::-1])
        ok = [p for p in (po, pc) if os.path.getsize(p) > 10000]
        rep["solids"][S] = {
            "n_strokes": cinfo["n_strokes"], "n_linelets": cinfo["n_linelets"],
            "median_vertices": cinfo["median_vertices"], "arc_world": arc,
            "runs_per_frame_ours": [int(min(nA)), int(max(nA))],
            "strokes_per_frame_canny": [int(min(nB)), int(max(nB))],
            "banked_temporal": BANKED[S], "files": ok + [ps]}
        print(f"  [{S}] {cinfo['n_strokes']} strokes, arc {arc:.3f}, runs/frame "
              f"{min(nA)}-{max(nA)} vs Canny {min(nB)}-{max(nB)}", flush=True)
        print(f"  wrote {po}\n  wrote {pc}\n  wrote {ps}", flush=True)
        del g
    json.dump(rep, open(os.path.join(OUT, "turntable_gallery.json"), "w"), indent=1)
    print(f"\n  -> {os.path.join(OUT,'turntable_gallery.json')}", flush=True)


if __name__ == "__main__":
    main()
