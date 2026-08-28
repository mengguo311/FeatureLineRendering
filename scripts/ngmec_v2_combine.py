#!/usr/bin/env python
"""NG-MEC-v2 — ADDITIVE log-odds combination of three orthogonal cues. METHOD-SAFE.

    S = w_teed * R(S_teed) + w_2dgs * R(S_normal) + w_epi * R(S_consensus)

R(.) = rankdata(v)/len(v) in (0,1], the M1a recipe's OWN rank transform (score_from_evidence
combines its channels as g = R(soft) + 0.5*R(rq90); eco_score.py:16-19 spends consensus the
same way). Rank-transforming each cue makes the sum a monotone, scale-free additive
log-odds pool: no cue can dominate through its units, and every cue keeps a vote everywhere.

NO VETO CASCADE. Nothing here thresholds any cue. That is the point: this project has two
recorded failures of the alternative — ECO's hard consensus veto was a NO-GO on lego, and
TGAP's frozen edge prior was ANTI-predictive once used as a gate. Orthogonal evidence is
spent additively.

CUES
  teed  scripts/explore/syn/finalscore_overall_<scene>__teed_native_0.5.npy
        frozen zero-shot TEED (BIPED weights), the validated rankable proposal source.
  2dgs  out/ngmec_v2_cue2dgs_<scene>.npy      (scripts/ngmec_v2_cue2dgs.py)
        continuous 2DGS rendered-normal ribbon dihedral, degrees.
  epi   out/eco_C_<scene>__teed0.5_K3_t2.5_r0_s16.npy   (scripts/eco_consensus.py)
        continuous multi-view epipolar consensus C in [0,1], TEED-keyed to match the base.

WRITES ONLY NEW NAMES. finalscore_overall_* files are protected by
out/CMEPI_protected_manifest.sha256; this script writes
finalscore_overall_<scene>__ngmecv2_<tag>.npy, a name that cannot collide with any
existing entry, and refuses to overwrite anything that already exists.
"""
import argparse, os, sys

import numpy as np
from scipy.stats import rankdata

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
SYN = os.path.join(TIER1, "scripts/explore/syn")
OUT = os.path.join(TIER1, "out")

BASE = "teed_native_0.5"
ECO_TAG = "teed0.5_K3_t2.5_r0_s16"


def R(v):
    """The recipe's own rank transform: rankdata(v)/len(v) -> (0, 1]."""
    return rankdata(v, method="average") / float(len(v))


def load_cues(scene):
    b = np.load(os.path.join(SYN, f"finalscore_overall_{scene}__{BASE}.npy"))
    g = np.load(os.path.join(OUT, f"ngmec_v2_cue2dgs_{scene}.npy"))
    c = np.load(os.path.join(OUT, f"eco_C_{scene}__{ECO_TAG}.npy"))
    assert len(b) == len(g) == len(c), (len(b), len(g), len(c))
    return b, g, c


def combine(scene, w_teed, w_2dgs, w_epi):
    b, g, c = load_cues(scene)
    return w_teed * R(b) + w_2dgs * R(g) + w_epi * R(c)


def wtag(w_2dgs, w_epi):
    return f"g{w_2dgs:g}_e{w_epi:g}".replace(".", "p")


def write(scene, w_teed, w_2dgs, w_epi, force=False):
    S = combine(scene, w_teed, w_2dgs, w_epi)
    name = f"finalscore_overall_{scene}__ngmecv2_{wtag(w_2dgs, w_epi)}.npy"
    p = os.path.join(SYN, name)
    if os.path.exists(p) and not force:
        return p, S, False
    np.save(p, S)
    return p, S, True


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="chair")
    ap.add_argument("--w_teed", type=float, default=1.0)
    ap.add_argument("--w_2dgs", type=float, required=True)
    ap.add_argument("--w_epi", type=float, required=True)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    p, S, made = write(a.scene, a.w_teed, a.w_2dgs, a.w_epi, a.force)
    print(f"[ngmecv2] {a.scene}  w=({a.w_teed:g},{a.w_2dgs:g},{a.w_epi:g})  "
          f"n={len(S)}  {'wrote' if made else 'exists'} {os.path.basename(p)}")
