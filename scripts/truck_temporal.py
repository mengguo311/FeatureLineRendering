"""Experiment B — Truck temporal go/no-go (driver-side; mesh-free).

Reuses the SHIPPED metric operators VERBATIM (m1b_stroke_temporal.frame_data /
sequence_metrics for P_pop, boiltest.churn for ink_churn). The ONLY change vs the
synthetic runs: the frame sequence is the REAL consecutive capture cameras (COLMAP poses),
not a synthesized orbit — the honest sequence for a real capture. fg_only silhouette
control ON. Mesh-free (Truck has no GT mesh).

Pre-registered go/no-go (FROZEN, from cron_3dgs_overnight.txt):
  GO  if fg_only P_pop ratio (Canny/ours) >=5x at 240f AND ink_churn ratio >=8x consecutive
      AND strip visibly steadier AND >=300 strokes/frame.
  NO-GO if either number misses OR <300 strokes/frame.
Matched-precision axis is NON-transportable (no GT mesh) — reported as such, not gated.
"""
import os, sys, json, time
TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "src"))
sys.path.insert(0, os.path.join(TIER1, "scripts"))
sys.path.insert(0, os.path.join(TIER1, "scripts/explore/syn"))
import numpy as np, cv2
from src import common, render
import truck_ingest

# redirect loaders to Truck (adapter only)
common.load_cameras = lambda scene: truck_ingest.load_truck_cameras()
common.load_gaussians = lambda scene: truck_ingest.load_truck_gaussians()

import m1b_stroke_temporal as M
import boiltest as B
from strokeviz import chain_args, VIZ
from dd3 import project_runs, draw_runs

OUT = os.path.join(TIER1, "out")
N_FRAMES = 240      # 240 consecutive real cameras (pre-registered horizon)
FG_ERODE = 2

class A: pass

