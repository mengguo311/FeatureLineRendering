"""Decisive test: is the 22% precision gap CARRIER JITTER (fixable by DT, distance 2.5-5px)
or STRUCTURAL false positives (>5px, texture/silhouette noise)? Sweep the precision label
tolerance tau_p and watch how precision climbs for the OVERALL recipe operating points."""
import os, sys, numpy as np
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1"))
sys.path.insert(0, os.path.expanduser("~/3dgs_line/tier1/scripts/explore/syn"))
from tune_lib import Harness
import numpy as np

scene = sys.argv[1] if len(sys.argv) > 1 else "chair"
h = Harness(scene)
X = h.X
s = np.load(os.path.expanduser(f"~/3dgs_line/tier1/scripts/explore/syn/finalscore_overall_{scene}.npy"))
o = np.argsort(-s, kind="stable")

TAUS = [2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0]
print(f"=== {scene}: OVERALL recipe, precision@tau_p sweep (recall fixed @3.0px) ===")
print(f"{'f':>5} {'n':>6} | " + " ".join(f"P@{t}".rjust(7) for t in TAUS) + " | recall@3")
for f in [0.30, 0.25, 0.22, 0.20]:
    keep = np.zeros(len(X), bool); keep[o[:int(round(f*len(X)))]] = True
    row = []
    for t in TAUS:
        p, r, nv = h.evaluate(X, extra_mask=keep, tau_p=t, tau_r=3.0)
        row.append(p)
        rec = r
    print(f"{f:>5} {int(keep.sum()):>6} | " + " ".join(f"{p:7.3f}" for p in row) + f" | {rec:.3f}")
print("\nInterpretation: if P jumps 0.77->0.90+ from 2.5->5px => carrier JITTER (DT-fixable).")
print("If P only crawls 0.77->0.83 => genuine structural false positives (method-limited).")
