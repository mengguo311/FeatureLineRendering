"""tier1/scripts/videoviz.py — headline turntable clip: dd3 carrier vs per-frame Canny.

*** MESH EVAL-ONLY: nothing here reads the mesh at all. *** Object space only, no per-scene
tuning.  The clip is rendered on THE METRIC'S OWN TRAJECTORY (look-at-corrected arc from
camera 5 to camera 15, 240 frames), so the video and every banked temporal number describe the
same motion.  The frozen `stroke_metric` warp/match/pop functions are reused directly so the
per-pair numbers are the same operator behind the 12.03x.

Per the pre-registration: the per-pair `cut` MAX, p99 and ARGMAX are reported, not just the
mean, because a mean over 239 pairs is structurally incapable of showing a burst.  The worst
pair is MARKED in the clip.  A per-frame stroke-count trace runs beneath.
"""
import argparse, json, os, subprocess, sys
import cv2, numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1); sys.path.insert(0, os.path.join(TIER1, "scripts"))
from src import common, render, view_split, stroke_metric                # noqa: E402
import temporal_m1b as T                                                 # noqa: E402
import m1b_stroke_temporal as M                                          # noqa: E402
from strokeviz import chain_args, VIZ, SCENE
from dd3 import project_runs, draw_runs

OUT = os.path.join(TIER1, "out")
N_FRAMES, FPS, TILE = 240, 24, 700
TRACE_H = 120


def load_carrier():
    z = np.load(os.path.join(OUT, f"carrier_dd3_{SCENE}.npz"))
    pts, offs, oe = z["pts"], z["offs"], z["open_end"]
    return [pts[offs[i]:offs[i + 1]] for i in range(len(offs) - 1)], [tuple(x) for x in oe]


