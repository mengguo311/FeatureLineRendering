"""CMEPI — batch-cache OTHER frozen zero-shot learned edge detectors, same contract as TEED.

*** METHOD-PATH. Mesh-free. No mesh_oracle import. ***

THE QUESTION THIS SCRIPT EXISTS TO ANSWER
    The arc's peak finding is that a FROZEN ZERO-SHOT LEARNED edge prior (TEED/BIPED) buys
    rankable seeds that move the M1b f-frontier outward.  Open question: is that a property
    of LEARNED EDGE PRIORS IN GENERAL, or is it TEED-SPECIFIC overfitting?  The only way to
    tell is to swap the detector and change NOTHING else.  So this script is
    `recall_trackB_teed.py` with the model made pluggable and every output path namespaced by
    detector; the cache it writes is byte-compatible with the TEED cache, which is what lets
    `final_recipe.set_edge_source(source="teed", cache=<this dir>)` read it with zero code
    change and keep the whole downstream pipeline bit-identical.

THE THREE DETECTORS, AND WHY THESE THREE
    Each is a PUBLISHED, FROZEN, ZERO-SHOT checkpoint.  Nothing is fine-tuned, nothing is
    per-scene tuned.  Together they separate the two things that could explain the TEED lift:

      detector   arch          params       training data                        isolates
      --------   ----          ------       -------------                        --------
      TEED       TED           58,910       BIPED                                (control)
      DexiNed    DexiNed       35,215,245   BIPED                                ARCHITECTURE
                                                                                 (same data,
                                                                                  598x bigger)
      PiDiNet    PiDiNet       710,149      BSDS500-aug + PASCAL VOC Context     ARCH *AND*
                 (carv4,sa,dil)                                                  TRAINING DATA

    DexiNed shares TEED's training set, so if it reproduces the lift the effect is not about
    the BIPED annotation protocol being uniquely lucky at 58K parameters.  PiDiNet shares
    neither, so if IT reproduces the lift the effect is not about BIPED at all.

EACH DETECTOR IS RUN ON ITS OWN REPO'S PREPROCESSING CONTRACT, NOT A SHARED ONE
    Forcing one normalisation on all three would be the opposite of a zero-shot transfer test
    -- it would measure how robust each checkpoint is to being fed the wrong input.  Each
    contract below was read off the originating source, not guessed:

      TEED     BGR uint8 -> float32, minus mean_bgr [104.007,116.669,122.679], NO /255.
               sigmoid(model(x)[-1]); fused map = last element (img_processing.py:151).
      DexiNed  BGR uint8 -> float32, minus mean_bgr [103.939,116.779,123.68], NO /255
               (xavysp/DexiNed datasets.py TestDataset.transform + main.py mean_pixel_values).
               kornia's DexiNed.forward returns ONE tensor of RAW LOGITS which IS the fused
               map (== the original repo's results[6] == block_cat); sigmoid applied OUTSIDE.
      PiDiNet  RGB uint8 -> /255 -> ImageNet Normalize(mean=[.485,.456,.406],
               std=[.229,.224,.225]) (edge_dataloader.py:27-31, test path uses the same
               transform).  net(x)[-1] is the fused map and the SIGMOID IS ALREADY APPLIED
               INSIDE the model (models/pidinet.py:279) -- applying it again would be a bug.

WHAT IS HELD BIT-IDENTICAL TO THE TEED CACHE (so the comparison is about the detector only)
    * ALPHA: the RGBA renders are composited over WHITE before the forward pass -- the same
      background final_recipe.photo_edge_map composites over and the background the 3DGS was
      trained with.  Feeding premultiplied RGB would put a fake black halo on every
      silhouette, and it would do so differently for each detector.
    * SCALE: two scales, 1.0 (native 800) and 0.64 (= 512, TEED's training resolution),
      quantised with the IDENTICAL `int(round(H*s/8))*8` rule, each resampled back to 800.
      `native` = the 1.0 map; `ms` = elementwise max over both.
    * STORAGE: raw probability (no per-image contrast stretch -- that is not comparable
      ACROSS views and the M1a evidence aggregate is multi-view), float16, one
      `v<view:03d>.npz` per view with keys `native` and `ms`, all 100 views.
    * VIEW KEYING: files are enumerated in `common.load_cameras` order, which is verified to
      be r_0..r_99 with file index == view index, the same assumption `final_recipe.teed_prob`
      makes when it parses the view id out of the rgb file name.

    DexiNed additionally gets replicate-padding up to a multiple of 16 (its repo resizes up
    to /16) and is cropped back; at 800 and 512 both are already multiples of 16, so this is
    a no-op here and is present only so the contract is right if the resolution ever changes.
"""
import os
import sys
import time
import json
import argparse
import hashlib