def main():
    t0 = time.time()
    ca = chain_args()
    ca.variant = "truck_gal"
    ca.fg_only = True
    ca.fg_erode = FG_ERODE
    # sequence_metrics matching params (frozen m1b_stroke_temporal defaults)
    ca.n_resample = 16; ca.max_cand = 6; ca.cand_radius = 40.0; ca.match_thresh = 3.0
    ca.raw_path = False
    # build chains from the mesh-free Truck carrier (linelets_truck_truck_gal_test.npz)
    # build_chains reads linelets_{scene}_{variant}_test.npz; make it point at our carrier
    src = os.path.join(OUT, "linelets_truck_gal_test.npz")
    dst = os.path.join(OUT, "linelets_truck_truck_gal_test.npz")
    import shutil; shutil.copy(src, dst)
    chain3d, cinfo = M.build_chains("truck", "truck_gal", ca)
    print(f"[truck] carrier -> {cinfo['n_strokes']} strokes "
          f"(NMS {cinfo['n_nms']} linelets, med vtx {cinfo['median_vertices']:.0f})", flush=True)

    cams, _ = common.load_cameras("truck")
    g = common.load_gaussians("truck")
    kg = render.defloat_mask(g["mu"], g["opacity"])
    nf = min(N_FRAMES, len(cams) - 1)
    seq = list(range(nf + 1))     # consecutive real cameras 0..nf
    print(f"[truck] {len(cams)} cams -> temporal over {nf} consecutive real-capture frames, fg_only ON", flush=True)

    # ---- P_pop (shipped operator, fg_only) over real consecutive cams ----
    frames = []
    for i in seq:
        frames.append(M.frame_data(g, kg, cams[i], chain3d, ca, g2=None))
        if i % 40 == 0:
            print(f"  [frame_data] {i}/{nf}", flush=True)
    m = M.sequence_metrics(frames, ca)
    A_pop, B_pop = m["A"]["P_pop"], m["B"]["P_pop"]
    A_n = m["A"]["n_strokes_per_frame"]
    pop_ratio = B_pop / max(A_pop, 1e-9)
    print(f"[P_pop fg_only] OURS {A_pop:.4f} ({A_n:.0f} strokes/frame)  "
          f"CANNY {B_pop:.4f}  ratio(Canny/ours) {pop_ratio:.2f}x", flush=True)

    # ---- ink_churn (shipped boiltest operator) over consecutive real cams ----
    oe = [(True, True)] * len(chain3d)
    O, C = [], []
    NB = min(30, nf)   # 30 consecutive frames for ink strip/churn (enough, fast)
    for k in range(NB):
        cam = cams[k]
        gb = render.render_gbuffer(g, kg, cam, with_albedo=True)
        O.append(draw_runs(project_runs(chain3d, oe, cam, gb["depth"]), cam))
        gray = np.clip(gb["albedo"].detach().cpu().numpy().mean(2) * 255, 0, 255).astype(np.uint8)
        bp = M.baseline_strokes(gray, ca.canny_lo, ca.canny_hi, ca.min_len, ca.approx_eps)
        C.append(draw_runs([(np.asarray(q, np.float64), True, True) for q in bp if len(q) > 1], cam))
        del gb
    co = [B.churn(B.ink(O[i]), B.ink(O[i+1])) for i in range(NB-1)]
    cc = [B.churn(B.ink(C[i]), B.ink(C[i+1])) for i in range(NB-1)]
    ic_ours, ic_canny = float(np.mean(co)), float(np.mean(cc))
    ic_ratio = ic_canny / max(ic_ours, 1e-9)
    print(f"[ink_churn] OURS {ic_ours:.4f} (max {np.max(co):.4f})  "
          f"CANNY {ic_canny:.4f} (max {np.max(cc):.4f})  ratio {ic_ratio:.2f}x", flush=True)

    # 8-frame consecutive strip for the eyeball test
    h = 400
    def strip(imgs):
        return np.concatenate([cv2.resize((np.clip(x,0,1)*255).astype(np.uint8),(h,h)) for x in imgs[:8]], 1)
    ro, rc = strip(O), strip(C)
    hdr = np.full((40, ro.shape[1], 3), 255, np.uint8)
    cv2.putText(hdr, f"TRUCK real-capture CONSECUTIVE frames 0-7  TOP=OURS ({cinfo['n_strokes']} str, churn {ic_ours:.3f})  BOTTOM=Canny (churn {ic_canny:.3f})",
                (10,27), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0,0,0), 1, cv2.LINE_AA)
    strip_p = os.path.join(VIZ, "truck_consecutive_strip.png")
    cv2.imwrite(strip_p, np.concatenate([hdr, ro, rc], 0)[:, :, ::-1])

    # ---- frozen go/no-go verdict ----
    go_pop = pop_ratio >= 5.0
    go_ic = ic_ratio >= 8.0
    go_density = A_n >= 300
    verdict = "GO" if (go_pop and go_ic and go_density) else "NO-GO"
    rep = {
        "experiment": "B — real-capture Truck (COLMAP estimated poses), mesh-free",
        "carrier": cinfo, "n_frames_pop": nf, "n_frames_churn": NB,
        "fg_only": True, "trajectory": "REAL consecutive capture cameras (not synthetic orbit)",
        "P_pop": {"ours": A_pop, "canny": B_pop, "ratio_canny_over_ours": pop_ratio,
                  "strokes_per_frame": A_n},
        "ink_churn": {"ours": ic_ours, "canny": ic_canny, "ratio": ic_ratio},
        "prereg": {"pop_ratio>=5": go_pop, "ink_churn_ratio>=8": go_ic,
                   "strokes>=300": go_density, "strip_steadier": "SEE truck_consecutive_strip.png"},
        "matched_precision": "NON-transportable (no GT mesh on real capture) — reported not gated",
        "VERDICT_numeric": verdict,
        "strip": strip_p,
        "elapsed_s": time.time() - t0,
    }
    json.dump(rep, open(os.path.join(OUT, "B_TRUCK_TEMPORAL.json"), "w"), indent=1)
    print(f"\n=== VERDICT (numeric, pending eyeball of strip): {verdict} ===")
    print(f"    P_pop ratio {pop_ratio:.2f}x (need>=5, {'PASS' if go_pop else 'MISS'})")
    print(f"    ink_churn ratio {ic_ratio:.2f}x (need>=8, {'PASS' if go_ic else 'MISS'})")
    print(f"    strokes/frame {A_n:.0f} (need>=300, {'PASS' if go_density else 'MISS'})")
    print(f"    wrote out/B_TRUCK_TEMPORAL.json + {strip_p}  ({time.time()-t0:.0f}s)")

if __name__ == "__main__":
    main()