def trace_panel(counts, k, w, title):
    """Per-frame stroke-count trace: a stable drawing drifts, a flickering one spikes."""
    img = np.full((TRACE_H, w, 3), 255, np.uint8)
    c = np.asarray(counts, np.float64)
    lo, hi = float(c.min()), float(c.max())
    rng = max(hi - lo, 1.0)
    xs = (np.arange(len(c)) / max(len(c) - 1, 1) * (w - 20) + 10).astype(int)
    ys = (TRACE_H - 26 - (c - lo) / rng * (TRACE_H - 46)).astype(int)
    for i in range(len(c) - 1):
        cv2.line(img, (xs[i], ys[i]), (xs[i + 1], ys[i + 1]), (40, 40, 40), 1, cv2.LINE_AA)
    cv2.line(img, (xs[k], 8), (xs[k], TRACE_H - 8), (0, 0, 220), 2)
    cv2.putText(img, f"{title}  strokes/frame  min {lo:.0f} max {hi:.0f}   frame {k}",
                (10, TRACE_H - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 0, 0), 1, cv2.LINE_AA)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=N_FRAMES)
    args = ap.parse_args()
    ca = chain_args()
    ca.n_resample, ca.max_cand, ca.cand_radius, ca.match_thresh = 16, 6, 40.0, 3.0
    cams, _ = common.load_cameras(SCENE)
    g = common.load_gaussians(SCENE)
    keep_g = render.defloat_mask(g["mu"], g["opacity"])
    chain3d, open_end = load_carrier()
    print(f"  carrier of record: {len(chain3d)} strokes", flush=True)
    target = np.median(g["mu"][keep_g], axis=0)
    path = T.orbit_cameras(cams[5], cams[15], args.frames, target)

    # ---- pass 1: the frozen metric, per PAIR ------------------------------------------
    per = {"A": {"pop": [], "cut": [], "unm": []}, "B": {"pop": [], "cut": [], "unm": []}}
    nA, nB = [], []
    prev = None
    for i, cam in enumerate(path):
        fd = M.frame_data(g, keep_g, cam, chain3d, ca)
        nA.append(len(fd["A"])); nB.append(len(fd["B"]))
        if prev is not None:
            for p_ in ("A", "B"):
                w, surv = stroke_metric.warp_strokes(prev[p_], prev["depth"], prev["cam"],
                                                     fd["cam"])
                m = stroke_metric.match_strokes(w, fd[p_], n_resample=ca.n_resample,
                                                max_cand=ca.max_cand,
                                                cand_radius=ca.cand_radius,
                                                match_thresh=ca.match_thresh)
                pp = stroke_metric.pop_penalty(m, n_dropped_by_warp=int((~surv).sum())
                                               if len(surv) else 0)
                per[p_]["pop"].append(pp["P_pop"]); per[p_]["cut"].append(pp["cut_frac"])
                per[p_]["unm"].append(pp["unmatched_frac"])
        prev = fd
        if (i + 1) % 60 == 0:
            print(f"    metric {i+1}/{len(path)}", flush=True)
    cutA = np.array(per["A"]["cut"])
    worst = int(np.argmax(cutA))
    stats = {p_: {"mean_P_pop": float(np.mean(per[p_]["pop"])),
                  "mean_cut": float(np.mean(per[p_]["cut"])),
                  "max_cut": float(np.max(per[p_]["cut"])),
                  "p99_cut": float(np.percentile(per[p_]["cut"], 99)),
                  "argmax_cut_pair": int(np.argmax(per[p_]["cut"])),
                  "mean_unmatched": float(np.mean(per[p_]["unm"])),
                  "max_unmatched": float(np.max(per[p_]["unm"])),
                  "argmax_unmatched_pair": int(np.argmax(per[p_]["unm"]))}
             for p_ in ("A", "B")}
    print(f"\n  OURS  cut mean {stats['A']['mean_cut']:.5f}  max {stats['A']['max_cut']:.5f} "
          f"p99 {stats['A']['p99_cut']:.5f}  argmax pair {worst}", flush=True)
    print(f"  OURS  unmatched mean {stats['A']['mean_unmatched']:.4f} "
          f"max {stats['A']['max_unmatched']:.4f} at pair "
          f"{stats['A']['argmax_unmatched_pair']}", flush=True)
    print(f"  CANNY cut mean {stats['B']['mean_cut']:.5f}  P_pop mean "
          f"{stats['B']['mean_P_pop']:.4f}", flush=True)

    # ---- pass 2: render the clip -------------------------------------------------------
    W = TILE * 2
    vp = os.path.join(VIZ, f"turntable_{SCENE}_dd3_vs_canny.mp4")
    vw = cv2.VideoWriter(vp, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, TILE + TRACE_H))
    ok_mp4 = vw.isOpened()
    gif, sheet = [], []
    for i, cam in enumerate(path):
        gb = render.render_gbuffer(g, keep_g, cam, with_albedo=True)
        dep = gb["depth"]
        ours = draw_runs(project_runs(chain3d, open_end, cam, dep), cam)
        gray = np.clip(gb["albedo"].detach().cpu().numpy().mean(2) * 255, 0, 255).astype(np.uint8)
        bpoly = M.baseline_strokes(gray, ca.canny_lo, ca.canny_hi, ca.min_len, ca.approx_eps)
        base = draw_runs([(np.asarray(q, np.float64), True, True) for q in bpoly if len(q) > 1],
                         cam)
        del gb
        L = cv2.resize((np.clip(ours, 0, 1) * 255).astype(np.uint8), (TILE, TILE))
        R = cv2.resize((np.clip(base, 0, 1) * 255).astype(np.uint8), (TILE, TILE))
        mark = (i == worst or i == worst + 1)
        for im, lab in ((L, f"OURS dd3  {len(chain3d)} object-space strokes"),
                        (R, "BASELINE per-frame Canny")):
            cv2.putText(im, lab, (12, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2,
                        cv2.LINE_AA)
        if mark:
            cv2.rectangle(L, (2, 2), (TILE - 3, TILE - 3), (0, 0, 220), 4)
            cv2.putText(L, f"WORST cut PAIR {worst}", (12, TILE - 16),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 0, 220), 2, cv2.LINE_AA)
        top = np.concatenate([L, R], 1)
        tr = np.concatenate([trace_panel(nA, i, TILE, "OURS"),
                             trace_panel(nB, i, TILE, "CANNY")], 1)
        fr = np.concatenate([top, tr], 0)[:, :, ::-1]
        if ok_mp4:
            vw.write(fr)
        if i % 4 == 0:
            gif.append(cv2.resize(fr, (W // 2, (TILE + TRACE_H) // 2)))
        if i % 20 == 0:
            sheet.append(cv2.resize(np.concatenate([L, R], 1)[:, :, ::-1], (700, 350)))
        if (i + 1) % 60 == 0:
            print(f"    render {i+1}/{len(path)}", flush=True)
    if ok_mp4:
        vw.release()
    made = [vp] if ok_mp4 and os.path.getsize(vp) > 10000 else []
    gp = os.path.join(VIZ, f"turntable_{SCENE}_dd3_vs_canny.gif")
    try:
        import imageio
        imageio.mimsave(gp, [f[:, :, ::-1] for f in gif], fps=12)
        made.append(gp)
    except Exception as e:
        print(f"  (gif fallback unavailable: {e})", flush=True)
    rows = [np.concatenate(sheet[r:r + 4], 1) for r in range(0, len(sheet) - 3, 4)]
    if rows:
        cs = os.path.join(VIZ, f"turntable_{SCENE}_contactsheet.png")
        cv2.imwrite(cs, np.concatenate(rows, 0)); made.append(cs)
    # worst-pair blow-up
    bp = []
    for k in (worst, worst + 1):
        cam = path[min(k, len(path) - 1)]
        gb = render.render_gbuffer(g, keep_g, cam)
        bp.append(cv2.resize((np.clip(draw_runs(project_runs(chain3d, open_end, cam,
                                                             gb["depth"]), cam), 0, 1) * 255
                              ).astype(np.uint8), (850, 850)))
        del gb
    wp = os.path.join(VIZ, f"turntable_{SCENE}_worstpair.png")
    cv2.imwrite(wp, np.concatenate(bp, 1)[:, :, ::-1]); made.append(wp)

    rep = {"scene": SCENE, "n_frames": args.frames, "fps": FPS,
           "trajectory": "look-at-corrected arc cam5->cam15, THE METRIC'S OWN path",
           "carrier": f"dd3 carrier of record, {len(chain3d)} strokes",
           "per_pair": stats, "worst_cut_pair": worst,
           "stroke_counts": {"ours_min": int(min(nA)), "ours_max": int(max(nA)),
                             "canny_min": int(min(nB)), "canny_max": int(max(nB))},
           "mp4_written": bool(ok_mp4), "files": made,
           "mesh_eval_only": "this script reads no mesh at all"}
    json.dump(rep, open(os.path.join(OUT, "videoviz.json"), "w"), indent=1)
    print(f"\n  stroke counts OURS {min(nA)}-{max(nA)} | CANNY {min(nB)}-{max(nB)}")
    for m_ in made:
        print("  " + m_)
    print(f"  -> {os.path.join(OUT,'videoviz.json')}", flush=True)


if __name__ == "__main__":
    main()