import cv2
import numpy as np
import torch

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
EXT = os.path.expanduser("~/3dgs_line/ext")
sys.path.insert(0, TIER1)
sys.path.insert(0, os.path.join(TIER1, "scripts/explore/syn"))

from src import common
import final_recipe as FR

OUT = os.path.join(TIER1, "out")
SCALES = (1.0, 0.64)                       # 0.64*800 = 512 = TEED/BIPED train resolution

TEED_DIR = os.path.join(EXT, "TEED")
TEED_CKPT = os.path.join(TEED_DIR, "checkpoints/BIPED/5/5_model.pth")
TEED_MEAN_BGR = np.array([104.007, 116.669, 122.679], np.float32)

PIDINET_DIR = os.path.join(EXT, "pidinet")
PIDINET_CKPT = os.path.join(PIDINET_DIR, "weights/table5_pidinet.pth")
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], np.float32)

DEXINED_MEAN_BGR = np.array([103.939, 116.779, 123.68], np.float32)


# ------------------------------------------------------------------ detector plugins
class Detector:
    """A frozen zero-shot edge detector: BGR uint8 HxWx3 -> float32 HxW prob in (0,1)."""

    name = "?"
    train_data = "?"
    citation = "?"

    def n_params(self):
        return int(sum(p.numel() for p in self.model.parameters()))

    @torch.no_grad()
    def prob(self, bgr):
        raise NotImplementedError


class TEEDDetector(Detector):
    name = "TEED"
    train_data = "BIPED"
    citation = "xavysp/TEED, 'Tiny and Efficient Model for the Edge Detection Generalization', ICCVW 2023"

    def __init__(self, device, ckpt=TEED_CKPT):
        if TEED_DIR not in sys.path:
            sys.path.insert(0, TEED_DIR)
        from ted import TED
        self.ckpt = ckpt
        self.model = TED().to(device).eval()
        self.model.load_state_dict(torch.load(ckpt, map_location=device))
        self.device = device

    @torch.no_grad()
    def prob(self, bgr):
        x = bgr.astype(np.float32) - TEED_MEAN_BGR           # BGR, NO /255
        x = torch.from_numpy(np.ascontiguousarray(x.transpose(2, 0, 1)))[None].to(self.device)
        return torch.sigmoid(self.model(x)[-1])[0, 0].float().cpu().numpy()


class DexiNedDetector(Detector):
    name = "DexiNed"
    train_data = "BIPED"
    citation = "Soria et al., 'Dense Extreme Inception Network', WACV 2020; weights DexiNed_BIPED_10.pth via kornia"

    def __init__(self, device):
        from kornia.filters.dexined import DexiNed
        self.model = DexiNed(pretrained=True)                # torch.hub -> ~/.cache/torch
        self.model.eval()
        self.model.disable_features = True                   # do not retain per-call outputs
        self.model = self.model.to(device)
        self.device = device
        self.ckpt = os.path.join(torch.hub.get_dir(), "checkpoints", "DexiNed_BIPED_10.pth")

    @torch.no_grad()
    def prob(self, bgr):
        H, W = bgr.shape[:2]
        x = bgr.astype(np.float32) - DEXINED_MEAN_BGR        # BGR, NO /255
        x = torch.from_numpy(np.ascontiguousarray(x.transpose(2, 0, 1)))[None].to(self.device)
        ph, pw = (-H) % 16, (-W) % 16                        # repo pads up to a /16 shape
        if ph or pw:
            x = torch.nn.functional.pad(x, (0, pw, 0, ph), mode="replicate")
        fused = self.model(x)                                # (1,1,H,W) RAW LOGITS = fused
        return torch.sigmoid(fused)[0, 0, :H, :W].float().cpu().numpy()


