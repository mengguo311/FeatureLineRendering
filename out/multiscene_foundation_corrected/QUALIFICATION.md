# Completed corrected qualification

All eight frozen iteration-30000 checkpoints and all 36 unchanged doses were evaluated. This phase used 512 image-quality rows and 1,152 controlled-dose rows. No local scientific threshold was changed.

| Scene | Seed1729 eligible | Seed2718 eligible | Route A | Route B | Qualified doses |
|---|---|---|---|---|---:|
| lego | True | False | False | True | 9/9 |
| chair | True | True | True | True | 9/9 |
| drums | False | False | False | False | 8/9 |
| ficus | False | False | False | False | 8/9 |

Lego seed2718 passes every image-quality and independent-pair row, but native replay black-RGB maximum error in TRAIN view53 is0.003987360746, exceeding1/255=0.003921568627. Stock top-level/native800 image equality is exact in that view; the failed check is the separate replay calibration. Route A is therefore unavailable. The valid seed1729 parent and all nine controlled doses support Route B.

Drums and Ficus fail the unchanged parent-quality gates. Their qualified perturbations do not repair parent quality. Drums moment_split_03 fails the unchanged RGB equivalence gate. Ficus redistribute_00 fails minor-child coverage (minimum0.004337673127, below0.005). All dose rows and all backgrounds are retained.

Only Lego and Chair enter local scientific inference. Expanded scope is INSUFFICIENT_POSTERIOR_QUALITY because fewer than three scenes qualify and neither Drums nor Ficus qualifies. Local scientific verdicts remain separate from this scope limitation.
