"""tier1/src/view_split.py — FROZEN train/val/test view split (METHOD-SAFE, mesh-free).

Every M1b number before this file was reported on views {0,25}, which were INSIDE the
100-view set the pull optimises against — i.e. in-sample. This freezes an honest split:

    TEST  10 views   never seen by the pull, never used to choose a threshold. Report here.
    VAL   10 views   used to pick gate thresholds / iteration counts.
    TRAIN 80 views   the only views the DT pull is allowed to consume.

The split is deterministic (no RNG) and spread evenly over the orbit, so no split gets a
contiguous arc of the object: test = every 10th view starting at 5, val = every 10th
starting at 0, train = the remaining 80.
"""
import numpy as np

N_VIEWS = 100


def split(n_views=N_VIEWS):
    idx = np.arange(n_views)
    test = idx[idx % 10 == 5]
    val = idx[idx % 10 == 0]
    train = idx[(idx % 10 != 5) & (idx % 10 != 0)]
    return {"train": train.tolist(), "val": val.tolist(), "test": test.tolist()}


SPLIT = split()
TRAIN, VAL, TEST = SPLIT["train"], SPLIT["val"], SPLIT["test"]

if __name__ == "__main__":
    s = split()
    for k, v in s.items():
        print(f"{k:6s} n={len(v):3d}  {v if len(v) <= 12 else str(v[:12]) + ' ...'}")