class PiDiNetDetector(Detector):
    name = "PiDiNet"
    train_data = "BSDS500-aug + PASCAL VOC Context"
    citation = "Su et al., 'Pixel Difference Networks for Efficient Edge Detection', ICCV 2021; weights table5_pidinet.pth"

    def __init__(self, device, ckpt=PIDINET_CKPT):
        if PIDINET_DIR not in sys.path:
            sys.path.insert(0, PIDINET_DIR)
        import models
        self.ckpt = ckpt
        args = argparse.Namespace(config="carv4", sa=True, dil=True)   # == table5_pidinet
        sd = torch.load(ckpt, map_location="cpu")["state_dict"]
        net = models.pidinet(args)
        net.load_state_dict({k.replace("module.", ""): v for k, v in sd.items()}, strict=True)
        # models/ops.py:84 allocates its rd-op buffer with torch.cuda.FloatTensor, i.e. on the
        # CURRENT cuda device rather than the weights' device.  Under CUDA_VISIBLE_DEVICES=1
        # the visible card IS index 0 so this is already consistent, but pin it anyway.
        if str(device).startswith("cuda"):
            torch.cuda.set_device(torch.device(device).index or 0)
        self.model = net.to(device).eval()
        self.device = device

    @torch.no_grad()
    def prob(self, bgr):
        rgb = bgr[:, :, ::-1].astype(np.float32) / 255.0     # BGR->RGB, ToTensor() scaling
        rgb = (rgb - IMAGENET_MEAN) / IMAGENET_STD
        x = torch.from_numpy(np.ascontiguousarray(rgb.transpose(2, 0, 1)))[None].to(self.device)
        return self.model(x)[-1][0, 0].float().cpu().numpy()  # sigmoid ALREADY applied inside


DETECTORS = {"teed": TEEDDetector, "dexined": DexiNedDetector, "pidinet": PiDiNetDetector}


# ------------------------------------------------------------------ shared TEED contract
def composite_white(rgba_path):
    """RGBA png -> BGR uint8 over a WHITE background (identical to FR.photo_edge_map)."""
    im = cv2.imread(rgba_path, cv2.IMREAD_UNCHANGED)
    if im.ndim == 3 and im.shape[2] == 4:
        a = im[:, :, 3:4].astype(np.float32) / 255.0
        return (im[:, :, :3].astype(np.float32) * a + 255.0 * (1 - a)).astype(np.uint8)
    return im[:, :, :3]


