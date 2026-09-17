# Step 4: six fixed downstream arms, before opening DEV

5-step/640-linelet smoke passed; final runs use 100 steps/16 TRAIN views for
every arm. Same sharp DT, trust bound, prune, chaining, visibility and brush.
New candidates retain their IDs/source lists through the exported chain vertices.

| Arm | Raw pool | Added | Added after prune | Added in chains | Final chains |
|---|---:|---:|---:|---:|---:|
| A | 29,916 | 0 | 0 | 0 | 2,024 |
| B top-k | 30,628 | 712 | 652 | 121 | 2,019 |
| C RGB | 30,209 | 293 | 280 | 89 | 2,026 |
| D union | 32,854 | 2,938 | 2,512 | 722 | 2,136 |
| N1 IDs | 29,916 | 0 | 0 | 0 | 2,024 |
| N2 shifted | 31,489 | 1,573 | 1,144 | 277 | 2,049 |

A and N1 path files have identical SHA256: a useful actual GPU repeat control.
Pull+prune+chain took 2.9–4.1 s per arm. Native counts do not measure picture quality.

Personally inspected `step4/raw_053.png`: the track assembly remains largely absent;
the missing cab roof span and bucket lower lip are not clearly restored as coherent
structure. Most additions are near existing support or on the baseplate. No G1 GO
is justified from raw projection. The baseline raw pool is already dense in the
regions where final drawings fragment: final sparsity is not solely seed absence.

All raw/new-only panels and linelet/chain arrays were generated before DEV access.
The next commit freezes paths (checksummed in `step4.json`) and the deterministic
full-orbit rendering/ink calibration code. DEV results cannot change method settings.
