#!/usr/bin/env python
"""PB1b TIER-0 — rank-overlap screen for cross-detector AGREEMENT-RANK.

*** NO MESH. NO GPU. Pure function of three banked seed-score vectors. ***

Operator, pre-registered to cap the variant space:
    percentile-normalise each detector score to [0,1], then elementwise MINIMUM.
    Geometric mean is the SINGLE declared sensitivity arm. Nothing else.

Frozen bar (necessary, NOT sufficient -- a pass buys only the right to spend tier-1):
    reference  O_ref = overlap(TEED_topk, DexiNed_topk)   [a channel swap already
                       measured as neutral-to-worse end-to-end]
    PASS iff   overlap(TEED_topk, AGREE_topk) <= O_ref
    FAIL       otherwise: agreement perturbs TEED LESS than a swap we already know is
               not worth taking, so it cannot produce a materially different outcome.
A tier-0 PASS may NOT greenlight a pull. Only tier-1 seed-P/R LIFT is the real gate.
"""
import json, os, sys

import numpy as np

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
SYN = os.path.join(TIER1, "scripts/explore/syn")
OUT = os.path.join(TIER1, "out")
DETS = ["teed_native_0.5", "dexined_native_0.5", "pidinet_native_0.5"]
SHORT = {"teed_native_0.5": "TEED", "dexined_native_0.5": "DexiNed",
         "pidinet_native_0.5": "PiDiNet"}
# scene -> (operative f, expected pool size, expected k)
SCENES = {"lego": (0.40, 99721, 39888), "chair": (0.30, 56884, 17065)}


def pct(s):
    """percentile-normalise to [0,1]; ties get their average rank (stable)."""
    o = np.argsort(s, kind="stable")
    r = np.empty(len(s), np.float64)
    r[o] = np.arange(len(s), dtype=np.float64)
    return r / max(len(s) - 1, 1)


def topk(s, k):
    return set(np.argsort(-s, kind="stable")[:k].tolist())


def ov(a, b, k):
    inter = len(a & b)
    return inter / k, inter / len(a | b)


def main():
    res = {}
    for scene, (f, npool, kexp) in SCENES.items():
        S = {}
        for d in DETS:
            p = os.path.join(SYN, f"finalscore_overall_{scene}__{d}.npy")
            S[d] = np.load(p)
        n = len(S[DETS[0]])
        assert all(len(v) == n for v in S.values())
        k = int(round(f * n))
        print(f"\n=== {scene}: pool={n} (expect {npool})  f={f}  k={k} (expect {kexp})")
        P = {d: pct(S[d]) for d in DETS}
        stack = np.stack([P[d] for d in DETS], 0)
        agree_min = stack.min(0)
        agree_geo = np.exp(np.log(np.clip(stack, 1e-12, None)).mean(0))
        # two-channel arm (TEED+DexiNed only) -- the version without the weak member
        st2 = np.stack([P[DETS[0]], P[DETS[1]]], 0)
        agree_min2 = st2.min(0)

        sets = {SHORT[d]: topk(S[d], k) for d in DETS}
        sets["AGREE_min3"] = topk(agree_min, k)
        sets["AGREE_geo3"] = topk(agree_geo, k)
        sets["AGREE_min2"] = topk(agree_min2, k)

        print("  pairwise overlap (|A&B|/k), i.e. the DIRECT cross-model invariance test:")
        names = list(sets)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                f1, j1 = ov(sets[a], sets[b], k)
                print(f"    {a:11s} vs {b:11s}  frac={f1:.4f}  jaccard={j1:.4f}")

        o_ref, j_ref = ov(sets["TEED"], sets["DexiNed"], k)
        rows = {}
        for arm in ("AGREE_min3", "AGREE_geo3", "AGREE_min2"):
            o, j = ov(sets["TEED"], sets[arm], k)
            passed = bool(o <= o_ref)
            rows[arm] = {"overlap_vs_TEED": o, "jaccard_vs_TEED": j,
                         "O_ref_TEED_vs_DexiNed": o_ref, "tier0_pass": passed}
            print(f"  BAR  O(TEED,{arm}) = {o:.4f}  vs  O_ref = {o_ref:.4f}  -> "
                  f"{'PASS (buys tier-1 only)' if passed else 'FAIL (no pull)'}")
        res[scene] = {"pool": n, "f": f, "k": k, "O_ref": o_ref, "jaccard_ref": j_ref,
                      "pairwise": {f"{a}|{b}": ov(sets[a], sets[b], k)[0]
                                   for i, a in enumerate(names) for b in names[i + 1:]},
                      "arms": rows}
    with open(os.path.join(OUT, "pb1b_tier0.json"), "w") as fh:
        json.dump(res, fh, indent=2)
    print(f"\nwrote out/pb1b_tier0.json")


if __name__ == "__main__":
    main()