def multiscale(det, bgr, scales=SCALES):
    """-> dict(native=[H,W] f32, ms=[H,W] f32).  Byte-for-byte the TEED cache's own rule."""
    H, W = bgr.shape[:2]
    outs = {}
    for s in scales:
        if s == 1.0:
            img = bgr
        else:
            h8 = int(round(H * s / 8)) * 8
            w8 = int(round(W * s / 8)) * 8
            img = cv2.resize(bgr, (w8, h8), interpolation=cv2.INTER_AREA)
        p = det.prob(img)
        if p.shape != (H, W):
            p = cv2.resize(p, (W, H), interpolation=cv2.INTER_LINEAR)
        outs[s] = p
    ms = np.maximum.reduce([outs[s] for s in scales])
    return {"native": outs[1.0].astype(np.float32), "ms": ms.astype(np.float32)}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--det", required=True, choices=sorted(DETECTORS))
    ap.add_argument("--scene", default="chair")
    ap.add_argument("--cache", default=None,
                    help="output dir; default out/<det>_edges_<scene>. NOTE the historical "
                         "recall_trackB_teed.py had a --cache default hardcoded to the CHAIR "
                         "path regardless of --scene; this one derives it from both.")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--sample_views", type=int, nargs="*", default=[0, 5, 25])
    args = ap.parse_args()

    cache = args.cache or os.path.join(OUT, f"{args.det}_edges_{args.scene}")
    os.makedirs(cache, exist_ok=True)
    cams, rgb_paths = common.load_cameras(args.scene)
    print(f"[cmepi] det={args.det} scene={args.scene} views={len(cams)} cache={cache}",
          flush=True)

    dev = args.device
    if dev.startswith("cuda") and not torch.cuda.is_available():
        dev = "cpu"
    try:
        det = DETECTORS[args.det](dev)
    except RuntimeError as e:                      # OOM on the shared card -> CPU is fine
        if "out of memory" not in str(e).lower() or dev == "cpu":
            raise
        print(f"[cmepi] GPU load failed ({e}); falling back to CPU", flush=True)
        torch.cuda.empty_cache()
        dev = "cpu"
        det = DETECTORS[args.det](dev)
    nparam = det.n_params()
    print(f"[cmepi] {det.name} loaded: {nparam} parameters ({nparam/1e6:.3f}M) "
          f"trained on {det.train_data}, device={dev}", flush=True)
    print(f"[cmepi] ckpt {det.ckpt}", flush=True)
    print(f"[cmepi] ckpt sha256 {sha256(det.ckpt)}", flush=True)

    # ---- smoke test on one view before committing to the batch (same asserts as TEED's)
    bgr0 = composite_white(rgb_paths[0])
    try:
        e0 = multiscale(det, bgr0)
    except RuntimeError as e:
        if "out of memory" not in str(e).lower() or dev == "cpu":
            raise
        print(f"[cmepi] GPU forward OOM; falling back to CPU", flush=True)
        del det
        torch.cuda.empty_cache()
        dev = "cpu"
        det = DETECTORS[args.det](dev)
        e0 = multiscale(det, bgr0)
    for k, v in e0.items():
        print(f"[cmepi] smoke {k}: shape={v.shape} dtype={v.dtype} min={v.min():.4f} "
              f"max={v.max():.4f} mean={v.mean():.4f} "
              f"frac>0.5={float((v > 0.5).mean()):.4f}", flush=True)
    assert e0["native"].shape == bgr0.shape[:2], "detector output shape != input"
    assert 0.0 <= e0["native"].min() and e0["native"].max() <= 1.0, "not a probability"
    assert e0["native"].max() > 0.5, "no confident edge — check the preprocessing contract"

    # ---- batch
    t0 = time.time()
    stats = []
    for i, p in enumerate(rgb_paths):
        e = multiscale(det, composite_white(p))
        np.savez_compressed(os.path.join(cache, f"v{i:03d}.npz"),
                            native=e["native"].astype(np.float16),
                            ms=e["ms"].astype(np.float16))
        stats.append({"view": i, "name": os.path.basename(p),
                      "frac_gt_0.5_native": float((e["native"] > 0.5).mean()),
                      "frac_gt_0.5_ms": float((e["ms"] > 0.5).mean())})
        if i % 20 == 0:
            print(f"  [{i:3d}/{len(rgb_paths)}] {os.path.basename(p)} "
                  f"frac>0.5 native={stats[-1]['frac_gt_0.5_native']:.4f} "
                  f"ms={stats[-1]['frac_gt_0.5_ms']:.4f} "
                  f"({time.time()-t0:.0f}s)", flush=True)
    dt = time.time() - t0
    print(f"[cmepi] cached {len(rgb_paths)} views in {dt:.1f}s "
          f"({dt/len(rgb_paths)*1000:.1f} ms/view, {len(SCALES)} scales each)", flush=True)

    # ---- side-by-side vs Canny, for the eyeball check
    viz = []
    for v in args.sample_views:
        bgr = composite_white(rgb_paths[v])
        e = multiscale(det, bgr)
        canny = FR.photo_edge_map(rgb_paths[v])
        panel = np.concatenate(
            [bgr, np.dstack([255 - canny] * 3),
             np.dstack([(255 * (1.0 - e["native"])).astype(np.uint8)] * 3),
             np.dstack([(255 * (1.0 - e["ms"])).astype(np.uint8)] * 3)], 1)
        cv2.putText(panel, f"RGB | CANNY(M1a) | {det.name} native | {det.name} ms",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
        pth = os.path.join(OUT, f"cmepi_sample_{args.det}_{args.scene}_v{v}.png")
        cv2.imwrite(pth, panel)
        viz.append(pth)
        print(f"[cmepi] viz -> {pth}", flush=True)

    meta = {"experiment": "CMEPI", "detector": det.name, "det_key": args.det,
            "scene": args.scene, "citation": det.citation,
            "train_data": det.train_data, "frozen_zero_shot": True, "fine_tuned": False,
            "ckpt": det.ckpt, "ckpt_sha256": sha256(det.ckpt),
            "n_params": nparam, "scales": list(SCALES), "cache": cache,
            "n_views": len(rgb_paths), "runtime_s": dt,
            "ms_per_view": dt / len(rgb_paths) * 1000, "device": dev, "viz": viz,
            "background": "white composite", "stored": "raw probability, float16",
            "per_view": stats}
    jp = os.path.join(OUT, f"cmepi_cache_{args.det}_{args.scene}.json")
    json.dump(meta, open(jp, "w"), indent=2)
    print(f"[cmepi] wrote {jp}", flush=True)
    tot = sum(os.path.getsize(os.path.join(cache, f)) for f in os.listdir(cache))
    print(f"[cmepi] DONE. cache size: {tot/1e6:.1f} MB", flush=True)


if __name__ == "__main__":
    main()
