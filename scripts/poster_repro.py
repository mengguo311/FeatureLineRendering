"""tier1/scripts/poster_repro.py — reproduce the SIGGRAPH-Asia-2025 poster pipeline
(Hao Weiren / Mukai, "3DGS rasterization-state feature line rendering") on ONE lego view.

*** MESH EVAL-ONLY: this script reads no mesh at all — it is pure image-space. ***

WHAT THIS IS.  The poster's method is per-pixel and image-space: it records, for every
pixel, the rasterisation state (colour, depth, normal, opacity and the top-k contributing
Gaussian IDs with their normalised blend weights), compares adjacent pixels channel by
channel, and fuses the resulting discontinuity fields into one feature-line image.

WHAT IS RECONSTRUCTED, NOT SOURCED.  We do not have the poster or its Figure 3.  Every
choice below marked [RECON] is our reconstruction from the user's description of the
method, not a transcription of the source:
  [RECON] the lego VIEW (we use cams[5], the first held-out TEST view and the anchor of
          the banked 240-frame orbit, so it is a pre-committed choice not a hand-picked one)
  [RECON] k = 4 and 8 (both reported, to expose k-sensitivity)
  [RECON] the per-channel operator forms (Sobel / 4-neighbour max)
  [RECON] the top-k weight NORMALISATION (we normalise within the retained top-k so a pixel's
          k weights sum to 1; the alternative is to normalise by the pixel's FULL accumulated
          weight, which leaks "how much mass top-k captured" into the dissimilarity)
  [RECON] the FUSION (rank-normalise each field to [0,1], then MAX) — OUR PARAMETER-FREE
          STAND-IN.  The poster's real fusion rule is UNKNOWN to us.
  [RECON] the THRESHOLD that turns the fused field into an ink image (ink-matched to the
          per-frame Canny baseline's ink density on the same frame)

GAUSSIAN-ID PLUMBING.  src/render.py is NOT modified (standing constraint: do not touch the
shipped pipeline).  render_state() below is a faithful copy of render.render_gbuffer's
fragment build + lexsort + segmented-exclusive-cumsum compositing, with ONE array added:
frag_gid, the ORIGINAL gaussian index of each fragment.  Two traps this handles explicitly:
  (a) `gi` from torch.nonzero is local to the radius bucket, which indexes the `ok`-culled
      set, which indexes the keep_mask subset -> the index must be remapped all the way back
      to the original ply row, or the IDs silently name the wrong primitives;
  (b) top-k by WEIGHT is NOT the front-most k, because w = T*alpha and alpha varies per
      fragment -> a second (stable, descending-w) lexsort is required, not a slice of the
      existing front-to-back order.
"""
import argparse, json, os, sys
import cv2, numpy as np, torch

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
sys.path.insert(0, TIER1); sys.path.insert(0, os.path.join(TIER1, "scripts"))
from src import common, render                                            # noqa: E402

OUT = os.path.join(TIER1, "out")
VIZ = os.path.join(OUT, "featviz")


# ----------------------------------------------------------------------------------
# 1. rasterisation state with per-pixel top-k Gaussian IDs + normalised blend weights
# ----------------------------------------------------------------------------------
def render_state(g, keep_mask, cam, device="cuda", K=8, r_min=1.0, r_max=15.0,
                 frag_alpha_min=0.01):
    """Compatibility API. Shared full-K implementation; historical files unchanged.

    Float64 transmittance improves precision; this wrapper is not a claim of
    bit-identical reproduction of the older copied disc renderer.
    """
    from src.raster_state import render_state as shared_render_state
    return shared_render_state(g, keep_mask, cam, device, K, r_min, r_max, frag_alpha_min)


# ----------------------------------------------------------------------------------
# 2. per-channel discontinuity operators
# ----------------------------------------------------------------------------------
def sobel_mag(x):
    gx = cv2.Sobel(x.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(x.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3)
    return np.sqrt(gx * gx + gy * gy)


def nb4_max(fn_pair, H, W, cov=None):
    """max over the 4-neighbourhood of a symmetric per-edge scalar.
    fn_pair(a_slice, b_slice) -> per-edge value.

    cov = the COVERAGE mask (alpha>0.01).  An edge between two EMPTY pixels has no
    rasterisation state at either end, and both set-valued channels return their MAXIMUM
    there by accident (two zero normals give a 90 deg angle; two empty ID sets share
    nothing, so weighted overlap gives 1).  Left in, that manufactures a large tied block
    at the top of the field, which then swallows the whole top-q budget at every q.  An
    edge with coverage at EITHER end is kept, because object-vs-empty is a real silhouette."""
    Dr = fn_pair((slice(None), slice(0, W - 1)), (slice(None), slice(1, W)))   # [H,W-1]
    Dd = fn_pair((slice(0, H - 1), slice(None)), (slice(1, H), slice(None)))   # [H-1,W]
    if cov is not None:
        Dr = Dr * (cov[:, :W - 1] | cov[:, 1:])
        Dd = Dd * (cov[:H - 1, :] | cov[1:, :])
    F = np.zeros((H, W), np.float32)
    F[:, :W - 1] = np.maximum(F[:, :W - 1], Dr)
    F[:, 1:] = np.maximum(F[:, 1:], Dr)
    F[:H - 1, :] = np.maximum(F[:H - 1, :], Dd)
    F[1:, :] = np.maximum(F[1:, :], Dd)
    return F, Dr, Dd


def normal_field(nrm, cov):
    H, W, _ = nrm.shape
    def pair(a, b):
        d = np.sum(nrm[a] * nrm[b], -1)
        return np.degrees(np.arccos(np.clip(d, -1, 1))).astype(np.float32)
    return nb4_max(pair, H, W, cov)[0]


def color_field(alb, cov):
    """[RECON] tone/hue discontinuity = CIE-Lab dE76 across adjacent pixels.
    Source is the VIEW-INDEPENDENT SH degree-0 composite (rasterisation state), not the
    photograph."""
    lab = cv2.cvtColor(np.clip(alb, 0, 1).astype(np.float32), cv2.COLOR_RGB2Lab)
    H, W, _ = lab.shape
    def pair(a, b):
        return np.linalg.norm(lab[a] - lab[b], axis=-1).astype(np.float32)
    return nb4_max(pair, H, W, cov)[0]


def topk_field(ids, ws, dev, cov, chunk=100):
    """WEIGHTED-OVERLAP dissimilarity between adjacent pixels:
           D(p,q) = 1 - sum_i min(w_p(i), w_q(i))   over the UNION of the two ID sets.
    Because IDs are unique within a pixel, sum_{i,j} [id_p(i)==id_q(j)] * min(w_p(i),w_q(j))
    equals the union sum exactly.  Chosen over Jaccard and over top-1-ID-changed because a
    gaussian merely fading out of the top-k still carries weight in both pixels, so this
    stays low there and saturates only where the contributing mixture is replaced wholesale."""
    H, W, K = ids.shape
    def edge(a_i, a_w, b_i, b_w):
        outs = []
        n = a_i.shape[0]
        for y0 in range(0, n, chunk):
            ai, aw = a_i[y0:y0 + chunk], a_w[y0:y0 + chunk]
            bi, bw = b_i[y0:y0 + chunk], b_w[y0:y0 + chunk]
            m = (ai[..., :, None] == bi[..., None, :]) & (ai[..., :, None] >= 0)
            ov = (m * torch.minimum(aw[..., :, None], bw[..., None, :])).sum((-1, -2))
            outs.append((1.0 - ov).cpu().numpy().astype(np.float32))
            del m, ov
        return np.concatenate(outs, 0)
    Dr = edge(ids[:, :W - 1], ws[:, :W - 1], ids[:, 1:], ws[:, 1:])
    Dd = edge(ids[:H - 1], ws[:H - 1], ids[1:], ws[1:])
    Dr = Dr * (cov[:, :W - 1] | cov[:, 1:])          # see nb4_max: empty-vs-empty gives 1
    Dd = Dd * (cov[:H - 1, :] | cov[1:, :])
    F = np.zeros((H, W), np.float32)
    F[:, :W - 1] = np.maximum(F[:, :W - 1], Dr)
    F[:, 1:] = np.maximum(F[:, 1:], Dr)
    F[:H - 1, :] = np.maximum(F[:H - 1, :], Dd)
    F[1:, :] = np.maximum(F[1:, :], Dd)
    return F


def support_mask(alpha, r=7):
    """The rasterisation state is UNDEFINED on pixels no gaussian covers.  Two empty pixels
    have no normals (dot=0 -> a spurious 90 deg) and no IDs (empty sets -> a spurious
    dissimilarity of 1), so an unmasked background does not read as "no feature", it reads as
    "maximal feature" and contaminates the rank normalisation of exactly those two channels.
    Support = object dilated by r so genuine silhouette edges (object-vs-empty) survive."""
    return cv2.dilate((alpha > 0.01).astype(np.uint8), np.ones((r, r), np.uint8)).astype(bool)


def compute_fields(st, Ks=(4, 8), support=None):
    dep = st["depth"].cpu().numpy()
    fin = np.isfinite(dep)
    depf = dep.copy()
    depf[~fin] = (dep[fin].max() * 1.05) if fin.any() else 1.0   # [RECON] background fill
    alpha = st["alpha"].cpu().numpy()
    cov = alpha > 0.01
    if support is None:
        support = support_mask(alpha)
    fields = {
        "opacity": sobel_mag(alpha),
        "depth": sobel_mag(depf),
        "normal": normal_field(st["normal"].cpu().numpy(), cov),
        "color": color_field(st["albedo"].cpu().numpy(), cov),
    }
    for k in Ks:
        fields[f"topk{k}"] = topk_field(st["topk_id"][..., :k].contiguous(),
                                        st["topk_w"][..., :k].contiguous()
                                        / st["topk_w"][..., :k].sum(-1, keepdim=True
                                                                    ).clamp(min=1e-12),
                                        st["topk_id"].device, cov)
    for n in fields:
        fields[n] = fields[n] * support
    return fields, support


# ----------------------------------------------------------------------------------
# 3. parameter-free fusion
# ----------------------------------------------------------------------------------
def rank_norm(x):
    """rn(v) = #{pixels strictly below v} / N.  Tie-safe (a tied block of zeros maps to
    exactly 0, so background does not float up to the mid-range as an average-rank would)."""
    f = x.ravel().astype(np.float64)
    s = np.sort(f)
    return (np.searchsorted(s, f, side="left") / len(f)).reshape(x.shape).astype(np.float32)


def fuse(fields, kfuse=8):
    """Rank-normalise EVERY field (so all are available for diagnostics), then MAX over the
    five poster channels.  [RECON] OUR PARAMETER-FREE STAND-IN; the poster's rule is UNKNOWN."""
    names = ["opacity", "depth", "normal", "color", f"topk{kfuse}"]
    rn = {n: rank_norm(v) for n, v in fields.items()}
    F = np.zeros_like(rn[names[0]])
    for n in names:
        F = np.maximum(F, rn[n])
    return F, rn, names


# ----------------------------------------------------------------------------------
# 4. novelty / redundancy of the top-k channel vs the depth channel
# ----------------------------------------------------------------------------------
def topn_mask(field, support, n):
    """The top n support pixels by field value.  NOT `field >= quantile`: these fields carry
    large exactly-tied blocks (a silhouette where every top-k set is disjoint gives D == 1
    everywhere along it), and a >= threshold admits the entire tie regardless of n, which
    silently freezes the detection set across a whole q sweep.  Ties here break by raster
    order — arbitrary, but disclosed and deterministic."""
    idx = np.flatnonzero(support.ravel())
    if idx.size == 0:
        return np.zeros_like(support)
    v = field.ravel()[idx]
    n = int(min(max(n, 1), v.size))
    sel = idx[np.argsort(-v, kind="stable")[:n]]
    m = np.zeros(field.size, bool); m[sel] = True
    return m.reshape(field.shape)


def topq_mask(field, support, q):
    return topn_mask(field, support, int(round(q * float(support.sum()))))


def jacc(a, b):
    u = (a | b).sum()
    return float((a & b).sum() / u) if u else 0.0


def redundancy(rn, support, qs=(0.005, 0.01, 0.02, 0.05),
               others=("depth", "normal", "opacity", "color", "topk4")):
    """Is the novel top-k channel redundant?  Measured against EVERY other channel, not just
    the one it was predicted to duplicate, each with its own rotated null."""
    rep = []
    for q in qs:
        A = topq_mask(rn["topk8"], support, q)      # the novel channel
        dtA = cv2.distanceTransform((~A).astype(np.uint8), cv2.DIST_L2, 5) \
            if A.any() else np.full(A.shape, 1e9, np.float32)
        e = {"q": q, "n_topk8": int(A.sum()), "vs": {}}
        for on in others:
            O = topq_mask(rn[on], support, q)
            On = np.rot90(O, 1).copy()
            dtO = cv2.distanceTransform((~O).astype(np.uint8), cv2.DIST_L2, 5) \
                if O.any() else np.full(O.shape, 1e9, np.float32)
            ee = {"jaccard": jacc(A, On * 0 + O), "jaccard_rotated_null": jacc(A, On)}
            for tol in (1.5, 3.0, 5.0):
                ee[f"frac_topk8_beyond_{tol}px"] = float((dtO[A] > tol).mean()) if A.any() else 0.0
            e["vs"][on] = ee
        B = topq_mask(rn["depth"], support, q)      # kept explicitly: the predicted duplicate
        Bn = np.rot90(B, 1).copy()
        dtB = cv2.distanceTransform((~B).astype(np.uint8), cv2.DIST_L2, 5) \
            if B.any() else np.full(B.shape, 1e9, np.float32)
        e.update({"n_depth": int(B.sum()),
                  "jaccard_topk8_vs_depth": jacc(A, B),
                  "jaccard_rotated_null": jacc(A, Bn)})
        # A tolerance SWEEP, not a single number: two detectors that trace the SAME contour
        # 1-2 px apart look 100% "novel" at tol=1.5 and 0% novel at tol=5.  Only the decay
        # across tolerances separates "offset duplicate" from "different structure".
        for tol in (1.5, 3.0, 5.0):
            e[f"frac_topk8_beyond_{tol}px_of_depth"] = \
                float((dtB[A] > tol).mean()) if A.any() else 0.0
            e[f"frac_depth_beyond_{tol}px_of_topk8"] = \
                float((dtA[B] > tol).mean()) if B.any() else 0.0
        rep.append(e)
    return rep


def silhouette_domination(rn, F, support, alpha, qs=(0.01, 0.02, 0.05)):
    """How much of each field's top-q budget is SPENT ON THE SILHOUETTE?

    The fused rank-max still is visibly almost pure outline.  That could be a property of the
    fields or of the fusion, and eyeballing cannot tell them apart, so measure it: the
    fraction of a field's top-q detections lying within 2 px of the alpha>0.5 boundary.
    If the individual channels are far less silhouette-dominated than their rank-max union,
    the fusion is what loses the interior lines, not the channels."""
    m = (alpha > 0.5).astype(np.uint8)
    k = np.ones((3, 3), np.uint8)
    sil = (cv2.dilate(m, k) - cv2.erode(m, k)) > 0
    dt = cv2.distanceTransform((~sil).astype(np.uint8), cv2.DIST_L2, 5)
    out = {"n_silhouette_px": int(sil.sum()), "n_support_px": int(support.sum()), "by_q": []}
    for q in qs:
        row = {"q": q}
        for name, fld in list(rn.items()) + [("FUSED", F)]:
            D = topq_mask(fld, support, q)
            row[name] = float((dt[D] <= 2.0).mean()) if D.any() else 0.0
        out["by_q"].append(row)
    return out


# ----------------------------------------------------------------------------------
# 5. panel
# ----------------------------------------------------------------------------------
def stretch(x, support, hi=99.5):
    """DISPLAY ONLY (affects no measurement): linear stretch of the RAW field to
    [0, P99.5 over the support].  Rank-normalisation is the FUSION rule, but it is
    uniformising by construction, so rendering a rank map as an image is a grey wash;
    the raw field with a robust stretch is what shows the structure."""
    v = x[support]
    t = np.percentile(v, hi) if v.size else 1.0
    return np.clip(x / max(t, 1e-12), 0, 1)


def wrap(title, ncol):
    out, cur = [], ""
    for w in title.split():
        if len(cur) + len(w) + 1 > ncol and cur:
            out.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        out.append(cur)
    return out


def tile(img01, title, size=620, cmap=cv2.COLORMAP_INFERNO, rgb=False, nline=3):
    if rgb:
        t = (np.clip(img01, 0, 1) * 255).astype(np.uint8)
    else:
        t = cv2.applyColorMap((np.clip(img01, 0, 1) * 255).astype(np.uint8), cmap)[:, :, ::-1]
    t = cv2.resize(t, (size, size), interpolation=cv2.INTER_AREA)
    hdr = np.full((22 * nline + 12, size, 3), 255, np.uint8)
    for i, ln in enumerate(wrap(title, 62)[:nline]):
        cv2.putText(hdr, ln, (8, 20 + 22 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.46,
                    (0, 0, 0), 1, cv2.LINE_AA)
    return np.concatenate([hdr, t], 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="lego")
    ap.add_argument("--view", type=int, default=5)      # [RECON] first held-out TEST view
    ap.add_argument("--churn_frames", type=int, default=8)
    ap.add_argument("--f0", type=int, default=100)
    ap.add_argument("--skip_churn", action="store_true")
    a = ap.parse_args()
    dev = "cuda"
    S = a.scene
    cams, rgbp = common.load_cameras(S)
    g = common.load_gaussians(S)
    kg = render.defloat_mask(g["mu"], g["opacity"])
    print(f"[state] {S}: {len(g['mu'])} gaussians, {int(kg.sum())} after de-floater; "
          f"view cams[{a.view}] name={cams[a.view].name}", flush=True)

    cam = cams[a.view]
    st = render_state(g, kg, cam, device=dev, K=8)
    print(f"[state] fragments={st['n_frag']:,}  topk arrays {tuple(st['topk_id'].shape)}",
          flush=True)
    ti = st["topk_id"].cpu().numpy()
    occ = (ti >= 0).sum(-1)
    alpha = st["alpha"].cpu().numpy()
    obj = alpha > 0.01
    print(f"[state] mean #gaussians in top-8 over object pixels: {occ[obj].mean():.2f}; "
          f"pixels with a full 8: {float((occ[obj]==8).mean()):.3f}", flush=True)

    fields, support = compute_fields(st, Ks=(4, 8))
    F, rn, names = fuse(fields, kfuse=8)
    red = redundancy(rn, support)
    sil = silhouette_domination(rn, F, support, alpha)
    for row in sil["by_q"]:
        print("[silhouette] q={:.3f}  ".format(row["q"]) +
              "  ".join(f"{n}={row[n]:.3f}" for n in
                        ("opacity", "depth", "normal", "color", "topk4", "topk8", "FUSED")),
              flush=True)
    for r in red:
        print(f"[redundancy] q={r['q']:.3f}  topk8 vs: " + "  ".join(
            f"{n} J={v['jaccard']:.3f}(null {v['jaccard_rotated_null']:.3f})"
            f" beyond3px={v['frac_topk8_beyond_3.0px']:.3f}"
            for n, v in r["vs"].items()), flush=True)

    # --- panel ---
    photo = cv2.imread(rgbp[a.view], cv2.IMREAD_UNCHANGED)
    if photo is not None:
        if photo.shape[2] == 4:
            al = photo[:, :, 3:4].astype(np.float32) / 255.0
            photo = photo[:, :, :3].astype(np.float32) / 255.0 * al + (1 - al)
        else:
            photo = photo[:, :, :3].astype(np.float32) / 255.0
        photo = photo[:, :, ::-1]
    else:
        photo = np.clip(st["albedo"].cpu().numpy(), 0, 1)

    q_ov = 0.01
    A = topq_mask(rn["topk8"], support, q_ov); B = topq_mask(rn["depth"], support, q_ov)
    kd = np.ones((3, 3), np.uint8)   # DISPLAY-only 1px dilation so the labels survive resize
    Ad = cv2.dilate(A.astype(np.uint8), kd).astype(bool)
    Bd = cv2.dilate(B.astype(np.uint8), kd).astype(bool)
    ov = np.ones(A.shape + (3,), np.float32)
    ov[Ad] = (0.90, 0.15, 0.15); ov[Bd] = (0.15, 0.30, 0.90)
    ov[Ad & Bd] = (0.10, 0.10, 0.10)

    Jq = [r for r in red if r["q"] == q_ov][0]
    # fused-field display: the rank-max is a RANKING, uniform by construction, so show
    # where its top decile sits (display-only stretch; changes no measurement)
    rF = rank_norm(np.where(support, F, -1.0))
    rFs = np.clip((rF - 0.90) / 0.10, 0, 1) * support

    ck_prev = None
    tiles = [
        tile(photo, f"RGB  {S} cams[{a.view}] ({cams[a.view].name})  [held-out TEST view]", rgb=True),
        tile(stretch(fields["opacity"], support), "1. OPACITY discont.  Sobel |grad alpha|"),
        tile(stretch(fields["depth"], support), "2. DEPTH discont.  Sobel |grad z|"),
        tile(stretch(fields["normal"], support), "3. NORMAL discont.  4-nb max angle"),
        tile(stretch(fields["color"], support), "4. COLOR/TONE discont.  4-nb max Lab dE"),
        tile(stretch(fields["topk4"], support), "5a. TOP-K GAUSSIAN  k=4  weighted overlap"),
        tile(stretch(fields["topk8"], support), "5b. TOP-K GAUSSIAN  k=8  weighted overlap"),
        tile(rFs, "FUSED rank-max, top decile [OUR PARAM-FREE STAND-IN; poster rule UNKNOWN]"),
        tile(np.zeros_like(F), "PLACEHOLDER-INKMATCHED"),
        tile(np.zeros_like(F), "PLACEHOLDER-RICH"),
        tile(ov, f"REDUNDANCY: top-1% detections. RED = top-k(k=8) only, BLUE = depth only, "
                 f"BLACK = both. Jaccard {Jq['jaccard_topk8_vs_depth']:.3f} vs rotated null "
                 f"{Jq['jaccard_rotated_null']:.3f}; {sil['by_q'][0]['topk8']:.0%} of top-k and "
                 f"{sil['by_q'][0]['depth']:.0%} of depth sit within 2px of the silhouette.",
             rgb=True),
    ]
    ctx_tiles = tiles
    rows = None
    panel = None
    return dict(a=a, S=S, cams=cams, g=g, kg=kg, F=F, rn=rn, red=red, support=support,
                obj=obj, occ=occ, st_nfrag=st["n_frag"], fields=fields, tiles=ctx_tiles,
                view_name=cams[a.view].name, sil=sil)


# ----------------------------------------------------------------------------------
# 6. composite still (ink) + free instrument: ink_churn on 8 CONSECUTIVE orbit frames
# ----------------------------------------------------------------------------------
def canny_ink(albedo_np, ca, M, draw_runs, cam):
    gray = np.clip(albedo_np.mean(2) * 255, 0, 255).astype(np.uint8)
    bp = M.baseline_strokes(gray, ca.canny_lo, ca.canny_hi, ca.min_len, ca.approx_eps)
    img = draw_runs([(np.asarray(qq, np.float64), True, True) for qq in bp if len(qq) > 1], cam)
    return img.min(2) < 0.6


def ink_from_fused(F, support, n_target):
    """[RECON] threshold the fused field so it draws n_target ink pixels — ink-MATCHED to
    the per-frame Canny baseline on the same frame, so ink_churn compares like with like."""
    return topn_mask(F, support, n_target)


def churn(a, b, tol=1.5):
    out = []
    for x, y in ((a, b), (b, a)):
        if not x.any():
            out.append(0.0); continue
        dt = (cv2.distanceTransform((~y).astype(np.uint8), cv2.DIST_L2, 5)
              if y.any() else np.full(y.shape, 1e9, np.float32))
        out.append(float((dt[x] > tol).mean()))
    return float(np.mean(out))


def finish(ctx):
    import temporal_m1b as T                                              # noqa: E402
    import m1b_stroke_temporal as M                                       # noqa: E402
    from strokeviz import chain_args
    from dd3 import draw_runs
    a, S, cams, g, kg = ctx["a"], ctx["S"], ctx["cams"], ctx["g"], ctx["kg"]
    F, support = ctx["F"], ctx["support"]
    ca = chain_args()
    dev = "cuda"

    # --- composite still, ink-matched to Canny on the SAME (still) view ---
    cam = cams[a.view]
    gb = render.render_gbuffer(g, kg, cam, with_albedo=True)
    ck = canny_ink(gb["albedo"].detach().cpu().numpy(), ca, M, draw_runs, cam)
    del gb
    torch.cuda.empty_cache()
    n_c = int(ck.sum())
    ink = ink_from_fused(F, support, n_c)
    still = np.full(F.shape, 255, np.uint8)
    still[ink] = 0
    p_im = os.path.join(VIZ, "poster_repro_lego_composite_still_inkmatched.png")
    cv2.imwrite(p_im, still)

    # A RICHER budget.  At the Canny-matched budget the fused field spends almost the whole
    # ink allowance on the silhouette (every one of the five channels ranks the object/empty
    # boundary at its top, so the MAX puts it first), and the interior feature lines never get
    # drawn.  q_rich is a DISCLOSED display budget, not a tuned constant: it exists so the
    # reader can see what the interior of the fused field actually contains.
    q_rich = 0.05
    ink_r = topq_mask(F, support, q_rich)
    still_r = np.full(F.shape, 255, np.uint8); still_r[ink_r] = 0
    p_still = os.path.join(VIZ, "poster_repro_lego_composite_still.png")
    cv2.imwrite(p_still, still_r)
    n_sil = int(ink.sum())
    print(f"[still] ink-matched {n_sil} px -> {p_im}", flush=True)
    print(f"[still] rich q={q_rich} {int(ink_r.sum())} px -> {p_still}", flush=True)

    # --- assemble the 11-tile panel now that the ink renderings exist ---
    tiles = ctx["tiles"]
    g2i = lambda m: np.repeat((m.astype(np.float32) / 255.0)[:, :, None], 3, 2)
    fs = ctx["sil"]["by_q"][0]["FUSED"]
    tiles[8] = tile(g2i(still), f"FEATURE LINE RENDERING, ink-MATCHED to per-frame Canny "
                                f"({n_sil} px). {fs:.0%} of the budget lands within 2px of the "
                                f"silhouette, so the interior creases are never drawn.",
                    rgb=True)
    tiles[9] = tile(g2i(still_r), f"FEATURE LINE RENDERING, richer budget: top {q_rich:.0%} of "
                                  f"support ({int(ink_r.sum())} px). [budget DISCLOSED, not tuned]",
                    rgb=True)
    rows = [np.concatenate(tiles[0:6], 1), np.concatenate(tiles[6:12], 1)]
    if rows[1].shape[1] < rows[0].shape[1]:
        pad = np.full((rows[1].shape[0], rows[0].shape[1] - rows[1].shape[1], 3), 255, np.uint8)
        rows[1] = np.concatenate([rows[1], pad], 1)
    panel = np.concatenate(rows, 0)
    lines = ["POSTER REPRODUCTION (Hao Weiren / Mukai, SIGGRAPH Asia 2025) - rasterisation-state "
             "feature-line fields on ONE held-out lego view (cams[5]).  Fields 1-4 and 5a/5b are "
             "the RAW fields with a P99.5 display stretch; the FUSION is rank-normalise-each-then-MAX.",
             "Bracketed labels are OUR RECONSTRUCTION from a description of the method, not the "
             "source: we have neither the poster nor its Figure 3, so fidelity to it is NOT assessed "
             "here.  Per-frame image-space: this WILL flicker; temporal is reported, NOT gated."]
    banner = np.full((34 * len(lines) + 14, panel.shape[1], 3), 255, np.uint8)
    for i, ln in enumerate(lines):
        cv2.putText(banner, ln, (14, 30 + 34 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.72,
                    (0, 0, 0), 1, cv2.LINE_AA)
    panel = np.concatenate([banner, panel], 0)
    p_panel = os.path.join(VIZ, "poster_repro_lego_fields.png")
    cv2.imwrite(p_panel, panel[:, :, ::-1])
    print(f"[panel] wrote {p_panel}  {panel.shape[1]}x{panel.shape[0]}", flush=True)

    churn_rep = None
    if not a.skip_churn:
        path = T.orbit_cameras(cams[5], cams[15], 240, np.median(g["mu"][kg], axis=0))
        FU, CK = [], []
        for k in range(a.f0, a.f0 + a.churn_frames):
            c = path[k]
            st = render_state(g, kg, c, device=dev, K=8)
            fl_, sup = compute_fields(st, Ks=(8,))
            f_, rn_, _ = fuse(fl_, kfuse=8)
            alb = st["albedo"].cpu().numpy()
            del st
            torch.cuda.empty_cache()
            ckm = canny_ink(alb, ca, M, draw_runs, c)
            FU.append(ink_from_fused(f_, sup, int(ckm.sum())))
            CK.append(ckm)
            print(f"  frame {k}: fused ink {int(FU[-1].sum())}  canny ink {int(ckm.sum())}",
                  flush=True)
        cf = [churn(FU[i], FU[i + 1]) for i in range(len(FU) - 1)]
        cc = [churn(CK[i], CK[i + 1]) for i in range(len(CK) - 1)]
        churn_rep = {"frames": list(range(a.f0, a.f0 + a.churn_frames)), "tol_px": 1.5,
                     "ink_matched_to": "per-frame Canny stroke render, same frame",
                     "ink_churn_fused_mean": float(np.mean(cf)),
                     "ink_churn_fused_max": float(np.max(cf)),
                     "ink_churn_canny_mean": float(np.mean(cc)),
                     "ink_churn_canny_max": float(np.max(cc)),
                     "banked_lego_canny_mean": 0.5358592081068483,
                     "banked_lego_objectspace_mean": 0.058360037369825854,
                     "ink_px_fused": [int(x.sum()) for x in FU],
                     "ink_px_canny": [int(x.sum()) for x in CK]}
        print(f"[churn] FUSED {np.mean(cf):.4f} (max {np.max(cf):.4f})   "
              f"CANNY-here {np.mean(cc):.4f}   banked lego Canny 0.5359 / ours 0.0584",
              flush=True)
        # consecutive strip for the eye
        h = 420
        rf = np.concatenate([cv2.resize((~x * 255).astype(np.uint8), (h, h)) for x in FU], 1)
        rc = np.concatenate([cv2.resize((~x * 255).astype(np.uint8), (h, h)) for x in CK], 1)
        hdr = np.full((40, rf.shape[1]), 255, np.uint8)
        cv2.putText(hdr, f"poster-fused (TOP, ink_churn {np.mean(cf):.3f}) vs per-frame Canny "
                         f"(BOTTOM, {np.mean(cc):.3f}) - frames {a.f0}-{a.f0+a.churn_frames-1} "
                         f"of the 240-frame orbit. Per-frame image-space: NOT gated on temporal.",
                    (10, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.5, 0, 1, cv2.LINE_AA)
        p_strip = os.path.join(VIZ, "poster_repro_lego_consecutive_strip.png")
        cv2.imwrite(p_strip, np.concatenate([hdr, rf, rc], 0))
        print(f"[churn] wrote {p_strip}", flush=True)

    rep = {"scene": S, "view_index": a.view, "view_name": ctx["view_name"],
           "n_gaussians": int(len(g["mu"])), "n_kept": int(kg.sum()),
           "n_fragments_still_view": int(ctx["st_nfrag"]),
           "mean_topk8_occupancy_object_px": float(ctx["occ"][ctx["obj"]].mean()),
           "panel": p_panel, "panel_wh": [int(panel.shape[1]), int(panel.shape[0])],
           "still_rich": p_still, "still_rich_ink_px": int(ink_r.sum()), "q_rich": q_rich,
           "still_inkmatched": p_im, "still_inkmatched_ink_px": int(ink.sum()),
           "canny_ink_px_same_view": n_c,
           "redundancy": ctx["red"], "silhouette_domination": ctx["sil"], "churn": churn_rep}
    jp = os.path.join(OUT, "poster_repro_lego.json")
    json.dump(rep, open(jp, "w"), indent=1)
    print(f"[done] wrote {jp}", flush=True)


if __name__ == "__main__":
    finish(main())
